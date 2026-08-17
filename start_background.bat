@echo off
title Start J.A.R.V.I.S. PC Bridge (Background)
cd /d "%~dp0"

echo ====================================================
echo      Starting J.A.R.V.I.S. Local PC Bridge
echo ====================================================
echo.

if not exist ".env" (
    echo [!] .env file not found.
    pause
    exit /b
)

:: Launch pythonw in background (no console window)
start "" pyw -3.12 pc_bridge.py

echo ✅ J.A.R.V.I.S. PC Bridge is now running in the background!
echo Your PC is linked to the 24/7 Railway bot.
echo.
timeout /t 3
