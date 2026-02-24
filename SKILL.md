---
name: video-audio-summary
description: 本地视频/音频语音转文字与结构化总结。当用户需要提取本地视频/音频文件的逐字稿，或对长音频/视频内容进行结构化总结时使用此技能。使用 Qwen3-ASR 进行本地语音识别，数据完全本地处理，无需云端服务。支持高精度中文识别、自动标点还原和中英混合识别。
---

# 视频/音频本地总结

## 概述

此技能提供完整的本地视频/音频处理工作流：从语音转文字（ASR）到结构化内容总结。使用 Qwen3-ASR 进行本地语音识别，确保数据隐私安全。

**核心优势：**
- **SOTA 级别中文识别精度**：Qwen3-ASR 在中文语音识别上表现优异
- **自动标点还原**：无需后处理，直接输出带标点的文本
- **超快处理速度**：相比 Whisper，吞吐量提升约 2000 倍
- **中英混合支持**：自动识别语言切换，无缝处理混合内容
- **方言支持**：对多种中文方言有更好的识别效果
- **官方 qwen-asr 包**：使用官方封装的 API，简单易用

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
- Python 3.8+（推荐 3.12）
- ffmpeg（视频处理必需）
- qwen-asr 包

**⚠️ 重要：环境准备**

#### Mac 用户（推荐使用 Conda）

```bash
# 创建并激活环境
conda create -n qwen3-asr python=3.12 -y
conda activate qwen3-asr

# 安装 qwen-asr（官方包，自动安装所需依赖）
pip install -U qwen-asr

# 模型会在首次使用时自动下载，也可提前下载
modelscope download --model Qwen/Qwen3-ASR-1.7B --local_dir ./Qwen3-ASR-1.7B
```

#### Linux/Windows 用户

```bash
# 创建虚拟环境
python3 -m venv qwen3-asr-env
source qwen3-asr-env/bin/activate  # Linux/Mac
# 或
qwen3-asr-env\Scripts\activate  # Windows

# 安装 qwen-asr
pip install -U qwen-asr
```

**模型大小：**
- **Qwen3-ASR-1.7B**：约 3.5GB，高精度，推荐使用
- **Qwen3-ASR-0.6B**：约 1.2GB，轻量级，适合低配设备

**模型缓存位置：**
- ModelScope 默认：`~/.cache/modelscope/hub/`
- 手动下载：指定的 `--local_dir` 目录

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

3. 检查 qwen-asr：
```bash
pip show qwen-asr
```

---

### 步骤 3：提取逐字稿

使用 Qwen3-ASR 提取语音转文字。

**脚本位置：**
```
scripts/extract_transcript.py
```

**使用方法：**
```bash
# 激活环境
conda activate qwen3-asr  # Mac
# 或
source qwen3-asr-env/bin/activate  # Linux

# 提取逐字稿（脚本会自动选择最优配置）
python scripts/extract_transcript.py "<视频/音频文件路径>" [输出目录]
```

**参数说明：**
- 第一个参数：视频/音频文件的完整路径
- 第二个参数（可选）：输出目录，默认为文件所在目录

**输出文件：**
- 文件名：`{原文件名}_逐字稿.md`
- 内容结构：
  - 文件元信息（文件名、模型、设备、识别语言）
  - 完整逐字稿（带时间戳，如有）
  - 自动标点还原

**模型选择与设备优化（自动检测）：**

脚本会自动检测硬件并选择最优配置：

| 硬件配置 | 推荐模型 | 设备 | 数据类型 | 预期加速 |
|---------|---------|------|----------|----------|
| NVIDIA GPU (显存 ≥ 8GB) | Qwen3-ASR-1.7B | cuda | bfloat16 | 10-20x |
| Apple Silicon (M1/M2/M3/M5) | Qwen3-ASR-1.7B | mps | bfloat16 | 3-5x |
| 高配 CPU (16GB+ RAM, 8+ 核) | Qwen3-ASR-1.7B | cpu | float32 | 1.5-2x |
| 标准 CPU (8GB+ RAM) | Qwen3-ASR-1.7B | cpu | float32 | 1.5x |
| 低配 CPU | Qwen3-ASR-0.6B | cpu | float32 | 基准 |

