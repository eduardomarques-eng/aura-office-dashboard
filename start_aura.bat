@echo off
chcp 65001 >nul
title Aura Decore HQ - Sistema Completo

echo.
echo ========================================================
echo   AURA DECORE HQ - INICIANDO SISTEMA COMPLETO
echo ========================================================
echo.

set BASE=C:\Users\erick\aura-office-dashboard
set WPP_DIR=C:\Users\erick\wppconnect-server
set PYTHON_VENV=%BASE%\.venv\Scripts\python.exe
set PYTHON_SYS=C:\Users\erick\AppData\Local\Programs\Python\Python312\python.exe

if exist "%PYTHON_VENV%" ( set PYTHON=%PYTHON_VENV% ) else ( set PYTHON=%PYTHON_SYS% )

rem ── Variáveis de ambiente ─────────────────────────────────────────────────────
set OTEL_SDK_DISABLED=true
set CREWAI_TELEMETRY_OPT_OUT=true
set LITELLM_TELEMETRY=false
set PYTHONDONTWRITEBYTECODE=1

rem ── 1. WPPConnect ─────────────────────────────────────────────────────────────
echo [1/3] WPPConnect (WhatsApp Server, porta 21465)...
netstat -ano | findstr :21465 >nul 2>&1
if %errorlevel% neq 0 (
    echo   Iniciando WPPConnect...
    start "WPPConnect Server" /min cmd /c "chcp 65001 >nul && cd /d %WPP_DIR% && npm run start"
    timeout /t 8 /nobreak >nul
    netstat -ano | findstr :21465 >nul 2>&1
    if %errorlevel% equ 0 ( echo   [OK] WPPConnect subiu! ) else ( echo   [AGUARDANDO] WPPConnect iniciando... )
) else (
    echo   [OK] WPPConnect ja esta rodando.
)

rem ── 2. Backend FastAPI ────────────────────────────────────────────────────────
echo [2/3] Backend FastAPI LENA (porta 8000)...
netstat -ano | findstr :8000 >nul 2>&1
if %errorlevel% neq 0 (
    echo   Iniciando Backend...
    start "Backend IVE/LENA" /min cmd /c "chcp 65001 >nul && cd /d %BASE%\backend && set OTEL_SDK_DISABLED=true && set CREWAI_TELEMETRY_OPT_OUT=true && %PYTHON% -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 --log-level warning"
    timeout /t 12 /nobreak >nul
    netstat -ano | findstr :8000 >nul 2>&1
    if %errorlevel% equ 0 ( echo   [OK] Backend subiu! ) else ( echo   [AGUARDANDO] Backend iniciando... )
) else (
    echo   [OK] Backend ja esta rodando.
)

rem ── 3. Watchdog ────────────────────────────────────────────────────────────────
echo [3/3] Watchdog 24/7 (monitor de saude)...
tasklist /FI "IMAGENAME eq python.exe" /FO CSV 2>nul | findstr /I "watchdog" >nul 2>&1
if %errorlevel% neq 0 (
    echo   Iniciando Watchdog...
    start "Watchdog Aura 24h" /min "%PYTHON%" "%BASE%\watchdog_aura.py"
    echo   [OK] Watchdog iniciado em background.
) else (
    echo   [OK] Watchdog ja esta rodando.
)

rem ── Status Final ──────────────────────────────────────────────────────────────
echo.
echo ========================================================
timeout /t 5 /nobreak >nul

echo   VERIFICANDO PORTAS:
netstat -ano | findstr :8000 >nul 2>&1
if %errorlevel% equ 0 ( echo   [UP] Backend IVE/LENA:   http://localhost:8000 ) else ( echo   [DOWN] Backend OFFLINE - verifique logs )
netstat -ano | findstr :21465 >nul 2>&1
if %errorlevel% equ 0 ( echo   [UP] WPPConnect:          http://localhost:21465 ) else ( echo   [DOWN] WPPConnect OFFLINE )
netstat -ano | findstr :5678 >nul 2>&1
if %errorlevel% equ 0 ( echo   [UP] n8n:                http://localhost:5678 ) else ( echo   [INFO] n8n: offline (opcional) )

echo.
echo   Health Check:    http://localhost:8000/health
echo   Webhook LENA:    http://localhost:8000/whatsapp/webhook
echo   Logs Watchdog:   %BASE%\backend\watchdog.log
echo ========================================================
echo.
echo   Sistema pronto! Para testar a LENA, envie uma mensagem
echo   WhatsApp ou execute: python diagnostico_aura.py
echo.
pause
