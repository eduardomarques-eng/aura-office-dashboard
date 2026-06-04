"""
windsor_tools.py — Cliente Windsor.ai para agentes da Aura Decore

Agentes integrados:
  ECHO  — auditor semanal (métricas de performance consolidadas)
  GUARD — CFO/financeiro (receita, ROAS, spend)
  SOL   — CRO (conversões, funil, ticket médio)
  REX   — crescimento orgânico (alcance, engajamento)
  MIRA  — SEO (Search Console)
  FEED  — publicação (resultados de posts)

Conectores Windsor (status 2026-06-04):
  facebook         [OK] Meta Ads (Aura Decore) — ativo quando ads rodarem
  facebook_organic [OK] Insights da Pagina Facebook (organico)
  instagram        [OK] Instagram Aura Decore (aura_decoracao)
  instagram_public [OK] Instagram publico @aura_decoracao
  shopify          [PENDENTE] Receita, pedidos, conversao — conectar OAuth
  searchconsole    [PENDENTE] SEO, keywords, cliques organicos Google
  googleanalytics4 [PENDENTE] Trafego, sessoes, eventos

API key: variável WINDSOR_API_KEY no .env
"""

import os
import httpx
from datetime import datetime, timedelta
from typing import Optional

WINDSOR_BASE = "https://connectors.windsor.ai/all"

# Campos relevantes por conector
FIELDS_META_ADS = [
    "date", "campaign", "campaign_status", "spend",
    "impressions", "clicks", "reach", "cpm", "cpc", "ctr",
    "actions_purchase", "action_values_purchase",
    "actions_post_engagement", "actions_link_click",
]

FIELDS_FACEBOOK_ORGANIC = [
    "date", "page_fans",
    "post_impressions", "post_engaged_users",
    "post_reactions_like_total", "post_comments", "post_shares",
]

FIELDS_INSTAGRAM = [
    "date", "profile_followers_count", "profile_media_count",
    "media_like_count", "media_comments_count",
    "likes_per_post", "comments_per_post",
    "media_type", "media_product_type",
]

FIELDS_SHOPIFY = [
    "date", "gross_revenue", "net_revenue", "orders",
    "sessions", "conversion_rate", "average_order_value",
    "total_customers", "returning_customers",
]

FIELDS_SEARCH_CONSOLE = [
    "date", "query", "clicks", "impressions", "ctr", "position",
]

FIELDS_GA4 = [
    "date", "sessions", "users", "new_users", "bounce_rate",
    "average_session_duration", "goal_completions_all",
]


def _get_api_key() -> Optional[str]:
    return os.getenv("WINDSOR_API_KEY")


def _date_range(days: int) -> tuple[str, str]:
    end = datetime.now().date()
    start = end - timedelta(days=days - 1)
    return str(start), str(end)


async def fetch_connector(
    connector: str,
    fields: list[str],
    days: int = 7,
    extra_params: dict | None = None,
) -> dict:
    """Busca dados de qualquer conector Windsor via REST API.
    URL: https://connectors.windsor.ai/all?api_key=KEY&connector=X&fields=a,b,c&date_preset=last_7d
    """
    api_key = _get_api_key()
    if not api_key:
        return {"error": "WINDSOR_API_KEY não configurada no .env", "connector": connector}

    date_from, date_to = _date_range(days)
    params = {
        "api_key": api_key,
        "connector": connector,
        "date_from": date_from,
        "date_to": date_to,
        "fields": ",".join(fields),  # Windsor espera string separada por vírgulas
    }
    if extra_params:
        params.update(extra_params)

    try:
        async with httpx.AsyncClient(timeout=25) as client:
            r = await client.get(WINDSOR_BASE, params=params)
            body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {"raw": r.text[:500]}
            if r.status_code == 200:
                rows = body.get("data", [])
                return {
                    "connector": connector,
                    "date_from": date_from,
                    "date_to": date_to,
                    "rows": len(rows),
                    "data": rows,
                }
            # 500 em conector sem dados ativos é esperado (ex: Meta Ads sem campanhas)
            if r.status_code == 500:
                return {
                    "connector": connector,
                    "rows": 0,
                    "data": [],
                    "note": f"Conector '{connector}' sem dados para o período ou não conectado ainda.",
                }
            return {"error": f"HTTP {r.status_code}: {r.text[:200]}", "connector": connector}
    except httpx.TimeoutException:
        return {"error": "Timeout ao conectar Windsor.ai", "connector": connector}
    except Exception as e:
        return {"error": str(e), "connector": connector}


