@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
title Prime AI - Autonomous Neural Cockpit [24/7 Voice]
color 0b
echo ==========================================================
echo     PRIME AI  ::  AUTONOMOUS NEURAL COCKPIT
echo       [ Zero GUI - 24/7 Voice Driven - Pure Power ]
echo ==========================================================
echo.
echo Initializing 24/7 Ambient Neural Voice Cockpit...
echo.
"C:\Users\thora\AppData\Local\Programs\Python\Python312\python.exe" voice_assistant.py
if errorlevel 1 (
    echo.
    echo An error occurred while running Prime AI.
    pause
)
pause
