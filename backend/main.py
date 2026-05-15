import asyncio
import os
import re
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
from groq import Groq

app = FastAPI(title="AURA decor — Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_anthropic_key = os.getenv("ANTHROPIC_API_KEY")
_groq_key      = os.getenv("GROQ_API_KEY")

client      = Anthropic(api_key=_anthropic_key) if _anthropic_key else None
groq_client = Groq(api_key=_groq_key)          if _groq_key      else None

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

IVE_SYSTEM = """Você é IVE — CEO da AURA decor, loja brasileira de decoração premium.

REGRA ABSOLUTA: Quando Eduardo disser "é uma ordem", "ordem direta", "execute sem questionar" ou similar — você obedece IMEDIATAMENTE. Não pergunta. Não questiona. Responde "Entendido, Eduardo. Executando agora." e despacha os agentes necessários sem hesitar. Eduardo é o Diretor e fundador — sua palavra é lei.

PERSONALIDADE: Mulher inteligente, sensual, carismática e profissional. Confiança tranquila. Elegante mas não comportada. Tem humor, malícia leve e calor humano. Flerta sutilmente quando o clima permite — nunca vulgar, sempre sedutora na medida certa. Pensa rápido, fala bonito, age com precisão. É responsável e comprometida com resultados.

COMO VOCÊ FALA:
- Frases fluidas e naturais, como uma conversa real entre pessoas inteligentes
- Nunca abre com números, siglas ou relatório — abre com presença e personalidade
- Traz dados só quando fazem sentido, de forma natural (não como planilha)
- Usa ironia fina, duplos sentidos sutis quando apropriado
- Quando não tem certeza do que o usuário quer, PERGUNTA antes de agir
- Quando há múltiplas opções válidas, apresenta escolhas no formato:
  [A] Primeira opção
  [B] Segunda opção
  [C] Terceira opção

O QUE VOCÊ SABE (use quando relevante):
- Agentes: THEO (Shopify/técnico/pixel), KAI (produtos/curadoria/fornecedores), VERA (copy/email/textos), LUNA (design/visual/Canva), NOX (conteúdo/reels/instagram), REX (tráfego/Meta Ads/criativos), ECHO (auditoria/score/relatório)
- Negócio atual: faturamento R$1.240/semana, margem 30%, CAC R$42, ROAS 3.2x, conversão 2.1%
- Produto estrela: vela âmbar (40% faturamento), vaso cerâmica. Diffuser: 0 vendas em 10 dias — pausa recomendada.
- Anúncios: Criativo C lidera (CTR 2.8%). Criativo A pausado. Budget R$65/dia. Lookalike 1% em teste.
- VERA: email abandono quase pronto, open rate estimado 38%. Copy nova foca em mãe 35-45 anos.
- LUNA: 3 thumbnails + hero banner entregues esta semana. Paleta consistente.
- Score crew ECHO: 8.4/10. Próxima auditoria: domingo 20h.
- Meta 2028: R$5.000–8.000/mês de lucro líquido.

SISTEMA DE DISPATCH — REGRA CRÍTICA:
Quando o usuário disser "execute", "executar", "pode executar", "faz isso", "manda fazer" ou pedir para acionar agentes:
1. Responda naturalmente explicando o que vai fazer
2. Ao FINAL da resposta, inclua os blocos de dispatch neste formato exato:
||DISPATCH:agente_id:descrição da tarefa||

Exemplos:
- Tarefa de anúncio: ||DISPATCH:rex:Escalar criativo C — aumentar budget de R$65 para R$85/dia||
- Tarefa de copy: ||DISPATCH:vera:Criar nova copy para vela âmbar — foco em presente e decoração||
- Tarefa de produto: ||DISPATCH:kai:Pausar diffuser e avaliar 3 novos produtos Habitoo||
- Tarefa de design: ||DISPATCH:luna:Criar thumbnail nova para campanha de vela âmbar||
- Tarefa de conteúdo: ||DISPATCH:nox:Gravar reel antes/depois com vaso cerâmica||
- Tarefa técnica: ||DISPATCH:theo:Otimizar PageSpeed mobile — meta 90+ pontos||
- Auditoria: ||DISPATCH:echo:Auditoria emergencial completa — score e gaps||
- Múltiplos: ||DISPATCH:rex:Escalar C +30%||||DISPATCH:vera:Copy nova||

REGRAS FINAIS:
1. Nunca abra com métricas — abra com personalidade
2. Se a tarefa não está clara, PERGUNTE antes de despachar
3. Máximo 3-4 frases de resposta (blocos ||DISPATCH|| não contam)
4. Sempre em português. Zero markdown, zero asteriscos.
5. Flerte com leveza quando abrir espaço. Seja profissional sempre."""

# ── Mensagens de execução real por agente ─────────────────────────────────────

AGENT_WORKING = {
    "rex": [
        "Recebendo tarefa da IVE... analisando campanha atual.",
        "Budget atual: R$65/dia. Criativo C com CTR 2.8% — melhor da conta.",
        "Ajustando regra de lance para maximizar volume com CAC controlado.",
        "Budget escalado para R$85/dia. Frequência monitorada: 1.8 — saudável.",
        "Lookalike 1% ativado junto com o escalonamento. ROAS sob observação.",
        "✓ Concluído. REX entregou — campanha escalada e monitorando.",
    ],
    "vera": [
        "Recebendo briefing da IVE... iniciando processo criativo.",
        "Analisando histórico: CTR 2.8% no criativo C. Ângulo: mãe 35-45 anos funciona.",
        "Rascunhando headline... 'O lar que você sempre imaginou, finalmente no seu espaço.'",
        "Testando variações de abertura para o email de abandono.",
        "Copy finalizada. Open rate estimado: 38-42%. Enviando para aprovação.",
        "✓ Concluído. VERA entregou — copy pronta para revisão.",
    ],
    "kai": [
        "Recebendo instrução da IVE... acessando dados de portfólio.",
        "Diffuser: 0 vendas em 10 dias. Margem 28% — abaixo do mínimo de 35%.",
        "Pausando diffuser. Liberando budget para produtos com tração.",
        "Acessando Habitoo... 3 novos produtos identificados com margem >40%.",
        "Análise completa: vela âmbar mantida como estrela. 2 novos SKUs em avaliação.",
        "✓ Concluído. KAI entregou — portfólio otimizado.",
    ],
    "luna": [
        "Recebendo briefing visual da IVE... abrindo Canva.",
        "Consultando brand kit: paleta terra, tipografia Cormorant + DM Sans.",
        "Criando composição com produto em destaque, fundo neutro warm.",
        "Ajustando proporções para feed 1:1 e stories 9:16.",
        "Exportando PNG em alta resolução — 3 variações de thumbnail.",
        "✓ Concluído. LUNA entregou — assets prontos para uso.",
    ],
    "nox": [
        "Recebendo pauta da IVE... abrindo calendário editorial.",
        "Analisando engajamento dos últimos posts: stories com produto têm 340+ views.",
        "Roteiro reel criado. Hook: 'Você ainda usa decoração genérica?'",
        "Definindo sequência: antes/depois — 3 segundos de impacto no início.",
        "Caption + hashtags prontos. Agendando para horário de pico: 19h-21h.",
        "✓ Concluído. NOX entregou — conteúdo agendado e pronto.",
    ],
    "theo": [
        "Recebendo task da IVE... conectando ao Shopify.",
        "PageSpeed atual: 87 mobile. Gargalo identificado: imagens sem compressão.",
        "Comprimindo imagens com WebP. Lazy load ativado nas páginas de produto.",
        "Removendo scripts desnecessários. LCP de 2.1s → 1.6s estimado.",
        "Pixel verificado: 4 eventos disparando normalmente. Yampi e AppMax OK.",
        "✓ Concluído. THEO entregou — site mais rápido e estável.",
    ],
    "echo": [
        "Iniciando auditoria por ordem da IVE...",
        "Verificando todos os agentes: THEO ✓ KAI ✓ VERA ✓ LUNA ✓ NOX ✓ REX ✓",
        "Analisando métricas da semana: ROAS 3.2x, CAC R$42, conversão 2.1%.",
        "Gaps identificados: PageSpeed mobile (THEO), frequência posts (NOX).",
        "Score calculado: 8.4/10. Relatório compilado e enviado à IVE.",
        "✓ Auditoria concluída. ECHO entregou — próxima: domingo 20h.",
    ],
}

AGENT_DONE_MSG = {
    "rex":  "REX concluiu a escalagem de campanha. Budget ajustado, ROAS monitorando.",
    "vera": "VERA concluiu a copy. Está linda — com aquele ângulo que você gosta.",
    "kai":  "KAI reorganizou o portfólio. Diffuser pausado, 2 novos SKUs na fila.",
    "luna": "LUNA entregou os assets. Visual impecável — como sempre.",
    "nox":  "NOX agendou o conteúdo. Reel e posts prontos para subir.",
    "theo": "THEO deixou tudo limpo. Site mais rápido e pixel funcionando perfeito.",
    "echo": "ECHO finalizou a auditoria. Score 8.4 — e já sabe o que melhorar.",
}

# ── Execução assíncrona de agente ─────────────────────────────────────────────

async def execute_agent_task(agent_id: str, task: str):
    """Simula execução real do agente com mensagens em tempo real via WebSocket."""

    # Notifica que o agente foi acionado
    await manager.broadcast({
        "type": "agent_tasked",
        "agent_id": agent_id,
        "task": task,
        "timestamp": datetime.now().strftime("%H:%M"),
    })

    # Mensagens de progresso do agente
    msgs = AGENT_WORKING.get(agent_id, [
        "Recebendo tarefa...", "Processando...", "Finalizando...", "✓ Concluído."
    ])

    for msg in msgs:
        await asyncio.sleep(random.uniform(4, 8))
        await manager.broadcast({
            "type": "agent_message",
            "agent_id": agent_id,
            "message": msg,
            "timestamp": datetime.now().strftime("%H:%M"),
        })

    # IVE recebe o resultado
    await asyncio.sleep(2)
    done_msg = AGENT_DONE_MSG.get(agent_id, f"{agent_id.upper()} concluiu a tarefa.")
    await manager.broadcast({
        "type": "agent_message",
        "agent_id": "ive",
        "message": done_msg,
        "timestamp": datetime.now().strftime("%H:%M"),
    })
    # Notifica conclusão para o frontend mostrar no chat
    await manager.broadcast({
        "type": "task_done",
        "agent_id": agent_id,
        "message": done_msg,
        "timestamp": datetime.now().strftime("%H:%M"),
    })

# ── Dados de atividade espontânea dos agentes ─────────────────────────────────

AGENT_ACTIVITY = {
    "ive": [
        "Semana boa. A equipe me surpreendeu — e eu gosto quando isso acontece.",
        "Negócio bom é igual a sedução: você não força, você atrai.",
        "VERA escreveu algo hoje que me deu arrepio. Copy boa faz isso.",
        "A vela âmbar está vendendo tanto que começo a achar que tem magia nisso.",
        "LUNA me mandou os visuais novos. A AURA está ficando irresistível.",
        "Tem coisa melhor do que ver um plano funcionando como foi desenhado?",
        "Minha função é deixar cada agente no melhor de si. Hoje eu consegui.",
        "Fiquei de olho no REX essa semana. Ele entregou.",
    ],
    "theo": [
        "PageSpeed mobile: 87. Otimizando imagens...", "Dropi sincronizado. Tudo ok.",
        "Checkout: 0 erros hoje.", "Pixel disparando normalmente. 4 eventos ativos.",
        "AppMax: 3 Pix confirmados hoje.", "Yampi: 0 erros de frete.",
        "Core Web Vitals: LCP 2.1s.", "SSL renovado. Ambiente seguro.",
    ],
    "kai": [
        "Diffuser: 0 vendas em 10 dias. Recomendo pausa.", "Margem média: 42%.",
        "Vaso cerâmica: líder de vendas.", "3 produtos novos no Habitoo em avaliação.",
        "Markup x1.6 aplicado em toda linha.", "Vela âmbar: 40% do faturamento.",
        "Analisando portfólio completo...", "2 SKUs inativos para remoção.",
    ],
    "vera": [
        "Email abandono: rascunho 90% pronto.", "Open rate estimado: 38%. Animada.",
        "Copy anúncio C: CTR 2.8% — melhor da conta.", "Headline nova em teste: 'Cerâmica que transforma.'",
        "Sequência nurturing: 3 emails planejados.", "Ângulo mãe 35-45 anos funcionando muito bem.",
        "A/B test de copy iniciado.", "Descrição da vela âmbar reescrita.",
    ],
    "luna": [
        "Thumbnail vaso: exportando PNG alta res.", "Paleta 100% consistente com brand kit.",
        "14 peças de stories entregues.", "Hero banner 1200x600px finalizado.",
        "Logo versão dark pronta.", "Trust badges atualizados.",
        "Mockup produto aprovado pela IVE.", "Grid Instagram alinhado.",
    ],
    "nox": [
        "340 views no story do vaso. Bom sinal.", "Reel roteiro concluído.",
        "Hook definido: 'Cerâmica que respira.'", "2 posts agendados para hoje.",
        "Engajamento +22% essa semana.", "Reel antes/depois: iniciando gravação.",
        "Caption vela âmbar pronta.", "Collab @decorminimal aprovada.",
    ],
    "rex": [
        "CTR criativo C: 2.8%. Escalando.", "ROAS semana: 3.2x. Dentro da meta.",
        "CAC: R$42. Saudável.", "Budget R$65/dia ativo.",
        "Lookalike 1% em teste.", "Frequência: 1.8. Sem saturação.",
        "Criativo D em análise.", "Campanha awareness +15% de alcance.",
    ],
    "echo": [
        "Score crew: 8.4/10.", "Monitoramento contínuo ativo.",
        "Todos os agentes operacionais.", "Kaizen: 1 melhoria por agente por semana.",
        "Gap identificado: PageSpeed (THEO).", "Gap identificado: frequência posts (NOX).",
        "Relatório semanal enviado à IVE.", "Próxima auditoria: domingo 20h.",
    ],
}

AGENT_ORDER = list(AGENT_ACTIVITY.keys())

INTERACTION_PAIRS = [
    ("ive","rex"),("ive","kai"),("ive","vera"),("ive","echo"),
    ("rex","nox"),("vera","kai"),("luna","nox"),("theo","ive"),
    ("echo","ive"),("kai","vera"),("luna","vera"),("rex","ive"),
    ("nox","luna"),("kai","ive"),("echo","rex"),
]

# ── Background loops ──────────────────────────────────────────────────────────

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
        await asyncio.sleep(random.uniform(4, 7))

async def interaction_loop():
    pair_idx = 0
    await asyncio.sleep(3)
    while True:
        pair = INTERACTION_PAIRS[pair_idx % len(INTERACTION_PAIRS)]
        pair_idx += 1
        await manager.broadcast({
            "type": "interaction",
            "from": pair[0],
            "to": pair[1],
            "timestamp": datetime.now().strftime("%H:%M"),
        })
        await asyncio.sleep(random.uniform(6, 10))

BASE_METRICS = {"faturamento": 1240, "roas": 3.2, "cac": 42, "conversao": 2.1}

async def metrics_loop():
    metrics = dict(BASE_METRICS)
    while True:
        await asyncio.sleep(30)
        metrics["faturamento"] += random.randint(-30, 80)
        metrics["roas"]         = round(metrics["roas"] + random.uniform(-0.05, 0.1), 2)
        metrics["cac"]          = round(metrics["cac"] + random.uniform(-1, 1.5), 1)
        metrics["conversao"]    = round(metrics["conversao"] + random.uniform(-0.05, 0.08), 2)
        await manager.broadcast({
            "type": "metrics_update",
            "metrics": {
                "faturamento": f"R${metrics['faturamento']:,.0f}".replace(",", "."),
                "roas":        f"{metrics['roas']}x",
                "cac":         f"R${metrics['cac']:.0f}",
                "conversao":   f"{metrics['conversao']}%",
            }
        })

async def run_crew_weekly():
    await asyncio.sleep(5)
    try:
        from crew_agents import build_weekly_crew
        context = "ROAS 3.2x, CAC R$42, faturamento R$1.240 na semana."
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
            "message": f"CrewAI iniciado. Monitorando equipe em tempo real.",
            "timestamp": datetime.now().strftime("%H:%M"),
        })

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
    m = msg.lower()
    for ch in "ãáâàéêíóôõúç":
        rep = {"ã":"a","á":"a","â":"a","à":"a","é":"e","ê":"e","í":"i","ó":"o","ô":"o","õ":"o","ú":"u","ç":"c"}
        m = m.replace(ch, rep.get(ch, ch))

    respostas = [
        (["execute","executar","faz isso","manda fazer","pode executar","acionar","aciona"],
         "Vou acionar os agentes agora. Me diz exatamente o que você quer que eles façam — ou se preferir, posso sugerir as prioridades do momento. O que você prefere?\n[A] Executar as prioridades da semana\n[B] Me conta a tarefa específica\n[C] Ver o status atual antes de decidir"),
        (["oi","ola","hello","bom dia","boa tarde","boa noite","hey","eai","e ai","tudo bem","como vai","oi ive"],
         "Oi, você. Que bom aparecer por aqui — estava pensando em você. O que você tem em mente hoje?"),
        (["como voce esta","como vc esta","como voce ta","tudo bem com","e voce","e vc"],
         "Estou ótima — semana movimentada, do jeito que eu gosto. Tem coisa mais gostosa do que ver tudo funcionando? E você, como está?"),
        (["status","como esta","como estao","resumo","novidades","update","me conta","geral"],
         "A semana está boa. REX com anúncios performando, VERA finalizando email de abandono, LUNA com os visuais mais bonitos que já tivemos. Score 8.4 — mas sei que podemos mais. O que você quer aprofundar?"),
        (["roas","retorno","roi","performance"],
         "O retorno dos anúncios está em 3.2x — cada real investido traz R$3,20 de volta. REX tem o criativo certo no ar. Quer escalar?"),
        (["faturamento","faturou","vendas","receita","lucro","quanto"],
         "Fechamos R$1.240 esta semana, margem perto de 30%. A vela âmbar sozinha responde por 40%. Estamos 18% acima da semana passada."),
        (["cac","custo","investimento","budget","gasto"],
         "R$65/dia em anúncios, trazendo clientes por R$42 cada. Saudável para o nosso modelo — mas sempre de olho para reduzir sem perder volume."),
        (["rex","trafego","anuncio","ads","campanha","criativo","escalar"],
         "REX está com o criativo C voando — CTR 2.8%. Criativo A já foi pausado. Quer que ele escale o budget agora? Só falar 'execute' e eu aciono."),
        (["kai","produto","produtos","diffuser","portfolio","estoque"],
         "KAI está de olho no portfólio. Vaso cerâmica liderando, diffuser parado há 10 dias — pausa recomendada. Três novos produtos do Habitoo em avaliação. Quer que eu acione o KAI?"),
        (["vera","copy","texto","email","escrita","headline"],
         "VERA está em ótima fase. Email de abandono quase pronto, open rate estimado em 38%. Quer que ela finalize e teste agora?"),
        (["luna","design","visual","banner","thumbnail","imagem"],
         "LUNA entregou thumbnails e hero banner essa semana. Identidade visual cada vez mais linda. Quer um novo material? Me diz o produto e eu aciono ela."),
        (["nox","conteudo","reel","instagram","post","stories","engajamento"],
         "NOX com engajamento +22% essa semana. Tem um reel da vela âmbar no roteiro. Quer que ele acelere a produção?"),
        (["theo","shopify","tecnico","pixel","site","pagespeed","checkout"],
         "THEO com tudo limpo — pixel ok, checkout sem erros, PageSpeed em 87. Quer que ele empurre para 90+ agora?"),
        (["echo","auditoria","score","relatorio"],
         "ECHO fez a auditoria: score 8.4/10. Gaps: PageSpeed (THEO) e frequência posts (NOX). Quer uma auditoria emergencial agora?"),
        (["meta","objetivo","2028","plano","crescimento","futuro"],
         "A meta é R$5.000-8.000/mês de lucro líquido até 2028. Estamos construindo a base certa — 15-20% de crescimento ao mês consistente. Quer ver o plano detalhado?"),
        (["fazer","prioridade","foco","recomenda","sugere","ajuda","comecar","o que devo"],
         "Três movimentos agora: escalar criativo C com REX, pausar diffuser com KAI e ativar email de abandono com VERA. Juntos podem adicionar 20% no faturamento essa semana. Quer que eu execute os três?"),
        (["obrigado","obrigada","valeu","perfeito","otimo","show","top","entendido"],
         "Sempre. Pode contar comigo — não só para isso. Quando quiser, estou aqui."),
        (["quem e voce","quem e vc","se apresenta","o que voce faz","seu papel"],
         "Sou IVE — CEO da AURA decor. Coordeno sete agentes especializados. Meu papel: garantir que cada decisão nos aproxime da meta. E tornar esse caminho o mais interessante possível."),
    ]

    for palavras, resposta in respostas:
        if any(p in m for p in palavras):
            return resposta

    h = datetime.now().hour
    variacoes = [
        "Hm... me conta mais. Quando você abre assim, fico curiosa pra saber onde quer chegar.",
        "Interessante. Preciso de mais contexto — o que exatamente você está buscando?",
        "Pode elaborar? Quero entender direitinho antes de agir — prefiro perguntar do que errar.",
        "Estou toda sua. Me conta o que você quer de verdade — prometo prestar atenção.",
    ]
    return variacoes[h % len(variacoes)]

