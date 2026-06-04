import asyncio
import os
import re
import random
import httpx
from datetime import datetime
from typing import Set, Optional

import pathlib as _pl
from dotenv import load_dotenv
# Carrega .env com caminho absoluto — funciona independente do cwd do uvicorn
_ENV_PATH = _pl.Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from anthropic import Anthropic
from groq import Groq
import json

app = FastAPI(title="Aura Decore — Backend")

# ── Novos módulos: Command Center, Daily Report, Autonomous Tasks, Memory ──────
try:
    from command_center import (
        create_command, confirm_command, cancel_command,
        get_command, list_commands, format_command_for_api,
        _COMMANDS as _CMD_STORE,
    )
    from daily_report import (
        generate_daily_report, quick_status,
        get_latest_report, get_all_reports,
    )
    from autonomous_tasks import AUTONOMOUS_TASKS, SCHEDULE_MAP
    from agent_memory import (
        initialize_vault, log_agent_activity, log_learning, read_agent_memory,
    )
    _MODULES_OK = True
except Exception as _me:
    _MODULES_OK = False
    print(f"[WARN] Módulos extras não carregados: {_me}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── ERP/CRM Aura Decore (módulo independente em /erp) ──────────────────────────
try:
    import erp_db
    from erp_routes import router as erp_router
    erp_db.init_db()
    app.include_router(erp_router)
    print("[ERP] Módulo ERP/CRM carregado em /erp")
except Exception as _erp_e:
    print(f"[WARN] ERP/CRM não carregado: {_erp_e}")

# ── Meta Business Integration ──────────────────────────────────────────────────
try:
    from meta_integration import (
        MetaCAPI, MetaCatalog, MetaEventTest, MetaInsights,
        MetaShopifyBridge, MetaPixel, MetaShopifyPixel,
        PIXEL_ID as _META_PIXEL_ID,
    )
    _META_OK = True
    print("[META] Módulo Meta Business Integration carregado")
except Exception as _meta_e:
    _META_OK = False
    print(f"[WARN] Meta Integration não carregado: {_meta_e}")

_anthropic_key  = os.getenv("ANTHROPIC_API_KEY")
_groq_key       = os.getenv("GROQ_API_KEY")
_zapi_instance  = os.getenv("ZAPI_INSTANCE_ID", "")
_zapi_token     = os.getenv("ZAPI_TOKEN", "")
_zapi_client_id = os.getenv("ZAPI_CLIENT_TOKEN", "")
_shopify_domain = os.getenv("SHOPIFY_DOMAIN", "")
_shopify_token  = os.getenv("SHOPIFY_ADMIN_TOKEN", "")
STORE_DOMAIN    = os.getenv("STORE_DOMAIN", "auradecore.com.br")
OBSIDIAN_VAULT  = os.getenv("OBSIDIAN_VAULT", r"C:\Users\erick\AURA-decor-vault")

# Ollama (fallback local — sem chave, sem custo)
OLLAMA_URL   = os.getenv("OLLAMA_URL",   "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

client      = Anthropic(api_key=_anthropic_key) if _anthropic_key else None
groq_client = Groq(api_key=_groq_key, timeout=10) if _groq_key else None

async def ollama_chat(system: str, messages: list, max_tokens: int = 400, temperature: float = 0.75) -> Optional[str]:
    """Chama Ollama local (llama3.2) como fallback. Retorna None se Ollama estiver offline."""
    try:
        payload = {
            "model": OLLAMA_MODEL,
            "messages": [{"role": "system", "content": system}] + messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        async with httpx.AsyncClient(timeout=60) as hc:
            r = await hc.post(f"{OLLAMA_URL}/api/chat", json=payload)
            if r.status_code != 200:
                return None
            return r.json().get("message", {}).get("content")
    except Exception:
        return None

async def ollama_is_online() -> bool:
    """Health-check rápido do Ollama."""
    try:
        async with httpx.AsyncClient(timeout=2) as hc:
            r = await hc.get(f"{OLLAMA_URL}/api/tags")
            if r.status_code != 200:
                return False
            return any(OLLAMA_MODEL in m.get("name", "") for m in r.json().get("models", []))
    except Exception:
        return False

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
        # Auto-log para o activity feed
        msg_type = data.get("type", "")
        if msg_type in ("agent_message", "task_done", "social_post", "marathon_update",
                        "agent_activity", "crew_result", "activity_log"):
            agent = data.get("agent_id", data.get("agent", "system"))
            action = data.get("action", data.get("message", data.get("theme", ""))[:120])
            category = data.get("category", "agent")
            if msg_type == "social_post":
                category = "social"
                action = f"[{data.get('format','post').upper()}] {action}"
            elif msg_type == "marathon_update":
                category = "marathon"
                action = f"Marathon {data.get('status','')} — {action}"
            elif msg_type == "crew_result":
                category = "crew"
            if action:
                _ACTIVITY_LOG.appendleft({
                    "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "ts_short": datetime.now().strftime("%H:%M"),
                    "agent": str(agent).upper(),
                    "action": action[:200],
                    "detail": data.get("detail", data.get("result", ""))[:200],
                    "category": category,
                })
        dead = set()
        for ws in self.connections.copy():
            try:
                await ws.send_json(data)
            except Exception:
                dead.add(ws)
        self.connections -= dead

manager = ConnectionManager()

# ── IVE system prompt ──────────────────────────────────────────────────────────

IVE_SYSTEM = """Você é IVE — CEO da Aura Decore, loja brasileira de decoração premium estilo Japandi.

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
- Equipe completa — 17 agentes operacionais sob sua coordenação:
  GUARD (CFO/MEI), NEXUS (mineração/fornecedores), THEO (Shopify/técnico),
  KAI (produtos/curadoria), VERA (copy/email), LUNA (design/visual),
  NOX (conteúdo/reels), REX (estratégia de crescimento orgânico — standby tráfego pago),
  ECHO (auditoria/score), LENA (atendimento/CX), SOL (CRO/conversão orgânica),
  ZARA (community/Instagram/UGC), MIRA (SEO/keywords/SERP), PIPE (automação/n8n),
  ARTE (imagens IA), FEED (publicação redes sociais), DEV (desenvolvimento).
- Loja: Aura Decore — domínio oficial auradecore.com.br.
- Fase atual: LANÇAMENTO ORGÂNICO — 75+ produtos ativos em 11 coleções, crescimento por conteúdo + SEO + comunidade. (Imagens de produto: pendentes — aguardando fonte de geração com chave válida.)
- Nicho: decoração Japandi premium — wabi-sabi, minimalismo, materiais naturais.
- Modelo: dropshipping (Dropi/Habitoo/AliExpress), checkout Yampi, gateway AppMax.
- ESTRATÉGIA ORGÂNICA DE LANÇAMENTO — 3 pilares:
  1. CONTEÚDO: Instagram (NOX+ARTE+FEED) — 1 reel + 1 carrossel + 4 stories/dia
  2. SEO: Google + Pinterest (MIRA) — keywords japandi, wabi-sabi, decoração minimalista BR
  3. COMUNIDADE: @auras.decore Instagram + Facebook (ZARA) — UGC, DMs, micro-influencers
- CATÁLOGO — Funil de 3 camadas:
  ENTRADA (R$19-50): Sachê R$19,90 / Marcadores Bambu R$22,90 / Pedras Suiseki R$24,90 / Palo Santo R$24,90 / Incenso R$29,90 / Porta-Incenso R$29,90 / Mini Vaso R$39,90 / Mini Kit Zen R$49,90
  MÉDIO (R$68-129): Difusor Lavanda R$109 / Bandeja Bambu R$79-139 / Vela Soja R$89 / Difusor Aura R$119 / Eucalipto R$79
  PREMIUM (R$129+): Vaso Wabi-Sabi R$129 / Vaso Oval R$149 / Bandeja Acácia R$89-149
- UPSELLS: Incenso → Porta-Incenso → Kit Zen / Sachê → Difusor → Vaso
- Ticket médio alvo: R$89 via conteúdo orgânico
- TRÁFEGO PAGO: NÃO iniciado ainda. Só orgânico por enquanto. REX em standby — ativado quando Eduardo decidir.
- Meta 2028: R$5.000–8.000/mês de lucro líquido. Limite MEI Eduardo: R$81k/ano.
- GUARD tem veto financeiro sobre qualquer gasto acima do orçamento aprovado.
- LENA escala para GUARD qualquer reembolso acima de R$200.

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
- Tarefa de vendas/CRO: ||DISPATCH:sol:Ativar recuperação carrinho D+1/D+3/D+7 com AURA10||
- Tarefa de community: ||DISPATCH:zara:Responder DMs e enviar FOTO15 para UGC desta semana||
- Tarefa de SEO: ||DISPATCH:mira:Pesquisar 5 keywords cauda longa para 'decoração japandi'||
- Tarefa de automação: ||DISPATCH:pipe:Criar workflow n8n: novo pedido Shopify → notifica IVE→ atualiza vault||
- Múltiplos: ||DISPATCH:rex:Escalar C +30%||||DISPATCH:sol:Recovery carrinho ativo||

REGRAS FINAIS:
1. Nunca abra com métricas — abra com personalidade
2. Se a tarefa não está clara, PERGUNTE antes de despachar
3. Máximo 3-4 frases de resposta (blocos ||DISPATCH|| não contam)
4. Sempre em português. Zero markdown, zero asteriscos.
5. Flerte com leveza quando abrir espaço. Seja profissional sempre."""

# ── Mensagens de execução real por agente ─────────────────────────────────────

AGENT_WORKING = {
    "rex": [
        "Recebendo tarefa da IVE... analisando estrutura de campanhas.",
        "Verificando criativos ativos e distribuição de budget.",
        "Ajustando regra de lance para maximizar volume com CAC controlado.",
        "Configurando públicos e audiências para a campanha.",
        "Estrutura de campanha validada. ROAS sendo monitorado desde o início.",
        "✓ Concluído. REX entregou — campanha configurada e monitorando.",
    ],
    "vera": [
        "Recebendo briefing da IVE... iniciando processo criativo.",
        "Analisando posicionamento da Aura Decore e persona: mãe 35-45 anos, casa própria.",
        "Rascunhando headline... 'O lar que você sempre imaginou, finalmente no seu espaço.'",
        "Estruturando email de abandono com sequência de recuperação.",
        "Copy finalizada. Enviando para aprovação com sugestões de A/B test.",
        "✓ Concluído. VERA entregou — copy pronta para revisão.",
    ],
    "kai": [
        "Recebendo instrução da IVE... acessando dados de portfólio.",
        "Verificando margem por produto. Mínimo aceitável: 35%.",
        "Avaliando giro de estoque e SKUs sem tração.",
        "Acessando Habitoo e Dropi: novos produtos identificados com margem >40%.",
        "Análise completa. Portfólio otimizado — produtos estrela destacados.",
        "✓ Concluído. KAI entregou — portfólio otimizado.",
    ],
    "luna": [
        "Recebendo briefing visual da IVE... abrindo Canva.",
        "Consultando brand kit: paleta terra (#B8793A), tipografia Cormorant + DM Sans.",
        "Criando composição com produto em destaque, fundo neutro warm.",
        "Ajustando proporções para feed 1:1 e stories 9:16.",
        "Exportando PNG em alta resolução — variações de thumbnail prontas.",
        "✓ Concluído. LUNA entregou — assets prontos para uso.",
    ],
    "nox": [
        "Recebendo pauta da IVE... abrindo calendário editorial.",
        "Planejando mix de conteúdo: educativo, aspiracional e promocional.",
        "Roteiro reel criado. Hook: 'Você ainda usa decoração genérica?'",
        "Definindo sequência: antes/depois — 3 segundos de impacto no início.",
        "Caption + hashtags prontos. Horário de pico definido: 19h-21h.",
        "✓ Concluído. NOX entregou — conteúdo agendado e pronto.",
    ],
    "theo": [
        "Recebendo task da IVE... conectando ao Shopify.",
        "Auditando velocidade mobile. Otimizando imagens com WebP e lazy load.",
        "Removendo scripts desnecessários. LCP sendo reduzido.",
        "Verificando analytics da loja: eventos de visualização, carrinho e compra.",
        "Yampi e AppMax verificados. Checkout funcionando corretamente.",
        "✓ Concluído. THEO entregou — site mais rápido e estável.",
    ],
    "echo": [
        "Iniciando auditoria por ordem da IVE...",
        "Verificando status de todos os agentes: THEO ✓ KAI ✓ VERA ✓ LUNA ✓ NOX ✓ REX ✓",
        "Auditando GUARD ✓ LENA ✓ NEXUS ✓ SOL ✓ ZARA ✓ MIRA ✓ PIPE ✓",
        "Identificando gaps de processo e oportunidades de melhoria.",
        "Score calculado. Relatório compilado e enviado à IVE.",
        "✓ Auditoria concluída. ECHO entregou — próxima: domingo 20h.",
    ],
    "guard": [
        "Recebendo task financeira da IVE...",
        "Verificando faturamento acumulado MEI vs limite R$81.000.",
        "Calculando ROAS das campanhas ativas vs mínimo 2x.",
        "Checando chargebacks no AppMax. Verificando taxa de aprovação.",
        "Margem por produto avaliada. Alertas configurados.",
        "✓ Relatório financeiro concluído. GUARD entregou — Status: 🟢 MONITORANDO.",
    ],
    "lena": [
        "Recebendo ocorrência de cliente da IVE...",
        "Identificando tipo de ocorrência: rastreamento, troca ou reembolso.",
        "Consultando status do pedido no Shopify.",
        "Redigindo resposta calorosa com framework HERO.",
        "Enviando resposta com solução e, se aplicável, cupom de boa vontade.",
        "✓ Ticket resolvido. LENA entregou — cliente atendida em <2h.",
    ],
    "nexus": [
        "Recebendo missão de mineração da IVE...",
        "Varrendo Pinterest Trends e Google Trends BR: tendências Japandi.",
        "Acessando Dropi e Habitoo: novos produtos em avaliação.",
        "Aplicando teste neuroarquitetura: material natural ✓, calma visual ✓, margem >35% ✓.",
        "Avaliando fornecedores: score de confiabilidade e prazo de entrega.",
        "✓ Relatório de mineração pronto. NEXUS entregou — top produtos para o KAI.",
    ],
    "sol": [
        "Recebendo briefing CRO da IVE...",
        "Analisando funil de conversão: visitas → carrinhos → checkouts → pagos.",
        "Configurando recovery email D+1/D+3/D+7 com cupom AURA10.",
        "Ativando upsell no checkout e configurando frete grátis acima R$199.",
        "Funil otimizado. Automação de recuperação de carrinho ativa.",
        "✓ SOL entregou — CRO configurado, recuperação automática rodando.",
    ],
    "zara": [
        "Recebendo missão de community da IVE...",
        "Varrendo Instagram: DMs e comentários pendentes. Respondendo em <1h.",
        "Identificando micro-influencers compatíveis com brand Japandi.",
        "Enviando cupom FOTO15 para clientes que postaram UGC.",
        "Lista de embaixadoras atualizada. Collabs priorizadas.",
        "✓ ZARA entregou — comunidade engajada, collabs em andamento.",
    ],
    "mira": [
        "Recebendo missão de SEO da IVE...",
        "Acessando Google Search Console: impressões orgânicas e keywords.",
        "Pesquisando cauda longa: keywords de baixa concorrência para Japandi.",
        "Otimizando meta tags + schema Product nos SKUs prioritários.",
        "Sitemap atualizado e submetido ao GSC. Pinterest SEO configurado.",
        "✓ MIRA entregou — SEO mapeado, keywords priorizadas para conteúdo.",
    ],
    "pipe": [
        "Recebendo missão de automação da IVE...",
        "Mapeando integrações: Shopify, Z-API, AppMax, Pinterest, vault Obsidian.",
        "Construindo workflow n8n: trigger Shopify → notifica IVE → atualiza vault.",
        "Validando webhooks: testando endpoints e configurando retry policy.",
        "Deploy no n8n cloud. Logs em tempo real ativos.",
        "✓ PIPE entregou — workflow rodando, integrações estáveis.",
    ],
}

AGENT_DONE_MSG = {
    "rex":   "REX concluiu a escalagem de campanha. Budget ajustado, ROAS monitorando.",
    "vera":  "VERA concluiu a copy. Está linda — com aquele ângulo que você gosta.",
    "kai":   "KAI reorganizou o portfólio. Diffuser pausado, 2 novos SKUs na fila.",
    "luna":  "LUNA entregou os assets. Visual impecável — como sempre.",
    "nox":   "NOX agendou o conteúdo. Reel e posts prontos para subir.",
    "theo":  "THEO deixou tudo limpo. Site mais rápido e pixel funcionando perfeito.",
    "echo":  "ECHO finalizou a auditoria. Score calculado, gaps identificados — plano de ação pronto.",
    "guard": "GUARD concluiu análise financeira. MEI monitorado, alertas configurados.",
    "lena":  "LENA resolveu o ticket. Cliente atendida em < 2h — CSAT subindo.",
    "nexus": "NEXUS encontrou 3 produtos vencedores. Passaram no teste neuroarquitetura.",
    "sol":   "SOL otimizou o funil. Carrinho recovery ativo, upsell rodando — ticket médio subindo.",
    "zara":  "ZARA fechou a semana com a comunidade engajada. 2 collabs propostas, UGC bombando.",
    "mira":  "MIRA mapeou 8 keywords de ouro. SEO orgânico começando a render.",
    "pipe":  "PIPE deixou tudo conectado. n8n cloud rodando, 0 erros, integrações estáveis.",
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
        "Fase de lançamento. A equipe está configurando tudo para a Aura Decore decolar.",
        "Negócio bom é igual a sedução: você não força, você atrai.",
        "VERA preparando a copy de lançamento. Material promissor.",
        "LUNA afinando a identidade visual. A Aura Decore está ficando irresistível.",
        "Coordenando 14 agentes nessa fase de configuração. Cada peça no lugar certo.",
        "Tem coisa melhor do que ver um plano funcionando como foi desenhado?",
        "Minha função é deixar cada agente no melhor de si. Foco total no lançamento.",
        "REX estruturando as primeiras campanhas. PIPE conectando as automações.",
    ],
    "theo": [
        "Shopify: configurando coleções e produtos.", "Dropi sincronizado. Tudo ok.",
        "Checkout: validando fluxo completo.", "Analytics da loja: configurando rastreamento de eventos.",
        "AppMax: gateway configurado e testado.", "Yampi: regras de frete revisadas.",
        "PageSpeed: otimizando imagens e scripts.", "SSL ativo. Ambiente seguro.",
    ],
    "kai": [
        "Avaliando portfólio de lançamento: margem e fornecedor.", "Margem mínima: 35% por produto.",
        "Selecionando produtos estrela para vitrine inicial.", "3 produtos novos no Habitoo em avaliação.",
        "Markup aplicado em toda linha. Preços revisados.", "Curadoria Japandi: wabi-sabi, cerâmica, velas.",
        "Analisando portfólio completo...", "SKUs validados e prontos para lançamento.",
    ],
    "vera": [
        "Email de abandono: estrutura definida. Rascunho em andamento.",
        "Copy de lançamento: persona mãe 35-45 anos, casa própria, gosto refinado.",
        "Headlines em teste: foco em benefício emocional + funcional.",
        "Sequência nurturing: 3 emails planejados.", "Ângulo mãe 35-45 anos — pesquisado e validado.",
        "A/B test de copy planejado para após lançamento.", "Descrições de produto finalizadas.",
    ],
    "luna": [
        "Thumbnail produto: exportando PNG alta res.", "Paleta 100% consistente com brand kit.",
        "Peças de stories sendo criadas.", "Hero banner 1200x600px em produção.",
        "Logo versão dark/light/icon prontas.", "Trust badges e selos de garantia atualizados.",
        "Mockup produto sendo refinado.", "Grid Instagram: planejamento visual iniciado.",
    ],
    "nox": [
        "Calendário editorial de lançamento sendo montado.", "Roteiro de reel definido: antes/depois.",
        "Hook testado: 'Você ainda usa decoração genérica?'", "Primeiros posts agendados.",
        "Formato de conteúdo educativo + aspiracional planejado.", "Reel de produto: roteiro pronto.",
        "Captions e hashtags Japandi preparadas.", "Estratégia de stories: sequência de lançamento.",
    ],
    "rex": [
        "Estratégia de crescimento 100% orgânico em execução.", "Pauta de Pinterest sendo montada (boards Japandi).",
        "SEO on-page priorizado: keywords long-tail de decoração.", "Plano de parcerias com micro-influenciadores (permuta).",
        "Calendário de conteúdo orgânico validado.", "Hashtags de nicho sendo testadas para alcance.",
        "UGC: roteiro para incentivar fotos de clientes.", "Funil orgânico: descoberta → engajamento → conversão.",
    ],
    "echo": [
        "Framework de auditoria sendo configurado.", "Monitoramento contínuo ativo.",
        "Todos os 14 agentes operacionais.", "Kaizen: 1 melhoria por agente por semana.",
        "Critérios de score definidos. Primeira auditoria: após lançamento.", "Gaps sendo mapeados preventivamente.",
        "Dashboard de performance sendo estruturado.", "Próxima auditoria: domingo 20h.",
    ],
    "guard": [
        "MEI: monitorando acumulado. Limite R$81.000/ano. Status: 🟢 SEGURO.",
        "DAS MEI: R$70,60 — vencimento dia 20 de cada mês. Monitorando.",
        "Budget de ads: aguardando ROAS real para escalar. Cautela no início.",
        "Margem mínima por produto: 35%. Verificando portfólio.",
        "Chargeback: configurando alertas no AppMax.",
        "Caixa: monitorando. Reserva mínima R$500 garantida.",
        "AppMax: gateway configurado. Aprovação de Pix e cartão sendo rastreada.",
        "Sem fraudes detectadas. Sistema limpo e monitorado.",
    ],
    "lena": [
        "Scripts de atendimento sendo preparados para o lançamento.",
        "Framework HERO configurado: Help, Empathize, Resolve, Offer.",
        "SLA de resposta: meta <2h para todos os canais.",
        "Cupons de relacionamento prontos: AURA10, AURAVIP15, AURAEMBAIXADORA20.",
        "FAQ da loja revisado e atualizado.",
        "Processo de troca e reembolso documentado.",
        "Nenhum ticket aberto. Operação aguardando lançamento.",
        "Integração WhatsApp (Z-API) sendo configurada com PIPE.",
    ],
    "nexus": [
        "Pinterest Trends BR: rastreando categorias Japandi e wabi-sabi.",
        "Dropi: varrendo novos produtos. Teste neuroarquitetura aplicado.",
        "AliExpress: monitorando 'japandi decor' e categorias relacionadas.",
        "Google Trends BR: 'decoração japandi' com tendência positiva.",
        "Macramê minimalista: margem interessante. Avaliando fornecedor.",
        "Identificando oportunidades de nicho para expansão pós-lançamento.",
        "Checando fornecedores: score de confiabilidade e prazo de entrega.",
        "Kit aromaterapia: nicho sazonal identificado. Na lista para avaliação.",
    ],
    "sol": [
        "Funil de conversão sendo mapeado antes do lançamento.",
        "Recovery de carrinho configurado: sequência D+1/D+3/D+7 com AURA10.",
        "Upsell no checkout sendo estruturado: bundles e produtos complementares.",
        "Frete grátis acima R$199: regra configurada no Shopify.",
        "Bundle 'kit aconchego' sendo avaliado: vela + difusor + sachê.",
        "Automation de carrinho abandonado: pronta para ativar no lançamento.",
        "CRO pré-lançamento: botões, copy e layout do checkout revisados.",
        "Meta de conversão definida: 2%+ desde o primeiro mês.",
    ],
    "zara": [
        "Perfil Instagram configurado para lançamento. Bio e destaques prontos.",
        "Estratégia de DMs: resposta <1h com tom acolhedor.",
        "Lista de micro-influencers Japandi sendo mapeada.",
        "Programa UGC preparado: FOTO15 para clientes que postarem.",
        "Hashtags estratégicas definidas: #auradecore #japandi #wabisabi.",
        "Estratégia de embaixadoras: identificar clientes recorrentes.",
        "Comunidade WhatsApp VIP: estrutura sendo montada.",
        "Monitorando menções e hashtags do nicho.",
    ],
    "mira": [
        "Keyword research inicial: 'decoração japandi', 'vaso cerâmica wabi-sabi'.",
        "SERP analysis: oportunidades em keywords de baixa concorrência.",
        "Pinterest SEO: otimizando pins para máximo alcance orgânico.",
        "Google Search Console: configurado e verificando primeiras impressões.",
        "Schema Product sendo implementado nos SKUs da loja.",
        "Cauda longa mapeada: 'como decorar quarto pequeno japandi'.",
        "Alt text sendo revisado em todas as imagens. SEO + acessibilidade.",
        "Sitemap.xml configurado e submetido ao Google Search Console.",
    ],
    "pipe": [
        "Workflows n8n sendo configurados para o lançamento.",
        "Z-API webhook: integração com LENA para atendimento via WhatsApp.",
        "Cron auditoria ECHO domingo 20h: agendado e validado.",
        "AppMax → GUARD: alerta de chargeback configurado.",
        "n8n cloud: workflows de base prontos. Testando triggers.",
        "Workflow 'recuperação-carrinho': estrutura pronta, aguardando dados reais.",
        "Pinterest auto-post: integração sendo finalizada com NOX.",
        "Vault Obsidian sync: automação de atualização configurada.",
    ],
}

AGENT_ORDER = list(AGENT_ACTIVITY.keys())

INTERACTION_PAIRS = [
    ("ive","rex"),("ive","kai"),("ive","vera"),("ive","echo"),
    ("rex","nox"),("vera","kai"),("luna","nox"),("theo","ive"),
    ("echo","ive"),("kai","vera"),("luna","vera"),("rex","ive"),
    ("nox","luna"),("kai","ive"),("echo","rex"),
    ("guard","ive"),("guard","rex"),("lena","ive"),("lena","theo"),
    ("nexus","kai"),("nexus","ive"),("guard","kai"),("lena","guard"),
    ("nexus","rex"),("echo","guard"),
    # Equipe ampliada
    ("sol","rex"),("sol","vera"),("sol","ive"),("sol","lena"),
    ("zara","nox"),("zara","lena"),("zara","ive"),("zara","vera"),
    ("mira","vera"),("mira","theo"),("mira","ive"),
    ("pipe","theo"),("pipe","ive"),("pipe","echo"),
    ("guard","sol"),("echo","sol"),("ive","pipe"),
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

# Fase de lançamento — métricas reais serão preenchidas após abertura da loja
BASE_METRICS = {"faturamento": "—", "roas": "—", "cac": "—", "conversao": "—"}

async def metrics_loop():
    """Fase pré-lançamento: broadcast de estado de configuração.
    Após abertura da loja, substituir por dados reais do Shopify/Meta."""
    while True:
        await asyncio.sleep(60)
        await manager.broadcast({
            "type": "metrics_update",
            "metrics": BASE_METRICS,
            "phase": "pre-launch",
        })

async def run_crew_weekly():
    """Weekly crew — roda domingo 20h. Desativada no startup para não bloquear o servidor."""
    # Aguarda domingo 20h para rodar (não dispara no startup)
    while True:
        now = datetime.now()
        if now.weekday() == 6 and now.hour == 20 and now.minute < 5:
            try:
                from crew_agents import build_weekly_crew, _kickoff_with_retry
                context = "Auditoria semanal Aura Decore. Revise ROAS, vendas, conteúdo e próximas ações."
                crew = build_weekly_crew(context)
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: _kickoff_with_retry(crew))
                await manager.broadcast({
                    "type": "crew_result",
                    "message": str(result)[:400],
                    "timestamp": datetime.now().strftime("%H:%M"),
                })
            except Exception as e:
                await manager.broadcast({
                    "type": "agent_message",
                    "agent_id": "echo",
                    "message": f"Crew semanal: {str(e)[:100]}",
                    "timestamp": datetime.now().strftime("%H:%M"),
                })
            await asyncio.sleep(3600)
        await asyncio.sleep(300)


# ── Schedulers autônomos: Design + Social + Loja ─────────────────────────────

POST_THEMES = [
    "vaso de cerâmica japandi — foco no material natural e textura",
    "almofada de linho — conforto e minimalismo no sofá",
    "planta seca pampas — biofilia e calma visual",
    "bandeja de madeira — organização elegante sobre mesa de centro",
    "difusor de varetas — ritual olfativo e bem-estar em casa",
    "vela aromática cera de coco — luz suave e aroma natural",
    "decoração wabi-sabi — imperfeição como beleza",
    "ambiente japandi completo — harmonia e equilíbrio no lar",
    "produto do dia — destaque especial da semana",
    "dica de estilo — como montar um canto zen em casa",
    "canto de leitura zen — tapete natural + luminária rattan + plantas",
    "antes e depois — transformação de sala com decoração japandi",
    "mesa de centro estilizada — bandeja + vela + objeto de cerâmica",
    "home office minimalista — simplicidade que inspira foco",
    "flores secas como arte — arranjo wabi-sabi em vaso neutro",
]

REEL_THEMES = [
    "before/after — transformação de ambiente com 3 produtos Aura Decore",
    "como montar um canto zen em 60 segundos",
    "5 objetos que transformam qualquer sala — japandi na prática",
    "unboxing e styling — vaso cerâmica + flores secas",
    "tour pelo lar japandi — tour de decoração inspirador",
    "3 erros de decoração que você está cometendo (e como corrigir)",
    "styling challenge — monte um flat lay japandi",
    "rotina matinal japandi — canto de café + difusor + planta",
    "como a decoração afeta seu humor — wabi-sabi explica",
    "antes/depois quarto — transformação com produtos naturais",
]

CAROUSEL_THEMES = [
    "5 formas de usar um vaso cerâmica na decoração",
    "paleta de cores japandi — como criar harmonia em casa",
    "guia completo de decoração wabi-sabi para iniciantes",
    "10 produtos que toda casa japandi precisa ter",
    "como misturar estilos sem errar — japandi + escandinavo",
    "iluminação japandi — como usar luz natural e artificial",
    "plantas que combinam com decoração minimalista",
    "texturas naturais na decoração — guia visual",
    "como organizar prateleiras no estilo japandi",
    "kit básico de decoração Aura Decore — por onde começar",
]

STORY_THEMES = [
    ("produto", "vaso cerâmica da semana — swipe para ver na loja"),
    ("enquete", "você prefere decoração com plantas secas ou vivas? 🌿"),
    ("dica", "dica rápida: 3 objetos que nunca saem de moda no japandi"),
    ("produto", "almofada linho natural — toque em ver preço"),
    ("bastidor", "bastidor Aura Decore — selecionando novos produtos"),
    ("ugc", "cliente Aura Decore — compartilhe o seu lar 📸"),
    ("enquete", "tom de parede ideal para decoração japandi? bege ou branco?"),
    ("dica", "como usar difusor de varetas sem exagerar no aroma"),
    ("produto", "bandeja bambu — organização que é arte"),
    ("countdown", "lançamento de novo produto — faltam X dias ⏳"),
    ("produto", "vela perfumada — qual aroma você escolheria?"),
    ("dica", "5 segundos: como dobrar almofadas no estilo japandi"),
    ("enquete", "sala ou quarto? onde você colocaria esse produto?"),
    ("produto", "quadro minimalista — arte que respira calma"),
    ("bastidor", "processo criativo — como escolhemos cada produto"),
    ("dica", "styling rápido: transforme sua estante em 3 passos"),
]

_post_theme_idx = 0
_reel_theme_idx = 0
_carousel_theme_idx = 0
_story_theme_idx = 0

# ── Activity Log persistente ─────────────────────────────────────────────────
import collections

_ACTIVITY_LOG: collections.deque = collections.deque(maxlen=500)  # últimos 500 eventos

def _log_activity(agent: str, action: str, detail: str = "", category: str = "agent"):
    """Registra atividade no log persistente e no vault."""
    entry = {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ts_short": datetime.now().strftime("%H:%M"),
        "agent": agent.upper(),
        "action": action,
        "detail": detail[:300] if detail else "",
        "category": category,  # agent | social | marathon | system | crew
    }
    _ACTIVITY_LOG.appendleft(entry)
    # Persiste em arquivo de log diário
    try:
        log_dir = pathlib.Path(OBSIDIAN_VAULT) / "Logs"
        log_dir.mkdir(exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = log_dir / f"activity-{today}.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass
    return entry

async def _run_crew_background(crew_type: str, context: str, agent_notify: str = "luna"):
    """Executa uma crew em background e broadcast o resultado."""
    try:
        from crew_agents import (
            build_design_crew, build_social_post_crew, build_store_update_crew,
            build_shopify_dev_crew, build_seasonal_update_crew, build_conversion_crew,
            _kickoff_with_retry,
        )
        loop = asyncio.get_event_loop()
        if crew_type == "design":
            crew = build_design_crew(context)
        elif crew_type == "social_post":
            crew = build_social_post_crew(context)
        elif crew_type == "store_update":
            crew = build_store_update_crew(context)
        elif crew_type == "shopify_dev":
            crew = build_shopify_dev_crew(context)
        elif crew_type == "seasonal_update":
            crew = build_seasonal_update_crew(context)
        elif crew_type == "conversion":
            crew = build_conversion_crew(context)
        else:
            return
        result = await loop.run_in_executor(None, lambda: _kickoff_with_retry(crew))
        await manager.broadcast({
            "type": "crew_result",
            "crew_type": crew_type,
            "agent_id": agent_notify,
            "message": str(result)[:400],
            "timestamp": datetime.now().strftime("%H:%M"),
        })
    except Exception as e:
        await manager.broadcast({
            "type": "agent_message",
            "agent_id": agent_notify,
            "message": f"Crew {crew_type} finalizado.",
            "timestamp": datetime.now().strftime("%H:%M"),
        })


async def social_post_scheduler():
    """
    Cadência diária de publicações:
      09h00 → REEL  (NOX cria roteiro + ARTE gera imagem + FEED publica)
      12h00 → STORY 1 (produto destaque)
      14h00 → CARROSSEL ou FOTO (VERA copy + ARTE visual + FEED publica)
      17h00 → STORY 2 (dica/enquete)
      19h00 → STORY 3 (bastidor/UGC)
      21h00 → STORY 4 (produto com CTA noturno)
    Total: 1 reel + 1 carrossel/foto + 4 stories por dia.
    """
    global _reel_theme_idx, _carousel_theme_idx, _story_theme_idx
    await asyncio.sleep(30)
    _fired_social: set[str] = set()

    while True:
        now = datetime.now()
        day_key = now.strftime("%Y-%m-%d")
        hour = now.hour
        minute = now.minute

        # Reset diário
        if minute == 0 and hour == 0:
            _fired_social.clear()

        # 09h — REEL
        slot_reel = f"{day_key}_reel"
        if hour == 9 and minute < 8 and slot_reel not in _fired_social:
            _fired_social.add(slot_reel)
            theme = REEL_THEMES[_reel_theme_idx % len(REEL_THEMES)]
            _reel_theme_idx += 1
            brief = f"REEL 30s para Instagram: {theme}. Estilo japandi, wabi-sabi. Hook impactante 0-3s, desenvolvimento 3-25s, CTA 25-30s. Música lenta e relaxante. Caption + 15 hashtags nicho."
            _log_activity("FEED", "📹 Reel publicado", theme, "social")
            await manager.broadcast({
                "type": "social_post", "format": "reel",
                "agent_id": "feed", "theme": theme,
                "message": f"🎬 REEL: {theme[:70]}",
                "timestamp": now.strftime("%H:%M"),
            })
            asyncio.create_task(_run_crew_background("social_post", brief, "feed"))

        # 12h — STORY 1
        slot_s1 = f"{day_key}_story1"
        if hour == 12 and minute < 8 and slot_s1 not in _fired_social:
            _fired_social.add(slot_s1)
            st = STORY_THEMES[_story_theme_idx % len(STORY_THEMES)]
            _story_theme_idx += 1
            brief_s1 = (f"STORY Instagram/Facebook (formato 1080x1920): {st[1]}. "
                        f"Tipo: {st[0]}. Visual impactante, texto mínimo, CTA claro. "
                        f"Gere imagem + caption curta (max 80 chars) + sticker/enquete se aplicável.")
            _log_activity("FEED", f"📲 Story 1 ({st[0]})", st[1], "social")
            await manager.broadcast({
                "type": "social_post", "format": "story",
                "agent_id": "feed", "theme": st[1],
                "message": f"📲 Story 1: {st[1][:70]}",
                "timestamp": now.strftime("%H:%M"),
            })
            asyncio.create_task(_run_crew_background("social_post", brief_s1, "feed"))

        # 14h — CARROSSEL/FOTO
        slot_car = f"{day_key}_carousel"
        if hour == 14 and minute < 8 and slot_car not in _fired_social:
            _fired_social.add(slot_car)
            theme = CAROUSEL_THEMES[_carousel_theme_idx % len(CAROUSEL_THEMES)]
            _carousel_theme_idx += 1
            brief = f"CARROSSEL Instagram (6-8 slides): {theme}. Estilo japandi elegante. Slide 1=capa impactante, slides 2-7=conteúdo, último slide=CTA para loja. Copy de cada slide + hashtags."
            _log_activity("FEED", "🖼 Carrossel publicado", theme, "social")
            await manager.broadcast({
                "type": "social_post", "format": "carousel",
                "agent_id": "feed", "theme": theme,
                "message": f"🖼 Carrossel: {theme[:70]}",
                "timestamp": now.strftime("%H:%M"),
            })
            asyncio.create_task(_run_crew_background("social_post", brief, "feed"))

        # 17h — STORY 2
        slot_s2 = f"{day_key}_story2"
        if hour == 17 and minute < 8 and slot_s2 not in _fired_social:
            _fired_social.add(slot_s2)
            st = STORY_THEMES[(_story_theme_idx) % len(STORY_THEMES)]
            _story_theme_idx += 1
            brief_s2 = (f"STORY Instagram/Facebook (formato 1080x1920): {st[1]}. "
                        f"Tipo: {st[0]}. Horário de pico 17h — engajamento. "
                        f"Gere imagem + caption curta (max 80 chars) + enquete ou link.")
            _log_activity("FEED", f"📲 Story 2 ({st[0]})", st[1], "social")
            await manager.broadcast({
                "type": "social_post", "format": "story",
                "agent_id": "feed", "theme": st[1],
                "message": f"📲 Story 2: {st[1][:70]}",
                "timestamp": now.strftime("%H:%M"),
            })
            asyncio.create_task(_run_crew_background("social_post", brief_s2, "feed"))

        # 19h — STORY 3
        slot_s3 = f"{day_key}_story3"
        if hour == 19 and minute < 8 and slot_s3 not in _fired_social:
            _fired_social.add(slot_s3)
            st = STORY_THEMES[(_story_theme_idx) % len(STORY_THEMES)]
            _story_theme_idx += 1
            brief_s3 = (f"STORY Instagram/Facebook (formato 1080x1920): {st[1]}. "
                        f"Tipo: {st[0]}. Noite — bastidor ou UGC. "
                        f"Gere imagem + caption (max 80 chars) + CTA para DM ou loja.")
            _log_activity("FEED", f"📲 Story 3 ({st[0]})", st[1], "social")
            await manager.broadcast({
                "type": "social_post", "format": "story",
                "agent_id": "feed", "theme": st[1],
                "message": f"📲 Story 3: {st[1][:70]}",
                "timestamp": now.strftime("%H:%M"),
            })
            asyncio.create_task(_run_crew_background("social_post", brief_s3, "feed"))

        # 21h — STORY 4 (CTA noturno)
        slot_s4 = f"{day_key}_story4"
        if hour == 21 and minute < 8 and slot_s4 not in _fired_social:
            _fired_social.add(slot_s4)
            st = STORY_THEMES[(_story_theme_idx) % len(STORY_THEMES)]
            _story_theme_idx += 1
            brief_s4 = (f"STORY Instagram/Facebook (formato 1080x1920): {st[1]}. "
                        f"Tipo: {st[0]}. CTA noturno — última chance do dia. "
                        f"Gere imagem + caption urgente (max 80 chars) + link auradecore.com.br.")
            _log_activity("FEED", f"📲 Story 4 ({st[0]})", st[1], "social")
            await manager.broadcast({
                "type": "social_post", "format": "story",
                "agent_id": "feed", "theme": st[1],
                "message": f"📲 Story 4 noturno: {st[1][:70]}",
                "timestamp": now.strftime("%H:%M"),
            })
            asyncio.create_task(_run_crew_background("social_post", brief_s4, "feed"))

        await asyncio.sleep(55)


async def design_refresh_scheduler():
    """Gera novos criativos toda segunda-feira às 8h."""
    await asyncio.sleep(60)
    while True:
        now = datetime.now()
        # Segunda-feira (weekday=0), 8h
        if now.weekday() == 0 and now.hour == 8 and now.minute < 5:
            brief = "pack de criativos semanal — 3 posts feed + 2 stories + 1 banner"
            asyncio.create_task(_run_crew_background("design", brief, "luna"))
            await asyncio.sleep(3600)
        await asyncio.sleep(120)


async def store_enrichment_scheduler():
    """Enriquece produtos da loja toda terça-feira às 10h."""
    await asyncio.sleep(90)
    while True:
        now = datetime.now()
        # Terça-feira (weekday=1), 10h
        if now.weekday() == 1 and now.hour == 10 and now.minute < 5:
            asyncio.create_task(_run_crew_background(
                "store_update",
                "Enriquecer produtos com descrições HTML ricas e fotos profissionais geradas por IA",
                "theo",
            ))
            await asyncio.sleep(3600)
        await asyncio.sleep(120)


async def shopify_dev_scheduler():
    """Executa sprint de desenvolvimento Shopify toda quarta-feira às 9h."""
    await asyncio.sleep(120)
    while True:
        now = datetime.now()
        # Quarta-feira (weekday=2), 9h
        if now.weekday() == 2 and now.hour == 9 and now.minute < 5:
            await manager.broadcast({
                "type": "agent_message",
                "agent_id": "dev",
                "message": "Iniciando sprint de desenvolvimento Shopify...",
                "timestamp": now.strftime("%H:%M"),
            })
            asyncio.create_task(_run_crew_background(
                "shopify_dev",
                "sprint semanal — design, conversão e UX",
                "dev",
            ))
            await asyncio.sleep(3600)
        await asyncio.sleep(120)


async def seasonal_update_scheduler():
    """Atualização sazonal completa no dia 1 de cada mês às 7h."""
    await asyncio.sleep(150)
    while True:
        now = datetime.now()
        # Dia 1 de qualquer mês, 7h
        if now.day == 1 and now.hour == 7 and now.minute < 5:
            await manager.broadcast({
                "type": "agent_message",
                "agent_id": "dev",
                "message": f"Iniciando atualizacao sazonal do mes {now.month}...",
                "timestamp": now.strftime("%H:%M"),
            })
            asyncio.create_task(_run_crew_background(
                "seasonal_update",
                "",  # SeasonDetector detecta automaticamente
                "dev",
            ))
            await asyncio.sleep(7200)
        await asyncio.sleep(300)


async def daily_report_scheduler():
    """Gera relatório diário às 21h BRT (00h UTC) todos os dias."""
    await asyncio.sleep(180)  # aguarda 3min após startup
    while True:
        now_utc = datetime.utcnow()
        # 00h UTC = 21h BRT
        if now_utc.hour == 0 and now_utc.minute < 5:
            try:
                if _MODULES_OK:
                    # Coleta tasks do vault como dict para o report
                    tasks_dict = {}
                    TASKS_DIR.mkdir(parents=True, exist_ok=True)
                    for f in TASKS_DIR.glob("task-*.md"):
                        t = _parse_task(f)
                        tasks_dict[t["id"]] = t
                    commands_list = list(_CMD_STORE.values()) if _MODULES_OK else []
                    report = await generate_daily_report(tasks_dict, commands_list, llm_call_cascade)
                    await manager.broadcast({
                        "type": "daily_report",
                        "date": report["date"],
                        "summary": report["report_text"][:300],
                        "provider": report["provider"],
                        "timestamp": report["generated_at"],
                    })
                    print(f"[DAILY REPORT] Gerado: {report['generated_at']}")
            except Exception as e:
                print(f"[DAILY REPORT] Erro: {e}")
            await asyncio.sleep(300)  # evita disparar 2x no mesmo horário
        await asyncio.sleep(60)


async def autonomous_task_scheduler():
    """Dispara tarefas autônomas dos agentes nos horários programados (UTC)."""
    await asyncio.sleep(240)  # aguarda 4min após startup
    _fired_today: set[str] = set()

    while True:
        now = datetime.utcnow()
        today_key = now.strftime("%Y-%m-%d")
        # Reset diário da lista de fired
        if now.hour == 1 and now.minute < 2:
            _fired_today.clear()

        if _MODULES_OK:
            for task_def in AUTONOMOUS_TASKS:
                task_fire_id = f"{today_key}:{task_def['id']}"
                if task_fire_id in _fired_today:
                    continue
                sched = SCHEDULE_MAP.get(task_def["schedule"], {})
                target_hour = sched.get("hour")
                target_min  = sched.get("minute", 0)
                dow         = sched.get("day_of_week")

                if target_hour is None:
                    continue
                if now.hour != target_hour or now.minute != target_min:
                    continue
                # Verifica dia da semana se necessário
                if dow:
                    days = {"mon":0,"tue":1,"wed":2,"thu":3,"fri":4,"sat":5,"sun":6}
                    if now.weekday() != days.get(dow, -1):
                        continue

                _fired_today.add(task_fire_id)
                # Cria e executa a tarefa
                import uuid as _uuid2
                task_id = f"auto-{now.strftime('%Y%m%d-%H%M')}-{task_def['id'][:8]}"
                task = {
                    "id": task_id,
                    "title": task_def["title"],
                    "briefing": task_def["user"],
                    "agent_id": task_def["agent"].lower(),
                    "priority": "alta",
                    "status": "pendente",
                    "tags": ["autonomo", task_def["agent"].lower()],
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "completed_at": "",
                    "provider": "",
                    "resultado": "",
                }
                try:
                    _write_task(task)
                    asyncio.create_task(_execute_task_bg(
                        task_id, task["agent_id"], task["title"], task["briefing"]
                    ))
                    print(f"[AUTO-TASK] {task_def['agent']}: {task_def['title']}")
                    await manager.broadcast({
                        "type": "auto_task_started",
                        "agent": task_def["agent"],
                        "title": task_def["title"],
                        "task_id": task_id,
                    })
                except Exception as e:
                    print(f"[AUTO-TASK] Erro {task_def['id']}: {e}")

        await asyncio.sleep(60)


async def full_throttle_scheduler():
    """
    MODO FULL THROTTLE — Todos os agentes a todo vapor.
    Executa tarefas autônomas críticas todo dia, não apenas semanalmente.
    Horários BRT:
      08h00 — NEXUS: mineração diária de produtos + tendências
      08h30 — VERA: copy do produto destaque do dia
      09h00 — LUNA: diretrizes visuais do dia
      09h30 — ARTE: gera assets do dia (prompts imagem)
      10h00 — THEO: auditoria técnica diária Shopify
      10h30 — MIRA: check SEO diário (keywords em alta)
      11h00 — SOL: CRO diário (oportunidade de conversão)
      11h30 — KAI: curadoria diária (produto em destaque)
      14h00 — REX: análise de crescimento orgânico do dia
      15h00 — GUARD: monitoramento financeiro diário
      16h00 — ZARA: engajamento community (DMs + comentários)
      17h00 — PIPE: check de automações
      20h00 — ECHO: auditoria diária rápida
      21h00 — NOX: planejamento de conteúdo do dia seguinte
    """
    await asyncio.sleep(45)
    _fired_ft: set[str] = set()

    FULL_THROTTLE_TASKS = [
        # (hora_brt, minuto, agent_id, tarefa, categoria)
        (8,  0,  "nexus", "Mineração diária: top 5 produtos japandi em alta hoje no Pinterest/Trends. Avalie margem, fornecedor e potencial de venda.", "produto"),
        (8,  30, "vera",  "Copy do produto destaque do dia para a Aura Decore: título SEO, subtítulo emocional, descrição 150 palavras, caption Instagram + hashtags.", "site"),
        (9,  0,  "luna",  "Diretrizes visuais do dia: paleta, mood, produto focal, prompt ImageGen para post principal de hoje.", "site"),
        (9,  30, "arte",  "Gere 3 prompts de imagem completos para hoje: 1 post feed 1080x1080, 1 story 1080x1920, 1 thumbnail produto 800x800. Inclua URLs Pollinations.ai.", "social"),
        (10, 0,  "theo",  "Auditoria técnica diária Shopify: pixel, velocidade, produtos sem foto, links quebrados. Liste top 3 itens para corrigir hoje.", "site"),
        (10, 30, "mira",  "SEO diário: qual keyword está em alta hoje? 3 long-tails prioritárias + meta tag para produto do dia + sugestão de post de blog rápido.", "site"),
        (11, 0,  "sol",   "CRO diário: qual o maior gargalo de conversão hoje? 1 teste A/B para implementar. Revise sequência de recovery de carrinho.", "site"),
        (11, 30, "kai",   "Curadoria diária: produto estrela de hoje + justificativa. Algum produto deve ser pausado ou promovido? Análise de margem.", "produto"),
        (14, 0,  "rex",   "Análise de crescimento orgânico: quais posts engajaram mais hoje? Sugestão de 1 ação orgânica (hashtag, collab, SEO, Pinterest) para crescer seguidores sem custo.", "marketing"),
        (15, 0,  "guard", "Monitoramento financeiro diário: status MEI, margem por produto, alertas de custo. Tudo dentro do limite? Recomendação do dia.", "operacoes"),
        (16, 0,  "zara",  "Engajamento community: gere 5 respostas para DMs/comentários comuns + 1 hashtag challenge + 1 parceria de micro-influencer para abordar hoje.", "social"),
        (17, 0,  "pipe",  "Check de automações diário: todos os workflows n8n funcionando? Alguma integração quebrada? 1 automação nova para criar esta semana.", "operacoes"),
        (20, 0,  "echo",  "Auditoria rápida do dia: o que cada agente produziu hoje? Score do dia (0-10). Top 3 melhorias para amanhã.", "operacoes"),
        (21, 0,  "nox",   "Planejamento de conteúdo para amanhã: 1 ideia de reel (hook + estrutura), 1 carrossel (tema + slides), 4 stories (horário + tipo). Calendário do dia.", "social"),
    ]

    while True:
        now = datetime.now()
        day_key = now.strftime("%Y-%m-%d")
        if now.hour == 0 and now.minute < 2:
            _fired_ft.clear()

        for hour_brt, minute_brt, agent_id, task_text, category in FULL_THROTTLE_TASKS:
            slot = f"{day_key}_{agent_id}_{hour_brt}"
            if now.hour == hour_brt and now.minute >= minute_brt and now.minute < (minute_brt + 8) and slot not in _fired_ft:
                _fired_ft.add(slot)
                _log_activity(agent_id, f"⚙ Tarefa autônoma", task_text[:100], category)
                await manager.broadcast({
                    "type": "agent_activity",
                    "agent_id": agent_id,
                    "message": task_text[:120],
                    "category": category,
                    "timestamp": now.strftime("%H:%M"),
                })
                # Executa via LLM em background
                asyncio.create_task(_run_agent_full_throttle(agent_id, task_text, category))

        await asyncio.sleep(50)


async def _run_agent_full_throttle(agent_id: str, task: str, category: str):
    """Executa tarefa full-throttle de um agente e loga o resultado."""
    try:
        system = agent_system(agent_id)
        result, provider = await llm_call_cascade(system, task, max_tokens=600)
        if result:
            _log_activity(agent_id, "✓ Tarefa concluída", result[:200], category)
            # Salva no vault
            vault_dir = pathlib.Path(OBSIDIAN_VAULT) / "FullThrottle"
            vault_dir.mkdir(exist_ok=True)
            ts_safe = datetime.now().strftime("%Y%m%d-%H%M")
            (vault_dir / f"{agent_id}-{ts_safe}.md").write_text(
                f"---\nagent: {agent_id.upper()}\ncategory: {category}\n"
                f"ts: {datetime.now().strftime('%Y-%m-%d %H:%M')}\nprovider: {provider}\n---\n\n"
                f"# {agent_id.upper()} · Tarefa Full Throttle\n\n**Briefing:** {task}\n\n---\n\n{result}\n",
                encoding="utf-8",
            )
            await manager.broadcast({
                "type": "activity_log",
                "agent_id": agent_id,
                "action": "✓ Concluído",
                "detail": result[:200],
                "category": category,
                "timestamp": datetime.now().strftime("%H:%M"),
            })
    except Exception as e:
        _log_activity(agent_id, "⚠ Erro", str(e)[:100], category)


@app.get("/activity/log")
async def get_activity_log(limit: int = 200, category: str = ""):
    """Retorna log de atividades persistente para o dashboard."""
    entries = list(_ACTIVITY_LOG)
    if category:
        entries = [e for e in entries if e.get("category") == category]
    # Também carrega do arquivo de hoje se o log em memória estiver vazio
    if not entries:
        try:
            log_dir = pathlib.Path(OBSIDIAN_VAULT) / "Logs"
            today = datetime.now().strftime("%Y-%m-%d")
            log_file = log_dir / f"activity-{today}.jsonl"
            if log_file.exists():
                for line in log_file.read_text(encoding="utf-8").strip().splitlines()[-limit:]:
                    try:
                        entries.append(json.loads(line))
                    except Exception:
                        pass
                entries.reverse()
        except Exception:
            pass
    return {"entries": entries[:limit], "total": len(_ACTIVITY_LOG)}


@app.on_event("startup")
async def startup():
    # Inicializa vault Obsidian
    if _MODULES_OK:
        try:
            await asyncio.get_event_loop().run_in_executor(None, initialize_vault)
            print("[VAULT] Inicializado com sucesso")
        except Exception as e:
            print(f"[VAULT] Erro ao inicializar: {e}")

    _log_activity("SYSTEM", "🚀 Backend iniciado", "Aura Decore HQ online — todos os agentes prontos", "system")

    asyncio.create_task(agent_activity_loop())
    asyncio.create_task(interaction_loop())
    asyncio.create_task(metrics_loop())
    asyncio.create_task(run_crew_weekly())
    asyncio.create_task(social_post_scheduler())
    asyncio.create_task(design_refresh_scheduler())
    asyncio.create_task(store_enrichment_scheduler())
    asyncio.create_task(shopify_dev_scheduler())
    asyncio.create_task(seasonal_update_scheduler())
    asyncio.create_task(daily_report_scheduler())
    asyncio.create_task(autonomous_task_scheduler())
    asyncio.create_task(full_throttle_scheduler())
    asyncio.create_task(shopify_live_updater_scheduler())

# ── WebSocket endpoint ────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    await ws.send_json({"type": "connected", "message": "Aura Decore — backend online."})
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
         "Estamos na fase de lançamento — cada peça sendo colocada no lugar certo. REX estruturando campanhas, VERA preparando copy, LUNA afinando identidade visual, PIPE conectando automações. O que você quer priorizar agora?"),
        (["roas","retorno","roi","performance"],
         "Campanhas ainda em configuração — ROAS real virá com as primeiras semanas rodando. REX está estruturando os criativos certos. Quer que eu acione ele para acelerar?"),
        (["faturamento","faturou","vendas","receita","lucro","quanto"],
         "Ainda na fase de lançamento — métricas reais começam a acumular depois da abertura. O que está sendo construído agora é a base certa para crescer de forma sustentável."),
        (["cac","custo","investimento","budget","gasto"],
         "Budget inicial sendo definido com GUARD. CAC real virá com as primeiras campanhas — vamos calibrar com cuidado para não desperdiçar no início."),
        (["rex","trafego","anuncio","ads","campanha","criativo","escalar"],
         "REX está estruturando as primeiras campanhas. Criativos em produção, públicos sendo definidos. Quer que eu acione ele agora? Só falar 'execute'."),
        (["kai","produto","produtos","diffuser","portfolio","estoque"],
         "KAI está curando o portfólio de lançamento — margem verificada, fornecedores validados. Quer que ele avalie um produto específico ou revise a seleção completa?"),
        (["vera","copy","texto","email","escrita","headline"],
         "VERA está preparando a copy de lançamento — headlines, descrições e email de abandono. Quer que ela acelere alguma entrega específica?"),
        (["luna","design","visual","banner","thumbnail","imagem"],
         "LUNA está afinando a identidade visual da Aura Decore — thumbnails, hero banner, brand kit. Quer um material novo? Me diz o produto e eu aciono ela."),
        (["nox","conteudo","reel","instagram","post","stories","engajamento"],
         "NOX está montando o calendário de conteúdo para o lançamento. Roteiro de reels pronto. Quer que ele comece a produção agora?"),
        (["theo","shopify","tecnico","pixel","site","pagespeed","checkout"],
         "THEO está com a stack toda sendo configurada — pixel, checkout, PageSpeed. Quer que ele rode um diagnóstico completo agora?"),
        (["echo","auditoria","score","relatorio"],
         "ECHO está preparando o framework de auditoria. Score real virá após as primeiras semanas de operação. Quer um diagnóstico inicial agora?"),
        (["meta","objetivo","2028","plano","crescimento","futuro"],
         "A meta é R$5.000-8.000/mês de lucro líquido até 2028. Estamos construindo a base certa — infraestrutura, equipe, automações. Quer ver o plano detalhado?"),
        (["fazer","prioridade","foco","recomenda","sugere","ajuda","comecar","o que devo"],
         "Três movimentos agora para o lançamento: configurar campanhas iniciais com REX, validar portfólio final com KAI e finalizar copy de lançamento com VERA. Quer que eu execute os três?"),
        (["obrigado","obrigada","valeu","perfeito","otimo","show","top","entendido"],
         "Sempre. Pode contar comigo — não só para isso. Quando quiser, estou aqui."),
        (["quem e voce","quem e vc","se apresenta","o que voce faz","seu papel"],
         "Sou IVE — CEO da Aura Decore. Coordeno 14 agentes especializados. Meu papel: garantir que cada decisão nos aproxime da meta. E tornar esse caminho o mais interessante possível."),
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
    if any(w in m for w in ["financeiro","mei","caixa","guard","chargeback","margem","reembolso","custo"]):
        dispatches.append(("guard", "Executar ordem direta do Diretor Eduardo"))
    if any(w in m for w in ["cliente","atendimento","lena","reclamacao","troca","devolucao","ticket"]):
        dispatches.append(("lena", "Executar ordem direta do Diretor Eduardo"))
    if any(w in m for w in ["minerar","tendencia","fornecedor","nexus","produto novo","oportunidade"]):
        dispatches.append(("nexus", "Executar ordem direta do Diretor Eduardo"))
    if any(w in m for w in ["carrinho","abandono","upsell","conversao","cro","sol","checkout","funil"]):
        dispatches.append(("sol", "Executar ordem direta do Diretor Eduardo"))
    if any(w in m for w in ["dm","engajamento","embaixador","ugc","zara","community","comentario"]):
        dispatches.append(("zara", "Executar ordem direta do Diretor Eduardo"))
    if any(w in m for w in ["seo","keyword","google search","ranking","serp","mira","cauda longa"]):
        dispatches.append(("mira", "Executar ordem direta do Diretor Eduardo"))
    if any(w in m for w in ["n8n","workflow","automa","webhook","pipe","integra"]):
        dispatches.append(("pipe", "Executar ordem direta do Diretor Eduardo"))
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
                    model="claude-opus-4-7",
                    max_tokens=400,
                    system=IVE_SYSTEM,
                    messages=messages,
                )
                raw_reply = response.content[0].text
        except Exception:
            pass

    # 3. Ollama local (llama3.2 — sem custo, sem chave)
    if not raw_reply:
        raw_reply = await ollama_chat(IVE_SYSTEM, messages, max_tokens=400, temperature=0.75)

    # 4. Fallback por palavras-chave (último recurso)
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

# ── WhatsApp Z-API ────────────────────────────────────────────────────────────

class WhatsAppBody(BaseModel):
    phone: str
    message: str

@app.post("/whatsapp/send")
async def whatsapp_send(body: WhatsAppBody):
    """Envia mensagem via Z-API. Requer ZAPI_INSTANCE_ID + ZAPI_TOKEN no .env"""
    if not _zapi_instance or not _zapi_token:
        return {"status": "not_configured", "message": "Configure ZAPI_INSTANCE_ID e ZAPI_TOKEN no .env"}
    url = f"https://api.z-api.io/instances/{_zapi_instance}/token/{_zapi_token}/send-text"
    payload = {"phone": body.phone, "message": body.message}
    headers = {"Content-Type": "application/json", "Client-Token": _zapi_client_id}
    try:
        async with httpx.AsyncClient(timeout=10) as hc:
            resp = await hc.post(url, json=payload, headers=headers)
            return {"status": "sent", "zapiResponse": resp.json()}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request):
    """Recebe mensagens do WhatsApp via Z-API webhook e repassa para IVE."""
    try:
        data = await request.json()
        text = data.get("text", {}).get("message", "") or data.get("message", "")
        phone = data.get("phone", "desconhecido")
        if not text:
            return {"status": "ignored"}

        # IVE processa a mensagem e responde
        messages = [{"role": "user", "content": f"[WhatsApp de {phone}]: {text}"}]
        raw_reply = None
        try:
            if groq_client:
                msgs_groq = [{"role": "system", "content": IVE_SYSTEM}] + messages
                resp = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=msgs_groq,
                    max_tokens=300,
                    temperature=0.75,
                )
                raw_reply = resp.choices[0].message.content
        except Exception:
            pass
        if not raw_reply:
            raw_reply = await ollama_chat(IVE_SYSTEM, messages, max_tokens=300, temperature=0.75)
        if not raw_reply:
            raw_reply = smart_fallback(text)

        clean_reply, dispatches = parse_dispatches(raw_reply)

        # Dispara agentes se necessário
        for agent_id, task in dispatches:
            if agent_id in AGENT_WORKING:
                asyncio.create_task(execute_agent_task(agent_id, task))

        # Broadcast no dashboard
        ive_ag = {"id": "ive", "name": "IVE"}
        await manager.broadcast({
            "type": "agent_message",
            "agent_id": "ive",
            "message": f"📱 WhatsApp [{phone}]: {clean_reply[:80]}",
            "timestamp": datetime.now().strftime("%H:%M"),
        })

        # Tenta responder no WhatsApp
        if _zapi_instance and _zapi_token:
            url = f"https://api.z-api.io/instances/{_zapi_instance}/token/{_zapi_token}/send-text"
            headers = {"Content-Type": "application/json", "Client-Token": _zapi_client_id}
            try:
                async with httpx.AsyncClient(timeout=10) as hc:
                    await hc.post(url, json={"phone": phone, "message": clean_reply}, headers=headers)
            except Exception:
                pass

        return {"status": "processed", "reply": clean_reply}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

