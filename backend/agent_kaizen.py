# -*- coding: utf-8 -*-
"""
Agent Kaizen — Sistema Avançado de Aprendizado Contínuo e Evolução dos Agentes
Aura Decore · 2026

Cada agente mantém:
- DNA de Aprendizado (o que funciona, o que não funciona)
- Score de Habilidades (atualizado semanalmente)
- Histórico de Execuções com métricas reais
- Auto-Otimização de Prompts baseada em dados

Comando: /agents evolve → run_agents_evolve()
"""
from __future__ import annotations

import json
import os
import pathlib
import platform
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Any, Optional

from anthropic import Anthropic

# ── Vault path ─────────────────────────────────────────────────────────────────
_default_vault = (
    r"C:\Users\erick\AURA-decor-vault"
    if platform.system() == "Windows"
    else "/app/vault"
)
VAULT = pathlib.Path(os.getenv("OBSIDIAN_VAULT", _default_vault))
KAIZEN_DIR = VAULT / "Kaizen"

# ── Persona da Ana Clara (público-alvo) ────────────────────────────────────────
ANA_CLARA_DNA = """
Ana Clara — Persona Central da Aura Decore
- Mulher, 25–45 anos, classe B/C+
- Trabalha fora, casa própria ou alugada, quer transformar seu lar
- Valores: bem-estar, tranquilidade, estética elevada sem ostentação
- Dores: casa parece "sem vida", não sabe por onde começar a decorar
- Desejos: ambiente calmo, instagramável mas funcional, produtos únicos
- Canais: Instagram (inspiração), Pinterest (projetos), WhatsApp (compra)
- Gatilhos: biofilia, materiais naturais, neuroarquitetura, estilo Bali/Japandi
- Objeções: preço, entrega, se vai combinar com o que já tem
- LTV médio esperado: R$450 em 12 meses (3 compras R$150)
"""

# ── Métricas que cada agente deve monitorar ─────────────────────────────────────
UNIVERSAL_METRICS = [
    "tempo_execucao_medio_min",
    "taxa_sucesso_tarefas",
    "qualidade_output_1_10",
    "colaboracao_outros_agentes",
    "impacto_na_receita",
]