async def fetch_meta_ads(days: int = 7) -> dict:
    """Meta Ads — campanhas pagas (ativo quando Eduardo lançar tráfego pago)."""
    return await fetch_connector("facebook", FIELDS_META_ADS, days)


async def fetch_facebook_organic(days: int = 7) -> dict:
    """Facebook Organic — insights da Página Aura Decore."""
    return await fetch_connector("facebook_organic", FIELDS_FACEBOOK_ORGANIC, days)


async def fetch_instagram(days: int = 7) -> dict:
    """Instagram @aura_decoracao — alcance, seguidores, engajamento (conector instagram_public)."""
    return await fetch_connector("instagram_public", FIELDS_INSTAGRAM, days)


async def fetch_instagram_insights(days: int = 7) -> dict:
    """Instagram insights detalhados (conector instagram — conta business conectada)."""
    return await fetch_connector("instagram", FIELDS_INSTAGRAM, days)


async def fetch_shopify(days: int = 7) -> dict:
    """Shopify — tenta Windsor primeiro; fallback para Admin API direta."""
    windsor_result = await fetch_connector("shopify", FIELDS_SHOPIFY, days)
    if isinstance(windsor_result, dict) and "error" not in windsor_result and windsor_result.get("rows", 0) > 0:
        return windsor_result
    # Windsor Shopify OAuth com falha → usa Admin API direta
    return await fetch_shopify_direct(days)


async def fetch_shopify_direct(days: int = 7) -> dict:
    """
    Shopify Admin REST API — direto, sem Windsor OAuth.
    Usa SHOPIFY_DOMAIN + SHOPIFY_ADMIN_TOKEN do .env.
    Retorna mesmo formato que fetch_connector() para compatibilidade.
    """
    domain = os.getenv("SHOPIFY_DOMAIN", "")
    token = os.getenv("SHOPIFY_ADMIN_TOKEN", "")
    if not domain or not token:
        return {"error": "SHOPIFY_DOMAIN ou SHOPIFY_ADMIN_TOKEN não configurados", "connector": "shopify_direct"}

    date_from, date_to = _date_range(days)
    # Shopify API 2024-04
    base_url = f"https://{domain}/admin/api/2024-04"
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # 1. Pedidos do período
            orders_resp = await client.get(
                f"{base_url}/orders.json",
                headers=headers,
                params={
                    "status": "any",
                    "created_at_min": f"{date_from}T00:00:00-03:00",
                    "created_at_max": f"{date_to}T23:59:59-03:00",
                    "limit": 250,
                    "fields": "id,total_price,subtotal_price,financial_status,created_at,line_items",
                },
            )
            if orders_resp.status_code != 200:
                return {
                    "error": f"Shopify Admin API HTTP {orders_resp.status_code}: {orders_resp.text[:200]}",
                    "connector": "shopify_direct",
                }

            orders = orders_resp.json().get("orders", [])

            # 2. Clientes totais (para cálculo de retorno)
            customers_resp = await client.get(
                f"{base_url}/customers/count.json",
                headers=headers,
            )
            total_customers = customers_resp.json().get("count", 0) if customers_resp.status_code == 200 else 0

            # 3. Produtos ativos
            products_resp = await client.get(
                f"{base_url}/products/count.json",
                headers=headers,
                params={"status": "active"},
            )
            active_products = products_resp.json().get("count", 0) if products_resp.status_code == 200 else 0

        # Agregar dados por dia
        from collections import defaultdict
        daily: dict = defaultdict(lambda: {"gross_revenue": 0.0, "net_revenue": 0.0, "orders": 0})
        for order in orders:
            day = order.get("created_at", "")[:10]
            gross = float(order.get("total_price") or 0)
            net = float(order.get("subtotal_price") or 0)
            daily[day]["gross_revenue"] += gross
            daily[day]["net_revenue"] += net
            daily[day]["orders"] += 1

        rows = []
        for day in sorted(daily.keys()):
            d = daily[day]
            rows.append({
                "date": day,
                "gross_revenue": round(d["gross_revenue"], 2),
                "net_revenue": round(d["net_revenue"], 2),
                "orders": d["orders"],
                "average_order_value": round(d["gross_revenue"] / d["orders"], 2) if d["orders"] > 0 else 0,
                "sessions": None,        # sessões requerem GA4
                "conversion_rate": None,
            })

        # Totais globais do período
        total_gross = sum(r["gross_revenue"] for r in rows)
        total_orders = sum(r["orders"] for r in rows)
        aov = round(total_gross / total_orders, 2) if total_orders > 0 else 0

        return {
            "connector": "shopify_direct",
            "source": "Shopify Admin API",
            "date_from": date_from,
            "date_to": date_to,
            "rows": len(rows),
            "data": rows,
            "summary": {
                "gross_revenue": round(total_gross, 2),
                "total_orders": total_orders,
                "average_order_value": aov,
                "total_customers": total_customers,
                "active_products": active_products,
            },
        }

    except httpx.TimeoutException:
        return {"error": "Timeout ao conectar Shopify Admin API", "connector": "shopify_direct"}
    except Exception as e:
        return {"error": str(e), "connector": "shopify_direct"}