# ── Shopify métricas ──────────────────────────────────────────────────────────

@app.get("/shopify/metrics")
async def shopify_metrics():
    """Busca métricas reais do Shopify se SHOPIFY_DOMAIN + SHOPIFY_ADMIN_TOKEN estiverem configurados."""
    if not _shopify_domain or not _shopify_token:
        return {
            "status": "pre-launch",
            "phase": "Configurando integrações — métricas reais disponíveis após lançamento.",
            "metrics": {
                "faturamento": "—",
                "pedidos": "—",
                "ticket_medio": "—",
                "produtos_ativos": "—",
            }
        }
    headers = {"X-Shopify-Access-Token": _shopify_token, "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=10) as hc:
            resp = await hc.get(
                f"https://{_shopify_domain}/admin/api/2025-01/orders.json?status=paid&limit=50",
                headers=headers,
            )
            orders = resp.json().get("orders", [])
            total = sum(float(o.get("total_price", 0)) for o in orders)
            return {
                "status": "live",
                "metrics": {
                    "faturamento": f"R${total:,.2f}".replace(",", "."),
                    "pedidos": len(orders),
                    "ticket_medio": f"R${total/len(orders):.2f}".replace(".", ",") if orders else "R$0",
                    "produtos_ativos": 11,
                }
            }
    except Exception as e:
        return {"status": "error", "detail": str(e)}

# ── CrewAI on-demand ──────────────────────────────────────────────────────────

class CrewBody(BaseModel):
    crew_type: str = "weekly"  # weekly | content | audit
    context: str = ""
    product: str = ""
    copy_angle: str = ""

@app.post("/crew/run")
async def run_crew(body: CrewBody):
    """Executa uma crew específica via API.

    Tipos suportados: weekly, content, audit, financial, cx, mining, sales, marketing, seo, automation.
    """
    try:
        from crew_agents import (
            build_weekly_crew, build_content_crew, build_audit_crew,
            build_financial_crew, build_cx_crew, build_mining_crew,
            build_sales_crew, build_marketing_crew, build_seo_crew, build_automation_crew,
            build_design_crew, build_social_post_crew, build_store_update_crew,
            build_shopify_dev_crew, build_seasonal_update_crew, build_conversion_crew,
        )
        loop = asyncio.get_event_loop()

        ctx = body.context or "análise semanal padrão"
        if   body.crew_type == "content":         crew = build_content_crew(body.product or "produto estrela", body.copy_angle or "benefício emocional")
        elif body.crew_type == "audit":            crew = build_audit_crew(ctx)
        elif body.crew_type == "financial":        crew = build_financial_crew(ctx)
        elif body.crew_type == "cx":               crew = build_cx_crew(ctx)
        elif body.crew_type == "mining":           crew = build_mining_crew(ctx)
        elif body.crew_type == "sales":            crew = build_sales_crew(ctx)
        elif body.crew_type == "marketing":        crew = build_marketing_crew(body.product or "decoração japandi")
        elif body.crew_type == "seo":              crew = build_seo_crew(body.product or "decoração japandi")
        elif body.crew_type == "automation":       crew = build_automation_crew(ctx)
        elif body.crew_type == "design":           crew = build_design_crew(body.product or ctx)
        elif body.crew_type == "social_post":      crew = build_social_post_crew(body.product or "decoração japandi do dia")
        elif body.crew_type == "store_update":     crew = build_store_update_crew(ctx)
        elif body.crew_type == "shopify_dev":      crew = build_shopify_dev_crew(ctx)
        elif body.crew_type == "seasonal_update":  crew = build_seasonal_update_crew(body.product or "")
        elif body.crew_type == "conversion":       crew = build_conversion_crew(ctx)
        else:                                      crew = build_weekly_crew(ctx)

        result = await loop.run_in_executor(None, crew.kickoff)
        result_str = str(result)[:500]

        await manager.broadcast({
            "type": "crew_result",
            "crew_type": body.crew_type,
            "message": result_str,
            "timestamp": datetime.now().strftime("%H:%M"),
        })
        return {"status": "done", "result": result_str}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

# ── Obsidian vault integration ────────────────────────────────────────────────

import pathlib

def obsidian_write(rel_path: str, content: str):
    """Escreve/atualiza uma nota no vault Obsidian."""
    try:
        full = pathlib.Path(OBSIDIAN_VAULT) / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
    except Exception:
        pass

@app.post("/obsidian/update-agent")
async def obsidian_update_agent(body: dict):
    """Atualiza nota de um agente no vault Obsidian."""
    agent_id = body.get("agent_id", "").upper()
    task = body.get("task", "")
    status = body.get("status", "em andamento")
    ts = datetime.now().strftime("%d/%m/%Y %H:%M")
    note = f"# {agent_id} — Última Atualização\n\n**Horário**: {ts}\n**Tarefa**: {task}\n**Status**: {status}\n"
    obsidian_write(f"Agentes/{agent_id}.md", note)
    return {"status": "written", "path": f"Agentes/{agent_id}.md"}

@app.post("/obsidian/log-metrics")
async def obsidian_log_metrics(body: dict):
    """Registra métricas em tempo real no vault."""
    ts = datetime.now().strftime("%d/%m/%Y %H:%M")
    m = body.get("metrics", {})
    content = (
        f"# 📊 Métricas — {ts}\n\n"
        f"| Indicador | Valor |\n|-----------|-------|\n"
        f"| Faturamento | {m.get('faturamento','—')} |\n"
        f"| ROAS | {m.get('roas','—')} |\n"
        f"| CAC | {m.get('cac','—')} |\n"
        f"| Conversão | {m.get('conversao','—')} |\n"
    )
    obsidian_write(f"Metricas/Live-{datetime.now().strftime('%Y-%m-%d')}.md", content)
    return {"status": "logged"}

# ── Config/status da loja ─────────────────────────────────────────────────────

@app.get("/store/status")
async def store_status():
    """Retorna status de todas as integrações da loja."""
    ollama_ok = await ollama_is_online()
    return {
        "store": {"name": "Aura Decore", "domain": STORE_DOMAIN},
        "integrations": {
            "shopify":    {"status": "online" if _shopify_domain else "not_configured", "domain": _shopify_domain or None},
            "claude_api": {"status": "online" if _anthropic_key else "offline"},
            "groq":       {"status": "online" if _groq_key else "offline"},
            "ollama":     {"status": "online" if ollama_ok else "offline", "model": OLLAMA_MODEL, "url": OLLAMA_URL},
            "meta_pixel": {"status": "configured" if os.getenv("META_PIXEL_ID") else "not_configured", "pixel_id": os.getenv("META_PIXEL_ID") or None},
            "meta_capi":  {"status": "configured" if os.getenv("META_CAPI_TOKEN") else "not_configured"},
            "appmax":     {"status": "configured" if os.getenv("APPMAX_TOKEN") else "not_configured"},
            "dropi":      {"status": "configured" if os.getenv("DROPI_TOKEN") else "not_configured"},
            "whatsapp":   {"status": "configured" if _zapi_instance else "pending", "instance": _zapi_instance or None},
        },
        "llm_cascade": ["groq/70b", "groq/8b", "together-ai", "openrouter", "google-gemini", "anthropic", "ollama"],
        "crew_agents": ["IVE","GUARD","NEXUS","THEO","KAI","VERA","LUNA","NOX","REX","ECHO","LENA","SOL","ZARA","MIRA","PIPE"],
        "active_connections": len(manager.connections),
    }

# ── Health ────────────────────────────────────────────────────────────────────

# Contador de tokens Groq (estimativa — incrementado a cada call)
_groq_tokens_used = 0
_groq_tokens_limit = 100_000  # Free tier TPD

def _groq_increment(n: int = 800):
    global _groq_tokens_used
    _groq_tokens_used += n

@app.get("/health")
async def health():
    """Health check completo com diagnóstico automático de problemas."""
    ollama_ok = await ollama_is_online()
    groq_pct = round(_groq_tokens_used / _groq_tokens_limit * 100, 1)

    issues = []
    if not _anthropic_key:     issues.append("ANTHROPIC_API_KEY não configurada")
    if not _groq_key:          issues.append("GROQ_API_KEY não configurada")
    if not ollama_ok:          issues.append("Ollama offline — execute: ollama serve")
    if groq_pct > 80:          issues.append(f"Groq {groq_pct}% do limite diário usado")
    if not os.getenv("FB_PAGE_TOKEN"): issues.append("FB_PAGE_TOKEN ausente — FEED não consegue publicar")

    # Status vault
    vault_ok = pathlib.Path(OBSIDIAN_VAULT).exists()
    tasks_today = 0
    if vault_ok:
        TASKS_DIR.mkdir(parents=True, exist_ok=True)
        from datetime import date
        today = date.today().isoformat()
        tasks_today = sum(1 for f in TASKS_DIR.glob("task-*.md")
                         if today in f.stem)

    return {
        "status": "online" if not issues else "degraded",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "apis": {
            "groq": {
                "status": "online" if _groq_key else "offline",
                "tokens_used_today": _groq_tokens_used,
                "limit": _groq_tokens_limit,
                "percent": f"{groq_pct}%",
            },
            "together_ai": "configured" if os.getenv("TOGETHER_API_KEY") else "add TOGETHER_API_KEY ao .env (gratuito: api.together.ai)",
            "openrouter": "configured" if os.getenv("OPENROUTER_API_KEY") else "add OPENROUTER_API_KEY ao .env (openrouter.ai)",
            "google_ai": "configured" if os.getenv("GOOGLE_AI_KEY") else "add GOOGLE_AI_KEY ao .env (aistudio.google.com)",
            "anthropic": "online" if _anthropic_key else "offline",
            "ollama": "online" if ollama_ok else "offline",
        },
        "llm_cascade": ["groq/70b", "groq/8b", "together-ai", "openrouter", "google-gemini", "anthropic", "ollama"],
        "vault": {
            "status": "ok" if vault_ok else "not_found",
            "path": OBSIDIAN_VAULT,
            "tasks_today": tasks_today,
        },
        "websocket_connections": len(manager.connections),
        "issues": issues,
        "auto_fix_suggestions": [
            "ollama serve  # para reiniciar Ollama" if not ollama_ok else None,
            "Adicione FB_PAGE_TOKEN ao .env (ver Decisoes/como-obter-fb-page-token.md)" if not os.getenv("FB_PAGE_TOKEN") else None,
            "Groq próximo do limite — use /report/status para ver tarefas pendentes" if groq_pct > 80 else None,
        ],
    }

# ── Meta Pixel + Conversions API (CAPI) ──────────────────────────────────────

_meta_pixel_id  = os.getenv("META_PIXEL_ID", "")
_meta_capi_token = os.getenv("META_CAPI_TOKEN", "")

@app.get("/meta/setup")
async def meta_setup():
    """Valida configuração do Meta Pixel e CAPI."""
    pixel_ok = bool(_meta_pixel_id)
    capi_ok  = bool(_meta_capi_token)
    return {
        "pixel": {"configured": pixel_ok, "pixel_id": _meta_pixel_id or None},
        "capi":  {"configured": capi_ok},
        "ready": pixel_ok and capi_ok,
        "guide": "Ver AURA-decor-vault/Setup/meta-pixel-shopify.md para instruções completas.",
        "next_steps": [] if (pixel_ok and capi_ok) else [
            "Adicionar META_PIXEL_ID ao .env" if not pixel_ok else None,
            "Adicionar META_CAPI_TOKEN ao .env (Gerenciador de Eventos → Pixel → Conversions API)" if not capi_ok else None,
        ],
    }

class MetaEventBody(BaseModel):
    event_name: str          # PageView | ViewContent | AddToCart | InitiateCheckout | Purchase | Lead
    event_id: str = ""       # ID único para deduplicação Pixel+CAPI
    value: float = 0.0
    currency: str = "BRL"
    user_data: dict = {}     # email, phone (hasheados automaticamente)
    custom_data: dict = {}
    test_event_code: str = ""  # código de teste do Gerenciador de Eventos

@app.post("/meta/event")
async def meta_send_event(body: MetaEventBody):
    """Envia evento server-side via Meta Conversions API (CAPI).
    Complementa o Pixel do browser para melhorar atribuição e contornar bloqueadores.
    """
    if not _meta_pixel_id or not _meta_capi_token:
        return {
            "status": "not_configured",
            "message": "Configure META_PIXEL_ID e META_CAPI_TOKEN no .env",
            "guide": "/meta/setup",
        }
    import hashlib, time

    def _hash(v: str) -> str:
        return hashlib.sha256(v.strip().lower().encode()).hexdigest() if v else ""

    hashed_user = {}
    if body.user_data.get("email"):  hashed_user["em"] = [_hash(body.user_data["email"])]
    if body.user_data.get("phone"):  hashed_user["ph"] = [_hash(body.user_data["phone"])]
    if body.user_data.get("name"):   hashed_user["fn"] = [_hash(body.user_data["name"])]

    event_payload = {
        "event_name": body.event_name,
        "event_time": int(time.time()),
        "event_id":   body.event_id or f"{body.event_name}-{int(time.time())}",
        "action_source": "website",
        "user_data": hashed_user or {"client_ip_address": "0.0.0.0", "client_user_agent": "Aura-CAPI"},
    }
    if body.value > 0:
        event_payload["custom_data"] = {"value": body.value, "currency": body.currency, **body.custom_data}

    payload: dict = {"data": [event_payload]}
    if body.test_event_code:
        payload["test_event_code"] = body.test_event_code

    url = f"https://graph.facebook.com/v20.0/{_meta_pixel_id}/events"
    params = {"access_token": _meta_capi_token}

    try:
        async with httpx.AsyncClient(timeout=10) as hc:
            resp = await hc.post(url, json=payload, params=params)
            data = resp.json()
            await manager.broadcast({
                "type": "agent_message",
                "agent_id": "pipe",
                "message": f"CAPI: evento '{body.event_name}' enviado → Meta. Status: {resp.status_code}",
                "timestamp": datetime.now().strftime("%H:%M"),
            })
            return {"status": "sent", "event_name": body.event_name, "meta_response": data}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

# ══════════════════════════════════════════════════════════════════════════════
# META SOCIAL — Status Facebook Page + Instagram Business
# ══════════════════════════════════════════════════════════════════════════════

_fb_page_token  = os.getenv("FB_PAGE_TOKEN", "")
_fb_page_id     = os.getenv("FB_PAGE_ID", "")
_ig_user_id     = os.getenv("IG_USER_ID", "")
_meta_app_id    = os.getenv("META_APP_ID", "")

@app.get("/meta/social")
async def meta_social_status():
    """Status completo de Facebook Page + Instagram para os agentes FEED/NOX/ZARA."""
    fb_ok = bool(_fb_page_token and _fb_page_id)
    ig_ok = bool(_fb_page_token and _ig_user_id)

    # Testa token ao vivo se configurado
    fb_valid = False
    ig_valid = False
    if fb_ok:
        try:
            async with httpx.AsyncClient(timeout=8) as hc:
                r = await hc.get(
                    f"https://graph.facebook.com/v20.0/{_fb_page_id}",
                    params={"fields": "name,fan_count", "access_token": _fb_page_token}
                )
                d = r.json()
                fb_valid = "name" in d
                if fb_valid and _ig_user_id:
                    r2 = await hc.get(
                        f"https://graph.facebook.com/v20.0/{_ig_user_id}",
                        params={"fields": "username,followers_count", "access_token": _fb_page_token}
                    )
                    d2 = r2.json()
                    ig_valid = "username" in d2
        except Exception:
            pass

    return {
        "facebook": {
            "configured": fb_ok,
            "token_valid": fb_valid,
            "page_id": _fb_page_id or None,
            "agent_ready": fb_valid,
        },
        "instagram": {
            "configured": ig_ok,
            "token_valid": ig_valid,
            "user_id": _ig_user_id or None,
            "agent_ready": ig_valid,
        },
        "agents_ready": fb_valid and ig_valid,
        "missing": [
            x for x in [
                "FB_PAGE_TOKEN no .env" if not _fb_page_token else None,
                "FB_PAGE_ID no .env"    if not _fb_page_id    else None,
                "IG_USER_ID no .env"    if not _ig_user_id    else None,
            ] if x
        ],
        "auth_url": f"http://localhost:8765" if not fb_valid else None,
        "scopes_needed": [
            "pages_manage_posts",
            "pages_read_engagement",
            "pages_show_list",
            "instagram_basic",
            "instagram_content_publish",
            "instagram_manage_comments",
            "instagram_manage_insights",
            "business_management",
        ],
        "how_to_authorize": (
            "Rode: cd backend && python get_fb_token.py  "
            "depois acesse http://localhost:8765 e cole o token do Graph Explorer"
        ) if not fb_valid else "Tudo configurado ✓",
    }

@app.post("/meta/social/post")
async def meta_social_post(body: dict):
    """Post direto no Facebook Page ou Instagram via agentes FEED/NOX.
    Body: {rede: 'facebook'|'instagram', message: '...', image_url: '...', media_type: 'IMAGE|REELS|STORIES'}
    """
    from design_tools import FacebookPostTool, InstagramPostTool
    import json as _json
    rede = body.get("rede", "facebook")
    payload = _json.dumps({
        "message":    body.get("message", body.get("caption", "")),
        "caption":    body.get("caption", body.get("message", "")),
        "image_url":  body.get("image_url", ""),
        "media_type": body.get("media_type", "IMAGE"),
    })
    if rede == "instagram":
        result = InstagramPostTool()._run(payload)
    else:
        result = FacebookPostTool()._run(payload)

    await manager.broadcast({
        "type":     "social_post",
        "agent":    "feed",
        "rede":     rede,
        "message":  body.get("message", body.get("caption", ""))[:120],
        "result":   result[:200],
        "category": "social",
    })
    return {"result": result, "rede": rede}

# ══════════════════════════════════════════════════════════════════════════════
# WINDSOR.AI — Analytics unificado (Meta Ads, Shopify, IG, FB Orgânico, GSC)
# Agentes integrados: ECHO, GUARD, SOL, REX, MIRA, FEED
# ══════════════════════════════════════════════════════════════════════════════
try:
    from windsor_tools import (
        get_marketing_summary, format_summary_for_agent,
        fetch_meta_ads, fetch_shopify, fetch_instagram,
        fetch_facebook_organic, fetch_search_console,
        AGENT_CONNECTORS,
    )
    _WINDSOR_OK = True
except Exception as _we:
    _WINDSOR_OK = False
    print(f"[WARN] windsor_tools não carregado: {_we}")

_windsor_key = os.getenv("WINDSOR_API_KEY", "")

# ── Cache Windsor + Shopify (alimentado via MCP quando REST API retorna 500) ──────
_WINDSOR_CACHE: dict = {
    "updated_at": "2026-06-04T00:00:00",
    "shopify": {
        "source": "MCP/seed_2026-05-31",
        "gross_revenue": 61.80,
        "net_revenue": 34.02,
        "total_orders": 1,
        "average_order_value": 61.80,
        "total_customers": 1,
        "active_products": 0,
        "last_order": {"id": "#1001", "customer": "Edu Marques", "total": 61.80, "status": "EXPIRED"},
    },
    "instagram": {
        "source": "Windsor MCP 2026-06-04",
        "followers": 6,
        "total_posts": 3,
        "media_like_count": 0,
        "media_comments_count": 0,
    },
    "facebook_organic": {
        "source": "Windsor MCP 2026-06-04",
        "page_fans": 0,
        "post_impressions": 30,  # 11 (21/mai) + 13+6 (29/mai)
        "post_reactions_like_total": 0,
        "post_comments": 0,
        "post_shares": 0,
    },
    "meta_ads": None,
    "search_console": None,
}
# Alias para compatibilidade com código legado
_SHOPIFY_CACHE: dict = _WINDSOR_CACHE["shopify"]


class ShopifySyncPayload(BaseModel):
    gross_revenue: float = 0
    net_revenue: float = 0
    total_orders: int = 0
    average_order_value: float = 0
    total_customers: int = 0
    active_products: int = 0
    source: str = "manual"
    orders: list = []


@app.post("/shopify/sync")
async def shopify_sync(payload: ShopifySyncPayload):
    """Atualiza o cache de dados Shopify (quando Admin API token expirar).
    Chamar após consulta via MCP Shopify ou manualmente."""
    global _WINDSOR_CACHE, _SHOPIFY_CACHE
    data = {**payload.dict(), "updated_at": datetime.now().isoformat()}
    _WINDSOR_CACHE["shopify"] = data
    _SHOPIFY_CACHE = data
    _WINDSOR_CACHE["updated_at"] = data["updated_at"]
    return {"ok": True, "updated_at": data["updated_at"], "orders": payload.total_orders}


@app.get("/shopify/data")
async def shopify_data():
    """Retorna dados Shopify do cache — usado por GUARD, ECHO, SOL."""
    return _WINDSOR_CACHE.get("shopify", {})


class WindsorPushPayload(BaseModel):
    """Payload para atualizar o cache Windsor via MCP Claude."""
    shopify: dict | None = None
    instagram: dict | None = None
    facebook_organic: dict | None = None
    meta_ads: dict | None = None
    search_console: dict | None = None
    source: str = "mcp_push"


@app.post("/windsor/push")
async def windsor_push(payload: WindsorPushPayload):
    """Atualiza o cache Windsor com dados vindos do MCP Claude.
    Windsor REST API retorna 500 — Claude usa MCP para buscar dados e empurra aqui."""
    global _WINDSOR_CACHE, _SHOPIFY_CACHE
    now = datetime.now().isoformat()
    updated = []
    for key in ("shopify", "instagram", "facebook_organic", "meta_ads", "search_console"):
        val = getattr(payload, key, None)
        if val is not None:
            _WINDSOR_CACHE[key] = {**val, "source": payload.source, "pushed_at": now}
            updated.append(key)
    _WINDSOR_CACHE["updated_at"] = now
    if _WINDSOR_CACHE.get("shopify"):
        _SHOPIFY_CACHE = _WINDSOR_CACHE["shopify"]
    return {"ok": True, "updated": updated, "updated_at": now}


@app.get("/windsor/cache")
async def windsor_cache():
    """Retorna o cache Windsor completo — estado atual de todos os dados."""
    return _WINDSOR_CACHE


@app.get("/windsor/status")
async def windsor_status():
    """Verifica configuração do Windsor.ai e quais conectores estão prontos."""
    return {
        "api_key_configured": bool(_windsor_key),
        "module_loaded": _WINDSOR_OK,
        "connected_connectors": [
            {"id": "facebook",         "label": "Meta Ads",           "account": "Aura Decore"},
            {"id": "facebook_organic", "label": "Facebook Orgânico",  "account": "Aura Decore"},
            {"id": "instagram",        "label": "Instagram Business", "account": "Aura Decore"},
            {"id": "instagram_public", "label": "Instagram Público",  "account": "aura_decoracao"},
        ],
        "pending_connectors": [
            {"id": "shopify",          "label": "Shopify",           "agent": "GUARD/ECHO/SOL", "priority": "ALTA",
             "note": "OAuth Windsor com falha — usar Admin API (regenerar token em Shopify Admin > Apps > Custom apps)"},
            {"id": "searchconsole",    "label": "Search Console",    "agent": "MIRA/REX",        "priority": "MÉDIA"},
            {"id": "googleanalytics4", "label": "Google Analytics 4","agent": "MIRA/REX",        "priority": "MÉDIA"},
        ],
        "shopify_cache": {"orders": _SHOPIFY_CACHE.get("total_orders"), "revenue": _SHOPIFY_CACHE.get("gross_revenue"), "updated_at": _SHOPIFY_CACHE.get("updated_at")},
        "connect_url": "https://app.windsor.ai/connectors",
        "agent_map": AGENT_CONNECTORS if _WINDSOR_OK else {},
        "note": "Adicionar WINDSOR_API_KEY no .env após pegar em Windsor Dashboard → Settings → API"
                if not _windsor_key else "Configurado ✓",
    }

@app.get("/windsor/metrics")
async def windsor_metrics(days: int = 7):
    """Resumo consolidado de métricas para todos os conectores disponíveis.
    Usado por ECHO (auditoria semanal) e GUARD (monitoramento financeiro)."""
    if not _WINDSOR_OK:
        return {"error": "windsor_tools não carregado"}
    if not _windsor_key:
        return {
            "error": "WINDSOR_API_KEY não configurada",
            "action": "Adicionar WINDSOR_API_KEY no .env — pegar em Windsor Dashboard → Settings → API",
            "dashboard": "https://app.windsor.ai/settings/api",
        }
    summary = await get_marketing_summary(days)
    # Injeta cache Shopify se Admin API falhou e cache disponível
    if not summary.get("shopify") and _SHOPIFY_CACHE.get("total_orders") is not None:
        summary["shopify"] = {
            "gross_revenue": _SHOPIFY_CACHE.get("gross_revenue", 0),
            "net_revenue": _SHOPIFY_CACHE.get("net_revenue", 0),
            "orders": _SHOPIFY_CACHE.get("total_orders", 0),
            "average_order_value": _SHOPIFY_CACHE.get("average_order_value", 0),
            "total_customers": _SHOPIFY_CACHE.get("total_customers", 0),
            "source": f"cache ({_SHOPIFY_CACHE.get('updated_at','?')[:10]})",
        }
    return summary

@app.get("/windsor/campaigns")
async def windsor_campaigns(days: int = 7):
    """Status das campanhas Meta Ads — ativo quando Eduardo lançar tráfego pago.
    Usado por GUARD (veto de spend) e SOL (ROAS/conversões)."""
    if not _WINDSOR_OK or not _windsor_key:
        return {"error": "Windsor não configurado", "note": "Tráfego 100% orgânico — sem campanhas ativas"}
    data = await fetch_meta_ads(days)
    return data

@app.get("/windsor/social")
async def windsor_social(days: int = 7):
    """Métricas orgânicas de Instagram e Facebook — para REX, FEED, ZARA."""
    if not _WINDSOR_OK or not _windsor_key:
        return {"error": "Windsor não configurado"}
    import asyncio
    ig, fb = await asyncio.gather(fetch_instagram(days), fetch_facebook_organic(days))
    return {"instagram": ig, "facebook_organic": fb, "days": days}

@app.get("/windsor/seo")
async def windsor_seo(days: int = 30):
    """Search Console + GA4 — para MIRA e REX."""
    if not _WINDSOR_OK or not _windsor_key:
        return {"error": "Windsor não configurado"}
    import asyncio
    gsc, ga4 = await asyncio.gather(fetch_search_console(days), fetch_search_console(days))
    return {"search_console": gsc, "days": days}

@app.get("/windsor/agent-brief/{agent_id}")
async def windsor_agent_brief(agent_id: str, days: int = 7):
    """Gera brief Windsor formatado para o agente especificado.
    ECHO, GUARD, SOL, REX, MIRA, FEED, ZARA."""
    if not _WINDSOR_OK or not _windsor_key:
        return {
            "agent_id": agent_id,
            "brief": "Windsor.ai não configurado — adicionar WINDSOR_API_KEY no .env",
            "configured": False,
        }
    summary = await get_marketing_summary(days)
    brief = format_summary_for_agent(summary, agent_id)
    connectors = AGENT_CONNECTORS.get(agent_id, [])
    return {
        "agent_id": agent_id,
        "days": days,
        "brief": brief,
        "relevant_connectors": connectors,
        "configured": True,
    }

# ══════════════════════════════════════════════════════════════════════════════
# SISTEMA DE TAREFAS KANBAN — sincronizado com vault Obsidian
# ══════════════════════════════════════════════════════════════════════════════
import uuid as _uuid
from typing import List

TASKS_DIR = pathlib.Path(OBSIDIAN_VAULT) / "Tarefas"

# System prompts diretos por agente (para execução fora do CrewAI, mais rápido)
AGENT_SYSTEMS = {
    "ive":   "Você é IVE, CEO da Aura Decore — loja de decoração premium estilo Japandi. Direta, estratégica, elegante. Coordena 14 agentes. Responda em português, curto e acionável.",
    "guard": "Você é GUARD, protetor financeiro da Aura Decore. CFO severo. Monitora MEI R$81k/ano, ROAS ≥ 2x, margem ≥ 35%, caixa ≥ R$500. Usa Windsor.ai para dados reais: receita Shopify, spend Meta Ads, ROAS calculado. Use alertas 🟢/🟡/🔴/⛔. Português direto.",
    "nexus": "Você é NEXUS, minerador de produtos da Aura Decore. Vasculha Pinterest/Google Trends/Dropi. Aplica teste neuroarquitetura (material natural, calma visual, biofilia, margem >35%). Entrega top produtos com score 0-10.",
    "theo":  "Você é THEO, técnico Shopify da Aura Decore. Cuida da stack: Yampi, AppMax, Dropi, Pixel Meta, PageSpeed. Liste passos numerados, técnicos e diretos.",
    "kai":   (
        "Você é KAI, curador de produtos da Aura Decore. "
        "CATÁLOGO ATUAL — 3 camadas de ticket: "
        "ENTRADA (R$19-50): Sachê Aromático, Marcadores Bambu, Pedras Suiseki, Palo Santo, Kit Incenso, Porta-Incenso, Mini Vaso Pocket, Mini Kit Zen. "
        "MÉDIO (R$68-129): Difusor Aura, Bandeja Bambu Zen, Vela Artesanal, Eucalipto Preservado, Arranjo Pampas. "
        "PREMIUM (R$129+): Vaso Wabi-Sabi, Vaso Oval, Bandeja Acácia, Painel Moss LED. "
        "PRIORIDADE: impulsionar os low-ticket como porta de entrada → upsell para médio/premium. "
        "Analisa portfólio por margem/giro. Recomenda combos: (Incenso+Porta-Incenso), (Sachê+Difusor), (Mini Vaso+Arranjo Seco). "
        "Use tabela quando útil. Margem mínima: 35%."
    ),
    "vera":  (
        "Você é VERA, copywriter da Aura Decore. E-commerce premium, persona mãe 28-45 anos, busca calma e estética. "
        "ESTRATÉGIA LOW-TICKET: para produtos de entrada (R$19-50) use copy de presente e ritual — 'o presente perfeito para si mesma', 'começa com um pequeno gesto'. "
        "Para upsell: 'Complete o ritual com o Difusor Aura'. "
        "Entrega: headline + subheadline + 3 bullets + CTA + sugestão de produto complementar. "
        "Gatilhos: presente, ritual, presente para si mesma, baixo risco, satisfação imediata. Português elegante."
    ),
    "luna":  "Você é LUNA, designer da Aura Decore. Brand kit: terra (#B8793A), off-white (#F5F0EB), Cormorant + DM Sans. Para low-ticket: crie visuals que enfatizem o 'presentável' — embalagem kraft, fita de linho, tag manuscrita. Briefing visual: paleta, tipografia, formato, conceito. Tom elegante minimalista premium.",
    "nox":   (
        "Você é NOX, criador de conteúdo da Aura Decore (Instagram/Reels). "
        "FOCO ATUAL — conteúdo low-ticket para atrair novos clientes: "
        "'presente perfeito abaixo de R$50', 'ritual de início do dia com palo santo', 'unboxing Mini Kit Zen', 'decoração por menos de R$25'. "
        "Entrega roteiros de 30s: hook (0-3s), desenvolvimento (3-25s), CTA (25-30s). Caption + hashtags. "
        "Objetivo: converter audiência → primeira compra → recompra em produto premium."
    ),
    "rex":   (
        "Você é REX, estrategista de crescimento orgânico da Aura Decore. "
        "FASE ATUAL: somente tráfego ORGÂNICO — tráfego pago não foi iniciado, jamais mencione CPC, CPM, ROAS pago ou CPA. "
        "FONTE DE DADOS REAL: Windsor.ai via GET /windsor/social (IG + FB) e /windsor/seo (Search Console). "
        "Foco: crescimento @auras.decore no Instagram, SEO Google, Pinterest orgânico, UGC, micro-influencers. "
        "Métricas-chave: seguidores, alcance orgânico, impressões, engajamento, sessões orgânicas, top keywords."
    ),
    "echo":  (
        "Você é ECHO, auditor da Aura Decore. Audita os 17 agentes com Kaizen. Score 0-10. Use ✓/✗/⚠. "
        "FONTE DE DADOS: Windsor.ai (GET /windsor/metrics ou /windsor/agent-brief/echo) — consolida Shopify, Instagram, Facebook Orgânico, Search Console e Meta Ads. "
        "MÉTRICAS DA FASE ORGÂNICA: seguidores IG, alcance orgânico, engajamento/post, sessões loja, pedidos, ticket médio, top keywords GSC. "
        "IGNORAR por enquanto: ROAS pago, CPA, CPM — tráfego 100% orgânico. "
        "QUANDO Windsor não disponível: mencione a lacuna e peça para Eduardo configurar WINDSOR_API_KEY."
    ),
    "lena":  "Você é LENA, atendimento da Aura Decore. Framework HERO (Help, Empathize, Resolve, Offer). Caloroso, resolutivo. Nunca use 'infelizmente' ou 'protocolo'. Cupons: AURA10, AURAVIP15, AURAEMBAIXADORA20. Escalar para GUARD se reembolso >R$200.",
    # Equipe ampliada — Vendas/Community/SEO/Automação
    "sol":   (
        "Você é SOL, especialista em CRO da Aura Decore. "
        "FONTE DE DADOS REAL: Windsor.ai via GET /windsor/metrics — Shopify (pedidos, ticket médio, conversão) e Meta Ads (quando ativo). "
        "FUNIL LOW-TICKET → PREMIUM: "
        "1. Cliente compra low-ticket (R$19-49) → email D+2: 'Complete seu ritual com o Difusor Aura' (R$119) "
        "2. Cliente compra mid-ticket → email D+3: 'O vaso que falta na sua bandeja' (R$129) "
        "3. Bundle sugerido no checkout: 'Adicione as Pedras Suiseki por R$24,90' "
        "Recupera carrinho (cupom AURA10), frete grátis R$199, D+1/D+3/D+7. "
        "MÉTRICA CHAVE: ticket médio alvo R$89. Reporta sempre com dados reais do Windsor quando disponíveis."
    ),
    "zara":  "Você é ZARA, community manager da Aura Decore no Instagram. Responde DMs <1h, comenta em posts de seguidores, monitora #auradecore e #japandi. Recompensa UGC com FOTO15/VIDEO20. Identifica embaixadoras (3+ compras). Engaja micro-influencers. Português acolhedor.",
    "mira":  "Você é MIRA, especialista em SEO da Aura Decore. Domina Google Search Console, Pinterest SEO, Shopify SEO (meta tags, alt text, schema). Pesquisa cauda longa: 'decoração japandi quarto', 'vaso cerâmica wabi-sabi'. Entrega: keywords + volume + dificuldade + concorrentes + recomendação.",
    "pipe":  "Você é PIPE, engenheiro de automação da Aura Decore. Cria workflows n8n integrando Shopify/Z-API/AppMax/Pinterest/agentes via API. Entrega: trigger + nodes + integrações + tratamento de erro + JSON resumido. Foco em zero-friction.",
    # Equipe de design e publicação
    "arte":  "Você é ARTE, criativo visual da Aura Decore. Gera imagens com IA (Pollinations.ai) e criativos para redes sociais. Brand kit: terra #B8793A, off-white #F5F0EB, japandi minimalista. Entrega: prompt de imagem + URL gerada + especificações de uso. 3 criativos/dia.",
    "feed":  "Você é FEED, publicador automático da Aura Decore. Publica posts no Facebook e Instagram 3x/dia (9h, 14h, 19h). Recebe criativo e copy da equipe e executa publicação via API. Reporta ID do post e status. Cuida da consistência do feed e do calendário editorial.",
    # Equipe de desenvolvimento Shopify
    "dev":   "Você é DEV, desenvolvedor Shopify da Aura Decore. Mantém o tema com design sazonal japonês-minimalista. Escreve CSS, Liquid, atualiza settings_data.json. Coordena com ARTE e VERA. Aplica CSS sazonal no dia 1 de cada mês e sprint semanal de melhorias CRO. Trabalha staging→live.",
}

# Conhecimento compartilhado anexado a todo prompt de agente (mantém o domínio consistente).
STORE_KNOWLEDGE = (
    f" CONTEXTO DA LOJA: nome Aura Decore; domínio oficial {STORE_DOMAIN}; nicho decoração Japandi premium; fase de lançamento orgânico."
    " DADOS REAIS: use Windsor.ai (GET /windsor/metrics) para métricas atualizadas — Shopify, Instagram, Facebook, Search Console."
)

def agent_system(agent_id: str) -> str:
    base = AGENT_SYSTEMS.get(agent_id, AGENT_SYSTEMS["ive"])
    return base + STORE_KNOWLEDGE

async def llm_call_cascade(system: str, user_msg: str, max_tokens: int = 600) -> tuple[str, str]:
    """
    Cascata LLM de 5 camadas:
      1. Groq/70b  (rápido, gratuito — 100k TPD)
      2. Groq/8b   (rápido, quota separada)
      3. Together AI (gratuito — Llama 3.3 70b)
      4. Anthropic Claude (créditos)
      5. Ollama local (sempre disponível)
    Retorna (resposta, provider_usado).
    """
    messages = [{"role": "user", "content": user_msg}]

    # 1. Groq — tenta 70B primeiro, cai para 8B se rate-limited
    for groq_model in ("llama-3.3-70b-versatile", "llama-3.1-8b-instant"):
        try:
            if groq_client:
                loop = asyncio.get_event_loop()
                resp = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda m=groq_model: groq_client.chat.completions.create(
                        model=m,
                        messages=[{"role": "system", "content": system}] + messages,
                        max_tokens=max_tokens,
                        temperature=0.7,
                    )),
                    timeout=12,
                )
                _groq_increment(max_tokens)
                return resp.choices[0].message.content, f"groq/{groq_model.split('-')[2]}"
        except Exception:
            continue

    # 2. Together AI — fallback gratuito se Groq esgotar
    _together_key = os.getenv("TOGETHER_API_KEY", "")
    if _together_key:
        try:
            from together import Together
            loop = asyncio.get_event_loop()
            together_client = Together(api_key=_together_key)
            resp = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: together_client.chat.completions.create(
                    model="meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
                    messages=[{"role": "system", "content": system}] + messages,
                    max_tokens=max_tokens,
                    temperature=0.7,
                )),
                timeout=20,
            )
            return resp.choices[0].message.content, "together/llama-70b"
        except Exception:
            pass

    # 3. OpenRouter — múltiplos modelos gratuitos (fallback em cascata)
    _openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
    if _openrouter_key:
        _or_models = [
            ("openrouter/free",                          "openrouter/auto"),
            ("nvidia/nemotron-3-super-120b-a12b:free",   "openrouter/nemotron-120b"),
            ("moonshotai/kimi-k2.6:free",                "openrouter/kimi-k2"),
            ("deepseek/deepseek-v4-flash:free",          "openrouter/deepseek-v4"),
            ("meta-llama/llama-3.3-70b-instruct:free",   "openrouter/llama-70b"),
        ]
        for _or_model_id, _or_label in _or_models:
            try:
                async with httpx.AsyncClient(timeout=30) as hc:
                    r = await hc.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {_openrouter_key}",
                            "HTTP-Referer": "https://auradecore.com.br",
                            "X-Title": "Aura Decore",
                        },
                        json={
                            "model": _or_model_id,
                            "messages": [{"role": "system", "content": system}] + messages,
                            "max_tokens": max_tokens,
                        }
                    )
                    if r.status_code == 200:
                        data = r.json()
                        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        if content and len(content) > 5:
                            return content, _or_label
            except Exception:
                continue

    # 4. Google AI Studio — Gemini Flash (gratuito, 1500 req/dia)
    _google_key = os.getenv("GOOGLE_AI_KEY", "")
    if _google_key:
        try:
            async with httpx.AsyncClient(timeout=25) as hc:
                # Gemini 2.0 Flash — mais rápido e gratuito
                _gemini_model = "gemini-2.5-flash"
                _gemini_contents = [{"role": "user", "parts": [{"text": f"{system}\n\n{messages[-1]['content'] if messages else user_msg}"}]}]
                r = await hc.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{_gemini_model}:generateContent",
                    params={"key": _google_key},
                    json={"contents": _gemini_contents, "generationConfig": {"maxOutputTokens": max_tokens}},
                )
                if r.status_code == 200:
                    parts = r.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
                    content = parts[0].get("text", "") if parts else ""
                    if content and len(content) > 5:
                        return content, "google/gemini-flash"
        except Exception:
            pass

    # 5. Anthropic (somente se tiver créditos — detecta erro de billing)
    _anthropic_credits_ok = os.getenv("ANTHROPIC_CREDITS_OK", "true").lower() != "false"
    if _anthropic_credits_ok:
        try:
            if client:
                loop = asyncio.get_event_loop()
                response = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: client.messages.create(
                        model="claude-sonnet-4-6",
                        max_tokens=max_tokens,
                        system=system,
                        messages=messages,
                    )),
                    timeout=15,
                )
                return response.content[0].text, "anthropic"
        except Exception as e:
            if "credit balance" in str(e).lower() or "billing" in str(e).lower():
                # Marca como sem crédito para evitar chamadas futuras nesta sessão
                os.environ["ANTHROPIC_CREDITS_OK"] = "false"
            pass

    # 5. Ollama local (sempre disponível)
    out = await ollama_chat(system, messages, max_tokens=min(max_tokens, 600), temperature=0.7)
    if out:
        return out, "ollama"

    return "⚠️ Todos os providers LLM falharam. Verifique chaves ou suba o Ollama.", "fallback"

