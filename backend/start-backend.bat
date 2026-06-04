@echo off
cd /d "C:\Users\erick\aura-office-dashboard\backend"
echo [%date% %time%] Iniciando backend Aura Decore... >> startup.log
python -m uvicorn main:app --host 0.0.0.0 --port 8000 >> backend.log 2>> backend-err.log
