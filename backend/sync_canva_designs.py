# -*- coding: utf-8 -*-
"""
sync_canva_designs.py — Script para exportar designs do Canva e enviar para o Shopify
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Lê os designs do Canva Pro listados no runbook e faz upload/associação no Shopify.
"""
import os
import sys
import json
import httpx
from dotenv import load_dotenv
from canva_tools import CanvaUploadShopifyTool

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Carregar variáveis do .env
load_dotenv(override=True)

CANVA_API_TOKEN = os.getenv("CANVA_API_TOKEN", "")
SHOPIFY_DOMAIN = os.getenv("SHOPIFY_DOMAIN", "")
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ADMIN_TOKEN", "") or os.getenv("SHOPIFY_ADMIN_API_TOKEN", "")

# Designs listados no Runbook da Frota
CANVA_DESIGNS = [
    {"name": "Post Instagram Vela Âmbar", "id": "DAHJbBgnrbg", "product_handle": "vela-soja-bambu", "alt": "Vela Soja Bambu e Cedro — Aura Decore"},
    {"name": "Thumbnail Vaso Cerâmica", "id": "DAHJbJGwXcg", "product_handle": "vaso-ceramica-wabi-sabi", "alt": "Vaso Cerâmica Wabi-Sabi — Aura Decore"},
    {"name": "Bandeja Madeira Natural", "id": "DAHJnTxG-q8", "product_handle": "bandeja-acacia", "alt": "Bandeja Acácia Minimalista — Aura Decore"},
    {"name": "Difusor Aromático", "id": "DAHJnasHQ4U", "product_handle": "difusor-ambiente", "alt": "Difusor de Ambiente Aura — Aura Decore"},
    {"name": "Pampas Naturais", "id": "DAHJnd0tEP4", "product_handle": "arranjo-pampas", "alt": "Arranjo Pampas e Trigo Seco — Aura Decore"},
    {"name": "Vaso Terracota", "id": "DAHJnWXnljo", "product_handle": "potes-terracota", "alt": "Potes Terracota Rusticos — Aura Decore"},
    {"name": "Vaso Fosco Bege Areia", "id": "DAHJnfB3XK0", "product_handle": "vaso-oval-minimalista", "alt": "Vaso Oval Minimalista — Aura Decore"},
    {"name": "Vela Âmbar Sândalo", "id": "DAHJnUWLHsU", "product_handle": "vela-soja-bambu", "alt": "Vela Artesanal de Soja — Aura Decore"},
    
    # Imagens institucionais/gerais (serão enviadas para a biblioteca de arquivos)
    {"name": "Trust Strip Benefícios", "id": "DAHJbNTe9Vk", "product_handle": None, "alt": "Selos de garantia e suporte — Aura Decore"},
    {"name": "Story Japandi Decoração", "id": "DAHLkTTiKi0", "product_handle": None, "alt": "Ambiente minimalista Japandi — Aura Decore"},
    {"name": "Post Feed Japandi", "id": "DAHLkViUzZs", "product_handle": None, "alt": "Lifestyle minimalista Japandi — Aura Decore"},
    {"name": "Carrossel Vaso Wabi-Sabi", "id": "DAHLujj94Ro", "product_handle": "vaso-ceramica-wabi-sabi", "alt": "Carrossel Vaso Cerâmica — Aura Decore"},
    {"name": "Story Busca Japandi", "id": "DAHLkUoPFEY", "product_handle": None, "alt": "Story busca instagram — @auradecore"},
    {"name": "Logo Eucalipto", "id": "DAHKZsNIBsE", "product_handle": None, "alt": "Logo Eucalipto — Aura Decore"},
    {"name": "Story Coleções Inverno 2026", "id": "DAHLka8m1kQ", "product_handle": None, "alt": "Story coleções inverno — @auradecore"},
    {"name": "Banner Japandi", "id": "DAHJnQS_epE", "product_handle": None, "alt": "Banner Japandi Editorial — Aura Decore"},
    {"name": "Sobre Mim / Institucional", "id": "DAHKZ1HaqBQ", "product_handle": None, "alt": "Sobre Nós — Aura Decore"},
]


def get_product_id_by_handle(handle: str) -> str | None:
    """Busca o ID do produto no Shopify pelo handle."""
    if not handle:
        return None
    try:
        url = f"https://{SHOPIFY_DOMAIN}/admin/api/2025-01/products.json?handle={handle}"
        headers = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}
        r = httpx.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            products = r.json().get("products", [])
            if products:
                return str(products[0]["id"])
    except Exception as e:
        print(f"⚠️ Erro ao buscar ID do produto '{handle}': {e}")
    return None


def run_sync():
    if not CANVA_API_TOKEN:
        print("❌ CANVA_API_TOKEN não configurado no .env. Configure para rodar a sincronização.")
        return
    if not SHOPIFY_DOMAIN or not SHOPIFY_TOKEN:
        print("❌ Credenciais do Shopify incompletas no .env.")
        return

    print("=" * 60)
    print("  INICIANDO SINCRONIZAÇÃO CANVA PRO ➔ SHOPIFY")
    print("=" * 60)
    print(f"  Loja: {SHOPIFY_DOMAIN}")
    print(f"  Total de designs: {len(CANVA_DESIGNS)}")
    print("=" * 60)

    uploader = CanvaUploadShopifyTool()

    for item in CANVA_DESIGNS:
        name = item["name"]
        design_id = item["id"]
        handle = item["product_handle"]
        alt = item["alt"]

        print(f"\n▶ Processando design: '{name}' (ID: {design_id})...")

        product_id = None
        if handle:
            print(f"  • Mapeado para produto: '{handle}'")
            product_id = get_product_id_by_handle(handle)
            if product_id:
                print(f"  • ID do produto encontrado: {product_id}")
            else:
                print(f"  ⚠️ Produto '{handle}' não encontrado no Shopify. Enviando para a biblioteca de arquivos.")

        # Criar input JSON para a tool
        payload = {
            "design_id": design_id,
            "filename": f"aura_{design_id}",
            "alt_text": alt
        }
        if product_id:
            payload["product_id"] = product_id

        # Executar a tool
        try:
            res = uploader._run(json.dumps(payload))
            print(f"  Result: {res}")
        except Exception as e:
            print(f"  ❌ Erro ao enviar design: {e}")

    print("\n" + "=" * 60)
    print("  SINCRONIZAÇÃO CONCLUÍDA")
    print("=" * 60)


if __name__ == "__main__":
    run_sync()
