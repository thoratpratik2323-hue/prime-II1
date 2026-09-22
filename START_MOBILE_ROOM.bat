@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
title Prime AI - Mobile Voice Cockpit Server [Port 8765]
color 0b
echo ==========================================================
echo     PRIME AI  ::  AUTONOMOUS MOBILE VOICE SERVER
echo       [ Connect Phone / Tablet on Local WiFi ]
echo ==========================================================
echo.
"C:\Users\thora\AppData\Local\Programs\Python\Python312\python.exe" room_server.py
if errorlevel 1 (
    echo.
    echo [ERROR] Mobile room server encountered an error.
    pause
)
pause
