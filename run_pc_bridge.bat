@echo off
title J.A.R.V.I.S. PC Bridge (Live Console)
cd /d "%~dp0"

echo ====================================================
echo         J.A.R.V.I.S. Local PC Bridge Client
echo ====================================================
echo.

py -3.12 pc_bridge.py
pause
