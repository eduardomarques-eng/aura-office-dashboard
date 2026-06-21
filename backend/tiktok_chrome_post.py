# -*- coding: utf-8 -*-
"""
tiktok_chrome_post.py — Posta vídeo no TikTok @decore.aura via automação Chrome
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Usa Playwright com o perfil Chrome do usuário (cookies de sessão TikTok já ativos).
Mesma abordagem do FB Pessoal via Chrome MCP — sem precisar de API TikTok.

Uso:
  python tiktok_chrome_post.py --video caminho/video.mp4 --caption "texto do post"
  python tiktok_chrome_post.py --video video.mp4 --post-date 2026-06-16   # lê caption do JSON
  python tiktok_chrome_post.py --dry-run --video video.mp4                # sem publicar

Pré-requisitos:
  pip install playwright && playwright install chromium
  Chrome com sessão TikTok ativa (tiktok.com/tiktokstudio/upload acessível)
"""
import os, sys, json, time, argparse, pathlib
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

UPLOAD_URL      = "https://www.tiktok.com/tiktokstudio/upload"
POSTS_DIR       = pathlib.Path(__file__).parent / "social_posts"
CHROME_PROFILE  = str(pathlib.Path(__file__).parent / "tiktok-chrome-profile")
EDGE_PROFILE    = str(pathlib.Path(__file__).parent / "tiktok-edge-profile")

BROWSER_ARGS = [
    "--no-sandbox",
    "--no-first-run",
    "--disable-session-crashed-bubble",
    "--disable-restore-session-state",
    "--disable-blink-features=AutomationControlled",
]

# Seletores TikTok Studio (testados em jun/2026)
SEL_FILE_INPUT  = 'input[type=file][accept*="video"]'
SEL_CAPTION     = '.public-DraftEditor-content, [data-testid="caption-input"], div[contenteditable="true"]'
SEL_POST_BTN    = 'button[data-e2e="post-button"], button:has-text("Publicar"), button:has-text("Post")'
SEL_SUCCESS     = '[data-e2e="upload-success"], .success-state, text=publicado com sucesso'


def carregar_caption_do_json(post_date: str) -> str:
    """Lê a caption TikTok do arquivo JSON gerado pelo social_agent.py."""
    filepath = POSTS_DIR / f"{post_date}.json"
    if not filepath.exists():
        raise FileNotFoundError(f"Post JSON não encontrado: {filepath}")
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("tiktok", data.get("instagram", ""))


