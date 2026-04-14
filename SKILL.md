---
name: video-audio-summary
description: "满分会议纪要系统。会议录音 → 结构化纪要 + 历史对比洞察。支持 Qwen3-ASR 本地高精度转写、本地替代说话人分离（不依赖 HF gated 模型）、声纹实名匹配、按议题分段、原话引用提取、历史会议对比分析。"
version: 3.0.0
tags:
  - meeting
  - asr
  - speaker-diarization
  - voiceprint
  - summary
  - transcription
  - qwen-asr
  - local-diarization
  - historical-insights
---

# 满分会议纪要系统

把会议录音处理成**逐字稿 + raw 结构化数据**，再由 Agent 生成可交付会议纪要，并可自动关联历史会议给出洞察。

**触发条件**：用户发送录音文件（mp3/wav/ogg/opus/m4a/flac）、说"总结会议/会议纪要/帮我总结录音"、说"注册声纹/记住我的声音"、要求"对比上次会议"、"看看有什么新进展"。

**依赖**：ffmpeg、Python 3.9+、Qwen3-ASR 模型（~3.5GB）。说话人分离使用本地替代方案，不依赖 HuggingFace gated 权限。

---

## 核心特性

| 特性 | 说明 |
|------|------|
| **Qwen3-ASR 本地转写** | SOTA 级中文识别，自动标点，中英混合支持，数据完全本地 |
| **本地说话人分离（替代）** | 基于 energy+cluster 的本地多说话人分段，不依赖 gated 模型 |
| **声纹实名匹配** | 注册声纹后自动识别说话人身份 |
| **按议题分段** | LLM 智能识别议题边界，生成结构化讨论段落 |
| **原话引用提取** | 自动识别关键决策、承诺、争议点的原文摘录 |
| **历史对比洞察** | 与历史会议对比，识别延续话题、新进展、待办闭环 |

---

## 路由与执行方式

- **模型**：优先使用高推理模型处理纪要生成与质量检查
- **执行方式**：默认在当前会话直接执行；仅当用户明确要求并行/委派时才使用 subagent
- **最小输入**：音频路径 + 输出路径（历史洞察和 speaker map 为可选）

---

## ⚡ 快速参考：两种使用方式

| 方式 | 场景 | 触发条件 |
|------|------|----------|
| **完整流程** | 从音频开始，需要转写 | 用户发送音频文件或说"总结会议/会议纪要" |
| **仅生成纪要** | 已有逐字稿，只需总结 | 用户说"已有逐字稿"、"直接总结"并附带文本，或使用 `--from-transcript` |

### 完整流程（从音频开始）

```
步骤 0：确认输入参数（音频路径、输出目录）
步骤 1：初始化与环境检查
步骤 2：跑主脚本（产出逐字稿 + raw）
步骤 3：检查输出 + 质量闸门
步骤 4：说话人确认 → 替换逐字稿人名
步骤 5：Agent 生成会议纪要
```

### 仅生成纪要（已有逐字稿）

```
步骤 1：读取用户提供的逐字稿
步骤 2：询问说话人身份（若有 SPEAKER_XX 等代号）
步骤 3：替换人名或根据上下文推测角色
步骤 4：Agent 生成会议纪要
```

---

### 完整流程详细步骤

### 步骤 1：初始化与环境检查（首次安装）

```bash
# 在 skill 目录执行（只需首次）
cd {baseDir}
bash scripts/check_environment.sh
```

可选环境变量：
- `QWEN_ASR_PYTHON`：指定带 `qwen_asr` 依赖的 Python（如 `~/qwen3-asr-env/bin/python`）
- `QWEN_ASR_VENV`：指定虚拟环境目录（脚本自动使用 `${QWEN_ASR_VENV}/bin/python`）
- `QWEN_ASR_MODEL_PATH`：指定本地模型目录（含 `config.json`）
- `QWEN_ASR_MODEL`：远端模型名（未设置本地路径时可用）

### 步骤 1.5：运行前快速检查

```bash
# 检查 ffmpeg
which ffmpeg

# 检查 Qwen3-ASR Python（任选其一）
test -x "${QWEN_ASR_PYTHON:-}" && echo "QWEN_ASR_PYTHON就绪" || echo "QWEN_ASR_PYTHON未设置（将自动探测）"
test -x "${QWEN_ASR_VENV:-}/bin/python" && echo "QWEN_ASR_VENV就绪" || echo "QWEN_ASR_VENV未设置（将自动探测）"

# 检查本地模型（可选；也可只设 QWEN_ASR_MODEL）
test -f "${QWEN_ASR_MODEL_PATH:-}/config.json" && echo "本地模型就绪" || echo "本地模型未设置（将自动探测或走 QWEN_ASR_MODEL）"

# 说话人分离无需 pyannote/HF 权限（本地替代方案）
echo "local diarization ready"
```

