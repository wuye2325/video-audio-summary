# Video-Audio-Summary

这是一个基于 `Qwen3-ASR` 的本地音视频语音转文字与结构化总结工具。

## 🌟 核心特性

- **数据隐私安全**：所有处理完全在本地完成，无需上传云端，保护您的会议、访谈隐私。
- **硬件自动优化**：智能检测系统硬件（CPU, GPU, Apple Silicon），自动选择最优模型和计算参数。
- **SOTA 级别中文识别**：Qwen3-ASR 在中文语音识别上表现优异，支持自动标点还原。
- **高处理速度**：相比 Whisper，吞吐量提升约 2000 倍。
- **中英混合支持**：自动识别语言切换，无缝处理混合内容。
- **高性能识别**：
  - 支持 **NVIDIA GPU (CUDA)**：1小时视频约 1-3 分钟处理完成。
  - 支持 **Apple Silicon (M系列芯片)**：支持 MPS 加速，性能卓越。

## 🚀 快速开始

### 1. 环境准备

确保您的系统已安装 `ffmpeg`。

```bash
# 克隆仓库
git clone https://github.com/YOUR_USERNAME/video-audio-summary.git
cd video-audio-summary

# 创建并激活虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install modelscope torch torchaudio soundfile pyyaml psutil
```

### 2. 运行环境检查

```bash
bash scripts/check_environment.sh
```

### 3. 提取逐字稿

```bash
# 脚本会自动检测硬件并选择最优模型（默认使用 Qwen3-ASR-1.7B）
python scripts/extract_transcript.py "/path/to/your/video.mp4"
```

## 🛠️ 脚本说明

- `scripts/extract_transcript.py`: 核心脚本，负责音视频转文字。
- `scripts/detect_hardware.py`: 硬件检测模块，提供优化建议。
- `scripts/check_environment.sh`: 快速检查运行环境。

## 💡 使用建议

- **模型选择**：
  - **Qwen3-ASR-1.7B**：高精度模型，约 3.5GB，推荐使用
  - **Qwen3-ASR-0.6B**：轻量级模型，约 1.2GB，适合低配设备
- **环境变量**（可选）：
  ```bash
  export QWEN_ASR_MODEL=Qwen/Qwen3-ASR-1.7B
  export QWEN_ASR_DEVICE=cuda  # 或 cpu/mps
  ```

## 📄 开源协议

MIT
