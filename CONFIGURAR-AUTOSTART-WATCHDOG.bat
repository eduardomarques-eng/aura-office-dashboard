@echo off
chcp 65001 >nul
title Aura Decore - Configurar Inicializacao Automatica

echo.
echo ========================================================
echo   AURA DECORE - Configurar Inicializacao Automatica
echo   O Watchdog vai iniciar junto com o Windows
echo ========================================================
echo.

set BASE=C:\Users\erick\aura-office-dashboard
set PYTHON_VENV=%BASE%\.venv\Scripts\python.exe
set PYTHON_SYS=C:\Users\erick\AppData\Local\Programs\Python\Python312\python.exe

if exist "%PYTHON_VENV%" (
    set PYTHON=%PYTHON_VENV%
) else (
    set PYTHON=%PYTHON_SYS%
)

set WATCHDOG=%BASE%\watchdog_aura.py
set TASK_NAME=AuraDecoreWatchdog

echo [1/4] Verificando privilegios de administrador...
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Este script precisa ser executado como Administrador!
    echo Clique com o botao direito e selecione "Executar como administrador"
    pause
    exit /b 1
)
echo [OK] Privilegios de administrador confirmados.

echo [2/4] Removendo tarefa antiga (se existir)...
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1
echo [OK] Feito.

echo [3/4] Criando tarefa no Agendador de Tarefas do Windows...
schtasks /create ^
    /tn "%TASK_NAME%" ^
    /tr "\"%PYTHON%\" \"%WATCHDOG%\"" ^
    /sc ONLOGON ^
    /ru "%USERNAME%" ^
    /rl HIGHEST ^
    /delay 0000:30 ^
    /f

if %errorlevel% equ 0 (
    echo [OK] Tarefa criada com sucesso!
) else (
    echo [ERRO] Falha ao criar tarefa no agendador.
    echo Tentando metodo alternativo via pasta Startup...
    
    set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
    set SHORTCUT=%STARTUP_DIR%\AuraDecoreWatchdog.bat
    
    echo @echo off > "%SHORTCUT%"
    echo chcp 65001 ^>nul >> "%SHORTCUT%"
    echo cd /d "%BASE%" >> "%SHORTCUT%"
    echo timeout /t 30 /nobreak ^>nul >> "%SHORTCUT%"
    echo start "" /min "%PYTHON%" "%WATCHDOG%" >> "%SHORTCUT%"
    
    echo [OK] Atalho criado em: %SHORTCUT%
)

echo [4/4] Iniciando o Watchdog agora...
start "" /min "%PYTHON%" "%WATCHDOG%"

echo.
echo ========================================================
echo   CONFIGURACAO CONCLUIDA!
echo.
echo   O Watchdog agora:
echo   - Inicia automaticamente com o Windows
echo   - Monitora Backend (porta 8000) e WPPConnect (21465)
echo   - Reinicia qualquer servico que cair
echo   - Logs em: %BASE%\backend\watchdog.log
echo.
echo   Para verificar: Agendador de Tarefas > AuraDecoreWatchdog
echo ========================================================
echo.
pause
