@echo off
REM ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REM setup_chrome_debug.bat — Ativa CDP no Chrome (1x só precisa fazer)
REM ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REM Reinicia o Chrome com --remote-debugging-port=9222
REM Isso permite que o Playwright se conecte ao Chrome já aberto,
REM resolvendo o conflito de perfil ao postar no TikTok.
REM
REM EXECUTE UMA VEZ. Depois, o Chrome sempre inicia com CDP ativo.
REM ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

echo.
echo  Aura Decore — Chrome Debug Setup
echo  Ativando Remote Debugging Port 9222...
echo.

REM Criar entrada no registro para flags permanentes do Chrome
REG ADD "HKCU\Software\Google\Chrome" /v "CommandLineFlagSecurityWarningsEnabled" /t REG_DWORD /d 0 /f >nul 2>&1

REM Fechar Chrome gentilmente (aguarda 3s)
echo  [1/3] Fechando Chrome...
taskkill /IM chrome.exe /F >nul 2>&1
timeout /t 2 /nobreak >nul

REM Localizar chrome.exe
set CHROME_PATH=
for %%P in (
  "%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"
  "%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"
  "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
) do (
  if exist %%P (
    set "CHROME_PATH=%%P"
    goto :found
  )
)
echo  ERRO: Chrome nao encontrado. Instale o Chrome e tente novamente.
pause
exit /b 1

:found
echo  [2/3] Chrome encontrado em: %CHROME_PATH%

REM Reabrir Chrome com remote debugging
echo  [3/3] Reiniciando Chrome com --remote-debugging-port=9222...
start "" %CHROME_PATH% --remote-debugging-port=9222 --restore-last-session

timeout /t 3 /nobreak >nul

REM Verificar se CDP respondeu
curl -s http://localhost:9222/json >nul 2>&1
if %ERRORLEVEL%==0 (
  echo.
  echo  ✅ SUCESSO! Chrome rodando com CDP ativo na porta 9222.
  echo  Agora o TikTok post funciona mesmo com Chrome aberto.
  echo  Use: python social_agent.py --tiktok-video video.mp4
) else (
  echo.
  echo  ⚠️  Chrome iniciado mas CDP ainda nao respondeu.
  echo  Aguarde 10s e teste: curl http://localhost:9222/json
)
echo.
pause
