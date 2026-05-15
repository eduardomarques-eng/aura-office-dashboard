@echo off
echo Iniciando AURA decor Backend...
cd /d "%~dp0"

if not exist ".env" (
  echo ERRO: Arquivo .env nao encontrado.
  echo Crie o arquivo .env com: ANTHROPIC_API_KEY=sk-ant-...
  pause
  exit /b 1
)

pip install -r requirements.txt --quiet
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
