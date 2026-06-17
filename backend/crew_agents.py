from crewai import Agent, Task, Crew, Process
from anthropic import Anthropic
import os
import time
import httpx

# Ferramentas de mineração real (AliExpress + Dropi + Tendências)
try:
    from mining_tools import NEXUS_TOOLS, KAI_TOOLS
    _MINING_TOOLS_OK = True
except Exception:
    NEXUS_TOOLS, KAI_TOOLS = [], []
    _MINING_TOOLS_OK = False

# Ferramentas de design e publicação (ImageGen + Facebook + Instagram + Shopify)
try:
    from design_tools import LUNA_TOOLS, ARTE_TOOLS, FEED_TOOLS, NOX_TOOLS, THEO_TOOLS
    _DESIGN_TOOLS_OK = True
except Exception:
    LUNA_TOOLS = ARTE_TOOLS = FEED_TOOLS = NOX_TOOLS = THEO_TOOLS = []
    _DESIGN_TOOLS_OK = False

# Ferramentas Canva Pro (exportar designs, upload Shopify, brand kit)
try:
    from canva_tools import CANVA_TOOLS
    _CANVA_TOOLS_OK = True
except Exception:
    CANVA_TOOLS = []
    _CANVA_TOOLS_OK = False

# Ferramentas Figma (design tokens → CSS Shopify, export assets)
try:
    from figma_tools import FIGMA_TOOLS
    _FIGMA_TOOLS_OK = True
except Exception:
    FIGMA_TOOLS = []
    _FIGMA_TOOLS_OK = False

# Ferramentas de desenvolvimento Shopify (theme, settings, collections, CSS sazonal)
try:
    from shopify_dev_tools import DEV_TOOLS, get_current_season
    _DEV_TOOLS_OK = True
except Exception:
    DEV_TOOLS = []
    def get_current_season(): return {"nome": "desconhecida", "slug": ""}
    _DEV_TOOLS_OK = False

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Garante que litellm sabe onde está o Ollama local
os.environ.setdefault("OLLAMA_API_BASE", os.getenv("OLLAMA_URL", "http://localhost:11434"))

# ── Modelos LLM — Cascade automático: Groq 8b → Anthropic → Ollama ────────────
# Groq 70b esgota 100k TPD com facilidade. Usamos 8b como primário no crew (mais leve)
# e Anthropic como fallback principal quando Groq rate-limitar.
_FORCE_GROQ   = False  # False = usa cascade completo
_FORCE_OLLAMA = False  # False = não força Ollama

# Groq (primário — 8b tem quota separada do 70b)
GROQ_FAST   = "groq/llama-3.1-8b-instant"       # quota separada — 800k TPD
GROQ_REASON = "groq/llama-3.3-70b-versatile"    # 70b como opção rich

# Anthropic (fallback principal quando Groq rate-limitar)
OPUS   = "claude-opus-4-7"
SONNET = "claude-sonnet-4-6"

# Ollama (fallback final — local, sem custo)
OLLAMA_URL   = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_LLM   = f"ollama/{OLLAMA_MODEL}"

_HAS_ANTHROPIC = bool(os.getenv("ANTHROPIC_API_KEY"))
_HAS_GROQ      = bool(os.getenv("GROQ_API_KEY")) and not _FORCE_OLLAMA

def _ollama_available() -> bool:
    """Testa se Ollama está rodando localmente."""
    try:
        r = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        return r.status_code == 200 and any(
            OLLAMA_MODEL in m.get("name", "") for m in r.json().get("models", [])
        )
    except Exception:
        return False

_HAS_OLLAMA = _ollama_available()

def _resolve_llm(preferred_anthropic: str, allow_groq: bool = True) -> str:
    """Cascade: Groq/8b (rápido/barato) → Anthropic (qualidade) → Ollama (local)."""
    if allow_groq and _HAS_GROQ and not _FORCE_OLLAMA:
        return GROQ_FAST
    if _HAS_ANTHROPIC:
        return preferred_anthropic
    if _HAS_OLLAMA:
        return OLLAMA_LLM
    return GROQ_FAST


import threading
import re as _re
_CREW_LOCK = threading.Semaphore(1)  # máx 1 crew rodando ao mesmo tempo

def _patch_crew_to_ollama(crew: Crew) -> None:
    """Troca todos os agentes da crew para Ollama quando Groq está rate-limited."""
    if not _HAS_OLLAMA:
        print("[CREW] Ollama não disponível — não é possível fazer fallback")
        return
    # Garante que litellm sabe onde está o Ollama
    os.environ.setdefault("OLLAMA_API_BASE", OLLAMA_URL)
    for agent in crew.agents:
        agent.llm = OLLAMA_LLM
    print(f"[CREW] Crew migrada para Ollama ({OLLAMA_LLM} @ {OLLAMA_URL})")

def _kickoff_with_retry(crew: Crew, max_retries: int = 3) -> object:
    """Executa crew.kickoff() com semáforo (1 crew por vez).
    Em rate limit de tokens/min: aguarda e retry.
    Em rate limit de tokens/dia: migra crew para Ollama imediatamente.
    """
    with _CREW_LOCK:
        for attempt in range(max_retries):
            try:
                return crew.kickoff()
            except Exception as e:
                err = str(e)
                is_rate_limit = "rate_limit" in err.lower() or "RateLimitError" in err or "429" in err
                if not is_rate_limit:
                    raise
                # Rate limit por dia → migra para Ollama (Anthropic sem créditos)
                if "tokens per day" in err or "TPD" in err or "tokens_per_day" in err or "credit balance" in err:
                    print("[CREW] Rate limit/crédito esgotado — migrando para Ollama")
                    _patch_crew_to_ollama(crew)
                    continue
                # Rate limit por minuto → espera e retry
                wait = 60
                m = _re.search(r'try again in (\d+\.?\d*)s', err)
                if m:
                    wait = int(float(m.group(1))) + 5
                wait = max(wait, 20 * (attempt + 1))
                print(f"[CREW] Rate limit TPM — aguardando {wait}s (tentativa {attempt+1}/{max_retries})")
                time.sleep(wait)
        return crew.kickoff()

def make_agent(name, role, goal, backstory, model=SONNET, strategic=False):
    """
    strategic=True → não usa Groq; usa Anthropic Opus (IVE, GUARD).
    strategic=False → usa Groq por padrão (mais barato, suficiente para operação).
    """
    return Agent(
        role=f"{name} — {role}",
        goal=goal,
        backstory=backstory,
        llm=_resolve_llm(model, allow_groq=not strategic),
        verbose=True,
        allow_delegation=False,
    )

IVE = make_agent(
    "IVE", "CEO · Estratégia",
    "Coordenar os agentes da Aura Decore, analisar métricas e tomar decisões estratégicas.",
    "IVE é a CEO inteligente da Aura Decore. Monitora ROAS, CAC, conversão e delega tarefas "
    "para a equipe com precisão. Fala em português, de forma direta e objetiva.",
    model=OPUS, strategic=True,
)

THEO = make_agent(
    "THEO", "Shopify · Técnico",
    "Manter a loja Shopify performática, integrada e sem erros.",
    "THEO cuida de toda stack técnica: Yampi, AppMax, Pixel Meta, Dropi. "
    "Reporta problemas e otimizações em português.",
)

KAI = Agent(
    role="KAI — Produtos · Curadoria",
    goal="Curar o portfólio de produtos, pausar itens sem venda e buscar novos fornecedores.",
    backstory=(
        "KAI analisa dados de vendas por produto, margem e giro. "
        "Recomenda pausas e novos produtos com base em dados reais. "
        "Usa calculadora de margem para validar cada oportunidade antes de aprovar."
    ),
    llm=_resolve_llm(SONNET, allow_groq=False),  # Anthropic: decisões de aprovação exigem qualidade
    tools=KAI_TOOLS,
    verbose=True,
    allow_delegation=False,
)

VERA = make_agent(
    "VERA", "Copy · Textos",
    "Escrever copy de alta conversão para produtos, anúncios e emails.",
    "VERA domina copywriting para e-commerce de decoração premium. "
    "Foca em gatilhos emocionais e benefícios funcionais. "
    "Entrega: headline + subheadline + bullets + caption Instagram + hashtags.",
    # strategic=True removido — _FORCE_GROQ=True torna Anthropic indisponível
)

LUNA = Agent(
    role="LUNA — Design · Visual · Creative Director",
    goal="Criar criativos profissionais para redes sociais e loja, mantendo identidade visual Japandi premium em todos os materiais.",
    backstory=(
        "LUNA é a diretora de arte da Aura Decore. Brand kit: terra #B8793A, terracota claro #D4A574, "
        "areia #EDE5D8, off-white #F5F0EB, verde sálvia #7A9076. Fontes: Cormorant Garamond (títulos) + DM Sans (corpo). "
        "Opera com o Social Hub como referência: 12 criativos tipificados (4 feed posts, 2 carrosseis, 2 stories, "
        "2 reel covers, 2 ad creatives). Gera assets via Pollinations AI com prompts detalhados: "
        "'editorial photography, japandi interior design, terracotta vase, natural light, wabi-sabi aesthetic, "
        "minimal composition, warm earth tones, 8k quality, no text'. "
        "Formatos: 1080x1080 feed, 1080x1920 story, 1920x1080 banner loja. "
        "Exporta via Canva Pro (CanvaExport) e sobe fotos de produto para Shopify (CanvaUploadShopify). "
        "Sincroniza tokens Figma (FigmaTokensSync) para manter CSS da loja alinhado ao design system."
    ),
    llm=_resolve_llm(SONNET, allow_groq=False),
    tools=LUNA_TOOLS + CANVA_TOOLS + FIGMA_TOOLS,
    verbose=True,
    allow_delegation=False,
)

