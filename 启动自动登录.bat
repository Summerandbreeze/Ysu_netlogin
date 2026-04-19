@echo off
chcp 65001 >nul 2>&1
title 燕山大学校园网自动登录

echo ============================================
echo    燕山大学校园网自动登录工具
echo ============================================
echo.

:: 切换到脚本所在目录
cd /d "%~dp0"

:: 检查Python是否可用
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到Python，请先安装Python 3.x
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 检查配置文件
if not exist "config.json" (
    echo [错误] 未找到配置文件 config.json
    echo 请参考 config.json 创建配置文件
    pause
    exit /b 1
)

echo [启动] 守护模式运行中...
echo        每5分钟检测一次网络
echo        按 Ctrl+C 可停止
echo.
echo ----------------------------------------
python ysu_login.py daemon 300
echo.
echo 程序已退出
pause
