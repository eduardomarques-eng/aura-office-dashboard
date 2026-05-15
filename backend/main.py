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
    "ive":  [
        "ROAS 3.2x confirmado. Escalando REX.", "Analisando métricas da semana...",
        "KAI: pause produto diffuser.", "Faturamento +18% semana anterior.",
        "REX: aumenta budget +30%.", "Reunião de alinhamento: todos os agentes.",
        "Meta junho: R$2.000 faturamento.", "IVE aprovando copy da VERA.",
    ],
    "theo": [
        "PageSpeed mobile: 87. Otimizando...", "Dropi sincronizado. Tudo ok.",
        "Checkout: 0 erros hoje.", "Pixel disparando normalmente.",
        "AppMax: 3 Pix confirmados.", "Yampi: 0 erros de frete.",
        "SSL renovado. Seguro.", "Core Web Vitals: LCP 2.1s.",
    ],
    "kai":  [
        "Diffuser: 0 vendas 10 dias.", "Margem média: 42%. OK.",
        "Vaso cerâmica: líder de vendas.", "Analisando portfólio...",
        "3 produtos novos no Habitoo.", "Markup: x1.6 aplicado.",
        "Vela âmbar: 40% do faturamento.", "Pausando diffuser amanhã.",
    ],
    "vera": [
        "Escrevendo email abandono...", "Open rate: 38%. Excelente!",
        "CTR anúncio C: 2.8%.", "Copy produto vela pronta.",
        "Headline: Cerâmica que transforma.", "Sequência nurturing: 3 emails.",
        "Angle novo: mãe 35-45 anos.", "A/B test copy iniciado.",
    ],
    "luna": [
        "Thumbnail vaso: exportando PNG...", "Paleta 100% consistente.",
        "Stories da semana: 14 peças.", "Hero banner 1200x600px ok.",
        "Logo versão dark pronta.", "Trust badges atualizados.",
        "Mockup produto finalizado.", "Grid Instagram alinhado.",
    ],
    "nox":  [
        "340 views story vaso.", "Reel roteiro pronto.",
        "Hook: Cerâmica que respira.", "2 posts pendentes.",
        "Engajamento +22% essa semana.", "Collab: @decorminimal aprovada.",
        "Reel antes/depois: gravando.", "Caption vela âmbar pronta.",
    ],
    "rex":  [
        "CTR criativo C: 2.8%. Escalando.", "ROAS semana: 3.2x.",
        "CAC: R$42. Dentro do limite.", "Budget: R$65/dia agora.",
        "Lookalike 1%: testando.", "Criativo D em revisão.",
        "Frequência: 1.8. Saudável.", "Campanha awareness +15% alcance.",
    ],
    "echo": [
        "Score crew: 8.4/10.", "Próxima auditoria: domingo.",
        "Todos agentes operacionais.", "Kaizen: 1 melhoria/agente/sem.",
        "THEO: melhorar PageSpeed.", "KAI: reduzir SKUs inativos.",
        "NOX: aumentar frequência posts.", "Relatório semanal enviado à IVE.",
    ],
}

AGENT_ORDER = list(AGENT_ACTIVITY.keys())

# ── Pares de interação entre agentes ─────────────────────────────────────────
INTERACTION_PAIRS = [
    ("ive", "rex"), ("ive", "kai"), ("ive", "vera"), ("ive", "echo"),
    ("rex", "nox"), ("vera", "kai"), ("luna", "nox"), ("theo", "ive"),
    ("echo", "ive"), ("kai", "vera"), ("luna", "vera"), ("rex", "ive"),
    ("nox", "luna"), ("kai", "ive"), ("echo", "rex"),
]

# ── Background loop: atividade individual dos agentes ────────────────────────

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

        await asyncio.sleep(random.uniform(3, 6))

# ── Background loop: interações entre pares ───────────────────────────────────

