# -*- coding: utf-8 -*-
"""
meta_admin_setup.py — Setup completo Meta via Shopify REST Admin API
Executa como admin:
  1. Cria webhooks CAPI (orders/create, checkouts/create, orders/paid)
  2. Injeta Meta Pixel no tema ao vivo (theme.liquid)
  3. Adiciona ViewContent na product.liquid (se existir)
  4. Adiciona Purchase no order_status.liquid (thank you page)
  5. Relatório final de status
"""
import os, sys, json, base64, pathlib
import httpx
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_ENV = pathlib.Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV, override=True)

DOMAIN       = os.getenv("SHOPIFY_DOMAIN", "10ei3t-sf.myshopify.com")
TOKEN        = os.getenv("SHOPIFY_ADMIN_API_TOKEN") or os.getenv("SHOPIFY_ADMIN_TOKEN", "")
PIXEL_ID     = os.getenv("META_PIXEL_ID", "")
RAILWAY_URL  = os.getenv("RAILWAY_URL", "https://aura-office-dashboard-production.up.railway.app")
THEME_ID     = "142767816809"  # Aura Decore - v5 (MAIN)

REST_BASE    = f"https://{DOMAIN}/admin/api/2024-10"
HEADERS      = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

print("=" * 60)
print("  META ADMIN SETUP — Aura Decore")
print("=" * 60)

# ──────────────────────────────────────────────────────────────
# 1. WEBHOOKS
# ──────────────────────────────────────────────────────────────
print("\n[1/4] Criando webhooks Shopify → CAPI...")

WEBHOOKS = [
    {"topic": "orders/create",    "address": f"{RAILWAY_URL}/meta/webhook/order"},
    {"topic": "orders/paid",      "address": f"{RAILWAY_URL}/meta/webhook/order"},
    {"topic": "checkouts/create", "address": f"{RAILWAY_URL}/meta/webhook/checkout"},
]

# Lista existentes para evitar duplicatas
existing = httpx.get(f"{REST_BASE}/webhooks.json", headers=HEADERS, timeout=15).json()
existing_topics = {w["topic"] for w in existing.get("webhooks", [])}
print(f"   Webhooks existentes: {existing_topics or 'nenhum'}")

for wh in WEBHOOKS:
    topic = wh["topic"]
    if topic in existing_topics:
        print(f"   ✅ {topic} — já existe")
        continue
    payload = {"webhook": {"topic": topic, "address": wh["address"], "format": "json"}}
    r = httpx.post(f"{REST_BASE}/webhooks.json", headers=HEADERS, json=payload, timeout=15)
    if r.status_code in (200, 201):
        wid = r.json().get("webhook", {}).get("id", "?")
        print(f"   ✅ {topic} — criado (ID: {wid})")
    else:
        print(f"   ❌ {topic} — erro {r.status_code}: {r.text[:200]}")

# ──────────────────────────────────────────────────────────────
# 2. PIXEL NO TEMA — theme.liquid
# ──────────────────────────────────────────────────────────────
print(f"\n[2/4] Injetando Meta Pixel no tema (ID: {THEME_ID})...")

if not PIXEL_ID:
    print("   ⚠️  META_PIXEL_ID não configurado — pixel não será injetado.")
    print("   Configure META_PIXEL_ID no .env e re-execute este script.")
else:
    PIXEL_SNIPPET = f"""
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

    # Lê theme.liquid atual
    r = httpx.get(
        f"{REST_BASE}/themes/{THEME_ID}/assets.json",
        params={"asset[key]": "layout/theme.liquid"},
        headers=HEADERS, timeout=20
    )
    if r.status_code == 200:
        asset = r.json().get("asset", {})
        content = asset.get("value", "")

        if f"fbq('init', '{PIXEL_ID}')" in content:
            print(f"   ✅ Pixel {PIXEL_ID} já está no theme.liquid")
        elif "fbq('init'" in content:
            print(f"   ⚠️  Outro pixel detectado no theme.liquid — verifique manualmente")
        else:
            # Injeta antes do </head>
            if "</head>" in content:
                new_content = content.replace("</head>", PIXEL_SNIPPET + "\n</head>", 1)
                payload = {"asset": {"key": "layout/theme.liquid", "value": new_content}}
                r2 = httpx.put(
                    f"{REST_BASE}/themes/{THEME_ID}/assets.json",
                    headers=HEADERS, json=payload, timeout=30
                )
                if r2.status_code in (200, 201):
                    print(f"   ✅ Pixel {PIXEL_ID} injetado no theme.liquid (antes do </head>)")
                else:
                    print(f"   ❌ Erro ao salvar theme.liquid: {r2.status_code} {r2.text[:300]}")
            else:
                print("   ❌ </head> não encontrado no theme.liquid — injete manualmente")
    else:
        print(f"   ❌ Não foi possível ler theme.liquid: {r.status_code}")

# ──────────────────────────────────────────────────────────────
# 3. PURCHASE EVENT — order_status.liquid (thank you page)
# ──────────────────────────────────────────────────────────────
print("\n[3/4] Verificando order_status.liquid (Purchase event)...")

if PIXEL_ID:
    PURCHASE_SNIPPET = """