# ── Definição do DNA de cada agente ────────────────────────────────────────────
ALL_AGENTS_DNA: dict[str, dict] = {
    "ive": {
        "nome": "IVE", "cargo": "CEO · Estratégia", "modelo": "claude-opus-4-7",
        "skill_focus": ["tomada_decisao", "delegacao", "analise_estrategica", "comunicacao_eduardo"],
        "metricas_primarias": ["decisoes_semana", "acuracia_previsao", "tempo_resposta_eduardo"],
        "persona_adaptacao": "Coordenadora que evolui com dados reais de vendas e comportamento da Ana Clara",
        "aprendizados_iniciais": [
            "Briefings concisos funcionam melhor que longos relatórios",
            "Eduardo prefere opções (A/B) ao invés de uma única decisão",
            "Priorizar ações que impactam conversão diretamente",
        ],
        "colaboradores_diretos": ["guard", "nexus", "vera", "luna", "echo", "sol"],
    },
    "guard": {
        "nome": "GUARD", "cargo": "CFO · Protetor Financeiro", "modelo": "claude-opus-4-7",
        "skill_focus": ["analise_financeira", "controle_mei", "alertas_risco", "veto_gastos"],
        "metricas_primarias": ["faturamento_acumulado_mei", "roas_semanal", "margem_bruta", "caixa_atual"],
        "persona_adaptacao": "CFO que aprende padrões de gasto e antecipa riscos antes que ocorram",
        "aprendizados_iniciais": [
            "Alertas 🟡 devem ser emitidos antes de virar 🔴",
            "DAS MEI dia 20 — notificar Eduardo no dia 15",
            "Produtos com margem < 40% precisam de justificativa estratégica",
        ],
        "colaboradores_diretos": ["ive", "kai", "sol", "fina"],
    },
    "nexus": {
        "nome": "NEXUS", "cargo": "Mineração · Produtos", "modelo": "claude-sonnet-4-6",
        "skill_focus": ["pesquisa_aliexpress", "analise_tendencias", "score_neuroarquitetura", "curadoria_fornecedor"],
        "metricas_primarias": ["produtos_minerados_semana", "score_medio", "taxa_aprovacao_kai", "tendencias_identificadas"],
        "persona_adaptacao": "Radar que aprende quais categorias a Ana Clara compra mais e prioriza buscas",
        "aprendizados_iniciais": [
            "Produtos com biofilia (plantas, madeira, bambu) têm score +2 automático",
            "AliExpress: filtrar seller rating > 4.7 e mínimo 200 reviews",
            "Tendência só conta se Pinterest + Google Trends convergem",
        ],
        "colaboradores_diretos": ["kai", "vera", "mira"],
    },
    "kai": {
        "nome": "KAI", "cargo": "Produtos · Curadoria", "modelo": "claude-sonnet-4-6",
        "skill_focus": ["analise_margem", "curadoria_portfolio", "pausa_produtos", "negociacao_fornecedor"],
        "metricas_primarias": ["produtos_ativos", "margem_media_portfolio", "produtos_pausados_mes", "rotatividade"],
        "persona_adaptacao": "Curador que aprende quais produtos convertem melhor para a Ana Clara específica",
        "aprendizados_iniciais": [
            "Produtos > R$150 exigem mais prova social (reviews + UGC)",
            "Itens de bambu e cerâmica têm giro mais rápido que têxteis",
            "Pausar produto após 15 dias sem venda (não 10) para dar tempo justo",
        ],
        "colaboradores_diretos": ["nexus", "vera", "theo", "guard"],
    },
    "vera": {
        "nome": "VERA", "cargo": "Copy · Textos", "modelo": "claude-sonnet-4-6",
        "skill_focus": ["headline_impacto", "copy_produto", "email_nutricao", "gatilhos_emocionais"],
        "metricas_primarias": ["copys_criadas_semana", "taxa_aprovacao_ive", "conversao_email", "ctr_anuncio"],
        "persona_adaptacao": "Copywriter que aprende quais palavras e emoções convertem a Ana Clara",
        "aprendizados_iniciais": [
            "Palavras que convertem: 'tranquilidade', 'lar dos sonhos', 'equilíbrio', 'minimalista'",
            "Evitar: 'oferta', 'desconto', 'promoção' (diminuem percepção de valor)",
            "Headlines com pergunta convertem 23% mais que afirmações",
            "Copy para Instagram: máximo 150 chars antes do 'mais'",
        ],
        "colaboradores_diretos": ["luna", "nox", "mira", "sol"],
    },
    "luna": {
        "nome": "LUNA", "cargo": "Design · Visual", "modelo": "claude-sonnet-4-6",
        "skill_focus": ["identidade_visual", "briefing_criativo", "brand_kit", "consistencia_visual"],
        "metricas_primarias": ["briefings_semana", "assets_aprovados", "consistencia_paleta", "tempo_producao"],
        "persona_adaptacao": "Diretora criativa que aprende quais estilos visuais geram mais engajamento da Ana Clara",
        "aprendizados_iniciais": [
            "Luz natural difusa > flash direto em fotos de produto",
            "Paleta terra #B8793A com off-white #F5F0EB = maior engajamento histórico",
            "Fundo texturizado (linho, madeira) aumenta CTR vs fundo branco",
        ],
        "colaboradores_diretos": ["arte", "nox", "vera", "dev"],
    },
    "nox": {
        "nome": "NOX", "cargo": "Conteúdo · Reels", "modelo": "claude-sonnet-4-6",
        "skill_focus": ["roteiro_reel", "hook_primeiros_3s", "calendario_conteudo", "mix_estrategico"],
        "metricas_primarias": ["posts_semana", "engajamento_medio", "alcance", "saves_compartilhamentos"],
        "persona_adaptacao": "Criador que aprende quais hooks param o scroll da Ana Clara às 21h",
        "aprendizados_iniciais": [
            "Hooks visuais (movimento) > hooks textuais no Instagram Reels",
            "Melhor horário de post: 10h (produto) 14h (educativo) 19h (lifestyle)",
            "Conteúdo 'Antes vs Depois' tem 3x mais saves que posts estáticos",
            "Mix: 40% educativo, 30% inspiracional, 30% produto direto",
        ],
        "colaboradores_diretos": ["vera", "luna", "arte", "feed"],
    },
    "rex": {
        "nome": "REX", "cargo": "Tráfego · Meta Ads", "modelo": "claude-sonnet-4-6",
        "skill_focus": ["gestao_ads", "otimizacao_roas", "criativo_performance", "segmentacao"],
        "metricas_primarias": ["roas", "cac", "ctr", "cpm", "frequencia"],
        "persona_adaptacao": "Gestor de ads que aprende quais criativos e audiências convertem a Ana Clara",
        "aprendizados_iniciais": [
            "ROAS < 1.5x → pausar imediatamente, não esperar",
            "Frequência > 3.5 = criativo esgotado, renovar",
            "Audiência Lookalike 2% supera interesse frio para e-commerce decoração",
            "Testar criativos: mínimo R$15/criativo/dia por 3 dias antes de julgar",
        ],
        "colaboradores_diretos": ["luna", "arte", "vera", "guard", "sol"],
    },
    "theo": {
        "nome": "THEO", "cargo": "Shopify · Técnico", "modelo": "claude-sonnet-4-6",
        "skill_focus": ["shopify_admin", "pixel_meta", "pagespeed", "checkout_otimizacao"],
        "metricas_primarias": ["pagespeed_mobile", "taxa_checkout", "produtos_atualizados", "erros_pixel"],
        "persona_adaptacao": "Técnico que aprende quais mudanças na loja aumentam conversão diretamente",
        "aprendizados_iniciais": [
            "publishablePublish nos 3 canais (ACTIVE sozinho não publica)",
            "Backup obrigatório antes de qualquer mudança no tema live",
            "PageSpeed < 70 mobile → investigar imagens não otimizadas",
            "Checkout: remover campos desnecessários aumenta conversão 15%",
        ],
        "colaboradores_diretos": ["kai", "vera", "pipe", "dev"],
    },
    "echo": {
        "nome": "ECHO", "cargo": "Auditor · Semanal", "modelo": "claude-sonnet-4-6",
        "skill_focus": ["auditoria_agentes", "score_performance", "identificacao_gaps", "kaizen"],
        "metricas_primarias": ["score_medio_equipe", "melhorias_implementadas", "gaps_identificados", "evolucao_semanal"],
        "persona_adaptacao": "Auditor que aprende onde o sistema tem gargalos e propõe Kaizen concreto",
        "aprendizados_iniciais": [
            "Score 0-10 por agente: < 6 requer plano de melhoria imediato",
            "Não aceitar 'estamos melhorando' sem número que prove",
            "Kaizen: 1 melhoria específica por agente por semana (não 5 genéricas)",
        ],
        "colaboradores_diretos": ["ive", "guard", "todos"],
    },
    "lena": {
        "nome": "LENA", "cargo": "Atendimento · CX", "modelo": "claude-sonnet-4-6",
        "skill_focus": ["atendimento_whatsapp", "resolucao_conflito", "fidelizacao", "hero_framework"],
        "metricas_primarias": ["csat", "tempo_resposta_medio_h", "tickets_resolvidos", "taxa_recompra"],
        "persona_adaptacao": "Atendente que aprende as dúvidas e objeções mais frequentes da Ana Clara",
        "aprendizados_iniciais": [
            "Dúvida mais frequente: prazo de entrega → responder com rastreio proativo",
            "Cupom AURA10 em qualquer reclamação > resolve 80% dos casos",
            "Nunca usar 'infelizmente', 'protocolo', 'política da empresa'",
            "Reembolso > R$200: escalar GUARD antes de aprovar",
        ],
        "colaboradores_diretos": ["guard", "sol", "zara"],
    },
    "sol": {
        "nome": "SOL", "cargo": "Vendas · CRO", "modelo": "claude-sonnet-4-6",
        "skill_focus": ["recuperacao_carrinho", "upsell_bundle", "funil_conversao", "ltv"],
        "metricas_primarias": ["conversao", "ticket_medio", "recovery_rate", "ltv", "recompra"],
        "persona_adaptacao": "CRO que aprende em qual momento da jornada a Ana Clara abandona o carrinho",
        "aprendizados_iniciais": [
            "D+1 com AURA10 recupera 15% dos carrinhos abandonados",
            "Bundle produto + complementar aumenta ticket em 35%",
            "Frete grátis ≥ R$299 é o principal gatilho de upsell",
            "Pós-compra D+7: pedir review com foto = UGC gratuito",
        ],
        "colaboradores_diretos": ["kai", "vera", "theo", "rex"],
    },
    "zara": {
        "nome": "ZARA", "cargo": "Community · Instagram", "modelo": "claude-sonnet-4-6",
        "skill_focus": ["dm_management", "ugc_incentivo", "embaixadoras", "engajamento_organico"],
        "metricas_primarias": ["seguidores", "dm_response_time_h", "ugc_gerado_mes", "embaixadoras_ativas"],
        "persona_adaptacao": "Community manager que aprende quais interações criam fãs da Aura Decore",
        "aprendizados_iniciais": [
            "Responder comentários dentro de 30min aumenta alcance orgânico",
            "Clientes com 3+ compras = candidatas a embaixadoras (cupom AURAEMBAIXADORA20)",
            "UGC com foto do produto no ambiente vale mais que produto sozinho",
        ],
        "colaboradores_diretos": ["nox", "luna", "feed", "lena"],
    },
    "mira": {
        "nome": "MIRA", "cargo": "SEO · Pesquisa", "modelo": "claude-sonnet-4-6",
        "skill_focus": ["keyword_research", "seo_shopify", "gsc_analise", "pinterest_seo"],
        "metricas_primarias": ["visitas_organicas_mes", "keywords_top10", "impressoes_gsc", "ctr_organico"],
        "persona_adaptacao": "SEO que aprende quais termos a Ana Clara usa para buscar decoração",
        "aprendizados_iniciais": [
            "Cauda longa: 'vaso japandi cerâmica brasil' converte mais que 'vaso decorativo'",
            "Pinterest SEO: 500 chars de descrição com 5 keywords naturais",
            "Meta title ideal: Keyword Principal | Aura Decore | 60 chars max",
        ],
        "colaboradores_diretos": ["vera", "theo", "nox"],
    },
    "pipe": {
        "nome": "PIPE", "cargo": "Automação · n8n", "modelo": "claude-sonnet-4-6",
        "skill_focus": ["n8n_workflows", "webhooks", "integracao_apis", "logs_retry"],
        "metricas_primarias": ["workflows_ativos", "taxa_sucesso_webhook", "erros_por_dia", "tempo_execucao_workflow"],
        "persona_adaptacao": "Engenheiro que aprende quais automações economizam mais tempo da operação",
        "aprendizados_iniciais": [
            "17 workflows ativos — verificar health toda segunda",
            "Falha de webhook: retry automático com backoff 1min/5min/15min",
            "Z-API: reconectar se >6h sem mensagem (sessão pode ter caído)",
        ],
        "colaboradores_diretos": ["theo", "feed", "nexus", "ive"],
    },
    "arte": {
        "nome": "ARTE", "cargo": "Criativo · IA Visual", "modelo": "claude-sonnet-4-6",
        "skill_focus": ["pollinations_prompts", "imagens_produto", "lifestyle_creative", "brand_consistency"],
        "metricas_primarias": ["imagens_geradas_dia", "aprovacao_luna", "assets_publicados", "tempo_geracao"],
        "persona_adaptacao": "Studio visual que aprende quais prompts geram imagens que a Ana Clara salva",
        "aprendizados_iniciais": [
            "Prompt base: 'editorial photography, japandi interior, natural light, wabi-sabi, 8k, minimal'",
            "Fundo linho > fundo branco em fotos de produto (+18% save rate)",
            "3 criativos/dia: 1 produto puro, 1 lifestyle ambiente, 1 detalhe textura",
        ],
        "colaboradores_diretos": ["luna", "nox", "feed", "theo"],
    },
    "feed": {
        "nome": "FEED", "cargo": "Publicador · Redes Sociais", "modelo": "claude-sonnet-4-6",
        "skill_focus": ["publicacao_instagram", "publicacao_facebook", "agendamento", "relatorio_post"],
        "metricas_primarias": ["posts_publicados_dia", "taxa_sucesso", "alcance_estimado", "falhas"],
        "persona_adaptacao": "Publicador que aprende os melhores horários e formatos para cada canal",
        "aprendizados_iniciais": [
            "3 canais: IG @auras.decore + FB Comercial (Graph API) + FB Pessoal (Chrome MCP)",
            "Falha em 2 publicações seguidas → alertar IVE imediatamente",
            "Melhor horário Instagram: 10h30/14h30/19h30 (não horário redondo)",
        ],
        "colaboradores_diretos": ["vera", "arte", "nox", "zara"],
    },
    "dev": {
        "nome": "DEV", "cargo": "Desenvolvedor · Shopify", "modelo": "claude-sonnet-4-6",
        "skill_focus": ["liquid_css", "cro_shopify", "pagespeed", "tema_sazonal"],
        "metricas_primarias": ["deployments_semana", "pagespeed_depois", "taxa_conversao_loja", "erros_js"],
        "persona_adaptacao": "Dev que aprende quais mudanças no tema aumentam conversão real",
        "aprendizados_iniciais": [
            "Tema live: 160266387561 — SEMPRE backup antes de mexer",
            "CRO priority: urgency timer > exit popup > cart upsell",
            "CSS: var(--font-body-scale) para escala de texto (body_scale=110 atual)",
        ],
        "colaboradores_diretos": ["pipe", "theo", "luna"],
    },
    "vega": {
        "nome": "VEGA", "cargo": "Videomaker · Motion Director", "modelo": "claude-sonnet-4-6",
        "skill_focus": ["roteiro_video", "motion_graphics", "reels_tiktok", "storytelling_visual"],
        "metricas_primarias": ["videos_semana", "views_medio", "retencao_30s", "compartilhamentos"],
        "persona_adaptacao": "Videomaker que aprende quais narrativas visuais capturam a Ana Clara em 3 segundos",
        "aprendizados_iniciais": [
            "Hook visual nos primeiros 1.5s > texto nos primeiros 3s",
            "ASMR de produto (som de textura, cerâmica) tem 4x mais retenção",
            "Formato vertical 9:16 nativo > crop de horizontal",
            "Higgsfield API Key pendente — usar templates de roteiro manual enquanto isso",
        ],
        "colaboradores_diretos": ["nox", "luna", "arte", "feed"],
    },
    "fina": {
        "nome": "FINA", "cargo": "Finanças Operacional · Pagamentos PJ", "modelo": "claude-sonnet-4-6",
        "skill_focus": ["pagamentos_fornecedores", "controle_caixa", "relatorio_mensal", "nubank_pj"],
        "metricas_primarias": ["contas_pagas_prazo", "saldo_caixa", "fornecedores_ativos", "inadimplencia"],
        "persona_adaptacao": "Tesoureira que aprende o fluxo de caixa real da Aura Decore mês a mês",
        "aprendizados_iniciais": [
            "Nubank PJ aguarda CNPJ ME — operar com MEI AppMax/Yampi enquanto isso",
            "Pagamentos só após aprovação explícita de Eduardo",
            "Relatório mensal para GUARD todo dia 1 do mês",
        ],
        "colaboradores_diretos": ["guard", "ive"],
    },
}

