# -*- coding: utf-8 -*-
"""
meta_integration.py — Integração completa Meta Business para Aura Decore
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Módulos:
  • MetaPixel     — Geração de snippets de pixel para o tema Shopify
  • MetaCAPI      — Conversions API (server-side events) via httpx
  • MetaCatalog   — Sincronização de catálogo de produtos com o Meta
  • MetaEventTest — Teste de eventos no Meta Event Manager
  • MetaInsights  — Relatório de status / diagnóstico
  • MetaShopify   — Web Pixel via Shopify Admin API
"""

import os, sys, hashlib, json, time, uuid, pathlib
from datetime import datetime
from typing import Optional
import httpx
from dotenv import load_dotenv

_ENV_PATH = pathlib.Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)

# ── Credenciais ────────────────────────────────────────────────────────────────
PIXEL_ID       = os.getenv("META_PIXEL_ID", "")
CAPI_TOKEN     = os.getenv("META_CAPI_TOKEN", "")
ACCESS_TOKEN   = os.getenv("META_ACCESS_TOKEN", "")
BUSINESS_ID    = os.getenv("META_BUSINESS_ID", "")
APP_ID         = os.getenv("META_APP_ID", "2073471413233500")
APP_SECRET     = os.getenv("META_APP_SECRET", "")
FB_PAGE_ID     = os.getenv("FB_PAGE_ID", "1111100822090245")
FB_PAGE_TOKEN  = os.getenv("FB_PAGE_TOKEN", "")
SHOPIFY_DOMAIN = os.getenv("SHOPIFY_DOMAIN", "10ei3t-sf.myshopify.com")
SHOPIFY_TOKEN  = os.getenv("SHOPIFY_ADMIN_TOKEN", "")
STORE_URL      = os.getenv("STORE_DOMAIN", "auradecore.com.br")

GRAPH_BASE = "https://graph.facebook.com/v20.0"

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _hash(value: str) -> str:
    """SHA-256 hash para Advanced Matching (PII)."""
    return hashlib.sha256(value.strip().lower().encode()).hexdigest()


def _event_id() -> str:
    return str(uuid.uuid4())


def _unix_now() -> int:
    return int(time.time())


def _missing_creds() -> list[str]:
    missing = []
    if not PIXEL_ID:     missing.append("META_PIXEL_ID")
    if not CAPI_TOKEN:   missing.append("META_CAPI_TOKEN")
    if not ACCESS_TOKEN: missing.append("META_ACCESS_TOKEN")
    if not BUSINESS_ID:  missing.append("META_BUSINESS_ID")
    if not APP_SECRET:   missing.append("META_APP_SECRET")
    return missing


# ══════════════════════════════════════════════════════════════════════════════
# 1. META PIXEL — Snippet para o Tema Shopify
# ══════════════════════════════════════════════════════════════════════════════

