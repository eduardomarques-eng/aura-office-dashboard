# whatsapp_agent.py — Aura Decore · Motor de atendimento WhatsApp Business
# Roteamento: LENA (padrão) → GUARD (reembolso) / SOL (carrinho) / ZARA (parceria)
# LLM: cascata completa via llm_engine (Groq → Together → OpenRouter → Gemini → Anthropic → Ollama)

import asyncio
import os
import re
import time
import json
from typing import Optional
from datetime import datetime

import httpx
from dotenv import load_dotenv
import pathlib as _pl

_ENV_PATH = _pl.Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)

# Motor LLM compartilhado
from llm_engine import llm as _llm_engine

# ── Credenciais Z-API ──────────────────────────────────────────────────────────
ZAPI_INSTANCE  = os.getenv("ZAPI_INSTANCE_ID", "")
ZAPI_TOKEN     = os.getenv("ZAPI_TOKEN", "")
ZAPI_CLIENT    = os.getenv("ZAPI_CLIENT_TOKEN", "")
ZAPI_BASE      = f"https://api.z-api.io/instances/{ZAPI_INSTANCE}/token/{ZAPI_TOKEN}"

# ── Shopify (lookup de pedidos) ─────────────────────────────────────────────────
SHOPIFY_DOMAIN = os.getenv("SHOPIFY_DOMAIN", "")
SHOPIFY_TOKEN  = os.getenv("SHOPIFY_ADMIN_TOKEN", "")

# ── Sessões de conversa (TTL = 2h) ────────────────────────────────────────────
_SESSIONS: dict = {}
_SESSION_TTL = 7200
_MAX_HISTORY = 10

# IDs de mensagens já processadas (deduplicação)
_SEEN_IDS: set = set()
_SEEN_MAX = 500

# ── Horário de atendimento (Brasília) ──────────────────────────────────────────
BUSINESS_HOURS = (8, 22)

# ── Cupons ativos ──────────────────────────────────────────────────────────────
CUPONS = {
    "AURA10":             "10% OFF em qualquer pedido",
    "AURAVIP15":          "15% OFF para clientes VIP",
    "AURAEMBAIXADORA20":  "20% OFF para embaixadoras",
}

# ── System prompts por agente ──────────────────────────────────────────────────
SYSTEM_PROMPTS = {
    "lena": (
        "Você é LENA, atendente da Aura Decore — loja de decoração Japandi/Wabi-sabi.\n"
        "Framework HERO: Help (acolha), Empathize (sinta junto), Resolve (solucione), Offer (ofereça próximo passo).\n"
        "Regras:\n"
        "- Português BR caloroso e natural. Máximo 3 parágrafos curtos. Nunca use 'infelizmente' nem 'protocolo'.\n"
        "- Cupons disponíveis: AURA10 (10% OFF), AURAVIP15 (VIP 15% OFF), AURAEMBAIXADORA20 (embaixadora 20% OFF).\n"
        "- Frete grátis em compras acima de R$199.\n"
        "- Prazo de entrega padrão: 15–25 dias úteis (dropshipping internacional).\n"
        "- Política de troca/devolução: 7 dias após recebimento, produto sem uso.\n"
        "- Site: auradecore.com.br\n"
        "- Se o cliente mencionar reembolso ou cancelamento, diga que vai verificar e retorna em até 1h.\n"
        "- Se perguntar sobre parceria/influencer, diga que vai passar para a equipe de comunidade.\n"
        "- Nunca prometa prazos que não estejam nas regras acima.\n"
        "- Termine sempre com uma pergunta ou oferta de ajuda.\n"
        "- Se receber dados do pedido no contexto, use-os para responder com precisão."
    ),
    "guard": (
        "Você é GUARD, protetor financeiro da Aura Decore.\n"
        "Avalie este pedido de reembolso/cancelamento com base nas políticas:\n"
        "- Devolução: aceita em até 7 dias após recebimento, produto sem uso.\n"
        "- Reembolso: aprovado se dentro da política. Valor máximo sem aprovação manual: R$200.\n"
        "- Acima de R$200 ou casos duvidosos: escale para Eduardo manualmente.\n"
        "Responda em JSON: {\"aprovado\": bool, \"motivo\": str, \"acao\": str, \"mensagem_cliente\": str}\n"
        "mensagem_cliente deve ser em português caloroso (máx 2 frases)."
    ),
    "sol": (
        "Você é SOL, especialista em vendas da Aura Decore.\n"
        "O cliente mencionou carrinho abandonado ou está indeciso sobre comprar.\n"
        "Gere uma mensagem de recuperação irresistível (máx 3 linhas) com:\n"
        "- Urgência suave (sem pressão agressiva)\n"
        "- Cupom AURA10 (10% OFF)\n"
        "- Frete grátis acima de R$199\n"
        "- Link: auradecore.com.br\n"
        "Tom: caloroso, inspirador, Japandi."
    ),
    "zara": (
        "Você é ZARA, community manager da Aura Decore.\n"
        "O cliente quer ser parceiro, influencer ou embaixador.\n"
        "Responda em português caloroso (máx 3 linhas):\n"
        "- Agradeça o interesse com entusiasmo genuíno\n"
        "- Peça para enviar portfólio ou perfil do IG/TikTok\n"
        "- Email: auras.de@gmail.com | Instagram: @auras.decore"
    ),
}

