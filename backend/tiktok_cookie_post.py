# -*- coding: utf-8 -*-
"""
tiktok_cookie_post.py — Posta no TikTok extraindo cookies do Chrome em execução
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Solução para quando Chrome já está aberto (Playwright não consegue usar o mesmo perfil).
Copia o banco de cookies do Chrome → decripta via DPAPI+AES-GCM → injeta no Playwright Chromium.

Uso:
  python tiktok_cookie_post.py --video video.mp4 --caption "texto"
  python tiktok_cookie_post.py --video video.mp4 --post-date 2026-06-16
  python tiktok_cookie_post.py --video video.mp4 --dry-run
"""
import os, sys, json, shutil, sqlite3, base64, time, argparse, pathlib, tempfile
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

UPLOAD_URL   = "https://www.tiktok.com/tiktokstudio/upload"
POSTS_DIR    = pathlib.Path(__file__).parent / "social_posts"
CHROME_BASE  = pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data"
COOKIES_SRC  = CHROME_BASE / "Default" / "Network" / "Cookies"
LOCAL_STATE  = CHROME_BASE / "Local State"

SEL_FILE_INPUT = 'input[type=file][accept*="video"]'
SEL_CAPTION    = '.public-DraftEditor-content, [data-testid="caption-input"], div[contenteditable="true"]'
SEL_POST_BTN   = 'button[data-e2e="post-button"], button:has-text("Publicar"), button:has-text("Post")'


def _copy_locked_file(src: pathlib.Path, dst: pathlib.Path) -> None:
    """Copia arquivo bloqueado pelo Chrome usando win32file com FILE_SHARE flags."""
    import win32file, win32con, pywintypes
    GENERIC_READ      = win32con.GENERIC_READ
    FILE_SHARE_ALL    = win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE
    OPEN_EXISTING     = win32con.OPEN_EXISTING
    FILE_ATTR_NORMAL  = win32con.FILE_ATTRIBUTE_NORMAL

    handle = win32file.CreateFile(
        str(src),
        GENERIC_READ,
        FILE_SHARE_ALL,
        None,
        OPEN_EXISTING,
        FILE_ATTR_NORMAL,
        None,
    )
    try:
        data = win32file.ReadFile(handle, src.stat().st_size)[1]
    finally:
        handle.Close()

    dst.write_bytes(data)


def _get_aes_key() -> bytes:
    """Lê e decripta a chave AES do Chrome via DPAPI do Windows."""
    with open(LOCAL_STATE, encoding="utf-8") as f:
        state = json.load(f)
    enc_key_b64 = state["os_crypt"]["encrypted_key"]
    enc_key = base64.b64decode(enc_key_b64)
    # Remove prefixo "DPAPI"
    enc_key = enc_key[5:]
    import win32crypt
    key = win32crypt.CryptUnprotectData(enc_key, None, None, None, 0)[1]
    return key


def _decrypt_cookie_value(enc_value: bytes, key: bytes) -> str:
    """Decripta um valor de cookie Chrome (v10 AES-256-GCM)."""
    if not enc_value:
        return ""
    # Valores v10: prefixo b"v10" + 12 bytes nonce + ciphertext + 16 bytes tag
    if enc_value[:3] == b"v10":
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        nonce = enc_value[3:15]
        ciphertext = enc_value[15:]
        aesgcm = AESGCM(key)
        try:
            return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8", errors="replace")
        except Exception:
            return ""
    # Valores legados (sem criptografia AES)
    try:
        import win32crypt
        return win32crypt.CryptUnprotectData(enc_value, None, None, None, 0)[1].decode("utf-8", errors="replace")
    except Exception:
        return ""


def exportar_cookies_tiktok() -> list[dict]:
    """Copia o banco de cookies do Chrome e extrai os de tiktok.com."""
    if not COOKIES_SRC.exists():
        raise FileNotFoundError(f"Cookies do Chrome não encontrado: {COOKIES_SRC}")

    key = _get_aes_key()

    # Copiar arquivo bloqueado via win32file com flags de compartilhamento
    tmp_dir = pathlib.Path(tempfile.mkdtemp())
    tmp_db  = tmp_dir / "Cookies"
    _copy_locked_file(COOKIES_SRC, tmp_db)
    # Copiar WAL/SHM se existirem (Chrome usa WAL mode)
    for ext in ["-wal", "-shm"]:
        src_ext = COOKIES_SRC.parent / (COOKIES_SRC.name + ext)
        if src_ext.exists():
            try:
                _copy_locked_file(src_ext, tmp_dir / (tmp_db.name + ext))
            except Exception:
                pass

    cookies = []
    conn = sqlite3.connect(str(tmp_db))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT name, encrypted_value, host_key, path, is_secure, is_httponly, "
            "samesite, expires_utc FROM cookies WHERE host_key LIKE '%tiktok.com'"
        ).fetchall()
    finally:
        conn.close()

    for row in rows:
        value = _decrypt_cookie_value(row["encrypted_value"], key)
        if not value:
            continue
        # Converter timestamp Windows (100ns desde 1601) para Unix
        expires = 0
        if row["expires_utc"]:
            expires = (row["expires_utc"] - 11644473600_000_000_0) // 10_000_000
        cookies.append({
            "name":     row["name"],
            "value":    value,
            "domain":   row["host_key"],
            "path":     row["path"],
            "secure":   bool(row["is_secure"]),
            "httpOnly": bool(row["is_httponly"]),
            "sameSite": ["Strict", "Lax", "None"][max(0, min(2, row["samesite"] or 0))],
            "expires":  int(expires) if expires > 0 else -1,
        })

    print(f"  → {len(cookies)} cookies tiktok.com exportados")
    return cookies