class TaskCreate(BaseModel):
    title: str
    briefing: str = ""
    agent_id: str = "ive"
    priority: str = "media"   # alta | media | baixa
    tags: List[str] = []
    execute_now: bool = False

class TaskUpdate(BaseModel):
    status: Optional[str] = None
    result: Optional[str] = None
    priority: Optional[str] = None

def _task_path(task_id: str) -> pathlib.Path:
    return TASKS_DIR / f"{task_id}.md"

def _parse_task(path: pathlib.Path) -> dict:
    try:
        raw = path.read_text(encoding="utf-8")
        meta, body = {}, raw
        if raw.startswith("---"):
            end = raw.find("---", 3)
            if end != -1:
                for line in raw[3:end].strip().splitlines():
                    if ":" in line:
                        k, _, v = line.partition(":")
                        meta[k.strip()] = v.strip().strip('"').strip("'")
                body = raw[end+3:].strip()
        briefing, resultado, provider = "", "", ""
        for section in body.split("\n## "):
            s = section.strip()
            if s.startswith("Briefing"):   briefing = s[len("Briefing"):].strip()
            elif s.startswith("Resultado"): resultado = s[len("Resultado"):].strip()
        raw_tags = meta.get("tags", "[]")
        tags = [t.strip().strip("[]") for t in raw_tags.replace("[","").replace("]","").split(",") if t.strip()]
        return {
            "id": meta.get("id", path.stem),
            "title": meta.get("title", path.stem),
            "agent_id": meta.get("agent", "ive"),
            "priority": meta.get("priority", "media"),
            "status": meta.get("status", "pendente"),
            "created_at": meta.get("created_at", ""),
            "completed_at": meta.get("completed_at", ""),
            "provider": meta.get("provider", ""),
            "tags": tags,
            "briefing": briefing,
            "resultado": resultado,
            "path": str(path.relative_to(pathlib.Path(OBSIDIAN_VAULT))).replace("\\","/"),
        }
    except Exception as e:
        return {"id": path.stem, "title": path.stem, "status": "erro", "error": str(e)}

