@echo off
title J.A.R.V.I.S. Client Setup for New Device
cd /d "%~dp0"

echo ====================================================
echo      J.A.R.V.I.S. New Device Setup & Connect
echo ====================================================
echo.

:: 1. Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python is NOT installed on this device!
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure to CHECK the box "Add Python to PATH" during installation.
    echo.
    pause
    exit /b
)

echo [+] Python detected:
python --version
echo.

:: 2. Install required dependencies
echo [+] Installing required Python packages (aiohttp, pyautogui, pillow, mss, pyperclip)...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [!] Error installing packages. Retrying with basic set...
    pip install aiohttp pyautogui pillow mss pyperclip
)

echo.
:: 3. Configure Windows Auto-Start
echo [+] Creating Windows Startup auto-start shortcut...
powershell -NoProfile -ExecutionPolicy Bypass -File autostart.ps1

echo.
:: 4. Start the Bridge in background
echo [+] Starting J.A.R.V.I.S. PC Bridge in persistent background mode...
powershell -NoProfile -ExecutionPolicy Bypass -File start_persistent.ps1

echo.
echo ====================================================
echo ✅ Setup Complete! This device is now linked to J.A.R.V.I.S.!
echo The bridge will now run automatically in the background.
echo ====================================================
echo.
timeout /t 5
