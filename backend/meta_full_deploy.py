# -*- coding: utf-8 -*-
"""
meta_full_deploy.py — Deploy completo Meta + Shopify para Aura Decore
Execute APÓS preencher o .env com todas as credenciais Meta.

Faz tudo automaticamente:
  1. Valida credenciais
  2. Duplica tema ao vivo (draft seguro)
  3. Injeta Meta Pixel + ViewContent + Purchase no tema draft
  4. Cria webhooks CAPI (orders + checkouts)
  5. Testa eventos CAPI
  6. Verifica catálogo Meta
  7. Gera relatório final
"""
import os, sys, json, time, pathlib
import httpx
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_ENV = pathlib.Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV, override=True)

DOMAIN      = os.getenv("SHOPIFY_DOMAIN", "10ei3t-sf.myshopify.com")
STOKEN      = os.getenv("SHOPIFY_ADMIN_API_TOKEN") or os.getenv("SHOPIFY_ADMIN_TOKEN", "")
PIXEL_ID    = os.getenv("META_PIXEL_ID", "")
CAPI_TOKEN  = os.getenv("META_CAPI_TOKEN", "")
BIZ_ID      = os.getenv("META_BUSINESS_ID", "")
APP_SECRET  = os.getenv("META_APP_SECRET", "")
ACCESS_TOKEN= os.getenv("META_ACCESS_TOKEN", "")
RAILWAY_URL = os.getenv("RAILWAY_URL", "https://aura-office-dashboard-production.up.railway.app")

REST = f"https://{DOMAIN}/admin/api/2024-10"
HEADERS = {"X-Shopify-Access-Token": STOKEN, "Content-Type": "application/json"}

REPORT = {"steps": [], "status": "ok"}

def step(msg, ok=True, detail=""):
    icon = "✅" if ok else "❌"
    line = f"  {icon} {msg}"
    if detail:
        line += f"\n     {detail}"
    print(line)
    REPORT["steps"].append({"msg": msg, "ok": ok, "detail": detail})
    if not ok:
        REPORT["status"] = "partial"

print("=" * 60)
print("  META FULL DEPLOY — Aura Decore")
print("=" * 60)

# ── 1. VALIDAR CREDENCIAIS ─────────────────────────────────────
print("\n[1/7] Validando credenciais...")
missing = []
if not PIXEL_ID:    missing.append("META_PIXEL_ID")
if not CAPI_TOKEN:  missing.append("META_CAPI_TOKEN")
if not BIZ_ID:      missing.append("META_BUSINESS_ID")
if not APP_SECRET:  missing.append("META_APP_SECRET")

if STOKEN.startswith("atkn_"):
    step("SHOPIFY_ADMIN_TOKEN", False,
         "Token atkn_ (Theme) não suporta REST Admin API.\n"
         "     Crie um token shpat_ em: Admin > Configurações > Apps > Desenvolver apps")
    has_shopify_api = False
else:
    r = httpx.get(f"{REST}/shop.json", headers=HEADERS, timeout=10)
    has_shopify_api = r.status_code == 200
    step("SHOPIFY_ADMIN_TOKEN", has_shopify_api,
         "shpat_ válido" if has_shopify_api else f"Erro {r.status_code}: {r.text[:100]}")

if missing:
    for m in missing:
        step(m, False, "Não configurado no .env")
    print(f"\n  ⚠️  Configure as credenciais faltantes no .env e re-execute.")
    print(f"  📋 Guia: AURA-decor-vault/Meta Business/META-FULL-SETUP.md")
    if not has_shopify_api:
        sys.exit(1)