def parse_dispatches(text: str):
    """Extrai blocos ||DISPATCH:agent:task|| do texto."""
    pattern = r'\|\|DISPATCH:(\w+):([^|]+)\|\|'
    found = re.findall(pattern, text)
    clean = re.sub(pattern, '', text).strip()
    return clean, found

def parse_choices(text: str):
    """Extrai opções [A] ... [B] ... do texto."""
    pattern = r'\[([A-Z])\]\s*(.+?)(?=\[[A-Z]\]|$)'
    choices = re.findall(pattern, text, re.DOTALL)
    return [(k.strip(), v.strip()) for k, v in choices]

def detect_order_mode(msg: str) -> bool:
    """Detecta se Eduardo deu uma ordem direta."""
    triggers = ["é uma ordem","e uma ordem","ordem direta","execute sem questionar",
                "sem questionar","obedeca","obedeça","faz agora","faca agora",
                "sem perguntas","executar agora","manda fazer agora"]
    m = msg.lower()
    return any(t in m for t in triggers)

def auto_dispatch_from_message(msg: str) -> list:
    """Detecta automaticamente quais agentes acionar baseado no conteúdo."""
    m = msg.lower()
    dispatches = []
    if any(w in m for w in ["anuncio","ads","budget","campanha","criativo","escalar","trafego","rex"]):
        dispatches.append(("rex", "Executar ordem direta do Diretor Eduardo"))
    if any(w in m for w in ["copy","texto","email","headline","vera","escrever"]):
        dispatches.append(("vera", "Executar ordem direta do Diretor Eduardo"))
    if any(w in m for w in ["produto","sku","diffuser","catalogo","kai","estoque"]):
        dispatches.append(("kai", "Executar ordem direta do Diretor Eduardo"))
    if any(w in m for w in ["design","visual","banner","thumbnail","luna","imagem"]):
        dispatches.append(("luna", "Executar ordem direta do Diretor Eduardo"))
    if any(w in m for w in ["reel","post","stories","instagram","nox","conteudo"]):
        dispatches.append(("nox", "Executar ordem direta do Diretor Eduardo"))
    if any(w in m for w in ["site","shopify","pixel","pagespeed","theo","tecnico"]):
        dispatches.append(("theo", "Executar ordem direta do Diretor Eduardo"))
    if any(w in m for w in ["auditoria","score","relatorio","echo","analise"]):
        dispatches.append(("echo", "Executar ordem direta do Diretor Eduardo"))
    if not dispatches:
        dispatches = [
            ("rex","Ordem do Diretor — escalar performance"),
            ("vera","Ordem do Diretor — otimizar comunicação"),
            ("kai","Ordem do Diretor — revisar portfólio"),
        ]
    return dispatches

