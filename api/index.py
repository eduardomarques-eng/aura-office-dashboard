# -*- coding: utf-8 -*-
"""
Aura Decore HQ — API Vercel (Serverless)
FastAPI rodando como serverless function no Vercel.
Acesso global HTTPS — sem precisar de rede local.
"""
import os, json, asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel

# ── LLM Clients ──────────────────────────────────────────────────────────────
try:
    from anthropic import Anthropic
    _ant = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY",""))
except Exception:
    _ant = None

try:
    from groq import Groq
    _groq = Groq(api_key=os.getenv("GROQ_API_KEY",""), timeout=12)
except Exception:
    _groq = None

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="Aura Decore HQ — Cloud")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

BRT = timezone(timedelta(hours=-3))
def _now(): return datetime.now(BRT).strftime("%H:%M")
def _ts():  return datetime.now(BRT).strftime("%Y-%m-%d %H:%M")

# ── In-memory state (persiste dentro de uma instância warm) ───────────────────
_ACTIVITY: list[dict] = []
_MARATHON: dict = {
    "active": False, "started_at": None,
    "tasks": {}, "decisions": [],
}
_AGENT_RESULTS: dict[str, dict] = {}

def _log(agent: str, action: str, cat: str = "agent"):
    entry = {"ts": _ts(), "ts_short": _now(), "agent": agent.upper(), "action": action[:200], "category": cat}
    _ACTIVITY.insert(0, entry)
    if len(_ACTIVITY) > 200:
        _ACTIVITY.pop()

# ── LLM cascade ───────────────────────────────────────────────────────────────
async def llm(system: str, user: str, max_tokens: int = 600) -> tuple[str, str]:
    loop = asyncio.get_event_loop()
    # 1. Groq
    if _groq:
        try:
            resp = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: _groq.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role":"system","content":system},{"role":"user","content":user}],
                    max_tokens=max_tokens, temperature=0.7,
                )), timeout=12)
            return resp.choices[0].message.content, "groq"
        except Exception: pass
    # 2. Anthropic
    if _ant:
        try:
            resp = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: _ant.messages.create(
                    model="claude-sonnet-4-5",
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role":"user","content":user}],
                )), timeout=25)
            return resp.content[0].text, "claude"
        except Exception: pass
    return "⚠ LLMs indisponíveis. Verifique as variáveis de ambiente no Vercel.", "error"

# ── System prompts ────────────────────────────────────────────────────────────
STORE_CONTEXT = (
    "Loja: Aura Decore (auradecore.com.br) — decoração japandi premium, fase de lançamento orgânico. "
    "28 produtos ativos. Funil: Entrada R$19-50 / Médio R$68-129 / Premium R$129+. "
    "Plataforma Shopify. APENAS tráfego orgânico — sem Meta Ads ativo ainda."
)

AGENTS = {
    "ive":   "Você é IVE, CEO da Aura Decore. Direta, estratégica, carismática. " + STORE_CONTEXT,
    "guard": "Você é GUARD, CFO da Aura Decore. Monitora MEI R$81k/ano, margens e custos. " + STORE_CONTEXT,
    "nexus": "Você é NEXUS, minerador de produtos japandi. Analisa tendências, fornecedores e margem >35%. " + STORE_CONTEXT,
    "theo":  "Você é THEO, técnico Shopify. Cuida de catálogo, pixel, velocidade e checkout. " + STORE_CONTEXT,
    "kai":   "Você é KAI, curador de produtos. Analisa portfólio, margem, upsell. Foco nos tiers low/mid/premium. " + STORE_CONTEXT,
    "vera":  "Você é VERA, copywriter. Copy elegante para persona mulher 28-45 anos. Ângulo: ritual, presente, calma. " + STORE_CONTEXT,
    "luna":  "Você é LUNA, diretora de arte. Paleta: terracota #B8793A, off-white #F5F0EB. Brand japandi premium. " + STORE_CONTEXT,
    "nox":   "Você é NOX, criador de conteúdo. Roteiros de Reels 30s, carrosseis, calendário editorial. " + STORE_CONTEXT,
    "rex":   "Você é REX, estrategista de crescimento ORGÂNICO. Instagram, Pinterest, SEO, collabs. SEM Meta Ads. " + STORE_CONTEXT,
    "echo":  "Você é ECHO, auditor. Score 0-10 por agente. Métricas orgânicas: seguidores, engajamento, conversão. " + STORE_CONTEXT,
    "lena":  "Você é LENA, atendimento CX. Framework HERO. Cupons AURA10/AURAVIP15. Tom acolhedor. " + STORE_CONTEXT,
    "sol":   "Você é SOL, especialista CRO. Funil low→premium. Recovery D+1/D+3/D+7. Frete grátis R$199. " + STORE_CONTEXT,
    "zara":  "Você é ZARA, community Instagram. DMs, UGC, micro-influencers. Hashtag #auradecore. " + STORE_CONTEXT,
    "mira":  "Você é MIRA, SEO. Keywords japandi, wabi-sabi, meta tags Shopify, Pinterest SEO. " + STORE_CONTEXT,
    "pipe":  "Você é PIPE, automação. n8n workflows, webhooks Shopify, Z-API WhatsApp. " + STORE_CONTEXT,
    "arte":  "Você é ARTE, criativo visual IA. Prompts Pollinations.ai estilo japandi wabi-sabi. " + STORE_CONTEXT,
    "feed":  "Você é FEED, publicador de redes sociais. Instagram @auras.decore + Facebook Aura Decore. " + STORE_CONTEXT,
}

