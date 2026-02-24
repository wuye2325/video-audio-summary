#!/bin/bash
# 检查视频/音频处理环境（Qwen3-ASR）
# 官方文档：https://www.modelscope.cn/models/Qwen/Qwen3-ASR-1.7B/summary
#
# ⚠️  国内网络常见问题与解决方案
#
# 1. pip 安装超时（torch 包约 80-500MB）:
#    按顺序尝试镜像：阿里云（推荐）→ 清华 → 腾讯云
#    用法: PIP_MIRROR=<URL> bash check_environment.sh
#
# 2. 模型下载 SSL 证书错误（企业代理 self-signed 证书）:
#    症状: SSLCertVerificationError / certificate verify failed
#    解法: 导出系统 Keychain 证书合并到 Python certifi（见步骤 7）
#          + 使用 hf-mirror.com 国内镜像下载 HuggingFace 模型
#
# 3. modelscope CLI 在 Python 3.12 下报 No module named 'pkg_resources':
#    解法: 直接用 huggingface_hub Python API 替代 CLI（见步骤 8）

# 默认使用阿里云镜像（推荐）
PIP_MIRROR="${PIP_MIRROR:-https://mirrors.aliyun.com/pypi/simple/}"
# 模型下载目录（留空则仅用 HuggingFace Hub 缓存）
MODEL_LOCAL_DIR="${MODEL_LOCAL_DIR:-$HOME/Qwen3-ASR-1.7B}"
PIP_TIMEOUT=300
PIP_RETRIES=5

echo "================================"
echo "视频/音频处理环境检查 (Qwen3-ASR)"
echo "================================"
echo ""
echo "pip 镜像源: $PIP_MIRROR"
echo "模型下载路径: $MODEL_LOCAL_DIR"
echo ""

pip_install() {
    pip install "$@" -i "$PIP_MIRROR" --timeout "$PIP_TIMEOUT" --retries "$PIP_RETRIES"
}

# 1. 检查 Python
echo "1. 检查 Python 环境..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    echo "   ✓ Python 已安装: $PYTHON_VERSION"
else
    echo "   ✗ Python 未安装"
    echo "   推荐: brew install python@3.12"
    exit 1
fi

# 2. 检查 pip
echo ""
echo "2. 检查 pip..."
if command -v pip3 &> /dev/null || command -v pip &> /dev/null; then
    echo "   ✓ pip 已安装"
else
    echo "   ✗ pip 未安装"
    exit 1
fi

# 3. 检查 ffmpeg
echo ""
echo "3. 检查 ffmpeg (视频处理必需)..."
if command -v ffmpeg &> /dev/null; then
    echo "   ✓ ffmpeg 已安装"
else
    echo "   ✗ ffmpeg 未安装（视频文件需要，纯音频可跳过）"
    echo "   安装: brew install ffmpeg"
fi

# 4. 检查 torch（先安装大包，降低超时风险）
echo ""
echo "4. 检查 PyTorch..."
if pip show torch &> /dev/null 2>&1; then
    VERSION=$(pip show torch 2>/dev/null | grep Version | cut -d' ' -f2)
    echo "   ✓ torch 已安装 (版本: $VERSION)"
else
    echo "   ○ torch 未安装，正在安装（约 80-500MB，耐心等待）..."
    pip_install torch torchaudio
    if [ $? -eq 0 ]; then
        echo "   ✓ torch 安装成功"
    else
        echo "   ✗ torch 安装失败"
        echo ""
        echo "   💡 网络超时排查建议（按顺序尝试）："
        echo "      PIP_MIRROR=https://pypi.tuna.tsinghua.edu.cn/simple bash $0"
        echo "      PIP_MIRROR=https://mirrors.cloud.tencent.com/pypi/simple bash $0"
        exit 1
    fi
fi

# 5. 检查 qwen-asr（核心依赖）
echo ""
echo "5. 检查 qwen-asr..."
if pip show qwen-asr &> /dev/null 2>&1; then
    VERSION=$(pip show qwen-asr 2>/dev/null | grep Version | cut -d' ' -f2)
    echo "   ✓ qwen-asr 已安装 (版本: $VERSION)"
else
    echo "   ○ qwen-asr 未安装，正在安装..."
    pip_install qwen-asr
    if [ $? -eq 0 ]; then
        echo "   ✓ qwen-asr 安装成功"
    else
        echo "   ✗ qwen-asr 安装失败，请参考步骤 4 的网络排查建议"
        exit 1
    fi
fi

