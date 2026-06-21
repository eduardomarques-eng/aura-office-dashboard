# -*- coding: utf-8 -*-
"""
setup_chrome_fb_pessoal.py - Opens Chrome for login on Facebook Personal @auras.decore (1x)
========================================================================================
Uses Playwright to open Chrome in persistent mode.
"""
import os
import pathlib
import sys
import time
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_ENV = pathlib.Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV, override=True)

CHROME_PROFILE = str(pathlib.Path(__file__).parent / "fb-pessoal-chrome-profile")
FB_MOBILE_URL  = "https://m.facebook.com"

CHROME_ARGS = [
    "--no-sandbox",
    "--no-first-run",
    "--disable-session-crashed-bubble",
    "--disable-infobars",
    "--disable-restore-session-state",
    "--hide-crash-restore-bubble",
    "--disable-features=TranslateUI",
    "--disable-blink-features=AutomationControlled",
]

def check_logged_in_state(page):
    """Retorna o estado de login atual no Facebook Mobile: 'login', 'checkpoint', 'logged_in' ou 'unknown'"""
    # 1. Verificar se ha inputs de login (e-mail/senha)
    try:
        if page.locator('input[name="email"], input[name="pass"], button[name="login"]').first.is_visible(timeout=500):
            return "login"
    except Exception:
        pass

    # 2. Verificar se ha elementos de logged_in (composer, menu, etc.) de forma explicita
    try:
        # Procurar por elementos especificos de quem esta logado:
        # - role="textbox" (caixa de texto para escrever post)
        # - aria-label contendo "pensando" ("No que voce esta pensando?")
        # - links contendo logout ou log_out
        # - botao de Menu
        # - link para notificacoes
        # - link para mensagens
        if page.locator('[role="textbox"], [aria-label*="pensando"], a[href*="logout"], a[href*="log_out"], [aria-label*="Menu"], [aria-label*="Página inicial"], [aria-label*="Home"], a[href*="/notifications"]').first.is_visible(timeout=500):
            return "logged_in"
    except Exception:
        pass

    # 3. Verificar se ha elementos explicitos de 2FA / Checkpoint
    url = page.url.lower()
    if "checkpoint" in url or "security_code" in url:
        return "checkpoint"
    try:
        if page.locator('input[name="approvals_code"], button:has-text("Continuar"), button:has-text("Submit Code")').first.is_visible(timeout=500):
            return "checkpoint"
    except Exception:
        pass

    return "unknown"