async def fetch_search_console(days: int = 7, top_queries: bool = True) -> dict:
    """Google Search Console — keywords, cliques, posição média."""
    fields = FIELDS_SEARCH_CONSOLE
    params = {"limit": "50"} if top_queries else {}
    return await fetch_connector("searchconsole", fields, days, params)


async def fetch_ga4(days: int = 7) -> dict:
    """Google Analytics 4 — sessões, usuários, taxa de rejeição."""
    return await fetch_connector("googleanalytics4", FIELDS_GA4, days)


def _summarize_rows(data: dict, numeric_fields: list[str]) -> dict | None:
    """Agrega linhas somando campos numéricos. Retorna None se sem dados ou com erro."""
    if "error" in data:
        return None
    rows = data.get("data", [])
    if not isinstance(rows, list) or not rows:
        return None  # conector sem dados no período ou não conectado
    totals = {f: 0.0 for f in numeric_fields}
    for row in rows:
        for f in numeric_fields:
            val = row.get(f) or 0
            try:
                totals[f] += float(val)
            except (TypeError, ValueError):
                pass
    return {k: round(v, 2) for k, v in totals.items()}


async def get_marketing_summary(days: int = 7) -> dict:
    """
    Resumo consolidado para ECHO/GUARD/SOL — agrega todos os conectores disponíveis.
    Retorna dict com seções por fonte de dados.
    """
    import asyncio

    results = await asyncio.gather(
        fetch_meta_ads(days),
        fetch_facebook_organic(days),
        fetch_instagram(days),
        fetch_shopify(days),
        fetch_search_console(days),
        return_exceptions=True,
    )

    meta, fb_org, ig, shopify, gsc = results

    summary = {
        "period_days": days,
        "generated_at": datetime.now().isoformat(),
        "meta_ads": None,
        "facebook_organic": None,
        "instagram": None,
        "shopify": None,
        "search_console": None,
    }

    def _ok(r):
        return isinstance(r, dict) and "error" not in r and r.get("rows", -1) != 0

    # Meta Ads
    summary["meta_ads"] = _summarize_rows(meta, [
        "spend", "impressions", "clicks", "reach",
        "actions_purchase", "action_values_purchase",
    ]) if _ok(meta) else None

    # Facebook Organic
    if _ok(fb_org):
        summary["facebook_organic"] = _summarize_rows(fb_org, [
            "page_fans", "post_impressions",
            "post_reactions_like_total", "post_comments", "post_shares",
        ])

    # Instagram
    if _ok(ig):
        summary["instagram"] = _summarize_rows(ig, [
            "media_like_count", "media_comments_count",
            "likes_per_post", "comments_per_post",
        ])
        ig_rows = ig.get("data", [])
        if isinstance(ig_rows, list) and ig_rows:
            last = ig_rows[-1]
            if summary["instagram"] is None:
                summary["instagram"] = {}
            summary["instagram"]["followers"] = last.get("profile_followers_count", 0)
            summary["instagram"]["total_posts"] = last.get("profile_media_count", 0)

    # Shopify — suporta resposta Windsor E resposta Admin API direta
    if isinstance(shopify, dict) and "error" not in shopify:
        if shopify.get("summary"):
            # Formato Admin API direta (fetch_shopify_direct)
            s = shopify["summary"]
            summary["shopify"] = {
                "gross_revenue": s.get("gross_revenue", 0),
                "net_revenue": s.get("gross_revenue", 0),  # aproximação
                "orders": s.get("total_orders", 0),
                "average_order_value": s.get("average_order_value", 0),
                "total_customers": s.get("total_customers", 0),
                "active_products": s.get("active_products", 0),
                "source": shopify.get("source", "Shopify"),
            }
        elif _ok(shopify):
            # Formato Windsor conector
            summary["shopify"] = _summarize_rows(shopify, [
                "gross_revenue", "net_revenue", "orders", "sessions",
            ])
            rows = shopify.get("data", [])
            if isinstance(rows, list) and rows and summary["shopify"]:
                last = rows[-1]
                for f in ("conversion_rate", "average_order_value"):
                    if f in last:
                        summary["shopify"][f"{f}_latest"] = last[f]

    # Search Console
    if _ok(gsc):
        summary["search_console"] = _summarize_rows(gsc, ["clicks", "impressions"])
        rows = gsc.get("data", [])
        if isinstance(rows, list) and summary["search_console"] is not None:
            top = sorted(rows, key=lambda r: float(r.get("clicks") or 0), reverse=True)[:5]
            summary["search_console"]["top_queries"] = [
                {"query": r.get("query"), "clicks": r.get("clicks"), "position": r.get("position")}
                for r in top
            ]

    return summary


