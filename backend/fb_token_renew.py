# -*- coding: utf-8 -*-
"""
fb_token_renew.py — Renovacao automatica do FB Page Token
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Valida o token atual. Se expirado, abre o servidor OAuth para renovar.
Roda diariamente via task agendada (aura-fb-token-health 08:09).

Para token PERMANENTE (nao expira):
  1. Acesse: https://developers.facebook.com/apps/2073471413233500/settings/basic/
  2. Copie "Chave Secreta do App" (App Secret)
  3. Adicione META_APP_SECRET=<valor> no .env
  4. Este script troca automaticamente por token de longa duracao (60 dias → permanente)
"""
import os, sys, pathlib, time, requests, webbrowser, subprocess
from dotenv import load_dotenv, set_key

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = pathlib.Path(__file__).parent
ENV = HERE / ".env"
load_dotenv(ENV, override=True)

TOKEN     = os.getenv("FB_PAGE_TOKEN", "")
PAGE_ID   = os.getenv("FB_PAGE_ID", "1111100822090245")
APP_ID    = os.getenv("META_APP_ID", "2073471413233500")
APP_SECRET = os.getenv("META_APP_SECRET", "")


def validate_token(token: str) -> bool:
    """Retorna True se o token for válido."""
    if not token:
        return False
    try:
        r = requests.get(
            f"https://graph.facebook.com/v20.0/{PAGE_ID}",
            params={"fields": "id,name", "access_token": token},
            timeout=10
        )
        data = r.json()
        return "id" in data and "error" not in data
    except Exception:
        return False


def get_longlife_token(short_token: str) -> str:
    """Troca token curto por token de longa duracao (60 dias) usando app secret."""
    if not APP_SECRET:
        return short_token
    try:
        # Passo 1: user token de longa duracao
        r = requests.get("https://graph.facebook.com/v20.0/oauth/access_token", params={
            "grant_type": "fb_exchange_token",
            "client_id": APP_ID,
            "client_secret": APP_SECRET,
            "fb_exchange_token": short_token,
        }, timeout=15)
        ll_user = r.json().get("access_token", "")
        if not ll_user:
            return short_token

        # Passo 2: page token permanente (nao expira)
        r2 = requests.get(f"https://graph.facebook.com/v20.0/{PAGE_ID}", params={
            "fields": "access_token",
            "access_token": ll_user,
        }, timeout=15)
        page_token = r2.json().get("access_token", "")
        return page_token if page_token else ll_user
    except Exception as e:
        print(f"[WARN] Nao foi possivel obter token longa duracao: {e}")
        return short_token


def save_token(token: str):
    text = ENV.read_text(encoding="utf-8")
    lines = []
    found_fb = found_meta = False
    for line in text.splitlines():
        if line.startswith("FB_PAGE_TOKEN="):
            lines.append(f"FB_PAGE_TOKEN={token}"); found_fb = True
        elif line.startswith("META_ACCESS_TOKEN="):
            lines.append(f"META_ACCESS_TOKEN={token}"); found_meta = True
        else:
            lines.append(line)
    if not found_fb:   lines.append(f"FB_PAGE_TOKEN={token}")
    if not found_meta: lines.append(f"META_ACCESS_TOKEN={token}")
    ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    print("[FB TOKEN] Validando token atual...")
    if validate_token(TOKEN):
        # Tenta upgrade para token longa duracao se tiver secret
        if APP_SECRET and len(TOKEN) < 200:
            print("[FB TOKEN] Upgrade para token permanente...")
            perm = get_longlife_token(TOKEN)
            if perm != TOKEN:
                save_token(perm)
                print(f"[FB TOKEN] Token permanente salvo: {perm[:25]}...")
            else:
                print("[FB TOKEN] Token ja e longa duracao ou upgrade falhou.")
        else:
            print(f"[FB TOKEN] Token valido: {TOKEN[:25]}...")
            if not APP_SECRET:
                print("[DICA] Adicione META_APP_SECRET no .env para tokens permanentes.")
        return True
    else:
        print("[FB TOKEN] Token EXPIRADO ou invalido. Iniciando renovacao...")
        # Abre servidor OAuth
        proc = subprocess.Popen(
            [sys.executable, str(HERE / "get_fb_token.py")],
            cwd=str(HERE)
        )
        print("[FB TOKEN] Servidor OAuth aberto em http://localhost:8765")
        print("[FB TOKEN] Acesse e autorize para renovar o token.")
        proc.wait()
        return False


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)


# ── COMO OBTER TOKEN PERMANENTE (sem expiração) ──────────────────────────────
# Opção A (recomendada): App Secret
#   1. Abra: https://developers.facebook.com/apps/2073471413233500/settings/basic/
#   2. Clique "Mostrar" ao lado de "Chave Secreta do App"
#   3. Copie o valor e adicione ao .env:
#      META_APP_SECRET=<valor>
#   4. Execute: python fb_token_renew.py
#      → Converte automaticamente em token de 60 dias → permanente de página
#
# Opção B (alternativa): Token Longo via Graph Explorer
#   1. Acesse: https://developers.facebook.com/tools/explorer/
#   2. App: "Aura Decore" | User: Página Aura Decore
#   3. Permissões: pages_manage_posts, pages_read_engagement, instagram_content_publish
#   4. Clique "Gerar Token de Acesso"
#   5. No menu "Access Token" → "Open in Access Token Tool"
#   6. Clique "Extend Access Token" → copie o token longo (60 dias)
#   7. Execute: python get_fb_token.py → cole em /save
#      OU adicione diretamente ao .env: FB_PAGE_TOKEN=<token_longo>
#
# Sem secret: token expira em ~1h mas é renovado automaticamente
# pelo task "aura-fb-token-health" que roda às 08:09 todos os dias.
# Para que a renovação funcione sem intervenção, o usuário precisa
# estar logado no Facebook no browser durante a execução da task.
