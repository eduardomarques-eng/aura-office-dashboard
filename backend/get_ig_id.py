# -*- coding: utf-8 -*-
"""
Auto-watcher: assim que FB_PAGE_TOKEN mudar no .env,
busca o IG_USER_ID via Graph API e salva automaticamente.

Uso: python get_ig_id.py
"""
import os
import sys
import time
import httpx
import pathlib
import re

# Force UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ENV_PATH = pathlib.Path(__file__).parent / ".env"

def _read_page_id():
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("FB_PAGE_ID="):
            return line.split("=", 1)[1].strip()
    return ""

PAGE_ID = _read_page_id() or "1111100822090245"

def read_env():
    env = {}
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env

def save_ig_id(ig_id: str):
    text = ENV_PATH.read_text(encoding="utf-8")
    if re.search(r"^IG_USER_ID=", text, re.MULTILINE):
        text = re.sub(r"^IG_USER_ID=.*$", f"IG_USER_ID={ig_id}", text, flags=re.MULTILINE)
    else:
        text += f"\nIG_USER_ID={ig_id}\n"
    # Remove expiry warning comment above FB_PAGE_TOKEN
    text = text.replace(
        "# Token expirou em 27-Mai-2026. Renovar: cd backend && python get_fb_token.py\n", ""
    )
    ENV_PATH.write_text(text, encoding="utf-8")
    print(f"[OK] IG_USER_ID={ig_id} salvo no .env")

def fetch_ig_id(token: str):
    try:
        r = httpx.get(
            f"https://graph.facebook.com/v20.0/{PAGE_ID}",
            params={"fields": "instagram_business_account", "access_token": token},
            timeout=15,
        )
        data = r.json()
        if "error" in data:
            print(f"  Graph API erro: {data['error']['message']}")
            return None
        ig = data.get("instagram_business_account", {})
        return ig.get("id")
    except Exception as e:
        print(f"  Requisicao falhou: {e}")
        return None

def try_fetch_and_save(token: str) -> bool:
    print("[~] Buscando IG_USER_ID na Graph API...")
    ig_id = fetch_ig_id(token)
    if ig_id:
        save_ig_id(ig_id)
        print(f"\n[OK] Concluido!")
        print(f"   FB_PAGE_ID  = {PAGE_ID}")
        print(f"   IG_USER_ID  = {ig_id}")
        print("   Reinicie o backend para ativar.")
        return True
    print("  [!] Nao foi possivel obter o IG_USER_ID.")
    print("      Causa provavel: token sem escopo instagram_basic OU")
    print("      conta do Instagram nao vinculada a pagina Aura Decore.")
    return False

def main():
    watch = "--watch" in sys.argv
    env = read_env()
    if env.get("IG_USER_ID"):
        print(f"[OK] IG_USER_ID ja configurado: {env['IG_USER_ID']}")
        return

    # 1) Tenta com o token atual imediatamente
    token = env.get("FB_PAGE_TOKEN", "")
    if token:
        print(f"[*] Tentando token atual: {token[:20]}...")
        if try_fetch_and_save(token):
            return

    if not watch:
        print("\n[i] Atualize FB_PAGE_TOKEN com escopos instagram_basic +")
        print("    instagram_content_publish e rode novamente este script.")
        print("    (use 'python get_ig_id.py --watch' para monitorar automaticamente)")
        return

    # 2) Modo --watch: aguarda o token mudar
    print("\n[*] Monitorando .env - aguardando novo FB_PAGE_TOKEN...")
    old_token = token
    while True:
        env       = read_env()
        new_token = env.get("FB_PAGE_TOKEN", "")
        if env.get("IG_USER_ID"):
            print(f"[OK] IG_USER_ID ja configurado: {env['IG_USER_ID']}")
            break
        if new_token and new_token != old_token:
            print(f"\n[+] Novo token detectado: {new_token[:20]}...")
            if try_fetch_and_save(new_token):
                break
            old_token = new_token
        time.sleep(3)

if __name__ == "__main__":
    main()
