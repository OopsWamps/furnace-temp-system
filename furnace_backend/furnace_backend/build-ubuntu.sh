#!/bin/bash

# Ubuntu 环境下构建脚本

set -e

echo "====================================="
echo "  Furnace Backend 构建脚本"
echo "====================================="

# 检查 Python 版本
PYTHON_CMD=""
if command -v python3.10 &> /dev/null; then
    PYTHON_CMD="python3.10"
elif command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
elif command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    echo "错误: 未找到 Python 3"
    exit 1
fi

echo "使用 Python: $PYTHON_CMD"
$PYTHON_CMD --version

# 创建虚拟环境
echo ""
echo "创建虚拟环境..."
if [ ! -d "venv" ]; then
    $PYTHON_CMD -m venv venv
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 升级 pip
echo "升级 pip..."
pip install --upgrade pip

# 安装依赖
echo ""
echo "安装项目依赖..."
pip install -r requirements.txt

# 安装 PyInstaller
echo "安装 PyInstaller..."
pip install pyinstaller

# 清理旧的构建
echo ""
echo "清理旧的构建文件..."
rm -rf build dist __pycache__

# 开始构建
echo ""
echo "开始构建二进制文件..."
pyinstaller --clean furnace_backend.spec

echo ""
echo "====================================="
echo "  构建完成!"
echo "====================================="
echo "二进制文件位置: dist/furnace_backend"
echo ""
echo "运行方式:"
echo "  cd dist"
echo "  ./furnace_backend"
echo ""
echo "确保 config/config.yaml 和模型文件在同一目录下"
echo ""