# ── Skill scores padrão para agentes novos ─────────────────────────────────────
DEFAULT_SKILL_SCORES = {
    "execucao": 7.0,
    "qualidade": 7.0,
    "velocidade": 7.0,
    "colaboracao": 7.0,
    "adaptabilidade": 6.0,
    "analise_dados": 6.0,
    "alinhamento_persona": 6.5,
}


@dataclass
class AgentKaizenRecord:
    """Registro Kaizen de um agente — memória persistente de evolução."""
    agent_id: str
    nome: str
    semana: str  # "2026-W24"
    skill_scores: dict = field(default_factory=lambda: dict(DEFAULT_SKILL_SCORES))
    execucoes_semana: int = 0
    taxa_sucesso: float = 0.0
    aprendizados_novos: list[str] = field(default_factory=list)
    o_que_funcionou: list[str] = field(default_factory=list)
    o_que_nao_funcionou: list[str] = field(default_factory=list)
    metricas: dict = field(default_factory=dict)
    evolucao_vs_semana_anterior: float = 0.0
    proximo_foco: str = ""
    ultima_atualizacao: str = field(default_factory=lambda: datetime.now().isoformat())


def _get_semana_atual() -> str:
    """Retorna a semana atual no formato ISO 'YYYY-WXX'."""
    hoje = datetime.now()
    return f"{hoje.year}-W{hoje.isocalendar()[1]:02d}"


