@echo off
title Disable J.A.R.V.I.S. Auto-Start
cd /d "%~dp0"

echo ====================================================
echo      Disable J.A.R.V.I.S. Auto-Start on Boot
echo ====================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File autostart.ps1 -Disable

echo.
pause
