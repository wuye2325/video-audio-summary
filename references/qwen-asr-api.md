# Qwen3-ASR API 参考

> 来源：官方 qwen-asr 文档
> 用途：需要自定义推理参数时参考

---

## 快速推理

```python
import torch
from qwen_asr import Qwen3ASRModel

model = Qwen3ASRModel.from_pretrained(
    "Qwen/Qwen3-ASR-1.7B",
    dtype=torch.bfloat16,   # 官方推荐 BF16
    device_map="mps",       # Mac 用 mps，NVIDIA 用 cuda:0，CPU 不传
    max_inference_batch_size=8,
    max_new_tokens=256,
)

results = model.transcribe(audio="audio.wav", language=None)
print(f"语言: {results[0].language}")
print(f"文本: {results[0].text}")
```

---

## 带时间戳推理

```python
model = Qwen3ASRModel.from_pretrained(
    "Qwen/Qwen3-ASR-1.7B",
    dtype=torch.bfloat16,
    device_map="cuda:0",
    forced_aligner="Qwen/Qwen3-ForcedAligner-0.6B",
    forced_aligner_kwargs=dict(dtype=torch.bfloat16, device_map="cuda:0"),
)

results = model.transcribe(
    audio=["audio1.wav", "audio2.wav"],
    language=None,
    return_time_stamps=True,
)

for r in results:
    print(r.language, r.text, r.time_stamps[0])
```

---

## 常用环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `QWEN_ASR_MODEL` | 远端模型名 | `Qwen/Qwen3-ASR-1.7B` |
| `QWEN_ASR_MODEL_PATH` | 本地模型目录 | `~/Qwen3-ASR-1.7B` |
| `QWEN_ASR_DEVICE` | 设备 | `cuda`/`mps`/`cpu` |
| `QWEN_ASR_DTYPE` | 数据类型 | `float16`/`bfloat16`/`float32` |
| `QWEN_ASR_CHUNK_SECONDS` | 分块时长 | `60`（默认） |