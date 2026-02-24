#!/bin/bash
# 检查视频/音频处理环境（Qwen3-ASR）

echo "================================"
echo "视频/音频处理环境检查"
echo "================================"
echo ""

# 1. 检查 Python
echo "1. 检查 Python 环境..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    echo "   ✓ Python 已安装: $PYTHON_VERSION"
else
    echo "   ✗ Python 未安装"
    echo "   请安装 Python 3.8+"
    exit 1
fi

# 2. 检查 pip
echo ""
echo "2. 检查 pip..."
if command -v pip3 &> /dev/null; then
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
    echo "   ✗ ffmpeg 未安装"
    echo "   请安装: brew install ffmpeg"
    exit 1
fi

# 4. 检查虚拟环境
echo ""
echo "4. 检查虚拟环境..."
VENV_PATH="$HOME/Downloads/qwen-asr-env"
if [ -d "$VENV_PATH" ]; then
    echo "   ✓ 虚拟环境已存在: $VENV_PATH"
else
    echo "   ○ 虚拟环境不存在，将创建: $VENV_PATH"
    python3 -m venv "$VENV_PATH"
    if [ $? -eq 0 ]; then
        echo "   ✓ 虚拟环境创建成功"
    else
        echo "   ✗ 虚拟环境创建失败"
        exit 1
    fi
fi

# 5. 检查/安装依赖
echo ""
echo "5. 检查依赖包..."
source "$VENV_PATH/bin/activate"

# 检查 modelscope
echo ""
echo "   检查 modelscope..."
if pip show modelscope &> /dev/null; then
    VERSION=$(pip show modelscope | grep Version | cut -d' ' -f2)
    echo "   ✓ modelscope 已安装 (版本: $VERSION)"
else
    echo "   ○ modelscope 未安装，正在安装..."
    pip install -i https://pypi.tuna.tsinghua.edu.cn/simple modelscope
    if [ $? -eq 0 ]; then
        echo "   ✓ modelscope 安装成功"
    else
        echo "   ✗ modelscope 安装失败"
        exit 1
    fi
fi

# 检查 torch
echo ""
echo "   检查 torch..."
if pip show torch &> /dev/null; then
    VERSION=$(pip show torch | grep Version | cut -d' ' -f2)
    echo "   ✓ torch 已安装 (版本: $VERSION)"
else
    echo "   ○ torch 未安装，正在安装..."
    pip install -i https://pypi.tuna.tsinghua.edu.cn/simple torch torchaudio
    if [ $? -eq 0 ]; then
        echo "   ✓ torch 安装成功"
    else
        echo "   ✗ torch 安装失败"
        exit 1
    fi
fi

# 检查 soundfile
echo ""
echo "   检查 soundfile..."
if pip show soundfile &> /dev/null; then
    VERSION=$(pip show soundfile | grep Version | cut -d' ' -f2)
    echo "   ✓ soundfile 已安装 (版本: $VERSION)"
else
    echo "   ○ soundfile 未安装，正在安装..."
    pip install -i https://pypi.tuna.tsinghua.edu.cn/simple soundfile
    if [ $? -eq 0 ]; then
        echo "   ✓ soundfile 安装成功"
    else
        echo "   ✗ soundfile 安装失败"
        exit 1
    fi
fi

echo ""
echo "================================"
echo "环境检查完成！"
echo "================================"
echo ""
echo "虚拟环境路径: $VENV_PATH"
echo "激活命令: source $VENV_PATH/bin/activate"
echo ""
echo "提示: 首次运行时需要下载 Qwen3-ASR 模型（约 1.7B 模型约 3.5GB）"
echo "模型将缓存到: ~/.cache/modelscope/hub/"
echo ""