**禁止事项**：
- ❌ 不要在未确认前改动生产环境配置
- ❌ 不要把失败结果当成功交付

### 步骤 2：跑主脚本

```bash
cd {baseDir} && \
PYTHONUNBUFFERED=1 \
python scripts/meeting-summarize-v2.py \
  --audio "/path/to/recording.m4a" \
  --transcript-out "/path/to/transcript.md" \
  --raw-out "/path/to/transcript.raw.json"
```

**可选参数**：
- `--num-speakers N`：已知参会人数
- `--speaker-map /path/to/map.json`：已知人名映射
- `--with-history-insight`：启用历史对比洞察
- `--history-meeting-date YYYY-MM-DD`：指定对比的历史会议日期

### 步骤 3：检查输出

```bash
# 检查生成的逐字稿（独立文件）
head -120 /path/to/transcript.md

# 检查 raw 文件（供 Agent 生成会议纪要）
python3 -m json.tool /path/to/transcript.raw.json | head -120
```

### 步骤 3.5：质量闸门（必须通过）

只要出现以下任一情况，视为失败，不可进入步骤 5：
- 日志出现“转写完成，共 0 段”
- `transcript.md` 为空或仅有标题
- `transcript.raw.json` 缺失 `segments/topics/actions`
- 说话人分离失败且结果退化为全 `Unknown`

```bash
# 1) 快速扫描失败信号（以 run.log 为例）
rg -n "转写完成，共 0 段|说话人分离失败|错误|Traceback" /tmp/run.log

# 2) 逐字稿必须有正文
wc -l /path/to/transcript.md
sed -n '1,80p' /path/to/transcript.md

# 3) raw 必须有关键字段
python3 - <<'PY'
import json
p="/path/to/transcript.raw.json"
d=json.load(open(p,"r",encoding="utf-8"))
for k in ("segments","topics","actions"):
    v=d.get(k)
    print(f"{k}: {'OK' if isinstance(v,list) else 'MISSING'} len={len(v) if isinstance(v,list) else 'n/a'}")
PY
```

失败处理原则：
1. 不做规则版降级纪要。
2. 直接定位根因并修复后重跑（环境、模型、音频质量、解析逻辑）。
3. 仅在质量闸门通过后，Agent 才进入步骤 5 生成会议纪要。

### 步骤 4：说话人确认 → 替换逐字稿人名

**规则**：如果检测到 ≥2 个有效说话人，必须先问用户确认身份，**然后替换逐字稿中的代号**。

**询问模板**：
```
检测到 X 位说话人：
- SPEAKER_01（YY 段发言）
- SPEAKER_02（ZZ 段发言）

请告诉我每位说话人对应谁？（如：SPEAKER_01 是莆主任，SPEAKER_02 是吴晔）
若不确定或不想提供，可直接回复"不确定"，Agent 将根据上下文语义推测。
```

**两种处理路径**：

| 用户响应 | 处理方式 |
|----------|----------|
| 提供姓名映射 | 替换逐字稿中的 `SPEAKER_XX` → 真实姓名 |
| 不提供/回复"不确定" | 保留代号，Agent 在生成纪要时根据上下文语义推测角色（如"业委会主任"、"产品经理"等）

**用户确认后，执行替换**：

用 Edit 工具批量替换逐字稿中的说话人代号：
- `SPEAKER_01` → `莆主任`
- `SPEAKER_02` → `吴晔`
- `Unknown` → 保持不变或根据上下文推断

**示例命令**：
```bash
# 使用 sed 批量替换（若逐字稿在 output 目录）
sed -i '' 's/SPEAKER_01/莆主任/g' output/逐字稿.md
sed -i '' 's/SPEAKER_02/吴晔/g' output/逐字稿.md
```

**重要**：替换完成后，**必须重新读取逐字稿**，确认人名已正确替换，然后才进入步骤 5。

**用户不提供姓名时的降级方案**：

若用户回复"不确定"或不提供，Agent 在生成纪要时根据上下文语义推测：
- 提取每位说话人的发言内容关键词
- 根据自称、称呼、话题判断角色（如"我作为业委会主任"、"李经理"等）
- 在纪要中使用推测的角色名（如"业委会代表"、"技术方"），而非 SPEAKER_XX 代号

**推测示例**：
```
SPEAKER_01 说："我们对物业的考核机制还在完善..."
→ 推测为：业委会代表 / 甲方代表

SPEAKER_02 说："我们做大模型的成本..."
→ 推测为：技术方 / 产品经理
```

### 步骤 5：交付纪要（Agent 生成）