# ── Marathon tasks (espelho simplificado do marathon_tasks.py) ────────────────
MARATHON_TASKS = [
    {"id":"mar_sex_guard","agent":"guard","day":"sexta","area":"operacoes","order":1,"title":"GUARD · Revisão financeira — margens e preços","needs_approval":True,"max_tokens":600,"system":AGENTS["guard"],"user":"Execute revisão financeira: calcule margens ideais por categoria, preços para 55% de margem, limite MEI. Entregue tabela de preços recomendados."},
    {"id":"mar_sex_nexus","agent":"nexus","day":"sexta","area":"produto","order":2,"title":"NEXUS · Mineração estratégica","needs_approval":False,"max_tokens":600,"system":AGENTS["nexus"],"user":"Top 10 produtos japandi com maior potencial. Critérios: margem >55%, apelo visual, prazo entrega <20 dias. Liste fornecedor, preço, margem."},
    {"id":"mar_sex_kai","agent":"kai","day":"sexta","area":"produto","order":3,"title":"KAI · 5 produtos estrela","needs_approval":True,"max_tokens":500,"system":AGENTS["kai"],"user":"Selecione os 5 produtos estrela do catálogo atual para lançamento. Justifique cada escolha. Organize em 2 coleções."},
    {"id":"mar_sex_luna","agent":"luna","day":"sexta","area":"site","order":4,"title":"LUNA · Brief criativo","needs_approval":False,"max_tokens":600,"system":AGENTS["luna"],"user":"Crie o brief criativo completo: tema visual, paleta, diretrizes fotográficas, grid Instagram, prompts ImageGen."},
    {"id":"mar_sex_mira","agent":"mira","day":"sexta","area":"site","order":5,"title":"MIRA · SEO deep-dive","needs_approval":True,"max_tokens":600,"system":AGENTS["mira"],"user":"15 keywords prioritárias, meta title+description para home e 5 produtos, estrutura URL Shopify, post de blog recomendado."},
    {"id":"mar_sex_theo","agent":"theo","day":"sexta","area":"site","order":6,"title":"THEO · Auditoria Shopify","needs_approval":False,"max_tokens":500,"system":AGENTS["theo"],"user":"Checklist de lançamento: pixel, checkout, velocidade, produtos sem foto, links quebrados, SSL. A loja está pronta?"},
    {"id":"mar_sex_pipe","agent":"pipe","day":"sexta","area":"operacoes","order":7,"title":"PIPE · Mapa de automações","needs_approval":True,"max_tokens":500,"system":AGENTS["pipe"],"user":"Top 5 automações críticas para lançar: triggers, ações, ferramentas, tempo de config. Qual implementar primeiro?"},
    {"id":"mar_sab_vera","agent":"vera","day":"sabado","area":"site","order":1,"title":"VERA · Copy completa","needs_approval":True,"max_tokens":1000,"system":AGENTS["vera"],"user":"Copy completa: hero home (headline+subtítulo+CTA), 5 produtos estrela (título+descrição+bullets), bio Instagram, caption de lançamento."},
    {"id":"mar_sab_arte","agent":"arte","day":"sabado","area":"site","order":2,"title":"ARTE · Pack de imagens","needs_approval":False,"max_tokens":600,"system":AGENTS["arte"],"user":"10 prompts completos para: hero banner, 5 produtos, 2 posts Instagram, 2 stories. Inclua URLs Pollinations.ai prontas."},
    {"id":"mar_sab_nox","agent":"nox","day":"sabado","area":"social","order":3,"title":"NOX · Roteiros + calendário","needs_approval":True,"max_tokens":700,"system":AGENTS["nox"],"user":"3 roteiros de Reels completos (before/after, como usar, educativo). Calendário 7 dias: feed, stories, carrosseis."},
    {"id":"mar_sab_rex","agent":"rex","day":"sabado","area":"marketing","order":4,"title":"REX · Crescimento orgânico","needs_approval":False,"max_tokens":600,"system":AGENTS["rex"],"user":"Estratégia orgânica da semana: melhores horários, hashtags, 3 micro-influencers para abordar, ideia de collab gratuita, meta de seguidores."},
    {"id":"mar_sab_sol","agent":"sol","day":"sabado","area":"site","order":5,"title":"SOL · CRO completo","needs_approval":True,"max_tokens":600,"system":AGENTS["sol"],"user":"Checklist CRO página de produto, sequência recovery D+1/D+3/D+7, bundle sugerido, threshold frete grátis, 3 melhorias UX."},
    {"id":"mar_sab_zara","agent":"zara","day":"sabado","area":"social","order":6,"title":"ZARA · Community","needs_approval":False,"max_tokens":500,"system":AGENTS["zara"],"user":"DM de boas-vindas, templates resposta comentários, 10 micro-influencers, hashtag strategy, ação UGC para clientes."},
    {"id":"mar_sab_feed","agent":"feed","day":"sabado","area":"social","order":7,"title":"FEED · Programação posts","needs_approval":True,"max_tokens":400,"system":AGENTS["feed"],"user":"Programação sábado+domingo: horários, formatos, captions, hashtags, plataformas. Fila de publicação completa."},
    {"id":"mar_dom_lena","agent":"lena","day":"domingo","area":"operacoes","order":1,"title":"LENA · Kit SAC","needs_approval":False,"max_tokens":500,"system":AGENTS["lena"],"user":"5 templates SAC, sequência pós-venda 3 emails, FAQ 8 perguntas, política de devolução para o site."},
    {"id":"mar_dom_echo","agent":"echo","day":"domingo","area":"operacoes","order":2,"title":"ECHO · Auditoria geral","needs_approval":False,"max_tokens":600,"system":AGENTS["echo"],"user":"Audite todas as entregas da maratona. Score por área (site/social/produto/marketing/ops). Lista de 5 gaps críticos. Nota geral de prontidão para lançamento."},
    {"id":"mar_dom_ive","agent":"ive","day":"domingo","area":"operacoes","order":3,"title":"IVE · Relatório executivo","needs_approval":True,"max_tokens":700,"system":AGENTS["ive"],"user":"Relatório final da maratona para Eduardo: o que foi produzido, o que está pronto, o que falta, plano da próxima semana, 5 decisões urgentes com recomendação, data sugerida de lançamento."},
]