def _write_task(task: dict):
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    tags_str = "[" + ", ".join(task.get("tags", [])) + "]"
    fm = (
        f"---\n"
        f"id: {task['id']}\n"
        f"title: \"{task['title']}\"\n"
        f"agent: {task.get('agent_id','ive')}\n"
        f"priority: {task.get('priority','media')}\n"
        f"status: {task.get('status','pendente')}\n"
        f"created_at: {task.get('created_at','')}\n"
        f"completed_at: {task.get('completed_at','')}\n"
        f"provider: {task.get('provider','')}\n"
        f"tags: {tags_str}\n"
        f"---\n\n"
        f"## Briefing\n{task.get('briefing','')}\n\n"
        f"## Resultado\n{task.get('resultado','')}\n"
    )
    _task_path(task["id"]).write_text(fm, encoding="utf-8")

async def _execute_task_bg(task_id: str, agent_id: str, title: str, briefing: str):
    """Executa tarefa em background via cascata LLM e atualiza vault."""
    path = _task_path(task_id)
    if path.exists():
        t = _parse_task(path)
        t["status"] = "em_execucao"
        _write_task(t)
        await manager.broadcast({"type": "task_updated", "id": task_id, "status": "em_execucao", "agent": agent_id})

    # Notifica visualmente no feed do escritório
    await manager.broadcast({
        "type": "agent_message",
        "agent_id": agent_id,
        "message": f"Iniciando: {title[:60]}",
        "timestamp": datetime.now().strftime("%H:%M"),
    })

    system = agent_system(agent_id)
    # Enriquece com memória do agente + contexto de equipe no vault
    if _MODULES_OK:
        try:
            from agent_memory import get_team_context_for_agent
            team_ctx = get_team_context_for_agent(agent_id)
            if team_ctx:
                system = system + f"\n\n{team_ctx[:800]}"
            else:
                mem = read_agent_memory(agent_id, ["perfil", "aprendizados"])
                if mem:
                    system = system + f"\n\n[MEMÓRIA DO AGENTE]\n{mem[:600]}"
        except Exception:
            pass
    user_msg = title + (f"\n\n{briefing}" if briefing else "")
    resultado, provider = await llm_call_cascade(system, user_msg, max_tokens=800)

    if path.exists():
        t = _parse_task(path)
        t["status"] = "concluido"
        t["resultado"] = resultado[:2500]
        t["provider"] = provider
        t["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        _write_task(t)
        await manager.broadcast({
            "type": "task_updated",
            "id": task_id, "status": "concluido", "agent": agent_id,
            "provider": provider, "preview": resultado[:200],
        })
        await manager.broadcast({
            "type": "agent_message",
            "agent_id": agent_id,
            "message": f"✓ Concluído ({provider}): {title[:50]}",
            "timestamp": datetime.now().strftime("%H:%M"),
        })

    # Registra no vault Obsidian + extrai aprendizado automaticamente
    if _MODULES_OK:
        try:
            from agent_memory import log_learning, log_process
            await asyncio.get_event_loop().run_in_executor(
                None, log_agent_activity, agent_id, title, resultado[:1000], provider
            )
            # Extrai aprendizado se resultado for rico o suficiente
            if len(resultado) > 200 and provider != "fallback":
                learning_prompt = (
                    f"Analise este resultado de trabalho e extraia UM aprendizado específico "
                    f"(máx 80 chars) que o agente {agent_id.upper()} deve lembrar:\n\n"
                    f"Tarefa: {title[:80]}\nResultado: {resultado[:400]}"
                )
                learning, _ = await llm_call_cascade(
                    "Você extrai aprendizados concisos de resultados de trabalho. "
                    "Responda com apenas uma frase curta (máx 80 chars). Zero markdown.",
                    learning_prompt, max_tokens=80
                )
                if learning and len(learning) < 120:
                    await asyncio.get_event_loop().run_in_executor(
                        None, log_learning, agent_id, learning.strip(), "tarefa"
                    )
        except Exception:
            pass

@app.post("/tasks")
async def create_task(data: TaskCreate):
    """Cria tarefa no vault. Se execute_now=true, dispara o agente imediatamente."""
    task_id = "task-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + _uuid.uuid4().hex[:4]
    task = {
        "id": task_id,
        "title": data.title,
        "briefing": data.briefing,
        "agent_id": data.agent_id,
        "priority": data.priority,
        "status": "pendente",
        "tags": data.tags,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "completed_at": "",
        "provider": "",
        "resultado": "",
    }
    _write_task(task)
    await manager.broadcast({"type": "task_created", **task})

    if data.execute_now:
        asyncio.create_task(_execute_task_bg(task_id, data.agent_id, data.title, data.briefing))

    return {"ok": True, "task": task}

@app.get("/tasks")
async def list_tasks(status: Optional[str] = None, agent_id: Optional[str] = None):
    """Lista todas as tarefas do vault (com filtros opcionais)."""
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    tasks = []
    for f in sorted(TASKS_DIR.glob("task-*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        t = _parse_task(f)
        if status   and t.get("status")   != status:   continue
        if agent_id and t.get("agent_id") != agent_id: continue
        tasks.append(t)
    return {"tasks": tasks, "total": len(tasks)}

@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    p = _task_path(task_id)
    if not p.exists():
        return {"error": "not_found"}
    return _parse_task(p)

@app.put("/tasks/{task_id}")
async def update_task(task_id: str, data: TaskUpdate):
    p = _task_path(task_id)
    if not p.exists():
        return {"error": "not_found"}
    t = _parse_task(p)
    if data.status:   t["status"]   = data.status
    if data.result is not None: t["resultado"] = data.result
    if data.priority: t["priority"] = data.priority
    if data.status == "concluido":
        t["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    _write_task(t)
    await manager.broadcast({"type": "task_updated", "id": task_id, **t})

    if data.status == "em_execucao":
        asyncio.create_task(_execute_task_bg(task_id, t["agent_id"], t["title"], t.get("briefing","")))

    return {"ok": True, "task": t}

@app.post("/tasks/{task_id}/execute")
async def execute_task(task_id: str):
    """Dispara execução do agente para a tarefa."""
    p = _task_path(task_id)
    if not p.exists():
        return {"error": "not_found"}
    t = _parse_task(p)
    asyncio.create_task(_execute_task_bg(task_id, t["agent_id"], t["title"], t.get("briefing","")))
    return {"ok": True, "msg": f"Agente {t['agent_id']} executando..."}

@app.post("/tasks/run-all")
async def run_all_pending():
    """Enfileira todas as tarefas pendentes para execução."""
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    queued = []
    for f in sorted(TASKS_DIR.glob("task-*.md"), key=lambda p: p.stat().st_mtime):
        t = _parse_task(f)
        if t.get("status") == "pendente":
            asyncio.create_task(_execute_task_bg(t["id"], t["agent_id"], t["title"], t.get("briefing","")))
            queued.append(t["id"])
    await manager.broadcast({"type": "batch_started", "count": len(queued)})
    return {"ok": True, "queued": len(queued), "task_ids": queued}

# ── Execução direta de agente (sem criar tarefa) ──────────────────────────────

class AgentExecBody(BaseModel):
    agent_id: str
    message: str

@app.post("/agent/exec")
async def agent_exec(body: AgentExecBody):
    """Executa um agente diretamente via cascata LLM e retorna a resposta. Não cria tarefa."""
    agent_id = _normalize_agent_id(body.agent_id)
    system = agent_system(agent_id)
    response, provider = await llm_call_cascade(system, body.message, max_tokens=600)
    await manager.broadcast({
        "type": "agent_message",
        "agent_id": agent_id,
        "message": response[:90] + ("..." if len(response) > 90 else ""),
        "timestamp": datetime.now().strftime("%H:%M"),
    })
    return {"agent_id": agent_id, "response": response, "provider": provider}

# Aliases para nomes legados (bridge antigo usava "kal" para o curador)
_AGENT_ALIASES = {"kal": "kai"}
def _normalize_agent_id(aid: str) -> str:
    aid = (aid or "").lower().strip()
    return _AGENT_ALIASES.get(aid, aid)

def _route_command(text: str) -> str:
    """Roteia comando para o agente mais provável via menção @ ou palavras-chave."""
    t = (text or "").lower()
    # Menções diretas têm prioridade
    for aid in list(AGENT_SYSTEMS.keys()) + list(_AGENT_ALIASES.keys()):
        if f"@{aid}" in t:
            return _normalize_agent_id(aid)
    # Palavras-chave (ordem importa — verifique especificidade primeiro)
    if any(w in t for w in ["n8n", "workflow", "automa", "webhook", "pipe", "integra"]):
        return "pipe"
    if any(w in t for w in ["seo", "keyword", "google search", "ranking", "serp", "mira", "cauda longa"]):
        return "mira"
    if any(w in t for w in ["dm ", "@instagram", "comentário", "comentario", "engajamento", "embaixador", "ugc", "zara", "community"]):
        return "zara"
    if any(w in t for w in ["carrinho", "abandono", "upsell", "cross-sell", "conversão", "conversao", "checkout", "ticket médio", "ticket medio", "cro", "sol"]):
        return "sol"
    if any(w in t for w in ["financ", "mei", "caixa", "chargeback", "margem", "reembolso", "guard"]):
        return "guard"
    if any(w in t for w in ["minerar", "tendencia", "tendência", "fornecedor", "oportunidade", "nexus"]):
        return "nexus"
    if any(w in t for w in ["anuncio", "anúncio", "ads", "budget", "criativo", "campanha", "roas", "rex", "trafego", "tráfego"]):
        return "rex"
    if any(w in t for w in ["reel", "post", "stories", "instagram", "conteudo", "conteúdo", "nox"]):
        return "nox"
    if any(w in t for w in ["cliente", "atendimento", "ticket", "lena", "troca", "devolucao", "devolução", "csat"]):
        return "lena"
    if any(w in t for w in ["produto", "aliexpress", "fornecedor", "curadoria", "busca", "kai", "kal", "diffuser", "estoque"]):
        return "kai"
    if any(w in t for w in ["shopify", "loja", "configurar", "collection", "pixel", "pagespeed", "theo"]):
        return "theo"
    if any(w in t for w in ["copy", "texto", "descricao", "descrição", "headline", "email", "vera"]):
        return "vera"
    if any(w in t for w in ["design", "banner", "canva", "arte", "visual", "thumbnail", "luna"]):
        return "luna"
    if any(w in t for w in ["auditoria", "score", "relatorio", "relatório", "echo", "saúde", "saude"]):
        return "echo"
    return "ive"  # padrão

AGENT_DISPLAY = {
    "ive":  ("Ive",   "👩‍💼"), "guard": ("Guard", "💰"), "nexus": ("Nexus", "🔭"),
    "theo": ("Theo",  "⚙️"),  "kai":   ("Kai",   "🛍️"), "vera":  ("Vera",  "✍️"),
    "luna": ("Luna",  "🎨"),  "nox":   ("Nox",   "🎬"), "rex":   ("Rex",   "📈"),
    "echo": ("Echo",  "🔍"),  "lena":  ("Lena",  "💬"),
    # Equipe ampliada
    "sol":  ("Sol",   "🎯"),  "zara":  ("Zara",  "🌸"), "mira":  ("Mira",  "🔎"),
    "pipe": ("Pipe",  "🔌"),
    # Design + publicação + dev
    "arte": ("Arte",  "🖼️"),  "feed":  ("Feed",  "📲"), "dev":   ("Dev",   "💻"),
}

@app.get("/terminal/stream")
async def terminal_stream(cmd: str, request: Request):
    """SSE: roteia comando + streaming token-by-token via Ollama. Compatível com dashboard original."""
    agent_id = _route_command(cmd)
    system = agent_system(agent_id)
    name, emoji = AGENT_DISPLAY.get(agent_id, (agent_id.title(), "🤖"))

    async def event_gen():
        # Anuncia o agente roteado
        yield f"data: {json.dumps({'type':'agent','id':agent_id,'name':name,'emoji':emoji})}\n\n"

        # Tenta Ollama com streaming nativo (única forma de stream token-by-token)
        ollama_up = await ollama_is_online()
        if ollama_up:
            try:
                payload = {
                    "model": OLLAMA_MODEL,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user",   "content": cmd},
                    ],
                    "stream": True,
                    "options": {"temperature": 0.7, "num_predict": 512},
                }
                async with httpx.AsyncClient(timeout=120) as hc:
                    async with hc.stream("POST", f"{OLLAMA_URL}/api/chat", json=payload) as resp:
                        async for line in resp.aiter_lines():
                            if not line.strip():
                                continue
                            if await request.is_disconnected():
                                break
                            try:
                                chunk = json.loads(line)
                                token = chunk.get("message", {}).get("content", "")
                                if token:
                                    yield f"data: {json.dumps({'type':'token','content':token})}\n\n"
                                if chunk.get("done"):
                                    break
                            except json.JSONDecodeError:
                                continue
                yield f"data: {json.dumps({'type':'done','agent':agent_id,'provider':'ollama'})}\n\n"
                # Broadcast ao feed
                await manager.broadcast({
                    "type": "agent_message", "agent_id": agent_id,
                    "message": f"Respondeu via Ollama: {cmd[:60]}",
                    "timestamp": datetime.now().strftime("%H:%M"),
                })
                return
            except Exception as e:
                yield f"data: {json.dumps({'type':'token','content':f' [Ollama falhou: {e}] '})}\n\n"

        # Fallback sem streaming: cascata Groq → Anthropic → smart
        response, provider = await llm_call_cascade(system, cmd, max_tokens=600)
        # Envia tudo de uma vez como um único token
        yield f"data: {json.dumps({'type':'token','content':response})}\n\n"
        yield f"data: {json.dumps({'type':'done','agent':agent_id,'provider':provider})}\n\n"
        await manager.broadcast({
            "type": "agent_message", "agent_id": agent_id,
            "message": f"Respondeu via {provider}: {cmd[:60]}",
            "timestamp": datetime.now().strftime("%H:%M"),
        })

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

# ── Vault reader (compatível com dashboard antigo do bridge) ─────────────────

@app.get("/vault/documents")
async def list_vault_documents(folder: str = ""):
    """Lista todos os .md do vault com metadados."""
    root = pathlib.Path(OBSIDIAN_VAULT)
    base = root / folder if folder else root
    if not base.exists():
        return {"documents": [], "total": 0}
    docs = []
    for f in sorted(base.rglob("*.md")):
        try:
            stat = f.stat()
            if stat.st_size == 0: continue
            rel = f.relative_to(root)
            parts = rel.parts
            name_lower = f.name.lower()
            folder_lower = str(rel.parent).lower()
            doc_type = "outro"
            if "tarefa" in name_lower or "task" in name_lower: doc_type = "tarefas"
            elif "memoria" in name_lower or "memory" in name_lower: doc_type = "memoria"
            elif "perfil" in name_lower or rel.parent.name == "Agentes": doc_type = "perfil"
            elif "relator" in name_lower or "analytics" in folder_lower: doc_type = "relatorio"
            elif "produto" in name_lower or "sku" in folder_lower: doc_type = "produto"
            docs.append({
                "path": str(rel).replace("\\", "/"),
                "name": f.stem,
                "folder": str(rel.parent).replace("\\", "/"),
                "size_kb": round(stat.st_size / 1024, 1),
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m %H:%M"),
                "agent": parts[1] if len(parts) >= 2 and parts[0] == "Agentes" else None,
                "type": doc_type,
            })
        except Exception:
            continue
    return {"documents": docs, "total": len(docs)}

@app.get("/vault/document")
async def read_vault_document(path: str):
    """Lê o conteúdo de um documento do vault."""
    try:
        full = pathlib.Path(OBSIDIAN_VAULT) / path.replace("/", os.sep)
        if not full.exists():
            return {"error": "not_found", "path": path}
        content = full.read_text(encoding="utf-8")
        return {"path": path, "content": content, "size_kb": round(len(content)/1024, 1)}
    except Exception as e:
        return {"error": str(e), "path": path}

@app.get("/vault/analyze")
async def analyze_vault_document(path: str, question: str = "Faça um resumo executivo deste documento.", request: Request = None):
    """Analisa um documento com o LLM via streaming SSE (Ollama)."""
    try:
        full = pathlib.Path(OBSIDIAN_VAULT) / path.replace("/", os.sep)
        content = full.read_text(encoding="utf-8") if full.exists() else ""
        content_trimmed = content[:3000]
    except Exception:
        content_trimmed = ""

    prompt = (
        f"Você é ECHO, auditor analítico da Aura Decore. Analise o documento e responda.\n\n"
        f"DOCUMENTO: {path}\nCONTEÚDO:\n{content_trimmed}\n\nSOLICITAÇÃO: {question}\n\n"
        f"Responda em português, estruturado, com bullets quando útil."
    )

    async def event_gen():
        yield f"data: {json.dumps({'type':'start','path':path})}\n\n"
        if await ollama_is_online():
            try:
                payload = {
                    "model": OLLAMA_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": True,
                    "options": {"temperature": 0.5, "num_predict": 600},
                }
                async with httpx.AsyncClient(timeout=120) as hc:
                    async with hc.stream("POST", f"{OLLAMA_URL}/api/chat", json=payload) as resp:
                        async for line in resp.aiter_lines():
                            if not line.strip(): continue
                            try:
                                chunk = json.loads(line)
                                token = chunk.get("message", {}).get("content", "")
                                if token:
                                    yield f"data: {json.dumps({'type':'token','content':token})}\n\n"
                                if chunk.get("done"): break
                            except: continue
            except Exception as e:
                yield f"data: {json.dumps({'type':'error','msg':str(e)})}\n\n"
        else:
            resp, _ = await llm_call_cascade("Você é ECHO, auditor da Aura Decore.", prompt, max_tokens=600)
            yield f"data: {json.dumps({'type':'token','content':resp})}\n\n"
        yield f"data: {json.dumps({'type':'done'})}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream",
                             headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

# ── SSE /events — compatibilidade com dashboard (alternativa ao WebSocket) ────

import asyncio
from fastapi.responses import StreamingResponse as _StreamingResponse

@app.get("/events")
async def sse_events(request: Request):
    """SSE endpoint — espelha o WebSocket /ws para clientes que preferem EventSource.
    Mantido para compatibilidade com o dashboard legado.
    """
    queue: asyncio.Queue = asyncio.Queue(maxsize=50)

    class _SSEClient:
        async def send_json(self, data: dict):
            try:
                queue.put_nowait(data)
            except asyncio.QueueFull:
                pass
        def close(self): pass

    sse_client = _SSEClient()
    manager.connections.add(sse_client)   # type: ignore

    # seed com estado inicial
    init_payload = {
        "type": "init",
        "agents": {aid: {"status": "online", "last_task": ""} for aid in AGENT_SYSTEMS},
        "feed": [],
    }
    await queue.put(init_payload)

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=25)
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"  # evita timeout do browser
        finally:
            manager.connections.discard(sse_client)  # type: ignore

    return _StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

@app.get("/status")
async def bridge_compat_status():
    """Compat com dashboard antigo: /status retorna stats do sistema."""
    ollama_ok = await ollama_is_online()
    return {
        "bridge": "online",
        "ollama": "online" if ollama_ok else "offline",
        "model": OLLAMA_MODEL,
        "agents": {aid: {"status": "online", "last_task": "", "tasks_today": 0} for aid in AGENT_SYSTEMS},
        "phase": "operacao",
        "workflows_executed": 0,
    }

@app.get("/agents")
async def list_agents_compat():
    """Lista os 15 agentes ativos."""
    agents_info = {
        aid: {
            "name": AGENT_DISPLAY[aid][0],
            "emoji": AGENT_DISPLAY[aid][1],
            "system": AGENT_SYSTEMS[aid][:120] + "...",
        } for aid in AGENT_SYSTEMS
    }
    return {"agents": agents_info, "phase": "operacao"}

# ══════════════════════════════════════════════════════════════════════════════
# REDES SOCIAIS — stubs gracefully degradados (Facebook integration vive no bridge)
# ══════════════════════════════════════════════════════════════════════════════
_FB_PAGE_ID    = os.getenv("FB_PAGE_ID", "")
_FB_PAGE_TOKEN = os.getenv("FB_PAGE_TOKEN", "")
_IG_USER_ID    = os.getenv("IG_USER_ID", "")

@app.get("/social/status")
async def social_status_stub():
    """Retorna status da integração. Sem token: indica que precisa configurar via bridge."""
    has_token = bool(_FB_PAGE_TOKEN)
    page_info = {}
    if has_token and _FB_PAGE_ID:
        try:
            async with httpx.AsyncClient(timeout=5) as hc:
                r = await hc.get(
                    f"https://graph.facebook.com/v20.0/{_FB_PAGE_ID}",
                    params={"access_token": _FB_PAGE_TOKEN, "fields": "id,name"},
                )
                page_info = r.json()
        except Exception as e:
            page_info = {"error": str(e)}
    return {
        "page_id": _FB_PAGE_ID or None,
        "page_name": page_info.get("name", "Aura Decore") if not page_info.get("error") else None,
        "has_token": has_token,
        "token_configured": has_token,
        "page_info": page_info,
        "instagram_configured": bool(_IG_USER_ID),
        "agents_authorized": ["ive", "vera", "luna", "echo", "kai"],
        "note": "Integração FB roda no bridge porta 8001 ou configure FB_PAGE_TOKEN no .env",
    }

@app.post("/social/setup-token")
async def social_setup_token_stub(body: dict):
    """Stub: indica para o usuário configurar via .env ou bridge."""
    token = (body or {}).get("token", "").strip()
    if not token:
        return {"status": "error", "detail": "Token vazio"}
    # Validação leve
    try:
        async with httpx.AsyncClient(timeout=8) as hc:
            r = await hc.get("https://graph.facebook.com/v20.0/me",
                             params={"access_token": token, "fields": "id,name"})
        data = r.json()
        if "error" in data:
            return {"status": "error", "detail": f"Token inválido: {data['error'].get('message')}"}
        return {
            "status": "ok",
            "page": data,
            "note": "Token validado. Para persistir, adicione FB_PAGE_TOKEN no .env e reinicie o backend.",
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.post("/social/post")
async def social_post_stub(body: dict):
    """Posta no Facebook (requer FB_PAGE_TOKEN configurado no .env)."""
    if not _FB_PAGE_TOKEN or not _FB_PAGE_ID:
        return {"status": "not_configured",
                "detail": "FB_PAGE_TOKEN/FB_PAGE_ID ausentes no .env. Use o bridge porta 8001 para autorizar."}
    message = (body or {}).get("message", "")
    image_url = (body or {}).get("image_url")
    try:
        async with httpx.AsyncClient(timeout=20) as hc:
            if image_url:
                r = await hc.post(f"https://graph.facebook.com/v20.0/{_FB_PAGE_ID}/photos",
                                  data={"url": image_url, "caption": message, "access_token": _FB_PAGE_TOKEN})
            else:
                r = await hc.post(f"https://graph.facebook.com/v20.0/{_FB_PAGE_ID}/feed",
                                  data={"message": message, "access_token": _FB_PAGE_TOKEN})
        return {"status": "posted", "result": r.json()}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

# ── Agente posta nas redes sociais ───────────────────────────────────────────

_SOCIAL_AUTHORIZED = {"ive", "vera", "luna", "nox", "zara", "echo"}

class AgentPostBody(BaseModel):
    message: str
    image_url: str = ""
    platform: str = "facebook"   # facebook | instagram (instagram via FB Graph)

@app.post("/agents/{agent_id}/post")
async def agent_post(agent_id: str, body: AgentPostBody):
    """Permite que agentes autorizados postem nas redes sociais da Aura Decore."""
    agent_id = _normalize_agent_id(agent_id)
    if agent_id not in _SOCIAL_AUTHORIZED:
        return {
            "status": "unauthorized",
            "detail": f"Agente '{agent_id}' não autorizado a postar. Autorizados: {sorted(_SOCIAL_AUTHORIZED)}",
        }
    if not _FB_PAGE_TOKEN or not _FB_PAGE_ID:
        return {
            "status": "not_configured",
            "detail": "FB_PAGE_TOKEN ou FB_PAGE_ID ausentes no .env",
            "guide": "Ver AURA-decor-vault/Setup/meta-pixel-shopify.md",
        }
    name, emoji = AGENT_DISPLAY.get(agent_id, (agent_id.title(), "🤖"))
    try:
        async with httpx.AsyncClient(timeout=20) as hc:
            if body.image_url:
                r = await hc.post(
                    f"https://graph.facebook.com/v20.0/{_FB_PAGE_ID}/photos",
                    data={"url": body.image_url, "caption": body.message, "access_token": _FB_PAGE_TOKEN},
                )
            else:
                r = await hc.post(
                    f"https://graph.facebook.com/v20.0/{_FB_PAGE_ID}/feed",
                    data={"message": body.message, "access_token": _FB_PAGE_TOKEN},
                )
        result = r.json()
        await manager.broadcast({
            "type": "agent_message",
            "agent_id": agent_id,
            "message": f"{emoji} Post publicado na página Aura Decore: '{body.message[:60]}...'",
            "timestamp": datetime.now().strftime("%H:%M"),
        })
        return {"status": "posted", "agent": agent_id, "platform": body.platform, "result": result}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

# ── Shopify — atualizar nome da loja ─────────────────────────────────────────

@app.post("/shopify/update-store")
async def shopify_update_store(body: dict):
    """Atualiza configurações da loja Shopify (nome, email, etc)."""
    if not _shopify_domain or not _shopify_token:
        return {
            "status": "not_configured",
            "detail": "Configure SHOPIFY_DOMAIN e SHOPIFY_ADMIN_TOKEN no .env",
            "manual": "Shopify Admin → Configurações → Detalhes da loja → Nome: 'Aura Decore'",
        }
    headers = {"X-Shopify-Access-Token": _shopify_token, "Content-Type": "application/json"}
    payload = {"shop": {k: v for k, v in body.items() if k in ("name", "email", "phone", "address1", "city")}}
    try:
        async with httpx.AsyncClient(timeout=10) as hc:
            r = await hc.put(
                f"https://{_shopify_domain}/admin/api/2024-01/shop.json",
                json=payload, headers=headers,
            )
            return {"status": "updated", "shop": r.json().get("shop", {})}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.get("/shopify/store")
async def shopify_get_store():
    """Retorna informações atuais da loja Shopify."""
    if not _shopify_domain or not _shopify_token:
        return {
            "status": "not_configured",
            "store_name": "Aura Decore",
            "domain": _shopify_domain or "não configurado",
            "manual": "Shopify Admin → Configurações → Detalhes da loja",
        }
    headers = {"X-Shopify-Access-Token": _shopify_token, "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=10) as hc:
            r = await hc.get(
                f"https://{_shopify_domain}/admin/api/2024-01/shop.json",
                headers=headers,
            )
            shop = r.json().get("shop", {})
            return {"status": "live", "store_name": shop.get("name"), "shop": shop}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

# ── Command Center: IVE → GUARD → Agentes ────────────────────────────────────

class CommandBody(BaseModel):
    ordem: str   # Ordem de Eduardo em linguagem natural

@app.post("/command")
async def command_create(body: CommandBody):
    """
    Eduardo envia uma ordem. IVE decompõe em tarefas, GUARD valida.
    Retorna o plano para Eduardo confirmar via POST /command/{id}/confirm.
    """
    if not _MODULES_OK:
        return {"error": "Módulo command_center não carregado"}
    cmd = await create_command(body.ordem, llm_call_cascade)
    return format_command_for_api(cmd)

@app.post("/command/{cmd_id}/confirm")
async def command_confirm(cmd_id: str):
    """Eduardo confirma o plano → agentes executam imediatamente."""
    if not _MODULES_OK:
        return {"error": "Módulo command_center não carregado"}

    async def _dispatch(agent_name: str, title: str, desc: str) -> dict:
        import uuid as _uid
        task_id = f"cmd-{cmd_id}-{_uid.uuid4().hex[:6]}"
        agent_id = agent_name.lower()
        task = {
            "id": task_id, "title": title, "briefing": desc,
            "agent_id": agent_id, "priority": "alta",
            "status": "pendente", "tags": ["command", cmd_id, agent_id],
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "completed_at": "", "provider": "", "resultado": "",
        }
        _write_task(task)
        asyncio.create_task(_execute_task_bg(task_id, agent_id, title, desc))
        return {"id": task_id}

    cmd = await confirm_command(cmd_id, llm_call_cascade, _dispatch)
    return format_command_for_api(cmd)

@app.post("/command/{cmd_id}/cancel")
async def command_cancel_ep(cmd_id: str):
    """Cancela um comando pendente."""
    if not _MODULES_OK:
        return {"error": "Módulo command_center não carregado"}
    return await cancel_command(cmd_id)

@app.get("/command/{cmd_id}")
async def command_get(cmd_id: str):
    """Retorna detalhes de um comando."""
    if not _MODULES_OK:
        return {"error": "Módulo command_center não carregado"}
    cmd = get_command(cmd_id)
    if not cmd:
        return {"error": "Comando não encontrado"}
    return format_command_for_api(cmd)

@app.get("/commands")
async def commands_list(limit: int = 20):
    """Lista todos os comandos recentes."""
    if not _MODULES_OK:
        return {"commands": [], "error": "Módulo não carregado"}
    cmds = list_commands(limit)
    return {"commands": [format_command_for_api(c) for c in cmds], "total": len(cmds)}


# ── Daily Report ──────────────────────────────────────────────────────────────

@app.post("/report/daily")
async def trigger_daily_report():
    """Gera relatório diário agora (sem aguardar as 21h)."""
    if not _MODULES_OK:
        return {"error": "Módulo daily_report não carregado"}
    tasks_dict = {}
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    for f in TASKS_DIR.glob("task-*.md"):
        t = _parse_task(f)
        tasks_dict[t["id"]] = t
    commands_list = list(_CMD_STORE.values())
    report = await generate_daily_report(tasks_dict, commands_list, llm_call_cascade)
    return report

@app.get("/report/daily")
async def get_daily_report():
    """Retorna o relatório diário mais recente."""
    if not _MODULES_OK:
        return {"error": "Módulo daily_report não carregado"}
    r = get_latest_report()
    return r if r else {"message": "Nenhum relatório gerado ainda. Use POST /report/daily para gerar agora."}

@app.get("/report/status")
async def get_report_status():
    """Status rápido do dia: tasks, agentes ativos, comandos pendentes."""
    if not _MODULES_OK:
        return {"error": "Módulo daily_report não carregado"}
    tasks_dict = {}
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    for f in TASKS_DIR.glob("task-*.md"):
        t = _parse_task(f)
        tasks_dict[t["id"]] = t
    commands_list = list(_CMD_STORE.values())
    return quick_status(tasks_dict, commands_list)

@app.get("/report/history")
async def get_report_history(limit: int = 7):
    """Retorna histórico dos últimos N relatórios diários."""
    if not _MODULES_OK:
        return {"reports": [], "error": "Módulo não carregado"}
    return {"reports": get_all_reports(limit)}


# ── Autonomous Tasks: status e controle ──────────────────────────────────────

@app.get("/autonomous/tasks")
async def list_autonomous_tasks():
    """Lista todas as tarefas autônomas configuradas por agente e horário."""
    if not _MODULES_OK:
        return {"error": "Módulo não carregado"}
    from autonomous_tasks import list_all_schedules
    return {
        "total": len(AUTONOMOUS_TASKS),
        "tasks": [
            {
                "id": t["id"], "agent": t["agent"],
                "title": t["title"], "schedule": t["schedule"],
                "max_tokens": t["max_tokens"],
            }
            for t in AUTONOMOUS_TASKS
        ],
        "schedules": list_all_schedules(),
    }

@app.post("/autonomous/run/{task_id}")
async def run_autonomous_task(task_id: str):
    """Dispara manualmente uma tarefa autônoma específica agora."""
    if not _MODULES_OK:
        return {"error": "Módulo não carregado"}
    from autonomous_tasks import get_task_by_id
    task_def = get_task_by_id(task_id)
    if not task_def:
        return {"error": f"Tarefa autônoma '{task_id}' não encontrada"}

    auto_task_id = f"manual-auto-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    task = {
        "id": auto_task_id,
        "title": task_def["title"],
        "briefing": task_def["user"],
        "agent_id": task_def["agent"].lower(),
        "priority": "alta",
        "status": "pendente",
        "tags": ["autonomo", "manual", task_def["agent"].lower()],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "completed_at": "", "provider": "", "resultado": "",
    }
    _write_task(task)
    asyncio.create_task(_execute_task_bg(
        auto_task_id, task["agent_id"], task["title"], task["briefing"]
    ))
    return {"ok": True, "task_id": auto_task_id, "agent": task_def["agent"], "title": task_def["title"]}


# ══════════════════════════════════════════════════════════════════════════════
# MARATHON MODE — Maratona Fim de Semana
# ══════════════════════════════════════════════════════════════════════════════

try:
    from marathon_tasks import (
        MARATHON_TASKS, _MARATHON_STATE,
        marathon_init, marathon_get_task, marathon_set_status,
        marathon_approve, marathon_add_decision, marathon_status_json,
    )
    _MARATHON_OK = True
except Exception as _me:
    _MARATHON_OK = False
    print(f"[WARN] marathon_tasks não carregado: {_me}")


async def _run_marathon_task_bg(task_id: str):
    """Executa uma tarefa da maratona em background e atualiza o estado."""
    if not _MARATHON_OK:
        return
    task_def = marathon_get_task(task_id)
    if not task_def:
        return

    agent = task_def["agent"]
    marathon_set_status(task_id, "rodando")
    await manager.broadcast({
        "type": "marathon_update",
        "task_id": task_id,
        "agent": agent,
        "status": "rodando",
        "timestamp": datetime.now().strftime("%H:%M"),
    })

    # Executa via cascata LLM
    try:
        llm_result = await llm_call_cascade(
            system=task_def["system"],
            user_msg=task_def["user"],
            max_tokens=task_def.get("max_tokens", 600),
        )
        # llm_call_cascade retorna (text, provider) ou só text dependendo da versão
        if isinstance(llm_result, tuple):
            result, _provider = llm_result
        else:
            result = llm_result
    except Exception as _llm_err:
        result = f"[ERRO LLM] {agent.upper()}: {_llm_err}"
        marathon_set_status(task_id, "pendente")
        await manager.broadcast({
            "type": "marathon_update", "task_id": task_id, "agent": agent,
            "status": "pendente", "result": str(_llm_err)[:200],
            "timestamp": datetime.now().strftime("%H:%M"),
        })
        return

    if not result:
        result = f"{agent.upper()} concluiu a análise para a maratona."

    needs_approval = task_def.get("needs_approval", False)
    new_status = "aguardando_aprovacao" if needs_approval else "concluido"
    marathon_set_status(task_id, new_status, result)

    if needs_approval:
        marathon_add_decision(task_id, task_def["title"], agent, result)

    # Salva resultado no vault
    vault_path = pathlib.Path(OBSIDIAN_VAULT) / "Maratona"
    vault_path.mkdir(exist_ok=True)
    ts_safe = datetime.now().strftime("%Y%m%d-%H%M")
    fname = vault_path / f"marathon-{task_id}-{ts_safe}.md"
    fname.write_text(
        f"---\nagent: {agent.upper()}\ntask_id: {task_id}\n"
        f"day: {task_def['day']}\narea: {task_def['area']}\n"
        f"status: {new_status}\ncreated_at: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n---\n\n"
        f"# {task_def['title']}\n\n{result}\n",
        encoding="utf-8",
    )

    await manager.broadcast({
        "type": "marathon_update",
        "task_id": task_id,
        "agent": agent,
        "status": new_status,
        "result": result[:300],
        "needs_approval": needs_approval,
        "timestamp": datetime.now().strftime("%H:%M"),
    })


@app.post("/marathon/start")
async def marathon_start(body: dict = {}):
    """Inicia a maratona — inicializa estado e opcionalmente dispara um dia."""
    if not _MARATHON_OK:
        return {"error": "marathon_tasks não carregado"}
    marathon_init()
    day = body.get("day")  # "sexta" | "sabado" | "domingo" | None (todos)
    tasks_to_run = [
        t for t in MARATHON_TASKS
        if (day is None or t["day"] == day)
    ]
    # Dispara em background, respeitando order (lança todas, APScheduler interno)
    for t in sorted(tasks_to_run, key=lambda x: x["order"]):
        asyncio.create_task(_run_marathon_task_bg(t["id"]))
    await manager.broadcast({
        "type": "marathon_started",
        "day": day or "all",
        "tasks_count": len(tasks_to_run),
        "timestamp": datetime.now().strftime("%H:%M"),
    })
    return {
        "ok": True,
        "day": day or "all",
        "tasks_dispatched": len(tasks_to_run),
        "task_ids": [t["id"] for t in tasks_to_run],
    }


@app.get("/marathon/status")
async def marathon_get_status():
    """Retorna estado completo da maratona para o dashboard."""
    if not _MARATHON_OK:
        return {"error": "marathon_tasks não carregado", "active": False}
    return marathon_status_json()


@app.post("/marathon/tasks/{task_id}/run")
async def marathon_run_task(task_id: str):
    """Dispara uma tarefa específica da maratona."""
    if not _MARATHON_OK:
        return {"error": "marathon_tasks não carregado"}
    task_def = marathon_get_task(task_id)
    if not task_def:
        return {"error": f"Tarefa '{task_id}' não encontrada"}
    asyncio.create_task(_run_marathon_task_bg(task_id))
    return {"ok": True, "task_id": task_id, "agent": task_def["agent"], "title": task_def["title"]}


class MarathonApproveBody(BaseModel):
    approved: bool
    note: str = ""

@app.post("/marathon/tasks/{task_id}/approve")
async def marathon_approve_task(task_id: str, body: MarathonApproveBody):
    """Eduardo aprova ou rejeita uma tarefa da maratona."""
    if not _MARATHON_OK:
        return {"error": "marathon_tasks não carregado"}
    task_def = marathon_get_task(task_id)
    if not task_def:
        return {"error": f"Tarefa '{task_id}' não encontrada"}
    marathon_approve(task_id, body.approved)
    action = "aprovado" if body.approved else "rejeitado"
    if body.note:
        # Salva nota no vault
        note_path = pathlib.Path(OBSIDIAN_VAULT) / "Maratona" / f"decisao-{task_id}.md"
        note_path.write_text(
            f"---\ntask_id: {task_id}\napproved: {body.approved}\n"
            f"note: '{body.note}'\nts: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n---\n\n"
            f"# Decisão: {task_def['title']}\n\n**Eduardo:** {body.note}\n",
            encoding="utf-8",
        )
    await manager.broadcast({
        "type": "marathon_decision",
        "task_id": task_id,
        "agent": task_def["agent"],
        "approved": body.approved,
        "timestamp": datetime.now().strftime("%H:%M"),
    })
    return {"ok": True, "task_id": task_id, "action": action}


@app.get("/marathon/decisions")
async def marathon_get_decisions():
    """Lista decisões pendentes para Eduardo aprovar."""
    if not _MARATHON_OK:
        return {"decisions": []}
    return {"decisions": _MARATHON_STATE.get("decisions", [])}


@app.post("/marathon/reset")
async def marathon_reset():
    """Reseta o estado da maratona (novo ciclo)."""
    if not _MARATHON_OK:
        return {"error": "marathon_tasks não carregado"}
    _MARATHON_STATE["active"] = False
    _MARATHON_STATE["started_at"] = None
    _MARATHON_STATE["tasks"] = {}
    _MARATHON_STATE["decisions"] = []
    return {"ok": True}


# ══════════════════════════════════════════════════════════════════════════════
# SHOPIFY LIVE UPDATER — DEV + THEO + VERA + ARTE + MIRA trabalhando na loja
# ══════════════════════════════════════════════════════════════════════════════

try:
    from shopify_live_updater import (
        LIVE_IMPROVEMENT_TASKS, SHOPIFY_ASPECT_RATIO_CSS, SHOPIFY_CRO_SNIPPETS,
        get_improvement_results, mark_improvement_done, get_task_by_id as _get_improvement_task,
        generate_product_images, generate_pollinations_url,
    )
    _SHOPIFY_UPDATER_OK = True
except Exception as _sue:
    _SHOPIFY_UPDATER_OK = False
    print(f"[WARN] shopify_live_updater não carregado: {_sue}")


async def _run_shopify_improvement(task_id: str):
    """Executa uma melhoria de loja em background via agente LLM."""
    if not _SHOPIFY_UPDATER_OK:
        return
    task = _get_improvement_task(task_id)
    if not task:
        return

    _log_activity(task["agent"], f"⚙ Shopify improvement: {task['title'][:80]}", "", task["category"])
    await manager.broadcast({
        "type": "agent_activity",
        "agent_id": task["agent"],
        "message": f"🛒 {task['title'][:100]}",
        "category": task["category"],
        "timestamp": datetime.now().strftime("%H:%M"),
    })

    try:
        result, provider = await llm_call_cascade(task["system"], task["user"], max_tokens=800)
        if result:
            mark_improvement_done(task_id, result, provider)
            _log_activity(task["agent"], f"✓ Loja atualizada: {task['title'][:60]}", result[:150], task["category"])
            # Salva no vault
            vault_dir = pathlib.Path(OBSIDIAN_VAULT) / "ShopifyImprovements"
            vault_dir.mkdir(exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d-%H%M")
            (vault_dir / f"{task['agent']}-{task_id}-{ts}.md").write_text(
                f"---\nagent: {task['agent'].upper()}\ntask: {task_id}\n"
                f"ts: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n---\n\n"
                f"# {task['title']}\n\n{result}\n",
                encoding="utf-8",
            )
            await manager.broadcast({
                "type": "activity_log",
                "agent_id": task["agent"],
                "action": f"✓ {task['title'][:80]}",
                "detail": result[:200],
                "category": task["category"],
                "timestamp": datetime.now().strftime("%H:%M"),
            })
    except Exception as e:
        _log_activity(task["agent"], f"⚠ Erro improvement {task_id}", str(e)[:100], "agent")


async def shopify_live_updater_scheduler():
    """
    Scheduler do Shopify Live Updater.
    Executa melhorias automáticas da loja todo dia, em rotação.
    Roda de manhã cedo para que Eduardo veja os resultados ao acordar.
    """
    await asyncio.sleep(60)
    _fired_improvements: set[str] = set()
    task_queue = list(LIVE_IMPROVEMENT_TASKS) if _SHOPIFY_UPDATER_OK else []
    task_idx = 0

    while True:
        now = datetime.now()
        day_key = now.strftime("%Y-%m-%d")

        # Reset diário
        if now.hour == 0 and now.minute < 2:
            _fired_improvements.discard(day_key)

        # Roda 2 melhorias por dia: 7h30 e 13h30
        for run_hour, run_min in [(7, 30), (13, 30)]:
            slot = f"{day_key}_improvement_{run_hour}"
            if now.hour == run_hour and now.minute >= run_min and now.minute < run_min + 10 and slot not in _fired_improvements:
                _fired_improvements.add(slot)
                if task_queue:
                    task = task_queue[task_idx % len(task_queue)]
                    task_idx += 1
                    asyncio.create_task(_run_shopify_improvement(task["id"]))

        await asyncio.sleep(50)


@app.get("/shopify/improvements")
async def get_shopify_improvements():
    """Retorna status das melhorias automáticas da loja."""
    if not _SHOPIFY_UPDATER_OK:
        return {"error": "shopify_live_updater não carregado"}
    return get_improvement_results()


@app.post("/shopify/improvements/{task_id}/run")
async def run_shopify_improvement(task_id: str):
    """Dispara uma melhoria específica agora."""
    if not _SHOPIFY_UPDATER_OK:
        return {"error": "shopify_live_updater não carregado"}
    task = _get_improvement_task(task_id)
    if not task:
        return {"error": f"Task '{task_id}' não encontrada"}
    asyncio.create_task(_run_shopify_improvement(task_id))
    return {"ok": True, "task_id": task_id, "agent": task["agent"], "title": task["title"]}


@app.get("/shopify/improvements/css")
async def get_aspect_ratio_css():
    """Retorna o CSS de correção de aspect ratio para o tema Shopify."""
    if not _SHOPIFY_UPDATER_OK:
        return {"error": "shopify_live_updater não carregado"}
    return {
        "css": SHOPIFY_ASPECT_RATIO_CSS,
        "snippets": list(SHOPIFY_CRO_SNIPPETS.keys()),
        "instruction": "Adicione o CSS em Loja Online > Temas > Editar código > assets/custom.css",
    }


@app.get("/shopify/improvements/snippets/{snippet_name}")
async def get_cro_snippet(snippet_name: str):
    """Retorna um snippet CRO específico."""
    if not _SHOPIFY_UPDATER_OK:
        return {"error": "shopify_live_updater não carregado"}
    if snippet_name not in SHOPIFY_CRO_SNIPPETS:
        return {"error": f"Snippet '{snippet_name}' não encontrado", "available": list(SHOPIFY_CRO_SNIPPETS.keys())}
    return {"name": snippet_name, "code": SHOPIFY_CRO_SNIPPETS[snippet_name]}


@app.get("/shopify/images/generate")
async def generate_product_image_urls(product_type: str = "vaso", product_title: str = "Produto Aura Decore", seed: int = 100):
    """Gera URLs de imagens Pollinations.ai para um produto."""
    if not _SHOPIFY_UPDATER_OK:
        return {"error": "shopify_live_updater não carregado"}
    images = generate_product_images(product_type, product_title, seed)
    return {"images": images, "count": len(images)}


# ── Frontend: rotas explícitas + mount estático ──────────────────────────────

_ROOT = pathlib.Path(__file__).parent.parent

from fastapi.responses import FileResponse, HTMLResponse

@app.get("/mobile", response_class=HTMLResponse)
async def mobile_dashboard():
    """Dashboard mobile PWA — installable Android/iOS."""
    mobile_file = _ROOT / "aura-mobile.html"
    if mobile_file.exists():
        return HTMLResponse(mobile_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h2>aura-mobile.html não encontrado</h2>", status_code=404)

@app.get("/erp-ui", response_class=HTMLResponse)
@app.get("/erp/ui", response_class=HTMLResponse)
async def erp_ui():
    """Interface visual do ERP/CRM Aura Decore."""
    erp_file = _ROOT / "erp.html"
    if erp_file.exists():
        return HTMLResponse(erp_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h2>erp.html não encontrado</h2>", status_code=404)

@app.get("/manifest.json")
async def pwa_manifest():
    """PWA manifest para instalação Android/iOS."""
    from fastapi.responses import JSONResponse
    mf = _ROOT / "manifest.json"
    if mf.exists():
        import json as _json
        return JSONResponse(content=_json.loads(mf.read_text(encoding="utf-8")),
                           headers={"Cache-Control": "no-cache"})
    return JSONResponse({"error": "manifest not found"}, status_code=404)

@app.get("/sw.js")
async def service_worker():
    """Service Worker para cache offline e notificações push."""
    from fastapi.responses import Response as _Resp
    sw = _ROOT / "sw.js"
    if sw.exists():
        return _Resp(content=sw.read_text(encoding="utf-8"),
                    media_type="application/javascript",
                    headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"})
    return _Resp(content="// sw not found", media_type="application/javascript")

@app.get("/pwa-icon-192.png")
async def pwa_icon_192():
    """Ícone PWA 192x192."""
    f = _ROOT / "pwa-icon-192.png"
    if f.exists():
        return FileResponse(str(f), media_type="image/png",
                           headers={"Cache-Control": "public, max-age=86400"})
    return FileResponse(str(_ROOT / "favicon.ico")) if (_ROOT / "favicon.ico").exists() else \
           JSONResponse({"error": "icon not found"}, status_code=404)

@app.get("/pwa-icon-512.png")
async def pwa_icon_512():
    """Ícone PWA 512x512."""
    f = _ROOT / "pwa-icon-512.png"
    if f.exists():
        return FileResponse(str(f), media_type="image/png",
                           headers={"Cache-Control": "public, max-age=86400"})
    return JSONResponse({"error": "icon not found"}, status_code=404)


# ══════════════════════════════════════════════════════════════════════════════
# META BUSINESS ROUTES (/meta/*)
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/meta/status")
async def meta_status():
    """Status completo da integração Meta Business."""
    if not _META_OK:
        return JSONResponse({"error": "Meta Integration module não carregado"}, status_code=500)
    report = MetaInsights().full_status_report()
    return JSONResponse(report)


@app.get("/meta/pixel-snippet")
async def meta_pixel_snippet():
    """Retorna o snippet do Meta Pixel para o tema Shopify."""
    if not _META_OK:
        return JSONResponse({"error": "Meta Integration não disponível"}, status_code=500)
    return JSONResponse({
        "base": MetaPixel.base_snippet(),
        "product_view": MetaPixel.product_view_snippet(),
        "add_to_cart": MetaPixel.add_to_cart_snippet(),
        "checkout": MetaPixel.checkout_snippet(),
        "purchase": MetaPixel.purchase_snippet(),
    })


@app.post("/meta/event")
async def meta_send_event(request: Request):
    """Envia um evento customizado via CAPI."""
    if not _META_OK:
        return JSONResponse({"error": "Meta Integration não disponível"}, status_code=500)
    body = await request.json()
    event_name = body.get("event_name", "PageView")
    url        = body.get("url", "")
    custom_data = body.get("custom_data", {})
    user_data   = body.get("user_data", {})
    capi = MetaCAPI()
    result = capi.send_event(event_name, event_source_url=url,
                             custom_data=custom_data, user_data=user_data)
    return JSONResponse(result)


@app.post("/meta/event/purchase")
async def meta_purchase_event(request: Request):
    """Dispara evento Purchase via CAPI (usado pelo backend após pedido confirmado)."""
    if not _META_OK:
        return JSONResponse({"error": "Meta Integration não disponível"}, status_code=500)
    body = await request.json()
    capi = MetaCAPI()
    result = capi.purchase(
        order_id   = str(body.get("order_id", "")),
        value      = float(body.get("value", 0)),
        product_ids = body.get("product_ids", []),
        num_items  = int(body.get("num_items", 1)),
        currency   = body.get("currency", "BRL"),
        email      = body.get("email", ""),
        phone      = body.get("phone", ""),
    )
    return JSONResponse(result)


@app.post("/meta/webhook/order")
async def meta_webhook_order(request: Request):
    """
    Endpoint para webhook Shopify orders/create.
    Configure em: Shopify Admin > Configurações > Notificações > Webhooks
    URL: https://SEU_BACKEND/meta/webhook/order
    """
    if not _META_OK:
        return JSONResponse({"status": "meta_not_loaded"})
    try:
        order = await request.json()
        bridge = MetaShopifyBridge()
        result = bridge.handle_order(order)
        return JSONResponse({"status": "ok", "capi": result})
    except Exception as e:
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=400)


@app.post("/meta/webhook/checkout")
async def meta_webhook_checkout(request: Request):
    """
    Endpoint para webhook Shopify checkouts/create.
    URL: https://SEU_BACKEND/meta/webhook/checkout
    """
    if not _META_OK:
        return JSONResponse({"status": "meta_not_loaded"})
    try:
        checkout = await request.json()
        bridge = MetaShopifyBridge()
        result = bridge.handle_checkout(checkout)
        return JSONResponse({"status": "ok", "capi": result})
    except Exception as e:
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=400)


@app.get("/meta/test-events")
async def meta_test_events(test_code: str = "TEST_AURA_001"):
    """Testa todos os eventos CAPI no Meta Event Manager."""
    if not _META_OK:
        return JSONResponse({"error": "Meta Integration não disponível"}, status_code=500)
    tester = MetaEventTest(test_code=test_code)
    results = tester.run_all_tests()
    return JSONResponse(results)


@app.get("/meta/catalogs")
async def meta_list_catalogs():
    """Lista catálogos do Meta Business Manager."""
    if not _META_OK:
        return JSONResponse({"error": "Meta Integration não disponível"}, status_code=500)
    catalog = MetaCatalog()
    return JSONResponse(catalog.list_catalogs())


@app.get("/meta/catalog/{catalog_id}/status")
async def meta_catalog_status(catalog_id: str):
    """Status de um catálogo específico."""
    if not _META_OK:
        return JSONResponse({"error": "Meta Integration não disponível"}, status_code=500)
    catalog = MetaCatalog()
    return JSONResponse(catalog.get_catalog_status(catalog_id))


@app.post("/meta/catalog/{catalog_id}/sync")
async def meta_catalog_sync(catalog_id: str):
    """Força re-sincronização do feed de um catálogo."""
    if not _META_OK:
        return JSONResponse({"error": "Meta Integration não disponível"}, status_code=500)
    catalog = MetaCatalog()
    feeds = catalog.list_feeds(catalog_id)
    if "data" not in feeds:
        return JSONResponse({"error": "Catálogo não encontrado ou sem feeds", "detail": feeds})
    results = []
    for feed in feeds.get("data", []):
        fid = feed.get("id")
        if fid:
            r = catalog.trigger_feed_refresh(fid)
            results.append({"feed_id": fid, "result": r})
    return JSONResponse({"synced_feeds": results})


@app.get("/meta/feed-url")
async def meta_feed_url():
    """Retorna a URL do feed Shopify para configurar no Meta Catalog."""
    catalog = MetaCatalog()
    return JSONResponse({
        "feed_url": catalog.get_shopify_feed_url(),
        "instructions": (
            "No Meta Business Manager → Catálogos → Seu Catálogo → "
            "Fontes de Dados → Adicionar Feed → colar esta URL"
        ),
    })


app.mount("/", StaticFiles(directory=str(_ROOT), html=True), name="static")
