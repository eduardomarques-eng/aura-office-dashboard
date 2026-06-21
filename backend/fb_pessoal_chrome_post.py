# -*- coding: utf-8 -*-
"""
fb_pessoal_chrome_post.py — Posta no Facebook Pessoal @auras.decore via Chrome
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Usa Playwright com perfil Chrome do usuário (cookies de sessão FB pessoal ativos).
Abordagem idêntica ao tiktok_chrome_post.py — sem precisar de API do Facebook.

Uso:
  python fb_pessoal_chrome_post.py --caption "texto do post" --image-url "https://..."
  python fb_pessoal_chrome_post.py --post-date 2026-06-16   # lê caption do JSON
  python fb_pessoal_chrome_post.py --dry-run --caption "..."  # sem publicar

Pré-requisitos:
  pip install playwright && playwright install chromium
  Chrome com sessão Facebook pessoal ativa (facebook.com logado como @auras.decore)
"""
import os, sys, json, time, argparse, pathlib
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

FB_MOBILE_URL   = "https://m.facebook.com"
POSTS_DIR       = pathlib.Path(__file__).parent / "social_posts"
CHROME_PROFILE  = str(pathlib.Path(__file__).parent / "fb-pessoal-chrome-profile")

BROWSER_ARGS = [
    "--no-sandbox",
    "--no-first-run",
    "--disable-session-crashed-bubble",
    "--disable-restore-session-state",
    "--disable-blink-features=AutomationControlled",
]

# Seletores Facebook Mobile (testados jun/2026)
SEL_COMPOSE     = '[data-testid="status-attachment-mentions-input"], [aria-label*="No que você está pensando"], div[role="textbox"]'
SEL_POST_BTN    = '[data-testid="react-composer-post-button"], button:has-text("Publicar"), button:has-text("Post")'
SEL_PHOTO_BTN   = '[data-testid="photo-video-button"], [aria-label*="foto"], [aria-label*="Foto"]'
SEL_FILE_INPUT  = 'input[type=file][accept*="image"]'


def carregar_caption_do_json(post_date: str) -> str:
    filepath = POSTS_DIR / f"{post_date}-creative.json"
    if not filepath.exists():
        filepath = POSTS_DIR / f"{post_date}.json"
    if not filepath.exists():
        raise FileNotFoundError(f"Post JSON não encontrado: {filepath}")
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)
    captions = data.get("captions", {})
    return captions.get("facebook", data.get("facebook", data.get("instagram", "")))