def _kaizen_path(agent_id: str) -> pathlib.Path:
    """Caminho do arquivo Kaizen de um agente no vault."""
    KAIZEN_DIR.mkdir(parents=True, exist_ok=True)
    return KAIZEN_DIR / f"{agent_id.upper()}-kaizen.json"


def _dna_path(agent_id: str) -> pathlib.Path:
    """Caminho do arquivo DNA (.md) de um agente no vault."""
    return VAULT / "Agentes" / agent_id.upper() / "kaizen-dna.md"


def load_kaizen_record(agent_id: str) -> AgentKaizenRecord:
    """Carrega o registro Kaizen de um agente. Cria se não existir."""
    path = _kaizen_path(agent_id)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return AgentKaizenRecord(**data)
        except Exception:
            pass
    dna = ALL_AGENTS_DNA.get(agent_id.lower(), {})
    record = AgentKaizenRecord(
        agent_id=agent_id.lower(),
        nome=dna.get("nome", agent_id.upper()),
        semana=_get_semana_atual(),
        aprendizados_novos=list(dna.get("aprendizados_iniciais", [])),
        o_que_funcionou=list(dna.get("aprendizados_iniciais", [])),
    )
    save_kaizen_record(record)
    return record


def save_kaizen_record(record: AgentKaizenRecord):
    """Salva o registro Kaizen de um agente no vault."""
    record.ultima_atualizacao = datetime.now().isoformat()
    path = _kaizen_path(record.agent_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(record), ensure_ascii=False, indent=2), encoding="utf-8")


