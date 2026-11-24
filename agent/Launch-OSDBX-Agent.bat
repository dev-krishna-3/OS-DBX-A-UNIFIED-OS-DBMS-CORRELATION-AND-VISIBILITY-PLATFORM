@echo off
title OS-DBX Forensic Collector (Live Stream)
cd /d "%~dp0"
color 0A

echo ======================================================================
echo           OS-DBX Unified Forensic Observability Platform
echo                     Endpoint Collector Agent
echo ======================================================================
echo.

set "PY_BIN="

REM 1. Check virtual environment
if exist "..\testing\venv\Scripts\python.exe" (
    set "PY_BIN=..\testing\venv\Scripts\python.exe"
) else if exist "venv\Scripts\python.exe" (
    set "PY_BIN=venv\Scripts\python.exe"
) else if exist "C:\Python315\python.exe" (
    set "PY_BIN=C:\Python315\python.exe"
)

REM 2. Check system PATH python
if "%PY_BIN%"=="" (
    where python >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        set "PY_BIN=python"
    )
)

if "%PY_BIN%"=="" (
    where py >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        set "PY_BIN=py"
    )
)

if "%PY_BIN%"=="" (
    echo [ERROR] Python not found on this system!
    echo Please install Python 3.10+ from python.org or Microsoft Store,
    echo or use Option 1 (osdbx-agent.exe).
    pause
    exit /b 1
)

echo [*] Using runtime: %PY_BIN%
echo [*] Checking dependencies (psutil, watchdog, requests)...
"%PY_BIN%" -c "import psutil, watchdog, requests" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [*] Installing required modules (one-time setup)...
    "%PY_BIN%" -m pip install --quiet psutil watchdog requests
)

echo [*] Cloud Server:   https://testing-4bux.onrender.com
echo [*] Cloud Dashboard:https://testing-sooty-omega.vercel.app/
echo.
echo ======================================================================
echo    Starting telemetry collection... Press Ctrl+C to stop.
echo ======================================================================
echo.

"%PY_BIN%" osdbx_agent.py --server "https://testing-4bux.onrender.com"

pause