# Inicializa estado da maratona
def _marathon_init():
    for t in MARATHON_TASKS:
        if t["id"] not in _MARATHON["tasks"]:
            _MARATHON["tasks"][t["id"]] = {"status":"pendente","result":"","approved":None,"started_at":None,"done_at":None}

_marathon_init()

# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

@app.get("/api/status")
async def status():
    pending = sum(1 for t in _MARATHON["tasks"].values() if t["status"] == "aguardando_aprovacao")
    return {
        "bridge": "online", "phase": "operacao",
        "agents": {a: {"status":"online","last_task":"","tasks_today":0} for a in AGENTS},
        "marathon_decisions_pending": pending,
        "activity_count": len(_ACTIVITY),
    }


class ChatBody(BaseModel):
    message: str
    agent_id: str = "ive"

@app.post("/api/chat")
async def chat(body: ChatBody):
    agent_id = body.agent_id.lower()
    system = AGENTS.get(agent_id, AGENTS["ive"])
    result, provider = await llm(system, body.message, max_tokens=500)
    _log(agent_id, body.message[:80], "agent")
    # Detecta dispatches ||DISPATCH:agente:tarefa||
    dispatched = []
    import re
    for m in re.finditer(r'\|\|DISPATCH:(\w+):([^|]+)\|\|', result):
        ag, task = m.group(1).lower(), m.group(2)
        dispatched.append({"agent": ag, "task": task})
        asyncio.create_task(_run_agent_bg(ag, task))
    clean = re.sub(r'\|\|DISPATCH:[^|]+\|\|', '', result).strip()
    return {"response": clean, "provider": provider, "dispatched": dispatched}


