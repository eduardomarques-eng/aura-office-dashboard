# -*- coding: utf-8 -*-
"""
windsor_shopify_connect.py — Conecta Windsor.ai ao Shopify automaticamente
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Uso:
  python windsor_shopify_connect.py               # abre guia visual no browser
  python windsor_shopify_connect.py <shpat_token> # conecta direto com o token

O token shpat_ pode ser obtido em:
  https://admin.shopify.com/store/10ei3t-sf/settings/apps/development
  → App → Credenciais da API → Revelar token uma vez
"""
import os, sys, pathlib, subprocess, webbrowser, requests
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = pathlib.Path(__file__).parent
ENV  = HERE / ".env"
load_dotenv(ENV, override=True)

WINDSOR_API_KEY = os.getenv("WINDSOR_API_KEY", "3c8626a63471e84bc499e211070c0b63a8c5")
SHOPIFY_DOMAIN  = os.getenv("SHOPIFY_DOMAIN", "10ei3t-sf.myshopify.com")


def validate_shpat(token: str) -> bool:
    """Valida se o token shpat_ funciona na Shopify Admin API."""
    try:
        r = requests.post(
            f"https://{SHOPIFY_DOMAIN}/admin/api/2024-10/graphql.json",
            headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"},
            json={"query": "{ shop { name } }"},
            timeout=10
        )
        return "shop" in r.json().get("data", {})
    except Exception:
        return False


def save_shpat(token: str):
    """Salva o shpat_ no .env."""
    text = ENV.read_text(encoding="utf-8")
    lines = []
    found = False
    for line in text.splitlines():
        if line.startswith("SHOPIFY_ADMIN_API_TOKEN="):
            lines.append(f"SHOPIFY_ADMIN_API_TOKEN={token}")
            found = True
        else:
            lines.append(line)
    if not found:
        lines.append(f"SHOPIFY_ADMIN_API_TOKEN={token}")
    ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[OK] SHOPIFY_ADMIN_API_TOKEN salvo: {token[:20]}...")


def connect_windsor(token: str) -> bool:
    """Conecta Windsor ao Shopify via API Windsor com o shpat_."""
    # Windsor connection endpoint
    endpoints_to_try = [
        f"https://onboard.windsor.ai/token_login?access_token={WINDSOR_API_KEY}&next=/app/shopify",
    ]

    # Try Windsor's internal connector API
    headers = {
        "Authorization": f"Bearer {WINDSOR_API_KEY}",
        "Content-Type": "application/json",
        "X-Windsor-Token": WINDSOR_API_KEY,
    }

    # Payload variations to try
    payloads = [
        {"datasource": "shopify", "credentials": {"shop": SHOPIFY_DOMAIN, "access_token": token}},
        {"connector": "shopify", "shop": SHOPIFY_DOMAIN, "token": token},
        {"type": "shopify", "shop_url": SHOPIFY_DOMAIN, "admin_api_access_token": token},
    ]

    connect_endpoints = [
        "https://onboard.windsor.ai/api/v1/connect",
        "https://onboard.windsor.ai/api/connector/add",
        "https://onboard.windsor.ai/api/shopify/connect",
    ]

    for ep in connect_endpoints:
        for payload in payloads:
            try:
                r = requests.post(ep, headers=headers, json=payload, timeout=8)
                if r.status_code in (200, 201):
                    print(f"[OK] Windsor conectado via {ep}!")
                    return True
            except Exception:
                pass

    # Fallback: abre página do Windsor pré-preenchida
    print("[INFO] API Windsor não encontrada — abrindo página de conexão...")
    webbrowser.open(f"https://onboard.windsor.ai/token_login?access_token={WINDSOR_API_KEY}&next=/app/shopify")
    print(f"\nNo formulário que abriu, preencha:")
    print(f"  Store URL: {SHOPIFY_DOMAIN}")
    print(f"  Admin API Token: {token}")
    return False


def main():
    print("=" * 55)
    print("  Windsor.ai ↔ Shopify — Aura Decore")
    print("=" * 55)

    # Pega token do argumento ou .env
    token = ""
    if len(sys.argv) > 1:
        token = sys.argv[1].strip()
    else:
        token = os.getenv("SHOPIFY_ADMIN_API_TOKEN", "").strip()

    if not token:
        print("\n[INFO] Sem token shpat_. Abrindo guia...")
        print("\nPasso a passo:")
        print("  1. Abra: https://admin.shopify.com/store/10ei3t-sf/settings/apps/development")
        print("  2. Clique no app 'Aura Decore'")
        print("  3. Aba 'Credenciais da API' → botão 'Revelar token uma vez'")
        print("  4. Copie o token shpat_XXXX")
        print("  5. Execute: python windsor_shopify_connect.py shpat_XXXXXXXX")
        webbrowser.open("https://admin.shopify.com/store/10ei3t-sf/settings/apps/development")
        return

    # Valida o token
    print(f"\n[1/3] Validando token: {token[:20]}...")
    if not validate_shpat(token):
        print("[ERRO] Token inválido ou expirado. Verifique e tente novamente.")
        return
    print("[OK] Token válido na Shopify Admin API!")

    # Salva no .env
    print("\n[2/3] Salvando token no .env...")
    save_shpat(token)

    # Conecta Windsor
    print("\n[3/3] Conectando Windsor...")
    ok = connect_windsor(token)
    if ok:
        print("\n[SUCESSO] Windsor conectado ao Shopify!")
    else:
        print("\n[MANUAL] Complete a conexão no formulário Windsor aberto.")
        print(f"  Store URL: {SHOPIFY_DOMAIN}")
        print(f"  Token:     {token}")

    print("=" * 55)


if __name__ == "__main__":
    main()