async def interaction_loop():
    pair_idx = 0
    await asyncio.sleep(2)
    while True:
        pair = INTERACTION_PAIRS[pair_idx % len(INTERACTION_PAIRS)]
        pair_idx += 1
        await manager.broadcast({
            "type": "interaction",
            "from": pair[0],
            "to": pair[1],
            "timestamp": datetime.now().strftime("%H:%M"),
        })
        await asyncio.sleep(random.uniform(5, 8))

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
    asyncio.create_task(interaction_loop())
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
    """Respostas contextuais da IVE — vocabulário amplo e variado."""
    import re
    m = msg.lower()
    # Remove acentos para matching mais robusto
    m = m.replace('ã','a').replace('á','a').replace('â','a').replace('à','a')
    m = m.replace('é','e').replace('ê','e').replace('í','i').replace('ó','o')
    m = m.replace('ô','o').replace('õ','o').replace('ú','u').replace('ç','c')

    respostas = [
        # Saudações
        (["oi","ola","hello","bom dia","boa tarde","boa noite","hey","eai","e ai","tudo bem","como vai","oi ive"],
         "Olá Eduardo! Estou monitorando tudo. ROAS 3.2x, equipe ativa, nenhum alerta crítico. Como posso ajudar?"),

        # Status geral
        (["status","como esta","como estao","como estamos","tudo","geral","resumo","overview","situacao","o que ta","o que esta","novidades","update","atualizacao"],
         "Equipe operacional. ROAS 3.2x, CAC R$42, faturamento +18%. REX escalando criativo C, VERA finalizou email de abandono, LUNA entregando assets. Score 8.4/10."),

        # ROAS / retorno
        (["roas","retorno","roi","performance","resultado","rendimento","retorno sobre"],
         "ROAS esta em 3.2x esta semana. REX escalou o criativo C com CTR 2.8% — dentro da meta. Seguimos monitorando diariamente."),

        # Faturamento / vendas
        (["faturamento","faturou","vendas","venda","receita","dinheiro","ganho","lucro","lucrei","lucramos","resultado financeiro","quanto vendeu","quanto fez","quanto ganhei","quanto ganhamos"],
         "Faturamento semanal: R$1.240. Lucro liquido estimado: R$380. Margem: 30.6%. Estamos +18% vs semana anterior. Vela ambar lidera com 40%."),

        # CAC / custo
        (["cac","custo","aquisicao","gasto","investimento","orcamento","budget","quanto gasta","quanto custa"],
         "CAC atual: R$42, dentro do limite de R$50. Budget total: R$65/dia no Meta Ads. REX otimizando para reduzir CAC mais 15% no proximo ciclo."),

        # Conversão
        (["conversao","taxa","checkout","carrinho","abandono","compra","pedido"],
         "Taxa de conversao: 2.1%, alta +0.3% na semana. VERA trabalha no email de abandono — estimativa de recuperacao de 12% dos carrinhos."),

        # REX / Tráfego / Anúncios
        (["rex","trafego","anuncio","ads","meta ads","campanha","criativo","facebook","instagram ads","impulsionar","impulsionamento"],
         "REX ativo. Criativo C lidera: CTR 2.8%, ROAS 3.2x. Criativo A pausado — CTR abaixo de 1%. Lookalike 1% em teste. Budget R$65/dia."),

        # KAI / Produtos
        (["kai","produto","produtos","portfolio","estoque","item","catalogo","colecao","sku","fornecedor","habitoo","dropi","importar"],
         "KAI reportou: vaso ceramica lidera com 40% do faturamento. Diffuser com 0 vendas em 10 dias — pausa recomendada. 3 produtos novos no Habitoo em avaliacao."),

        # VERA / Copy
        (["vera","copy","texto","email","escrita","conteudo escrito","descricao","headline","chamada","mensagem"],
         "VERA finalizou email de abandono de carrinho. Open rate estimado: 38%. Angulo novo testando: mae 35-45 anos. Copy do anuncio C com CTR 2.8%."),

        # LUNA / Design
        (["luna","design","visual","banner","arte","imagem","logo","thumbnail","identidade","paleta","cor","canva","layout"],
         "LUNA entregou 3 thumbnails novos e hero banner 1200x600px. Paleta 100% alinhada com brand kit. Logo versao dark finalizada."),

        # THEO / Técnico
        (["theo","shopify","tecnico","pixel","site","pagina","velocidade","pagespeed","checkout erro","erro","bug","integracao","yampi","appmax"],
         "THEO reporta: Pixel disparando normalmente, 0 erros no checkout. PageSpeed mobile em 87 — otimizacao em andamento. Yampi e AppMax sem falhas."),

        # NOX / Conteúdo
        (["nox","conteudo","reel","reels","instagram","post","stories","story","feed","engajamento","viral","video"],
         "NOX publicou 5 posts e 14 stories essa semana. Engajamento +22%. Reel da vela ambar em roteiro — hook: Ceramica que respira. 340 views no story do vaso."),

        # ECHO / Auditoria
        (["echo","auditoria","score","relatorio","analise","revisao","kaizen","avaliacao","nota"],
         "ECHO finalizou auditoria semanal. Score da crew: 8.4/10. Melhorias indicadas: PageSpeed (THEO), frequencia posts (NOX), SKUs inativos (KAI). Proxima: domingo 20h."),

        # Meta / Objetivos
        (["meta","objetivo","2028","plano","planos","crescimento","estrategia","projecao","quanto quer","sonho","visao","futuro","onde","aonde"],
         "Meta 2028: R$5.000-8.000/mes de lucro liquido. Crescimento necessario: 15-20% ao mes. Estamos no caminho — base solida com ROAS 3.2x e margem 30%."),

        # Próximos passos / o que fazer
        (["fazer","proximo","prioridade","foco","acao","o que devo","recomenda","conselho","sugere","sugestao","ajuda","me ajuda"],
         "Prioridade agora: escalar criativo C com REX, pausar diffuser com KAI e ativar email de abandono da VERA. Esses 3 movimentos podem +20% no faturamento essa semana."),

        # Agradecimento
        (["obrigado","valeu","perfeito","otimo","excelente","show","legal","massa","top","entendido","ok"],
         "Otimo! Qualquer decisao que precisar, estou aqui. A equipe esta alinhada e pronta. Vamos crescer."),
    ]

    for palavras, resposta in respostas:
        if any(p in m for p in palavras):
            return resposta

    # Fallback final — varia por hora para parecer vivo
    from datetime import datetime
    h = datetime.now().hour
    variacoes = [
        "Eduardo, pode me dar mais detalhes? Posso analisar qualquer agente, metrica ou produto especifico.",
        "Entendido. Consulte qualquer agente: REX (ads), KAI (produtos), VERA (copy), LUNA (design), THEO (tecnico), NOX (conteudo), ECHO (auditoria).",
        "Processando... Qual area voce quer focar? Trafego, produtos, copy, design ou metricas financeiras?",
        "Estou monitorando tudo. ROAS 3.2x, equipe ativa. Pode perguntar sobre qualquer agente ou metrica.",
    ]
    return variacoes[h % len(variacoes)]

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