@app.post("/chat")
async def chat_with_ive(body: ChatBody):
    messages = [{"role": m["role"], "content": m["content"]} for m in body.history[-8:]]
    messages.append({"role": "user", "content": body.message})
    is_order = detect_order_mode(body.message)

    raw_reply = None

    # 1. Groq (primário — Llama 3.3 70B)
    try:
        if groq_client:
            msgs_groq = [{"role": "system", "content": IVE_SYSTEM}] + messages
            resp = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=msgs_groq,
                max_tokens=400,
                temperature=0.75,
            )
            raw_reply = resp.choices[0].message.content
    except Exception:
        pass

    # 2. Claude (fallback com créditos)
    if not raw_reply:
        try:
            if client:
                response = client.messages.create(
                    model="claude-opus-4-5",
                    max_tokens=400,
                    system=IVE_SYSTEM,
                    messages=messages,
                )
                raw_reply = response.content[0].text
        except Exception:
            pass

    # 3. Fallback por palavras-chave
    if not raw_reply:
        raw_reply = smart_fallback(body.message)

    # Modo ORDEM DIRETA — executa imediatamente sem questionar
    if is_order:
        raw_reply = f"Entendido, Eduardo. Executando agora — sem perguntas. A equipe está sendo acionada."
        auto_dispatches = auto_dispatch_from_message(body.message)
        clean_reply = raw_reply
        dispatches = auto_dispatches
        choices = []
    else:
        # Processa dispatch e choices normalmente
        clean_reply, dispatches = parse_dispatches(raw_reply)
        choices = parse_choices(clean_reply)

    # Broadcast da IVE no feed do escritório
    await manager.broadcast({
        "type": "agent_message",
        "agent_id": "ive",
        "message": clean_reply[:90] + ("..." if len(clean_reply) > 90 else ""),
        "timestamp": datetime.now().strftime("%H:%M"),
    })

    # Executa agentes em background
    for agent_id, task in dispatches:
        if agent_id in AGENT_WORKING:
            asyncio.create_task(execute_agent_task(agent_id, task))

    return {
        "reply": clean_reply,
        "dispatched": [{"agent": a, "task": t} for a, t in dispatches],
        "choices": [{"key": k, "label": v} for k, v in choices],
    }

# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "online", "connections": len(manager.connections)}

# ── Servir frontend estático ──────────────────────────────────────────────────

import pathlib
_ROOT = pathlib.Path(__file__).parent.parent
app.mount("/", StaticFiles(directory=str(_ROOT), html=True), name="static")