# ── Intents (ordem importa: mais específico primeiro) ─────────────────────────
_INTENT_ORDERED = [
    ("reembolso",  r"\b(reembolso|devolu[cç][aã]o|devolver|estornar|cancelar pedido|cancelamento|estorno|trocar|troca)\b"),
    ("reclamacao", r"\b(errado|problema|defeito|quebrado|danificado|n[aã]o chegou|sumiu|atrasado|raiva|decepcionada)\b"),
    ("parceria",   r"\b(parceria|influencer|embaixadora|divulgar|publi|permuta|colabora[cç][aã]o|ugc)\b"),
    ("pedido",     r"\b(pedido|rastrear|rastreio|entrega|prazo|chegou|despachou|c[oó]digo|nfe|nota fiscal)\b"),
    ("carrinho",   r"\b(carrinho|finalizar|comprar|desconto|cupom|frete|gr[aá]tis|oferta|promo[cç][aã]o)\b"),
    ("produto",    r"\b(produto|pre[cç]o|dispon[ií]vel|vende|quanto custa|valor|estoque|foto|cor|tamanho)\b"),
    ("saudacao",   r"\b(oi|ol[aá]|bom dia|boa tarde|boa noite|hey|hello|e a[ií]|salve)\b"),
]
_INTENT_PATTERNS = dict(_INTENT_ORDERED)

_ORDER_PATTERN = re.compile(r"#?(\d{4,6})")

def classify_intent(text: str) -> str:
    t = text.lower()
    for intent, pattern in _INTENT_ORDERED:
        if re.search(pattern, t):
            return intent
    return "geral"

def route_agent(intent: str) -> str:
    if intent == "reembolso":
        return "guard"
    if intent == "carrinho":
        return "sol"
    if intent == "parceria":
        return "zara"
    return "lena"

def extract_order_number(text: str) -> Optional[str]:
    m = _ORDER_PATTERN.search(text)
    return m.group(1) if m else None

# ── Lookup real de pedido Shopify ──────────────────────────────────────────────
async def _shopify_order_info(order_number: str) -> Optional[str]:
    """Retorna resumo do pedido em texto para injetar no contexto da LENA."""
    if not SHOPIFY_DOMAIN or not SHOPIFY_TOKEN:
        return None
    try:
        url = f"https://{SHOPIFY_DOMAIN}/admin/api/2024-01/orders.json"
        headers = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}
        params  = {"name": f"#{order_number}", "status": "any", "fields": "id,name,email,financial_status,fulfillment_status,created_at,line_items,shipping_lines,tracking_url"}
        async with httpx.AsyncClient(timeout=10) as hc:
            r = await hc.get(url, headers=headers, params=params)
            if r.status_code != 200:
                return None
            orders = r.json().get("orders", [])
            if not orders:
                return f"Pedido #{order_number} não encontrado no sistema."
            o = orders[0]
            items = ", ".join(i["title"] for i in o.get("line_items", []))
            fin   = o.get("financial_status", "—")
            ful   = o.get("fulfillment_status") or "pendente"
            track = o.get("tracking_url") or "link de rastreio não disponível ainda"
            date  = o.get("created_at", "")[:10]
            return (
                f"Pedido #{order_number} | Data: {date} | Itens: {items} | "
                f"Pagamento: {fin} | Entrega: {ful} | Rastreio: {track}"
            )
    except Exception:
        return None