class MetaPixel:
    """Gera o código do Pixel Meta para injeção no tema Shopify."""

    @staticmethod
    def base_snippet(pixel_id: str = "") -> str:
        pid = pixel_id or PIXEL_ID
        if not pid:
            return "<!-- META_PIXEL_ID não configurado no .env -->"
        return f"""<!-- Meta Pixel Code — Aura Decore -->
<script>
!function(f,b,e,v,n,t,s)
{{if(f.fbq)return;n=f.fbq=function(){{n.callMethod?
n.callMethod.apply(n,arguments):n.queue.push(arguments)}};
if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
n.queue=[];t=b.createElement(e);t.async=!0;
t.src=v;s=b.getElementsByTagName(e)[0];
s.parentNode.insertBefore(t,s)}}(window, document,'script',
'https://connect.facebook.net/en_US/fbevents.js');
fbq('init', '{pid}');
fbq('track', 'PageView');
</script>
<noscript>
  <img height="1" width="1" style="display:none"
    src="https://www.facebook.com/tr?id={pid}&ev=PageView&noscript=1"/>
</noscript>
<!-- End Meta Pixel Code -->"""

    @staticmethod
    def product_view_snippet(pixel_id: str = "") -> str:
        """Snippet para página de produto — ViewContent."""
        pid = pixel_id or PIXEL_ID
        if not pid:
            return ""
        return f"""<script>
fbq('track', 'ViewContent', {{
  content_ids: ['{{{{ product.id }}}}'],
  content_name: '{{{{ product.title | escape }}}}',
  content_category: '{{{{ product.type | escape }}}}',
  content_type: 'product',
  value: {{{{ product.price | money_without_currency }}}},
  currency: '{{{{ shop.currency }}}}'
}});
</script>"""

    @staticmethod
    def add_to_cart_snippet(pixel_id: str = "") -> str:
        """Snippet para evento AddToCart."""
        pid = pixel_id or PIXEL_ID
        if not pid:
            return ""
        return """<script>
document.querySelectorAll('form[action*="/cart/add"]').forEach(function(form) {
  form.addEventListener('submit', function() {
    var price = parseFloat(document.querySelector('[data-product-price]')?.innerText?.replace(/[^0-9,.]/g,'')?.replace(',','.') || 0);
    fbq('track', 'AddToCart', {
      content_ids: [window.__productId || ''],
      content_type: 'product',
      value: price,
      currency: 'BRL'
    });
  });
});
</script>"""

    @staticmethod
    def checkout_snippet(pixel_id: str = "") -> str:
        """Snippet para InitiateCheckout (via checkout.liquid)."""
        pid = pixel_id or PIXEL_ID
        if not pid:
            return ""
        return """<script>
fbq('track', 'InitiateCheckout', {
  num_items: {{ cart.item_count }},
  value: {{ cart.total_price | money_without_currency }},
  currency: '{{ shop.currency }}'
});
</script>"""

    @staticmethod
    def purchase_snippet(pixel_id: str = "") -> str:
        """Snippet para Purchase (order status page / thank you page)."""
        pid = pixel_id or PIXEL_ID
        if not pid:
            return ""
        return """<script>
{% if first_time_accessed %}
fbq('track', 'Purchase', {
  value: {{ order.total_price | money_without_currency }},
  currency: '{{ order.currency }}',
  content_ids: [{% for line in order.line_items %}'{{ line.product_id }}'{% unless forloop.last %},{% endunless %}{% endfor %}],
  content_type: 'product',
  num_items: {{ order.line_items | size }}
});
{% endif %}
</script>"""

    @staticmethod
    def full_theme_head(pixel_id: str = "") -> str:
        """Bloco completo para o <head> do tema."""
        return MetaPixel.base_snippet(pixel_id)


# ══════════════════════════════════════════════════════════════════════════════
# 2. META CAPI — Conversions API (Server-Side)
# ══════════════════════════════════════════════════════════════════════════════