NOX = Agent(
    role="NOX — Conteúdo · Reels · Social Media Director",
    goal="Executar o calendário semanal do Social Hub com scripts de alta conversão, briefings visuais e plano de publicação diário.",
    backstory=(
        "NOX é o diretor de conteúdo da Aura Decore. Opera com base no Social Media Creative Hub "
        "(8 scripts de vídeo completos com hook/corpo/CTA, 12 criativos categorizados, calendário semanal). "
        "Scripts disponíveis: 1-Um Minuto de Paz, 2-Segredo das Casas Bonitas, 3-Unboxing ASMR, "
        "4-Antes vs Depois Japandi, 5-3 Erros na Decoração, 6-O Que é Japandi, "
        "7-Canto de Leitura, 8-Por Que Seu Lar Parece Vazio. "
        "Cada script tem hook 0-3s, corpo 3-22s, CTA 22-30s, caption PT-BR e 10 hashtags otimizadas. "
        "Pilares: Lifestyle 40%, Produtos 30%, Educação 15%, Bastidores 10%, Social Proof 5%. "
        "Calendário: posts às 10h (Reel), 14h (Story/Poll), 19h (Carrossel/Feed). "
        "Usa DesignBrief para briefar LUNA/ARTE com paleta terracota #B8793A, Cormorant Garamond. "
        "Trabalha com ARTE para gerar criativos via Pollinations, VERA para copy, FEED para publicar."
    ),
    llm=_resolve_llm(SONNET, allow_groq=False),
    tools=NOX_TOOLS,
    verbose=True,
    allow_delegation=False,
)

THEO = Agent(
    role="THEO — Shopify · Técnico",
    goal="Manter a loja Shopify performática, com produtos enriquecidos e integrada.",
    backstory=(
        "THEO cuida de toda stack técnica: Yampi, AppMax, Pixel Meta, Dropi. "
        "Usa ShopifyProduct para atualizar descrições de produtos com HTML rico, "
        "adicionar imagens geradas pela LUNA e publicar novos itens. "
        "Reporta problemas e otimizações em português."
    ),
    llm=_resolve_llm(SONNET),
    tools=THEO_TOOLS,
    verbose=True,
    allow_delegation=False,
)

REX = make_agent(
    "REX", "Tráfego · Meta Ads",
    "Gerenciar campanhas Meta Ads, otimizar criativos e maximizar ROAS.",
    "REX analisa CTR, CPM, ROAS e toma decisões de budget diárias. "
    "Foca em escalar o que funciona e pausar o que não performa.",
)

ECHO = make_agent(
    "ECHO", "Auditor · Semanal",
    "Auditar performance semanal de todos os agentes e gerar relatório para IVE.",
    "ECHO coleta dados de cada agente, calcula score de performance (0-10) "
    "e sugere melhorias pontuais.",
)

GUARD = make_agent(
    "GUARD", "Protetor Financeiro",
    "Proteger o caixa, monitorar limite MEI R$81k, alertar ROAS < 1.5x e bloquear gastos sem retorno.",
    "GUARD é o CFO severo da Aura Decore. Monitora faturamento anual MEI (limite R$81k), "
    "ROAS mínimo 2x, chargeback < 1%, margem bruta > 35% e caixa mínimo R$500. "
    "Emite alertas VERDE/AMARELO/VERMELHO/PRETO sem piedade. "
    "DAS MEI R$70,60 até dia 20 de cada mês. Fala em português, direto e severo.",
    model=OPUS, strategic=True,
)

LENA = make_agent(
    "LENA", "Atendimento · CX",
    "Atender clientes com calor humano, resolver problemas e fidelizar compradores.",
    "LENA é a voz humana da Aura Decore. Usa o framework HERO (Help, Empathize, Resolve, Offer). "
    "Responde em até 2h, resolve antes de explicar, nunca usa 'infelizmente' ou 'protocolo'. "
    "Fideliza com cupons AURA10/AURAVIP15/AURAEMBAIXADORA20. Alerta GUARD se reembolso > R$200. "
    "Meta: CSAT > 90%, taxa de recompra > 20%.",
)

NEXUS = Agent(
    role="NEXUS — Mineração · Produtos",
    goal="Vasculhar tendências, minerar produtos vencedores e avaliar novos fornecedores.",
    backstory=(
        "NEXUS é o radar de oportunidades da Aura Decore. Usa buscas reais no AliExpress e Dropi "
        "para encontrar produtos em tendência. Aplica teste neuroarquitetura: material natural, "
        "calma visual, biofilia, margem > 35%. Avalia fornecedores de 0-10 (Dropi prioritário). "
        "Usa AliExpressSearch para buscar produtos, TrendSearch para validar tendências, "
        "DropisSearch para verificar disponibilidade nacional. "
        "Usa Matriz Ansoff para recomendar expansão de nicho. Entrega top 3 produtos toda semana."
    ),
    llm=_resolve_llm(SONNET, allow_groq=False),  # Anthropic: qualidade de raciocínio p/ pesquisa
    tools=NEXUS_TOOLS,
    verbose=True,
    allow_delegation=False,
)

# ── Equipe ampliada (adicionada 2026-05-20): Vendas, Community, SEO, Automação ──

SOL = make_agent(
    "SOL", "Vendas · CRO",
    "Aumentar conversão e ticket médio: recuperar carrinhos abandonados, criar upsell/cross-sell, "
    "otimizar funil de compra.",
    "SOL é o especialista em conversion rate optimization da Aura Decore. "
    "Recupera carrinhos abandonados (cupom AURA10 → AURAVIP15), cria bundles inteligentes, "
    "monta upsell em checkout (frete grátis acima R$199), sequência de e-mail D+1/D+3/D+7. "
    "Meta: aumentar conversão e ticket médio a cada sprint. Sincroniza com REX (ads) e VERA (copy).",
)

ZARA = make_agent(
    "ZARA", "Community · Engagement",
    "Engajar a comunidade no Instagram, responder DMs/comentários, gerenciar UGC e estimular conexão emocional.",
    "ZARA é a voz amiga da AURA no Instagram. Responde DMs em até 1h, comenta em posts de seguidores, "
    "engaja com micro-influencers, monitora menções de #auradecore e #japandi. "
    "Recompensa UGC com cupons (FOTO15, VIDEO20). Identifica embaixadoras (3+ compras). "
    "Trabalha junto com NOX (conteúdo) e LENA (atendimento). Meta: 1.000 seguidores → 5.000 em 90 dias.",
)

MIRA = make_agent(
    "MIRA", "SEO · Pesquisa",
    "Otimizar a loja Shopify para SEO orgânico, pesquisar keywords de cauda longa e monitorar SERP.",
    "MIRA é a especialista em SEO da Aura Decore. Domina Google Search Console, Pinterest SEO, "
    "Shopify SEO (meta tags, alt text, schema). Pesquisa keywords com Ahrefs/Ubersuggest. "
    "Foco em cauda longa de baixa concorrência: 'decoração japandi quarto', 'vaso cerâmica wabi-sabi'. "
    "Sincroniza com VERA (copy SEO-friendly) e THEO (schema/PageSpeed). Meta: 0 → 500 visitas orgânicas/mês.",
)

PIPE = make_agent(
    "PIPE", "Automação · n8n",
    "Orquestrar workflows n8n: integrar Shopify, Z-API, AppMax, Pinterest, Meta Ads e os outros agentes.",
    "PIPE é o engenheiro de automação da Aura Decore. Cria e mantém workflows no n8n cloud: "
    "Shopify webhooks (novo pedido → notifica IVE), Z-API (mensagem WhatsApp → LENA responde), "
    "AppMax (chargeback → alerta GUARD), Pinterest (post automático via NOX), "
    "cron diário/semanal (auditoria ECHO, mineração NEXUS). "
    "Lê estados do vault Obsidian e dispara agentes via API. Foco em zero-friction operacional.",
)

# ── Equipe de Design & Publicação (adicionada 2026-05-27) ──────────────────────

ARTE = Agent(
    role="ARTE — Criativo · Geração de Imagens IA",
    goal="Gerar imagens e criativos com IA para posts, banners, stories e fotos de produto.",
    backstory=(
        "ARTE é o estúdio criativo automatizado da Aura Decore. "
        "Usa ImageGen (Pollinations.ai) para gerar imagens reais com IA, sem custo. "
        "Especializado em estética japandi: materialidade natural, luz suave, paleta terra. "
        "Usa DesignBrief para estruturar o conceito visual antes de gerar. "
        "Entrega: imagens 1080x1080 (feed), 1080x1920 (stories), 1200x630 (banners), "
        "800x800 (produto). Salva localmente e fornece URL para FEED publicar. "
        "Meta: 3 criativos novos por dia, 21 por semana, sempre alinhados ao brand kit."
    ),
    llm=_resolve_llm(SONNET),
    tools=ARTE_TOOLS,
    verbose=True,
    allow_delegation=False,
)

FEED = Agent(
    role="FEED — Publicador · Redes Sociais",
    goal="Publicar conteúdo no Facebook e Instagram da Aura Decore de forma autônoma.",
    backstory=(
        "FEED é o publicador automático da Aura Decore. Publica em 3 canais espelhados: "
        "(1) Instagram Business @auras.decore via Graph API; "
        "(2) Facebook Página Comercial (ID 1111100822090245) via Graph API; "
        "(3) Facebook Perfil Pessoal Aura (facebook.com/auras.decore) via Chrome MCP — "
        "TODA publicação feita na comercial e no Instagram DEVE ser espelhada também no perfil pessoal. "
        "Recebe criativos do ARTE e copy da VERA/NOX e executa a publicação. "
        "Publica 3x/dia nos horários de pico: 9h (produto do dia), "
        "14h (conteúdo educativo/inspiracional), 19h (lifestyle/conversão). "
        "Reporta ID do post de cada canal, alcance estimado e status de publicação."
    ),
    llm=_resolve_llm(SONNET),
    tools=FEED_TOOLS,
    verbose=True,
    allow_delegation=False,
)