def format_summary_for_agent(summary: dict, agent: str) -> str:
    """Formata o summary como texto para injetar no system prompt do agente."""
    lines = [f"\n\n📊 DADOS WINDSOR.AI — últimos {summary.get('period_days', 7)} dias:"]

    if summary.get("meta_ads"):
        m = summary["meta_ads"]
        spend = m.get("spend", 0)
        if spend > 0:
            lines.append(
                f"🎯 Meta Ads: gasto R${spend:.2f} | alcance {int(m.get('reach',0)):,} | "
                f"cliques {int(m.get('clicks',0)):,} | compras {int(m.get('actions_purchase',0))} | "
                f"receita ads R${m.get('action_values_purchase',0):.2f}"
            )
        else:
            lines.append("🎯 Meta Ads: sem campanhas ativas (tráfego 100% orgânico)")
    else:
        lines.append("🎯 Meta Ads: conector não disponível")

    if summary.get("facebook_organic"):
        f = summary["facebook_organic"]
        lines.append(
            f"📘 Facebook Orgânico: {int(f.get('post_impressions',0)):,} impressões | "
            f"{int(f.get('post_reactions_like_total',0)):,} reações | "
            f"{int(f.get('post_comments',0)):,} comentários | "
            f"{int(f.get('page_fans',0)):,} fãs da Página"
        )
    else:
        lines.append("📘 Facebook Orgânico: sem dados no período (Página nova — postar para gerar métricas)")

    if summary.get("instagram"):
        i = summary["instagram"]
        lines.append(
            f"📸 Instagram @aura_decoracao: {i.get('followers', '?')} seguidores | "
            f"{i.get('total_posts', '?')} posts | "
            f"{int(i.get('media_like_count',0))} curtidas | "
            f"{int(i.get('media_comments_count',0))} comentários"
        )
    else:
        lines.append("📸 Instagram: sem dados no período")

    if summary.get("shopify"):
        s = summary["shopify"]
        src = s.get("source", "Windsor")
        aov = s.get("average_order_value") or s.get("average_order_value_latest", "—")
        extra = ""
        if s.get("total_customers"):
            extra = f" | {s['total_customers']} clientes | {s.get('active_products',0)} produtos ativos"
        lines.append(
            f"🛍️ Shopify ({src}): R${s.get('gross_revenue',0):.2f} bruto | "
            f"{int(s.get('orders',0))} pedidos | "
            f"ticket médio: R${aov}{extra}"
        )
    else:
        lines.append("🛍️ Shopify: sem dados (Admin API + Windsor indisponíveis)")

    if summary.get("search_console"):
        sc = summary["search_console"]
        tq = sc.get("top_queries", [])
        lines.append(
            f"🔍 Search Console: {int(sc.get('clicks',0)):,} cliques | "
            f"{int(sc.get('impressions',0)):,} impressões"
        )
        if tq:
            lines.append("  Top queries: " + " | ".join(
                f"\"{q['query']}\" ({q['clicks']} cliques, pos {q.get('position','?')})"
                for q in tq[:3]
            ))
    else:
        lines.append("🔍 Search Console: conector não conectado → adicionar em Windsor Dashboard")

    lines.append(f"  ⚙️  Gerado em: {summary.get('generated_at','')[:16]}")
    return "\n".join(lines)


# Mapeamento: agente → conectores relevantes
AGENT_CONNECTORS = {
    "echo":  ["shopify", "instagram_public", "facebook_organic", "searchconsole", "facebook"],
    "guard": ["shopify", "facebook"],
    "sol":   ["shopify", "facebook"],
    "rex":   ["instagram_public", "facebook_organic", "searchconsole", "googleanalytics4"],
    "mira":  ["searchconsole", "googleanalytics4"],
    "feed":  ["instagram_public", "facebook_organic"],
    "zara":  ["instagram_public"],
}
