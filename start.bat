@echo off
echo ============================================================
echo   INICIANDO CERVO BOT
echo ============================================================
echo.
echo Verificando configuracion...
python -c "from config import Config; print(f'Testing Mode: {Config.TESTING_MODE}'); print(f'Puerto: {Config.FLASK_PORT}')"
echo.
echo Iniciando servidor Flask...
echo.
python app.py