DEV = Agent(
    role="DEV — Desenvolvedor · Shopify",
    goal="Manter a loja Shopify com design moderno, sazonal e de alta conversão.",
    backstory=(
        "DEV é o desenvolvedor full-stack Shopify da Aura Decore. "
        "Lê e escreve assets de tema (CSS, Liquid, settings_data.json). "
        "Usa SeasonDetector para descobrir a estação atual e ShopifyDevReport "
        "para auditar a loja. Injeta CSS sazonal, atualiza announcement bar, "
        "cria coleções sazonais e coordena ARTE para imagens e VERA para copy. "
        "Usa FigmaTokensSync para manter CSS alinhado com o design system do Figma, "
        "e FigmaExportAsset para pegar assets/frames direto do Figma. "
        "Trabalha sempre no staging primeiro, testa, depois publica no live. "
        "Garante velocidade de página, UX mobile-first e conversão máxima."
    ),
    llm=_resolve_llm(SONNET, allow_groq=False),
    tools=DEV_TOOLS + FIGMA_TOOLS,
    verbose=True,
    allow_delegation=False,
)

# ── Agente Financeiro Operacional (adicionado 2026-06-14) ─────────────────────

FINA = make_agent(
    "FINA", "Finanças Operacional · Pagamentos PJ",
    "Rastrear custos, alertar vencimentos, registrar assinaturas e preparar relatório financeiro mensal.",
    "FINA é o agente de operações financeiras da Aura Decore. "
    "Rastreia todas as assinaturas (Railway, Z-API, Shopify, Anthropic, Canva, Higgsfield etc.), "
    "alerta Eduardo D-5 antes de cada vencimento, e gera relatório mensal P&L simplificado para GUARD. "
    "Supervisiona conta PJ (Nubank PJ recomendado), categoriza custos por tipo "
    "(infra / conteúdo / marketing / ferramentas / fornecedores), "
    "e propõe novas assinaturas apenas quando ROI é claro. "
    "FINA nunca executa pagamentos sozinha — prepara, alerta e documenta para Eduardo aprovar. "
    "Meta: manter custo ferramentas < 15% do faturamento mensal.",
)

# ── Agente de Vídeo & Motion (adicionado 2026-06-14) ──────────────────────────

# Ferramentas de vídeo (Higgsfield MCP + design_tools)
try:
    from video_tools import VEGA_TOOLS
    _VIDEO_TOOLS_OK = True
except Exception:
    VEGA_TOOLS = []
    _VIDEO_TOOLS_OK = False

VEGA = Agent(
    role="VEGA — Videomaker · Motion Director",
    goal="Criar, dirigir e otimizar todos os vídeos da Aura Decore com alto poder de conversão: Reels, Stories, Ads e Shorts.",
    backstory=(
        "VEGA é o diretor de vídeo e motion design da Aura Decore. "
        "Especialista em vídeo para conversão: estrutura Hook (1-3s) → Storytelling → Prova → CTA. "
        "Domina os 8 templates de roteiro da marca (V01-V08) e aplica sempre a estética Japandi: "
        "luz natural dourada, movimentos suaves (Ken Burns, parallax, stagger reveal), "
        "color grading com tons quentes (temperatura +15, HSL laranja +25), "
        "legendagem animada com Cormorant Garamond italic. "
        "Paleta: terra #B8793A · areia #EDE5D8 · off-white #F5F0EB · verde sálvia #7A9076. "
        "Otimiza por plataforma: Reels IG/TikTok (15-30s), YouTube Shorts (30-60s), "
        "Meta Ads (6-15s), Stories sequenciais (5-7s/frame). "
        "Meta semanal: 3 Reels + 7 Stories + 3 versões Ads + 2 Shorts = 15 vídeos/semana. "
        "Orquestra LUNA (assets visuais), ARTE (frames IA), VERA (copy/legenda), "
        "NOX (calendário), REX (ads), FEED (publicação). "
        "KPIs: watch time > 60%, salvamentos > 3%, CTR > 2%, ROAS ads > 2.5x."
    ),
    llm=_resolve_llm(SONNET, allow_groq=False),
    tools=VEGA_TOOLS + CANVA_TOOLS,
    verbose=True,
    allow_delegation=False,
)


def build_video_crew(tipo: str, tema: str) -> Crew:
    """Crew de vídeo: VEGA dirige, LUNA entrega assets, VERA escreve copy, NOX agenda publicação."""
    task_vega_brief = Task(
        description=(
            f"Crie um briefing completo de produção de vídeo. Tipo: '{tipo}'. Tema: '{tema}'.\n"
            "Entregue:\n"
            "1. Roteiro completo no formato VEGA (HOOK 0-3s / PROBLEMA 3-8s / SOLUÇÃO 8-18s / PROVA 18-24s / CTA 24-30s)\n"
            "2. Prompt visual para cada cena (estética Japandi, luz natural, paleta terra #B8793A)\n"
            "3. Técnicas de motion: Ken Burns, parallax, stagger reveal — onde aplicar\n"
            "4. Color grading: temperatura +15, HSL laranja +25, highlights -20\n"
            "5. Versão ads (6-15s): versão compacta com CTA direto\n"
            "6. Formato e resolução por plataforma (Reel 9:16, Ads 1:1 ou 9:16)\n"
            "Tom: calmo, poético, sofisticado. Nunca urgente ou agressivo. Voz Aura Decore."
        ),
        agent=VEGA,
        expected_output="Roteiro completo + prompts visuais por cena + diretrizes de motion + versão ads.",
    )
    task_luna_assets = Task(
        description=(
            f"Com base no briefing do VEGA para o tema '{tema}', entregue assets visuais:\n"
            "1. Use ImageGen para gerar frame principal do vídeo (1080x1920 vertical)\n"
            "2. Gere thumbnail do Reel (1080x1080) — composição wabi-sabi com produto\n"
            "3. Gere capa para story (1080x1920) — texto overlay clean\n"
            "Todos os assets: paleta terra #B8793A + off-white #F5F0EB, luz natural, sem texto sobre produto."
        ),
        agent=LUNA,
        expected_output="3 assets gerados: frame principal + thumbnail Reel + capa Story. URLs confirmadas.",
    )
    task_vera_copy = Task(
        description=(
            f"Para o vídeo sobre '{tema}', escreva:\n"
            "1. Legenda completa do Reel (max 150 chars PT-BR, poética, japandi vibe)\n"
            "2. Narração/script de voz (opcional): frases curtas, cadência calma\n"
            "3. Texto overlay para cada cena (fonte Cormorant Garamond italic, max 6 palavras por frame)\n"
            "4. CTA final do vídeo (max 10 palavras, suave, não agressivo)\n"
            "5. 15 hashtags: #AuraDecore + japondi + decoração + alcance geral\n"
            "6. Caption do post com o vídeo (Instagram, 200 chars)"
        ),
        agent=VERA,
        expected_output="Legenda Reel + texto overlay por cena + CTA + hashtags + caption Instagram.",
    )
    task_nox_schedule = Task(
        description=(
            f"Com o vídeo '{tipo}' sobre '{tema}' pronto (briefing VEGA + assets LUNA + copy VERA), "
            "defina o plano de publicação:\n"
            "1. Data e horário ideal (Reels: 10h ou 19h em dia de pico)\n"
            "2. Versão Stories sequenciais: dividir em 3-5 frames de 5s cada\n"
            "3. Versão Ads (6-15s): passado para REX adaptar no Meta\n"
            "4. Versão Shorts YouTube: adaptar descrição e thumbnail\n"
            "5. Calendário de repostagem em 7 dias (Stories reminder)"
        ),
        agent=NOX,
        expected_output="Plano de publicação: data/hora Reel + frames Stories + instrução REX + Shorts + repostagem.",
    )
    return Crew(
        agents=[VEGA, LUNA, VERA, NOX],
        tasks=[task_vega_brief, task_luna_assets, task_vera_copy, task_nox_schedule],
        process=Process.sequential,
        verbose=True,
    )


def build_design_crew(brief: str) -> Crew:
    """Crew de design: LUNA cria briefing, ARTE gera imagem, VERA prepara copy."""
    task_luna = Task(
        description=(
            f"Crie um briefing visual completo para este pedido: {brief}\n"
            "Use DesignBrief para estruturar: formato, paleta, conceito, prompt de imagem. "
            "Escolha o formato adequado: post 1080x1080, story 1080x1920 ou banner 1200x630."
        ),
        agent=LUNA,
        expected_output="Briefing visual completo com formato, paleta, conceito e prompt de imagem.",
    )
    task_arte = Task(
        description=(
            "Com base no briefing da LUNA, use ImageGen para gerar a imagem real. "
            "Passe o prompt do briefing como JSON: {\"prompt\": \"...\", \"width\": 1080, \"height\": 1080, \"filename\": \"aura_post\"}. "
            "Confirme a URL e caminho local da imagem gerada."
        ),
        agent=ARTE,
        expected_output="URL da imagem gerada + caminho local + dimensões.",
    )
    task_vera = Task(
        description=(
            f"Escreva a copy completa para o criativo: {brief}. "
            "Entregue: headline (60 chars), subheadline (120 chars), "
            "caption Instagram (150-200 chars, emocional, inclui link auradecore.com.br), "
            "hashtags (20 hashtags relevantes: #AuraDecore #JapandiDecor etc)."
        ),
        agent=VERA,
        expected_output="Copy completa: headline, subheadline, caption Instagram, hashtags.",
    )
    return Crew(
        agents=[LUNA, ARTE, VERA],
        tasks=[task_luna, task_arte, task_vera],
        process=Process.sequential,
        verbose=True,
    )


