# 常见问题与故障排除

---

## FAQ

### Q: 脚本会自动选择最优配置吗？

是的。脚本自动检测硬件并选择最优方案：
- **NVIDIA GPU** → CUDA（最快）
- **Apple Silicon** → MPS（比 CPU 快 3-5 倍）
- **CPU** → 根据 CPU 配置选择模型大小

### Q: pip 安装网络超时？

`torch` 约 80-500MB，国内直连 PyPI 易超时。

```bash
# 推荐：使用 check_environment.sh（已内置阿里云镜像）
bash scripts/check_environment.sh

# 或手动安装
pip install torch torchaudio -i https://mirrors.aliyun.com/pypi/simple/ --timeout 300
pip install qwen-asr -i https://mirrors.aliyun.com/pypi/simple/
```

### Q: SSL 证书错误（企业网络代理）？

企业/学校网络代理（深信服、Zscaler）用自签名证书拦截 HTTPS。

```bash
# 已集成到 check_environment.sh，自动修复
# 或手动合并系统证书到 certifi
CERTIFI=$(python3 -c "import certifi; print(certifi.where())")
security export -t certs -f pemseq -k /Library/Keychains/System.keychain >> "$CERTIFI"
```

### Q: 如何下载模型？

```bash
# 使用 hf-mirror.com 镜像（国内推荐）
python3 -c "
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
from huggingface_hub import snapshot_download
snapshot_download('Qwen/Qwen3-ASR-1.7B', local_dir='~/Qwen3-ASR-1.7B')
"
```

### Q: 处理速度慢？

1. 检查是否有 GPU（安装 CUDA Toolkit）
2. Apple Silicon 确保使用最新 qwen-asr（支持 MPS）
3. 使用小模型：`export QWEN_ASR_MODEL=Qwen/Qwen3-ASR-0.6B`

### Q: 中文识别效果不好？

- Qwen3-ASR 针对中文优化，通常优于 Whisper
- 确保音频质量清晰
- 已自动处理标点还原

---

## 环境变量速查

| 变量 | 说明 |
|------|------|
| `QWEN_ASR_PYTHON` | 指定 Python 解释器路径 |
| `QWEN_ASR_VENV` | 指定虚拟环境目录 |
| `QWEN_ASR_MODEL_PATH` | 本地模型目录（含 config.json） |
| `QWEN_ASR_MODEL` | 远端模型名 |
| `QWEN_ASR_DEVICE` | 设备：cuda/mps/cpu |
| `QWEN_ASR_DTYPE` | 数据类型：float16/bfloat16/float32 |

---

## API 参考

详细 API 用法见 `references/qwen-asr-api.md`