@echo off
title OS-DBX Forensic Collector Agent
cd /d "%~dp0"

echo ======================================================================
echo           OS-DBX Forensic Endpoint Collector
echo ======================================================================
echo.

set "PY_BIN="
if exist "..\..\backend\venv\Scripts\python.exe" (
    set "PY_BIN=..\..\backend\venv\Scripts\python.exe"
) else if exist "..\venv\Scripts\python.exe" (
    set "PY_BIN=..\venv\Scripts\python.exe"
) else if exist "venv\Scripts\python.exe" (
    set "PY_BIN=venv\Scripts\python.exe"
)

if "%PY_BIN%"=="" (
    where python >nul 2>&1
    if not errorlevel 1 set "PY_BIN=python"
)
if "%PY_BIN%"=="" (
    where py >nul 2>&1
    if not errorlevel 1 set "PY_BIN=py"
)

set DEFAULT_SERVER=https://testing-4bux.onrender.com
set /p SERVER_INPUT="Enter Server URL [Press Enter for %DEFAULT_SERVER%]: "
if "%SERVER_INPUT%"=="" set SERVER_INPUT=%DEFAULT_SERVER%

if not "%SERVER_INPUT:~0,4%"=="http" set SERVER_URL=http://%SERVER_INPUT%
if "%SERVER_INPUT:~0,4%"=="http" set SERVER_URL=%SERVER_INPUT%

set /p HOST_INPUT="Enter Host ID / Computer Name [Press Enter for %COMPUTERNAME%]: "
if "%HOST_INPUT%"=="" set HOST_INPUT=%COMPUTERNAME%

echo.
echo [*] Target Server: %SERVER_URL%
echo [*] Device Host ID: %HOST_INPUT%
echo [*] Starting collector...
echo.

if exist "osdbx-agent.exe" (
    osdbx-agent.exe --server "%SERVER_URL%" --host-id "%HOST_INPUT%"
) else if exist "..\osdbx_agent.py" (
    if "%PY_BIN%"=="" (
        echo [ERROR] Python not found on this system! Please install Python 3.10+
        pause
        exit /b 1
    )
    "%PY_BIN%" ..\osdbx_agent.py --server "%SERVER_URL%" --host-id "%HOST_INPUT%"
) else if exist "osdbx_agent.py" (
    if "%PY_BIN%"=="" (
        echo [ERROR] Python not found on this system! Please install Python 3.10+
        pause
        exit /b 1
    )
    "%PY_BIN%" osdbx_agent.py --server "%SERVER_URL%" --host-id "%HOST_INPUT%"
) else (
    echo [ERROR] Neither osdbx-agent.exe nor osdbx_agent.py was found!
)
pause
