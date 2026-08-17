@echo off
title J.A.R.V.I.S. Status Monitor
cd /d "%~dp0"

echo ====================================================
echo             J.A.R.V.I.S. Bot Status
echo ====================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File status.ps1

echo.
echo ====================================================
pause