def carregar_caption_do_json(post_date: str) -> str:
    filepath = POSTS_DIR / f"{post_date}.json"
    if not filepath.exists():
        raise FileNotFoundError(f"Post JSON não encontrado: {filepath}")
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("tiktok", data.get("instagram", ""))


def postar_tiktok(video_path: str, caption: str, dry_run: bool = False) -> dict:
    """Posta vídeo no TikTok Studio usando Playwright Chromium + cookies do Chrome."""
    from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

    video_path = str(pathlib.Path(video_path).resolve())
    if not pathlib.Path(video_path).exists():
        return {"ok": False, "msg": f"Arquivo não encontrado: {video_path}"}

    if dry_run:
        print(f"\n  [DRY RUN] TikTok Cookie Post:")
        print(f"  Vídeo: {video_path}")
        print(f"  Caption: {caption[:200]}...")
        return {"ok": True, "msg": "dry-run"}

    print(f"\n  🎵 Exportando cookies do Chrome...")
    try:
        cookies = exportar_cookies_tiktok()
    except Exception as e:
        return {"ok": False, "msg": f"Erro ao exportar cookies: {e}"}

    if not cookies:
        return {"ok": False, "msg": "Nenhum cookie TikTok encontrado no Chrome. Faça login em tiktok.com primeiro."}

    print(f"  🚀 Iniciando Playwright Chromium (headless=False)...")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--start-maximized"],
        )
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 800},
        )

        # Injetar cookies
        ctx.add_cookies(cookies)
        page = ctx.new_page()

        try:
            print(f"  → Navegando para {UPLOAD_URL}")
            page.goto(UPLOAD_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)

            content = page.inner_text("body")
            if "Log in" in content or "Iniciar sessão" in content or "Entrar" in content:
                browser.close()
                return {"ok": False, "msg": "Sessão expirada — cookies insuficientes. Faça login manual no Chrome e tente novamente."}

            print(f"  → Aguardando tela de upload...")
            try:
                page.wait_for_selector(SEL_FILE_INPUT, timeout=15000)
            except PwTimeout:
                browser.close()
                return {"ok": False, "msg": "Página de upload não carregou. Verifique se está logado no TikTok."}

            print(f"  → Enviando vídeo: {pathlib.Path(video_path).name}")
            file_input = page.locator(SEL_FILE_INPUT).first
            file_input.set_input_files(video_path)

            print(f"  → Aguardando processamento do upload (até 2 min)...")
            try:
                page.wait_for_selector(
                    SEL_CAPTION + ", textarea, div[contenteditable]",
                    timeout=120000
                )
            except PwTimeout:
                browser.close()
                return {"ok": False, "msg": "Upload demorou mais de 2 min"}

            page.wait_for_timeout(2000)

            print(f"  → Preenchendo caption...")
            for sel in [SEL_CAPTION, 'div[contenteditable="true"]', "textarea"]:
                try:
                    el = page.locator(sel).first
                    el.wait_for(state="visible", timeout=5000)
                    el.click()
                    page.keyboard.press("Control+a")
                    page.keyboard.type(caption)
                    break
                except Exception:
                    continue

            page.wait_for_timeout(2000)

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

            page.wait_for_timeout(5000)

            if not posted:
                print("  ⚠️  Botão Publicar não encontrado")
                browser.close()
                return {"ok": False, "msg": "Botão 'Publicar' não encontrado"}

            final_text = page.inner_text("body")
            browser.close()
            if any(w in final_text.lower() for w in ["sucesso", "publicado", "success", "posted"]):
                print("  ✅ TikTok publicado com sucesso!")
                return {"ok": True, "msg": "Publicado via TikTok Studio"}
            else:
                print("  ✅ Post enviado (verificar @decore.aura)")
                return {"ok": True, "msg": "Post enviado — verifique @decore.aura"}

        except Exception as e:
            print(f"  ❌ Erro: {e}")
            try:
                browser.close()
            except Exception:
                pass
            return {"ok": False, "msg": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Posta vídeo no TikTok via cookies do Chrome")
    parser.add_argument("--video", required=True)
    parser.add_argument("--caption", default="")
    parser.add_argument("--post-date", default="")
    parser.add_argument("--dry-run", action="store_true")
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
        print(f"  ⚠️  Usando hashtags padrão")

    result = postar_tiktok(args.video, caption, dry_run=args.dry_run)

    if result["ok"]:
        print(f"\n  ✅ {result['msg']}")
        sys.exit(0)
    else:
        print(f"\n  ❌ {result['msg']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
