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
start "Aura Decore — Backend IVE" cmd /k "chcp 65001 > nul && ..\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

ping 127.0.0.1 -n 5 > nul

echo [2/4] Verificando token Meta...
..\.venv\Scripts\python -c "import pathlib; env = {line.split('=', 1)[0].strip(): line.split('=', 1)[1].strip() for line in pathlib.Path('.env').read_text(encoding='utf-8').splitlines() if line.strip() and not line.strip().startswith('#') and '=' in line}; token = env.get('FB_PAGE_TOKEN', ''); print('  [OK] FB_PAGE_TOKEN configurado' if token else '  [!] FB_PAGE_TOKEN vazio - iniciando servidor de autorizacao...')" 2>nul

..\.venv\Scripts\python -c "import pathlib, subprocess; env = {line.split('=', 1)[0].strip(): line.split('=', 1)[1].strip() for line in pathlib.Path('.env').read_text(encoding='utf-8').splitlines() if line.strip() and not line.strip().startswith('#') and '=' in line}; not env.get('FB_PAGE_TOKEN', '') and (subprocess.Popen(['..\\.venv\\Scripts\\python.exe', 'get_fb_token.py'], creationflags=0x10) or True) and print('  Servidor de token iniciado em http://localhost:8765')" 2>nul

ping 127.0.0.1 -n 3 > nul

echo [3/4] Abrindo dashboard principal...
start "" "C:\Users\erick\aura-office-dashboard\index.html"

ping 127.0.0.1 -n 3 > nul

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