def setup():
    from playwright.sync_api import sync_playwright

    profile_path = pathlib.Path(CHROME_PROFILE)
    profile_path.mkdir(parents=True, exist_ok=True)

    print("\n  Aura Decore - Setup Facebook Pessoal Chrome")
    print("  ============================================")
    print(f"  Perfil: {CHROME_PROFILE}")
    print("  (Perfil separado - nao afeta seu Chrome principal)\n")
    print("  Abrindo Google Chrome...")

    with sync_playwright() as p:
        try:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=CHROME_PROFILE,
                channel="chrome",
                headless=False,
                args=CHROME_ARGS,
                viewport={"width": 390, "height": 844},  # mobile viewport
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
                timeout=30000,
            )
        except Exception as e:
            print(f"\n  ERRO ao abrir Chrome: {e}")
            print("  Tentando sem especificar channel='chrome'...")
            try:
                ctx = p.chromium.launch_persistent_context(
                    user_data_dir=CHROME_PROFILE,
                    headless=False,
                    args=CHROME_ARGS,
                    viewport={"width": 390, "height": 844},
                    user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
                    timeout=30000,
                )
            except Exception as e2:
                print(f"\n  ERRO Critico: Playwright Chromium tambem falhou: {e2}")
                return

        pages = ctx.pages
        page = pages[0] if pages else ctx.new_page()

        # Checar se ja esta logado
        try:
            print("  Verificando login no Facebook...")
            page.goto(FB_MOBILE_URL, wait_until="domcontentloaded", timeout=25000)
            time.sleep(3)
            
            state = check_logged_in_state(page)
            if state == "logged_in":
                print("\n  Facebook ja logado! Sessao ativa.")
                print(f"  Perfil: {CHROME_PROFILE}")
                print("\n  Pronto. Agora voce pode executar a publicacao:")
                print("  python fb_pessoal_chrome_post.py --caption 'Mensagem de teste' --dry-run")
                ctx.close()
                return
            
            # Forçar navegação direta para m.facebook.com/login se necessário
            if state == "unknown":
                try:
                    page.goto("https://m.facebook.com/login", wait_until="domcontentloaded", timeout=20000)
                    time.sleep(3)
                    state = check_logged_in_state(page)
                except Exception:
                    pass

            # Se nao logado e na tela de login, preencher as credenciais fornecidas
            if state == "login" or page.locator('input[name="email"]').first.is_visible(timeout=3000):
                fb_email = os.getenv("FB_PERSONAL_EMAIL", "auras.de@gmail.com")
                fb_pass = os.getenv("FB_PERSONAL_PASSWORD", "Edu@102030")
                print(f"  Preenchendo credenciais do Facebook ({fb_email})...")
                email_input = page.locator('input[name="email"]').first
                pass_input = page.locator('input[name="pass"]').first
                login_btn = page.locator('button[name="login"]').first
                
                if email_input.is_visible(timeout=3000):
                    email_input.fill(fb_email)
                    time.sleep(1)
                if pass_input.is_visible(timeout=3000):
                    pass_input.fill(fb_pass)
                    time.sleep(1)
                if login_btn.is_visible(timeout=3000):
                    print("  Clicando em entrar...")
                    login_btn.click()
                    time.sleep(5)
        except Exception as e:
            print(f"  Aviso ao checar Facebook: {e}")

        # Garantir que esta no Facebook
        if "facebook.com" not in page.url:
            try:
                page.goto(FB_MOBILE_URL, wait_until="domcontentloaded", timeout=20000)
            except Exception as e:
                print(f"  Aviso ao ir para Facebook: {e}")

        print("\n  FACA LOGIN NO FACEBOOK PESSOAL NA JANELA DO NAVEGADOR QUE SE ABRIU.")
        print("  Caso solicite codigo de autenticacao (2FA), digite diretamente no navegador.")
        print("  O script detectara o login automaticamente quando voce terminar.\n")

        max_wait = 300
        start = time.time()
        logged_in = False
        last_alert_time = 0

        while time.time() - start < max_wait:
            try:
                url = page.url
                if not url:
                    break
                
                state = check_logged_in_state(page)
                
                if state == "logged_in":
                    # Checagem extra de confirmacao
                    time.sleep(2)
                    if check_logged_in_state(page) == "logged_in":
                        logged_in = True
                        break
                elif state == "checkpoint":
                    now = time.time()
                    if now - last_alert_time > 15:
                        print("  [2FA / SECURITY CHECK] Facebook solicitou codigo de autenticacao.")
                        print("  Por favor, digite o codigo de seguranca diretamente na janela do navegador.")
                        last_alert_time = now
                        
                elapsed = int(time.time() - start)
                if elapsed > 0 and elapsed % 30 == 0:
                    print(f"  Aguardando login no navegador... (estado atual: {state})")
                time.sleep(2)
            except Exception as e:
                print(f"  Navegador fechado ou erro na verificacao: {e}")
                break

        if logged_in:
            print(f"\n  Login detectado com sucesso! ({page.url[:60]})")
            print("  Aguardando alguns segundos para sincronizar cookies...")
            time.sleep(5)
            print("\n  Sessao do Facebook Pessoal salva com sucesso!")
            print(f"  Perfil: {CHROME_PROFILE}")
        else:
            print("\n  Nao foi possivel detectar o login de forma automatizada ou houve timeout.")
            print("  Se voce completou o login, os cookies devem ter sido salvos de qualquer forma.")
            print("  Verifique rodando o script de teste.")

        try:
            ctx.close()
        except Exception:
            pass

if __name__ == "__main__":
    setup()
