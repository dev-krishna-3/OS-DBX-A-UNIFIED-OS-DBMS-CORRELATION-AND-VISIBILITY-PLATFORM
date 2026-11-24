@echo off
title OS-DBX Forensic Collector Agent
cd /d "%~dp0"

echo ======================================================================
echo           OS-DBX Forensic Endpoint Collector
echo ======================================================================
echo.

set PYTHON_EXEC=python
if exist "C:\Users\adity\Music\OS-DBX-A-UNIFIED-OS-DBMS-CORRELATION-AND-VISIBILITY-PLATFORM\backend\venv\Scripts\python.exe" (
    set "PYTHON_EXEC=C:\Users\adity\Music\OS-DBX-A-UNIFIED-OS-DBMS-CORRELATION-AND-VISIBILITY-PLATFORM\backend\venv\Scripts\python.exe"
)

set SERVER_URL=https://testing-4bux.onrender.com
set HOST_ID=0cf8e73b-d573-477f-a368-4271f7440450
set API_TOKEN=8xC_xZOr4QpFe0c0ZV1ZD2nwT03FzbHlME166yPU6ULSqyyDtcJo6mc7gv8ADcXx

echo [*] Target Server: %SERVER_URL%
echo [*] Device Host ID: %HOST_ID%
echo [*] Starting Python collector...
echo.

if exist "osdbx_agent.py" (
    "%PYTHON_EXEC%" osdbx_agent.py --server "%SERVER_URL%" --host-id "%HOST_ID%" --token "%API_TOKEN%"
) else if exist "..\osdbx_agent.py" (
    "%PYTHON_EXEC%" ..\osdbx_agent.py --server "%SERVER_URL%" --host-id "%HOST_ID%" --token "%API_TOKEN%"
) else (
    echo [ERROR] osdbx_agent.py not found!
)
pause