**手动指定配置（可选）：**
```bash
# 强制指定模型
export QWEN_ASR_MODEL=Qwen/Qwen3-ASR-1.7B  # 或 Qwen/Qwen3-ASR-0.6B

# 强制指定设备
export QWEN_ASR_DEVICE=cuda  # 或 cpu/mps

# 强制指定数据类型
export QWEN_ASR_DTYPE=float16  # 或 bfloat16/float32

# 指定本地模型路径（优先级最高）
export QWEN_ASR_MODEL_PATH=/path/to/local/model

python scripts/extract_transcript.py "video.mp4"
```

**预期处理时间：**
- NVIDIA GPU：约 1 小时音频 → 1-3 分钟
- Apple Silicon (MPS)：约 1 小时音频 → 10-15 分钟
- Apple Silicon (CPU)：约 1 小时音频 → 20-30 分钟
- 高配 CPU：约 1 小时音频 → 30-40 分钟

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

**extract_transcript.py** - 逐字稿提取脚本
- 功能：使用 Qwen3-ASR 将视频/音频转为带时间戳的逐字稿
- 输入：视频/音频文件路径
- 输出：Markdown 格式的逐字稿文件
- 依赖：qwen-asr（自动安装 torch, torchaudio 等）
- 特性：自动检测硬件配置并选择最优模型和设备

**detect_hardware.py** - 硬件检测模块
- 功能：自动检测 CPU、GPU、内存等硬件信息
- 支持平台：Windows、macOS、Linux
- 检测内容：
  - 操作系统和架构
  - CPU 核心数和类型
  - 系统内存大小
  - GPU 信息（NVIDIA、AMD、Apple Silicon）
- 推荐配置：
  - 最优模型（1.7B / 0.6B）
  - 最优设备类型（cpu/cuda/mps）
  - 最优数据类型（float16/float32）

**check_environment.sh** - 环境检查脚本
- 功能：检查并准备运行环境
- 检查项：Python, pip, ffmpeg, 虚拟环境, qwen-asr
- 自动创建虚拟环境和安装依赖

### references/

此技能当前不需要额外参考文档。

### assets/

此技能当前不需要额外资源文件。

---

## 常见问题

**Q: 脚本会自动选择最优配置吗？**
A: 是的！脚本会自动检测您的硬件配置（CPU、GPU、内存）并选择最优方案：
- **NVIDIA GPU** → 使用 Qwen3-ASR-1.7B + CUDA（最快）
- **Apple Silicon** → 使用 Qwen3-ASR-1.7B + MPS（比 CPU 快 3-5 倍）
- **高配 CPU** → 使用 Qwen3-ASR-1.7B + CPU
- **标准/低配 CPU** → 使用 Qwen3-ASR-0.6B + CPU

**Q: 如何手动指定模型或设备？**
A: 使用环境变量覆盖自动检测：
```bash
export QWEN_ASR_MODEL=Qwen/Qwen3-ASR-1.7B
export QWEN_ASR_DEVICE=cuda  # 或 cpu/mps
export QWEN_ASR_DTYPE=float16  # 或 bfloat16/float32
python scripts/extract_transcript.py "video.mp4"
```

**Q: pip 安装时网络超时（ReadTimeoutError）怎么办？**
A: `torch` 包体积约 80-500MB，直连 PyPI 官方源在国内经常超时。按以下顺序尝试镜像：

```bash
# 方案1：使用 check_environment.sh（已内置阿里云镜像，默认推荐）
bash scripts/check_environment.sh

# 方案2：手动指定镜像安装（阿里云最稳定）
pip install torch torchaudio -i https://mirrors.aliyun.com/pypi/simple/ --timeout 300
pip install qwen-asr -i https://mirrors.aliyun.com/pypi/simple/ --timeout 300

# 方案3：切换到其他镜像
PIP_MIRROR=https://pypi.tuna.tsinghua.edu.cn/simple  # 清华
PIP_MIRROR=https://mirrors.cloud.tencent.com/pypi/simple  # 腾讯云
```

> **关键经验**：先单独安装 `torch torchaudio`（大包），再安装 `qwen-asr`（小包），比一次性安装超时风险更低。