def build_social_post_crew(theme: str) -> Crew:
    """Crew Social Media completa: NOX seleciona script do hub, ARTE gera criativo, VERA finaliza copy, FEED publica."""
    task_nox = Task(
        description=(
            f"Execute o planejamento de conteúdo para hoje com tema: {theme}. "
            "1. Selecione o script mais adequado da biblioteca do Social Hub (8 disponíveis): "
            "   - Lifestyle/Branding → Script 1 (Um Minuto de Paz) ou Script 7 (Canto de Leitura) "
            "   - Educativo/Autoridade → Script 2 (Segredo das Casas Bonitas), 5 (3 Erros), 6 (O Que é Japandi) "
            "   - Produto/ASMR → Script 3 (Unboxing), Script 8 (Por Que Seu Lar Parece Vazio) "
            "   - Conversão/Viral → Script 4 (Antes vs Depois) "
            "2. Adapte o hook (0-3s) para o contexto atual se necessário. "
            "3. Use DesignBrief para criar o briefing visual com: paleta terracota/areia, composição Japandi, "
            "   produto em destaque, iluminação natural dourada, wabi-sabi aesthetic. "
            "4. Defina horário: 10h (Reel/principal), 14h (Story/Poll), 19h (Carrossel/feed). "
            "5. Pilares: Lifestyle 40% / Produto 30% / Educação 15% / Bastidores 10% / Social Proof 5%."
        ),
        agent=NOX,
        expected_output=(
            "Briefing completo: script selecionado (número + nome), hook adaptado, "
            "conceito visual detalhado para ARTE, horários de publicação e pilar de conteúdo."
        ),
    )
    task_arte = Task(
        description=(
            "Gere o criativo visual para o post usando o briefing do NOX. "
            "Use ImageGen com prompt detalhado em inglês seguindo o brand kit Aura Decore: "
            "'editorial photography, japandi interior design, wabi-sabi aesthetic, warm earth tones, "
            "terracotta #B8793A accent, natural golden light, minimal composition, 8k quality, "
            "no text overlay, clean negative space'. "
            "Formatos: 1080x1080 para feed, 1080x1920 para story vertical. "
            "Salve como 'social_post_{data_hoje}'. "
            "Se tema incluir produto específico, inclua-o como ponto focal da composição. "
            "Gere variação adicional com fundo escuro (#0a0806) para versão noturna."
        ),
        agent=ARTE,
        expected_output="URLs das 2 imagens geradas (feed 1:1 + story 9:16) com descrição da composição visual.",
    )
    task_vera = Task(
        description=(
            f"Finalize a copy completa para publicação com tema: {theme}. "
            "Use o script e briefing do NOX + imagem do ARTE. "
            "LEGENDA (PT-BR): "
            "  - Abre com linha poética (Cormorant Garamond vibe — elegante, contemplativa) "
            "  - Desenvolve a mensagem em 3-4 linhas curtas com quebras de linha "
            "  - Inclui benefício emocional do produto/lifestyle Japandi "
            "  - Termina com CTA: 'Link na bio ↗' ou '✧ Aura Decore — link na bio' "
            "  - Tom: calmo, poético, minimalista, sofisticado. NUNCA urgente ou agressivo. "
            "HASHTAGS: 20 tags otimizadas = 3 marca + 5 estilo + 5 nicho + 4 alcance + 3 local. "
            "Inclua sempre: #AuraDecore #Japandi #DecorMinimalista "
            "COPY STORY: versão curta (max 3 linhas) para o story com enquete ou CTA."
        ),
        agent=VERA,
        expected_output=(
            "Caption completa (legenda + hashtags), "
            "copy para story/enquete, "
            "sugestão de áudio/trilha."
        ),
    )
    task_feed = Task(
        description=(
            "Publique o conteúdo completo nos 3 CANAIS ESPELHADOS usando os resultados anteriores. "
            "1. Instagram Feed @auras.decore: FacebookPost (Instagram via Graph API) com imagem 1:1 + caption + hashtags. "
            "2. Instagram Story: post da versão story 9:16 (se gerada pelo ARTE). "
            "3. Facebook Página Comercial (ID 1111100822090245): FacebookPost com mesma imagem + caption simplificada. "
            "4. Facebook Perfil Pessoal (facebook.com/auras.decore): ESPELHAR o MESMO post da comercial/Instagram "
            "via Chrome MCP (perfil pessoal não tem API) — mesma imagem + mesma caption. "
            "Regra: tudo que vai para a comercial e o Instagram TAMBÉM vai para o perfil pessoal. "
            "Se publicação automática falhar por token expirado (FB_PAGE_TOKEN), "
            "entregue o pacote completo formatado: imagem URL + caption + hashtags + horário sugerido "
            "para Eduardo publicar manualmente via agendador (Later/Buffer/Meta Business Suite)."
        ),
        agent=FEED,
        expected_output=(
            "IDs dos posts publicados no Instagram, Facebook Comercial e confirmação do espelhamento no Perfil Pessoal, "
            "ou pacote completo para publicação manual com todos os assets organizados."
        ),
    )
    return Crew(
        agents=[NOX, ARTE, VERA, FEED],
        tasks=[task_nox, task_arte, task_vera, task_feed],
        process=Process.sequential,
        verbose=True,
    )


def build_store_update_crew(context: str) -> Crew:
    """Crew de enriquecimento da loja: THEO lista produtos, VERA escreve descrições, ARTE gera foto, THEO atualiza."""
    task_theo_list = Task(
        description=(
            "Liste os produtos ativos na loja Shopify. "
            "Use ShopifyProduct sem product_id para listar todos com ID e título. "
            f"Contexto: {context}"
        ),
        agent=THEO,
        expected_output="Lista de produtos com ID, título e status.",
    )
    task_vera = Task(
        description=(
            "Para CADA produto listado pelo THEO, escreva uma descrição HTML rica para Shopify:\n"
            "- <h2>: headline emocional japandi\n"
            "- <p>: parágrafo de 50-80 palavras (sensorial, biofílico)\n"
            "- <ul>: 4-5 bullets de características (material, dimensão, cuidado, uso)\n"
            "- <p>: chamada para ação suave\n"
            "Tom: premium, poético, japandi. Em português."
        ),
        agent=VERA,
        expected_output="Descrição HTML completa para cada produto.",
    )
    task_arte = Task(
        description=(
            "Para o produto MAIS IMPORTANTE da lista (maior potencial japandi), "
            "gere uma foto de produto profissional usando ImageGen:\n"
            "Prompt base: '[nome do produto], japandi minimalist product photo, "
            "natural wood surface, soft diffused light, ceramic texture, wabi-sabi aesthetic, "
            "premium e-commerce photography, clean background, ultra realistic'\n"
            "Formato: 800x800px. Filename: 'produto_hero'."
        ),
        agent=ARTE,
        expected_output="URL da foto de produto gerada para o produto principal.",
    )
    task_theo_update = Task(
        description=(
            "Atualize a loja Shopify com os resultados:\n"
            "1. Para cada produto: use ShopifyProduct com product_id e body_html da VERA\n"
            "2. Para o produto principal: adicione a imagem gerada pelo ARTE\n"
            "Confirme cada atualização."
        ),
        agent=THEO,
        expected_output="Confirmação de atualização de cada produto com novo body_html e imagem.",
    )
    return Crew(
        agents=[THEO, VERA, ARTE],
        tasks=[task_theo_list, task_vera, task_arte, task_theo_update],
        process=Process.sequential,
        verbose=True,
    )


def build_product_images_crew(products: list = None) -> Crew:
    """Missão diária: KAI prioriza, ARTE gera imagens profissionais, LUNA aprova, THEO sobe no Shopify.
    Meta: 5-7 produtos/dia com 1 capa + 2 lifestyle + fotos fornecedor até todos os 54 estarem completos."""
    context = f"Produtos a atualizar hoje: {products}" if products else "Priorizar produtos mais visitados e com maior margem"
    task_kai = Task(
        description=(
            "Defina a fila de produtos a atualizar HOJE com imagens profissionais. "
            "Selecione 5–7 produtos priorizando: (1) produtos minerados NEXUS com oportunidade ENTRAR AGORA, "
            "(2) produtos estrela (Vela Âmbar, Vaso Cerâmica), (3) produtos sem foto profissional. "
            f"Contexto: {context} "
            "Retorne lista ordenada com nome do produto, ID Shopify e tipo de imagem necessária."
        ),
        agent=KAI,
        expected_output="Lista priorizada de 5–7 produtos com ID Shopify e briefing de imagem para ARTE.",
    )
    task_arte = Task(
        description=(
            "Para CADA produto na fila do KAI, gere o pacote completo de imagens:\n"
            "1. CAPA PROFISSIONAL (800×800px WebP): prompt japandi — '[produto], japandi minimalist product photo, "
            "warm earth tones #B8793A, soft natural light, ceramic texture, clean background, "
            "wabi-sabi aesthetic, premium e-commerce photography, ultra realistic, 8K'\n"
            "2. FOTO LIFESTYLE 1 (800×800px): produto em ambiente japandi decorado — linho, planta seca, madeira\n"
            "3. FOTO LIFESTYLE 2 (800×800px): close-up textura/material — sensação tátil premium\n"
            "Gere via Pollinations.ai (rápido) → se baixa qualidade, regerar via Google Imagen (Gemini API). "
            "Nomear arquivos: [produto-slug]_capa.webp, [produto-slug]_lifestyle1.webp, [produto-slug]_lifestyle2.webp\n"
            "Adicionar logo Aura watermark sutil (15% opacity, canto inferior direito) via Canva Pro MCP."
        ),
        agent=ARTE,
        expected_output="URLs/paths das imagens geradas (capa + 2 lifestyle) para cada produto, prontas para revisão da LUNA.",
    )
    task_luna = Task(
        description=(
            "Revise e aprove CADA imagem gerada pelo ARTE. Critérios obrigatórios:\n"
            "✅ Paleta correta (#B8793A, #F5F0EB, #EDE5D8, #7A9076)\n"
            "✅ Fundo neutro sem elementos discordantes\n"
            "✅ Logo Aura visível mas sutil (15% opacity)\n"
            "✅ Resolução mínima 800×800px, formato WebP\n"
            "✅ Estética japandi consistente\n"
            "Se REPROVADA: devolver para ARTE com feedback específico de prompt. "
            "Se APROVADA: passar para THEO com ordem de exibição definida:\n"
            "Posição 1: capa profissional | Posição 2: lifestyle 1 | Posição 3: lifestyle 2 | Posição 4+: fornecedor"
        ),
        agent=LUNA,
        expected_output="Lista de imagens aprovadas por produto com ordem de exibição para THEO subir no Shopify.",
    )
    task_theo = Task(
        description=(
            "Suba TODAS as imagens aprovadas pela LUNA no Shopify para cada produto:\n"
            "1. Use Shopify Admin API / ShopifyProduct com product_id para cada produto\n"
            "2. Upload das imagens na ordem definida pela LUNA (capa primeiro)\n"
            "3. Converter para WebP se necessário (PageSpeed)\n"
            "4. Definir alt text SEO: '[nome produto] japandi minimalista | Aura Decore'\n"
            "5. Confirmar upload e registrar produto como ATUALIZADO no vault\n"
            "Reportar: lista de produtos atualizados hoje + contador acumulado (X/54 completos)."
        ),
        agent=THEO,
        expected_output="Confirmação de upload para cada produto, contador total (X/54 produtos com imagens profissionais completas).",
    )
    return Crew(
        agents=[KAI, ARTE, LUNA, THEO],
        tasks=[task_kai, task_arte, task_luna, task_theo],
        process=Process.sequential,
        verbose=True,
    )


