@echo off
chcp 65001 >nul
title Aura Decore — Watchdog 24/7

echo.
echo ========================================================
echo      🌿 AURA DECORE — SISTEMA DE AGENTES 24/7
echo      Watchdog inteligente com auto-reinicialização
echo ========================================================
echo.

set BASE=C:\Users\erick\aura-office-dashboard
set PYTHON=%BASE%\.venv\Scripts\python.exe

if not exist "%PYTHON%" (
    set PYTHON=C:\Users\erick\AppData\Local\Programs\Python\Python312\python.exe
)

echo [CHECK] Python: %PYTHON%
echo [CHECK] Base: %BASE%
echo.

set OTEL_SDK_DISABLED=true
set CREWAI_TELEMETRY_OPT_OUT=true
set PYTHONDONTWRITEBYTECODE=1

echo Iniciando Watchdog (monitora Backend + WPPConnect + n8n local)...
echo Logs em: %BASE%\backend\watchdog.log
echo.
echo Pressione Ctrl+C para encerrar.
echo.

cd /d "%BASE%"
"%PYTHON%" watchdog_aura.py
pause
