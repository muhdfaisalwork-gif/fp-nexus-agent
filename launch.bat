@echo off
title FP Nexus Agent Studio
color 0A

echo =================================================================
echo   FP NEXUS AGENT - Autonomous Freelancing Platforms Studio
echo =================================================================
echo.

cd /d "%~dp0"

echo [1/3] Checking Python environment...
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

%PYTHON_EXE% --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH.
    pause
    exit /b 1
)

echo [2/3] Checking dependencies...
%PYTHON_EXE% -m pip install -r requirements.txt >nul 2>&1

echo [3/3] Launching Studio Server on http://localhost:8001 ...
start http://localhost:8001
%PYTHON_EXE% run.py

pause
