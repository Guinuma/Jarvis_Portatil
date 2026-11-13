@echo off
setlocal
cd /d "%~dp0" || exit /b 1

python --version >nul 2>&1
if errorlevel 1 (
    echo Instala o Python 3 e volta a abrir este ficheiro.
    pause
    exit /b 1
)

if not exist "holo\server.py" (
    echo Falta o H.O.L.O Hands. Executa git submodule update --init nesta pasta.
    pause
    exit /b 1
)

python jarvis_holo.py --open
set "jarvis_exit=%errorlevel%"
if not "%jarvis_exit%"=="0" pause
exit /b %jarvis_exit%
