#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aura Decore — Image Pipeline v3
Fluxo: OpenRouter/Gemini → base64 → GCS staged upload → Shopify CDN → productCreateMedia
Usa: Python 3.12 + httpx + dotenv
"""
import os, sys, time, json, base64, re
from datetime import datetime
import httpx
from dotenv import load_dotenv

_ENV = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(_ENV, override=True)

OR_KEY      = os.getenv("OPENROUTER_API_KEY", "")
SHOPIFY_MCP_TOKEN = ""  # Obtido via stagedUploadsCreate pelo GraphQL interno

# O MCP do Shopify usa autenticação própria — vamos proxy via o backend local
BACKEND_URL = "http://localhost:8000"
SHOPIFY_GQL = "https://10ei3t-sf.myshopify.com/admin/api/2024-10/graphql.json"

IMGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated_images", "pipeline_v3")
os.makedirs(IMGS_DIR, exist_ok=True)

BRAND = (
    "professional product photography, japandi minimalist aesthetic, "
    "warm off-white background #F5F0EB, soft natural diffused light, "
    "shallow depth of field, premium luxury home decor, artisan handmade, "
    "clean minimal composition, high resolution 1080p, square 1:1 format"
)

# ── produto → prompt ───────────────────────────────────────────────────────────
PRODUCTS = [
    ("gid://shopify/Product/7795259015273", "vaso-oval-minimalista",
     "oval matte white ceramic vase artisan japandi"),
    ("gid://shopify/Product/7798301229161", "vaso-ceramica-organico-olivo",
     "organic curved olive green ceramic vase wabi-sabi"),
    ("gid://shopify/Product/7798307160169", "vaso-ceramica-achatado-wabi",
     "low flat wabi-sabi ceramic vase wide mouth beige matte"),
    ("gid://shopify/Product/7798306635881", "jarro-ceramico-areia",
     "cylindrical sand beige ceramic jar artisan"),
    ("gid://shopify/Product/7798306504809", "conjunto-bowl-ceramica",
     "set of 3 ceramic bowls nested beige cream matte"),
    ("gid://shopify/Product/7798306930793", "porta-velas-trio",
     "trio ceramic candle holders white matte different heights"),
    ("gid://shopify/Product/7798306734185", "prato-ceramica-lua",
     "decorative ceramic plate matte white lunar minimal"),
    ("gid://shopify/Product/7798309716073", "porta-joias-ceramica",
     "white ceramic jewelry tray minimal organic shape"),
    ("gid://shopify/Product/7795259277417", "incensario-ripple",
     "ceramic incense holder ripple wave matte zen"),
    ("gid://shopify/Product/7795259342953", "vela-pilar-argila",
     "natural clay pillar candle handmade earthy tone"),
    ("gid://shopify/Product/7795259080809", "vela-soja-bambu-cedro",
     "soy wax candle glass jar bamboo cedar scent minimal"),
    ("gid://shopify/Product/7797722251369", "vela-cera-abelha",
     "beeswax artisan candle golden honey color natural"),
    ("gid://shopify/Product/7798309552233", "castical-bambu",
     "bamboo woven candle holder natural weave zen"),
    ("gid://shopify/Product/7798309027945", "castical-ceramica-triptico",
     "three tall ceramic candleholders white matte"),
    ("gid://shopify/Product/7798309257321", "suporte-vela-madeira",
     "floating wood candle holder natural tealight minimal"),
    ("gid://shopify/Product/7798309421161", "lanterna-rattan-mini",
     "mini rattan woven lantern natural fiber warm candlelight"),
    ("gid://shopify/Product/7798308831337", "abajur-bambu",
     "bamboo table lamp shade natural woven warm light"),
    ("gid://shopify/Product/7798301491305", "luminaria-rattan-bali",
     "rattan dome pendant lamp natural woven bali style"),
    ("gid://shopify/Product/7798307455081", "almofada-boucle-areia",
     "bouclé cushion sand natural color textured fabric minimal"),
    ("gid://shopify/Product/7798307815529", "almofada-linho-bordado",
     "linen cushion cover beige subtle hand embroidery"),
    ("gid://shopify/Product/7798307979369", "manta-trico-chunky",
     "chunky knit throw blanket off-white thick cozy minimal"),
    ("gid://shopify/Product/7798301327465", "manta-algodao-terracota",
     "organic cotton throw blanket terracotta rust folded"),
    ("gid://shopify/Product/7798308143209", "toalha-linho-premium",
     "premium linen face towels natural folded spa minimal"),
    ("gid://shopify/Product/7798307651689", "tapete-juta-redondo",
     "round jute natural fiber rug 120cm top view flat lay"),
    ("gid://shopify/Product/7798308339817", "tapete-algodao-minimalista",
     "cotton minimalist rug natural 60x90 flat lay clean"),
    ("gid://shopify/Product/7795259441257", "arranjo-algodao-seco",
     "dried cotton stem bouquet branches white fluffy vase"),
    ("gid://shopify/Product/7795259146345", "eucalipto-preservado",
     "preserved eucalyptus dried bouquet grey-green botanical"),
    ("gid://shopify/Product/7797722382441", "flores-always-viva",
     "always-viva dried flowers bouquet yellow purple Brazilian"),
    ("gid://shopify/Product/7797722415209", "algodao-crudo-kumo",
     "raw cotton bolls thin stems natural dried botanical"),
    ("gid://shopify/Product/7795259310185", "cesta-rattan-oval",
     "oval rattan storage basket natural wicker weave minimal"),
    ("gid://shopify/Product/7795259179113", "suporte-livros-madeira",
     "pair minimalist solid wood bookends natural grain desk"),
    ("gid://shopify/Product/7795259211881", "difusor-varas-lavanda",
     "reed diffuser glass bottle lavender minimal elegant"),
    ("gid://shopify/Product/7795259408489", "porta-incenso-bambu",
     "bamboo incense holder natural minimal groove zen"),
    ("gid://shopify/Product/7798301589609", "espelho-oval-madeira",
     "oval mirror solid natural wood frame japandi minimal"),
    ("gid://shopify/Product/7798309945449", "bandeja-marmore",
     "oval marble surface wood rim tray luxury japandi"),
    ("gid://shopify/Product/7798310207593", "caixa-organizadora",
     "wooden storage box with lid natural wood grain minimal"),
    ("gid://shopify/Product/7798310371433", "kit-ritual-matinal",
     "morning ritual kit curated items incense vase candle stone gift"),
    ("gid://shopify/Product/7796713980009", "mini-kit-zen",
     "small zen starter kit incense palo santo stone gift"),
    ("gid://shopify/Product/7797722447977", "kit-zen-nacional",
     "Brazilian zen gift kit natural items herbs stone sachet"),
    ("gid://shopify/Product/7797722316905", "pedra-semipreciosa-trio",
     "trio semiprecious stones rose quartz amethyst citrine velvet pouch"),
    ("gid://shopify/Product/7797722284137", "pedra-sabao-sabi",
     "soapstone decorative smooth natural grey-green veins minimal"),
    ("gid://shopify/Product/7797722218601", "sache-ervas-brasileiras",
     "Brazilian herb sachet natural linen bag dried lavender"),
    ("gid://shopify/Product/7796713848937", "palo-santo-3",
     "3 palo santo sacred wood sticks natural light brown minimal"),
    ("gid://shopify/Product/7796713816169", "sache-aromatico-linho",
     "linen sachet bag lavender cedar aromatherapy small tied"),
    ("gid://shopify/Product/7796713947241", "porta-incenso-madeira",
     "flat wood incense holder minimal plank natural grain"),
    ("gid://shopify/Product/7796713914473", "marcadores-bambu",
     "3 bamboo bookmarks kanji engraved elegant minimal"),
    ("gid://shopify/Product/7795242598505", "porta-objetos-madeira",
     "minimal wood desk organizer compartments natural grain"),
    ("gid://shopify/Product/7795242500201", "difusor-bambu",
     "bamboo reed diffuser glass bottle natural aroma minimal"),
    ("gid://shopify/Product/7795242401897", "arranjo-pampas-trigo",
     "pampas grass dried wheat botanical arrangement natural beige"),
    ("gid://shopify/Product/7795242303593", "bandeja-bambu-zen",
     "bamboo serving tray zen minimal natural flat lay"),
    ("gid://shopify/Product/7795242270825", "vaso-wabi-sabi-textura",
     "wabi-sabi ceramic vase rough surface beige artisan"),
    ("gid://shopify/Product/7792661168233", "painel-moss-led",
     "wood panel preserved moss LED light wall art biophilic"),
    ("gid://shopify/Product/7792646291561", "kit-jardinagem-ervas",
     "herb garden kit aromatic plants small pots seeds minimal"),
    ("gid://shopify/Product/7792646258793", "candeeiro-bambu",
     "bamboo candleholder coconut wax candle natural warm glow"),
    ("gid://shopify/Product/7786642800745", "bandeja-acacia",
     "minimal acacia wood tray rectangle natural grain elegant"),
    ("gid://shopify/Product/7786642702441", "diffuser-blend-200ml",
     "premium reed diffuser 200ml glass bottle rattan sticks luxury"),
    ("gid://shopify/Product/7786642636905", "arranjo-pampas-secos",
     "pampas grass dried plants eucalyptus arrangement natural beige"),
    ("gid://shopify/Product/7786642538601", "almofada-linho-natural",
     "natural linen cushion pillow 45x45 off-white Belgian minimal"),
    ("gid://shopify/Product/7786642473065", "vela-aromatica-aura",
     "natural soy wax scented candle artisan amber jar minimal"),
    ("gid://shopify/Product/7786642440297", "vaso-ceramica-japandi",
     "japandi ceramic vase high temperature artisan off-white minimal"),
    ("gid://shopify/Product/7786418307177", "vaso-ceramica-fosco-bege",
     "matte ceramic vase beige sand color artisan japandi"),
    ("gid://shopify/Product/7786418274409", "bandeja-madeira-natural",
     "minimalist natural wood serving tray honey color grain"),
    ("gid://shopify/Product/7786418241641", "diffuser-varetas-aromaticas",
     "reed diffuser ambient fragrance rattan sticks botanical"),
    ("gid://shopify/Product/7786418208873", "pampas-naturais-secos",
     "pampas grass natural dried plume bouquet beige golden boho"),
    ("gid://shopify/Product/7786418176105", "almofada-linho-45x45",
     "natural linen cushion cover off-white minimal clean japandi"),
    ("gid://shopify/Product/7786418143337", "vela-ambar-sandalo",
     "natural soy wax candle amber sandalwood glass jar warm"),
    ("gid://shopify/Product/7786418110569", "vaso-terracota",
     "terracotta ceramic vase artisan warm earthy handmade boho"),
    ("gid://shopify/Product/7786418045033", "vaso-ceramica-branco",
     "white minimalist ceramic vase artisan handmade clean japandi"),
    ("gid://shopify/Product/7785846669417", "diffuser-premium-cedro",
     "premium reed diffuser cedar sandalwood 200ml elegant frosted"),
    ("gid://shopify/Product/7785846603881", "pampa-seco-premium",
     "premium dried pampas grass natural beige fluffy plume minimal"),
    ("gid://shopify/Product/7785846571113", "almofada-linho-minimalista",
     "natural linen cushion pillow bege textured fabric sofa minimal"),
    ("gid://shopify/Product/7785846505577", "vela-ambar-coco",
     "amber natural coconut wax candle artisan warm honey tone"),
    ("gid://shopify/Product/7785846440041", "vaso-ceramica-wabi-bege",
     "wabi-sabi ceramic vase beige natural handmade artisan organic"),
]


# ── Funções ────────────────────────────────────────────────────────────────────

def gen_image_openrouter(prompt: str) -> bytes | None:
    full = f"{prompt}, {BRAND}"
    headers = {
        "Authorization": f"Bearer {OR_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://auradecore.com.br",
        "X-Title": "Aura Decore",
    }
    body = {
        "model": "google/gemini-2.5-flash-image",
        "messages": [{"role": "user", "content": full}],
        "max_tokens": 500,
    }
    try:
        r = httpx.post("https://openrouter.ai/api/v1/chat/completions",
                       headers=headers, json=body, timeout=120)
        if r.status_code != 200:
            print(f"    OR {r.status_code}: {r.text[:150]}")
            return None
        data = r.json()
        imgs = data["choices"][0]["message"].get("images", [])
        if not imgs:
            print("    Sem imagens na resposta")
            return None
        url = imgs[0]["image_url"]["url"]
        if url.startswith("data:"):
            # base64 inline
            b64 = url.split(",", 1)[1]
            return base64.b64decode(b64)
        else:
            # URL externa
            r2 = httpx.get(url, timeout=30)
            return r2.content if r2.status_code == 200 else None
    except Exception as e:
        print(f"    ERRO: {e}")
        return None


def shopify_gql(query: str, variables: dict = None, token: str = "") -> dict:
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": token,
    }
    body = {"query": query}
    if variables:
        body["variables"] = variables
    r = httpx.post(SHOPIFY_GQL, headers=headers, json=body, timeout=30)
    return r.json() if r.status_code == 200 else {"error": r.text[:200]}


def staged_upload_create(filename: str, filesize: int, token: str) -> dict | None:
    q = """
    mutation SU($input: [StagedUploadInput!]!) {
      stagedUploadsCreate(input: $input) {
        stagedTargets {
          url resourceUrl
          parameters { name value }
        }
        userErrors { field message }
      }
    }"""
    v = {"input": [{"filename": filename, "mimeType": "image/png",
                    "resource": "IMAGE", "fileSize": str(filesize)}]}
    d = shopify_gql(q, v, token)
    targets = d.get("data", {}).get("stagedUploadsCreate", {}).get("stagedTargets", [])
    return targets[0] if targets else None


def upload_gcs(upload_url: str, img_bytes: bytes) -> bool:
    try:
        r = httpx.put(upload_url, content=img_bytes,
                      headers={"Content-Type": "image/png"}, timeout=60)
        return r.status_code == 200
    except Exception as e:
        print(f"    GCS err: {e}")
        return False


def create_media(product_id: str, resource_url: str, alt: str, token: str) -> bool:
    q = """
    mutation CM($pid: ID!, $media: [CreateMediaInput!]!) {
      productCreateMedia(productId: $pid, media: $media) {
        media { ... on MediaImage { id status } }
        mediaUserErrors { field message }
      }
    }"""
    v = {"pid": product_id,
         "media": [{"originalSource": resource_url,
                    "alt": alt, "mediaContentType": "IMAGE"}]}
    d = shopify_gql(q, v, token)
    errs = d.get("data", {}).get("productCreateMedia", {}).get("mediaUserErrors", [])
    if errs:
        print(f"    Media errs: {errs}")
        return False
    return True


def main(shopify_token: str):
    print("=" * 60)
    print(f"  Aura Image Pipeline  |  {datetime.now().strftime('%H:%M:%S')}")
    print(f"  {len(PRODUCTS)} produtos  |  OpenRouter Gemini Flash Image")
    print("=" * 60)

    ok = fail = skip = 0
    log_path = os.path.join(os.path.dirname(__file__), "pipeline_v3.log")
    log = open(log_path, "w", encoding="utf-8")

    for i, (gid, handle, prompt) in enumerate(PRODUCTS, 1):
        print(f"\n[{i:2}/{len(PRODUCTS)}] {handle[:50]}...")
        cache = os.path.join(IMGS_DIR, f"{handle}.png")

        # 1. Gerar (ou usar cache)
        if os.path.exists(cache) and os.path.getsize(cache) > 5000:
            img = open(cache, "rb").read()
            print(f"  ✓ Cache ({len(img)//1024}KB)")
        else:
            img = gen_image_openrouter(prompt)
            if not img:
                fail += 1
                log.write(f"FAIL_GEN {handle}\n")
                time.sleep(5)
                continue
            open(cache, "wb").write(img)
            print(f"  ✓ Gerada ({len(img)//1024}KB)")
            time.sleep(3)  # OR rate-limit

        # 2. Staged upload
        target = staged_upload_create(f"{handle}.png", len(img), shopify_token)
        if not target:
            fail += 1
            log.write(f"FAIL_STAGED {handle}\n")
            continue
        print(f"  ✓ Staged URL obtida")

        # 3. Upload GCS
        if not upload_gcs(target["url"], img):
            fail += 1
            log.write(f"FAIL_GCS {handle}\n")
            continue
        print(f"  ✓ GCS upload OK")

        # 4. Create media
        resource_url = target["resourceUrl"]
        title = handle.replace("-", " ").title()
        if not create_media(gid, resource_url, f"{title} — Aura Decore", shopify_token):
            fail += 1
            log.write(f"FAIL_MEDIA {handle}\n")
            continue

        ok += 1
        log.write(f"OK {handle} {resource_url}\n")
        print(f"  ✅ Imagem na CDN do Shopify!")
        time.sleep(1)

    print(f"\n{'='*60}")
    print(f"  ✅ OK: {ok}  ❌ Fail: {fail}  ⏭ Skip: {skip}")
    print(f"  Log: {log_path}")
    print("=" * 60)
    log.close()


if __name__ == "__main__":
    token = sys.argv[1] if len(sys.argv) > 1 else ""
    if not token:
        print("Uso: python image_pipeline.py <shopify_admin_token>")
        print("Obter em: Admin Shopify → Configurações → Apps → Desenvolver apps → Create app → Admin API token")
        sys.exit(1)
    if not OR_KEY:
        print("OPENROUTER_API_KEY não configurada no .env")
        sys.exit(1)
    main(token)
