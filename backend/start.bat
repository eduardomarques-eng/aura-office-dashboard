@echo off
echo ================================================
echo   Aura Decore HQ — Backend + HTTPS + PWA Mobile
echo ================================================
cd /d "%~dp0"

if not exist ".env" (
  echo ERRO: Arquivo .env nao encontrado.
  pause & exit /b 1
)

set PYTHON=C:\Users\erick\AppData\Local\Programs\Python\Python312\python.exe
set SSL_CERT=..\ssl_cert.pem
set SSL_KEY=..\ssl_key.pem

echo [1/3] Verificando dependencias...
%PYTHON% -m pip install -r requirements.txt --quiet 2>nul

echo [2/3] Verificando SSL...
if exist %SSL_CERT% (
  echo   Certificado SSL encontrado
) else (
  echo   Gerando certificado SSL...
  %PYTHON% ..\generate_icons.py 2>nul
)

echo [3/3] Iniciando servidor...
echo.
echo  HTTPS Dashboard:  https://localhost:8000
echo  HTTPS Mobile:     https://localhost:8000/mobile
echo  Rede local:       https://10.0.0.108:8000/mobile
echo.
echo  No celular: abra Chrome, acesse o link da rede local,
echo  aceite o aviso de seguranca, depois instale o app.
echo.

if exist %SSL_CERT% (
  %PYTHON% -m uvicorn main:app --host 0.0.0.0 --port 8000 --ssl-keyfile %SSL_KEY% --ssl-certfile %SSL_CERT%
) else (
  echo  SSL nao disponivel, usando HTTP...
  %PYTHON% -m uvicorn main:app --host 0.0.0.0 --port 8000
)

pause