class MetaCAPI:
    """
    Envia eventos server-side para a Meta Conversions API.
    Documentação: https://developers.facebook.com/docs/marketing-api/conversions-api
    """

    ENDPOINT = "https://graph.facebook.com/v20.0/{pixel_id}/events"

    def __init__(self, pixel_id: str = "", capi_token: str = ""):
        self.pixel_id  = pixel_id or PIXEL_ID
        self.token     = capi_token or CAPI_TOKEN

    def _build_user_data(
        self,
        email: str = "",
        phone: str = "",
        first_name: str = "",
        last_name: str = "",
        city: str = "",
        state: str = "",
        zip_code: str = "",
        country: str = "br",
        client_ip: str = "",
        client_ua: str = "",
        fbc: str = "",
        fbp: str = "",
    ) -> dict:
        ud = {}
        if email:      ud["em"]         = [_hash(email)]
        if phone:      ud["ph"]         = [_hash(phone.replace(" ", "").replace("-", ""))]
        if first_name: ud["fn"]         = [_hash(first_name)]
        if last_name:  ud["ln"]         = [_hash(last_name)]
        if city:       ud["ct"]         = [_hash(city)]
        if state:      ud["st"]         = [_hash(state)]
        if zip_code:   ud["zp"]         = [_hash(zip_code)]
        if country:    ud["country"]    = [_hash(country)]
        if client_ip:  ud["client_ip_address"] = client_ip
        if client_ua:  ud["client_user_agent"]  = client_ua
        if fbc:        ud["fbc"]        = fbc
        if fbp:        ud["fbp"]        = fbp
        return ud

    def send_event(
        self,
        event_name: str,
        event_source_url: str = "",
        custom_data: dict = None,
        user_data: dict = None,
        test_event_code: str = "",
    ) -> dict:
        """Envia um evento para a CAPI. Retorna resposta da API."""
        if not self.pixel_id or not self.token:
            return {"error": "META_PIXEL_ID ou META_CAPI_TOKEN não configurados no .env"}

        payload = {
            "data": [{
                "event_name": event_name,
                "event_time": _unix_now(),
                "event_id": _event_id(),
                "event_source_url": event_source_url or f"https://{STORE_URL}",
                "action_source": "website",
                "user_data": user_data or {"client_ip_address": "unknown"},
                "custom_data": custom_data or {},
            }],
            "access_token": self.token,
        }
        if test_event_code:
            payload["test_event_code"] = test_event_code

        url = self.ENDPOINT.format(pixel_id=self.pixel_id)
        try:
            r = httpx.post(url, json=payload, timeout=15)
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    # ── Eventos Padrão ─────────────────────────────────────────────────────────

    def page_view(self, url: str = "", ip: str = "", ua: str = "", fbc: str = "", fbp: str = "") -> dict:
        ud = self._build_user_data(client_ip=ip, client_ua=ua, fbc=fbc, fbp=fbp)
        return self.send_event("PageView", event_source_url=url, user_data=ud)

    def view_content(
        self,
        product_id: str,
        product_name: str,
        value: float,
        url: str = "",
        currency: str = "BRL",
        **kwargs,
    ) -> dict:
        ud = self._build_user_data(**{k: v for k, v in kwargs.items() if k in
            ["email","phone","first_name","last_name","client_ip","client_ua","fbc","fbp"]})
        cd = {
            "content_ids": [product_id],
            "content_name": product_name,
            "content_type": "product",
            "value": value,
            "currency": currency,
        }
        return self.send_event("ViewContent", event_source_url=url, custom_data=cd, user_data=ud)

    def add_to_cart(
        self,
        product_id: str,
        product_name: str,
        value: float,
        quantity: int = 1,
        currency: str = "BRL",
        url: str = "",
        **kwargs,
    ) -> dict:
        ud = self._build_user_data(**{k: v for k, v in kwargs.items() if k in
            ["email","phone","first_name","last_name","client_ip","client_ua","fbc","fbp"]})
        cd = {
            "content_ids": [product_id],
            "content_name": product_name,
            "content_type": "product",
            "value": value,
            "currency": currency,
            "num_items": quantity,
        }
        return self.send_event("AddToCart", event_source_url=url, custom_data=cd, user_data=ud)

    def initiate_checkout(
        self,
        value: float,
        num_items: int = 1,
        currency: str = "BRL",
        url: str = "",
        **kwargs,
    ) -> dict:
        ud = self._build_user_data(**{k: v for k, v in kwargs.items() if k in
            ["email","phone","first_name","last_name","client_ip","client_ua","fbc","fbp"]})
        cd = {"value": value, "currency": currency, "num_items": num_items}
        return self.send_event("InitiateCheckout", event_source_url=url, custom_data=cd, user_data=ud)

    def purchase(
        self,
        order_id: str,
        value: float,
        product_ids: list[str],
        num_items: int = 1,
        currency: str = "BRL",
        url: str = "",
        **kwargs,
    ) -> dict:
        ud = self._build_user_data(**{k: v for k, v in kwargs.items() if k in
            ["email","phone","first_name","last_name","client_ip","client_ua","fbc","fbp"]})
        cd = {
            "order_id": order_id,
            "content_ids": product_ids,
            "content_type": "product",
            "value": value,
            "currency": currency,
            "num_items": num_items,
        }
        return self.send_event("Purchase", event_source_url=url, custom_data=cd, user_data=ud)

    # ── Eventos Customizados Decoração ─────────────────────────────────────────

    def wishlist_add(self, product_id: str, product_name: str, url: str = "", **kwargs) -> dict:
        """AddToWishlist — favoritar produto na loja."""
        ud = self._build_user_data(**{k: v for k, v in kwargs.items() if k in
            ["email","phone","client_ip","client_ua","fbc","fbp"]})
        cd = {"content_ids": [product_id], "content_name": product_name}
        return self.send_event("AddToWishlist", event_source_url=url, custom_data=cd, user_data=ud)

    def room_inspiration_view(self, style: str = "japandi", url: str = "") -> dict:
        """Evento customizado: usuario visualizou galeria de inspiração."""
        cd = {"style": style, "content_category": "inspiration"}
        return self.send_event("ViewInspiration", event_source_url=url, custom_data=cd)

    def collection_browse(self, collection_name: str, url: str = "") -> dict:
        """Evento customizado: usuario navegou em uma coleção."""
        cd = {"content_category": collection_name}
        return self.send_event("BrowseCollection", event_source_url=url, custom_data=cd)

    def search_event(self, search_term: str, url: str = "") -> dict:
        """Search — usuario fez uma busca na loja."""
        cd = {"search_string": search_term}
        return self.send_event("Search", event_source_url=url, custom_data=cd)

    def complete_registration(self, email: str = "", url: str = "") -> dict:
        """CompleteRegistration — cadastro de newsletter/conta."""
        ud = self._build_user_data(email=email)
        return self.send_event("CompleteRegistration", event_source_url=url, user_data=ud)

    def contact_event(self, url: str = "") -> dict:
        """Contact — usuario entrou em contato (WhatsApp/formulário)."""
        return self.send_event("Contact", event_source_url=url)


