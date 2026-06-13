"""
Integração AppMax (gateway) + Yampi (checkout) para Aura Decore.

AppMax  — gateway de pagamento brasileiro (PIX, boleto, cartão)
          Docs: https://developers.appmax.com.br/
Yampi   — plataforma de checkout / gestão de pedidos BR
          Docs: https://developers.yampi.io/
"""

import os
import hmac
import hashlib
import httpx
from datetime import datetime
from typing import Optional

# ── Credenciais (carregadas via .env) ─────────────────────────────────────────
APPMAX_TOKEN       = os.getenv("APPMAX_TOKEN", "")
APPMAX_BASE        = "https://api.appmax.com.br/api/v3"

YAMPI_TOKEN        = os.getenv("YAMPI_TOKEN", "")
YAMPI_USER_TOKEN   = os.getenv("YAMPI_USER_TOKEN", "")
YAMPI_ALIAS        = os.getenv("YAMPI_ALIAS", "")   # alias da loja no Yampi
YAMPI_BASE         = "https://api.yampi.io/v2"

APPMAX_WEBHOOK_SECRET = os.getenv("APPMAX_WEBHOOK_SECRET", "")


# ── AppMax ─────────────────────────────────────────────────────────────────────

async def appmax_get_orders(page: int = 1, per_page: int = 20) -> dict:
    """Lista pedidos recentes no AppMax."""
    if not APPMAX_TOKEN:
        return {"error": "APPMAX_TOKEN não configurado"}
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(
            f"{APPMAX_BASE}/order",
            headers={"Authorization": f"Bearer {APPMAX_TOKEN}"},
            params={"page": page, "per_page": per_page},
        )
        return r.json() if r.status_code == 200 else {"error": r.text, "status": r.status_code}


async def appmax_get_order(order_id: str) -> dict:
    """Detalhes de um pedido AppMax."""
    if not APPMAX_TOKEN:
        return {"error": "APPMAX_TOKEN não configurado"}
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(
            f"{APPMAX_BASE}/order/{order_id}",
            headers={"Authorization": f"Bearer {APPMAX_TOKEN}"},
        )
        return r.json() if r.status_code == 200 else {"error": r.text, "status": r.status_code}


async def appmax_get_chargebacks(page: int = 1) -> dict:
    """Lista chargebacks — GUARD monitora isso."""
    if not APPMAX_TOKEN:
        return {"error": "APPMAX_TOKEN não configurado"}
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(
            f"{APPMAX_BASE}/chargeback",
            headers={"Authorization": f"Bearer {APPMAX_TOKEN}"},
            params={"page": page},
        )
        return r.json() if r.status_code == 200 else {"error": r.text, "status": r.status_code}


async def appmax_get_summary() -> dict:
    """Resumo financeiro AppMax — receita, conversão, status."""
    if not APPMAX_TOKEN:
        return {"error": "APPMAX_TOKEN não configurado"}
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(
            f"{APPMAX_BASE}/dashboard",
            headers={"Authorization": f"Bearer {APPMAX_TOKEN}"},
        )
        return r.json() if r.status_code == 200 else {"error": r.text, "status": r.status_code}