def record_execution(agent_id: str, task: str, success: bool, duration_min: float,
                     quality_score: float, notes: str = ""):
    """
    Registra uma execução de tarefa no histórico Kaizen do agente.
    Chamado automaticamente após cada crew kickoff.
    """
    record = load_kaizen_record(agent_id)
    semana_atual = _get_semana_atual()

    # Reseta registro se for semana nova
    if record.semana != semana_atual:
        record.semana = semana_atual
        record.execucoes_semana = 0
        record.taxa_sucesso = 0.0
        record.aprendizados_novos = []

    record.execucoes_semana += 1

    # Atualiza taxa de sucesso (média móvel)
    prev_total = record.execucoes_semana - 1
    record.taxa_sucesso = (record.taxa_sucesso * prev_total + (1.0 if success else 0.0)) / record.execucoes_semana

    # Atualiza skill scores
    if quality_score > 0:
        old_q = record.skill_scores.get("qualidade", 7.0)
        record.skill_scores["qualidade"] = round((old_q * 0.8 + quality_score * 0.2), 2)

    if duration_min > 0:
        # Velocidade: < 5min = 10, > 30min = 5
        vel_score = max(5.0, min(10.0, 10.0 - (duration_min - 5) * 0.167))
        old_v = record.skill_scores.get("velocidade", 7.0)
        record.skill_scores["velocidade"] = round((old_v * 0.8 + vel_score * 0.2), 2)

    # Registra métricas
    record.metricas[f"duracao_min_{datetime.now().strftime('%m%d_%H%M')}"] = duration_min

    # Aprende com o resultado
    if success and notes:
        record.o_que_funcionou.append(f"[{datetime.now().strftime('%m/%d')}] {notes}")
        record.o_que_funcionou = record.o_que_funcionou[-20:]  # mantém últimos 20
    elif not success and notes:
        record.o_que_nao_funcionou.append(f"[{datetime.now().strftime('%m/%d')}] {notes}")
        record.o_que_nao_funcionou = record.o_que_nao_funcionou[-10:]  # mantém últimos 10

    save_kaizen_record(record)


def _score_geral(record: AgentKaizenRecord) -> float:
    """Calcula score geral do agente (0-10)."""
    scores = list(record.skill_scores.values())
    base = sum(scores) / len(scores) if scores else 7.0
    sucesso_bonus = (record.taxa_sucesso - 0.7) * 2  # bonus se > 70% sucesso
    return round(min(10.0, max(0.0, base + sucesso_bonus)), 2)


