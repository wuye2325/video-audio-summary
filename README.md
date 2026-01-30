# Video-Audio-Summary

这是一个基于 `faster-whisper` 的本地音视频语音转文字与结构化总结工具。

## 🌟 核心特性

- **数据隐私安全**：所有处理完全在本地完成，无需上传云端，保护您的会议、访谈隐私。
- **硬件自动优化**：智能检测系统硬件（CPU, GPU, Apple Silicon），自动选择最优模型和计算参数。
- **高性能识别**：
  - 支持 **NVIDIA GPU (CUDA)**：1小时视频约 2-5 分钟处理完成。
  - 支持 **Apple Silicon (M系列芯片)**：利用 CoreML 加速，性能卓越。
- **结构化深度总结**：不仅提供带时间戳的逐字稿，还能自动提取核心主题、观点、金句及 Todo 清单。

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
pip install faster-whisper
```

### 2. 运行环境检查

```bash
bash scripts/check_environment.sh
```

### 3. 提取逐字稿

```bash
# 脚本会自动检测硬件并选择最优模型（默认使用 large-v3-turbo）
python scripts/extract_transcript.py "/path/to/your/video.mp4"
```

## 🛠️ 脚本说明

- `scripts/extract_transcript.py`: 核心脚本，负责音视频转文字。
- `scripts/detect_hardware.py`: 硬件检测模块，提供优化建议。
- `scripts/check_environment.sh`: 快速检查运行环境。

## 💡 使用建议

- **国内用户**：建议设置 `export HF_ENDPOINT=https://hf-mirror.com` 以加速模型下载。
- **模型选择**：默认使用 `large-v3-turbo`，在速度与准确率之间取得了完美平衡。

## 📄 开源协议

MIT