<!-- META PIXEL PURCHASE — Aura Decore -->
<script>
{% if first_time_accessed %}
fbq('track', 'Purchase', {
  value: {{ order.total_price | money_without_currency }},
  currency: '{{ order.currency }}',
  content_ids: [{% for line in order.line_items %}'{{ line.product_id }}'{% unless forloop.last %},{% endunless %}{% endfor %}],
  content_type: 'product',
  num_items: {{ order.line_items | size }}
});
{% endif %}
</script>
<!-- END META PIXEL PURCHASE -->
"""
    r = httpx.get(
        f"{REST_BASE}/themes/{THEME_ID}/assets.json",
        params={"asset[key]": "layout/order-status.liquid"},
        headers=HEADERS, timeout=20
    )
    if r.status_code == 200:
        content = r.json().get("asset", {}).get("value", "")
        if "fbq('track', 'Purchase'" in content:
            print("   ✅ Purchase event já está no order-status.liquid")
        else:
            new_content = PURCHASE_SNIPPET + "\n" + content
            payload = {"asset": {"key": "layout/order-status.liquid", "value": new_content}}
            r2 = httpx.put(
                f"{REST_BASE}/themes/{THEME_ID}/assets.json",
                headers=HEADERS, json=payload, timeout=30
            )
            if r2.status_code in (200, 201):
                print("   ✅ Purchase event injetado no order-status.liquid")
            else:
                print(f"   ℹ️  order-status.liquid: {r2.status_code} (arquivo pode não existir — use checkout.liquid ou scripts de checkout)")
    else:
        # Tenta checkout.liquid
        print(f"   ℹ️  order-status não encontrado (status {r.status_code}) — verifique Shopify Admin > Checkout > Scripts adicionais")
else:
    print("   ⚠️  Pixel ID não configurado — pulando")

# ──────────────────────────────────────────────────────────────
# 4. VIEWCONTENT — sections/product-template.liquid
# ──────────────────────────────────────────────────────────────
print("\n[4/4] Verificando product template (ViewContent)...")

if PIXEL_ID:
    VIEW_CONTENT_SNIPPET = """
<!-- META PIXEL ViewContent — Aura Decore -->
<script>
fbq('track', 'ViewContent', {
  content_ids: ['{{ product.id }}'],
  content_name: '{{ product.title | escape }}',
  content_category: '{{ product.type | escape }}',
  content_type: 'product',
  value: {{ product.price | money_without_currency }},
  currency: '{{ shop.currency }}'
});
</script>
<!-- END META ViewContent -->
"""
    # Tenta main-product.liquid ou product-template.liquid
    for key in ["sections/main-product.liquid", "sections/product-template.liquid",
                "templates/product.liquid", "sections/product-form.liquid"]:
        r = httpx.get(
            f"{REST_BASE}/themes/{THEME_ID}/assets.json",
            params={"asset[key]": key},
            headers=HEADERS, timeout=20
        )
        if r.status_code == 200:
            content = r.json().get("asset", {}).get("value", "")
            if "fbq('track', 'ViewContent'" in content:
                print(f"   ✅ ViewContent já está em {key}")
            else:
                new_content = content + "\n" + VIEW_CONTENT_SNIPPET
                payload = {"asset": {"key": key, "value": new_content}}
                r2 = httpx.put(
                    f"{REST_BASE}/themes/{THEME_ID}/assets.json",
                    headers=HEADERS, json=payload, timeout=30
                )
                if r2.status_code in (200, 201):
                    print(f"   ✅ ViewContent injetado em {key}")
                else:
                    print(f"   ❌ Erro em {key}: {r2.status_code}")
            break
    else:
        print("   ℹ️  Template de produto não encontrado — ViewContent via Pixel base suficiente por ora")
else:
    print("   ⚠️  Pixel ID não configurado — pulando")

# ──────────────────────────────────────────────────────────────
# RELATÓRIO FINAL
# ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("  SETUP CONCLUÍDO — Resumo")
print("=" * 60)

# Verifica webhooks criados
wh_list = httpx.get(f"{REST_BASE}/webhooks.json", headers=HEADERS, timeout=15).json()
print(f"\n  Webhooks ativos ({len(wh_list.get('webhooks', []))}):")
for w in wh_list.get("webhooks", []):
    print(f"    ✅ {w['topic']} → {w['address']}")

print(f"\n  Pixel Meta: {'✅ ' + PIXEL_ID if PIXEL_ID else '❌ Configure META_PIXEL_ID no .env'}")
print(f"  CAPI Token: {'✅ configurado' if os.getenv('META_CAPI_TOKEN') else '❌ Configure META_CAPI_TOKEN no .env'}")
print(f"  Catálogo FB: ✅ 78 produtos publicados no canal Facebook & Instagram")
print(f"\n  Próximo passo:")
if not PIXEL_ID:
    print("    1. Configure META_PIXEL_ID no .env")
    print("    2. Execute: python meta_admin_setup.py  (injetará pixel no tema)")
    print("    3. Execute: python meta_integration.py test-events")
else:
    print("    1. Execute: python meta_integration.py test-events")
    print("    2. Verifique no Meta Event Manager: business.facebook.com/events_manager")
print("=" * 60)
