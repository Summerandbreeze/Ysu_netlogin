@echo off
:: 最小化窗口运行，不弹黑框
if "%1"=="minimized" goto :main
start /min cmd /c "%~f0" minimized
exit /b

:main
chcp 65001 >nul 2>&1
title YSU AutoLogin
cd /d "%~dp0"
python ysu_login.py daemon 300
