@echo off
title Enable J.A.R.V.I.S. Auto-Start on Boot
cd /d "%~dp0"

echo ====================================================
echo      Configure J.A.R.V.I.S. Auto-Start on Boot
echo ====================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File autostart.ps1

echo.
pause