def generate_kaizen_dna_md(agent_id: str) -> str:
    """Gera o arquivo markdown de DNA Kaizen de um agente."""
    record = load_kaizen_record(agent_id)
    dna = ALL_AGENTS_DNA.get(agent_id.lower(), {})
    score = _score_geral(record)

    o_que_funcionou = "\n".join(f"- ✅ {s}" for s in record.o_que_funcionou[-10:]) or "- (sem registros ainda)"
    o_que_nao_funcionou = "\n".join(f"- ❌ {s}" for s in record.o_que_nao_funcionou[-5:]) or "- (sem registros ainda)"
    skills_md = "\n".join(f"| {k} | {v}/10 |" for k, v in record.skill_scores.items())
    focais = "\n".join(f"- {f}" for f in dna.get("skill_focus", []))
    metricas = "\n".join(f"- `{m}`" for m in dna.get("metricas_primarias", []))
    aprendizados = "\n".join(f"- 🧠 {a}" for a in record.aprendizados_novos[-15:]) or "- (acumulando...)"

    return f"""---
agente: {record.nome}
cargo: {dna.get('cargo', '')}
semana: {record.semana}
score_geral: {score}/10
atualizado: {datetime.now().strftime('%Y-%m-%d %H:%M')}
---

# 🧬 DNA Kaizen — {record.nome}

> Sistema de aprendizado contínuo. Atualizado automaticamente após cada ciclo de evolução.

## 📊 Score da Semana
**{score}/10** | Execuções: {record.execucoes_semana} | Taxa sucesso: {record.taxa_sucesso:.0%}

## 🎯 Habilidades (Skills)
| Skill | Score |
|-------|-------|
{skills_md}

## 🔭 Foco Estratégico
{focais}

## 📈 Métricas Primárias
{metricas}

## ✅ O Que Funcionou
{o_que_funcionou}

## ❌ O Que Não Funcionou
{o_que_nao_funcionou}

## 🧠 Aprendizados Acumulados
{aprendizados}

## 🎯 Próximo Foco
{record.proximo_foco or dna.get('persona_adaptacao', 'Melhorar alinhamento com a persona Ana Clara')}

## 👥 Ana Clara — Adaptações para esta Persona
{ANA_CLARA_DNA}

## 🤝 Colaboradores Diretos
{chr(10).join(f'- {c.upper()}' for c in dna.get('colaboradores_diretos', []))}
"""