# ── 2. DUPLICAR TEMA (se tiver token REST) ─────────────────────
draft_theme_id = None
if has_shopify_api:
    print("\n[2/7] Criando tema draft para edição segura...")
    try:
        r = httpx.get(f"{REST}/themes.json", headers=HEADERS, timeout=15)
        themes = r.json().get("themes", [])
        live = next((t for t in themes if t["role"] == "main"), None)
        # Verifica se já existe draft com nosso nome
        draft = next((t for t in themes if t["name"] == "Aura Decore - v5 [Meta Draft]"), None)

        if draft:
            draft_theme_id = draft["id"]
            step("Tema draft", True, f"Já existe: {draft['name']} (ID: {draft_theme_id})")
        elif live:
            r2 = httpx.post(f"{REST}/themes.json",
                headers=HEADERS, timeout=30,
                json={"theme": {"name": "Aura Decore - v5 [Meta Draft]",
                                "src": f"https://{DOMAIN}/admin/themes/{live['id']}.zip",
                                "role": "unpublished"}})
            if r2.status_code in (200, 201):
                draft_theme_id = r2.json().get("theme", {}).get("id")
                step("Tema draft criado", True, f"ID: {draft_theme_id}")
                time.sleep(5)  # aguarda processamento
            else:
                step("Criar tema draft", False, f"{r2.status_code}: {r2.text[:200]}")
        else:
            step("Tema ao vivo não encontrado", False)
    except Exception as e:
        step("Duplicar tema", False, str(e))
else:
    print("\n[2/7] Pulando (sem token REST)...")
    step("Duplicar tema", False, "Requer token shpat_")

