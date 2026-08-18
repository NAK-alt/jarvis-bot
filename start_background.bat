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

:: Launch via WMI persistent PowerShell script
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_persistent.ps1"

echo.
timeout /t 3