def write_agent_kaizen_dna(agent_id: str):
    """Escreve o arquivo kaizen-dna.md no vault do agente."""
    content = generate_kaizen_dna_md(agent_id)
    path = _dna_path(agent_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def update_agent_skill(agent_id: str, skill: str, new_score: float, justification: str = ""):
    """Atualiza um skill específico de um agente com justificativa."""
    record = load_kaizen_record(agent_id)
    old_score = record.skill_scores.get(skill, 7.0)
    record.skill_scores[skill] = round(min(10.0, max(0.0, new_score)), 2)
    if justification:
        learning = f"Skill '{skill}' {old_score:.1f}→{new_score:.1f}: {justification}"
        record.aprendizados_novos.append(learning)
    save_kaizen_record(record)


def write_shared_learning_dna():
    """Escreve o DNA de Aprendizado Compartilhado entre todos os agentes."""
    path = VAULT / "Memoria" / "Compartilhada" / "dna-aprendizado.md"
    path.parent.mkdir(parents=True, exist_ok=True)

    all_records = []
    for agent_id in ALL_AGENTS_DNA:
        record = load_kaizen_record(agent_id)
        score = _score_geral(record)
        all_records.append((record.nome, score, record.execucoes_semana))

    all_records.sort(key=lambda x: x[1], reverse=True)
    ranking_md = "\n".join(
        f"| {i+1} | {nome} | {score}/10 | {execs} execuções |"
        for i, (nome, score, execs) in enumerate(all_records)
    )

    content = f"""---
tipo: dna-compartilhado
atualizado: {datetime.now().strftime('%Y-%m-%d %H:%M')}
semana: {_get_semana_atual()}
---

# 🧬 DNA de Aprendizado Compartilhado — Aura Decore

> Memória coletiva de todos os 20 agentes. Cada agente lê este arquivo antes de executar tarefas.

## 🏆 Ranking de Performance Esta Semana
| Pos | Agente | Score | Execuções |
|-----|--------|-------|-----------|
{ranking_md}

## 🎯 Persona Ana Clara — O Que Aprendemos
{ANA_CLARA_DNA}

## 📋 Regras Absolutas da Empresa
1. ROAS mínimo 2x para qualquer campanha paga
2. Margem mínima 35% em todos os produtos
3. Caixa mínimo R$500 sempre
4. DAS MEI R$70,60 até dia 20 de cada mês
5. Nenhum gasto sem aprovação do GUARD
6. Toda decisão estratégica passa pela IVE
7. Eduardo tem autoridade suprema sobre todos os agentes
8. Publicar produto = publishablePublish nos 3 canais (ACTIVE não basta)
9. Backup obrigatório antes de qualquer mudança no tema Shopify

## 🔑 Aprendizados Globais (Toda a Equipe)
- Conteúdo que mostra transformação (antes/depois) converte 3x mais
- Ana Clara compra às 19h–22h (horário pós-trabalho)
- WhatsApp tem conversão 5x maior que email para este nicho
- Produtos com biofilia (bambu, cerâmica, linho) têm giro 40% mais rápido
- Copy emocional sobre paz/tranquilidade supera copy técnico sobre materiais
- Frete grátis ≥ R$299 é o gatilho de upsell mais efetivo
- Reviews com foto de ambiente real valem mais que reviews textuais

## ⚡ Princípios Kaizen
1. **Memorização Ativa** — Todo agente registra o que funcionou e o que não funcionou
2. **Auto-Otimização** — Skills e prompts são atualizados semanalmente com base em dados
3. **Análise Baseada em Dados** — Métricas reais guiam decisões, não intuição
4. **Adaptação à Persona** — Cada ação é filtrada pela perspectiva da Ana Clara
5. **Eficiência Operacional** — Reduzir tempo desnecessário e aumentar qualidade
6. **Colaboração Inteligente** — Agentes compartilham aprendizados via este DNA
"""
    path.write_text(content, encoding="utf-8")


def run_agents_evolve(eduardo_context: str = "") -> dict:
    """
    Comando principal: /agents evolve
    Executa evolução completa de todos os 20 agentes.
    Retorna relatório detalhado.
    """
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    semana = _get_semana_atual()
    relatorio = {
        "semana": semana,
        "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "agentes_evoluidos": 0,
        "score_medio_antes": 0.0,
        "score_medio_depois": 0.0,
        "evolucoes": [],
        "top_performers": [],
        "precisa_atencao": [],
        "dna_compartilhado": "✅ atualizado",
        "resumo_executivo": "",
    }

    scores_antes = []
    scores_depois = []
    resultados_agentes = []

    # ── Fase 1: Auditar e evoluir cada agente ──────────────────────────────────
    for agent_id, dna in ALL_AGENTS_DNA.items():
        nome = dna["nome"]
        record = load_kaizen_record(agent_id)
        score_antes = _score_geral(record)
        scores_antes.append(score_antes)

        # Usa Claude para analisar e sugerir evolução
        prompt = f"""Você é o sistema de evolução Kaizen da Aura Decore.
Analise o agente {nome} ({dna['cargo']}) e sugira melhorias específicas.

CONTEXTO DO AGENTE:
- Foco de skills: {', '.join(dna['skill_focus'])}
- Métricas primárias: {', '.join(dna['metricas_primarias'])}
- Adaptação persona: {dna['persona_adaptacao']}
- Aprendizados iniciais: {json.dumps(dna.get('aprendizados_iniciais', []), ensure_ascii=False)}

REGISTRO ATUAL:
- Score geral: {score_antes}/10
- Execuções esta semana: {record.execucoes_semana}
- Taxa sucesso: {record.taxa_sucesso:.0%}
- O que funcionou: {json.dumps(record.o_que_funcionou[-5:], ensure_ascii=False)}
- O que não funcionou: {json.dumps(record.o_que_nao_funcionou[-3:], ensure_ascii=False)}

CONTEXTO DO EDUARDO: {eduardo_context or 'Sem contexto adicional esta semana.'}

TAREFA: Retorne um JSON com exatamente estas chaves:
{{
  "novo_aprendizado": "1 frase específica de aprendizado para este agente",
  "melhoria_skill_foco": "qual skill focar para melhorar (ex: qualidade, velocidade, colaboracao)",
  "novo_score_skill": 7.5,
  "proximo_foco": "1 frase sobre onde este agente deve se concentrar na próxima semana",
  "dica_persona_ana_clara": "1 ação concreta que este agente pode fazer para servir melhor a Ana Clara"
}}

Seja específico, prático e baseado em dados. Responda APENAS com o JSON."""

        try:
            resp = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = resp.content[0].text.strip()
            # Extrai JSON mesmo se vier com markdown
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            evolution = json.loads(raw)

            # Aplica a evolução no registro
            if evolution.get("novo_aprendizado"):
                record.aprendizados_novos.append(f"[IA Kaizen] {evolution['novo_aprendizado']}")

            skill = evolution.get("melhoria_skill_foco", "qualidade")
            novo_score = float(evolution.get("novo_score_skill", 7.5))
            update_agent_skill(agent_id, skill, novo_score, evolution.get("novo_aprendizado", ""))

            record = load_kaizen_record(agent_id)
            if evolution.get("proximo_foco"):
                record.proximo_foco = evolution["proximo_foco"]
            if evolution.get("dica_persona_ana_clara"):
                record.aprendizados_novos.append(f"[Ana Clara] {evolution['dica_persona_ana_clara']}")
            save_kaizen_record(record)

            score_depois = _score_geral(record)
            scores_depois.append(score_depois)

            evolucao = {
                "agente": nome,
                "cargo": dna["cargo"],
                "score_antes": score_antes,
                "score_depois": score_depois,
                "delta": round(score_depois - score_antes, 2),
                "novo_aprendizado": evolution.get("novo_aprendizado", ""),
                "proximo_foco": evolution.get("proximo_foco", ""),
            }
            resultados_agentes.append(evolucao)
            relatorio["evolucoes"].append(evolucao)

        except Exception as e:
            scores_depois.append(score_antes)
            entry = {
                "agente": nome, "cargo": dna["cargo"],
                "score_antes": score_antes, "score_depois": score_antes,
                "delta": 0.0, "erro": str(e)[:100],
            }
            relatorio["evolucoes"].append(entry)
            resultados_agentes.append(entry)

        # Escreve DNA atualizado no vault
        write_agent_kaizen_dna(agent_id)

    # ── Fase 2: DNA compartilhado ──────────────────────────────────────────────
    write_shared_learning_dna()

    # ── Fase 3: Relatório final ────────────────────────────────────────────────
    relatorio["agentes_evoluidos"] = len(ALL_AGENTS_DNA)
    relatorio["score_medio_antes"] = round(sum(scores_antes) / len(scores_antes), 2) if scores_antes else 0.0
    relatorio["score_medio_depois"] = round(sum(scores_depois) / len(scores_depois), 2) if scores_depois else 0.0

    # Top performers e quem precisa de atenção
    resultados_agentes.sort(key=lambda x: x.get("score_depois", 0), reverse=True)
    relatorio["top_performers"] = [
        f"{r['agente']} ({r['score_depois']}/10)" for r in resultados_agentes[:3]
    ]
    precisa = [r for r in resultados_agentes if r.get("score_depois", 10) < 6.5]
    relatorio["precisa_atencao"] = [
        f"{r['agente']} ({r['score_depois']}/10)" for r in precisa
    ]

    # Gera resumo executivo com IVE
    try:
        delta_total = relatorio["score_medio_depois"] - relatorio["score_medio_antes"]
        resumo_prompt = f"""Você é IVE, CEO da Aura Decore. Gere um resumo executivo do ciclo Kaizen desta semana.

Dados:
- Semana: {semana}
- Score médio ANTES: {relatorio['score_medio_antes']}/10
- Score médio DEPOIS: {relatorio['score_medio_depois']}/10
- Delta: {delta_total:+.2f}
- Top performers: {', '.join(relatorio['top_performers'])}
- Precisam atenção: {', '.join(relatorio['precisa_atencao']) or 'Nenhum 🎉'}
- Total agentes evoluídos: {relatorio['agentes_evoluidos']}/20

Escreva um resumo executivo de 3-4 linhas em português, direto ao ponto, com o que Eduardo precisa saber.
Tom: profissional, confiante, orientado a dados."""

        resp = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=300,
            messages=[{"role": "user", "content": resumo_prompt}]
        )
        relatorio["resumo_executivo"] = resp.content[0].text.strip()
    except Exception as e:
        relatorio["resumo_executivo"] = (
            f"Ciclo Kaizen {semana} concluído. {relatorio['agentes_evoluidos']} agentes evoluídos. "
            f"Score médio: {relatorio['score_medio_antes']} → {relatorio['score_medio_depois']}."
        )

    # Salva relatório no vault
    _save_evolve_report(relatorio)

    return relatorio