def build_shopify_dev_crew(sprint: str = "") -> Crew:
    """Crew de desenvolvimento Shopify: DEV audita, ARTE gera hero, VERA escreve copy, DEV publica."""
    season = get_current_season()
    season_info = f"Estação atual: {season.get('nome', 'geral')} (slug: {season.get('slug', '')})"

    task_audit = Task(
        description=(
            f"Audite a loja Shopify atual com ShopifyDevReport. {season_info}. "
            f"Sprint/foco: {sprint if sprint else 'melhoria geral de conversão e design'}. "
            "Verifique: tema ativo, CSS sazonal aplicado, announcement bar, hero banner, "
            "coleção destaque, velocidade e UX mobile. "
            "Liste exatamente o que precisa ser atualizado com prioridade."
        ),
        agent=DEV,
        expected_output="Relatório de auditoria com lista priorizada de melhorias necessárias.",
    )
    task_hero_image = Task(
        description=(
            f"Gere a imagem hero para a estação: {season.get('nome', 'atual')}. "
            f"Use o prompt: '{season.get('prompt_hero', 'japandi minimalist home decor, seasonal, warm light')}'. "
            "Dimensões: 1200x628px (hero banner). Filename: 'hero_sazonal'. "
            "Este banner vai na seção principal da loja."
        ),
        agent=ARTE,
        expected_output="URL do hero banner gerado e caminho local do arquivo.",
    )
    task_copy = Task(
        description=(
            f"Escreva os textos sazonais para a loja. Estação: {season.get('nome', 'atual')}. "
            f"Entregue: (1) Hero headline (máx 50 chars): baseado em '{season.get('hero_headline', '')}', "
            f"(2) Hero subheadline (máx 100 chars): '{season.get('hero_subheadline', '')}', "
            f"(3) Announcement bar (máx 80 chars): '{season.get('announcement', '')}', "
            "(4) Título da coleção destaque. "
            "Tom: sofisticado, japandi, acolhedor. Em português."
        ),
        agent=VERA,
        expected_output="Headline, subheadline, announcement e título de coleção para a estação atual.",
    )
    task_deploy = Task(
        description=(
            "Aplique todas as melhorias na loja Shopify com base na auditoria, hero e copy:\n"
            "1. Use ShopifyCSSInjector para aplicar CSS sazonal com paleta da estação\n"
            "2. Use ShopifyAnnouncement para atualizar o banner de anúncio\n"
            "3. Use ShopifyThemeSettings para atualizar hero headline e subheadline\n"
            "4. Use ShopifyCollection para criar/atualizar coleção sazonal\n"
            "Aplique primeiro no staging (ShopifyPublishTheme com action=publish_staging), "
            "depois publique no live (action=publish_live). "
            "Reporte todas as mudanças aplicadas."
        ),
        agent=DEV,
        expected_output="Confirmação de todas as mudanças aplicadas com URLs e status de publicação.",
    )
    return Crew(
        agents=[DEV, ARTE, VERA],
        tasks=[task_audit, task_hero_image, task_copy, task_deploy],
        process=Process.sequential,
        verbose=True,
    )


def build_seasonal_update_crew(season_slug: str = "") -> Crew:
    """Crew de atualização sazonal completa: detecta estação, gera visuais, atualiza toda a loja."""
    season = get_current_season()
    slug = season_slug or season.get("slug", "geral")

    task_detect = Task(
        description=(
            "Use SeasonDetector para identificar a estação atual. "
            "Retorne: nome da estação, paleta de cores, produtos em foco, "
            "CSS accent color e todo o contexto sazonal para os próximos agentes."
        ),
        agent=DEV,
        expected_output="Dados completos da estação atual: nome, slug, paleta, produtos, CSS, prompt de hero.",
    )
    task_visuals = Task(
        description=(
            f"Gere o pacote visual completo para a estação '{slug}':\n"
            "1. Hero banner 1200x628: cena de decoração japandi sazonal\n"
            "2. Post Instagram 1080x1080: produto destaque da estação\n"
            "3. Story 1080x1920: lifestyle japandi com ambiente sazonal\n"
            "Use o prompt sazonal do SeasonDetector para cada imagem. "
            "Filenames: hero_sazonal, post_sazonal, story_sazonal."
        ),
        agent=ARTE,
        expected_output="URLs e caminhos das 3 imagens sazonais geradas.",
    )
    task_all_copy = Task(
        description=(
            f"Escreva todo o conteúdo textual sazonal para '{slug}':\n"
            "1. Hero headline e subheadline (loja)\n"
            "2. Announcement bar\n"
            "3. Descrição da coleção sazonal\n"
            "4. Caption Instagram do post sazonal + 20 hashtags\n"
            "5. Caption do story + CTA\n"
            "6. Título e meta-description para SEO\n"
            "Tom: premium japandi, emocional, em português."
        ),
        agent=VERA,
        expected_output="Todos os textos sazonais: loja, redes sociais e SEO.",
    )
    task_deploy_all = Task(
        description=(
            "Aplique a atualização sazonal COMPLETA na loja:\n"
            "1. ShopifyCSSInjector — inject CSS accent color sazonal\n"
            "2. ShopifyThemeSettings — hero headline + subheadline\n"
            "3. ShopifyAnnouncement — announcement bar sazonal\n"
            "4. ShopifyCollection — criar coleção sazonal com handle baseado no slug\n"
            "5. ShopifyPublishTheme — staging primeiro, depois live\n"
            "Reporte: o que mudou, o que ficou igual, e próximas ações recomendadas."
        ),
        agent=DEV,
        expected_output="Relatório completo de atualização sazonal com todas as mudanças aplicadas.",
    )
    return Crew(
        agents=[DEV, ARTE, VERA],
        tasks=[task_detect, task_visuals, task_all_copy, task_deploy_all],
        process=Process.sequential,
        verbose=True,
    )


def build_conversion_crew(context: str = "") -> Crew:
    """Crew de otimização de conversão: DEV audita UX, SOL analisa dados, VERA melhora copy, DEV implementa."""
    task_ux_audit = Task(
        description=(
            f"Audite a loja focando em conversão (CRO). Contexto: {context}. "
            "Use ShopifyDevReport para verificar: "
            "(1) CTAs visíveis e atrativos, "
            "(2) prova social (reviews, contador de vendas), "
            "(3) urgência (estoque limitado, frete grátis), "
            "(4) trust badges, "
            "(5) velocidade mobile, "
            "(6) checkout simplificado. "
            "Pontue cada item de 0-10 e liste as 3 melhorias de maior impacto."
        ),
        agent=DEV,
        expected_output="Auditoria CRO com pontuação por item e top 3 melhorias prioritárias.",
    )
    task_data = Task(
        description=(
            "Com base na auditoria do DEV, analise os dados de vendas atuais. "
            "Identifique: produto com maior taxa de abandono de carrinho, "
            "página com maior bounce rate, horário de pico de visitas. "
            "Recomende: qual produto promover, qual desconto testar, "
            "qual elemento de urgência adicionar."
        ),
        agent=SOL,
        expected_output="Análise de dados com produto prioritário, recomendação de desconto e elemento de urgência.",
    )
    task_cro_copy = Task(
        description=(
            "Reescreva os elementos de copy de alta conversão:\n"
            "1. Headline do produto mais importante (gatilho emocional + benefício)\n"
            "2. Botão de compra (além de 'Comprar', teste variações)\n"
            "3. Frase de urgência/escassez (natural, não agressiva)\n"
            "4. Trust badge copy (garantia, frete, devolução)\n"
            "5. Announcement bar com oferta especial\n"
            "Tom: persuasivo mas sofisticado, não agressivo. Japandi lifestyle."
        ),
        agent=VERA,
        expected_output="Copy CRO completa: headline, CTA, urgência, trust badges, announcement.",
    )
    task_implement = Task(
        description=(
            "Implemente as melhorias de conversão na loja:\n"
            "1. ShopifyThemeSettings — atualizar hero com nova headline\n"
            "2. ShopifyAnnouncement — oferta especial da VERA\n"
            "3. ShopifyCSSInjector — destacar CTA buttons com cor accent\n"
            "4. ShopifyPublishTheme — aplicar mudanças no live\n"
            "Documente cada mudança implementada e o impacto esperado em conversão."
        ),
        agent=DEV,
        expected_output="Confirmação das melhorias CRO implementadas com impacto esperado.",
    )
    return Crew(
        agents=[DEV, SOL, VERA],
        tasks=[task_ux_audit, task_data, task_cro_copy, task_implement],
        process=Process.sequential,
        verbose=True,
    )