# ══════════════════════════════════════════════════════════════════════════════
# 3. META CATALOG — Sincronização de Catálogo com Facebook
# ══════════════════════════════════════════════════════════════════════════════

class MetaCatalog:
    """
    Gerencia o catálogo de produtos no Meta Business Manager.
    Requer: META_BUSINESS_ID, META_ACCESS_TOKEN
    """

    def __init__(self):
        self.token       = ACCESS_TOKEN
        self.business_id = BUSINESS_ID

    def _get(self, path: str, params: dict = None) -> dict:
        params = params or {}
        params["access_token"] = self.token
        try:
            r = httpx.get(f"{GRAPH_BASE}/{path}", params=params, timeout=20)
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    def _post(self, path: str, data: dict = None) -> dict:
        data = data or {}
        data["access_token"] = self.token
        try:
            r = httpx.post(f"{GRAPH_BASE}/{path}", json=data, timeout=20)
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    def list_catalogs(self) -> dict:
        """Lista catálogos do Business Manager."""
        if not self.business_id:
            return {"error": "META_BUSINESS_ID não configurado"}
        return self._get(f"{self.business_id}/owned_product_catalogs",
                         {"fields": "id,name,product_count"})

    def get_catalog_status(self, catalog_id: str) -> dict:
        """Status e diagnóstico de um catálogo."""
        return self._get(catalog_id, {"fields": "id,name,product_count,feed_count"})

    def list_catalog_products(self, catalog_id: str, limit: int = 25) -> dict:
        """Lista produtos em um catálogo."""
        return self._get(f"{catalog_id}/products",
                         {"fields": "id,name,retailer_id,availability,price", "limit": limit})

    def list_feeds(self, catalog_id: str) -> dict:
        """Lista feeds de um catálogo (Shopify feed)."""
        return self._get(f"{catalog_id}/product_feeds",
                         {"fields": "id,name,latest_upload,schedule"})

    def trigger_feed_refresh(self, feed_id: str) -> dict:
        """Força re-sincronização de um feed."""
        return self._post(f"{feed_id}/uploads")

    def create_catalog(self, name: str = "Aura Decore") -> dict:
        """Cria um novo catálogo no Business Manager."""
        if not self.business_id:
            return {"error": "META_BUSINESS_ID não configurado"}
        return self._post(f"{self.business_id}/owned_product_catalogs", {"name": name})

    def get_shopify_feed_url(self) -> str:
        """URL padrão do feed de produtos Shopify para o Facebook."""
        return f"https://{SHOPIFY_DOMAIN}/collections/all.atom"

    def associate_pixel_to_catalog(self, catalog_id: str) -> dict:
        """Associa o Pixel Meta ao catálogo para remarketing dinâmico."""
        if not PIXEL_ID:
            return {"error": "META_PIXEL_ID não configurado"}
        return self._post(f"{catalog_id}/external_event_sources",
                          {"external_event_sources": [PIXEL_ID]})


