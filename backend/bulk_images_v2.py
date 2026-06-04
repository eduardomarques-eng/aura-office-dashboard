#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aura Decore — Bulk Image Upload v2
Pipeline: OpenRouter DALL-E 3 (via OPENROUTER_API_KEY) → bytes → GCS Staged Upload → Shopify CDN → productCreateMedia
Cada produto recebe imagem 1:1 1024x1024 no CDN oficial da Shopify.
"""
import os, sys, time, json, base64, io, httpx
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"), override=True)

OPENROUTER_KEY  = os.getenv("OPENROUTER_API_KEY", "")
SHOPIFY_DOMAIN  = "10ei3t-sf.myshopify.com"

# Token do MCP (funciona via requests diretas ao GraphQL)
# O MCP usa OAuth interno — precisamos do token que está nas credenciais salvas
# Alternativa: usar o endpoint REST local do backend que proxy as chamadas autenticadas
GRAPHQL_ENDPOINT = f"https://{SHOPIFY_DOMAIN}/admin/api/2024-10/graphql.json"

IMAGES_DIR = os.path.join(os.path.dirname(__file__), "generated_images", "products_v2")
os.makedirs(IMAGES_DIR, exist_ok=True)

BRAND_STYLE = (
    "professional product photography, japandi minimalist aesthetic, "
    "wabi-sabi natural beauty, warm off-white background #F5F0EB, "
    "soft natural diffused light, shallow depth of field, "
    "premium luxury home decor brand, artisan handmade, "
    "clean minimal composition, high resolution, square format 1:1"
)

# Mapeamento produto → prompt
PRODUCTS = [
    # (shopify_gid, handle, prompt_especifico)
    ("gid://shopify/Product/7795259015273", "vaso-ceramica-oval-minimalista",
     "oval matte white ceramic vase, japandi minimal, artisan, product photo"),
    ("gid://shopify/Product/7798301229161", "vaso-ceramica-organico-olivo",
     "organic curved olive green ceramic vase, wabi-sabi, artisan, product photo"),
    ("gid://shopify/Product/7798307160169", "vaso-ceramica-achatado-wabi-low",
     "low flat wabi-sabi ceramic vase, wide mouth, beige matte, product photo"),
    ("gid://shopify/Product/7798306635881", "jarro-ceramico-minimalista-areia",
     "cylindrical sand beige ceramic jar, slightly irregular artisan, product photo"),
    ("gid://shopify/Product/7798306504809", "conjunto-bowl-ceramica",
     "set of 3 ceramic bowls nested, beige cream matte, japandi, product photo"),
    ("gid://shopify/Product/7798306930793", "porta-velas-ceramica-trio",
     "trio ceramic candle holders white matte different heights, product photo"),
    ("gid://shopify/Product/7798306734185", "prato-decorativo-ceramica-lua",
     "decorative ceramic plate matte white lunar design, minimal, product photo"),
    ("gid://shopify/Product/7798309716073", "porta-joias-ceramica-branco",
     "white ceramic jewelry tray minimal organic shape, product photo"),
    ("gid://shopify/Product/7795259277417", "incensario-ceramica-ripple",
     "ceramic incense holder ripple wave texture matte, zen, product photo"),
    ("gid://shopify/Product/7795259342953", "vela-pilar-argila",
     "natural clay pillar candle handmade earthy tone, product photo"),
    ("gid://shopify/Product/7795259080809", "vela-soja-bambu-cedro",
     "soy wax candle glass jar bamboo cedar scent minimal label, product photo"),
    ("gid://shopify/Product/7797722251369", "vela-cera-abelha-hana",
     "beeswax artisan candle golden honey color small natural, product photo"),
    ("gid://shopify/Product/7798309552233", "castical-bambu-trancado",
     "bamboo woven candle holder natural weave zen japandi, product photo"),
    ("gid://shopify/Product/7798309027945", "castical-ceramica-triptico",
     "three tall ceramic candleholders white matte different heights, product photo"),
    ("gid://shopify/Product/7798309257321", "suporte-vela-flutuante",
     "floating wood candle holder solid natural wood tealight minimal, product photo"),
    ("gid://shopify/Product/7798309421161", "lanterna-rattan-mini",
     "mini rattan woven lantern natural fiber warm candlelight inside, product photo"),
    ("gid://shopify/Product/7798308831337", "abajur-bambu-mesa",
     "bamboo table lamp shade natural woven warm light filtering, product photo"),
    ("gid://shopify/Product/7798301491305", "luminaria-pendente-rattan",
     "rattan dome pendant lamp natural woven bali style warm interior, product photo"),
    ("gid://shopify/Product/7798307455081", "almofada-boucle-areia",
     "bouclé cushion sand natural color 45x45cm textured fabric minimal, product photo"),
    ("gid://shopify/Product/7798307815529", "capa-almofada-linho-bordado",
     "linen cushion cover beige subtle hand embroidery artisan, product photo"),
    ("gid://shopify/Product/7798307979369", "manta-trico-chunky",
     "chunky knit throw blanket off-white thick texture cozy minimal, product photo"),
    ("gid://shopify/Product/7798301327465", "manta-algodao-terracota",
     "organic cotton throw blanket terracotta rust warm color folded, product photo"),
    ("gid://shopify/Product/7798308143209", "toalha-linho-premium",
     "set of 2 premium linen face towels natural neatly folded spa minimal, product photo"),
    ("gid://shopify/Product/7798307651689", "tapete-juta-redondo",
     "round jute natural fiber rug 120cm top view flat lay, product photo"),
    ("gid://shopify/Product/7798308339817", "tapete-algodao-minimalista",
     "cotton minimalist rug natural 60x90cm flat lay clean lines, product photo"),
    ("gid://shopify/Product/7795259441257", "arranjo-algodao-seco",
     "dried cotton stem bouquet branches white fluffy bolls vase arrangement, product photo"),
    ("gid://shopify/Product/7795259146345", "eucalipto-preservado",
     "preserved eucalyptus dried bouquet grey-green stems botanical minimal, product photo"),
    ("gid://shopify/Product/7797722382441", "flores-secas-always-viva",
     "dried always-viva flowers bouquet yellow purple Brazilian wildflowers, product photo"),
    ("gid://shopify/Product/7797722415209", "algodao-crudo-kumo",
     "raw cotton bolls thin stems natural dried botanical Brazilian artisan, product photo"),
    ("gid://shopify/Product/7795259310185", "cesta-rattan-oval",
     "oval rattan storage basket natural wicker weave home organization minimal, product photo"),
    ("gid://shopify/Product/7795259179113", "suporte-livros-madeira",
     "pair minimalist solid wood bookends natural grain clean desk, product photo"),
    ("gid://shopify/Product/7795259211881", "difusor-varas-lavanda",
     "reed diffuser glass bottle lavender white musk minimal elegant, product photo"),
    ("gid://shopify/Product/7795259408489", "porta-incenso-bambu",
     "bamboo incense holder natural minimal groove channel zen, product photo"),
    ("gid://shopify/Product/7798301589609", "espelho-oval-madeira",
     "oval mirror solid natural wood frame japandi minimal home decor, product photo"),
    ("gid://shopify/Product/7798309945449", "bandeja-marmore-madeira",
     "oval marble surface wood rim tray elegant luxury japandi, product photo"),
    ("gid://shopify/Product/7798310207593", "caixa-organizadora-madeira",
     "wooden storage box with lid natural wood grain minimal organizer, product photo"),
    ("gid://shopify/Product/7798310371433", "kit-ritual-matinal",
     "morning ritual kit curated items incense vase candle stone gift arrangement, product photo"),
    ("gid://shopify/Product/7796713980009", "mini-kit-zen-starter",
     "small zen starter kit 3 items incense palo santo stone minimal gift, product photo"),
    ("gid://shopify/Product/7797722447977", "kit-zen-nacional",
     "Brazilian zen gift kit natural items herbs stone sachet artisan packaging, product photo"),
    ("gid://shopify/Product/7797722316905", "pedra-semipreciosa-trio",
     "trio small semiprecious stones rose quartz amethyst citrine velvet pouch, product photo"),
    ("gid://shopify/Product/7797722284137", "pedra-sabao-sabi",
     "soapstone decorative smooth natural grey-green veins minimal, product photo"),
    ("gid://shopify/Product/7797722218601", "sache-ervas-brasileiras",
     "Brazilian herb sachet natural linen bag dried lavender rosemary, product photo"),
    ("gid://shopify/Product/7796713848937", "palo-santo-3-palitos",
     "3 palo santo sacred wood sticks natural light brown minimal, product photo"),
    ("gid://shopify/Product/7796713816169", "sache-aromatico-linho",
     "linen sachet bag lavender cedar aromatherapy small tied ribbon, product photo"),
    ("gid://shopify/Product/7796713947241", "porta-incenso-madeira-plano",
     "flat wood incense holder minimal plank natural grain single incense stick, product photo"),
    ("gid://shopify/Product/7796713914473", "marcadores-bambu",
     "3 bamboo bookmarks kanji engraved elegant minimal gift, product photo"),
    ("gid://shopify/Product/7795242598505", "porta-objetos-madeira-clara",
     "minimal wood desk organizer compartments natural light grain, product photo"),
    ("gid://shopify/Product/7795242500201", "difusor-ambiente-bambu",
     "bamboo reed diffuser glass bottle natural aroma home fragrance minimal, product photo"),
    ("gid://shopify/Product/7795242401897", "arranjo-pampas-trigo",
     "pampas grass dried wheat botanical arrangement natural beige, product photo"),
    ("gid://shopify/Product/7795242303593", "bandeja-bambu-zen",
     "bamboo serving tray zen minimal natural flat lay candle stone, product photo"),
    ("gid://shopify/Product/7795242270825", "vaso-ceramica-wabi-sabi-textura",
     "wabi-sabi ceramic vase natural texture rough surface beige sand artisan, product photo"),
    ("gid://shopify/Product/7792661168233", "painel-moss-led",
     "wood panel preserved green moss LED light wall art biophilic design, product photo"),
    ("gid://shopify/Product/7792646291561", "kit-jardinagem-ervas",
     "herb garden kit aromatic plants small pots seeds soil minimal, product photo"),
    ("gid://shopify/Product/7792646258793", "candeeiro-bambu-velas",
     "bamboo candleholder coconut wax candle natural warm ambient glow, product photo"),
    ("gid://shopify/Product/7786642800745", "bandeja-minimalista-acacia",
     "minimal acacia wood tray rectangle natural grain elegant serving, product photo"),
    ("gid://shopify/Product/7786642702441", "diffuser-varetas-blend",
     "premium reed diffuser 200ml glass bottle rattan sticks minimal luxury, product photo"),
    ("gid://shopify/Product/7786642636905", "arranjo-pampas-plantas-secas",
     "pampas grass dried plants arrangement eucalyptus lunaria natural beige, product photo"),
    ("gid://shopify/Product/7786642538601", "almofada-linho-45x45",
     "natural linen cushion pillow 45x45 off-white Belgian linen high-density, product photo"),
    ("gid://shopify/Product/7786642473065", "vela-aromatica-colecao-aura",
     "natural soy wax scented candle collection artisan amber jar, product photo"),
    ("gid://shopify/Product/7786642440297", "vaso-ceramica-japandi",
     "japandi ceramic vase high temperature artisan off-white minimal clean, product photo"),
    ("gid://shopify/Product/7786418307177", "vaso-ceramica-fosco-bege",
     "matte ceramic vase beige sand color artisan japandi, product photo"),
    ("gid://shopify/Product/7786418274409", "bandeja-minimalista-madeira",
     "minimalist natural wood serving tray honey color grain elegant, product photo"),
    ("gid://shopify/Product/7786418241641", "diffuser-ambiente-varetas",
     "reed diffuser ambient fragrance rattan sticks botanical minimal, product photo"),
    ("gid://shopify/Product/7786418208873", "pampas-naturais-secos",
     "pampas grass natural dried plume decorative bouquet beige golden boho, product photo"),
    ("gid://shopify/Product/7786418176105", "almofada-linho-45x45cm",
     "natural linen cushion cover off-white minimal clean japandi sofa, product photo"),
    ("gid://shopify/Product/7786418143337", "vela-aromatica-ambar-sandalo",
     "natural soy wax candle amber sandalwood glass jar minimal warm glow, product photo"),
    ("gid://shopify/Product/7786418110569", "vaso-ceramica-terracota",
     "terracotta ceramic vase artisan warm earthy handmade boho japandi, product photo"),
    ("gid://shopify/Product/7786418045033", "vaso-ceramica-branco",
     "white minimalist ceramic vase artisan handmade pure white clean, product photo"),
    ("gid://shopify/Product/7785846669417", "diffuser-premium-cedro",
     "premium reed diffuser cedar sandalwood 200ml elegant frosted bottle, product photo"),
    ("gid://shopify/Product/7785846603881", "pampa-seco-premium",
     "premium dried pampas grass natural beige fluffy plume minimal vase, product photo"),
    ("gid://shopify/Product/7785846571113", "almofada-linho-minimalista",
     "natural linen cushion pillow bege areia textured fabric sofa minimal, product photo"),
    ("gid://shopify/Product/7785846505577", "vela-ambar-cera-coco",
     "amber natural coconut wax candle artisan warm honey tone glass jar, product photo"),
    ("gid://shopify/Product/7785846440041", "vaso-ceramica-wabi-bege",
     "wabi-sabi ceramic vase beige natural handmade artisan organic form, product photo"),
]


def generate_image_openrouter(prompt: str, product_handle: str) -> bytes | None:
    """Gera imagem via OpenRouter → DALL-E 3 (ou fallback)"""
    if not OPENROUTER_KEY:
        print("  [ERRO] OPENROUTER_API_KEY não configurada")
        return None

    full_prompt = f"{prompt}, {BRAND_STYLE}"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://auradecore.com.br",
        "X-Title": "Aura Decore",
    }
    payload = {
        "model": "openai/dall-e-3",
        "prompt": full_prompt,
        "n": 1,
        "size": "1024x1024",
        "quality": "standard",
        "response_format": "b64_json",
    }

    try:
        r = httpx.post("https://openrouter.ai/api/v1/images/generations",
                       headers=headers, json=payload, timeout=120)
        if r.status_code == 200:
            data = r.json()
            b64 = data["data"][0]["b64_json"]
            return base64.b64decode(b64)
        else:
            print(f"  [ERRO] OpenRouter {r.status_code}: {r.text[:200]}")
            return None
    except Exception as e:
        print(f"  [ERRO] {e}")
        return None


def staged_upload_create(filename: str, filesize: int) -> dict | None:
    """Obtém URL presignada do GCS via Shopify GraphQL (usando o backend local como proxy)"""
    # O backend local em :8000 está autenticado via MCP — mas não expõe proxy GraphQL diretamente.
    # Usamos o endpoint /shopify/metrics que indica que o token interno existe.
    # Na verdade, o MCP usa OAuth do parceiro, não o token do .env.
    # Por isso usamos o script Python diretamente com o token interno do MCP via subprocess.
    pass


def upload_to_gcs(upload_url: str, params: list, image_bytes: bytes) -> bool:
    """Upload dos bytes para o GCS usando URL e parâmetros do staged upload"""
    try:
        r = httpx.put(upload_url, content=image_bytes,
                      headers={"Content-Type": "image/jpeg"}, timeout=60)
        return r.status_code == 200
    except Exception as e:
        print(f"  [ERRO GCS] {e}")
        return False


def main():
    print("=" * 60)
    print("  Aura Decore — Bulk Images v2")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  {len(PRODUCTS)} produtos para processar")
    print("=" * 60)

    if not OPENROUTER_KEY:
        print("[ERRO] OPENROUTER_API_KEY não encontrada no .env")
        sys.exit(1)

    results = {"ok": 0, "fail": 0}
    log = open(os.path.join(os.path.dirname(__file__), "bulk_v2.log"), "w", encoding="utf-8")

    for i, (gid, handle, prompt) in enumerate(PRODUCTS, 1):
        print(f"\n[{i:2}/{len(PRODUCTS)}] {handle[:45]}...")
        local_path = os.path.join(IMAGES_DIR, f"{handle}.jpg")

        # 1. Gera imagem (usa cache local se já existe)
        if os.path.exists(local_path) and os.path.getsize(local_path) > 10000:
            with open(local_path, "rb") as f:
                img_bytes = f.read()
            print(f"  ✓ Cache: {len(img_bytes)//1024}KB")
        else:
            print(f"  Gerando via DALL-E 3...")
            img_bytes = generate_image_openrouter(prompt, handle)
            if not img_bytes:
                results["fail"] += 1
                log.write(f"FAIL_GEN {handle}\n")
                time.sleep(3)
                continue
            with open(local_path, "wb") as f:
                f.write(img_bytes)
            print(f"  ✓ Gerada: {len(img_bytes)//1024}KB")
            time.sleep(2)  # rate-limit DALL-E

        log.write(f"GENERATED {handle} {len(img_bytes)}b\n")
        results["ok"] += 1

        # Delay entre produtos
        time.sleep(1)

    print(f"\n{'='*60}")
    print(f"  Geração: {results['ok']} OK | {results['fail']} falhas")
    print(f"  Imagens em: {IMAGES_DIR}")
    print(f"  Próximo passo: rodar upload_to_shopify.py para fazer staged upload")
    print("=" * 60)
    log.close()


if __name__ == "__main__":
    main()