def build_financial_crew(context: str) -> Crew:
    """Crew financeira: GUARD analisa caixa, MEI e ROAS. Consulta REX."""
    task_guard = Task(
        description=(
            f"Análise financeira semanal Aura Decore. Contexto: {context}. "
            "Verifique: (1) faturamento acumulado MEI vs limite R$81k, "
            "(2) ROAS da semana vs meta 2x, (3) margem por produto vs mínimo 35%, "
            "(4) caixa disponível vs reserva mínima R$500, "
            "(5) chargebacks vs limite 1%. Emita alerta: VERDE/AMARELO/VERMELHO/PRETO."
        ),
        agent=GUARD,
        expected_output="Relatório financeiro com status MEI, alerta de cor, e 1 ação prioritária.",
    )
    task_rex_guard = Task(
        description="Com base no alerta do GUARD, informe o ROAS atual e se o orçamento de ads deve ser reduzido, mantido ou escalado.",
        agent=REX,
        expected_output="ROAS atual e recomendação de budget: reduzir/manter/escalar com percentual.",
    )
    return Crew(
        agents=[GUARD, REX],
        tasks=[task_guard, task_rex_guard],
        process=Process.sequential,
        verbose=True,
    )


def build_cx_crew(customer_issue: str) -> Crew:
    """Crew de atendimento: LENA resolve, GUARD aprova reembolso se > R$200."""
    task_lena = Task(
        description=(
            f"Resolva o seguinte problema de cliente usando o framework HERO: {customer_issue}. "
            "Identifique o tipo (rastreamento/troca/reembolso/defeito/cancelamento/dúvida). "
            "Escreva a resposta completa para o cliente em português caloroso. "
            "Se reembolso > R$200, informe que precisa de aprovação do GUARD."
        ),
        agent=LENA,
        expected_output="Resposta completa ao cliente + tipo de ocorrência + ação interna necessária.",
    )
    return Crew(
        agents=[LENA],
        tasks=[task_lena],
        process=Process.sequential,
        verbose=True,
    )


def build_mining_crew(context: str) -> Crew:
    """Crew de mineração: NEXUS pesquisa no AliExpress/Dropi, KAI valida margem, VERA prepara copy."""
    task_nexus = Task(
        description=(
            f"Mine 5 produtos em tendência para Aura Decore. Contexto: {context}\n\n"
            "INSTRUÇÕES:\n"
            "1. Use AliExpressSearch para buscar: 'japandi ceramic vase', 'wabi-sabi home decor', "
            "'linen cushion minimalist', 'bamboo tray zen', 'dried pampas grass decor'\n"
            "2. Use TrendSearch para verificar: 'decoracao japandi brasil 2025'\n"
            "3. Use DropisSearch para checar disponibilidade nacional de cada produto encontrado\n"
            "4. Para cada produto liste: nome, URL AliExpress, preço custo USD estimado, "
            "disponível no Dropi (sim/não), score neuroarquitetura 0-10 "
            "(material natural +2, calma visual +2, biofilia +2, tendência +2, margem estimada +2)\n"
            "5. Priorize produtos com score >= 7 e custo < $15 USD"
        ),
        agent=NEXUS,
        expected_output=(
            "Lista de 5 produtos com: nome, URL AliExpress, preço USD, "
            "Dropi disponível (sim/não), score neuroarquitetura (0-10) com justificativa."
        ),
    )
    task_kai_nexus = Task(
        description=(
            "Valide os 5 produtos minerados pelo NEXUS:\n"
            "1. Use MarginCalculator para calcular margem de cada produto "
            "(custo USD do NEXUS, câmbio 5.80, markup 2.5x)\n"
            "2. Use DropisSearch para confirmar estoque nacional\n"
            "3. Decida: APROVADO / REPROVADO / AGUARDAR\n"
            "   - APROVADO: margem real >= 35% + score >= 7\n"
            "   - REPROVADO: margem < 35% ou concorrência alta demais\n"
            "   - AGUARDAR: margem ok mas sem estoque nacional ainda\n"
            "Selecione o TOP 3 para a Aura Decore."
        ),
        agent=KAI,
        expected_output=(
            "TOP 3 produtos: status (APROVADO/REPROVADO/AGUARDAR), "
            "margem real %, preço custo BRL, preço sugerido BRL, justificativa."
        ),
    )
    task_vera_nexus = Task(
        description=(
            "Para os produtos APROVADOS pelo KAI, escreva copy para a loja Shopify:\n"
            "1. Headline do produto (max 60 chars) — emotivo, japandi\n"
            "2. Subheadline (max 120 chars) — benefício funcional + sensorial\n"
            "3. 3 bullets de produto (cada um max 80 chars)\n"
            "4. Tag de coleção sugerida (ex: 'Wabi-Sabi', 'Zen Living', 'Natural Home')\n"
            "Tom: calmo, premium, evoca tranquilidade e conexão com a natureza."
        ),
        agent=VERA,
        expected_output="Copy completo para cada produto aprovado: headline, subheadline, 3 bullets, tag de coleção.",
    )
    return Crew(
        agents=[NEXUS, KAI, VERA],
        tasks=[task_nexus, task_kai_nexus, task_vera_nexus],
        process=Process.sequential,
        verbose=True,
    )


def build_weekly_crew(context: str) -> Crew:
    task_ive = Task(
        description=f"Analise o contexto semanal e dê 3 diretrizes estratégicas para a equipe. Contexto: {context}",
        agent=IVE,
        expected_output="3 diretrizes estratégicas em português, cada uma em 1 frase.",
    )
    task_rex = Task(
        description="Com base nas diretrizes da IVE, sugira 1 ação de otimização de campanhas Meta Ads.",
        agent=REX,
        expected_output="1 ação de otimização com justificativa de dados.",
    )
    task_kai = Task(
        description="Avalie o portfólio atual e recomende 1 produto para pausar e 1 para destacar.",
        agent=KAI,
        expected_output="1 produto para pausar e 1 para destacar, com motivo.",
    )
    task_vera = Task(
        description="Escreva 1 linha de copy para o produto destaque escolhido pelo KAI.",
        agent=VERA,
        expected_output="1 linha de copy de até 10 palavras.",
    )
    task_luna = Task(
        description=(
            "Com base no produto destaque da semana escolhido pelo KAI, crie um briefing visual completo: "
            "paleta de cores, tipografia recomendada, formato de banner (dimensões), e descrição do conceito visual. "
            "Garanta consistência com o brand kit terra/offwhite da Aura Decore."
        ),
        agent=LUNA,
        expected_output="Briefing visual: paleta, tipografia, formato banner e conceito em até 4 linhas.",
    )
    task_nox = Task(
        description=(
            "Crie o roteiro de 1 Reel de 30 segundos para o produto destaque da semana. "
            "Inclua: hook de abertura (0-3s), desenvolvimento (3-25s) e CTA final (25-30s). "
            "Use o conceito visual da LUNA e o ângulo de copy da VERA."
        ),
        agent=NOX,
        expected_output="Roteiro completo do Reel com hook, desenvolvimento e CTA.",
    )
    task_echo = Task(
        description=(
            "Audite a performance da equipe nesta rodada: avalie a qualidade de cada entrega "
            "(IVE, REX, KAI, VERA, LUNA, NOX) e dê um score geral de 0 a 10 com 1 sugestão de melhoria por agente."
        ),
        agent=ECHO,
        expected_output="Score geral (0-10), scores individuais e 1 sugestão por agente.",
    )

    return Crew(
        agents=[IVE, REX, KAI, VERA, LUNA, NOX, ECHO],
        tasks=[task_ive, task_rex, task_kai, task_vera, task_luna, task_nox, task_echo],
        process=Process.sequential,
        verbose=True,
    )


def build_content_crew(product: str, copy_angle: str) -> Crew:
    """Crew focada em criação de conteúdo premium: VERA + LUNA + NOX — alinhada ao Social Media Creative Hub."""
    task_vera = Task(
        description=(
            f"Escreva copy de alta conversão para '{product}' com ângulo: {copy_angle}. "
            "Siga o brand voice Aura Decore: calmo, poético, minimalista, sofisticado. "
            "Entregue: headline (máx 8 palavras), subheadline (1 linha), 3 bullets de benefício emocional, "
            "caption Instagram PT-BR (150-200 chars) + CTA 'link na bio', 15 hashtags otimizadas. "
            "Tom: nunca urgente, nunca agressivo. Aspira estilo de vida Japandi."
        ),
        agent=VERA,
        expected_output="Headline, subheadline, 3 bullets, caption IG + hashtags.",
    )
    task_luna = Task(
        description=(
            f"Crie briefing visual completo para criativo de '{product}' seguindo o Social Hub brand kit. "
            "Paleta: terra #B8793A + areia #EDE5D8 + off-white #F5F0EB. "
            "Fontes: Cormorant Garamond (headlines) + DM Sans (body). "
            "Especifique: 3 prompts Pollinations para ImageGen (feed 1080x1080, story 1080x1920, "
            "thumbnail reel 1080x1080), composição visual (produto como ponto focal, wabi-sabi, "
            "luz natural dourada, elementos naturais: linho, madeira, cerâmica). "
            "Use DesignBrief + ImageGen para gerar as imagens."
        ),
        agent=LUNA,
        expected_output="3 prompts Pollinations + URLs das imagens geradas + especificação visual.",
    )
    task_nox = Task(
        description=(
            f"Crie roteiro completo de Reel 30s para '{product}' usando copy da VERA e visual da LUNA. "
            "Siga estrutura do Social Hub: "
            "  HOOK (0-3s): pergunta impactante ou visual hipnótico + texto overlay provocativo "
            "  CORPO (3-22s): 4 cenas com timestamps, produto integrado naturalmente, narrativa Japandi "
            "  CTA (22-30s): texto overlay clean + logo Aura + call to action suave "
            "  LEGENDA: adapte a copy da VERA para formato Instagram "
            "  ÁUDIO: sugira música (lo-fi ambient / piano / ASMR) "
            "Entregue roteiro pronto para produção, sem necessidade de edição."
        ),
        agent=NOX,
        expected_output="Roteiro completo com hook/corpo/CTA + legenda + hashtags + sugestão de áudio.",
    )
    return Crew(
        agents=[VERA, LUNA, NOX],
        tasks=[task_vera, task_luna, task_nox],
        process=Process.sequential,
        verbose=True,
    )