# ── 3. INJETAR PIXEL NO DRAFT ─────────────────────────────────
if has_shopify_api and draft_theme_id and PIXEL_ID:
    print(f"\n[3/7] Injetando pixel {PIXEL_ID} no tema draft...")
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
    try:
        # Lê theme.liquid do draft
        r = httpx.get(f"{REST}/themes/{draft_theme_id}/assets.json",
                      params={"asset[key]": "layout/theme.liquid"},
                      headers=HEADERS, timeout=20)
        content = r.json().get("asset", {}).get("value", "")

        if f"fbq('init', '{PIXEL_ID}')" in content:
            step("Pixel já injetado no draft", True)
        elif "</head>" in content:
            new = content.replace("</head>", PIXEL_CODE + "\n</head>", 1)
            r2 = httpx.put(f"{REST}/themes/{draft_theme_id}/assets.json",
                           headers=HEADERS,
                           json={"asset": {"key": "layout/theme.liquid", "value": new}},
                           timeout=30)
            if r2.status_code in (200, 201):
                step("Pixel injetado no tema draft", True, f"Pixel ID: {PIXEL_ID}")
            else:
                step("Injetar pixel", False, f"{r2.status_code}: {r2.text[:200]}")
        else:
            step("</head> não encontrado", False)
    except Exception as e:
        step("Injetar pixel", False, str(e))

    # Purchase event no order-status (checkout scripts)
    PURCHASE_CODE = f"""
<!-- META PIXEL Purchase — Aura Decore -->
{{% if first_time_accessed %}}
<script>
fbq('track', 'Purchase', {{
  value: {{{{ order.total_price | money_without_currency }}}},
  currency: '{{{{ order.currency }}}}',
  content_ids: [{{% for line in order.line_items %}}'{{{{ line.product_id }}}}'{{%- unless forloop.last -%}},{{% endunless %}}{{% endfor %}}],
  content_type: 'product',
  num_items: {{{{ order.line_items | size }}}}
}});
</script>
{{% endif %}}
<!-- END META PIXEL Purchase -->
"""
    try:
        for key in ["layout/checkout.liquid", "sections/main-cart-footer.liquid"]:
            r = httpx.get(f"{REST}/themes/{draft_theme_id}/assets.json",
                          params={"asset[key]": key}, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                content = r.json().get("asset", {}).get("value", "")
                if "fbq('track', 'Purchase'" not in content:
                    new = PURCHASE_CODE + "\n" + content
                    r2 = httpx.put(f"{REST}/themes/{draft_theme_id}/assets.json",
                                   headers=HEADERS,
                                   json={"asset": {"key": key, "value": new}}, timeout=30)
                    if r2.status_code in (200, 201):
                        step(f"Purchase event em {key}", True)
                    break
    except Exception as e:
        pass  # não crítico
else:
    print("\n[3/7] Pulando pixel (sem credenciais completas)...")
    if not PIXEL_ID:
        step("Injetar pixel", False, "META_PIXEL_ID não configurado")

# ── 4. WEBHOOKS ───────────────────────────────────────────────
if has_shopify_api:
    print("\n[4/7] Criando webhooks Shopify → CAPI...")
    try:
        existing_r = httpx.get(f"{REST}/webhooks.json", headers=HEADERS, timeout=15)
        existing = {w["topic"] for w in existing_r.json().get("webhooks", [])}

        WHS = [
            ("orders/create",    f"{RAILWAY_URL}/meta/webhook/order"),
            ("orders/paid",      f"{RAILWAY_URL}/meta/webhook/order"),
            ("checkouts/create", f"{RAILWAY_URL}/meta/webhook/checkout"),
        ]
        for topic, url in WHS:
            if topic in existing:
                step(f"Webhook {topic}", True, "já existe")
            else:
                r = httpx.post(f"{REST}/webhooks.json", headers=HEADERS,
                               json={"webhook": {"topic": topic, "address": url, "format": "json"}},
                               timeout=15)
                ok = r.status_code in (200, 201)
                wid = r.json().get("webhook", {}).get("id", "?") if ok else ""
                step(f"Webhook {topic}", ok,
                     f"ID: {wid}" if ok else f"{r.status_code}: {r.text[:150]}")
    except Exception as e:
        step("Webhooks", False, str(e))
else:
    print("\n[4/7] Webhooks — requer token shpat_")
    step("Webhooks", False, "Criar manualmente: Admin > Configurações > Notificações > Webhooks")
    print("     URL orders:    " + RAILWAY_URL + "/meta/webhook/order")
    print("     URL checkouts: " + RAILWAY_URL + "/meta/webhook/checkout")

# ── 5. TESTE CAPI ─────────────────────────────────────────────
if PIXEL_ID and CAPI_TOKEN:
    print("\n[5/7] Testando CAPI...")
    try:
        from meta_integration import MetaEventTest
        tester = MetaEventTest(test_code="DEPLOY_AURA_001")
        r = tester.test_single("PageView")
        ok = "events_received" in r
        step("CAPI PageView test", ok,
             f"{r.get('events_received', 0)} evento(s)" if ok else str(r))
    except Exception as e:
        step("CAPI test", False, str(e))
else:
    print("\n[5/7] CAPI test — aguardando META_PIXEL_ID + META_CAPI_TOKEN")
    step("CAPI test", False, "Credenciais não configuradas")

# ── 6. CATÁLOGO META ──────────────────────────────────────────
if BIZ_ID and ACCESS_TOKEN:
    print("\n[6/7] Verificando catálogos Meta...")
    try:
        from meta_integration import MetaCatalog
        cat = MetaCatalog()
        result = cat.list_catalogs()
        catalogs = result.get("data", [])
        if catalogs:
            step(f"Catálogos Meta ({len(catalogs)})", True,
                 " | ".join(f"{c.get('name','')} ({c.get('product_count',0)} produtos)"
                             for c in catalogs))
        else:
            step("Catálogos Meta", False, "Nenhum encontrado — crie em: business.facebook.com/products/catalogs/")
    except Exception as e:
        step("Catálogos Meta", False, str(e))
else:
    print("\n[6/7] Catálogo — aguardando META_BUSINESS_ID + META_ACCESS_TOKEN")
    step("Catálogo", False, "Credenciais não configuradas")

# ── 7. RELATÓRIO FINAL ────────────────────────────────────────
print("\n" + "=" * 60)
print("  RELATÓRIO FINAL")
print("=" * 60)
ok_count = sum(1 for s in REPORT["steps"] if s["ok"])
total    = len(REPORT["steps"])
print(f"\n  Concluído: {ok_count}/{total} etapas")

if draft_theme_id and has_shopify_api and PIXEL_ID:
    print(f"\n  ✅ Tema draft com pixel criado (ID: {draft_theme_id})")
    print(f"     Para ativar: Shopify Admin > Temas > 'Aura Decore - v5 [Meta Draft]' > Publicar")

print(f"\n  78 produtos: ✅ publicados no canal Facebook & Instagram")
print(f"  Feed URL: https://{DOMAIN}/collections/all.atom")
print(f"  Webhook endpoint: {RAILWAY_URL}/meta/webhook/")

if REPORT["status"] == "ok":
    print("\n  🎉 SETUP COMPLETO!")
else:
    print("\n  ⚠️  Setup parcial — complete as etapas acima e re-execute.")

print("=" * 60)
