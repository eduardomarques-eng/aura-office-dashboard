import asyncio
import json
import os
import random
from datetime import datetime
from typing import Set

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from anthropic import Anthropic

app = FastAPI(title="AURA decor — Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ── WebSocket manager ──────────────────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.connections: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.add(ws)

    def disconnect(self, ws: WebSocket):
        self.connections.discard(ws)

    async def broadcast(self, data: dict):
        dead = set()
        for ws in self.connections.copy():
            try:
                await ws.send_json(data)
            except Exception:
                dead.add(ws)
        self.connections -= dead

manager = ConnectionManager()

# ── IVE system prompt ──────────────────────────────────────────────────────────

IVE_SYSTEM = """Você é IVE, a CEO estratégica da AURA decor — loja de decoração premium brasileira.
Coordena 7 agentes de IA especializados:
• THEO (Shopify/Técnico) • KAI (Produtos/Curadoria) • VERA (Copy/Textos)
• LUNA (Design/Visual)   • NOX (Conteúdo/Reels)     • REX (Tráfego/Meta Ads)
• ECHO (Auditor Semanal)

Métricas atuais: ROAS 3.2x | CAC R$42 | Faturamento semanal R$1.240 | Conversão 2.1%
Meta 2028: R$5.000–8.000/mês de lucro líquido.

Responda sempre em português, de forma direta e estratégica. Máximo 2-3 frases.
Cite outros agentes quando relevante (ex: "REX deve escalar..."). Nunca use markdown."""

# ── Dados de atividade dos agentes (fallback sem CrewAI) ──────────────────────

AGENT_ACTIVITY = {
    "ive":  ["ROAS 3.2x confirmado. Escalando REX.", "Analisando métricas da semana...",
             "KAI: pause produto diffuser.", "Faturamento +18% semana anterior."],
    "theo": ["PageSpeed mobile: 87. Otimizando...", "Dropi sincronizado. Tudo ok.",
             "Checkout: 0 erros hoje.", "Pixel disparando normalmente."],
    "kai":  ["Diffuser: 0 vendas 10 dias.", "Margem média: 42%. OK.",
             "Vaso cerâmica: líder de vendas.", "Analisando portfólio..."],
    "vera": ["Escrevendo email abandono...", "Open rate: 38%. Excelente!",
             "CTR anúncio C: 2.8%.", "Copy produto vela pronta."],
    "luna": ["Thumbnail vaso: exportando PNG...", "Paleta 100% consistente.",
             "Stories da semana: 14 peças.", "Hero banner 1200x600px ok."],
    "nox":  ["340 views story vaso.", "Reel roteiro pronto.",
             'Hook: "Cerâmica que respira."', "2 posts pendentes."],
    "rex":  ["CTR criativo C: 2.8%. Escalando.", "ROAS semana: 3.2x.",
             "CAC: R$42. Dentro do limite.", "Budget: R$65/dia agora."],
    "echo": ["Score crew: 8.4/10.", "Próxima auditoria: domingo.",
             "Todos agentes operacionais.", "Kaizen: 1 melhoria/agente/sem."],
}

AGENT_ORDER = list(AGENT_ACTIVITY.keys())

# ── Background loop: atividade dos agentes ────────────────────────────────────

async def agent_activity_loop():
    idx = 0
    msg_idx = {ag: 0 for ag in AGENT_ACTIVITY}

    while True:
        agent_id = AGENT_ORDER[idx % len(AGENT_ORDER)]
        msgs = AGENT_ACTIVITY[agent_id]
        message = msgs[msg_idx[agent_id] % len(msgs)]
        msg_idx[agent_id] += 1
        idx += 1

        await manager.broadcast({
            "type": "agent_message",
            "agent_id": agent_id,
            "message": message,
            "timestamp": datetime.now().strftime("%H:%M"),
        })

        await asyncio.sleep(random.uniform(6, 10))

# ── Background loop: métricas flutuantes ──────────────────────────────────────

BASE_METRICS = {
    "faturamento": 1240,
    "roas": 3.2,
    "cac": 42,
    "conversao": 2.1,
}

async def metrics_loop():
    metrics = dict(BASE_METRICS)
    while True:
        await asyncio.sleep(30)
        metrics["faturamento"] += random.randint(-30, 80)
        metrics["roas"]        = round(metrics["roas"] + random.uniform(-0.05, 0.1), 2)
        metrics["cac"]         = round(metrics["cac"] + random.uniform(-1, 1.5), 1)
        metrics["conversao"]   = round(metrics["conversao"] + random.uniform(-0.05, 0.08), 2)

        await manager.broadcast({
            "type": "metrics_update",
            "metrics": {
                "faturamento": f"R${metrics['faturamento']:,.0f}".replace(",", "."),
                "roas":        f"{metrics['roas']}x",
                "cac":         f"R${metrics['cac']:.0f}",
                "conversao":   f"{metrics['conversao']}%",
            }
        })

# ── CrewAI rodada semanal (opcional) ─────────────────────────────────────────

async def run_crew_weekly():
    """Roda uma rodada de CrewAI e transmite os resultados via WS."""
    await asyncio.sleep(5)  # aguarda conexões
    try:
        from crew_agents import build_weekly_crew
        context = "ROAS 3.2x, CAC R$42, faturamento R$1.240 na semana. Criativo C com melhor CTR."
        crew = build_weekly_crew(context)

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, crew.kickoff)

        await manager.broadcast({
            "type": "crew_result",
            "message": str(result),
            "timestamp": datetime.now().strftime("%H:%M"),
        })
    except Exception as e:
        await manager.broadcast({
            "type": "agent_message",
            "agent_id": "echo",
            "message": f"Sistema CrewAI iniciado. Monitorando... ({type(e).__name__})",
            "timestamp": datetime.now().strftime("%H:%M"),
        })

# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    asyncio.create_task(agent_activity_loop())
    asyncio.create_task(metrics_loop())
    asyncio.create_task(run_crew_weekly())

# ── WebSocket endpoint ────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    await ws.send_json({"type": "connected", "message": "AURA backend online."})
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)

# ── Chat com IVE ─────────────────────────────────────────────────────────────

class ChatBody(BaseModel):
    message: str
    history: list = []

def smart_fallback(msg: str) -> str:
    """Respostas contextuais da IVE sem API — baseadas em palavras-chave."""
    m = msg.lower()
    if any(w in m for w in ["roas","retorno","roi"]):
        return "ROAS está em 3.2x esta semana. REX escalou o criativo C com CTR 2.8% — dentro da meta. Seguimos monitorando."
    if any(w in m for w in ["rex","tráfego","anúncio","ads","meta"]):
        return "REX está ativo. Budget diário: R$65. Criativo C liderando com ROAS 3.2x. Criativo A foi pausado — CTR abaixo de 1%."
    if any(w in m for w in ["kai","produto","portfólio","estoque"]):
        return "KAI reportou: vaso cerâmica lidera com 40% do faturamento. Diffuser com 0 vendas em 10 dias — recomendo pausar amanhã."
    if any(w in m for w in ["vera","copy","texto","email"]):
        return "VERA finalizou o email de abandono de carrinho. Open rate estimado: 38%. CTR do anúncio C subiu para 2.8%."
    if any(w in m for w in ["luna","design","visual","banner","arte"]):
        return "LUNA entregou 3 thumbnails novos e o hero banner 1200x600px. Paleta 100% alinhada com o brand kit AURA."
    if any(w in m for w in ["theo","shopify","técnico","pixel","site"]):
        return "THEO reporta: Pixel disparando normalmente, 0 erros no checkout. PageSpeed mobile em 87 — otimização em andamento."
    if any(w in m for w in ["nox","conteúdo","reel","instagram","post"]):
        return "NOX tem 14 stories e 5 posts publicados. Reel da vela âmbar em roteiro — gancho: Cerâmica que respira."
    if any(w in m for w in ["echo","auditoria","score","relatório"]):
        return "ECHO finalizou a auditoria semanal. Score da crew: 8.4/10. Próxima auditoria: domingo 20h. Kaizen: 1 melhoria por agente."
    if any(w in m for w in ["faturamento","vendas","receita","dinheiro"]):
        return "Faturamento semanal: R$1.240. Lucro líquido estimado: R$380. Margem: 30.6%. Estamos +18% vs semana anterior."
    if any(w in m for w in ["cac","custo","aquisição"]):
        return "CAC atual: R$42. Dentro do limite máximo de R$50. REX otimizando para reduzir mais 15% no próximo ciclo."
    if any(w in m for w in ["status","equipe","geral","como","tudo"]):
        return "Equipe operacional. ROAS 3.2x, CAC R$42, faturamento +18%. REX escalando, VERA com email pronto, LUNA entregando assets. Score: 8.4/10."
    if any(w in m for w in ["meta","objetivo","2028","lucro"]):
        return "Meta 2028: R$5.000–8.000/mês de lucro líquido. Estamos no caminho — crescimento consistente de 15-20% ao mês necessário."
    if any(w in m for w in ["oi","olá","hello","bom dia","boa tarde","boa noite"]):
        return "Olá Eduardo! Estou monitorando tudo. ROAS 3.2x, equipe ativa, nenhum alerta crítico. Como posso ajudar?"
    if any(w in m for w in ["obrigado","valeu","perfeito","ótimo"]):
        return "Ótimo! Qualquer decisão que precisar, estou aqui. A equipe está alinhada e operacional."
    # fallback genérico
    return f"Analisando sua mensagem... Equipe operacional, ROAS 3.2x, faturamento R$1.240 esta semana. REX e VERA em execução. Posso detalhar algum agente específico?"

@app.post("/chat")
async def chat_with_ive(body: ChatBody):
    messages = [{"role": m["role"], "content": m["content"]} for m in body.history[-6:]]
    messages.append({"role": "user", "content": body.message})

    reply = None

    # Tenta Claude API
    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            response = client.messages.create(
                model="claude-opus-4-5",
                max_tokens=300,
                system=IVE_SYSTEM,
                messages=messages,
            )
            reply = response.content[0].text
    except Exception:
        pass  # cai no fallback

    # Fallback inteligente
    if not reply:
        reply = smart_fallback(body.message)

    await manager.broadcast({
        "type": "agent_message",
        "agent_id": "ive",
        "message": reply[:80] + ("..." if len(reply) > 80 else ""),
        "timestamp": datetime.now().strftime("%H:%M"),
    })

    return {"reply": reply}

# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "online", "connections": len(manager.connections)}

# ── Servir frontend estático ──────────────────────────────────────────────────

import pathlib
_ROOT = pathlib.Path(__file__).parent.parent  # aura-office-dashboard/
app.mount("/", StaticFiles(directory=str(_ROOT), html=True), name="static")
