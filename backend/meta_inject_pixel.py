# -*- coding: utf-8 -*-
"""
meta_inject_pixel.py — Injeta Meta Pixel no tema Shopify via REST API
Requer: SHOPIFY_ADMIN_TOKEN=shpat_... (não atkn_)
Execute APÓS configurar META_PIXEL_ID e um token shpat_ no .env
"""
import os, sys, pathlib
import httpx
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_ENV = pathlib.Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV, override=True)

DOMAIN   = os.getenv("SHOPIFY_DOMAIN", "10ei3t-sf.myshopify.com")
TOKEN    = os.getenv("SHOPIFY_ADMIN_TOKEN", "")
PIXEL_ID = os.getenv("META_PIXEL_ID", "")

if not PIXEL_ID:
    print("❌ Configure META_PIXEL_ID no .env primeiro")
    sys.exit(1)

if TOKEN.startswith("atkn_"):
    print("❌ SHOPIFY_ADMIN_TOKEN é um Theme Access Token (atkn_)")
    print("   Precisa de um Admin API token (shpat_):")
    print("   Shopify Admin > Configurações > Apps > Desenvolver apps >")
    print("   Criar app > instalar > copiar token shpat_")
    print()
    print("   OU use a rota nativa:")
    print("   Shopify Admin > Apps > Facebook & Instagram > Pixel")
    sys.exit(1)

REST_BASE = f"https://{DOMAIN}/admin/api/2024-10"
HEADERS   = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

# Descobre tema ao vivo
r = httpx.get(f"{REST_BASE}/themes.json", headers=HEADERS, timeout=15)
themes = r.json().get("themes", [])
live = next((t for t in themes if t["role"] == "main"), None)
if not live:
    print("❌ Tema principal não encontrado")
    sys.exit(1)

THEME_ID = live["id"]
print(f"✅ Tema: {live['name']} (ID: {THEME_ID})")

PIXEL_CODE = f"""
  <!-- ═══ META PIXEL — Aura Decore ═══ -->
  <script>
  !function(f,b,e,v,n,t,s)
  {{if(f.fbq)return;n=f.fbq=function(){{n.callMethod?
  n.callMethod.apply(n,arguments):n.queue.push(arguments)}};
  if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
  n.queue=[];t=b.createElement(e);t.async=!0;
  t.src=v;s=b.getElementsByTagName(e)[0];
  s.parentNode.insertBefore(t,s)}}(window, document,'script',
  'https://connect.facebook.net/en_US/fbevents.js');
  fbq('init', '{PIXEL_ID}');
  fbq('track', 'PageView');
  </script>
  <noscript><img height="1" width="1" style="display:none"
    src="https://www.facebook.com/tr?id={PIXEL_ID}&ev=PageView&noscript=1"/></noscript>
  <!-- ═══ END META PIXEL ═══ -->
"""

# Lê e atualiza theme.liquid
r = httpx.get(f"{REST_BASE}/themes/{THEME_ID}/assets.json",
              params={"asset[key]": "layout/theme.liquid"},
              headers=HEADERS, timeout=20)
content = r.json().get("asset", {}).get("value", "")

if f"fbq('init', '{PIXEL_ID}')" in content:
    print(f"✅ Pixel {PIXEL_ID} já está no tema!")
elif "fbq('init'" in content:
    print("⚠️  Outro pixel encontrado no tema — verifique manualmente")
elif "</head>" in content:
    new = content.replace("</head>", PIXEL_CODE + "\n</head>", 1)
    r2 = httpx.put(f"{REST_BASE}/themes/{THEME_ID}/assets.json",
                   headers=HEADERS,
                   json={"asset": {"key": "layout/theme.liquid", "value": new}},
                   timeout=30)
    if r2.status_code in (200, 201):
        print(f"✅ Pixel {PIXEL_ID} injetado com sucesso!")
    else:
        print(f"❌ Erro: {r2.status_code} — {r2.text[:300]}")

# Webhooks
print("\n[Webhooks] Criando webhooks CAPI...")
RAILWAY = os.getenv("RAILWAY_URL", "https://aura-office-dashboard-production.up.railway.app")
WHS = [
    ("orders/create",    f"{RAILWAY}/meta/webhook/order"),
    ("orders/paid",      f"{RAILWAY}/meta/webhook/order"),
    ("checkouts/create", f"{RAILWAY}/meta/webhook/checkout"),
]
existing = {w["topic"] for w in httpx.get(f"{REST_BASE}/webhooks.json",
            headers=HEADERS, timeout=15).json().get("webhooks", [])}
for topic, url in WHS:
    if topic in existing:
        print(f"  ✅ {topic} já existe")
        continue
    r = httpx.post(f"{REST_BASE}/webhooks.json", headers=HEADERS,
                   json={"webhook": {"topic": topic, "address": url, "format": "json"}},
                   timeout=15)
    if r.status_code in (200, 201):
        print(f"  ✅ {topic} criado")
    else:
        print(f"  ❌ {topic}: {r.status_code} {r.text[:150]}")

print("\n✅ Setup concluído!")
print("   Execute: python meta_integration.py test-events")
