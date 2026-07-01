#!/bin/bash
# XCP 握手测试工具 - Linux 打包脚本

set -e

echo "========================================"
echo "  XCP 握手测试工具 - Linux 打包脚本"
echo "========================================"
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到 Python3，请先安装 Python 3.10+"
    exit 1
fi

echo "[1/4] 安装依赖..."
pip3 install pyinstaller construct pyserial pyusb python-can rich chardet traitlets toml pytz pydantic pybind11 cmake

echo ""
echo "[2/4] 编译 C++ 扩展..."
python3 build_ext.py

echo ""
echo "[3/4] 打包可执行文件..."
pyinstaller --clean xcp_handshake_test.spec

echo ""
echo "[4/4] 完成！"
echo "========================================"
echo ""
echo "打包完成！输出文件在 dist/ 目录下"
echo "运行: ./dist/XCP_Handshake_Test"
echo ""
