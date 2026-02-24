#!/usr/bin/env python3 -u
"""
使用 Qwen3-ASR 提取视频/音频语音转文字
用法: python extract_transcript.py <视频/音频文件路径> [输出目录]

环境变量（可选）：
- QWEN_ASR_MODEL_PATH: 本地模型路径（优先级最高）
- QWEN_ASR_MODEL: ModelScope 模型名（Qwen/Qwen3-ASR-1.7B 或 Qwen/Qwen3-ASR-0.6B）
- QWEN_ASR_DEVICE: 强制指定设备（cpu/cuda/mps）
- QWEN_ASR_DTYPE: 数据类型（float16/bfloat16/float32）
- QWEN_ASR_CHUNK_SECONDS: 每块音频时长（秒），默认 60

使用前请先安装 qwen-asr：
pip install -U qwen-asr

首次使用会自动下载模型，或提前下载：
modelscope download --model Qwen/Qwen3-ASR-1.7B --local_dir ./Qwen3-ASR-1.7B
"""
import sys
import os
import time
import subprocess
import tempfile
import shutil
from pathlib import Path

# 禁用输出缓冲，确保实时显示进度
sys.stdout.reconfigure(line_buffering=True)


# ============================================================
# 进度显示工具
# ============================================================

def format_timestamp(seconds: float) -> str:
    """格式化时间戳为 HH:MM:SS 格式"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_eta(seconds: float) -> str:
    """格式化预计剩余时间"""
    if seconds <= 0:
        return "完成"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def print_progress(current_chunk: int, total_chunks: int,
                   current_pos: float, total_duration: float,
                   elapsed: float, chunk_start_time: float):
    """打印进度条"""
    pct = current_pos / total_duration if total_duration > 0 else 0
    bar_width = 40
    filled = int(bar_width * pct)
    bar = "█" * filled + "░" * (bar_width - filled)

    # 预计剩余时间（根据已处理时长 / 耗时比例推算）
    if elapsed > 0 and pct > 0:
        eta_secs = elapsed / pct * (1 - pct)
    else:
        eta_secs = 0

    speed = current_pos / elapsed if elapsed > 0 else 0  # 音频倍速

    print(
        f"\r  [{bar}] {pct*100:5.1f}%  "
        f"已处理 {format_timestamp(current_pos)} / {format_timestamp(total_duration)}  "
        f"块 {current_chunk}/{total_chunks}  "
        f"速度 {speed:.1f}x  "
        f"剩余 {format_eta(eta_secs)}",
        end="",
        flush=True,
    )


# ============================================================
# 媒体信息
# ============================================================

def get_media_duration(media_path: str) -> float:
    """
    使用 ffprobe 获取媒体文件总时长（秒）。
    失败时返回 0。
    """
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(media_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


# ============================================================
# 音频切块
# ============================================================

def split_audio_to_chunks(media_path: str, chunk_seconds: int, tmp_dir: str) -> list:
    """
    使用 ffmpeg 将音频/视频切成固定时长的 WAV 片段。

    Returns:
        [(chunk_index, chunk_path, start_sec, end_sec), ...]
    """
    duration = get_media_duration(media_path)
    if duration <= 0:
        # 无法获取时长，退化为不分块处理
        return [(0, str(media_path), 0.0, 0.0)]

    chunks = []
    start = 0.0
    idx = 0
    while start < duration:
        end = min(start + chunk_seconds, duration)
        chunk_path = os.path.join(tmp_dir, f"chunk_{idx:04d}.wav")
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-i", str(media_path),
            "-t", str(end - start),
            "-ar", "16000",   # 16kHz，ASR 标准采样率
            "-ac", "1",       # 单声道
            "-f", "wav",
            chunk_path,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode != 0:
            print(f"\n⚠️  切片 {idx} 失败（ffmpeg 错误），跳过该片段", flush=True)
        else:
            chunks.append((idx, chunk_path, start, end))
        start = end
        idx += 1

    return chunks, duration


# ============================================================
# 硬件检测
# ============================================================

def get_hardware_config():
    """
    获取硬件检测并推荐最优配置

    Returns:
        配置字典，包含模型名称、设备、dtype 等
    """
    try:
        script_dir = Path(__file__).parent
        sys.path.insert(0, str(script_dir))

        from detect_hardware import HardwareDetector
        detector = HardwareDetector()
        hardware_info = detector.detect_all()
        config = detector.recommend_qwen_asr_config(hardware_info)
        return config, hardware_info, detector
    except Exception as e:
        print(f"注意: 硬件检测失败 ({e})，使用默认配置")
        return {
            "model": "Qwen/Qwen3-ASR-1.7B",
            "device": "cpu",
            "dtype": "float32",
            "reason": "使用默认配置",
            "estimated_speedup": "1x (基准)",
        }, None, None


# ============================================================
# 主流程
# ============================================================

def extract_transcript(media_path: str, output_dir: str = None) -> str:
    """
    提取视频/音频的逐字稿（支持实时进度显示）

    Args:
        media_path: 视频/音频文件路径
        output_dir: 输出目录，默认为文件所在目录

    Returns:
        输出文件的路径
    """
    # ---- 导入检测 ----
    use_qwen_asr = False
    asr_model = None
    inference_pipeline = None

    try:
        import torch
        from qwen_asr import Qwen3ASRModel
        use_qwen_asr = True
        print("使用 qwen-asr 官方 API")
    except (ImportError, TypeError):
        print("注意: qwen-asr 不可用 (需要 Python 3.10+)")
        print("尝试使用 ModelScope pipeline 作为备选方案...")

    if not use_qwen_asr:
        try:
            import torch
            from modelscope.pipelines import pipeline
            from modelscope.utils.constant import Tasks
            print("✓ ModelScope 导入成功")
        except ImportError as e:
            print(f"错误: modelscope 未安装")
            print(f"详细错误: {e}")
            print(f"请运行: pip install -U modelscope")
            sys.exit(1)

    media_file = Path(media_path)
    if not media_file.exists():
        raise FileNotFoundError(f"文件不存在: {media_path}")

    # ---- 输出路径 ----
    if output_dir is None:
        output_dir = media_file.parent
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    output_filename = f"{media_file.stem}_逐字稿.md"
    output_path = output_dir / output_filename

    # ---- 硬件 & 模型配置 ----
    local_model_path = os.environ.get("QWEN_ASR_MODEL_PATH")
    env_model = os.environ.get("QWEN_ASR_MODEL")
    env_device = os.environ.get("QWEN_ASR_DEVICE")
    env_dtype = os.environ.get("QWEN_ASR_DTYPE")
    chunk_seconds = int(os.environ.get("QWEN_ASR_CHUNK_SECONDS", "60"))

    if local_model_path and Path(local_model_path).exists():
        model = local_model_path
        if env_device and env_dtype:
            device = env_device
            dtype = env_dtype
        else:
            config, _, _ = get_hardware_config()
            device = env_device or config.get("device", "cpu")
            dtype = env_dtype or config.get("dtype", "float32")
        print("=" * 60)
        print("使用本地模型")
        print("=" * 60)
        print(f"模型路径: {model}")
        print(f"设备: {device}")
        print(f"数据类型: {dtype}")
        print("=" * 60 + "\n")
    elif env_model or env_device:
        model = env_model or "Qwen/Qwen3-ASR-1.7B"
        device = env_device or "cpu"
        dtype = env_dtype or "float32"
        print("=" * 60)
        print("使用环境变量指定的配置")
        print("=" * 60)
        print(f"模型: {model}")
        print(f"设备: {device}")
        print(f"数据类型: {dtype}")
        print("=" * 60 + "\n")
    else:
        print("=" * 60)
        print("正在检测硬件配置...")
        print("=" * 60)

        config, hardware_info, detector = get_hardware_config()

        if hardware_info and detector:
            detector.print_hardware_info(hardware_info)
            detector.print_recommended_config(config)
            model = config["model"]
            device = config["device"]
            dtype = config.get("dtype", "float32")
        else:
            model = "Qwen/Qwen3-ASR-1.7B"
            device = "cpu"
            dtype = "float32"
            print("使用默认配置: Qwen/Qwen3-ASR-1.7B/CPU/float32")

    # dtype 按设备修正
    if device == "mps":
        dtype = dtype if env_dtype else "bfloat16"
    elif device == "cuda":
        dtype = dtype if env_dtype else "bfloat16"
    else:
        dtype = dtype if env_dtype else "float32"

    print("=" * 60)
    print(f"正在加载 Qwen3-ASR 模型...")
    print(f"模型: {model}")
    print(f"设备: {device}")
    print(f"数据类型: {dtype}")
    print("=" * 60 + "\n")

    # ---- 加载模型 ----
    import torch
    if use_qwen_asr:
        model_kwargs = {
            "dtype": getattr(torch, dtype),
            "device_map": device,
            "max_inference_batch_size": 8,
            "max_new_tokens": 256,
        }
        if device == "cpu":
            model_kwargs.pop("device_map", None)

        asr_model = Qwen3ASRModel.from_pretrained(model, **model_kwargs)
    else:
        from modelscope.pipelines import pipeline
        from modelscope.utils.constant import Tasks

        if device == "mps":
            device_for_pipeline = "mps" if torch.backends.mps.is_available() else "cpu"
        elif device == "cuda":
            device_for_pipeline = "gpu"
        else:
            device_for_pipeline = "cpu"

        inference_pipeline = pipeline(
            task=Tasks.auto_speech_recognition,
            model=model,
            device=device_for_pipeline,
        )

    # ---- 获取媒体时长 ----
    print(f"正在分析文件: {media_file.name}")
    total_duration = get_media_duration(str(media_file))

    if total_duration > 0:
        print(f"文件时长: {format_timestamp(total_duration)}")
        print(f"转录块大小: {chunk_seconds} 秒/块（共约 {int(total_duration / chunk_seconds) + 1} 块）")
        print(f"（可通过环境变量 QWEN_ASR_CHUNK_SECONDS 调整块大小）\n")
    else:
        print("⚠️  无法获取文件时长，将整体处理（无法显示进度）\n")

    print(f"{'=' * 60}")
    print("开始转录，请稍候...")
    print(f"{'=' * 60}\n")

    # ---- 切块 & 逐块转录 ----
    tmp_dir = tempfile.mkdtemp(prefix="qwen_asr_")
    all_segments = []          # [(start_sec, end_sec, text), ...]
    full_text_parts = []
    detected_language = "未知"

    total_start = time.time()

    try:
        if total_duration > 0 and total_duration > chunk_seconds:
            # ---- 分块处理（显示进度） ----
            chunks_result = split_audio_to_chunks(str(media_file), chunk_seconds, tmp_dir)
            chunks, _ = chunks_result

            total_chunks = len(chunks)
            print(f"共切分 {total_chunks} 个音频块，开始逐块转录：\n")

            chunk_start_time = time.time()
            for chunk_idx, (i, chunk_path, chunk_start, chunk_end) in enumerate(chunks):
                # 打印当前块信息
                print(
                    f"  ▶ 处理块 {chunk_idx + 1}/{total_chunks}  "
                    f"[{format_timestamp(chunk_start)} → {format_timestamp(chunk_end)}]",
                    flush=True,
                )

                t0 = time.time()

                if use_qwen_asr:
                    results = asr_model.transcribe(audio=chunk_path, language=None)
                    if results and len(results) > 0:
                        r = results[0]
                        chunk_text = getattr(r, "text", "").strip()
                        detected_language = getattr(r, "language", detected_language) or detected_language
                        time_stamps = getattr(r, "time_stamps", None)

                        if time_stamps:
                            for ts in time_stamps:
                                if isinstance(ts, dict):
                                    s = chunk_start + ts.get("start", 0)
                                    e = chunk_start + ts.get("end", 0)
                                    t = ts.get("text", "").strip()
                                else:
                                    s = chunk_start + getattr(ts, "start_time", 0)
                                    e = chunk_start + getattr(ts, "end_time", 0)
                                    t = getattr(ts, "text", "").strip()
                                all_segments.append((s, e, t))
                        else:
                            all_segments.append((chunk_start, chunk_end, chunk_text))

                        full_text_parts.append(chunk_text)
                    else:
                        all_segments.append((chunk_start, chunk_end, ""))
                else:
                    result = inference_pipeline(audio_in=chunk_path)
                    chunk_text = result.get("text", "").strip()
                    detected_language = result.get("language", detected_language) or detected_language
                    timestamps = result.get("timestamps", [])

                    if timestamps:
                        for ts in timestamps:
                            s = chunk_start + ts.get("start", 0)
                            e = chunk_start + ts.get("end", 0)
                            t = ts.get("text", "").strip()
                            all_segments.append((s, e, t))
                    else:
                        all_segments.append((chunk_start, chunk_end, chunk_text))
                    full_text_parts.append(chunk_text)

                elapsed_chunk = time.time() - t0
                elapsed_total = time.time() - total_start
                processed_audio = chunk_end

                # 打印进度条
                print_progress(
                    chunk_idx + 1, total_chunks,
                    processed_audio, total_duration,
                    elapsed_total, chunk_start_time,
                )
                print(f"  ✓ 耗时 {elapsed_chunk:.1f}s", flush=True)

            print(f"\n{'=' * 60}")
            print(f"✓ 全部 {total_chunks} 块转录完成！总耗时 {format_eta(time.time() - total_start)}")
            print(f"{'=' * 60}\n")

        else:
            # ---- 整体处理（文件较短，或无法获取时长） ----
            print("文件较短，整体处理中...", flush=True)
            if use_qwen_asr:
                results = asr_model.transcribe(audio=str(media_file), language=None)
                if results and len(results) > 0:
                    r = results[0]
                    text_result = getattr(r, "text", "")
                    detected_language = getattr(r, "language", "未知") or "未知"
                    time_stamps = getattr(r, "time_stamps", None)
                    if time_stamps:
                        for ts in time_stamps:
                            if isinstance(ts, dict):
                                s = ts.get("start", 0)
                                e = ts.get("end", 0)
                                t = ts.get("text", "").strip()
                            else:
                                s = getattr(ts, "start_time", 0)
                                e = getattr(ts, "end_time", 0)
                                t = getattr(ts, "text", "").strip()
                            all_segments.append((s, e, t))
                    else:
                        full_text_parts.append(text_result)
            else:
                result = inference_pipeline(audio_in=str(media_file))
                text_result = result.get("text", "")
                detected_language = result.get("language", "未知") or "未知"
                timestamps = result.get("timestamps", [])
                if timestamps:
                    for ts in timestamps:
                        s = ts.get("start", 0)
                        e = ts.get("end", 0)
                        t = ts.get("text", "").strip()
                        all_segments.append((s, e, t))
                else:
                    full_text_parts.append(text_result)

            elapsed = time.time() - total_start
            print(f"✓ 转录完成，耗时 {format_eta(elapsed)}\n")

    finally:
        # 清理临时目录
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # ---- 生成 Markdown ----
    md_content = f"""# {media_file.stem} - 逐字稿

**文件名**: {media_file.name}
**模型**: {model}
**设备**: {device}
**识别语言**: {detected_language}

---

## 完整逐字稿

"""

    if all_segments:
        for i, (start_sec, end_sec, text) in enumerate(all_segments, 1):
            if text:
                md_content += f"### [{i:03d}] {format_timestamp(start_sec)} - {format_timestamp(end_sec)}\n\n{text}\n\n"
    else:
        md_content += "\n".join(full_text_parts)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"✓ 逐字稿已保存到: {output_path}")
    print(f"✓ 识别语言: {detected_language}")
    print("\n处理完成！")

    return str(output_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python extract_transcript.py <视频/音频文件路径> [输出目录]")
        sys.exit(1)

    media_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        extract_transcript(media_path, output_dir)
    except Exception as e:
        import traceback
        print(f"错误: {e}")
        traceback.print_exc()
        sys.exit(1)
