@echo off
title PRIME AI :: AUTONOMOUS NEURAL COCKPIT
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
echo Starting Prime AI Neural Cockpit...
"C:\Users\thora\AppData\Local\Programs\Python\Python312\python.exe" prime.py
if errorlevel 1 (
    echo.
    echo Prime AI exited with an error. Press any key to close.
    pause >nul
)