# 6. 验证 PyTorch 及硬件加速
echo ""
echo "6. 验证 PyTorch 及硬件加速支持..."
python3 - << 'EOF'
import sys
try:
    import torch
    print(f"   ✓ PyTorch 版本: {torch.__version__}")
    if torch.cuda.is_available():
        print(f"   ✓ CUDA 可用: {torch.cuda.get_device_name(0)}")
    else:
        print("   ○ CUDA 不可用（非 NVIDIA GPU 属正常）")
    if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        print("   ✓ MPS 可用（Apple Silicon 加速就绪）")
        print("   ✓ 建议配置: dtype=torch.bfloat16, device_map='mps'")
    else:
        print("   ○ MPS 不可用（非 Apple Silicon 属正常）")
except ImportError:
    print("   ✗ PyTorch 未安装")
    sys.exit(1)
EOF
[ $? -ne 0 ] && exit 1

# 7. 修复 SSL 证书（企业/学校代理环境必须执行）
echo ""
echo "7. 检查 SSL 证书配置..."
SSL_TEST=$(python3 -c "import urllib.request; urllib.request.urlopen('https://hf-mirror.com', timeout=5)" 2>&1)
if [ $? -eq 0 ]; then
    echo "   ✓ SSL 连接正常，无需修复"
else
    echo "   ✗ SSL 连接失败（可能存在代理自签名证书）"
    echo "   正在将系统 Keychain 证书合并到 Python certifi..."

    CERTIFI_PATH=$(python3 -c "import certifi; print(certifi.where())")
    # 备份原证书
    [ ! -f "${CERTIFI_PATH}.bak" ] && cp "$CERTIFI_PATH" "${CERTIFI_PATH}.bak"

    # 导出并合并系统证书
    security export -t certs -f pemseq -k /Library/Keychains/System.keychain >> "$CERTIFI_PATH" 2>/dev/null
    security export -t certs -f pemseq -k ~/Library/Keychains/login.keychain-db >> "$CERTIFI_PATH" 2>/dev/null

    CERT_COUNT=$(grep -c 'BEGIN CERTIFICATE' "$CERTIFI_PATH")
    echo "   ✓ 系统证书已合并（总证书数: $CERT_COUNT）"
    echo "   提示: 备份保存在 ${CERTIFI_PATH}.bak"

    # 重新验证
    SSL_TEST2=$(python3 -c "import urllib.request; urllib.request.urlopen('https://hf-mirror.com', timeout=5)" 2>&1)
    if [ $? -eq 0 ]; then
        echo "   ✓ SSL 修复成功"
    else
        echo "   ⚠ SSL 仍然失败，可能需要手动安装企业根证书"
    fi
fi

# 8. 下载 Qwen3-ASR-1.7B 模型
echo ""
echo "8. 检查 Qwen3-ASR-1.7B 模型..."
if [ -f "$MODEL_LOCAL_DIR/config.json" ]; then
    echo "   ✓ 模型已存在: $MODEL_LOCAL_DIR"
else
    echo "   ○ 模型不存在，正在从 hf-mirror.com 下载（约 3.5GB）..."
    echo "   ⚠ 注意：modelscope CLI 在 Python 3.12 下存在 pkg_resources 兼容问题"
    echo "   ✓ 改用 huggingface_hub Python API + hf-mirror.com 镜像下载"

    python3 - << PYEOF
import os, sys
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
try:
    from huggingface_hub import snapshot_download
    local_dir = os.path.expanduser('$MODEL_LOCAL_DIR')
    print(f"   开始下载到: {local_dir}")
    path = snapshot_download(
        repo_id='Qwen/Qwen3-ASR-1.7B',
        local_dir=local_dir,
    )
    print(f"   ✓ 模型下载完成: {path}")
except Exception as e:
    print(f"   ✗ 下载失败: {e}")
    print("   💡 手动下载命令:")
    print("      HF_ENDPOINT=https://hf-mirror.com python3 -c \"")
    print("      from huggingface_hub import snapshot_download")
    print("      snapshot_download('Qwen/Qwen3-ASR-1.7B', local_dir='~/Qwen3-ASR-1.7B')\"")
    sys.exit(1)
PYEOF
    [ $? -ne 0 ] && exit 1
fi

echo ""
echo "================================"
echo "环境检查完成！"
echo "================================"
echo ""
echo "快速开始："
echo "  export QWEN_ASR_MODEL_PATH=$MODEL_LOCAL_DIR"
echo "  python scripts/extract_transcript.py \"/path/to/video.mp4\""
echo ""
