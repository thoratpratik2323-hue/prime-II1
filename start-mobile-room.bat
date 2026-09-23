@echo off
chcp 65001 >nul
title PRIME AI - MOBILE VOICE COCKPIT SERVER
cd /d "%~dp0"
echo ==========================================================
echo    PRIME AI :: MOBILE VOICE COCKPIT SERVER
echo ==========================================================
"C:\Users\thora\AppData\Local\Programs\Python\Python312\python.exe" mobile_room_server.py 8765
pause