**前提**：逐字稿中说话人代号已完成姓名替换。

会议纪要由 Agent 基于**替换后的逐字稿** + raw.json 生成。

**输出格式**：参见 `references/meeting-template.md`

核心结构：
- 参会人员表（用户确认后的说话人身份）
- 议题分段（智能合并相关段落）
- 每议题配原话摘录（防幻觉）
- 行动项表 + 风险事项

---

## 历史对比洞察

当使用 `--with-history-insight` 时，系统会：

1. **扫描历史会议**：读取 `~/memory/meeting/` 目录下的所有会议纪要
2. **建立索引**：使用 `meeting-indexer.py` 构建可检索的会议数据库
3. **智能关联**：基于议题相似度、参与人员、关键词匹配关联相关历史会议
4. **生成洞察**：
   - **延续话题**：识别与历史会议相同议题的新进展
   - **决策变更**：检测与历史决定不一致的新决策
   - **待办闭环**：检查上次会议 action items 的完成状态
   - **趋势分析**：识别反复出现的问题或模式

---

## 仅生成纪要流程（已有逐字稿）

**适用场景**：用户已通过其他录音软件生成逐字稿，只想用本技能生成会议纪要。

### 步骤 1：读取逐字稿

```bash
# 用户直接提供逐字稿路径
--from-transcript /path/to/transcript.md
```

Agent 使用 Read 工具读取逐字稿内容。

### 步骤 2：识别说话人代号

扫描逐字稿，识别是否有 SPEAKER_XX、Speaker_A 等代号：
- 若有 → 询问用户身份映射
- 若无（已有真实姓名）→ 直接进入步骤 4

### 步骤 3：替换人名或推测角色

**用户提供姓名** → 批量替换：
```
SPEAKER_01 → 莆主任
SPEAKER_02 → 吴晔
```

**用户不提供** → 根据上下文推测角色（见步骤 4 详细说明）。

### 步骤 4：生成会议纪要

基于逐字稿内容，按方法论标准生成纪要。

---

## 纪要质量标准（方法论对照）

本技能按"满分会议纪要方法论"生成纪要：

| 分数 | 标准 | 本技能实现 |
|------|------|------------|
| 5分 | 基础转写 | ✅ Qwen3-ASR 转写 |
| 6-7分 | 结构化分段 | ✅ 按议题分段 + 关键结论 |
| 8分 | 原话节选 | ✅ 每议题配原话摘录（防幻觉） |
| 9分 | 历史对比 | ✅ `--with-history-insight` 关联往期会议 |
| 10分 | 未来探索 | ⚠️ 可扩展（语音克隆、知识图谱等） |

**核心理念**：每个重要观点后配原话节选，保留语气语境，确保表达准确。

---

## 声纹管理

```bash
# 注册声纹（建议 3-10 秒、清晰、单人语音）
python scripts/voiceprint-manager.py enroll --name "张三" --audio /path/to/voice.wav

# 识别说话人
python scripts/voiceprint-manager.py identify --audio /path/to/audio.wav --json

# 查看已注册声纹
python scripts/voiceprint-manager.py list

# 删除声纹
python scripts/voiceprint-manager.py delete --name "张三"
```

---

## 缓存机制

缓存目录：`~/.openclaw/workspace/cache/video-audio-summary/`

- **ASR 缓存**：`<音频哈希>_asr.json`
- **说话人分离缓存**：`<音频哈希>_diarization.json`

使用原则：
- 改 speaker-map 时，不重跑 ASR
- 只补缺失部分，不整场重算

---

## 错误处理决策树

```
脚本执行失败？
├── ffmpeg 不存在 → 告诉用户安装 ffmpeg → 停止
├── Qwen3-ASR 模型缺失 → 告诉用户下载模型 → 停止
├── Qwen3-ASR 环境损坏 → 尝试重建环境 → 重试
├── 本地说话人分离失败 → 先修复根因（音频质量/参数）再重试，不做规则版纪要降级
├── 转写完成但段数=0 且逐字稿有内容 → 修复解析链路后重跑，不允许直接交付
└── 其他 Python 错误 → 贴完整 traceback 告诉用户 + 给出下一步修复建议
```

---

## 输出文件规范

生成的会议纪要保存到：`~/memory/meeting/YYYY-MM-DD-[主题].md`

文件名规范：
- 日期前缀：`YYYY-MM-DD-`
- 主题简述：用 `-` 连接关键词
- 示例：`2026-04-14-产品2.0架构评审会.md`

---

## 参考文件

- **会议纪要模板**：`references/meeting-template.md`
- **测试基线记录**：`references/test-baseline.md`
- **核心脚本**：`scripts/meeting-summarize-v2.py`
- **历史索引**：`scripts/meeting-indexer.py`
