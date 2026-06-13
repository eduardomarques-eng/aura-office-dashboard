@echo off
chcp 65001 > nul
echo.
echo ===================================================
echo   NEXUS — Mineracao AliExpress / Dropi
echo ===================================================
echo.
cd /d "C:\Users\erick\aura-office-dashboard\backend"
python -u run_mining.py
echo.
echo Mineracao concluida! Resultado em mining_result.md
echo Vault: C:\Users\erick\AURA-decor-vault\Mineracao\
pause
