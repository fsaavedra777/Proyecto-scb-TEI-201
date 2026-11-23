@echo off
REM Instala lo necesario (una sola vez). Requiere Python 3.10 o superior.
cd /d "%~dp0"
python -m pip install -r requirements.txt
pause