# ── Sessões ────────────────────────────────────────────────────────────────────
def get_or_create_session(phone: str, name: str = "") -> dict:
    now = time.time()
    if phone in _SESSIONS:
        sess = _SESSIONS[phone]
        if now - sess["last_ts"] > _SESSION_TTL:
            _SESSIONS[phone] = {"history": [], "last_ts": now, "name": name or sess.get("name", ""), "state": "open"}
    else:
        _SESSIONS[phone] = {"history": [], "last_ts": now, "name": name, "state": "open"}
    _SESSIONS[phone]["last_ts"] = now
    return _SESSIONS[phone]

def add_to_history(phone: str, role: str, content: str):
    if phone not in _SESSIONS:
        return
    hist = _SESSIONS[phone]["history"]
    hist.append({"role": role, "content": content})
    if len(hist) > _MAX_HISTORY * 2:
        _SESSIONS[phone]["history"] = hist[-(_MAX_HISTORY * 2):]

def is_business_hours() -> bool:
    h = datetime.now().hour
    return BUSINESS_HOURS[0] <= h < BUSINESS_HOURS[1]

# ── Wrapper LLM (usa cascata completa do llm_engine) ─────────────────────────
async def _llm(system: str, messages: list, max_tokens: int = 350) -> str:
    text, _ = await _llm_engine(system, messages, max_tokens=max_tokens)
    return text

# ── Envio Z-API ────────────────────────────────────────────────────────────────
async def _zapi_send(phone: str, message: str):
    if not ZAPI_INSTANCE or not ZAPI_TOKEN:
        return
    url     = f"{ZAPI_BASE}/send-text"
    headers = {"Content-Type": "application/json", "Client-Token": ZAPI_CLIENT}
    try:
        async with httpx.AsyncClient(timeout=10) as hc:
            await hc.post(url, json={"phone": phone, "message": message}, headers=headers)
    except Exception:
        pass

async def _zapi_typing(phone: str):
    """Envia indicador de digitação por 2 segundos."""
    if not ZAPI_INSTANCE or not ZAPI_TOKEN:
        return
    url     = f"{ZAPI_BASE}/send-presence"
    headers = {"Content-Type": "application/json", "Client-Token": ZAPI_CLIENT}
    try:
        async with httpx.AsyncClient(timeout=5) as hc:
            await hc.post(url, json={"phone": phone, "presence": "composing"}, headers=headers)
        await asyncio.sleep(2)
        async with httpx.AsyncClient(timeout=5) as hc:
            await hc.post(url, json={"phone": phone, "presence": "paused"}, headers=headers)
    except Exception:
        pass

