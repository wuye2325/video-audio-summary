---
name: video-audio-summary
description: 本地视频/音频语音转文字与结构化总结。当用户需要提取本地视频/音频文件的逐字稿，或对长音频/视频内容进行结构化总结时使用此技能。支持中文语音识别，数据完全本地处理，无需云端服务。
---

# 视频/音频本地总结

## 概述

此技能提供完整的本地视频/音频处理工作流：从语音转文字（ASR）到结构化内容总结。使用 faster-whisper 进行本地语音识别，确保数据隐私安全。

**使用场景：**
- 提取本地视频/音频的逐字稿
- 对会议录音、访谈、直播等内容进行结构化总结
- 需要数据本地处理，不使用云端服务的场景

---

## 工作流程

### 步骤 1：明确要处理的文件

首先确认用户提供的文件路径和类型。

**支持格式：**
- 视频：MP4, MOV, AVI, MKV, FLV, WMV
- 音频：MP3, WAV, M4A, FLAC, AAC, OGG

**确认文件存在：**
```bash
ls -la "<文件路径>"
```

**获取文件基本信息：**
```bash
ffmpeg -i "<文件路径>" 2>&1 | grep -E "Duration|Audio|Video"
```

---

### 步骤 2：检查并准备环境

检查系统环境是否满足要求。

**环境要求：**
- Python 3.8+
- ffmpeg（视频处理必需）
- faster-whisper 库

**⚠️ 重要：模型下载加速**

首次运行时需要下载 Whisper 模型（约 1.5GB），**强烈建议使用国内镜像**加速下载：

```bash
# 设置 Hugging Face 镜像（中国大陆用户推荐）
export HF_ENDPOINT=https://hf-mirror.com
```

此环境变量需要在每次运行脚本前设置，或添加到 shell 配置文件（`~/.zshrc` 或 `~/.bashrc`）中永久生效。

**模型缓存位置：**
- 默认路径：`~/.cache/huggingface/hub/`
- 模型文件：`models--Systran--faster-whisper-medium/`

**环境检查脚本位置：**
```
scripts/check_environment.sh
```

**手动检查命令：**

1. 检查 Python：
```bash
python3 --version
```

2. 检查 ffmpeg：
```bash
ffmpeg -version
```

3. 检查虚拟环境（默认路径 `~/Downloads/whisper-env`）：
```bash
ls -la ~/Downloads/whisper-env/
```

4. 检查 faster-whisper：
```bash
source ~/Downloads/whisper-env/bin/activate
pip show faster-whisper
```

**环境准备（如未完成）：**

```bash
# 1. 设置模型下载镜像（中国大陆用户推荐）
export HF_ENDPOINT=https://hf-mirror.com

# 2. 创建虚拟环境并安装依赖
python3 -m venv ~/Downloads/whisper-env
source ~/Downloads/whisper-env/bin/activate
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple faster-whisper
```

---

### 步骤 3：提取逐字稿

使用 faster-whisper 提取语音转文字。

**脚本位置：**
```
scripts/extract_transcript.py
```

**使用方法：**
```bash
source ~/Downloads/whisper-env/bin/activate
python scripts/extract_transcript.py "<视频/音频文件路径>" [输出目录]
```

**参数说明：**
- 第一个参数：视频/音频文件的完整路径
- 第二个参数（可选）：输出目录，默认为文件所在目录

**输出文件：**
- 文件名：`{原文件名}_逐字稿.md`
- 内容结构：
  - 文件元信息（文件名、识别语言、片段数量）
  - 完整逐字稿（带时间戳 HH:MM:SS）
  - 纯文本版（方便复制）

**模型选择：**
- **自动优化**（推荐）：脚本会自动检测硬件并选择最优配置
  - NVIDIA GPU：使用 large-v3-turbo + CUDA（最快，10-20x 加速）
  - Apple Silicon：使用 large-v3-turbo + CPU（2-3x 加速）
  - 高配 CPU：使用 large-v3-turbo + int8 量化（2-3x 加速）
  - 标准配置：使用 medium + int8 量化（1.5-2x 加速）
  - 低配设备：使用 small 模型（确保稳定性）

**手动指定配置（可选）：**
```bash
# 强制指定模型
export WHISPER_MODEL=large-v3-turbo

# 强制指定设备
export WHISPER_DEVICE=cuda  # 或 cpu

# 强制指定计算类型
export WHISPER_COMPUTE_TYPE=float16  # 或 float32/int8/default
```

**预期处理时间：**
- NVIDIA GPU：约 1 小时音频 → 2-5 分钟
- Apple Silicon (turbo)：约 1 小时音频 → 30-40 分钟
- 高配 CPU (turbo+int8)：约 1 小时音频 → 30-40 分钟
- 标准配置 (medium+int8)：约 1 小时音频 → 50-60 分钟

---

### 步骤 4：结构化总结

对逐字稿进行结构化分析和总结。

**当逐字稿文件较大（>20000 tokens）时：**

使用 general-purpose agent 进行分析：
```
请分析文件 `<逐字稿文件路径>`，这是关于"<主题>"的对话/演讲逐字稿。

请完成以下任务：
1. 识别参与者/演讲者
2. 提取核心主题（3-6个）
3. 结构化总结：
   - 概述（时间、参与者、主题）
   - 主要讨论内容（分主题）
   - 核心观点和见解
   - 实践建议或操作方法
   - 关键金句

将总结保存为 Markdown 文件到 `<输出文件路径>`
```

