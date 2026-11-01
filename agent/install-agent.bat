@echo off
setlocal enabledelayedexpansion
title OS-DBX Forensic Collector Installer

echo ======================================================================
echo       OS-DBX: Enterprise Endpoint Forensic Agent Installer
echo ======================================================================
echo.

:: 1. Check Python installation
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed on this system.
    echo Please install Python 3.10+ from https://python.org or Windows Store.
    pause
    exit /b 1
)

:: 2. Target Server URL & Device Credential
set "SERVER_URL=%~1"
if "%SERVER_URL%"=="" (
    set /p "SERVER_URL=Enter OS-DBX Server URL [Default: http://localhost:8000]: "
)
if "%SERVER_URL%"=="" set "SERVER_URL=http://localhost:8000"

set "DEVICE_TOKEN=%~2"
if "%DEVICE_TOKEN%"=="" (
    set /p "DEVICE_TOKEN=Enter Device Credential Token (from OS-DBX Devices panel): "
)

:: 3. Save config
set "AGENT_DIR=%~dp0"
set "CONFIG_FILE=%AGENT_DIR%config.json"
echo {"server_url": "%SERVER_URL%", "host_id": "%COMPUTERNAME%", "api_token": "%DEVICE_TOKEN%", "watch_paths": ["%USERPROFILE%\\Desktop", "."], "poll_interval_sec": 3.0} > "%CONFIG_FILE%"

echo [*] Target Server: %SERVER_URL%
echo [*] Target Host:   %COMPUTERNAME%
echo.

:: 4. Verify / Install Dependencies
echo [*] Checking required forensic libraries (psutil, watchdog)...
python -m pip install --quiet psutil watchdog

:: 5. Register Auto-start Task on Windows Boot/Logon
echo [*] Registering silent startup task in Windows Task Scheduler...
set "TASK_NAME=OSDBX_Forensic_Agent"
set "PYTHONW_PATH="
for /f "delims=" %%i in ('where pythonw 2^>nul') do (
    if not defined PYTHONW_PATH set "PYTHONW_PATH=%%i"
)
if "%PYTHONW_PATH%"=="" (
    for /f "delims=" %%i in ('where python 2^>nul') do (
        if not defined PYTHONW_PATH set "PYTHONW_PATH=%%~dpi\pythonw.exe"
    )
)

schtasks /Create /TN "%TASK_NAME%" /TR "\"%PYTHONW_PATH%\" \"%AGENT_DIR%osdbx_agent.py\"" /SC ONLOGON /RL HIGHEST /F >nul 2>&1
if %ERRORLEVEL% neq 0 (
    schtasks /Create /TN "%TASK_NAME%" /TR "\"%PYTHONW_PATH%\" \"%AGENT_DIR%osdbx_agent.py\"" /SC ONLOGON /F >nul 2>&1
)

:: 6. Launch the Agent right now in the background
echo [*] Launching silent background collector...
start "" "%PYTHONW_PATH%" "%AGENT_DIR%osdbx_agent.py"

echo.
echo ======================================================================
echo  [✓] OS-DBX Forensic Collector successfully enrolled!
echo  Endpoint Host ID: %COMPUTERNAME%
echo  Streaming To:     %SERVER_URL%
echo  Status:           Active (Runs silently on boot)
echo  Log File:         %AGENT_DIR%agent.log
echo ======================================================================
echo.
echo To remove the collector when investigation is finished:
echo Double-click uninstall-agent.bat
echo.
pause