def appmax_verify_webhook(payload: bytes, signature: str) -> bool:
    """Valida assinatura HMAC do webhook AppMax."""
    if not APPMAX_WEBHOOK_SECRET:
        return True  # sem secret configurado, aceita tudo (dev)
    expected = hmac.new(
        APPMAX_WEBHOOK_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def appmax_classify_event(event_type: str) -> str:
    """Classifica evento AppMax para roteamento de agentes."""
    routing = {
        "order.paid":       "GUARD",   # receita confirmada
        "order.canceled":   "SOL",     # recuperação
        "order.refunded":   "GUARD",   # reembolso → alerta MEI
        "chargeback.open":  "GUARD",   # chargeback crítico
        "chargeback.won":   "GUARD",
        "chargeback.lost":  "GUARD",
        "order.pending":    "LENA",    # aguardando pagamento
    }
    return routing.get(event_type, "IVE")


# ── Yampi ──────────────────────────────────────────────────────────────────────

def _yampi_headers() -> dict:
    return {
        "User-Token": YAMPI_USER_TOKEN,
        "User-Secret-Key": YAMPI_TOKEN,
        "Content-Type": "application/json",
    }


async def yampi_get_orders(page: int = 1, per_page: int = 20) -> dict:
    """Lista pedidos Yampi."""
    if not YAMPI_TOKEN or not YAMPI_ALIAS:
        return {"error": "YAMPI_TOKEN ou YAMPI_ALIAS não configurado"}
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(
            f"{YAMPI_BASE}/{YAMPI_ALIAS}/orders",
            headers=_yampi_headers(),
            params={"page": page, "per_page": per_page},
        )
        return r.json() if r.status_code == 200 else {"error": r.text, "status": r.status_code}


async def yampi_get_order(order_id: str) -> dict:
    """Detalhes de um pedido Yampi."""
    if not YAMPI_TOKEN or not YAMPI_ALIAS:
        return {"error": "YAMPI_TOKEN ou YAMPI_ALIAS não configurado"}
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(
            f"{YAMPI_BASE}/{YAMPI_ALIAS}/orders/{order_id}",
            headers=_yampi_headers(),
        )
        return r.json() if r.status_code == 200 else {"error": r.text, "status": r.status_code}


async def yampi_get_abandoned_carts(page: int = 1) -> dict:
    """Carrinhos abandonados Yampi — SOL processa para recovery."""
    if not YAMPI_TOKEN or not YAMPI_ALIAS:
        return {"error": "YAMPI_TOKEN ou YAMPI_ALIAS não configurado"}
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(
            f"{YAMPI_BASE}/{YAMPI_ALIAS}/abandoned-carts",
            headers=_yampi_headers(),
            params={"page": page},
        )
        return r.json() if r.status_code == 200 else {"error": r.text, "status": r.status_code}


async def yampi_get_customers(page: int = 1) -> dict:
    """Lista clientes Yampi — LENA usa para CX."""
    if not YAMPI_TOKEN or not YAMPI_ALIAS:
        return {"error": "YAMPI_TOKEN ou YAMPI_ALIAS não configurado"}
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(
            f"{YAMPI_BASE}/{YAMPI_ALIAS}/customers",
            headers=_yampi_headers(),
            params={"page": page},
        )
        return r.json() if r.status_code == 200 else {"error": r.text, "status": r.status_code}


async def yampi_update_order_status(order_id: str, status: str) -> dict:
    """Atualiza status de pedido Yampi."""
    if not YAMPI_TOKEN or not YAMPI_ALIAS:
        return {"error": "YAMPI_TOKEN ou YAMPI_ALIAS não configurado"}
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.put(
            f"{YAMPI_BASE}/{YAMPI_ALIAS}/orders/{order_id}",
            headers=_yampi_headers(),
            json={"status": status},
        )
        return r.json() if r.status_code in (200, 201) else {"error": r.text, "status": r.status_code}


async def yampi_summary() -> dict:
    """Resumo operacional Yampi — pedidos hoje, semana, mês."""
    orders = await yampi_get_orders(per_page=50)
    if "error" in orders:
        return orders
    items = orders.get("data", {}).get("data", [])
    today = datetime.now().strftime("%Y-%m-%d")
    today_orders = [o for o in items if o.get("created_at", "").startswith(today)]
    return {
        "total_listed": len(items),
        "today": len(today_orders),
        "today_revenue": sum(float(o.get("total", 0)) for o in today_orders),
    }


# ── Status combinado ───────────────────────────────────────────────────────────

async def payment_health() -> dict:
    """Verifica saúde das integrações de pagamento."""
    appmax_ok = bool(APPMAX_TOKEN)
    yampi_ok  = bool(YAMPI_TOKEN and YAMPI_ALIAS)

    result = {
        "appmax": {
            "configured": appmax_ok,
            "token_set":  appmax_ok,
        },
        "yampi": {
            "configured": yampi_ok,
            "token_set":  bool(YAMPI_TOKEN),
            "alias_set":  bool(YAMPI_ALIAS),
            "user_token_set": bool(YAMPI_USER_TOKEN),
        },
    }

    # Teste de conectividade se configurado
    if appmax_ok:
        try:
            async with httpx.AsyncClient(timeout=8) as c:
                r = await c.get(f"{APPMAX_BASE}/order?per_page=1",
                                headers={"Authorization": f"Bearer {APPMAX_TOKEN}"})
                result["appmax"]["api_reachable"] = r.status_code != 401
                result["appmax"]["api_status"] = r.status_code
        except Exception as e:
            result["appmax"]["api_reachable"] = False
            result["appmax"]["error"] = str(e)

    if yampi_ok:
        try:
            async with httpx.AsyncClient(timeout=8) as c:
                r = await c.get(f"{YAMPI_BASE}/{YAMPI_ALIAS}/orders?per_page=1",
                                headers=_yampi_headers())
                result["yampi"]["api_reachable"] = r.status_code != 401
                result["yampi"]["api_status"] = r.status_code
        except Exception as e:
            result["yampi"]["api_reachable"] = False
            result["yampi"]["error"] = str(e)

    return result
