# 满分会议纪要系统

> 基于 Qwen3-ASR 的本地音视频转写 + AI 会议纪要生成工具
> 按方法论标准：5分转写 → 8分原话节选 → 9分历史对比洞察

---

## 核心特性

| 特性 | 说明 |
|------|------|
| **本地处理** | 数据完全本地，无云端上传，保护隐私 |
| **Qwen3-ASR 转写** | SOTA 中文识别，自动标点，中英混合支持 |
| **说话人分离** | 本地替代方案（energy+cluster），不依赖 HF gated 模型 |
| **结构化纪要** | 按议题分段 + 原话摘录（防幻觉） + 行动项提取 |
| **历史对比** | 关联往期会议，识别延续话题、决策变更、待办闭环 |
| **两种模式** | 完整流程（从音频）或仅生成纪要（已有逐字稿） |

---

## 快速开始

### 完整流程（从音频开始）

```bash
# 1. 环境检查（首次）
bash scripts/check_environment.sh

# 2. 运行主脚本
python scripts/meeting-summarize-v2.py --audio "/path/to/audio.mp3"

# 3. 输出位置
#    逐字稿：output/{音频名}-逐字稿.md
#    原始数据：output/{音频名}.raw.json
```

### 仅生成纪要（已有逐字稿）

直接向 Agent 提供逐字稿文件，说"帮我生成会议纪要"。

---

## 文件结构

```
video-audio-summary/
├── SKILL.md              # 核心工作流（主要文档）
├── TROUBLESHOOTING.md    # 常见问题 FAQ
├── references/           # 参考文档
│   ├── meeting-template.md   # 会议纪要模板
│   ├── test-baseline.md      # 测试基线记录
│   └── qwen-asr-api.md       # Qwen3-ASR API 参考
├── scripts/              # 核心脚本
│   ├── meeting-summarize-v2.py   # 主脚本
│   ├── extract_transcript_resumable.py  # ASR 转写
│   ├── check_environment.sh     # 环境检查
│   └── meeting-indexer.py       # 历史索引
├── output/               # 输出目录
└── .venv-qwen-asr/       # 虚拟环境
```

---

## 详细文档

- **工作流程**：见 `SKILL.md`
- **故障排除**：见 `TROUBLESHOOTING.md`
- **纪要模板**：见 `references/meeting-template.md`

---

## 环境要求

| 依赖 | 说明 |
|------|------|
| ffmpeg | 音视频处理 |
| Python 3.10+ | qwen-asr 要求 |
| Qwen3-ASR-1.7B | 本地模型（约 3.5GB） |

---

## 纪要质量标准

按"满分会议纪要方法论"：

| 分数 | 标准 | 本技能实现 |
|------|------|------------|
| 5分 | 基础转写 | ✅ Qwen3-ASR |
| 6-7分 | 结构化分段 | ✅ 按议题分段 |
| 8分 | 原话节选 | ✅ 每议题配原文引用 |
| 9分 | 历史对比 | ✅ 关联往期会议 |

---

## 开源协议

MIT