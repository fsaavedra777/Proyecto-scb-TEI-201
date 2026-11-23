@echo off
REM Inicia el sistema SCB: gateway (Arduino -> base de datos) y dashboard.
cd /d "%~dp0"
start "SCB gateway" cmd /k python gateway.py
timeout /t 3 > nul
start "SCB dashboard" cmd /k python -m streamlit run dashboard.py
