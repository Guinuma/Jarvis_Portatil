@echo off
setlocal
cd /d "%~dp0" || exit /b 1
python jarvis_app.py --open
if errorlevel 1 pause
