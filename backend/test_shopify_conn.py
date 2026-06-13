# -*- coding: utf-8 -*-
"""Teste rápido de conexão Shopify com token atkn_"""
import os
import sys
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

load_dotenv()

import httpx

DOMAIN = os.getenv("SHOPIFY_DOMAIN", "10ei3t-sf.myshopify.com")
TOKEN = os.getenv("SHOPIFY_ADMIN_TOKEN", "")

print("=" * 60)
print("  TESTE DE CONEXÃO SHOPIFY")
print("=" * 60)
print(f"  Domínio: {DOMAIN}")
print(f"  Token:   {TOKEN[:20]}...{TOKEN[-8:] if len(TOKEN) > 20 else ''}")
print(f"  Prefixo: {TOKEN[:5] if TOKEN else '(vazio)'}")
print("=" * 60)

# Teste 1: REST API (várias versões)
print("\n[1] Testando REST API (shop.json)...")
for ver in ["2025-01", "2024-10", "2024-07", "2024-04", "2024-01"]:
    try:
        r = httpx.get(
            f"https://{DOMAIN}/admin/api/{ver}/shop.json",
            headers={"X-Shopify-Access-Token": TOKEN},
            timeout=15
        )
        print(f"  API {ver}: HTTP {r.status_code}", end="")
        if r.status_code == 200:
            shop = r.json().get("shop", {})
            print(f" ✅ Loja: {shop.get('name')} | Plano: {shop.get('plan_name')} | Email: {shop.get('email')}")
            break
        else:
            print(f" ❌ {r.text[:150]}")
    except Exception as e:
        print(f" ❌ Erro: {e}")

# Teste 2: GraphQL
print("\n[2] Testando GraphQL API...")
try:
    r = httpx.post(
        f"https://{DOMAIN}/admin/api/2024-10/graphql.json",
        headers={"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"},
        json={"query": "{ shop { name plan { displayName } currencyCode primaryDomain { url } } }"},
        timeout=15
    )
    print(f"  GraphQL: HTTP {r.status_code}", end="")
    if r.status_code == 200:
        data = r.json()
        shop_data = data.get("data", {}).get("shop", {})
        if shop_data:
            print(f" ✅ {shop_data.get('name')} | {shop_data.get('plan',{}).get('displayName')} | {shop_data.get('primaryDomain',{}).get('url')}")
        else:
            errors = data.get("errors", [])
            print(f" ⚠️ Sem dados: {errors}")
    else:
        print(f" ❌ {r.text[:200]}")
except Exception as e:
    print(f" ❌ Erro: {e}")

# Teste 3: Listar produtos
print("\n[3] Testando acesso a produtos...")
try:
    r = httpx.get(
        f"https://{DOMAIN}/admin/api/2024-10/products/count.json",
        headers={"X-Shopify-Access-Token": TOKEN},
        timeout=15
    )
    print(f"  Produtos: HTTP {r.status_code}", end="")
    if r.status_code == 200:
        count = r.json().get("count", 0)
        print(f" ✅ Total: {count} produtos")
    else:
        print(f" ❌ {r.text[:150]}")
except Exception as e:
    print(f" ❌ Erro: {e}")

# Teste 4: Temas
print("\n[4] Testando acesso a temas...")
try:
    r = httpx.get(
        f"https://{DOMAIN}/admin/api/2024-10/themes.json",
        headers={"X-Shopify-Access-Token": TOKEN},
        timeout=15
    )
    print(f"  Temas: HTTP {r.status_code}", end="")
    if r.status_code == 200:
        themes = r.json().get("themes", [])
        for t in themes:
            role = t.get("role", "")
            print(f"\n    - {t.get('name')} [{role}] (ID: {t.get('id')})")
    else:
        print(f" ❌ {r.text[:150]}")
except Exception as e:
    print(f" ❌ Erro: {e}")

print("\n" + "=" * 60)
print("  TESTE CONCLUÍDO")
print("=" * 60)
