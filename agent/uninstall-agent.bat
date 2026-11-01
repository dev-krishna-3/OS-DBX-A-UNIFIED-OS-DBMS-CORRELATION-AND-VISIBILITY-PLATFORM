@echo off
setlocal enabledelayedexpansion
title OS-DBX Forensic Collector Uninstaller

echo ======================================================================
echo       OS-DBX: Enterprise Endpoint Forensic Agent Uninstaller
echo ======================================================================
echo.

set "AGENT_DIR=%~dp0"
set "TASK_NAME=OSDBX_Forensic_Agent"

:: 1. Terminate background agent process if PID file exists
if exist "%AGENT_DIR%agent.pid" (
    set /p AGENT_PID=<"%AGENT_DIR%agent.pid"
    echo [*] Stopping background collector process (PID !AGENT_PID!)...
    taskkill /F /PID !AGENT_PID! >nul 2>&1
    del /f /q "%AGENT_DIR%agent.pid" >nul 2>&1
)

:: 2. Safety process cleanup
for /f "tokens=2" %%p in ('wmic process where "CommandLine like '%%osdbx_agent.py%%'" get ProcessId 2^>nul ^| findstr [0-9]') do (
    echo [*] Terminating lingering agent process %%p...
    taskkill /F /PID %%p >nul 2>&1
)

:: 3. Remove Windows Scheduled Task
echo [*] Removing auto-start task from Task Scheduler...
schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1

:: 4. Clean up local logs
if exist "%AGENT_DIR%agent.log" (
    del /f /q "%AGENT_DIR%agent.log" >nul 2>&1
)

echo.
echo ======================================================================
echo  [✓] OS-DBX Forensic Collector completely removed from this system!
echo  - Background process terminated
echo  - Auto-start boot task deleted
echo  - Temporary logs and PID files removed
echo  - Zero system footprint remaining
echo ======================================================================
echo.
pause