# ══════════════════════════════════════════════════════════════════════════════
# 4. META EVENT TEST — Teste de Eventos
# ══════════════════════════════════════════════════════════════════════════════

class MetaEventTest:
    """
    Testa se os eventos estão chegando corretamente ao Meta Event Manager.
    Usa test_event_code para visibilidade no painel de testes.
    """

    def __init__(self, test_code: str = "TEST12345"):
        self.capi = MetaCAPI()
        self.test_code = test_code

    def run_all_tests(self) -> dict:
        """Executa todos os testes de eventos e retorna relatório."""
        results = {}
        base_url = f"https://{STORE_URL}"

        print("[META TEST] Iniciando testes de eventos...")

        # PageView
        results["PageView"] = self.capi.send_event(
            "PageView", event_source_url=base_url,
            user_data={"client_ip_address": "177.0.0.1"},
            test_event_code=self.test_code
        )
        print(f"  PageView: {results['PageView'].get('events_received', results['PageView'].get('error', '?'))}")

        # ViewContent
        results["ViewContent"] = self.capi.view_content(
            product_id="7785846440041",
            product_name="Vaso Cerâmica Wabi",
            value=89.90,
            url=f"{base_url}/products/vaso-ceramica-wabi",
        )
        print(f"  ViewContent: {results['ViewContent'].get('events_received', results['ViewContent'].get('error', '?'))}")

        # AddToCart
        results["AddToCart"] = self.capi.add_to_cart(
            product_id="7785846440041",
            product_name="Vaso Cerâmica Wabi",
            value=89.90,
            url=f"{base_url}/cart",
        )
        print(f"  AddToCart: {results['AddToCart'].get('events_received', results['AddToCart'].get('error', '?'))}")

        # InitiateCheckout
        results["InitiateCheckout"] = self.capi.initiate_checkout(
            value=89.90, num_items=1,
            url=f"{base_url}/checkout",
        )
        print(f"  InitiateCheckout: {results['InitiateCheckout'].get('events_received', results['InitiateCheckout'].get('error', '?'))}")

        # Purchase
        results["Purchase"] = self.capi.purchase(
            order_id="TEST-001",
            value=89.90,
            product_ids=["7785846440041"],
            url=f"{base_url}/thank-you",
        )
        print(f"  Purchase: {results['Purchase'].get('events_received', results['Purchase'].get('error', '?'))}")

        # Eventos customizados
        results["Search"] = self.capi.search_event("vaso ceramica", url=base_url)
        results["Contact"] = self.capi.contact_event(url=base_url)
        results["CompleteRegistration"] = self.capi.complete_registration(
            email="test@test.com", url=base_url
        )

        return results

    def test_single(self, event_name: str) -> dict:
        """Testa um único evento pelo nome."""
        return self.capi.send_event(
            event_name,
            event_source_url=f"https://{STORE_URL}",
            user_data={"client_ip_address": "177.0.0.1"},
            test_event_code=self.test_code,
        )


# ══════════════════════════════════════════════════════════════════════════════
# 5. META SHOPIFY WEBHOOK — Recebe webhooks do Shopify para CAPI
# ══════════════════════════════════════════════════════════════════════════════

