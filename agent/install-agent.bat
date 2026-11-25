@echo off
setlocal enabledelayedexpansion
title OS-DBX Forensic Collector Installer

echo ======================================================================
echo       OS-DBX: Enterprise Endpoint Forensic Agent Installer
echo ======================================================================
echo.

:: 1. Check Execution Mode (Standalone Binary vs System Python)
set "AGENT_DIR=%~dp0"
set "EXE_PATH=%AGENT_DIR%bin\osdbx-agent.exe"
set "USE_EXE=0"

if exist "%EXE_PATH%" (
    echo [*] Standalone collector binary detected: %EXE_PATH%
    echo [*] No Python or tool installation required on this system.
    set "USE_EXE=1"
) else (
    where python >nul 2>&1
    if !ERRORLEVEL! neq 0 (
        echo [ERROR] Python is not installed on this system, and bin\osdbx-agent.exe was not found.
        echo Either:
        echo   1. Copy the standalone bin\osdbx-agent.exe onto this PC (Recommended - Zero install).
        echo   2. Install Python 3.10+ from https://python.org.
        pause
        exit /b 1
    )
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
if !USE_EXE! equ 0 (
    echo [*] Checking required forensic libraries (psutil, watchdog)...
    python -m pip install --quiet psutil watchdog
)

:: 5. Register Auto-start Task on Windows Boot/Logon
echo [*] Registering startup task in Windows Task Scheduler...
set "TASK_NAME=OSDBX_Forensic_Agent"

if !USE_EXE! equ 1 (
    set "RUN_CMD=\"%EXE_PATH%\""
) else (
    set "PYTHONW_PATH="
    for /f "delims=" %%i in ('where pythonw 2^>nul') do (
        if not defined PYTHONW_PATH set "PYTHONW_PATH=%%i"
    )
    if "%PYTHONW_PATH%"=="" (
        for /f "delims=" %%i in ('where python 2^>nul') do (
            if not defined PYTHONW_PATH set "PYTHONW_PATH=%%~dpi\pythonw.exe"
        )
    )
    set "RUN_CMD=\"!PYTHONW_PATH!\" \"%AGENT_DIR%osdbx_agent.py\""
)

schtasks /Create /TN "%TASK_NAME%" /TR "!RUN_CMD!" /SC ONLOGON /RL HIGHEST /F >nul 2>&1
if !ERRORLEVEL! neq 0 (
    schtasks /Create /TN "%TASK_NAME%" /TR "!RUN_CMD!" /SC ONLOGON /F >nul 2>&1
)

:: 6. Launch the Agent right now in the background
echo [*] Launching background collector...
if !USE_EXE! equ 1 (
    start "" "%EXE_PATH%"
) else (
    start "" "%PYTHONW_PATH%" "%AGENT_DIR%osdbx_agent.py"
)

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
