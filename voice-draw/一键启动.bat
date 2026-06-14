@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title Voice Draw - 纯语音绘图工具

echo ================================================
echo        Voice Draw - 纯语音绘图工具
echo ================================================
echo.

:: 检测 Python
set PYTHON=d:\Project\pythonProject\.venv\Scripts\python.exe
if not exist "%PYTHON%" (
    echo [错误] 未找到 Python: %PYTHON%
    echo 请修改本文件中的 PYTHON 路径
    pause
    exit /b 1
)

:: 检查依赖
echo [1/3] 检查依赖...
%PYTHON% -c "import fastapi, uvicorn, openai" 2>nul
if errorlevel 1 (
    echo [警告] 依赖未安装，正在安装...
    d:\Project\pythonProject\.venv\Scripts\pip install fastapi uvicorn openai
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
)
echo [✓] 依赖检查通过

:: 检查 API Key
echo.
echo [2/3] 检查 API Key...
%PYTHON% -c "import os; key = os.getenv('DEEPSEEK_API_KEY', 'your-api-key-here'); exit(0 if key != 'your-api-key-here' else 1)" 2>nul
if errorlevel 1 (
    echo [提示] 未设置 DEEPSEEK_API_KEY 环境变量
    echo.
    echo 请选择设置方式:
    echo   1. 直接输入密钥 (本次生效)
    echo   2. 已在 server.py 中硬编码 (跳过)
    echo.
    set /p API_KEY="请输入 DeepSeek API Key (直接回车跳过): "
    if not "!API_KEY!"=="" set DEEPSEEK_API_KEY=!API_KEY!
)
echo [✓] API Key 检查完成

:: 启动服务
echo.
echo [3/3] 启动服务...
echo.
echo ================================================
echo   服务地址: http://localhost:8765
echo   按 Ctrl+C 停止服务
echo ================================================
echo.

:: 等待1秒后打开浏览器
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:8765"

:: 启动 Python 服务
cd /d "%~dp0"
%PYTHON% server.py

pause