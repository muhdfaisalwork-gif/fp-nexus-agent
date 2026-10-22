@echo off
title FP Nexus - Interactive Account Login
color 0B

echo =================================================================
echo   FP NEXUS AGENT - Interactive Account Login
echo =================================================================
echo.

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo Select platform to connect:
echo [1] Fiverr
echo [2] Upwork
echo.
set /p choice="Enter choice (1 or 2): "

if "%choice%"=="2" (
    echo Launching Upwork browser login...
    %PYTHON_EXE% scripts/login_browser.py upwork
) else (
    echo Launching Fiverr browser login...
    %PYTHON_EXE% scripts/login_browser.py fiverr
)

echo.
pause
