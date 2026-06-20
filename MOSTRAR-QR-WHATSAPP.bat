@echo off
chcp 65001 > nul
echo ===================================================
echo   Aura Decore — Autenticador WhatsApp Business
echo ===================================================
echo.

cd /d "C:\Users\erick\aura-office-dashboard"

if exist wppconnect_qr.png (
    del wppconnect_qr.png
)

echo [1/2] Obtendo o QR Code atualizado do servidor WPPConnect...
.venv\Scripts\python.exe backend\get_wpp_qr.py
echo.

if exist wppconnect_qr.png (
    echo [2/2] Abrindo a imagem do QR Code para escaneamento...
    start wppconnect_qr.png
    echo.
    echo ---------------------------------------------------
    echo Instruções:
    echo 1. Abra o WhatsApp Business no celular da loja.
    echo 2. Vá em Configurações > Aparelhos Conectados > Conectar Aparelho.
    echo 3. Escaneie a imagem que se abriu.
    echo 4. Caso o QR Code expire ou falte, feche a imagem e execute este script novamente!
    echo ---------------------------------------------------
) else (
    echo [!] Não foi possível obter o QR Code.
    echo Verifique se o servidor WPPConnect está rodando em segundo plano.
)
echo.
pause
