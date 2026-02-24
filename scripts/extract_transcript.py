#!/usr/bin/env python3 -u
"""
使用 Qwen3-ASR 提取视频/音频语音转文字
用法: python extract_transcript.py <视频/音频文件路径> [输出目录]

环境变量（可选）：
- QWEN_ASR_MODEL_PATH: 本地模型路径（优先级最高）
- QWEN_ASR_MODEL: ModelScope 模型名（Qwen/Qwen3-ASR-1.7B 或 Qwen/Qwen3-ASR-0.6B）
- QWEN_ASR_DEVICE: 强制指定设备（cpu/cuda/mps）

使用前请先下载模型：
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
        配置字典，包含模型名称、设备等
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
    try:
        from modelscope.pipelines import pipeline
        from modelscope.utils.constant import Tasks
    except ImportError:
        print("错误: modelscope 未安装")
        print("请运行: pip install modelscope torch torchaudio soundfile")
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

    # 确定使用的模型
    if local_model_path and Path(local_model_path).exists():
        # 使用本地模型
        model = local_model_path
        device = env_device or "cpu"
        print("=" * 60)
        print("使用本地模型")
        print("=" * 60)
        print(f"模型路径: {model}")
        print(f"设备: {device}")
        print("=" * 60 + "\n")
    elif env_model or env_device:
        # 用户手动指定了 ModelScope 模型名
        model = env_model or "Qwen/Qwen3-ASR-1.7B"
        device = env_device or "cpu"
        print("=" * 60)
        print("使用环境变量指定的配置")
        print("=" * 60)
        print(f"模型: {model}")
        print(f"设备: {device}")
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
        else:
            # 使用默认配置
            model = "Qwen/Qwen3-ASR-1.7B"
            device = "cpu"
            print("使用默认配置: Qwen/Qwen3-ASR-1.7B/CPU")

    print("=" * 60)
    print(f"正在加载 Qwen3-ASR 模型...")
    print(f"模型: {model}")
    print(f"设备: {device}")
    print("=" * 60 + "\n")

    # 初始化推理 pipeline
    # Qwen3-ASR 支持: "auto", "cpu", "cuda", "mps"
    inference_pipeline = pipeline(
        task=Tasks.auto_speech_recognition,
        model=model,
        device=device
    )

    print(f"\n正在处理文件: {media_file.name}")
    print("这可能需要几分钟，请耐心等待...\n")

    # 执行识别
    # Qwen3-ASR 会自动处理音频，并返回带时间戳的结果
    result = inference_pipeline(audio_in=str(media_file))

    # 解析结果
    # Qwen3-ASR 返回格式: {"text": "...", "timestamps": [...]}
    text_result = result.get("text", "")
    timestamps = result.get("timestamps", [])

    print(f"\n✓ 语音识别完成\n")

    # 生成 Markdown 格式输出
    md_content = f"""# {media_file.stem} - 逐字稿

**文件名**: {media_file.name}
**模型**: {model}
**设备**: {device}

---

## 完整逐字稿

"""

    # 添加逐字稿内容
    if timestamps:
        # 有时间戳的情况，分段显示
        for i, ts in enumerate(timestamps, 1):
            if isinstance(ts, dict):
                start_time = format_timestamp(ts.get("start", 0))
                end_time = format_timestamp(ts.get("end", 0))
                text = ts.get("text", "").strip()
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