def _save_evolve_report(relatorio: dict):
    """Salva o relatório de evolução no vault."""
    data_str = relatorio["data"].replace(":", "-").replace(" ", "_")
    path = VAULT / "Relatorios" / "Semanais" / f"kaizen-{data_str}.md"
    path.parent.mkdir(parents=True, exist_ok=True)

    evolucoes_md = "\n".join(
        f"| {e['agente']} | {e['cargo']} | {e['score_antes']}/10 | {e['score_depois']}/10 | "
        f"{'+' if e.get('delta', 0) >= 0 else ''}{e.get('delta', 0)} | {e.get('novo_aprendizado', e.get('erro', '—'))[:80]} |"
        for e in relatorio["evolucoes"]
    )

    content = f"""---
tipo: relatorio-kaizen
semana: {relatorio['semana']}
data: {relatorio['data']}
score_antes: {relatorio['score_medio_antes']}
score_depois: {relatorio['score_medio_depois']}
---

# 🧬 Relatório Kaizen — {relatorio['semana']}
**Data:** {relatorio['data']}

## 📋 Resumo Executivo (IVE)
{relatorio['resumo_executivo']}

## 📊 Métricas Globais
- **Score médio ANTES:** {relatorio['score_medio_antes']}/10
- **Score médio DEPOIS:** {relatorio['score_medio_depois']}/10
- **Agentes evoluídos:** {relatorio['agentes_evoluidos']}/20
- **Top performers:** {', '.join(relatorio['top_performers'])}
- **Precisam atenção:** {', '.join(relatorio['precisa_atencao']) or 'Nenhum 🎉'}

## 🔄 Evolução por Agente
| Agente | Cargo | Score Antes | Score Depois | Delta | Aprendizado |
|--------|-------|-------------|--------------|-------|-------------|
{evolucoes_md}

## 🧬 DNA Compartilhado
{relatorio['dna_compartilhado']}

---
*Gerado automaticamente pelo sistema Kaizen da Aura Decore.*
"""
    path.write_text(content, encoding="utf-8")


def get_kaizen_summary() -> dict:
    """Retorna resumo rápido do estado atual de todos os agentes."""
    summary = {
        "semana": _get_semana_atual(),
        "agentes": {},
        "score_medio": 0.0,
    }
    scores = []
    for agent_id, dna in ALL_AGENTS_DNA.items():
        record = load_kaizen_record(agent_id)
        score = _score_geral(record)
        scores.append(score)
        summary["agentes"][dna["nome"]] = {
            "score": score,
            "execucoes": record.execucoes_semana,
            "taxa_sucesso": f"{record.taxa_sucesso:.0%}",
            "proximo_foco": record.proximo_foco[:80] if record.proximo_foco else "",
        }
    summary["score_medio"] = round(sum(scores) / len(scores), 2) if scores else 0.0
    return summary
