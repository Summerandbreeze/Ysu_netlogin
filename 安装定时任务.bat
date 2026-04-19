@echo off
chcp 65001 >nul 2>&1
title 安装校园网自动登录定时任务

echo ============================================
echo    安装校园网自动登录 - Windows定时任务
echo ============================================
echo.

:: 获取脚本所在目录的绝对路径
set "SCRIPT_DIR=%~dp0"
set "PYTHON_SCRIPT=%SCRIPT_DIR%ysu_login.py"
set "PYTHON_EXE=C:\Python313\python.exe"

:: 检查Python
if not exist "%PYTHON_EXE%" (
    echo [检查] 尝试查找 Python...
    for /f "delims=" %%i in ('where python 2^>nul') do set "PYTHON_EXE=%%i"
)
if not exist "%PYTHON_EXE%" (
    echo [错误] 未找到Python，请手动修改此脚本中的PYTHON_EXE路径
    pause
    exit /b 1
)
echo [信息] Python路径: %PYTHON_EXE%
echo [信息] 脚本路径: %PYTHON_SCRIPT%
echo.

:: 先删除已有的同名任务（忽略错误）
schtasks /delete /tn "YSU_校园网自动登录" /f >nul 2>&1

:: 创建定时任务：每小时运行一次，全天24小时
echo [安装] 创建定时任务（每小时运行一次）...
schtasks /create /tn "YSU_校园网自动登录" /tr "\"%PYTHON_EXE%\" \"%PYTHON_SCRIPT%\" once" /sc hourly /mo 1 /f /rl highest

if %errorlevel% equ 0 (
    echo.
    echo ============================================
    echo   ✅ 定时任务安装成功！
    echo ============================================
    echo.
    echo   任务名称: YSU_校园网自动登录
    echo   执行频率: 每小时一次
    echo   执行方式: 单次检测（断网自动登录）
    echo.
    echo   管理命令:
    echo     查看任务: schtasks /query /tn "YSU_校园网自动登录"
    echo     手动运行: schtasks /run /tn "YSU_校园网自动登录"
    echo     删除任务: schtasks /delete /tn "YSU_校园网自动登录" /f
    echo.
    echo   💡 建议同时将「启动自动登录.bat」放入
    echo      Windows启动文件夹，实现开机自动运行守护模式
    echo.
) else (
    echo.
    echo [错误] 定时任务创建失败，请以管理员身份运行此脚本
    echo.
)

pause