**当逐字稿较小时：**

直接分析文件内容并生成结构化总结，包含以下部分：

1. **概述**
   - 文件信息
   - 参与者/演讲者
   - 时长/字数

2. **核心主题**（3-6个）
   - 主题标题
   - 详细内容说明

3. **核心观点**
   - 按参与者/演讲者分类
   - 列出主要观点

4. **实践建议**
   - 可操作的具体建议
   - 实施方法

5. **关键金句**
   - 摘录 10-30 条精彩观点
   - 保留原始表述

6. **总结与展望**
   - 主要共识
   - 行动计划
   - 应用场景

**输出文件：**
- 文件名：`{原文件名}_结构化总结.md`

---

## 资源说明

### scripts/

**extract_transcript.py** - 逐字稿提取脚本（已升级，支持硬件自动检测）
- 功能：使用 faster-whisper 将视频/音频转为带时间戳的逐字稿
- 输入：视频/音频文件路径
- 输出：Markdown 格式的逐字稿文件
- 依赖：faster-whisper, ffmpeg
- **新特性**：自动检测硬件配置并选择最优模型和参数

**detect_hardware.py** - 硬件检测模块
- 功能：自动检测 CPU、GPU、内存等硬件信息
- 支持平台：Windows、macOS、Linux
- 检测内容：
  - 操作系统和架构
  - CPU 核心数和类型
  - 系统内存大小
  - GPU 信息（NVIDIA、AMD、Apple Silicon）
- 推荐配置：
  - 最优模型大小（small/medium/large-v3-turbo）
  - 最优设备类型（cpu/cuda/mps）
  - 最优计算类型（float32/float16/int8）
  - 最优批处理大小

**check_environment.sh** - 环境检查脚本
- 功能：检查并准备运行环境
- 检查项：Python, pip, ffmpeg, 虚拟环境, faster-whisper
- 自动创建虚拟环境和安装依赖

### references/

此技能当前不需要额外参考文档。

### assets/

此技能当前不需要额外资源文件。

---

## 常见问题

**Q: 脚本会自动选择最优配置吗？**
A: 是的！脚本会自动检测您的硬件配置（CPU、GPU、内存）并选择最优方案：
- **NVIDIA GPU** → 使用 large-v3-turbo + CUDA（最快）
- **Apple Silicon** → 使用 large-v3-turbo + CPU（比 medium 快 2-3 倍）
- **高配 CPU** → 使用 large-v3-turbo + int8 量化
- **标准配置** → 使用 medium + int8 量化
- **低配设备** → 使用 small 模型

**Q: 如何手动指定模型或设备？**
A: 使用环境变量覆盖自动检测：
```bash
export WHISPER_MODEL=large-v3-turbo
export WHISPER_DEVICE=cuda
export WHISPER_COMPUTE_TYPE=float16
python scripts/extract_transcript.py "video.mp4"
```

**Q: 处理速度还是很慢怎么办？**
A:
1. 检查是否有 NVIDIA GPU（安装 CUDA Toolkit）
2. 如果是 Apple Silicon，确保使用最新版本的 faster-whisper
3. 尝试使用 int8 量化：`export WHISPER_COMPUTE_TYPE=int8`
4. 考虑使用 smaller 模型：`export WHISPER_MODEL=small`

**Q: 中文识别效果不好？**
A:
- 脚本已默认使用 medium 或 large-v3-turbo 模型（中文效果好）
- 确保音频质量清晰
- 已启用 VAD 过滤（vad_filter=True）

**Q: 视频文件太大怎么办？**
A: 可以先用 ffmpeg 提取音频：
```bash
ffmpeg -i input.mp4 -vn -acodec copy output.m4a
```

**Q: 如何查看我的硬件检测结果？**
A: 运行硬件检测脚本：
```bash
python scripts/detect_hardware.py
```

**Q: large-v3-turbo 模型是什么？**
A: OpenAI 2024年发布的最新 Whisper 模型，相比 medium/large-v3：
- 速度：比 medium 快 2-4 倍，比 large-v3 快 8 倍
- 质量：与 large-v3 相当，优于 medium
- 大小：809M（介于 medium 的 769M 和 large 的 1550M 之间）

---

## 快速开始示例

```bash
# 1. 设置模型下载镜像（中国大陆用户推荐，首次运行必需）
export HF_ENDPOINT=https://hf-mirror.com

# 2. 检查环境
bash scripts/check_environment.sh

# 3. （可选）检测硬件并查看推荐配置
source ~/Downloads/whisper-env/bin/activate
python scripts/detect_hardware.py

# 4. 提取逐字稿（脚本会自动选择最优配置）
python scripts/extract_transcript.py "/path/to/video.mp4"

# 5. 查看逐字稿
open "/path/to/video_逐字稿.md"
```

**提示**：将镜像设置添加到 shell 配置文件可永久生效：
```bash
# 添加到 ~/.zshrc 或 ~/.bashrc
echo 'export HF_ENDPOINT=https://hf-mirror.com' >> ~/.zshrc
source ~/.zshrc
```

**高级用法**：手动指定配置
```bash
# 强制使用特定模型或设备
export WHISPER_MODEL=large-v3-turbo
export WHISPER_DEVICE=cuda  # 如果有 NVIDIA GPU
export WHISPER_COMPUTE_TYPE=float16
python scripts/extract_transcript.py "/path/to/video.mp4"
```
