@echo off
chcp 65001 > nul
echo.
echo ===================================================
echo   Aura Decore — Sistema de Agentes
echo   Dashboard de Comandos Executivos
echo ===================================================
echo.

cd /d "C:\Users\erick\aura-office-dashboard\backend"

echo [1/4] Iniciando backend IVE (porta 8000)...
start "Aura Decore — Backend IVE" cmd /k "chcp 65001 > nul && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 4 /nobreak > nul

echo [2/4] Verificando token Meta...
python -c "
import os, pathlib
env = {}
for line in pathlib.Path('.env').read_text(encoding='utf-8').splitlines():
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip()
token = env.get('FB_PAGE_TOKEN', '')
if token:
    print('  [OK] FB_PAGE_TOKEN configurado')
else:
    print('  [!] FB_PAGE_TOKEN vazio - iniciando servidor de autorizacao...')
" 2>nul

python -c "
import os, pathlib
env = {}
for line in pathlib.Path('.env').read_text(encoding='utf-8').splitlines():
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip()
if not env.get('FB_PAGE_TOKEN', ''):
    import subprocess
    subprocess.Popen(['python', 'get_fb_token.py'], creationflags=0x00000010)
    print('  Servidor de token iniciado em http://localhost:8765')
" 2>nul

timeout /t 2 /nobreak > nul

echo [3/4] Abrindo dashboard principal...
start "" "C:\Users\erick\aura-office-dashboard\index.html"

timeout /t 2 /nobreak > nul

echo [4/4] Status do sistema:
echo.
echo   Backend IVE:      http://localhost:8000
echo   Health:           http://localhost:8000/health
echo   Meta^/Social:      http://localhost:8000/meta/social
echo   Windsor:          http://localhost:8000/windsor/status
echo   Token Meta:       http://localhost:8765  (se necessario)
echo.
echo ===================================================
echo   Para ativar Facebook^/Instagram:
echo   1. Acesse http://localhost:8765
echo   2. Siga as instrucoes do Graph Explorer
echo   3. Cole o token e salve
echo   Guia completo: AURA-decor-vault\Setup\meta-facebook-instagram-setup.md
echo ===================================================
echo.
pause
