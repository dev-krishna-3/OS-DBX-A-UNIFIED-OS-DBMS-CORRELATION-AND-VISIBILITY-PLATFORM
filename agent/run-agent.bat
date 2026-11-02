@echo off
title OS-DBX Forensic Collector Agent
cd /d "%~dp0"

echo ======================================================================
echo           OS-DBX Forensic Endpoint Collector
echo ======================================================================
echo.

set DEFAULT_SERVER=http://10.72.84.192:8000
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

if exist "bin\osdbx-agent.exe" (
    bin\osdbx-agent.exe --server "%SERVER_URL%" --host-id "%HOST_INPUT%"
) else if exist "osdbx-agent.exe" (
    osdbx-agent.exe --server "%SERVER_URL%" --host-id "%HOST_INPUT%"
) else (
    echo [ERROR] osdbx-agent.exe not found in this folder!
)
pause
