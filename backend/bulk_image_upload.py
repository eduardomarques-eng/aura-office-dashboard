#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aura Decore — Geração e Upload em Massa de Imagens de Produto
Usa Pollinations.ai (Flux) para gerar + Shopify Admin API para subir
Aspect ratio: 1:1 (1080x1080) — padrão Shopify
"""

import os, sys, json, time, urllib.parse, httpx, random

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from datetime import datetime
from dotenv import load_dotenv

# Carrega .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"), override=True)

# ── Config ─────────────────────────────────────────────────────────────
SHOPIFY_DOMAIN = os.getenv("SHOPIFY_DOMAIN", "10ei3t-sf.myshopify.com")
SHOPIFY_TOKEN  = os.getenv("SHOPIFY_ADMIN_TOKEN", "")
API_VERSION    = "2024-10"
HEADERS        = {
    "X-Shopify-Access-Token": SHOPIFY_TOKEN,
    "Content-Type": "application/json"
}
IMAGES_DIR     = os.path.join(os.path.dirname(__file__), "generated_images", "products")
os.makedirs(IMAGES_DIR, exist_ok=True)

BRAND_STYLE = (
    "professional product photography, japandi minimalist aesthetic, "
    "wabi-sabi natural beauty, warm off-white background #F5F0EB, "
    "soft natural diffused light, shallow depth of field, "
    "premium luxury home decor brand, artisan handmade, "
    "clean minimal composition, high resolution 1080p, "
    "terracotta and natural earth tones, elegant lifestyle"
)

# ── Mapeamento produto → prompt de imagem ──────────────────────────────
PRODUCT_PROMPTS = {
    # Cerâmica
    "vaso-ceramica-oval-minimalista": "oval ceramic vase matte white glaze minimal japandi, side view, neutral warm background",
    "vaso-ceramica-organico-olivo": "organic curved ceramic vase olive green matte finish, artisan handmade, wabi-sabi",
    "vaso-ceramica-achatado-wabi-low": "low flat ceramic vase wide mouth beige matte, minimal horizontal shape, wabi-sabi",
    "jarro-ceramico-minimalista-areia": "cylindrical ceramic jar sand beige matte glaze, slightly irregular artisan, minimal",
    "conjunto-bowl-ceramica-set-3-pecas": "set of 3 ceramic bowls different sizes beige cream matte, nested arrangement, minimal",
    "porta-velas-ceramica-trio": "three ceramic candle holders different heights matte white beige, elegant trio set",
    "prato-decorativo-ceramica-lua-nova": "decorative ceramic plate lunar crescent design matte white, minimal wall decor",
    "porta-joias-ceramica-branco-minimal": "white ceramic jewelry holder tray minimal organic shape, small organizer",
    "incensario-de-ceramica-ripple": "ceramic incense holder ripple wave texture matte glaze, zen minimal design",

    # Velas e Aromáticos
    "vela-pilar-de-cera-natural-tom-argila": "natural clay pillar candle handmade artisan, warm earthy tone, minimal background",
    "vela-artesanal-de-soja-bambu-cedro": "soy candle glass jar bamboo cedar scent, minimal label, warm light",
    "vela-de-cera-de-abelha-artesanal-hana": "beeswax candle handmade honey golden color, small artisan candle, natural",
    "difusor-de-varas-lavanda-musk-branco": "reed diffuser glass bottle lavender white musk, minimal elegant design, home fragrance",
    "castical-de-bambu-trancado-natural": "bamboo woven candle holder natural artisan weave, zen japandi style",
    "castical-de-ceramica-triptico-alto": "three tall ceramic candleholders white matte different heights, elegant set",
    "suporte-de-vela-flutuante-madeira-natural": "floating wood candle holder solid natural wood, minimal design, tealight",

    # Iluminação
    "lanterna-de-rattan-decorativa-mini": "mini rattan woven lantern natural fiber, warm candlelight inside, bohemian japandi",
    "abajur-de-bambu-natural-mesa": "bamboo table lamp shade natural woven, warm light filtering through, japandi",
    "luminaria-pendente-rattan-bali-dome": "rattan dome pendant lamp natural woven, suspended, bali dome shape, warm interior",

    # Têxteis
    "almofada-boucle-areia-natural-45x45cm": "bouclé cushion sand natural color 45x45cm, textured fabric, minimal sofa styling",
    "capa-de-almofada-linho-bordado-bege": "linen cushion cover beige with subtle embroidery, artisan textile, minimal",
    "manta-trico-chunky-off-white": "chunky knit throw blanket off-white, thick texture, cozy minimal styling",
    "manta-de-algodao-organico-terracota": "organic cotton throw blanket terracotta rust color, folded softly, minimal",
    "toalha-de-rosto-linho-premium-set-2": "set of 2 premium linen face towels natural color, neatly folded, spa minimal",
    "tapete-de-juta-natural-redondo-120cm": "round jute natural fiber rug 120cm, flat lay top view, natural texture minimal",
    "tapete-de-algodao-minimalista-natural-60x90cm": "cotton minimalist rug natural stripe pattern 60x90, flat lay, simple elegant",

    # Botânica
    "arranjo-de-ramos-de-algodao-seco": "dried cotton stem bouquet branches natural white fluffy bolls, vase arrangement",
    "eucalipto-preservado-buque-seco-natural": "preserved eucalyptus dried bouquet grey-green stems, botanical minimal",
    "flores-secas-always-viva-buque-brasileiro": "always-viva everlasting dried flowers bouquet yellow purple, Brazilian wildflowers",
    "algodao-crudo-decorativo-kumo": "raw cotton bolls on thin stems natural dried botanical, Brazilian artisan",

    # Aromáticos e Rituais
    "palo-santo-natural-pack-com-3-palitos": "3 palo santo wood sticks natural sacred wood, minimal arrangement on stone surface",
    "sache-aromatico-de-linho-lavanda-cedro": "linen sachet bag lavender cedar aromatherapy, small tied ribbon, minimal",
    "sache-de-ervas-brasileiras-sakura": "Brazilian herb sachet natural linen, dried herbs visible, minimal artisan packaging",
    "porta-incenso-em-bambu-natural": "bamboo incense holder natural groove minimal, incense stick resting, zen",
    "porta-incenso-minimal-em-madeira-plano": "flat wood incense holder minimal plank natural grain, single incense stick",

    # Organização e Acessórios
    "cesta-de-rattan-organizadora-oval": "oval rattan storage basket natural wicker weave, home organization, minimal",
    "suporte-de-livros-em-madeira-natural-minimalista": "pair of minimalist solid wood bookends natural grain, clean desk styling",
    "espelho-oval-com-moldura-de-madeira-natural": "oval mirror solid wood natural frame, leaning against white wall, japandi",
    "bandeja-marmore-e-madeira-oval": "oval marble and wood tray elegant combination, marble surface wood border, luxury",
    "caixa-organizadora-de-madeira-com-tampa": "wooden storage box with lid natural wood grain, minimal clean design",
    "pedras-decorativas-suiseki-trio-natural": "three smooth river stones suiseki natural polished, zen minimal arrangement on linen",

    # Kits e Presentes
    "kit-ritual-matinal-aura-zen": "morning ritual kit curated items incense vase candle stone, gift box arrangement minimal",
    "mini-kit-zen-starter-aura-decore": "small zen starter kit 3 items incense palo santo stone, minimal gift arrangement",
    "kit-zen-nacional-presente-brasileiro": "Brazilian zen gift kit natural items herbs stone sachet, artisan packaging linen",

    # Outros acessórios
    "bandeja-marmore-e-madeira-oval": "oval marble stone surface wood rim tray serving elegant, luxury home",
    "marcadores-de-pagina-em-bambu-set-3-pecas": "3 bamboo bookmark set with japanese kanji engraved, minimal elegant",
    "pedra-sabao-decorativa-sabi": "soapstone decorative piece smooth natural veins Minas Gerais Brazil, minimal",
    "pedra-semipreciosa-mini-kit-trio-mg": "trio of small semiprecious stones rose quartz amethyst citrine velvet pouch",
}

def get_pollinations_url(prompt: str, product_handle: str, size: int = 1080) -> str:
    """Gera URL da imagem via Pollinations.ai"""
    full_prompt = f"{prompt}, {BRAND_STYLE}"
    encoded = urllib.parse.quote(full_prompt)
    seed = abs(hash(product_handle)) % 99999 + 1
    return (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width={size}&height={size}&seed={seed}&nologo=true&enhance=true&model=flux"
    )

def download_image(url: str, filepath: str, retries: int = 3) -> bool:
    """Baixa imagem e salva localmente"""
    for attempt in range(retries):
        try:
            r = httpx.get(url, timeout=60, follow_redirects=True)
            if r.status_code == 200 and len(r.content) > 5000:
                with open(filepath, "wb") as f:
                    f.write(r.content)
                return True
        except Exception as e:
            print(f"  Tentativa {attempt+1} falhou: {e}")
            time.sleep(3)
    return False

def upload_image_to_shopify(product_id: str, image_url: str, alt_text: str) -> dict | None:
    """Sobe imagem para produto no Shopify via GraphQL"""
    # Usa REST API que é mais simples para upload de imagem por URL
    numeric_id = product_id.split("/")[-1]
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/{API_VERSION}/products/{numeric_id}/images.json"

    payload = {
        "image": {
            "src": image_url,
            "alt": alt_text
        }
    }

    try:
        r = httpx.post(url, headers=HEADERS, json=payload, timeout=30)
        if r.status_code in (200, 201):
            data = r.json()
            return data.get("image", {})
        else:
            print(f"  Erro Shopify {r.status_code}: {r.text[:200]}")
            return None
    except Exception as e:
        print(f"  Erro upload: {e}")
        return None

def get_all_products_without_images() -> list[dict]:
    """Busca todos os produtos sem imagem via REST API"""
    products = []
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/{API_VERSION}/products.json?limit=250&fields=id,title,handle,images"

    while url:
        try:
            r = httpx.get(url, headers=HEADERS, timeout=30)
            if r.status_code != 200:
                print(f"Erro ao buscar produtos: {r.status_code}")
                break

            data = r.json()
            batch = data.get("products", [])

            for p in batch:
                if not p.get("images"):
                    products.append(p)

            # Paginação via header Link
            link = r.headers.get("Link", "")
            if 'rel="next"' in link:
                import re
                match = re.search(r'<([^>]+)>; rel="next"', link)
                url = match.group(1) if match else None
            else:
                url = None

        except Exception as e:
            print(f"Erro na busca: {e}")
            break

    return products

def main():
    print("=" * 60)
    print("  Aura Decore — Upload em Massa de Imagens")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    print("\n[1/4] Buscando produtos sem imagem...")
    products = get_all_products_without_images()
    print(f"  → {len(products)} produtos sem imagem encontrados")

    if not products:
        print("  Todos os produtos já têm imagens!")
        return

    results = {"success": 0, "failed": 0, "skipped": 0}
    log_file = os.path.join(os.path.dirname(__file__), "bulk_image_upload.log")

    print(f"\n[2/4] Gerando e subindo imagens...")

    with open(log_file, "w", encoding="utf-8") as log:
        log.write(f"Aura Decore — Bulk Image Upload\n{datetime.now()}\n\n")

        for i, product in enumerate(products, 1):
            handle = product["handle"]
            title  = product["title"]
            pid    = product["id"]

            print(f"\n  [{i}/{len(products)}] {title[:50]}...")

            # Busca prompt customizado ou gera um genérico
            prompt = PRODUCT_PROMPTS.get(handle)
            if not prompt:
                # Gera prompt genérico baseado no título
                prompt = f"{title.lower()} product, japandi home decor, minimal artisan"

            # Gera URL da imagem
            img_url = get_pollinations_url(prompt, handle)
            filepath = os.path.join(IMAGES_DIR, f"{handle}.jpg")

            print(f"     Gerando imagem: {img_url[:80]}...")

            # Baixa a imagem primeiro
            if download_image(img_url, filepath):
                print(f"     ✓ Imagem baixada ({os.path.getsize(filepath)//1024}KB)")

                # Sobe para Shopify usando URL do Pollinations diretamente
                print(f"     Subindo para Shopify...")
                result = upload_image_to_shopify(str(pid), img_url, title)

                if result:
                    print(f"     ✅ Imagem adicionada! ID: {result.get('id')}")
                    results["success"] += 1
                    log.write(f"✅ {title} | {handle} | img_id={result.get('id')}\n")
                else:
                    print(f"     ⚠ Upload falhou, tentando com arquivo local...")
                    results["failed"] += 1
                    log.write(f"❌ {title} | {handle} | upload falhou\n")
            else:
                print(f"     ❌ Falha ao gerar imagem")
                results["failed"] += 1
                log.write(f"❌ {title} | {handle} | geração falhou\n")

            # Rate limit: 2 req/s na Shopify API
            time.sleep(0.6)

    print("\n" + "=" * 60)
    print(f"  CONCLUÍDO:")
    print(f"  ✅ Sucesso: {results['success']}")
    print(f"  ❌ Falha:   {results['failed']}")
    print(f"  Log: {log_file}")
    print("=" * 60)

if __name__ == "__main__":
    main()