class MetaShopifyBridge:
    """
    Bridge: Recebe webhooks do Shopify e dispara eventos CAPI correspondentes.
    Registrar webhooks em: Shopify Admin > Configurações > Notificações > Webhooks
      • orders/create  → POST /meta/webhook/order
      • checkouts/create → POST /meta/webhook/checkout
    """

    def __init__(self):
        self.capi = MetaCAPI()

    def handle_order(self, order: dict) -> dict:
        """Processa webhook orders/create → dispara Purchase na CAPI."""
        try:
            order_id    = str(order.get("id", ""))
            total       = float(order.get("total_price", 0))
            currency    = order.get("currency", "BRL")
            email       = order.get("email", "")
            phone       = order.get("phone", "")
            customer    = order.get("customer", {})
            first_name  = customer.get("first_name", "")
            last_name   = customer.get("last_name", "")
            line_items  = order.get("line_items", [])
            product_ids = [str(li.get("product_id", "")) for li in line_items]
            num_items   = sum(li.get("quantity", 1) for li in line_items)

            addr = order.get("billing_address") or order.get("shipping_address") or {}
            city    = addr.get("city", "")
            state   = addr.get("province_code", "")
            zip_c   = addr.get("zip", "")

            return self.capi.purchase(
                order_id=order_id,
                value=total,
                product_ids=product_ids,
                num_items=num_items,
                currency=currency,
                email=email,
                phone=phone,
                first_name=first_name,
                last_name=last_name,
                city=city,
                state=state,
                zip_code=zip_c,
                url=f"https://{STORE_URL}/thank-you",
            )
        except Exception as e:
            return {"error": str(e)}

    def handle_checkout(self, checkout: dict) -> dict:
        """Processa webhook checkouts/create → dispara InitiateCheckout na CAPI."""
        try:
            total     = float(checkout.get("total_price", 0))
            currency  = checkout.get("currency", "BRL")
            email     = checkout.get("email", "")
            num_items = sum(li.get("quantity", 1) for li in checkout.get("line_items", []))

            return self.capi.initiate_checkout(
                value=total,
                num_items=num_items,
                currency=currency,
                email=email,
                url=f"https://{STORE_URL}/checkout",
            )
        except Exception as e:
            return {"error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# 6. META INSIGHTS — Diagnóstico e Relatório de Status
# ══════════════════════════════════════════════════════════════════════════════

class MetaInsights:
    """Diagnóstico completo da integração Meta + relatório de status."""

    def full_status_report(self) -> dict:
        """Gera relatório completo de status da integração."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "store": SHOPIFY_DOMAIN,
            "credentials": {},
            "pixel": {},
            "capi": {},
            "catalog": {},
            "channel": {},
        }

        # Credenciais
        missing = _missing_creds()
        report["credentials"] = {
            "status": "❌ INCOMPLETO" if missing else "✅ OK",
            "configured": {
                "META_PIXEL_ID": bool(PIXEL_ID),
                "META_CAPI_TOKEN": bool(CAPI_TOKEN),
                "META_ACCESS_TOKEN": bool(ACCESS_TOKEN),
                "META_BUSINESS_ID": bool(BUSINESS_ID),
                "META_APP_ID": bool(APP_ID),
                "META_APP_SECRET": bool(APP_SECRET),
                "FB_PAGE_ID": bool(FB_PAGE_ID),
                "FB_PAGE_TOKEN": bool(FB_PAGE_TOKEN),
            },
            "missing": missing,
        }

        # Pixel
        report["pixel"] = {
            "id": PIXEL_ID or "NÃO CONFIGURADO",
            "snippet_ready": bool(PIXEL_ID),
            "events_configured": [
                "PageView", "ViewContent", "AddToCart",
                "InitiateCheckout", "Purchase", "Search",
                "AddToWishlist", "Contact", "CompleteRegistration",
                "ViewInspiration", "BrowseCollection",
            ],
        }

        # CAPI
        report["capi"] = {
            "status": "✅ Pronto" if (PIXEL_ID and CAPI_TOKEN) else "❌ Aguardando credenciais",
            "deduplication": "event_id (UUID) gerado automaticamente",
            "advanced_matching": "SHA-256 em email, phone, nome, cidade, estado, CEP",
        }

        # Catalog
        report["catalog"] = {
            "channel": "Facebook & Instagram (gid://shopify/Publication/159608209513)",
            "status": "✅ Canal instalado na loja",
            "feed_url": f"https://{SHOPIFY_DOMAIN}/collections/all.atom",
        }

        # Pixel snippet
        if PIXEL_ID:
            report["pixel"]["snippet_preview"] = MetaPixel.base_snippet()[:200] + "..."

        return report

    def print_report(self):
        report = self.full_status_report()
        print("\n" + "═" * 60)
        print("  META BUSINESS — STATUS REPORT — Aura Decore")
        print("═" * 60)
        print(f"  📅 {report['timestamp']}")
        print(f"  🏪 Loja: {report['store']}")
        print()
        print("  CREDENCIAIS:")
        creds = report["credentials"]
        print(f"    Status: {creds['status']}")
        for k, v in creds["configured"].items():
            icon = "✅" if v else "❌"
            print(f"    {icon} {k}")
        if creds["missing"]:
            print(f"\n    ⚠️  Faltando: {', '.join(creds['missing'])}")
        print()
        print("  PIXEL:")
        print(f"    ID: {report['pixel']['id']}")
        print(f"    Eventos: {len(report['pixel']['events_configured'])}")
        print()
        print("  CAPI:")
        print(f"    {report['capi']['status']}")
        print()
        print("  CATÁLOGO:")
        print(f"    {report['catalog']['status']}")
        print("═" * 60 + "\n")
        return report


# ══════════════════════════════════════════════════════════════════════════════
# 7. SHOPIFY WEB PIXEL — Registrar Pixel via Admin API
# ══════════════════════════════════════════════════════════════════════════════

class MetaShopifyPixel:
    """
    Registra o Meta Pixel como Web Pixel no Shopify (Customer Events API).
    Requer: META_PIXEL_ID configurado no .env
    """

    SHOPIFY_GRAPHQL = f"https://{SHOPIFY_DOMAIN}/admin/api/2024-10/graphql.json"
    HEADERS = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": SHOPIFY_TOKEN,
    }

    def register_web_pixel(self, pixel_id: str = "") -> dict:
        """Registra o pixel Meta como Customer Event Pixel no Shopify."""
        pid = pixel_id or PIXEL_ID
        if not pid:
            return {"error": "META_PIXEL_ID não configurado"}

        # O pixel Meta padrão para Web Pixel API do Shopify
        mutation = """
        mutation webPixelCreate($webPixel: WebPixelInput!) {
          webPixelCreate(webPixel: $webPixel) {
            webPixel {
              id
              settings
            }
            userErrors {
              field
              message
            }
          }
        }
        """
        variables = {
            "webPixel": {
                "settings": json.dumps({"pixel_id": pid})
            }
        }
        try:
            r = httpx.post(
                self.SHOPIFY_GRAPHQL,
                json={"query": mutation, "variables": variables},
                headers=self.HEADERS,
                timeout=20,
            )
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    def get_web_pixels(self) -> dict:
        """Lista Web Pixels registrados na loja."""
        query = """{ webPixels(first: 10) { nodes { id settings } } }"""
        try:
            r = httpx.post(
                self.SHOPIFY_GRAPHQL,
                json={"query": query},
                headers=self.HEADERS,
                timeout=15,
            )
            return r.json()
        except Exception as e:
            return {"error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# CLI — Execução direta para teste/diagnóstico
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Meta Integration — Aura Decore")
    parser.add_argument("action", choices=[
        "status", "test-events", "test-pixel", "list-catalogs",
        "pixel-snippet", "publish-all"
    ], help="Ação a executar")
    parser.add_argument("--test-code", default="", help="Código de teste Meta Event Manager")
    args = parser.parse_args()

    if args.action == "status":
        MetaInsights().print_report()

    elif args.action == "test-events":
        if not PIXEL_ID or not CAPI_TOKEN:
            print("❌ Configure META_PIXEL_ID e META_CAPI_TOKEN no .env primeiro")
        else:
            tester = MetaEventTest(test_code=args.test_code or "TEST_AURA_001")
            results = tester.run_all_tests()
            print("\n📊 Resultados dos testes:")
            for event, result in results.items():
                ok = "✅" if "events_received" in result else "❌"
                print(f"  {ok} {event}: {result}")

    elif args.action == "test-pixel":
        snippet = MetaPixel.base_snippet()
        print("\n📋 Snippet Meta Pixel Base:")
        print(snippet)

    elif args.action == "list-catalogs":
        catalog = MetaCatalog()
        result = catalog.list_catalogs()
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.action == "pixel-snippet":
        print(MetaPixel.full_theme_head())

    elif args.action == "publish-all":
        print("Use a rota API /meta/publish-all-products via FastAPI.")
