@echo off
:: ============================================================
::  Moltin TypeWriter — Launcher
::  Always runs from the correct project directory so Python
::  can find all modules (config, services, ui, etc.)
:: ============================================================

:: Move to the directory where this .bat file lives (project root)
cd /d "%~dp0"

:: Check Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.11+ from https://python.org
    pause
    exit /b 1
)

:: Create venv if missing
if not exist ".venv\Scripts\python.exe" (
    echo [Setup] Creating virtual environment...
    python -m venv .venv
    echo [Setup] Installing dependencies ^(first run only^)...
    .venv\Scripts\pip install -q -r requirements.txt
    :: Write the .pth file so any file can be run directly
    for /f "delims=" %%i in ('.venv\Scripts\python.exe -c "import sys; print([p for p in sys.path if chr(115)+chr(105)+chr(116)+chr(101) in p][0])"') do set SITE=%%i
    echo c:\Users\zexyo\Desktop\Moltin TypeWriter> "%SITE%\moltin.pth"
)

:: Launch the app
echo Starting Moltin TypeWriter...
start "" ".venv\Scripts\pythonw.exe" "%~dp0main.py"
