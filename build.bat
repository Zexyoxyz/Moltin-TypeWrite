@echo off
echo ============================================================
echo   Moltin TypeWriter — Build Windows Installer
echo ============================================================

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

echo Installing build dependencies...
.venv\Scripts\pip install -q -r requirements.txt

echo Building executable...
.venv\Scripts\python build.py

echo.
echo Build complete. Check the dist\ folder.
pause
