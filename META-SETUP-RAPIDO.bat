@echo off
chcp 65001 >nul
title META FULL SETUP — Aura Decore

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║       META FULL SETUP — Aura Decore                     ║
echo ║       Abrindo todos os painéis necessários...           ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

echo [1/6] Abrindo Meta Events Manager (pegar Pixel ID + CAPI Token)...
start "" "https://business.facebook.com/events_manager"
timeout /t 2 >nul

echo [2/6] Abrindo Meta Business Settings (pegar Business ID)...
start "" "https://business.facebook.com/settings/info"
timeout /t 2 >nul

echo [3/6] Abrindo Meta App Dashboard (pegar App Secret)...
start "" "https://developers.facebook.com/apps/2073471413233500/settings/basic/"
timeout /t 2 >nul

echo [4/6] Abrindo Shopify - App Facebook e Instagram (configurar Pixel nativo)...
start "" "https://admin.shopify.com/store/10ei3t-sf/apps/facebook"
timeout /t 2 >nul

echo [5/6] Abrindo Shopify - Criar Admin API Token (shpat_)...
start "" "https://admin.shopify.com/store/10ei3t-sf/settings/apps/development"
timeout /t 2 >nul

echo [6/6] Iniciando servidor OAuth para FB Page Token...
start "" cmd /k "cd /d C:\Users\erick\aura-office-dashboard\backend && python get_fb_token.py"
timeout /t 3 >nul

echo.
echo ═══════════════════════════════════════════════════════════
echo  PASSOS RÁPIDOS (10 minutos):
echo ═══════════════════════════════════════════════════════════
echo.
echo  PASSO 1 — Meta Events Manager (aba 1):
echo    • Clique no seu Pixel
echo    • Configurações ^> "Conversions API" ^> "Gerar token"
echo    • Copie: META_PIXEL_ID e META_CAPI_TOKEN
echo.
echo  PASSO 2 — Meta Business Settings (aba 2):
echo    • Copie o "ID do Business Manager"
echo    • Cole em: META_BUSINESS_ID no .env
echo.
echo  PASSO 3 — Meta App (aba 3):
echo    • Clique "Mostrar" no App Secret
echo    • Cole em: META_APP_SECRET no .env
echo.
echo  PASSO 4 — Shopify Facebook app (aba 4):
echo    • Configure o Pixel ID lá (mais fácil!)
echo    • Isso injeta pixel + CAPI automaticamente
echo.
echo  PASSO 5 — Após preencher .env, execute:
echo    cd backend ^&^& python meta_admin_setup.py
echo.
echo ═══════════════════════════════════════════════════════════
echo  .env fica em: C:\Users\erick\aura-office-dashboard\backend\.env
echo ═══════════════════════════════════════════════════════════
echo.
pause
