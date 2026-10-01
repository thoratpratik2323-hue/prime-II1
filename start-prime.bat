@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Prime AI - Autonomous Neural Cockpit
"C:\Users\thora\AppData\Local\Programs\Python\Python312\python.exe" prime.py --force %*
if errorlevel 1 (
    echo.
    echo [ERROR] Prime AI encountered an issue.
    pause
)
pause
