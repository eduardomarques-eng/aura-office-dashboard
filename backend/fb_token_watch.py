# -*- coding: utf-8 -*-
"""
fb_token_watch.py — Aguarda FB_PAGE_TOKEN aparecer no .env e valida.
Roda após get_fb_token.py. Quando o token é salvo, testa contra a Graph API.
"""
import os, sys, time, pathlib
import httpx

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ENV_PATH = pathlib.Path(__file__).parent / ".env"
GRAPH = "https://graph.facebook.com/v20.0"

def read_env():
    env = {}
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env

def main():
    print("[WATCH] Aguardando autorizacao do Facebook (ate 10 min)...")
    deadline = time.time() + 600
    token = ""
    while time.time() < deadline:
        env = read_env()
        token = env.get("FB_PAGE_TOKEN", "")
        if token and len(token) > 30:
            print(f"\n[WATCH] Token detectado no .env: {token[:25]}...")
            break
        time.sleep(5)

    if not token or len(token) <= 30:
        print("\n[WATCH] Timeout — token nao foi autorizado ainda.")
        print("        Reabra: http://localhost:8765/  e clique 'Autorizar com Facebook'")
        return 1

    # ── Validacao 1: /me ───────────────────────────────────────
    print("\n[1/3] Validando token...")
    r = httpx.get(f"{GRAPH}/me", params={"access_token": token, "fields": "id,name"}, timeout=15)
    me = r.json()
    if "error" in me:
        print(f"   ERRO: {me['error'].get('message')}")
        return 1
    print(f"   OK -> {me.get('name')} (ID: {me.get('id')})")

    # ── Validacao 2: paginas ───────────────────────────────────
    print("\n[2/3] Listando paginas geridas...")
    r2 = httpx.get(f"{GRAPH}/me/accounts",
                   params={"access_token": token, "fields": "id,name,access_token"}, timeout=15)
    pages = r2.json().get("data", [])
    for p in pages:
        print(f"   - {p.get('name')} (ID: {p.get('id')})")

    # ── Validacao 3: Instagram vinculado ───────────────────────
    print("\n[3/3] Verificando Instagram Business...")
    ig_id = read_env().get("IG_USER_ID", "")
    if ig_id:
        r3 = httpx.get(f"{GRAPH}/{ig_id}",
                       params={"access_token": token, "fields": "username,name"}, timeout=15)
        ig = r3.json()
        if "error" in ig:
            print(f"   IG aviso: {ig['error'].get('message')}")
        else:
            print(f"   OK -> @{ig.get('username')} ({ig.get('name')})")

    print("\n" + "=" * 50)
    print("  TOKEN VALIDO E FUNCIONAL!")
    print("  Proximo: python social_agent.py  (publica agora)")
    print("=" * 50)
    return 0

if __name__ == "__main__":
    sys.exit(main())