def build_sales_crew(context: str) -> Crew:
    """Crew de vendas/CRO: SOL recupera carrinhos, REX ajusta ads, VERA escreve copy de e-mail."""
    task_sol = Task(
        description=(
            f"Analise contexto de vendas: {context}. "
            "Identifique gargalo do funil (abandono carrinho? checkout? CAC alto?). "
            "Recomende 1 ação CRO: bundle, upsell, cupom estratégico, sequência email D+1/D+3/D+7 "
            "ou ajuste de copy no checkout. Estime impacto em % na conversão e no ticket médio."
        ),
        agent=SOL,
        expected_output="Diagnóstico de funil + 1 ação CRO + impacto estimado em conversão e ticket.",
    )
    task_vera_sol = Task(
        description="Escreva copy de email de recuperação de carrinho baseado na ação do SOL: assunto + corpo (3 parágrafos) + CTA.",
        agent=VERA,
        expected_output="Email completo: subject line + corpo + CTA.",
    )
    task_rex_sol = Task(
        description="Sugira 1 ajuste de retargeting Meta Ads para suportar a ação CRO do SOL (público customizado de carrinho abandonado, criativo específico).",
        agent=REX,
        expected_output="Configuração de público + criativo recomendado + budget sugerido.",
    )
    return Crew(
        agents=[SOL, VERA, REX],
        tasks=[task_sol, task_vera_sol, task_rex_sol],
        process=Process.sequential,
        verbose=True,
    )


def build_marketing_crew(theme: str) -> Crew:
    """Crew de marketing completa: NOX planeja semana com Social Hub, VERA escreve copy premium, ZARA engaja comunidade."""
    task_nox = Task(
        description=(
            f"Execute o planejamento semanal de marketing com tema: '{theme}'. "
            "Crie calendário de 7 dias baseado no Social Media Creative Hub: "
            "Distribuição por pilares: Lifestyle 40% / Produto 30% / Educação 15% / Bastidores 10% / Social Proof 5%. "
            "Mix por tipo: Reels (4), Carrosseis (3), Stories diários (7), Foto (1). "
            "Para cada post defina: dia, horário (10h/14h/19h), tipo, pilar, script_id do hub (1-8 se for Reel), "
            "produto destaque, hook principal e objetivo (branding/conversão/engajamento/autoridade). "
            "Inclua pelo menos 1 post que use cada um dos 4 produtos Aura Decore na semana."
        ),
        agent=NOX,
        expected_output="Calendário 7 dias completo: data, hora, tipo, pilar, script vinculado, produto, hook, objetivo.",
    )
    task_vera_mkt = Task(
        description=(
            f"Para os 7 posts do calendário NOX com tema '{theme}', escreva copy completa: "
            "Caption PT-BR: poética, calma, minimalista (voice Aura Decore). Máx 200 chars. "
            "15 hashtags por post: 3 marca (#AuraDecore + 2) + 5 estilo Japandi + 5 nicho decoração + 2 alcance geral. "
            "Para posts de Reel: inclua CTA de legenda alinhado ao script (ex: 'Salva esse reel ✧'). "
            "Para carrosseis: inclua CTA de deslizar ('Deslize para ver ↓'). "
            "Para stories: texto curto (<50 chars) + sugestão de enquete ou reação."
        ),
        agent=VERA,
        expected_output="7 captions completas + 15 hashtags por post + copy de story.",
    )
    task_zara_mkt = Task(
        description=(
            "Com base no calendário semanal, crie plano de engajamento da comunidade: "
            "1. Para cada post: 3 ações (contas para marcar, pergunta para stories, CTA de comentário). "
            "2. DM de boas-vindas para novos seguidores (texto warm, Japandi vibe). "
            "3. Resposta padrão para comentários de 'preço?' e 'como comprar?'. "
            "4. Identifique 3 micro-influencers de decoração brasileira para collab orgânica "
            "   (perfis com 5K-50K seguidores, estética alinhada, sem custo). "
            "5. Sugestão de hashtags challenge que @auradecore poderia criar para UGC."
        ),
        agent=ZARA,
        expected_output="Plano de engagement por post + DM boas-vindas + respostas padrão + 3 micro-influencers + ideia de challenge.",
    )
    return Crew(
        agents=[NOX, VERA, ZARA],
        tasks=[task_nox, task_vera_mkt, task_zara_mkt],
        process=Process.sequential,
        verbose=True,
    )


def build_seo_crew(keyword: str) -> Crew:
    """Crew de SEO: MIRA pesquisa keywords, VERA escreve copy SEO, THEO implementa no Shopify."""
    task_mira = Task(
        description=(
            f"Pesquise keyword '{keyword}'. Entregue: volume mensal estimado, dificuldade SEO (0-100), "
            "3 variações de cauda longa relacionadas, 2 perguntas frequentes ('People Also Ask'), "
            "e análise dos top 3 concorrentes no SERP."
        ),
        agent=MIRA,
        expected_output="Relatório SEO completo da keyword.",
    )
    task_vera_seo = Task(
        description="Com base no relatório do MIRA, escreva: title tag (60 chars), meta description (155 chars), H1, e 1 parágrafo introdutório SEO-friendly para a página.",
        agent=VERA,
        expected_output="Title + meta + H1 + parágrafo intro.",
    )
    task_theo_seo = Task(
        description="Liste passos técnicos no Shopify para implementar a otimização SEO: onde inserir cada elemento, schema markup necessário (Product, BreadcrumbList), ajustes de URL slug.",
        agent=THEO,
        expected_output="Checklist técnico Shopify passo-a-passo.",
    )
    return Crew(
        agents=[MIRA, VERA, THEO],
        tasks=[task_mira, task_vera_seo, task_theo_seo],
        process=Process.sequential,
        verbose=True,
    )


# ── Agentes de Neuromarketing (adicionados 2026-06-16) ───────────────────────────

# Import engine (graceful — não quebra se arquivo ausente)
try:
    from neuromarketing_engine import (
        build_neuro_prompt, get_template, score_lead,
        generate_promo_blast, DESIRE_MAP, PAIN_MAP,
        COPY_FRAMEWORKS, NEURO_TRIGGERS,
    )
    _NEURO_ENGINE_OK = True
except Exception:
    _NEURO_ENGINE_OK = False

NEURO = make_agent(
    "NEURO", "Copy Neuromarketing · Estrategista de Desejo",
    "Criar copy sutil e irresistível usando neuromarketing: ativar desejo, nomear dores e construir pontes emocionais para ação.",
    (
        "NEURO é o estrategista de copy mais sofisticado da Aura Decore. "
        "Domina 6 desejos nucleares da Ana Clara (status, pertencimento, segurança, conforto, beleza, controle) "
        "e 5 dores emocionais primárias (caos, genérico, estresse, vergonha, paralisia). "
        "Aplica frameworks de copy com maestria: "
        "PAS (Problem→Agitate→Solve) para prospects frios, "
        "BAB (Before→After→Bridge) para contraste emocional, "
        "AIDA (Attention→Interest→Desire→Action) para anúncios, "
        "SBO (Story→Bridge→Offer) para nurturing quente, "
        "Prova Social quando há UGC disponível. "
        "Gatilhos neurológicos usados com SUTILEZA: escassez real (não fake), perda, autoridade, identidade, novidade. "
        "NUNCA usa linguagem de vendedor agressivo. "
        "A copy da Aura é como uma amiga eloquente que entende de design — não um vendedor de telemarketing. "
        "Calibra o tom pelo score do lead: frio → educativo/inspiracional, morno → curiosidade/escassez suave, "
        "quente → pertencimento/identidade, VIP → exclusividade/gratidão. "
        "Sincroniza com VERA (copy produto), SOL (CRO/conversão) e LENA (atendimento). "
        "Meta: aumentar CTR de mensagens WhatsApp em 40% e taxa de conversão pós-nutrição em 25%."
    ),
)

PROMO = make_agent(
    "PROMO", "Disparos Promocionais · Lead Nurturing",
    "Orquestrar sequências de promoção e ofertas para leads, segmentando por temperatura e comportamento.",
    (
        "PROMO é o maestro de disparos promocionais da Aura Decore. "
        "Segmenta leads em frio/morno/quente/VIP e define a sequência de nurturing correta para cada grupo. "
        "Sequências gerenciadas: "
        "novo_lead (5 touchpoints: D0→D2→D5→D7→D14), "
        "pos_compra (3 touchpoints: imediato→D7→D14 com upsell), "
        "win_back (3 touchpoints: D0→D3→D7 para inativos 60+d). "
        "Calendário de flash sales: máximo 2/mês para não saturar a base. "
        "Regras de frequência: máximo 1 mensagem a cada 48h por lead. "
        "Janela de envio: 09h-21h (horário Brasília). "
        "Cupons por temperatura: frio=AURA10(10%), morno=AURA10 ou AURAVIP15, quente/VIP=AURAVIP15(15%) ou AURAEMBAIXADORA20(20%). "
        "Desengajamento: após 3 mensagens sem resposta, pausar lead por 30 dias. "
        "Integra com NEURO para copy e com SOL para dados de conversão. "
        "KPIs: open rate WhatsApp >60%, conversão pós-disparo >5%, opt-out <2%."
    ),
)


