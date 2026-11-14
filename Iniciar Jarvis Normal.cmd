@echo off
setlocal
cd /d "%~dp0" || exit /b 1
python -m jarvis.app --open
if errorlevel 1 pause
