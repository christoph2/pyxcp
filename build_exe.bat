@echo off
chcp 65001 >nul
echo ========================================
echo   XCP 握手测试工具 - Windows 打包脚本
echo ========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

echo [1/4] 安装依赖...
pip install pyinstaller construct pyserial pyusb python-can rich chardet traitlets toml pytz pydantic pybind11 cmake
if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)

echo.
echo [2/4] 编译 C++ 扩展...
python build_ext.py
if errorlevel 1 (
    echo [警告] C++ 扩展编译可能有问题，继续尝试打包...
)

echo.
echo [3/4] 打包 EXE...
pyinstaller --clean xcp_handshake_test.spec
if errorlevel 1 (
    echo [错误] 打包失败
    pause
    exit /b 1
)

echo.
echo [4/4] 完成！
echo ========================================
echo.
echo 打包完成！输出文件在 dist\ 目录下
echo 运行: dist\XCP_Handshake_Test.exe
echo.
pause