def build_neuromarketing_crew(lead_context: dict) -> Crew:
    """Crew de neuromarketing: NEURO elabora copy estratégico, VERA refina texto, SOL define oferta, PROMO executa disparo."""
    nome     = lead_context.get("nome", "cliente")
    produto  = lead_context.get("produto", "")
    score    = lead_context.get("score", "morno")
    stage    = lead_context.get("stage", "morno_produto")

    task_neuro = Task(
        description=(
            f"Desenvolva a estratégia de copy neuromarketing para este lead:\n"
            f"- Nome: {nome}\n"
            f"- Score (temperatura): {score}\n"
            f"- Produto de interesse: {produto}\n"
            f"- Estágio do funil: {stage}\n\n"
            "Entregue:\n"
            "1. Desejo nuclear primário ativado (dos 6: status/pertencimento/segurança/conforto/beleza/controle)\n"
            "2. Dor emocional endereçada (dos 5: caos/genérico/estresse/vergonha/paralisia)\n"
            "3. Framework escolhido (PAS/BAB/AIDA/SBO/Prova Social) e justificativa\n"
            "4. Gatilho neurológico aplicado (escassez/urgência/perda/autoridade/identidade/reciprocidade)\n"
            "5. Mensagem WhatsApp final: máximo 4 parágrafos curtos, 100 palavras, tom Ana Clara, "
            "nunca pressão explícita, cupom embutido naturalmente quando pertinente.\n"
            "6. Variação A/B: versão alternativa com abordagem diferente (15-20% variação de tom)."
        ),
        agent=NEURO,
        expected_output=(
            "Estratégia completa: desejo + dor + framework + gatilho + "
            "mensagem WhatsApp principal + variação A/B."
        ),
    )
    task_vera = Task(
        description=(
            "Refine a mensagem criada pelo NEURO. Garanta:\n"
            "- Voz 100% Aura Decore: calma, elegante, próxima\n"
            "- Português BR natural, sem anglicismos forçados\n"
            "- Emoji com moderação (máx 2, só se amplificam emoção)\n"
            "- Link auradecore.com.br posicionado naturalmente\n"
            "- Cupom em negrito quando presente\n"
            "- CTA final como sugestão, não ordem\n"
            "Retorne a versão refinada da mensagem principal e da variação A/B."
        ),
        agent=VERA,
        expected_output="Versão principal refinada + variação A/B refinada, prontas para disparo.",
    )
    task_sol = Task(
        description=(
            f"Com base no score '{score}' e stage '{stage}', defina a oferta comercial:\n"
            "1. Qual cupom usar (AURA10 / AURAVIP15 / AURAEMBAIXADORA20 / nenhum)?\n"
            "2. Há produto complementar para sugerir (cross-sell/upsell)?\n"
            "3. Há urgência real (estoque baixo? promoção com prazo)?\n"
            "4. Próximo touchpoint: quando enviar a próxima mensagem se não houver resposta?\n"
            "5. Critério de conversão: o que conta como sucesso nesse disparo?\n"
            "Retorne essas decisões como JSON estruturado."
        ),
        agent=SOL,
        expected_output=(
            "JSON: {cupom, produto_complementar, urgencia_real, proximo_touchpoint_dias, "
            "criterio_conversao, score_esperado_conversao}"
        ),
    )
    task_promo = Task(
        description=(
            "Monte o pacote final de disparo com os insumos de NEURO, VERA e SOL:\n"
            "1. Mensagem final (versão A — principal)\n"
            "2. Mensagem B (variação teste)\n"
            "3. Sequência completa: quando enviar cada mensagem (D0, D+N)\n"
            "4. Regras de pausa: se lead responder, pausar sequência automática\n"
            "5. Métricas para acompanhar: taxa de resposta, cliques no link, conversão\n"
            "6. Instrução para o n8n: payload JSON pronto para o webhook /whatsapp/send\n\n"
            "Formato do payload n8n:\n"
            "{\n"
            "  \"phone\": \"{phone}\",\n"
            "  \"message\": \"[mensagem final]\",\n"
            "  \"variant\": \"A\",\n"
            "  \"schedule_next\": {\"dias\": N, \"stage\": \"next_stage\"}\n"
            "}"
        ),
        agent=PROMO,
        expected_output=(
            "Pacote completo de disparo: msg A + msg B + sequência + regras de pausa + "
            "payload JSON para n8n."
        ),
    )
    return Crew(
        agents=[NEURO, VERA, SOL, PROMO],
        tasks=[task_neuro, task_vera, task_sol, task_promo],
        process=Process.sequential,
        verbose=True,
    )


def build_promo_blast_crew(
    colecao: str = "Japandi Premium",
    desconto: int = 15,
    cupom: str = "AURAVIP15",
    n_produtos: int = 5,
    hora_fim: str = "23h59",
) -> Crew:
    """Crew de flash sale: NEURO cria copy de urgência, VERA refina, PROMO gera payload de massa para n8n."""
    task_neuro_blast = Task(
        description=(
            f"Crie copy de flash sale para disparo em massa (base de clientes Aura Decore).\n"
            f"Parâmetros:\n"
            f"- Coleção: {colecao}\n"
            f"- Desconto: {desconto}% OFF\n"
            f"- Cupom: {cupom}\n"
            f"- Produtos na oferta: {n_produtos} itens\n"
            f"- Válido até: {hora_fim} hoje\n\n"
            "Entregue:\n"
            "1. Versão QUENTE (para clientes que já compraram): foco em exclusividade + gratidão\n"
            "2. Versão MORNA (para quem visitou mas não comprou): foco em escassez + oportunidade\n"
            "3. Versão FRIA (newsletter/novo cadastro): foco em descoberta + prova social\n"
            "Regras: máx 80 palavras/versão, sem fake urgency, tom Aura Decore, cupom em destaque."
        ),
        agent=NEURO,
        expected_output="3 versões de copy (quente/morna/fria) para flash sale.",
    )
    task_vera_blast = Task(
        description=(
            "Refine as 3 versões de copy do NEURO para o flash sale. "
            "Garanta coerência de voz Aura em todas. "
            "Adicione emoji estratégico (⚡ para urgência, 🌿 para marca, 🎁 para oferta). "
            "Versão final deve ter: linha de abertura impactante + corpo + cupom em negrito + link. "
            "Retorne as 3 versões refinadas prontas para WhatsApp."
        ),
        agent=VERA,
        expected_output="3 versões refinadas: quente, morna, fria — prontas para disparo.",
    )
    task_promo_blast = Task(
        description=(
            "Prepare o pacote completo de flash sale para execução pelo n8n:\n"
            "1. Segmentação da base: quente (compraram nos últimos 30d), morna (visitou 7-30d), fria (resto)\n"
            "2. Payload JSON para cada segmento:\n"
            "   { \"segment\": \"quente|morna|fria\", \"message\": \"...\", \"cupom\": \"...\", "
            "     \"validade_horas\": 24 }\n"
            "3. Janela de disparo: quente às 10h, morna às 12h, fria às 15h (evitar pico de respostas simultâneas)\n"
            "4. Critério de sucesso: >5% de respostas ou cliques rastreados\n"
            "5. Regra de opt-out: se cliente responder PARA ou NÃO QUERO, remover da lista\n"
            "Retorne o JSON final pronto para o webhook n8n /promo/blast."
        ),
        agent=PROMO,
        expected_output=(
            "JSON de disparo com 3 segmentos, horários escalonados, payloads prontos e critérios de sucesso."
        ),
    )
    return Crew(
        agents=[NEURO, VERA, PROMO],
        tasks=[task_neuro_blast, task_vera_blast, task_promo_blast],
        process=Process.sequential,
        verbose=True,
    )


def build_automation_crew(workflow_goal: str) -> Crew:
    """Crew de automação: PIPE arquiteta o workflow n8n, THEO valida integrações."""
    task_pipe = Task(
        description=(
            f"Projete um workflow n8n para: {workflow_goal}. "
            "Liste: (1) trigger (webhook/cron/manual), (2) nodes necessários (HTTP request, switch, code, etc), "
            "(3) integrações (Shopify, Z-API, AppMax, vault Obsidian, API agente), "
            "(4) tratamento de erro + retry. Entregue o esqueleto JSON do workflow."
        ),
        agent=PIPE,
        expected_output="Esqueleto n8n: trigger + nodes + integrações + JSON resumido.",
    )
    task_theo_pipe = Task(
        description="Valide o workflow do PIPE: as integrações Shopify/AppMax/Z-API estão usando endpoints corretos? Há risco de loop ou rate limit? Sugira ajustes.",
        agent=THEO,
        expected_output="Validação técnica + ajustes recomendados.",
    )
    return Crew(
        agents=[PIPE, THEO],
        tasks=[task_pipe, task_theo_pipe],
        process=Process.sequential,
        verbose=True,
    )


def build_audit_crew(context: str) -> Crew:
    """Crew de auditoria completa: ECHO coordena todos os agentes."""
    task_theo = Task(
        description=f"Faça um diagnóstico técnico da loja: PageSpeed, Pixel, Checkout, Yampi, AppMax. Contexto: {context}",
        agent=THEO,
        expected_output="Diagnóstico técnico com score e 2 ações prioritárias.",
    )
    task_rex = Task(
        description="Analise performance das campanhas Meta Ads: ROAS, CAC, CTR criativo C. Sugira 1 ajuste.",
        agent=REX,
        expected_output="Análise de campanha com 1 ajuste priorizado.",
    )
    task_echo = Task(
        description="Consolide os diagnósticos de THEO e REX. Gere score geral e plano de ação semanal.",
        agent=ECHO,
        expected_output="Score consolidado e plano de ação com 3 prioridades.",
    )
    return Crew(
        agents=[THEO, REX, ECHO],
        tasks=[task_theo, task_rex, task_echo],
        process=Process.sequential,
        verbose=True,
    )