class AgentExecBody(BaseModel):
    agent_id: str
    message: str

@app.post("/api/agent/exec")
async def agent_exec(body: AgentExecBody):
    agent_id = body.agent_id.lower()
    system = AGENTS.get(agent_id, AGENTS["ive"])
    result, provider = await llm(system, body.message, max_tokens=600)
    _log(agent_id, f"Exec: {body.message[:80]}", "agent")
    _AGENT_RESULTS[agent_id] = {"result": result, "ts": _ts(), "provider": provider}
    return {"agent_id": agent_id, "response": result, "provider": provider}


async def _run_agent_bg(agent_id: str, task: str):
    system = AGENTS.get(agent_id, AGENTS["ive"])
    result, provider = await llm(system, task, max_tokens=500)
    _log(agent_id, f"✓ {task[:80]}", "agent")
    _AGENT_RESULTS[agent_id] = {"result": result, "ts": _ts(), "provider": provider}


# ── ACTIVITY LOG ──────────────────────────────────────────────────────────────
@app.get("/api/activity/log")
async def activity_log(limit: int = 50):
    return {"entries": _ACTIVITY[:limit], "total": len(_ACTIVITY)}


# ── MARATHON ──────────────────────────────────────────────────────────────────
def _marathon_status_json():
    tasks_out = []
    for t in MARATHON_TASKS:
        state = _MARATHON["tasks"].get(t["id"], {})
        tasks_out.append({
            "id": t["id"], "agent": t["agent"].upper(), "day": t["day"],
            "area": t["area"], "order": t["order"], "title": t["title"],
            "needs_approval": t["needs_approval"],
            "status": state.get("status", "pendente"),
            "result": state.get("result", "")[:300],
            "approved": state.get("approved"),
            "started_at": state.get("started_at"),
            "done_at": state.get("done_at"),
        })
    total = len(MARATHON_TASKS)
    done  = sum(1 for t in tasks_out if t["status"] in ("concluido","aprovado"))
    run   = sum(1 for t in tasks_out if t["status"] == "rodando")
    wait  = sum(1 for t in tasks_out if t["status"] == "aguardando_aprovacao")
    return {
        "active": _MARATHON["active"],
        "started_at": _MARATHON["started_at"],
        "progress": {"total": total, "done": done, "running": run, "waiting_approval": wait},
        "tasks": tasks_out,
        "decisions": _MARATHON["decisions"],
    }

@app.get("/api/marathon/status")
async def marathon_status():
    return _marathon_status_json()

@app.get("/api/marathon/decisions")
async def marathon_decisions():
    return {"decisions": _MARATHON["decisions"]}

class MarathonStartBody(BaseModel):
    day: str = ""

@app.post("/api/marathon/start")
async def marathon_start(body: MarathonStartBody):
    _MARATHON["active"] = True
    _MARATHON["started_at"] = _ts()
    tasks = [t for t in MARATHON_TASKS if not body.day or t["day"] == body.day]
    for t in sorted(tasks, key=lambda x: x["order"]):
        _MARATHON["tasks"][t["id"]]["status"] = "rodando"
        _MARATHON["tasks"][t["id"]]["started_at"] = _now()
        asyncio.create_task(_run_marathon_task(t["id"]))
    _log("SYSTEM", f"Maratona iniciada — {len(tasks)} tarefas", "marathon")
    return {"ok": True, "day": body.day or "all", "tasks_dispatched": len(tasks)}