# ── Processador principal ──────────────────────────────────────────────────────
async def process_message(phone: str, text: str, name: str = "", message_id: str = "") -> dict:
    """
    Processa mensagem recebida do WhatsApp.
    Retorna {"agent": str, "reply": str, "intent": str, "escalated": bool}
    """
    # Deduplicação
    if message_id:
        if message_id in _SEEN_IDS:
            return {"agent": "none", "reply": "", "intent": "duplicate", "escalated": False}
        _SEEN_IDS.add(message_id)
        if len(_SEEN_IDS) > _SEEN_MAX:
            _SEEN_IDS.clear()

    text = text.strip()
    if not text:
        return {"agent": "none", "reply": "", "intent": "empty", "escalated": False}

    sess   = get_or_create_session(phone, name)
    intent = classify_intent(text)
    primary_agent = route_agent(intent)
    escalated = False

    # Fora do horário comercial
    if not is_business_hours():
        reply = (
            f"Olá{', ' + name if name else ''}! 🌿 Recebemos sua mensagem.\n"
            "Nosso atendimento é das 8h às 22h. Quando abrirmos, "
            "a LENA vai te responder pessoalmente! 💚\n"
            "Enquanto isso, visite: auradecore.com.br"
        )
        return {"agent": "lena", "reply": reply, "intent": intent, "escalated": False}

    # Histórico de conversa (últimas 6 mensagens)
    history = sess["history"][-6:]

    # ── Lookup de pedido Shopify ──────────────────────────────────────────────
    order_context = ""
    order_num = extract_order_number(text)
    if order_num and intent in ("pedido", "reclamacao", "reembolso"):
        info = await _shopify_order_info(order_num)
        if info:
            order_context = f"\n[DADOS DO PEDIDO NA LOJA]: {info}\n"

    # ── GUARD — reembolso/cancelamento ────────────────────────────────────────
    guard_context = ""
    if primary_agent == "guard":
        escalated = True
        guard_result = await _llm(
            SYSTEM_PROMPTS["guard"],
            [{"role": "user", "content": f"Cliente ({name or phone}) solicitou: {text}{order_context}"}],
            max_tokens=250,
        )
        try:
            g = json.loads(guard_result)
            base_reply = g.get("mensagem_cliente", "")
            guard_context = f"\n[GUARD: aprovado={g.get('aprovado')}, motivo={g.get('motivo')}, ação={g.get('acao')}]"
        except Exception:
            base_reply = guard_result
            guard_context = ""

        lena_prompt = (
            f"O cliente ({name or phone}) pediu reembolso/devolução: '{text}'.\n"
            f"{order_context}"
            f"GUARD preparou esta resposta: '{base_reply}'.\n"
            "Reescreva com seu tom HERO — caloroso, empático, sem burocracia."
        )
        reply = await _llm(SYSTEM_PROMPTS["lena"], [{"role": "user", "content": lena_prompt}], max_tokens=300)

    # ── SOL — recuperação de carrinho ─────────────────────────────────────────
    elif primary_agent == "sol":
        reply = await _llm(SYSTEM_PROMPTS["sol"], [{"role": "user", "content": text}], max_tokens=250)

    # ── ZARA — parceria/influencer ────────────────────────────────────────────
    elif primary_agent == "zara":
        reply = await _llm(SYSTEM_PROMPTS["zara"], [{"role": "user", "content": text}], max_tokens=200)

    # ── LENA — atendimento geral ──────────────────────────────────────────────
    else:
        ctx = ""
        if name:
            ctx += f"Nome do cliente: {name}.\n"
        ctx += f"Intent detectado: {intent}.\n"
        if order_context:
            ctx += order_context
        if intent == "pedido":
            ctx += "O cliente pergunta sobre status/entrega. Prazo padrão: 15–25 dias úteis.\n"
        elif intent == "reclamacao":
            ctx += "Cliente com problema. Seja extremamente empático. Peça número do pedido se não tiver.\n"
        elif intent == "saudacao" and not history:
            ctx += "Primeira mensagem desta sessão. Cumprimente com entusiasmo e pergunte como pode ajudar.\n"

        user_msg = ctx + text if ctx else text
        msgs = history + [{"role": "user", "content": user_msg}]
        reply = await _llm(SYSTEM_PROMPTS["lena"], msgs, max_tokens=320)

    add_to_history(phone, "user", text)
    add_to_history(phone, "assistant", reply)

    return {
        "agent":     primary_agent,
        "reply":     reply,
        "intent":    intent,
        "escalated": escalated,
        "guard_log": guard_context if escalated else "",
    }


async def handle_incoming(phone: str, text: str, name: str = "", message_id: str = "") -> dict:
    """Função pública: processa + envia resposta via Z-API."""
    asyncio.create_task(_zapi_typing(phone))
    await asyncio.sleep(1.5)

    result = await process_message(phone, text, name, message_id)

    if result["reply"]:
        asyncio.create_task(_zapi_send(phone, result["reply"]))

    return result
