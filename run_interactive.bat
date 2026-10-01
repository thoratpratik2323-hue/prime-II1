@echo off
chcp 65001 >nul
cd /d "c:\My Projects\Personal Projects\Prime"
title Prime AI - Autonomous Neural Cockpit
echo ===================================================
echo   Starting Prime AI Autonomous Neural Cockpit...
echo ===================================================
"C:\Users\thora\AppData\Local\Programs\Python\Python312\python.exe" prime.py --force
echo.
echo [Prime AI has terminated with exit code: %ERRORLEVEL%]
pause
