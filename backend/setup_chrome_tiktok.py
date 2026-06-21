# -*- coding: utf-8 -*-
"""
setup_chrome_tiktok.py — Abre Chrome com perfil limpo para login TikTok (1x)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Usa perfil NOVO (sem crash recovery dialog) — diferente do perfil principal.
Chrome e Edge rodam em paralelo sem conflito.

Uso: python setup_chrome_tiktok.py
"""
import os
import pathlib
import sys
import time
from dotenv import load_dotenv

_ENV = pathlib.Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV, override=True)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

CHROME_PROFILE = str(pathlib.Path(__file__).parent / "tiktok-chrome-profile")
TIKTOK_LOGIN   = "https://www.tiktok.com/login"
TIKTOK_STUDIO  = "https://www.tiktok.com/tiktokstudio/upload"

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


def setup():
    from playwright.sync_api import sync_playwright

    profile_path = pathlib.Path(CHROME_PROFILE)
    profile_path.mkdir(parents=True, exist_ok=True)

    print("\n  Aura Decore — Setup TikTok Chrome")
    print("  ===================================")
    print(f"  Perfil: {CHROME_PROFILE}")
    print("  (Perfil separado — nao afeta seu Chrome principal)\n")
    print("  Abrindo Google Chrome...")

    with sync_playwright() as p:
        try:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=CHROME_PROFILE,
                channel="chrome",
                headless=False,
                args=CHROME_ARGS,
                timeout=30000,
            )
        except Exception as e:
            print(f"\n  ERRO ao abrir Chrome: {e}")
            print("  Tentando Microsoft Edge...")
            try:
                EDGE_PROFILE = str(pathlib.Path(__file__).parent / "tiktok-edge-profile")
                pathlib.Path(EDGE_PROFILE).mkdir(parents=True, exist_ok=True)
                ctx = p.chromium.launch_persistent_context(
                    user_data_dir=EDGE_PROFILE,
                    channel="msedge",
                    headless=False,
                    args=CHROME_ARGS,
                    timeout=30000,
                )
                print("  Edge aberto como fallback.")
            except Exception as e2:
                print(f"\n  ERRO Edge tambem falhou: {e2}")
                return

        pages = ctx.pages
        page = pages[0] if pages else ctx.new_page()

        # Checar se já logado
        try:
            print("  Verificando login no TikTok Studio...")
            page.goto(TIKTOK_STUDIO, wait_until="domcontentloaded", timeout=25000)
            time.sleep(3)
            url = page.url
            body = ""
            try:
                body = page.inner_text("body")
            except Exception:
                pass
            if "tiktokstudio" in url and any(w in body for w in ["Select", "Seleciona", "drag", "arrasta", "upload", "carregar"]):
                print("\n  TikTok ja logado! Studio acessivel.")
                print(f"  Perfil: {CHROME_PROFILE}")
                print("\n  Use: python tiktok_chrome_post.py --video video.mp4 --caption '...'")
                ctx.close()
                return
        except Exception as e:
            print(f"  Aviso ao checar Studio: {e}")

        # Navegar para login
        try:
            page.goto(TIKTOK_LOGIN, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(3000)
            
            # Tenta preencher as credenciais se houver suporte da página e inputs visíveis
            tiktok_email = os.getenv("TIKTOK_EMAIL", "auras.de@gmail.com")
            tiktok_pass = os.getenv("TIKTOK_PASSWORD", "Edu@2020")
            
            # Clicar em "Usar telefone / e-mail / nome de usuário" se estiver na tela de seleção
            try:
                login_methods = page.locator('p:has-text("Use phone / email / username"), p:has-text("Usar telefone/e-mail/nome de usuário")')
                if login_methods.first.is_visible(timeout=3000):
                    login_methods.first.click()
                    page.wait_for_timeout(2000)
            except Exception:
                pass
                
            # Mudar para aba de email/username se necessário
            try:
                email_tab = page.locator('a:has-text("Entrar com e-mail ou nome de usuário"), a:has-text("Log in with email or username")')
                if email_tab.first.is_visible(timeout=2000):
                    email_tab.first.click()
                    page.wait_for_timeout(1000)
            except Exception:
                pass

            # Preencher inputs
            email_input = page.locator('input[name="username"], input[placeholder*="telefone"], input[placeholder*="Email"]').first
            pass_input = page.locator('input[type="password"]').first
            
            if email_input.is_visible(timeout=3000):
                email_input.fill(tiktok_email)
                page.wait_for_timeout(1000)
            if pass_input.is_visible(timeout=3000):
                pass_input.fill(tiktok_pass)
                page.wait_for_timeout(1000)
                
            print(f"  Credenciais do TikTok preenchidas ({tiktok_email}).")
        except Exception as e:
            print(f"  Aviso ao preencher credenciais TikTok: {e}")

        print("\n  FACA LOGIN NO TIKTOK NA JANELA DO CHROME AGORA.")
        print("  Se necessário, resolva o quebra-cabeça (captcha) ou digite o código de verificação.")
        print("  O script detecta o login automaticamente (max 5 min).\n")

        max_wait = 300
        start = time.time()
        logged_in = False

        while time.time() - start < max_wait:
            try:
                url = page.url
                if not url:
                    break
                if "tiktok.com/login" not in url and "tiktok.com" in url:
                    logged_in = True
                    break
                elapsed = int(time.time() - start)
                if elapsed > 0 and elapsed % 30 == 0:
                    print(f"  Aguardando... {elapsed}s")
                time.sleep(2)
            except Exception:
                print("  Chrome fechado antes do login.")
                try:
                    ctx.close()
                except Exception:
                    pass
                return

        if logged_in:
            print(f"\n  Login detectado! ({page.url[:60]})")
            try:
                page.goto(TIKTOK_STUDIO, wait_until="domcontentloaded", timeout=20000)
                time.sleep(2)
                print("\n  Login confirmado! Perfil Chrome salvo.")
            except Exception:
                print("\n  Logado. Perfil salvo.")
            print(f"  Perfil: {CHROME_PROFILE}")
            print("\n  Pronto. Agora use:")
            print("  python tiktok_chrome_post.py --video video.mp4 --caption '...'")
        else:
            print("\n  Timeout. Execute novamente.")

        try:
            ctx.close()
        except Exception:
            pass


if __name__ == "__main__":
    setup()
