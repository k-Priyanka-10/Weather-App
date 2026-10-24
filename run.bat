@echo off
title SkyCast Weather Forecast Application
echo Starting SkyCast Weather Application...

:: Check py launcher first
py -3.12 --version >nul 2>&1
if %errorlevel% equ 0 (
    py -3.12 main.py
    goto end
)

py --version >nul 2>&1
if %errorlevel% equ 0 (
    py main.py
    goto end
)

python --version >nul 2>&1
if %errorlevel% equ 0 (
    python main.py
    goto end
)

echo Python is not found in PATH or via 'py' launcher.
echo Please ensure Python 3.10+ is installed and accessible.
pause

:end