async def _run_marathon_task(task_id: str):
    t = next((x for x in MARATHON_TASKS if x["id"] == task_id), None)
    if not t: return
    result, provider = await llm(t["system"], t["user"], t.get("max_tokens", 600))
    needs_approval = t.get("needs_approval", False)
    new_status = "aguardando_aprovacao" if needs_approval else "concluido"
    _MARATHON["tasks"][task_id].update({"status": new_status, "result": result[:1000], "done_at": _now()})
    if needs_approval:
        _MARATHON["decisions"].append({
            "task_id": task_id, "title": t["title"],
            "agent": t["agent"].upper(), "result": result[:800],
            "created_at": _now(),
        })
    _log(t["agent"], f"✓ {t['title'][:80]}", "marathon")

@app.post("/api/marathon/tasks/{task_id}/run")
async def marathon_run_task(task_id: str):
    t = next((x for x in MARATHON_TASKS if x["id"] == task_id), None)
    if not t: return {"error": "not found"}
    _MARATHON["tasks"][task_id].update({"status": "rodando", "started_at": _now()})
    asyncio.create_task(_run_marathon_task(task_id))
    return {"ok": True, "task_id": task_id}

class ApproveBody(BaseModel):
    approved: bool
    note: str = ""

@app.post("/api/marathon/tasks/{task_id}/approve")
async def marathon_approve(task_id: str, body: ApproveBody):
    _MARATHON["tasks"][task_id]["approved"] = body.approved
    _MARATHON["tasks"][task_id]["status"] = "aprovado" if body.approved else "rejeitado"
    _MARATHON["decisions"] = [d for d in _MARATHON["decisions"] if d["task_id"] != task_id]
    action = "aprovado" if body.approved else "rejeitado"
    _log("EDUARDO", f"Decisão: {task_id} → {action}", "marathon")
    return {"ok": True, "task_id": task_id, "action": action}

@app.post("/api/marathon/reset")
async def marathon_reset():
    _MARATHON["active"] = False; _MARATHON["started_at"] = None
    _MARATHON["tasks"] = {}; _MARATHON["decisions"] = []
    _marathon_init()
    return {"ok": True}


# ── SHOPIFY quick endpoints ────────────────────────────────────────────────────
@app.get("/api/shopify/improvements")
async def shopify_improvements():
    return {"done": 6, "total": 6, "results": {}, "pending": []}

@app.post("/api/shopify/improvements/{task_id}/run")
async def shopify_run_improvement(task_id: str):
    _log("DEV", f"Melhoria disparada: {task_id}", "site")
    return {"ok": True, "task_id": task_id}


# ── TASKS (Kanban stub) ────────────────────────────────────────────────────────
@app.get("/api/tasks")
async def get_tasks():
    return {"tasks": [], "total": 0}


# ── Serve mobile HTML ─────────────────────────────────────────────────────────
@app.get("/")
@app.get("/mobile")
async def serve_mobile():
    import pathlib
    # No Vercel, o HTML fica na pasta public/
    for path in [
        pathlib.Path(__file__).parent.parent / "public" / "mobile.html",
        pathlib.Path(__file__).parent.parent / "aura-mobile.html",
    ]:
        if path.exists():
            return HTMLResponse(path.read_text(encoding="utf-8"))
    return HTMLResponse("<h2>mobile.html não encontrado</h2>", status_code=404)

@app.get("/manifest.json")
async def manifest():
    import pathlib
    f = pathlib.Path(__file__).parent.parent / "manifest.json"
    if f.exists():
        return JSONResponse(json.loads(f.read_text(encoding="utf-8")))
    return JSONResponse({"error": "not found"}, status_code=404)

@app.get("/sw.js")
async def sw():
    import pathlib
    from fastapi.responses import Response
    f = pathlib.Path(__file__).parent.parent / "sw.js"
    if f.exists():
        return Response(f.read_text(encoding="utf-8"), media_type="application/javascript",
                       headers={"Service-Worker-Allowed": "/"})
    return Response("// sw not found", media_type="application/javascript")