def postar_fb_pessoal(caption: str, image_url: str = "", image_path: str = "",
                      dry_run: bool = False, no_publish: bool = False) -> dict:
    """Abre Chrome com perfil existente e posta no Facebook pessoal @auras.decore."""
    from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

    if dry_run:
        print(f"\n  [DRY RUN] FB Pessoal Chrome:")
        print(f"  Caption: {caption[:200]}...")
        if image_url:
            print(f"  Imagem URL: {image_url[:80]}...")
        return {"ok": True, "msg": "dry-run"}

    print(f"\n  📘 FB Pessoal — iniciando Chrome...")

    with sync_playwright() as p:
        ctx_obj = None
        using_cdp = False

        chrome_ok = pathlib.Path(CHROME_PROFILE).exists()

        try:
            if chrome_ok:
                print(f"  Abrindo Chrome com perfil: {CHROME_PROFILE}")
                ctx_obj = p.chromium.launch_persistent_context(
                    CHROME_PROFILE,
                    channel="chrome",
                    headless=False,
                    args=BROWSER_ARGS,
                    viewport={"width": 390, "height": 844},  # mobile viewport
                    user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
                    slow_mo=300,
                    ignore_https_errors=True,
                )
                page = ctx_obj.new_page()
            else:
                # CDP fallback — Chrome já aberto com --remote-debugging-port=9223
                try:
                    print("  Tentando CDP (porta 9223)...")
                    ctx_obj = p.chromium.connect_over_cdp("http://localhost:9223")
                    using_cdp = True
                    page = ctx_obj.pages[0] if ctx_obj.pages else ctx_obj.new_page()
                except Exception:
                    return {"ok": False, "msg": f"Perfil não encontrado: {CHROME_PROFILE}. Execute setup_chrome_fb_pessoal.py primeiro."}

            # Navegar para FB Mobile
            print(f"  Navegando para {FB_MOBILE_URL}...")
            page.goto(FB_MOBILE_URL, wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)

            # Verificar login (criterio robusto)
            is_login_el = False
            try:
                is_login_el = page.locator('input[name="email"], input[name="pass"], button[name="login"]').first.is_visible(timeout=3000)
            except Exception:
                pass
            is_login_url = "login" in page.url.lower() or "checkpoint" in page.url.lower()
            if is_login_el or is_login_url or "facebook.com" not in page.url:
                return {"ok": False, "msg": "Nao logado no Facebook. Faca login no Chrome primeiro e salve o perfil."}

            # Clicar na área de composição
            print("  Clicando em 'No que você está pensando?'...")
            compose = page.locator(SEL_COMPOSE)
            compose.first.click(timeout=10000)
            time.sleep(1)

            # Se tiver imagem via URL, usar link compartilhado + caption
            # Se tiver arquivo local, fazer upload
            if image_path and pathlib.Path(image_path).exists():
                try:
                    photo_btn = page.locator(SEL_PHOTO_BTN)
                    photo_btn.first.click(timeout=5000)
                    time.sleep(1)
                    file_input = page.locator(SEL_FILE_INPUT)
                    file_input.set_input_files(image_path, timeout=5000)
                    time.sleep(2)
                except Exception:
                    pass  # Seguir sem imagem se falhar

            # Digitar caption
            print("  Digitando caption...")
            compose_active = page.locator(SEL_COMPOSE)
            compose_active.first.click(timeout=5000)
            page.keyboard.type(caption, delay=30)
            time.sleep(1)

            # Se só tem URL de imagem (sem arquivo local), adicionar ao texto
            if image_url and not image_path:
                page.keyboard.press("End")
                page.keyboard.press("Enter")
                page.keyboard.type(image_url, delay=20)
                time.sleep(2)

            if no_publish:
                print("  [no-publish] Post preenchido — revisar antes de publicar.")
                time.sleep(15)
                return {"ok": True, "msg": "Post pronto para revisão — não publicado"}

            # Clicar em Publicar
            print("  Clicando em Publicar...")
            post_btn = page.locator(SEL_POST_BTN)
            post_btn.first.click(timeout=10000)
            time.sleep(5)

            # Verificar sucesso (URL muda ou aparece feed)
            if "facebook.com" in page.url and "story" in page.url:
                return {"ok": True, "msg": "Publicado no FB Pessoal @auras.decore"}

            # Verificação alternativa: se não houver dialog de erro
            error_visible = page.locator('[role="alertdialog"]').is_visible(timeout=3000)
            if error_visible:
                error_text = page.locator('[role="alertdialog"]').inner_text()
                return {"ok": False, "msg": f"Erro FB: {error_text[:200]}"}

            return {"ok": True, "msg": "Publicado (sem confirmação visual explícita)"}

        except PwTimeout as e:
            return {"ok": False, "msg": f"Timeout: {str(e)[:200]}"}
        except Exception as e:
            return {"ok": False, "msg": str(e)[:300]}
        finally:
            if ctx_obj and not using_cdp:
                try:
                    ctx_obj.close()
                except Exception:
                    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Posta no Facebook Pessoal @auras.decore via Chrome")
    parser.add_argument("--caption",    default="",  help="Texto do post")
    parser.add_argument("--image-url",  default="",  help="URL da imagem para incluir no post")
    parser.add_argument("--image-path", default="",  help="Arquivo local de imagem para upload")
    parser.add_argument("--post-date",  default="",  help="Data YYYY-MM-DD para ler caption do JSON")
    parser.add_argument("--dry-run",    action="store_true", help="Preview sem publicar")
    parser.add_argument("--no-publish", action="store_true", help="Preencher mas não clicar Publicar")
    args = parser.parse_args()

    caption = args.caption
    if not caption and args.post_date:
        caption = carregar_caption_do_json(args.post_date)

    if not caption:
        print("❌ Forneça --caption ou --post-date")
        sys.exit(1)

    result = postar_fb_pessoal(
        caption=caption,
        image_url=args.image_url,
        image_path=args.image_path,
        dry_run=args.dry_run,
        no_publish=args.no_publish,
    )
    icon = "✅" if result["ok"] else "❌"
    print(f"\n{icon} {result['msg']}")
    sys.exit(0 if result["ok"] else 1)
