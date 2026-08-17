@echo off
title J.A.R.V.I.S. Telegram Bridge
cd /d "%~dp0"
echo ====================================================
echo         J.A.R.V.I.S. Telegram Voice & PC Bridge
echo ====================================================
echo.

if not exist ".env" (
    echo [!] .env file not found. Creating from .env.example...
    copy .env.example .env
    echo Please fill in your TELEGRAM_BOT_TOKEN and GEMINI_API_KEY in .env before running!
    notepad .env
    pause
    exit /b
)

set PYTHON_CMD=py -3.12
where py >nul 2>nul
if %errorlevel% neq 0 (
    set PYTHON_CMD=python
)

echo [*] Starting J.A.R.V.I.S....
%PYTHON_CMD% main.py
pause
