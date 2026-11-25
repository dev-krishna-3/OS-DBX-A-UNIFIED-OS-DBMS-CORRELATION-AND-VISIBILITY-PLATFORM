@echo off
title OS-DBX Standalone Forensic Collector
cd /d "%~dp0"
echo ======================================================================
echo           OS-DBX Standalone Forensic Endpoint Collector
echo ======================================================================
echo.
echo [*] Launching osdbx-agent.exe...
echo [*] Live Dashboard: https://testing-sooty-omega.vercel.app/
echo.
osdbx-agent.exe
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Notice: If Windows 11 Smart App Control blocked this binary:
    echo     Open Windows Security -^> App ^& browser control -^> Smart App Control
    echo     and set it to Evaluation or Off, OR use Option 2 (Portable Runner).
    echo.
)
pause
