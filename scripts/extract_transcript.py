#!/usr/bin/env python3 -u
"""
使用 faster-whisper 提取视频/音频语音转文字
用法: python extract_transcript.py <视频/音频文件路径> [输出目录]

环境变量（可选）：
- HF_ENDPOINT: Hugging Face 镜像地址，中国大陆用户推荐设置为 https://hf-mirror.com
- WHISPER_MODEL: 强制指定模型大小（tiny/small/base/medium/large-v3/large-v3-turbo）
- WHISPER_DEVICE: 强制指定设备（cpu/cuda）
- WHISPER_COMPUTE_TYPE: 强制指定计算类型（float32/float16/int8/default）
"""
import sys
import os
import time
from pathlib import Path

# 禁用输出缓冲，确保实时显示进度
sys.stdout.reconfigure(line_buffering=True)

# 设置 Hugging Face 镜像（优先使用国内镜像加速模型下载）
# 如果用户未设置 HF_ENDPOINT，默认使用 hf-mirror.com
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

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
        配置字典，包含模型大小、设备、计算类型等
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
        config = detector.recommend_whisper_config(hardware_info)

        return config, hardware_info, detector
    except Exception as e:
        # 硬件检测失败，使用默认配置
        print(f"注意: 硬件检测失败 ({e})，使用默认配置")
        return {
            "model_size": "medium",
            "device": "cpu",
            "compute_type": "default",
            "batch_size": 16,
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
        from faster_whisper import WhisperModel
    except ImportError:
        print("错误: faster-whisper 未安装")
        print("请运行: pip install faster-whisper")
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

    # 检查是否有环境变量强制指定配置
    env_model = os.environ.get("WHISPER_MODEL")
    env_device = os.environ.get("WHISPER_DEVICE")
    env_compute_type = os.environ.get("WHISPER_COMPUTE_TYPE")

    if env_model or env_device or env_compute_type:
        # 用户手动指定了配置，跳过自动检测
        model_size = env_model or "medium"
        device = env_device or "cpu"
        compute_type = env_compute_type or "default"
        print("=" * 60)
        print("使用环境变量指定的配置")
        print("=" * 60)
        print(f"模型: {model_size}")
        print(f"设备: {device}")
        print(f"计算类型: {compute_type}")
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
            model_size = config["model_size"]
            device = config["device"]
            compute_type = config["compute_type"]
            batch_size = config["batch_size"]
        else:
            # 使用默认配置
            model_size = "medium"
            device = "cpu"
            compute_type = "default"
            batch_size = 16
            print("使用默认配置: medium/CPU/default")

    # 如果没有通过硬件检测获取 batch_size，使用默认值
    if 'batch_size' not in locals():
        batch_size = 16

    print("=" * 60)
    print(f"正在加载 Whisper 模型 ({model_size})...")
    print(f"设备: {device} | 计算类型: {compute_type}")
    print("=" * 60 + "\n")

    # 初始化模型
    model = WhisperModel(
        model_size,
        device=device,
        compute_type=compute_type
    )

    print(f"\n正在处理文件: {media_file.name}")
    print("这可能需要几分钟，请耐心等待...\n")

    # 转写视频
    segments, info = model.transcribe(
        str(media_file),
        language="zh",  # 指定中文
        task="transcribe",
        word_timestamps=True,  # 获取词级时间戳
        vad_filter=True,  # 使用 VAD 过滤静音
    )

    # 获取检测到的语言
    detected_language = info.language
    language_probability = info.language_probability

    print(f"检测到语言: {detected_language} (置信度: {language_probability:.2%})")
    print("=" * 60)
    print("\n正在识别语音（实时进度）：\n")

    # 收集所有分段，并显示进度
    all_segments = []
    segment_count = 0
    last_time = 0

    for segment in segments:
        all_segments.append(segment)
        segment_count += 1

        # 显示进度（每10个segment或时间推进超过5秒）
        current_progress = ""
        if segment.end > last_time + 5 or segment_count % 10 == 0:
            current_time = format_timestamp(segment.end)
            print(f"  进度: [{current_time}] 已识别 {segment_count} 个片段...")
            last_time = segment.end

    print(f"\n✓ 共识别出 {len(all_segments)} 个语音片段\n")

    # 生成 Markdown 格式输出
    md_content = f"""# {media_file.stem} - 逐字稿

**文件名**: {media_file.name}
**识别语言**: {detected_language}
**片段数量**: {len(all_segments)}

---

## 完整逐字稿（带时间戳）

"""

    # 添加带时间戳的逐字稿
    for i, segment in enumerate(all_segments, 1):
        start_time = format_timestamp(segment.start)
        end_time = format_timestamp(segment.end)
        text = segment.text.strip()

        md_content += f"### [{i:03d}] {start_time} - {end_time}\n\n{text}\n\n"

    # 添加纯文本版本（方便复制）
    md_content += "\n---\n\n## 纯文本版（方便复制）\n\n"

    full_text = "".join([segment.text.strip() for segment in all_segments])
    md_content += full_text

    # 保存到文件
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"✓ 逐字稿已保存到: {output_path}")
    print(f"✓ 共 {len(all_segments)} 个片段")
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
        print(f"错误: {e}")
        sys.exit(1)
