#!/bin/bash
# 检查视频/音频处理环境（Qwen3-ASR）
# 官方文档：https://www.modelscope.cn/models/Qwen/Qwen3-ASR-1.7B/summary
#
# ⚠️  国内网络说明（pip 安装常见超时解决方案）
# PyPI 官方源速度慢或超时时，推荐按以下顺序尝试镜像：
#   1. 阿里云（推荐）:   https://mirrors.aliyun.com/pypi/simple/
#   2. 清华大学:         https://pypi.tuna.tsinghua.edu.cn/simple
#   3. 腾讯云:          https://mirrors.cloud.tencent.com/pypi/simple
# 用法：PIP_MIRROR=<镜像URL> bash check_environment.sh

# 默认使用阿里云镜像（国内最稳定，PyPI 官方源经常超时）
PIP_MIRROR="${PIP_MIRROR:-https://mirrors.aliyun.com/pypi/simple/}"
PIP_TIMEOUT=300
PIP_RETRIES=5

echo "================================"
echo "视频/音频处理环境检查 (Qwen3-ASR)"
echo "================================"
echo ""
echo "pip 镜像源: $PIP_MIRROR"
echo "（如需更换，运行: PIP_MIRROR=<镜像URL> bash check_environment.sh）"
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
    echo "   ✗ ffmpeg 未安装（视频文件需要此工具，纯音频文件可跳过）"
    echo "   安装: brew install ffmpeg"
fi

# 4. 检查 torch（先单独安装，包体积大，超时风险高）
echo ""
echo "4. 检查 PyTorch..."
if pip show torch &> /dev/null 2>&1; then
    VERSION=$(pip show torch 2>/dev/null | grep Version | cut -d' ' -f2)
    echo "   ✓ torch 已安装 (版本: $VERSION)"
else
    echo "   ○ torch 未安装，正在安装（约 80-500MB，耐心等待）..."
    echo "   使用镜像: $PIP_MIRROR"
    pip_install torch torchaudio
    if [ $? -eq 0 ]; then
        echo "   ✓ torch 安装成功"
    else
        echo "   ✗ torch 安装失败"
        echo ""
        echo "   💡 网络超时排查建议："
        echo "      1. 切换镜像: PIP_MIRROR=https://pypi.tuna.tsinghua.edu.cn/simple bash $0"
        echo "      2. 或手动分步安装: pip install torch torchaudio -i <镜像URL> --timeout 300"
        echo "      3. 可用镜像列表："
        echo "         - 阿里云:  https://mirrors.aliyun.com/pypi/simple/"
        echo "         - 清华:    https://pypi.tuna.tsinghua.edu.cn/simple"
        echo "         - 腾讯云:  https://mirrors.cloud.tencent.com/pypi/simple"
        exit 1
    fi
fi

# 5. 检查 qwen-asr（核心依赖）
echo ""
echo "5. 检查 qwen-asr（核心依赖）..."
if pip show qwen-asr &> /dev/null 2>&1; then
    VERSION=$(pip show qwen-asr 2>/dev/null | grep Version | cut -d' ' -f2)
    echo "   ✓ qwen-asr 已安装 (版本: $VERSION)"
else
    echo "   ○ qwen-asr 未安装，正在安装..."
    pip_install qwen-asr
    if [ $? -eq 0 ]; then
        echo "   ✓ qwen-asr 安装成功"
    else
        echo "   ✗ qwen-asr 安装失败"
        echo "   💡 请参考上方网络超时排查建议"
        exit 1
    fi
fi

# 6. 检查 torch 及 MPS 支持（Mac Apple Silicon）
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
        print("   ✓ 建议使用: dtype=torch.bfloat16, device_map='mps'")
    else:
        print("   ○ MPS 不可用（非 Apple Silicon 属正常）")

except ImportError:
    print("   ✗ PyTorch 未安装")
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    exit 1
fi

# 7. 检查 modelscope（可选）
echo ""
echo "7. 检查 modelscope（可选，国内高速下载模型用）..."
if pip show modelscope &> /dev/null 2>&1; then
    VERSION=$(pip show modelscope 2>/dev/null | grep Version | cut -d' ' -f2)
    echo "   ✓ modelscope 已安装 (版本: $VERSION)"
else
    echo "   ○ 未安装（可选）。如需国内高速下载模型："
    echo "     pip install modelscope -i $PIP_MIRROR"
fi

echo ""
echo "================================"
echo "环境检查完成！"
echo "================================"
echo ""
echo "快速开始（Mac Apple Silicon 用户）："
echo "  python scripts/extract_transcript.py \"/path/to/video.mp4\""
echo ""
echo "模型首次运行时自动下载（约 3.5GB），也可提前手动下载："
echo "  modelscope download --model Qwen/Qwen3-ASR-1.7B --local_dir ~/Qwen3-ASR-1.7B"
echo "  export QWEN_ASR_MODEL_PATH=~/Qwen3-ASR-1.7B"
echo ""