**Q: 处理速度还是很慢怎么办？**
A:
1. 检查是否有 NVIDIA GPU（安装 CUDA Toolkit）
2. 如果是 Apple Silicon，确保使用最新版本的 qwen-asr（支持 MPS）
3. 考虑使用 0.6B 模型：`export QWEN_ASR_MODEL=Qwen/Qwen3-ASR-0.6B`

**Q: 中文识别效果不好？**
A:
- Qwen3-ASR 针对中文优化，识别效果通常优于 Whisper
- 确保音频质量清晰
- 模型已自动处理标点还原，无需额外配置

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

**Q: Qwen3-ASR 有什么优势？**
A: 相比 Whisper：
- **中文精度更高**：专门针对中文优化
- **自动标点还原**：输出结果直接带标点
- **速度更快**：吞吐量提升约 2000 倍
- **中英混合**：自动识别语言切换
- **方言支持**：对多种中文方言支持更好
- **官方封装**：提供简单易用的 `qwen-asr` 包

---

## 快速开始示例

### Mac (M1/M2/M3/M5) 用户

```bash
# 1. 创建环境
conda create -n qwen3-asr python=3.12 -y
conda activate qwen3-asr

# 2. 安装 qwen-asr
pip install -U qwen-asr

# 3. （可选）检测硬件并查看推荐配置
python scripts/detect_hardware.py

# 4. 提取逐字稿（脚本会自动选择 MPS 加速）
python scripts/extract_transcript.py "/path/to/video.mp4"

# 5. 查看逐字稿
open "/path/to/video_逐字稿.md"
```

### Linux/Windows 用户

```bash
# 1. 创建虚拟环境
python3 -m venv qwen3-asr-env
source qwen3-asr-env/bin/activate  # Linux
# 或 qwen3-asr-env\Scripts\activate  # Windows

# 2. 安装 qwen-asr
pip install -U qwen-asr

# 3. 提取逐字稿
python scripts/extract_transcript.py "/path/to/video.mp4"
```

**高级用法**：手动指定配置
```bash
# 强制使用特定模型或设备
export QWEN_ASR_MODEL=Qwen/Qwen3-ASR-1.7B
export QWEN_ASR_DEVICE=cuda  # 如果有 NVIDIA GPU
export QWEN_ASR_DTYPE=float16
python scripts/extract_transcript.py "/path/to/video.mp4"
```

---

## 环境清理

如果之前使用过 faster-whisper，可以清理旧环境释放空间：

```bash
# 删除旧的虚拟环境
rm -rf ~/Downloads/whisper-env

# 删除 Hugging Face 缓存的 Whisper 模型（约 1.4GB）
rm -rf ~/.cache/huggingface/hub/models--Systran--faster-whisper-*
rm -rf ~/.cache/huggingface/hub/.locks/models--Systran--faster-whisper-*
```

**总计可释放约 2GB 空间**

---

## 官方 qwen-asr API 参考

### 快速推理示例

```python
import torch
from qwen_asr import Qwen3ASRModel

# 创建模型
model = Qwen3ASRModel.from_pretrained(
    "Qwen/Qwen3-ASR-1.7B",
    dtype=torch.bfloat16,   # 官方推荐 bfloat16，模型权重格式为 BF16
    device_map="mps",       # Mac 使用 "mps"，NVIDIA 使用 "cuda:0"，CPU 不传此参数
    max_inference_batch_size=8,
    max_new_tokens=256,
)

# 执行识别
results = model.transcribe(
    audio="your_audio_file.wav",
    language=None,  # 自动检测语言
)

# 获取结果
print(f"识别语言: {results[0].language}")
print(f"识别文本: {results[0].text}")
```

### 带时间戳的批量推理

```python
import torch
from qwen_asr import Qwen3ASRModel

model = Qwen3ASRModel.from_pretrained(
    "Qwen/Qwen3-ASR-1.7B",
    dtype=torch.bfloat16,
    device_map="cuda:0",
    forced_aligner="Qwen/Qwen3-ForcedAligner-0.6B",  # 启用时间戳
    forced_aligner_kwargs=dict(
        dtype=torch.bfloat16,
        device_map="cuda:0",
    ),
)

results = model.transcribe(
    audio=["audio1.wav", "audio2.wav"],
    language=None,
    return_time_stamps=True,
)

for r in results:
    print(r.language, r.text, r.time_stamps[0])
```
