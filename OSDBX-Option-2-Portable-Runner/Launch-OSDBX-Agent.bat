@echo off
title OS-DBX Forensic Collector Agent
cd /d "%~dp0"

echo ======================================================================
echo           OS-DBX Unified Forensic Observability Platform
echo                     Endpoint Collector Agent
echo ======================================================================
echo.

set "PY_BIN="

if exist "..\backend\venv\Scripts\python.exe" set "PY_BIN=..\backend\venv\Scripts\python.exe"
if "%PY_BIN%"=="" if exist "venv\Scripts\python.exe" set "PY_BIN=venv\Scripts\python.exe"
if "%PY_BIN%"=="" if exist "..\testing\venv\Scripts\python.exe" set "PY_BIN=..\testing\venv\Scripts\python.exe"
if "%PY_BIN%"=="" if exist "C:\Python315\python.exe" set "PY_BIN=C:\Python315\python.exe"
if "%PY_BIN%"=="" (
    where python >nul 2>&1
    if not errorlevel 1 set "PY_BIN=python"
)
if "%PY_BIN%"=="" (
    where py >nul 2>&1
    if not errorlevel 1 set "PY_BIN=py"
)

if "%PY_BIN%"=="" (
    echo [ERROR] Python not found on this system!
    echo Please install Python 3.10+ from python.org or the Microsoft Store.
    echo.
    pause
    exit /b 1
)

echo [*] Python runtime: %PY_BIN%
echo [*] Verifying libraries: psutil, watchdog, requests...
"%PY_BIN%" -c "import psutil, watchdog, requests" >nul 2>&1
if errorlevel 1 (
    echo [*] Installing required packages...
    "%PY_BIN%" -m pip install --quiet psutil watchdog requests
)

echo [*] Cloud Backend:   https://testing-4bux.onrender.com
echo [*] Cloud Dashboard: https://testing-sooty-omega.vercel.app/
echo.
echo [*] Live telemetry is streaming. Press Ctrl+C to stop.
echo ======================================================================
echo.

"%PY_BIN%" osdbx_agent.py --server "https://testing-4bux.onrender.com"

pause
