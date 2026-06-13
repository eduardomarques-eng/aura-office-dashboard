@echo off
chcp 65001 >nul
echo.
echo ============================================================
echo   SHOPIFY TOKEN GENERATOR - Aura Decore
echo   Criando e instalando app via Shopify CLI
echo ============================================================
echo.
echo [PASSO 1] Criando app no Dev Dashboard...
echo (Siga as instrucoes na tela - escolha sua organizacao e nome do app)
echo.

cd /d "C:\Users\erick\aura-office-dashboard\shopify-app"

REM Criar app novo
call npx -y @shopify/cli@latest app init --path "C:\Users\erick\aura-office-dashboard\shopify-app-token" --name "Aura Backend Token"

echo.
echo ============================================================
echo [PASSO 2] Fazendo deploy do app...
echo ============================================================
echo.

cd /d "C:\Users\erick\aura-office-dashboard\shopify-app-token"
call npx -y @shopify/cli@latest app deploy --no-release

echo.
echo ============================================================
echo [PASSO 3] Mostrando credenciais...
echo ============================================================
echo.

call npx -y @shopify/cli@latest app env show

echo.
echo ============================================================
echo   PRONTO! Copie o SHOPIFY_API_SECRET e o access token acima.
echo   Cole no chat do Antigravity para eu salvar no .env
echo ============================================================
echo.
pause
