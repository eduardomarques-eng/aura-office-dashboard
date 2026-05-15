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

@app.post("/chat")
async def chat_with_ive(body: ChatBody):
    messages = [{"role": m["role"], "content": m["content"]} for m in body.history[-6:]]
    messages.append({"role": "user", "content": body.message})

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=300,
        system=IVE_SYSTEM,
        messages=messages,
    )
    reply = response.content[0].text

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

app.mount("/", StaticFiles(directory="..", html=True), name="static")
