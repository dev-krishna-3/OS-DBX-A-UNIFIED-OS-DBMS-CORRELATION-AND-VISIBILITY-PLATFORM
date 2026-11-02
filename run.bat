@echo off
setlocal enabledelayedexpansion
title OS-DBX Platform Launcher

echo ======================================================================
echo          OS-DBX: Unified OS-DBMS Visibility Platform
echo ======================================================================
echo.

:: 1. Check Python
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.12+ from https://python.org or the Microsoft Store.
    pause
    exit /b 1
)

:: 2. Set environment paths
set "ROOT_DIR=%~dp0"
set "PYTHONPATH=%ROOT_DIR%backend;%ROOT_DIR%os_monitor"

:: 3. Check / Activate Virtual Environment
if exist "%ROOT_DIR%backend\venv\Scripts\activate.bat" (
    echo [*] Activating backend virtual environment...
    call "%ROOT_DIR%backend\venv\Scripts\activate.bat"
) else (
    echo [*] Creating virtual environment in backend\venv...
    python -m venv "%ROOT_DIR%backend\venv"
    call "%ROOT_DIR%backend\venv\Scripts\activate.bat"
    echo [*] Installing required packages...
    python -m pip install -r "%ROOT_DIR%backend\requirements.txt"
)

:: 4. Verify Frontend Build exists
if not exist "%ROOT_DIR%frontend\dist\index.html" (
    echo [*] Pre-compiled frontend bundle not found.
    where npm >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        echo [*] Building frontend bundle...
        cd /d "%ROOT_DIR%frontend"
        call npm install
        call npm run build
        cd /d "%ROOT_DIR%"
    ) else (
        echo [!] Warning: Node.js/npm not found and dist bundle missing.
        echo Backend will run in API-only mode at http://127.0.0.1:8000
    )
)

:: 5. Launch Browser after 2 seconds in background
start "" /b powershell -Command "Start-Sleep -Seconds 2; Start-Process 'http://localhost:8000'"

:: 6. Start Unified FastAPI Server (0.0.0.0 allows other PCs on network to connect)
echo.
echo ======================================================================
echo  [✓] OS-DBX Platform is running!
echo  Local URL:    http://localhost:8000
echo  Network URL:  http://%COMPUTERNAME%:8000
echo  API Docs:     http://localhost:8000/docs
echo ======================================================================
echo.
echo Press CTRL+C to stop the platform.
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
