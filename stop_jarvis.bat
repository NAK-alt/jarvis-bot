@echo off
title Stop J.A.R.V.I.S.
cd /d "%~dp0"

echo ====================================================
echo             Stopping J.A.R.V.I.S. Bot
echo ====================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File stop.ps1

echo.
timeout /t 3
