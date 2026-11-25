@echo off
echo ======================================================================
echo    Building Standalone OS-DBX Forensic Collector (No Python Required)
echo ======================================================================
echo.

python -m pip install --quiet pyinstaller psutil watchdog
python -m PyInstaller --onefile --name osdbx-agent "%~dp0osdbx_agent.py" --distpath "%~dp0bin" --workpath "%~dp0..\build\agent" --specpath "%~dp0..\build\agent"

echo.
echo [*] Standalone binary ready at: %~dp0bin\osdbx-agent.exe
echo [*] You can copy this .exe to any Windows PC without installing Python!
