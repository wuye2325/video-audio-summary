#!/usr/bin/env python3 -u
"""
使用 Qwen3-ASR 提取视频/音频语音转文字
用法: python extract_transcript.py <视频/音频文件路径> [输出目录]

环境变量（可选）：
- QWEN_ASR_MODEL_PATH: 本地模型路径（优先级最高）
- QWEN_ASR_MODEL: ModelScope 模型名（Qwen/Qwen3-ASR-1.7B 或 Qwen/Qwen3-ASR-0.6B）
- QWEN_ASR_DEVICE: 强制指定设备（cpu/cuda/mps）
- QWEN_ASR_DTYPE: 数据类型（float16/bfloat16/float32）

使用前请先安装 qwen-asr：
pip install -U qwen-asr

首次使用会自动下载模型，或提前下载：
modelscope download --model Qwen/Qwen3-ASR-1.7B --local_dir ./Qwen3-ASR-1.7B
"""
import sys
import os
import time
from pathlib import Path

# 禁用输出缓冲，确保实时显示进度
sys.stdout.reconfigure(line_buffering=True)


def format_timestamp(seconds: float) -> str:
    """格式化时间戳为 HH:MM:SS 格式"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def get_hardware_config():
    """
    获取硬件检测并推荐最优配置

    Returns:
        配置字典，包含模型名称、设备、dtype 等
    """
    # 尝试导入硬件检测模块
    try:
        # 添加脚本目录到路径
        script_dir = Path(__file__).parent
        sys.path.insert(0, str(script_dir))

        from detect_hardware import HardwareDetector
        detector = HardwareDetector()

        # 检测硬件
        hardware_info = detector.detect_all()

        # 获取推荐配置
        config = detector.recommend_qwen_asr_config(hardware_info)

        return config, hardware_info, detector
    except Exception as e:
        # 硬件检测失败，使用默认配置
        print(f"注意: 硬件检测失败 ({e})，使用默认配置")
        return {
            "model": "Qwen/Qwen3-ASR-1.7B",
            "device": "cpu",
            "dtype": "float32",
            "reason": "使用默认配置",
            "estimated_speedup": "1x (基准)",
        }, None, None


def extract_transcript(media_path: str, output_dir: str = None) -> str:
    """
    提取视频/音频的逐字稿

    Args:
        media_path: 视频/音频文件路径
        output_dir: 输出目录，默认为文件所在目录

    Returns:
        输出文件的路径
    """
    # 导入 qwen-asr 或 ModelScope pipeline（备选方案）
    use_qwen_asr = False
    asr_model = None
    inference_pipeline = None

    # 尝试导入 qwen-asr
    try:
        import torch
        from qwen_asr import Qwen3ASRModel
        use_qwen_asr = True
        print("使用 qwen-asr 官方 API")
    except (ImportError, TypeError) as e:
        print(f"注意: qwen-asr 不可用 (需要 Python 3.10+)")
        print(f"尝试使用 ModelScope pipeline 作为备选方案...")

    # 如果 qwen-asr 不可用，尝试使用 ModelScope
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

    # 确定输出目录
    if output_dir is None:
        output_dir = media_file.parent
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    # 输出文件名
    output_filename = f"{media_file.stem}_逐字稿.md"
    output_path = output_dir / output_filename

    # ========================================
    # 硬件检测与自动配置优化
    # ========================================

    # 优先检查本地模型路径
    local_model_path = os.environ.get("QWEN_ASR_MODEL_PATH")
    env_model = os.environ.get("QWEN_ASR_MODEL")
    env_device = os.environ.get("QWEN_ASR_DEVICE")
    env_dtype = os.environ.get("QWEN_ASR_DTYPE")

    # 确定使用的模型
    if local_model_path and Path(local_model_path).exists():
        # 使用本地模型
        model = local_model_path
        device = env_device or "cpu"
        dtype = env_dtype or "float32"
        print("=" * 60)
        print("使用本地模型")
        print("=" * 60)
        print(f"模型路径: {model}")
        print(f"设备: {device}")
        print(f"数据类型: {dtype}")
        print("=" * 60 + "\n")
    elif env_model or env_device:
        # 用户手动指定了 ModelScope 模型名
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
        # 自动检测硬件并推荐最优配置
        print("=" * 60)
        print("正在检测硬件配置...")
        print("=" * 60)

        config, hardware_info, detector = get_hardware_config()

        if hardware_info and detector:
            # 显示硬件信息
            detector.print_hardware_info(hardware_info)

            # 显示推荐配置
            detector.print_recommended_config(config)

            # 使用推荐配置
            model = config["model"]
            device = config["device"]
            dtype = config.get("dtype", "float32")
        else:
            # 使用默认配置
            model = "Qwen/Qwen3-ASR-1.7B"
            device = "cpu"
            dtype = "float32"
            print("使用默认配置: Qwen/Qwen3-ASR-1.7B/CPU/float32")

    # 根据 device 自动选择合适的 dtype（官方推荐 bfloat16，模型权重格式为 BF16）
    if device == "mps":
        # Apple Silicon M1+ 支持 bfloat16，与官方示例保持一致
        dtype = dtype if env_dtype else "bfloat16"
    elif device == "cuda":
        # NVIDIA GPU 推荐 bfloat16（官方文档示例），也支持 float16
        dtype = dtype if env_dtype else "bfloat16"
    else:
        # CPU 使用 float32 确保精度
        dtype = dtype if env_dtype else "float32"

    print("=" * 60)
    print(f"正在加载 Qwen3-ASR 模型...")
    print(f"模型: {model}")
    print(f"设备: {device}")
    print(f"数据类型: {dtype}")
    print("=" * 60 + "\n")

    # 初始化模型
    import torch
    if use_qwen_asr:
        # qwen-asr 官方 API
        model_kwargs = {
            "dtype": getattr(torch, dtype),
            "device_map": device,
            "max_inference_batch_size": 8,
            "max_new_tokens": 256,
        }

        # 如果是 CPU，移除 device_map 参数（qwen-asr 会自动处理）
        if device == "cpu":
            model_kwargs.pop("device_map", None)

        asr_model = Qwen3ASRModel.from_pretrained(model, **model_kwargs)
    else:
        # ModelScope pipeline（备选方案）
        from modelscope.pipelines import pipeline
        from modelscope.utils.constant import Tasks

        # 转换设备名称到 ModelScope 格式
        if device == "mps":
            # 检查 MPS 可用性
            if torch.backends.mps.is_available():
                device_for_pipeline = "mps"
            else:
                device_for_pipeline = "cpu"
        elif device == "cuda":
            device_for_pipeline = "gpu"
        else:
            device_for_pipeline = "cpu"

        inference_pipeline = pipeline(
            task=Tasks.auto_speech_recognition,
            model=model,
            device=device_for_pipeline
        )

    print(f"\n正在处理文件: {media_file.name}")
    print("这可能需要几分钟，请耐心等待...\n")

    # 执行识别
    if use_qwen_asr:
        # qwen-asr 官方 API
        results = asr_model.transcribe(
            audio=str(media_file),
            language=None,  # 自动检测语言
        )
    else:
        # ModelScope pipeline（备选方案）
        result = inference_pipeline(audio_in=str(media_file))

    print(f"\n✓ 语音识别完成\n")

    # 解析结果
    if use_qwen_asr:
        # qwen-asr 返回的是结果对象列表
        if results and len(results) > 0:
            result_obj = results[0]
            text_result = getattr(result_obj, "text", "")
            detected_language = getattr(result_obj, "language", "未知")
            time_stamps = getattr(result_obj, "time_stamps", None)
        else:
            text_result = ""
            detected_language = "未知"
            time_stamps = None
    else:
        # ModelScope pipeline 返回字典
        text_result = result.get("text", "")
        detected_language = result.get("language", "未知")
        time_stamps = result.get("timestamps", [])

    # 生成 Markdown 格式输出
    md_content = f"""# {media_file.stem} - 逐字稿

**文件名**: {media_file.name}
**模型**: {model}
**设备**: {device}
**识别语言**: {detected_language}

---

## 完整逐字稿

"""

    # 添加逐字稿内容
    if time_stamps:
        # 有时间戳的情况，分段显示
        for i, ts in enumerate(time_stamps, 1):
            if isinstance(ts, dict):
                start_time = format_timestamp(ts.get("start", 0))
                end_time = format_timestamp(ts.get("end", 0))
                text = ts.get("text", "").strip()
                md_content += f"### [{i:03d}] {start_time} - {end_time}\n\n{text}\n\n"
            elif hasattr(ts, "text") and hasattr(ts, "start_time"):
                start_time = format_timestamp(ts.start_time)
                end_time = format_timestamp(ts.end_time)
                text = ts.text.strip()
                md_content += f"### [{i:03d}] {start_time} - {end_time}\n\n{text}\n\n"
            else:
                # 兼容其他格式
                md_content += f"{ts}\n\n"
    else:
        # 无时间戳，直接显示文本
        md_content += text_result

    # 保存到文件
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
