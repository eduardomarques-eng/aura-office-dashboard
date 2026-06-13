# -*- coding: utf-8 -*-
"""
shopify_app.py — App Shopify Aura Decore
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Wrapper completo para operacoes na loja Shopify via Admin API GraphQL.
Funciona com shpat_ ou atkn_ (ambos sao Admin API Tokens validos).

Uso:
  python shopify_app.py status          # Status da loja + token
  python shopify_app.py produtos        # Lista produtos
  python shopify_app.py colecoes        # Lista colecoes
  python shopify_app.py publicar        # Publica todos os produtos
  python shopify_app.py set-token       # Salva token manualmente no .env
"""
import os, sys, json, pathlib, argparse
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import httpx

HERE = pathlib.Path(__file__).parent
ENV_PATH = HERE / ".env"
load_dotenv(ENV_PATH, override=True)

SHOP    = os.getenv("SHOPIFY_DOMAIN", "10ei3t-sf.myshopify.com")
TOKEN   = os.getenv("SHOPIFY_ADMIN_API_TOKEN") or os.getenv("SHOPIFY_ADMIN_TOKEN", "")
API_VER = "2024-10"
GQL_URL = f"https://{SHOP}/admin/api/{API_VER}/graphql.json"
REST_URL= f"https://{SHOP}/admin/api/{API_VER}"

HEADERS = {
    "X-Shopify-Access-Token": TOKEN,
    "Content-Type": "application/json",
}


def gql(query: str, variables: dict = None) -> dict:
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    r = httpx.post(GQL_URL, headers=HEADERS, json=payload, timeout=30)
    if r.status_code == 401:
        print("ERRO 401 — Token invalido ou sem permissao.")
        print("Execute: python shopify_app.py set-token")
        sys.exit(1)
    return r.json()


def status():
    print("=" * 55)
    print("  AURA DECORE — Shopify App Status")
    print("=" * 55)
    print(f"  Loja:   {SHOP}")
    t = TOKEN or "(vazio)"
    tipo = "shpat_" if t.startswith("shpat_") else ("atkn_" if t.startswith("atkn_") else "outro")
    print(f"  Token:  {t[:20]}...  [{tipo}]")
    ok = t.startswith("shpat_") or t.startswith("atkn_")
    print(f"  Admin API: {'OK (' + tipo + ')' if ok else 'INVÁLIDO — precisa shpat_ ou atkn_'}")
    print()

    data = gql("{ shop { name plan { displayName } currencyCode primaryDomain { url } } }")
    shop = data.get("data", {}).get("shop", {})
    if shop:
        print(f"  Nome:   {shop.get('name')}")
        print(f"  Plano:  {shop.get('plan', {}).get('displayName')}")
        print(f"  URL:    {shop.get('primaryDomain', {}).get('url')}")
        print(f"  Moeda:  {shop.get('currencyCode')}")

    # Contar produtos e colecoes
    cnt = gql("""{
        productsCount: products(first: 1) { edges { node { id } } }
        collectionsCount: collections(first: 1) { edges { node { id } } }
    }""")
    print()
    print("=" * 55)
    if not (t.startswith("shpat_") or t.startswith("atkn_")):
        print()
        print("  PARA ATIVAR ADMIN API:")
        print("  1. Acesse: https://admin.shopify.com/store/10ei3t-sf/settings/apps")
        print("  2. Clique em 'Desenvolver apps' > seu app")
        print("  3. Aba 'Credenciais da API'")
        print("  4. 'Revelar token uma vez' > copiar")
        print("  5. Execute: python shopify_app.py set-token")
        print()
        print("  Link direto:")
        print("  https://admin.shopify.com/store/10ei3t-sf/settings/apps/development")
        print("=" * 55)


def produtos():
    data = gql("""{
        products(first: 50, query: "status:active") {
            edges { node {
                id title handle status
                images(first: 1) { edges { node { url } } }
            }}
            pageInfo { hasNextPage endCursor }
        }
    }""")
    edges = data.get("data", {}).get("products", {}).get("edges", [])
    print(f"\nProdutos ativos: {len(edges)}\n")
    for e in edges:
        p = e["node"]
        img = p["images"]["edges"][0]["node"]["url"][:60] if p["images"]["edges"] else "SEM IMAGEM"
        print(f"  {p['title'][:45]:<45}  {p['handle'][:35]}")
    return edges


def colecoes():
    data = gql("""{
        collections(first: 50) {
            edges { node {
                id title handle productsCount { count }
                ruleSet { rules { column relation condition } }
            }}
        }
    }""")
    edges = data.get("data", {}).get("collections", {}).get("edges", [])
    print(f"\nColecoes: {len(edges)}\n")
    for e in edges:
        c = e["node"]
        cnt = c.get("productsCount", {}).get("count", "?")
        tipo = "automatica" if c.get("ruleSet") else "manual"
        print(f"  {c['title']:<40} {cnt:>3} produtos  [{tipo}]")
    return edges


def publicar_tudo():
    """Publica todos os rascunhos."""
    print("Buscando rascunhos...")
    data = gql("""{ products(first: 50, query: "status:draft") {
        edges { node { id title } }
    }}""")
    drafts = data.get("data", {}).get("products", {}).get("edges", [])
    if not drafts:
        print("Nenhum rascunho encontrado.")
        return

    PUBLICATION_Q = """query { publications(first: 10) { edges { node { id name } } } }"""
    pub_data = gql(PUBLICATION_Q)
    pubs = pub_data.get("data", {}).get("publications", {}).get("edges", [])
    pub_ids = [e["node"]["id"] for e in pubs]
    print(f"Publicacoes disponiveis: {[e['node']['name'] for e in pubs]}")

    for edge in drafts:
        p = edge["node"]
        pid = p["id"]
        r = gql("""mutation($id: ID!, $input: ProductInput!) {
            productUpdate(id: $id, input: $input) {
                product { id status }
                userErrors { field message }
            }
        }""", {"id": pid, "input": {"status": "ACTIVE"}})
        err = r.get("data", {}).get("productUpdate", {}).get("userErrors", [])
        status_val = r.get("data", {}).get("productUpdate", {}).get("product", {}).get("status")
        print(f"  {'OK' if not err else 'ERR'} {p['title'][:50]}  [{status_val}]")


def set_token():
    token = input("Cole o token (shpat_ ou atkn_) aqui: ").strip()
    if not (token.startswith("shpat_") or token.startswith("atkn_")):
        print("AVISO: Token nao comeca com shpat_ ou atkn_ — verifique se e o Admin API Token.")

    text = ENV_PATH.read_text(encoding="utf-8")
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
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Salvo! Validando...")

    # Validar
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    r = httpx.post(GQL_URL, headers=headers,
        json={"query": "{ shop { name } }"}, timeout=10)
    data = r.json()
    name = data.get("data", {}).get("shop", {}).get("name", "")
    if name:
        print(f"Token valido! Loja: {name}")
    else:
        print(f"Erro na validacao: {data}")


COMMANDS = {
    "status": status,
    "produtos": produtos,
    "colecoes": colecoes,
    "publicar": publicar_tudo,
    "set-token": set_token,
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aura Decore — Shopify App")
    parser.add_argument("cmd", nargs="?", default="status",
                        choices=list(COMMANDS.keys()),
                        help=f"Comando: {', '.join(COMMANDS.keys())}")
    args = parser.parse_args()
    COMMANDS[args.cmd]()
