@echo off
REM ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REM setup_tiktok_profile.bat — Cria perfil Chrome dedicado ao TikTok (1x só)
REM ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REM EXECUTE COM O CHROME FECHADO (para ter acesso ao banco de cookies)
REM Copia o perfil Default do Chrome para tiktok-chrome-profile/
REM Depois a automação usa esse perfil separado — nunca conflita com o Chrome principal
REM ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set "SRC=%LOCALAPPDATA%\Google\Chrome\User Data\Default"
set "DST=%~dp0tiktok-chrome-profile\Default"
set "SRC_STATE=%LOCALAPPDATA%\Google\Chrome\User Data\Local State"
set "DST_STATE=%~dp0tiktok-chrome-profile\Local State"

echo.
echo  Aura Decore — TikTok Profile Setup
echo  =====================================
echo.

REM Verificar se Chrome está fechado
tasklist /FI "IMAGENAME eq chrome.exe" 2>NUL | find /I /N "chrome.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo  ERRO: Feche o Chrome antes de executar este script!
    echo  O banco de cookies fica bloqueado enquanto o Chrome esta aberto.
    echo.
    pause
    exit /b 1
)

echo  [1/3] Chrome fechado. Criando pasta do perfil...
if exist "%DST%" (
    rmdir /s /q "%DST%" 2>NUL
)
mkdir "%DST%" 2>NUL
mkdir "%~dp0tiktok-chrome-profile" 2>NUL

echo  [2/3] Copiando perfil Chrome (cookies + sessao TikTok)...
REM Copiar arquivos essenciais para autenticacao
copy /Y "%SRC_STATE%" "%DST_STATE%" >NUL 2>&1
copy /Y "%SRC%\Cookies" "%DST%\Cookies" >NUL 2>&1
copy /Y "%SRC%\Preferences" "%DST%\Preferences" >NUL 2>&1
copy /Y "%SRC%\Secure Preferences" "%DST%\Secure Preferences" >NUL 2>&1
copy /Y "%SRC%\Web Data" "%DST%\Web Data" >NUL 2>&1
copy /Y "%SRC%\Login Data" "%DST%\Login Data" >NUL 2>&1

REM Copiar pasta Network (Cookies modernos - Chrome 96+)
if not exist "%DST%\Network" mkdir "%DST%\Network"
copy /Y "%SRC%\Network\Cookies" "%DST%\Network\Cookies" >NUL 2>&1

echo  [3/3] Verificando...
if exist "%DST%\Network\Cookies" (
    echo.
    echo  SUCESSO! Perfil TikTok criado em:
    echo  %~dp0tiktok-chrome-profile
    echo.
    echo  Agora pode usar com Chrome aberto:
    echo  python social_agent.py --tiktok-video video.mp4
    echo.
    echo  O perfil precisa ser atualizado quando os cookies expirarem.
    echo  Basta fechar o Chrome e rodar este script novamente.
) else (
    echo  AVISO: Cookies nao copiados. Verifique se o Chrome estava fechado.
)
echo.
pause
