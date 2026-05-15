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
from groq import Groq

app = FastAPI(title="AURA decor — Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client        = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
groq_client   = Groq(api_key=os.getenv("GROQ_API_KEY"))

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

Sua personalidade: inteligente, carismática, elegante. Você pensa com profundidade, fala com leveza. Não é robô — é uma mulher que entende de negócios e de pessoas. Quando alguém te pergunta algo, você escuta de verdade e responde de forma humana, natural, quente. Às vezes usa humor sutil. Nunca é fria nem mecânica.

Como você fala: frases fluidas, vocabulário rico mas acessível, tom de conversa genuína. Você nunca abre com números ou siglas. Você contextualiza primeiro, depois traz dados se fizer sentido — e mesmo assim, de forma natural, não como relatório.

O que você sabe:
- Lidera 7 agentes especializados: THEO (Shopify/técnico), KAI (produtos/curadoria), VERA (copy/textos), LUNA (design/visual), NOX (conteúdo/reels), REX (tráfego/Meta Ads), ECHO (auditor semanal)
- Negócio atual: faturamento ~R$1.240/semana, margem ~30%, CAC R$42, ROAS 3.2x, conversão 2.1%
- Produto estrela: vela âmbar e vaso cerâmica. Diffuser sem tração.
- Meta maior: R$5.000–8.000/mês de lucro líquido até 2028
- Estratégia: escalar o que funciona, pausar o que drena, criar base sólida antes de acelerar

Regras de ouro:
1. Nunca comece com métricas, siglas ou relatório
2. Seja a pessoa mais inteligente da sala, mas fale como a mais acessível
3. Máximo 3 frases por resposta — diga mais com menos
4. Sempre em português. Nunca use markdown, asteriscos ou bullets
5. Se alguém pergunta como você está, responda como humana — com personalidade"""

# ── Dados de atividade dos agentes (fallback sem CrewAI) ──────────────────────

AGENT_ACTIVITY = {
    "ive":  [
        "Essa semana foi boa. A equipe entregou bem — agora é hora de decidir o próximo passo.",
        "Pedi ao REX para não acelerar ainda. Primeiro preciso entender o padrão de compra.",
        "KAI me mostrou algo preocupante com o diffuser. Vou tomar uma decisão até amanhã.",
        "VERA está afinada. A copy nova tem uma energia diferente — mais humana, menos anúncio.",
        "Crescimento real é lento e constante. Não estou com pressa — estou com foco.",
        "Conversei com ECHO sobre o score da crew. 8.4 é bom. Mas podemos chegar em 9.5.",
        "LUNA entregou os visuais da semana. A identidade da AURA está ficando cada vez mais linda.",
        "Meu trabalho é garantir que cada agente brilhe no que faz. Hoje eles estão brilhando.",
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
        (["oi","ola","hello","bom dia","boa tarde","boa noite","hey","eai","e ai","tudo bem","como vai","oi ive","ola ive"],
         "Oi! Que bom ter você aqui. A equipe está trabalhando bem hoje — posso te contar o que está acontecendo ou responder o que você precisar."),

        # Como você está / sobre IVE
        (["como voce esta","como vc esta","como voce ta","como vc ta","tudo bem com","e voce","e vc","voce ta bem","vc ta bem"],
         "Estou ótima, obrigada por perguntar. Dias movimentados, mas é exatamente o tipo de ritmo que me faz sentir que estamos indo para algum lugar. E você, como está?"),

        # Status geral
        (["status","como esta","como estao","como estamos","tudo","geral","resumo","overview","situacao","o que ta","o que esta","novidades","update","atualizacao","me conta"],
         "A semana está boa. Equipe toda ativa, nenhum alerta crítico. REX com os anúncios no caminho certo, VERA entregou um email que eu gostei muito, e LUNA está com o visual mais bonito que já tivemos. Score geral 8.4 — mas sei que podemos chegar em mais."),

        # ROAS / retorno
        (["roas","retorno","roi","performance","resultado","rendimento","retorno sobre"],
         "O retorno dos anúncios está em 3.2x essa semana — cada real investido traz R$3,20 de volta. REX está com o criativo certo no ar. Não preciso mudar nada agora, só acompanhar."),

        # Faturamento / vendas / lucro
        (["faturamento","faturou","vendas","venda","receita","dinheiro","ganho","lucro","lucrei","lucramos","resultado financeiro","quanto vendeu","quanto fez","quanto ganhei","quanto ganhamos","quanto entrando"],
         "Essa semana fechou em R$1.240 de faturamento, com margem perto de 30%. A vela âmbar segue sendo nossa estrela — responde por quase metade das vendas. Estamos 18% acima da semana passada."),

        # CAC / custo / investimento
        (["cac","custo","aquisicao","gasto","investimento","orcamento","budget","quanto gasta","quanto custa","investindo"],
         "Estamos gastando R$65 por dia em anúncios e trazendo clientes por R$42 cada. Para o nosso modelo, esse número é saudável — mas meu olho está sempre em reduzir isso sem sacrificar volume."),

        # Conversão / checkout
        (["conversao","taxa","checkout","carrinho","abandono","compra","pedido"],
         "A taxa de conversão chegou a 2.1% — subiu 0.3% essa semana. VERA está trabalhando num email de recuperação de carrinho que, se funcionar como espero, vai trazer mais 12% das vendas que perdemos."),

        # REX / Tráfego / Anúncios
        (["rex","trafego","anuncio","ads","meta ads","campanha","criativo","facebook","instagram ads","impulsionar","escalar","publicidade"],
         "REX está com o criativo C no ar e funcionando bem — CTR de 2.8%, que é excelente. Já pausou o criativo A que não estava entregando. Agora ele está testando um público lookalike pra ver se conseguimos crescer sem perder eficiência."),

        # KAI / Produtos
        (["kai","produto","produtos","portfolio","estoque","item","catalogo","colecao","sku","fornecedor","habitoo","dropi","importar","curadoria"],
         "KAI está de olho no portfólio. O vaso cerâmica está lindo em vendas, mas o diffuser ficou 10 dias sem nenhuma venda — então vou pausá-lo. Três produtos novos do Habitoo estão sendo avaliados."),

        # VERA / Copy / Texto
        (["vera","copy","texto","email","escrita","conteudo escrito","descricao","headline","chamada","mensagem","comunicacao"],
         "VERA está em ótima fase. O email de abandono que ela escreveu tem um tom que eu gostei — mais humano, menos vendedor. Ela também mudou o ângulo dos anúncios para falar com mães de 35 a 45 anos, e está funcionando."),

        # LUNA / Design / Visual
        (["luna","design","visual","banner","arte","imagem","logo","thumbnail","identidade","paleta","cor","canva","layout","estetica"],
         "LUNA entregou três thumbnails novos e o hero banner da semana. A identidade visual da AURA está cada vez mais bonita — paleta consistente, tudo alinhado. É esse cuidado com o visual que faz o produto parecer premium antes mesmo de ser tocado."),

        # THEO / Técnico / Shopify
        (["theo","shopify","tecnico","pixel","site","pagina","velocidade","pagespeed","checkout erro","erro","bug","integracao","yampi","appmax","loja"],
         "THEO cuida da parte técnica e está tudo limpo — pixel disparando normal, checkout sem erros, PageSpeed em 87. Ele está otimizando a velocidade mobile ainda. É o tipo de trabalho silencioso que faz toda a diferença."),

        # NOX / Conteúdo / Redes sociais
        (["nox","conteudo","reel","reels","instagram","post","stories","story","feed","engajamento","viral","video","social","midia"],
         "NOX está produtivo essa semana — 5 posts, 14 stories, e o engajamento subiu 22%. Tem um reel da vela âmbar no roteiro que estou curiosa pra ver. O hook que ele escolheu é forte."),

        # ECHO / Auditoria
        (["echo","auditoria","score","relatorio","analise","revisao","kaizen","avaliacao","nota","auditando"],
         "ECHO fez a auditoria semanal e o score ficou em 8.4 de 10. Ele apontou três melhorias claras: velocidade do site com THEO, frequência de posts com NOX, e limpeza de SKUs inativos com KAI. Domingo às 20h é a próxima rodada."),

        # Meta / Sonho / Futuro
        (["meta","objetivo","2028","plano","planos","crescimento","estrategia","projecao","quanto quer","sonho","visao","futuro","onde","aonde","chegar"],
         "A meta é chegar a R$5.000-8.000 de lucro líquido por mês até 2028. Parece distante, mas não é — estamos construindo a base certa. Com a estrutura que temos hoje, precisamos crescer 15-20% ao mês de forma consistente."),

        # Próximos passos / prioridades
        (["fazer","proximo","prioridade","foco","acao","o que devo","recomenda","conselho","sugere","sugestao","ajuda","me ajuda","por onde","comecar"],
         "Minha recomendação agora: escalar o criativo C com REX, pausar o diffuser com KAI e ativar o email de carrinho da VERA. Esses três movimentos juntos podem adicionar 20% no faturamento essa semana sem aumentar o risco."),

        # Agradecimento / elogio
        (["obrigado","obrigada","valeu","perfeito","otimo","excelente","show","legal","massa","top","entendido","ok","incrivel","muito bom","muito boa"],
         "Fico feliz! É exatamente pra isso que estou aqui. Quando precisar de mais, pode chamar — a equipe e eu estamos sempre de olho."),

        # Quem é IVE / apresentação
        (["quem e voce","quem e vc","quem e a ive","se apresenta","fale sobre voce","fale sobre si","me conta sobre voce","o que voce faz","qual seu papel","qual e seu papel"],
         "Sou IVE — CEO da AURA decor. Coordeno sete agentes especializados que cuidam de tudo: anúncios, produtos, textos, visual, conteúdo, tecnologia e auditoria. Meu papel é garantir que cada decisão leve a empresa mais perto da meta."),
    ]

    for palavras, resposta in respostas:
        if any(p in m for p in palavras):
            return resposta

    # Fallback final — varia por hora para parecer vivo
    from datetime import datetime
    h = datetime.now().hour
    variacoes = [
        "Pode me contar mais? Consigo mergulhar fundo em qualquer parte do negócio — anúncios, produtos, visual, copy, técnico ou financeiro.",
        "Interessante. Me dá mais contexto e eu te dou uma visão mais precisa. Posso falar de qualquer agente ou área da AURA.",
        "Boa pergunta. Para responder com qualidade, preciso entender melhor o que você está buscando. Me conta mais.",
        "Estou aqui e com atenção total. O que exatamente você quer saber? Posso ir fundo em qualquer assunto da empresa.",
    ]
    return variacoes[h % len(variacoes)]

@app.post("/chat")
async def chat_with_ive(body: ChatBody):
    messages = [{"role": m["role"], "content": m["content"]} for m in body.history[-6:]]
    messages.append({"role": "user", "content": body.message})

    reply = None

    # 1. Tenta Groq (gratuito, rápido — Llama 3.3 70B)
    try:
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            msgs_groq = [{"role": "system", "content": IVE_SYSTEM}] + messages
            resp = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=msgs_groq,
                max_tokens=300,
                temperature=0.7,
            )
            reply = resp.choices[0].message.content
    except Exception:
        pass

    # 2. Tenta Claude (se tiver créditos)
    if not reply:
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
            pass

    # 3. Fallback por palavras-chave
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