def postar_tiktok(video_path: str, caption: str, dry_run: bool = False, no_publish: bool = False) -> dict:
    """Abre Chrome com perfil existente e posta o vídeo no TikTok Studio.

    no_publish=True: faz upload e preenche caption, mas NÃO clica em Publicar
    (deixa o browser aberto para revisão manual). Útil para o primeiro teste.
    """
    from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

    video_path = str(pathlib.Path(video_path).resolve())
    if not pathlib.Path(video_path).exists():
        return {"ok": False, "msg": f"Arquivo não encontrado: {video_path}"}

    if dry_run:
        print(f"\n  [DRY RUN] TikTok Chrome:")
        print(f"  Vídeo: {video_path}")
        print(f"  Caption: {caption[:200]}...")
        return {"ok": True, "msg": "dry-run"}

    print(f"\n  🎵 TikTok Studio — iniciando Chrome...")

    with sync_playwright() as p:
        ctx_obj = None
        using_cdp = False

        # Perfil Chrome dedicado (criado por setup_chrome_tiktok.py — já logado no TikTok)
        chrome_ok = pathlib.Path(CHROME_PROFILE).exists()
        edge_ok   = pathlib.Path(EDGE_PROFILE).exists()

        # 1ª opção: Chrome com perfil TikTok dedicado
        if chrome_ok:
            print(f"  → Usando Chrome + perfil TikTok dedicado...")
            try:
                ctx_obj = p.chromium.launch_persistent_context(
                    user_data_dir=CHROME_PROFILE,
                    channel="chrome",
                    headless=False,
                    args=BROWSER_ARGS,
                    timeout=30000,
                )
            except Exception as e:
                print(f"  ⚠️  Chrome falhou: {e}")
                ctx_obj = None

        # 2ª opção: Edge com perfil TikTok dedicado
        if ctx_obj is None and edge_ok:
            print(f"  → Usando Microsoft Edge + perfil TikTok dedicado...")
            try:
                ctx_obj = p.chromium.launch_persistent_context(
                    user_data_dir=EDGE_PROFILE,
                    channel="msedge",
                    headless=False,
                    args=BROWSER_ARGS,
                    timeout=30000,
                )
            except Exception as e:
                print(f"  ⚠️  Edge falhou: {e}")
                ctx_obj = None

        if ctx_obj is None:
            return {"ok": False, "msg": (
                "Perfil TikTok não encontrado. Execute o setup uma vez:\n\n"
                "  python setup_chrome_tiktok.py\n\n"
                "Isso abre o Chrome para você fazer login no TikTok. Depois, todos os posts são automáticos."
            )}

        pages = ctx_obj.pages
        page = pages[0] if pages else ctx_obj.new_page()

        def _close():
            try:
                if ctx_obj:
                    ctx_obj.close()
            except Exception:
                pass

        try:
            print(f"  → Navegando para {UPLOAD_URL}")
            page.goto(UPLOAD_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)

            content = page.inner_text("body")
            if "Log in" in content or "Iniciar sessão" in content or "Entrar" in content:
                _close()
                return {"ok": False, "msg": "TikTok não está logado no Chrome. Faça login em tiktok.com e tente novamente."}

            print(f"  → Aguardando página de upload...")
            try:
                page.wait_for_selector(SEL_FILE_INPUT, timeout=15000)
            except PwTimeout:
                _close()
                return {"ok": False, "msg": "Página de upload não carregou (timeout). TikTok pode estar com problemas."}

            print(f"  → Enviando vídeo: {pathlib.Path(video_path).name}")
            file_input = page.locator(SEL_FILE_INPUT).first
            file_input.set_input_files(video_path)

            print(f"  → Aguardando upload processar (pode levar 30-120s)...")
            try:
                page.wait_for_selector(
                    SEL_CAPTION + ", textarea, div[contenteditable]",
                    timeout=120000
                )
            except PwTimeout:
                _close()
                return {"ok": False, "msg": "Upload demorou mais de 2 min — verifique o Chrome manualmente"}

            page.wait_for_timeout(2000)

            print(f"  → Preenchendo caption...")
            caption_el = None
            for sel in [SEL_CAPTION, 'div[contenteditable="true"]', "textarea"]:
                try:
                    el = page.locator(sel).first
                    el.wait_for(state="visible", timeout=5000)
                    caption_el = el
                    break
                except Exception:
                    continue

            if caption_el:
                caption_el.click()
                page.keyboard.press("Control+a")
                page.keyboard.type(caption)
            else:
                print(f"  ⚠️  Caption field não encontrado — verifique manualmente")

            page.wait_for_timeout(2000)

            if no_publish:
                print(f"\n  ✅ Upload + caption prontos. NÃO publicado (modo revisão).")
                print(f"  → Revise no Chrome e clique 'Publicar' manualmente se estiver OK.")
                print(f"  → Pressione Enter aqui para fechar o Chrome...")
                try:
                    input()
                except Exception:
                    page.wait_for_timeout(60000)
                _close()
                return {"ok": True, "msg": "Modo revisão — upload pronto, publicação manual"}

            print(f"  → Publicando...")
            posted = False
            for sel in [SEL_POST_BTN, 'button[class*="post"]', 'button[class*="submit"]']:
                try:
                    btn = page.locator(sel).last
                    btn.wait_for(state="visible", timeout=5000)
                    btn.click()
                    posted = True
                    break
                except Exception:
                    continue

            if not posted:
                print(f"  ⚠️  Botão de publicar não encontrado")
                _close()
                return {"ok": False, "msg": "Botão 'Publicar' não encontrado — publicação manual necessária"}

            page.wait_for_timeout(5000)
            final_text = page.inner_text("body")
            _close()
            if any(w in final_text.lower() for w in ["sucesso", "publicado", "success", "posted"]):
                print(f"  ✅ TikTok publicado com sucesso!")
                return {"ok": True, "msg": "Publicado via TikTok Studio"}
            else:
                print(f"  ✅ Post enviado (verificar @decore.aura)")
                return {"ok": True, "msg": "Post enviado — verifique @decore.aura"}

        except Exception as e:
            print(f"  ❌ Erro durante postagem: {e}")
            _close()
            return {"ok": False, "msg": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Posta vídeo no TikTok @decore.aura via Chrome")
    parser.add_argument("--video", required=True, help="Caminho para o arquivo .mp4")
    parser.add_argument("--caption", default="", help="Texto/caption do post TikTok")
    parser.add_argument("--post-date", default="", help="Data do post (YYYY-MM-DD) para ler caption do JSON")
    parser.add_argument("--dry-run", action="store_true", help="Preview sem publicar")
    parser.add_argument("--no-publish", action="store_true", help="Upload+caption mas NÃO publica (revisão manual)")
    args = parser.parse_args()

    caption = args.caption
    if not caption and args.post_date:
        try:
            caption = carregar_caption_do_json(args.post_date)
            print(f"  Caption carregado de social_posts/{args.post_date}.json")
        except FileNotFoundError as e:
            print(f"  ⚠️  {e}")

    if not caption:
        caption = "#AuraDecore #Japandi #DecorTikTok #CasaMinimalista #WabiSabi"
        print(f"  ⚠️  Caption não fornecido — usando hashtags padrão")

    result = postar_tiktok(args.video, caption, dry_run=args.dry_run, no_publish=args.no_publish)

    if result["ok"]:
        print(f"\n  ✅ {result['msg']}")
        sys.exit(0)
    else:
        print(f"\n  ❌ {result['msg']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
