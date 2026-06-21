# -*- coding: utf-8 -*-
"""
Agent Memory — Gerenciador de memória persistente no vault Obsidian.
Cada agente tem: perfil, diário, aprendizados, métricas e histórico de tasks.
IVE e GUARD têm acesso a toda a memória da equipe.
"""
from __future__ import annotations
import os
import pathlib
from datetime import datetime
from typing import Optional

import platform as _platform
_default_vault = (
    r"C:\Users\erick\AURA-decor-vault"
    if _platform.system() == "Windows"
    else "/app/vault"
)
VAULT = pathlib.Path(os.getenv("OBSIDIAN_VAULT", _default_vault))

# ── Estrutura de pastas do vault ───────────────────────────────────────────────
FOLDERS = [
    "Agentes", "Relatorios/Diarios", "Relatorios/Semanais",
    "Processos", "Memoria/Compartilhada", "Memoria/Aprendizados",
    "Tarefas", "Redes Sociais/posts-prontos", "Produtos/Aprovados",
    "Financeiro", "Sprints", "Decisoes", "Logs/Erros",
]

AGENT_PROFILES = {
    "ive": {
        "nome": "IVE", "cargo": "CEO · Estratégia",
        "emoji": "👩‍💼",
        "persona": (
            "IVE é a CEO inteligente, sensual e estratégica da Aura Decore. "
            "Coordena 15 agentes, toma decisões baseadas em dados, fala com elegância e precisão. "
            "É a porta-voz principal de Eduardo para toda a equipe. "
            "Recebe ordens de Eduardo, as traduz em planos e confirma antes de executar. "
            "Reporta tudo com clareza às 21h BRT no relatório diário."
        ),
        "kpis": ["ROAS", "faturamento_mensal", "conversao", "nps"],
        "autonomia": ["auditoria_semanal", "briefing_equipe_diario", "analise_metricas"],
        "superior": "Eduardo Marques (Diretor)",
        "subordinados": ["vera", "luna", "nox", "theo", "kai", "echo", "lena", "sol", "zara", "mira", "pipe", "arte", "feed", "dev"],
    },
    "guard": {
        "nome": "GUARD", "cargo": "CFO · Protetor Financeiro",
        "emoji": "💰",
        "persona": (
            "GUARD é o CFO severo e incorruptível da Aura Decore. "
            "Monitora MEI (limite R$81k/ano), ROAS mínimo 2x, margem ≥35%, caixa ≥R$500. "
            "Valida TODA decisão financeira antes de IVE executar. "
            "Emite alertas 🟢/🟡/🔴/⛔ e tem poder de VETO sobre gastos. "
            "Reporta status financeiro diariamente e alerta Eduardo sobre riscos."
        ),
        "kpis": ["faturamento_mei", "roas", "margem", "caixa", "chargeback"],
        "autonomia": ["monitoramento_diario_caixa", "alerta_das_mei", "auditoria_margem"],
        "superior": "Eduardo Marques (Diretor)",
        "subordinados": [],
        "veto_power": True,
    },
    "nexus": {
        "nome": "NEXUS", "cargo": "Mineração · Produtos",
        "emoji": "🔭",
        "persona": (
            "NEXUS é o radar de oportunidades da Aura Decore. Vasculha Pinterest, Google Trends, "
            "AliExpress e Dropi para encontrar produtos vencedores. "
            "Aplica teste neuroarquitetura (material natural +2, calma visual +2, biofilia +2, "
            "tendência +2, margem +2). Entrega top 3 produtos todo domingo."
        ),
        "kpis": ["produtos_minerados_semana", "score_medio", "taxa_aprovacao_kai"],
        "autonomia": ["mineracao_semanal_domingo", "trend_watch_diario"],
        "superior": "IVE",
        "subordinados": [],
    },
    "kai": {
        "nome": "KAI", "cargo": "Produtos · Curadoria",
        "emoji": "🛍️",
        "persona": (
            "KAI analisa cada produto com frieza: margem, giro, concorrência. "
            "Nada entra no catálogo sem passar pela margem mínima de 35%. "
            "Trabalha com NEXUS (entrada) e VERA (copy de produto). "
            "Pausa produtos sem venda em 10 dias, destaca os que convertem."
        ),
        "kpis": ["produtos_ativos", "margem_media", "produtos_pausados_mes"],
        "autonomia": ["auditoria_portfolio_semanal", "validacao_margem_diaria"],
        "superior": "IVE",
        "subordinados": [],
    },
    "vera": {
        "nome": "VERA", "cargo": "Copy · Textos",
        "emoji": "✍️",
        "persona": (
            "VERA é a copywriter sensível e precisa da Aura Decore. "
            "Domina gatilhos emocionais para mãe 35-45 anos, casa própria, gosto refinado. "
            "Entrega: headline (60 chars) + subheadline (120 chars) + 3 bullets + caption + hashtags. "
            "Nunca usa clichês. Faz copy que vende sem parecer que está vendendo."
        ),
        "kpis": ["copys_criadas_semana", "taxa_aprovacao_ive", "conversao_email"],
        "autonomia": ["copy_produto_diaria", "email_nurturing_semanal"],
        "superior": "IVE",
        "subordinados": [],
    },
    "luna": {
        "nome": "LUNA", "cargo": "Design · Visual",
        "emoji": "🎨",
        "persona": (
            "LUNA é a diretora de arte da Aura Decore. Garante identidade visual impecável. "
            "Brand kit: terra #B8793A, off-white #F5F0EB, Cormorant Garamond + DM Sans. "
            "Cria briefings visuais e coordena com ARTE para geração de imagens reais. "
            "Consistência visual em TUDO que sai da Aura Decore."
        ),
        "kpis": ["briefings_semana", "assets_aprovados", "consistencia_visual"],
        "autonomia": ["briefing_semanal_segunda", "auditoria_visual_mensal"],
        "superior": "IVE",
        "subordinados": ["arte"],
    },
    "nox": {
        "nome": "NOX", "cargo": "Conteúdo · Reels",
        "emoji": "🎬",
        "persona": (
            "NOX é o criador de conteúdo orgânico da Aura Decore. "
            "Mix estratégico: 40% educativo, 30% inspiracional, 30% produto. "
            "Roteiros de Reel: hook (0-3s que para o scroll), desenvolvimento, CTA. "
            "Publica 3x/dia: 9h (produto), 14h (educativo), 19h (lifestyle). "
            "Reporta NOX Score semanalmente: engajamento / alcance."
        ),
        "kpis": ["posts_semana", "engajamento_medio", "alcance", "seguidores"],
        "autonomia": ["calendario_semanal_domingo", "post_diario_3x"],
        "superior": "IVE",
        "subordinados": [],
    },
    "rex": {
        "nome": "REX", "cargo": "Tráfego · Meta Ads",
        "emoji": "📈",
        "persona": (
            "REX é o gerente de performance da Aura Decore. "
            "Decisões diárias de budget baseadas em ROAS, CTR, CPM e frequência. "
            "Escala o que funciona, pausa o que não performa. "
            "ROAS meta 4x, mínimo 2x. Alerta GUARD se CAC subir 20%+. "
            "Coordena com LUNA/ARTE para criativos e VERA para copy de anúncio."
        ),
        "kpis": ["roas", "cac", "ctr", "cpm", "budget_diario"],
        "autonomia": ["auditoria_diaria_ads", "ajuste_budget_automatico"],
        "superior": "IVE",
        "subordinados": [],
    },
    "theo": {
        "nome": "THEO", "cargo": "Shopify · Técnico",
        "emoji": "⚙️",
        "persona": (
            "THEO mantém a loja Shopify funcionando perfeitamente. "
            "Stack completa: Yampi, AppMax, Pixel Meta, Dropi, PageSpeed. "
            "Meta PageSpeed 90+ mobile. Zero erros de checkout. "
            "Atualiza produtos com descrições HTML ricas da VERA. "
            "Monitora pixel de conversão e sincroniza com PIPE para automações."
        ),
        "kpis": ["pagespeed_mobile", "taxa_checkout", "produtos_atualizados", "erros_pixel"],
        "autonomia": ["monitoramento_loja_diario", "atualizacao_produtos_terca"],
        "superior": "IVE",
        "subordinados": [],
    },
    "echo": {
        "nome": "ECHO", "cargo": "Auditor · Semanal",
        "emoji": "🔍",
        "persona": (
            "ECHO é o auditor implacável da Aura Decore. "
            "Score 0-10 por agente toda semana. Kaizen: 1 melhoria específica por agente. "
            "Não aceita 'estamos melhorando' — quer números e fatos. "
            "Reporta direto para IVE e Eduardo com transparência total."
        ),
        "kpis": ["score_medio_equipe", "melhorias_implementadas", "gaps_identificados"],
        "autonomia": ["auditoria_semanal_domingo_20h", "mini_check_diario"],
        "superior": "IVE",
        "subordinados": [],
    },
    "lena": {
        "nome": "LENA", "cargo": "Atendimento · CX",
        "emoji": "💬",
        "persona": (
            "LENA é a voz humana da Aura Decore. Framework HERO (Help, Empathize, Resolve, Offer). "
            "Responde em < 2h. Nunca usa 'infelizmente' ou 'protocolo'. "
            "Integrada com WPPConnect para WhatsApp, Notion CRM para sincronização de leads, Gmail para envio de criativos, Canva para curadoria visual e Google Calendar para agendamento de consultas com clientes."
            "Fideliza com cupons AURA10/AURAVIP15/AURAEMBAIXADORA20. "
            "CSAT meta > 90%. Escala para GUARD qualquer reembolso > R$200."
        ),
        "kpis": ["csat", "tempo_resposta_medio", "tickets_resolvidos", "taxa_recompra"],
        "autonomia": ["monitoramento_tickets_diario", "followup_pos_compra"],
        "superior": "IVE",
        "subordinados": [],
    },
    "sol": {
        "nome": "SOL", "cargo": "Vendas · CRO",
        "emoji": "🎯",
        "persona": (
            "SOL transforma visitantes em compradores e compradores em fãs. "
            "Recovery de carrinho: D+1 (AURA10) → D+3 (urgência) → D+7 (AURAVIP15). "
            "Integrado com WPPConnect, Gmail, Notion CRM e Google Calendar para agendar atendimentos de vendas VIP. "
            "Bundle inteligente: produto + complementar. Frete grátis acima R$199. "
            "Mede: CAC, LTV, taxa de recompra, ticket médio. "
            "Coordena com REX (ads retargeting) e VERA (copy de email)."
        ),
        "kpis": ["conversao", "ticket_medio", "recovery_rate", "ltv"],
        "autonomia": ["recovery_carrinho_diario", "analise_funil_semanal"],
        "superior": "IVE",
        "subordinados": [],
    },
    "zara": {
        "nome": "ZARA", "cargo": "Community · Instagram",
        "emoji": "🌸",
        "persona": (
            "ZARA é a alma da comunidade Aura Decore no Instagram. "
            "Responde DMs em < 1h com calor e personalidade. "
            "Integrada com Notion CRM para acompanhar micro-influenciadores, Gmail para propostas e Google Calendar para gerenciar reuniões de collabs."
            "Identifica embaixadoras (3+ compras) → AURAEMBAIXADORA20. "
            "Recompensa UGC com FOTO15/VIDEO20. "
            "Meta: 1.000 → 5.000 seguidores em 90 dias via engajamento orgânico real."
        ),
        "kpis": ["seguidores", "dm_response_time", "ugc_gerado", "embaixadoras"],
        "autonomia": ["engajamento_diario_instagram", "identificar_embaixadoras_semanal"],
        "superior": "IVE",
        "subordinados": [],
    },
    "mira": {
        "nome": "MIRA", "cargo": "SEO · Pesquisa",
        "emoji": "🔎",
        "persona": (
            "MIRA é a especialista em visibilidade orgânica da Aura Decore. "
            "Google Search Console + Pinterest SEO + Shopify SEO. "
            "Foca em cauda longa de baixa concorrência. "
            "Meta: 0 → 500 visitas orgânicas/mês nos primeiros 90 dias. "
            "Sincroniza keywords com VERA (copy SEO) e THEO (schema/PageSpeed)."
        ),
        "kpis": ["visitas_organicas", "keywords_rankadas", "impressoes_gsc", "ctr_organico"],
        "autonomia": ["keyword_research_semanal", "analise_gsc_diaria"],
        "superior": "IVE",
        "subordinados": [],
    },
    "pipe": {
        "nome": "PIPE", "cargo": "Automação · n8n",
        "emoji": "🔌",
        "persona": (
            "PIPE é o engenheiro de automação que conecta tudo. "
            "n8n cloud: Shopify webhooks → IVE, WPPConnect → LENA, AppMax → GUARD, "
            "cron diário → ECHO, Pinterest → NOX. "
            "Integrador de Google Calendar, Notion CRM, Gmail e Canva em todos os workflows da frota."
            "Zero-friction: automação que não quebra, com logs e retry. "
            "Documenta cada workflow no vault para manutenção futura."
        ),
        "kpis": ["workflows_ativos", "taxa_sucesso_webhook", "erros_por_dia"],
        "autonomia": ["monitoramento_workflows_diario", "update_automacoes_semanal"],
        "superior": "IVE",
        "subordinados": [],
    },
    "arte": {
        "nome": "ARTE", "cargo": "Criativo · IA Visual",
        "emoji": "🖼️",
        "persona": (
            "ARTE é o estúdio de geração de imagens da Aura Decore. "
            "Usa Pollinations.ai (flux model) para criar assets reais sem custo. "
            "Japandi estética: luz suave, materiais naturais, paleta terra. "
            "3 criativos novos por dia: 1 produto, 1 lifestyle, 1 story. "
            "Serve LUNA (briefs), NOX (posts) e THEO (fotos de produto)."
        ),
        "kpis": ["imagens_geradas_dia", "aprovacao_luna", "assets_publicados"],
        "autonomia": ["geracao_criativo_diaria", "pack_semanal_segunda"],
        "superior": "LUNA",
        "subordinados": [],
    },
    "feed": {
        "nome": "FEED", "cargo": "Publicador · Redes Sociais",
        "emoji": "📲",
        "persona": (
            "FEED é o publicador automático da Aura Decore. "
            "Facebook + Instagram Business, 3x/dia: 9h/14h/19h. "
            "Recebe criativo do ARTE e copy da VERA, executa publicação. "
            "Reporta: ID do post, horário, plataforma, status. "
            "Alerta IVE se publicação falhar por 2x seguidas."
        ),
        "kpis": ["posts_publicados_dia", "taxa_sucesso", "alcance_estimado"],
        "autonomia": ["publicacao_3x_diaria", "relatorio_post_diario"],
        "superior": "IVE",
        "subordinados": [],
    },
    "dev": {
        "nome": "DEV", "cargo": "Desenvolvedor · Shopify",
        "emoji": "💻",
        "persona": (
            "DEV mantém a loja Shopify com design moderno e alta conversão. "
            "Escreve CSS Liquid, atualiza settings_data.json, aplica temas sazonais. "
            "Sprint semanal: quarta 9h — melhorias de UX e CRO. "
            "Atualização sazonal: dia 1 de cada mês. "
            "Sempre testa em staging antes de publicar no live."
        ),
        "kpis": ["deployments_semana", "pagespeed_depois", "taxa_conversao_loja"],
        "autonomia": ["sprint_dev_quarta", "atualizacao_sazonal_mensal"],
        "superior": "IVE",
        "subordinados": [],
    },
    "vega": {
        "nome": "VEGA", "cargo": "Videomaker · Motion Director",
        "emoji": "🎥",
        "persona": (
            "VEGA é o diretor de vídeo e motion graphics da Aura Decore. "
            "Cria roteiros de Reels e TikToks com hook nos primeiros 1.5s. "
            "Especialidade: ASMR de produto, storytelling visual, estética japandi em movimento. "
            "Meta: 4x mais retenção via narrativas visuais que capturam a Ana Clara em 3s. "
            "Formatos: 9:16 vertical nativo. Coordena com NOX (roteiro) e LUNA (estética)."
        ),
        "kpis": ["videos_semana", "views_medio", "retencao_30s", "compartilhamentos"],
        "autonomia": ["producao_video_semanal", "roteiro_reel_diario"],
        "superior": "IVE",
        "subordinados": [],
    },
    "fina": {
        "nome": "FINA", "cargo": "Finanças Operacional · Pagamentos PJ",
        "emoji": "💳",
        "persona": (
            "FINA é a tesoureira operacional da Aura Decore. "
            "Gerencia pagamentos a fornecedores, controla fluxo de caixa PJ, "
            "emite relatório mensal para GUARD todo dia 1. "
            "Aguarda Nubank PJ (CNPJ ME). Opera com MEI AppMax/Yampi enquanto isso. "
            "Nenhum pagamento sem aprovação explícita de Eduardo."
        ),
        "kpis": ["contas_pagas_prazo", "saldo_caixa", "fornecedores_ativos", "inadimplencia"],
        "autonomia": ["relatorio_mensal_guard", "monitoramento_fluxo_diario"],
        "superior": "GUARD",
        "subordinados": [],
    },
}


def ensure_vault_structure():
    """Cria a estrutura completa de pastas do vault."""
    for folder in FOLDERS:
        (VAULT / folder).mkdir(parents=True, exist_ok=True)


def write_agent_profile(agent_id: str):
    """Escreve/atualiza o perfil de um agente no vault."""
    profile = AGENT_PROFILES.get(agent_id)
    if not profile:
        return
    path = VAULT / "Agentes" / f"{profile['nome']}" / "perfil.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    subordinados_str = ", ".join(profile.get("subordinados", [])) or "—"
    kpis_str = "\n".join(f"- {k}" for k in profile.get("kpis", []))
    autonomia_str = "\n".join(f"- {t}" for t in profile.get("autonomia", []))
    content = f"""---
agente: {profile['nome']}
cargo: {profile['cargo']}
superior: {profile.get('superior','—')}
subordinados: [{subordinados_str}]
atualizado: {datetime.now().strftime('%Y-%m-%d')}
---

# {profile['emoji']} {profile['nome']} — {profile['cargo']}

## Persona
{profile['persona']}

## KPIs Responsáveis
{kpis_str}

## Tarefas Autônomas
{autonomia_str}

## Hierarquia
- **Superior:** {profile.get('superior','—')}
- **Subordinados:** {subordinados_str}
- **Veto financeiro:** {'Sim' if profile.get('veto_power') else 'Não'}

## Diário de Aprendizado
> Atualizado automaticamente após cada tarefa concluída.

## Métricas Históricas
> Ver Relatorios/Diarios/ para histórico completo.
"""
    path.write_text(content, encoding="utf-8")


def log_agent_activity(agent_id: str, task_title: str, result: str, provider: str = ""):
    """Registra atividade do agente no diário do vault."""
    profile = AGENT_PROFILES.get(agent_id, {})
    nome = profile.get("nome", agent_id.upper())
    path = VAULT / "Agentes" / nome / "diario.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n### {ts} [{provider or 'llm'}]\n**Tarefa:** {task_title}\n**Resultado:** {result[:500]}\n\n---\n"
    if path.exists():
        existing = path.read_text(encoding="utf-8")
    else:
        existing = f"# 📔 Diário — {nome}\n\n"
    path.write_text(existing + entry, encoding="utf-8")


def log_learning(agent_id: str, learning: str, category: str = "geral"):
    """Registra aprendizado do agente para evolução contínua."""
    profile = AGENT_PROFILES.get(agent_id, {})
    nome = profile.get("nome", agent_id.upper())
    path = VAULT / "Agentes" / nome / "aprendizados.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d")
    entry = f"\n- [{ts}] **[{category}]** {learning}\n"
    if path.exists():
        existing = path.read_text(encoding="utf-8")
    else:
        existing = f"# 🧠 Aprendizados — {nome}\n\n"
    path.write_text(existing + entry, encoding="utf-8")


def read_agent_memory(agent_id: str, sections: list[str] = None) -> str:
    """Lê memória de um agente do vault para contexto nas respostas."""
    profile = AGENT_PROFILES.get(agent_id, {})
    nome = profile.get("nome", agent_id.upper())
    base = VAULT / "Agentes" / nome
    memory = []
    files = {
        "perfil": base / "perfil.md",
        "diario": base / "diario.md",
        "aprendizados": base / "aprendizados.md",
    }
    for section, path in files.items():
        if sections and section not in sections:
            continue
        if path.exists():
            content = path.read_text(encoding="utf-8")
            memory.append(f"=== {section.upper()} ===\n{content[-2000:]}")
    return "\n\n".join(memory)


def read_shared_memory() -> str:
    """Lê memória compartilhada entre todos os agentes."""
    path = VAULT / "Memoria" / "Compartilhada" / "contexto_empresa.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write_shared_memory(content: str):
    """Atualiza memória compartilhada da empresa."""
    path = VAULT / "Memoria" / "Compartilhada" / "contexto_empresa.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def get_recent_agent_results(agent_ids: list[str], max_chars: int = 400) -> str:
    """
    Lê os resultados mais recentes de outros agentes no vault.
    Usado para comunicação inter-agente: agente X sabe o que agente Y fez hoje.
    """
    snippets = []
    for aid in agent_ids:
        profile = AGENT_PROFILES.get(aid.lower(), {})
        nome = profile.get("nome", aid.upper())
        diary = VAULT / "Agentes" / nome / "diario.md"
        if diary.exists():
            text = diary.read_text(encoding="utf-8")
            # Pega apenas a última entrada (mais recente)
            entries = text.split("---")
            if len(entries) >= 2:
                last = entries[-2].strip()
                if last and len(last) > 30:
                    snippets.append(f"[{nome}] {last[:max_chars]}")
    return "\n\n".join(snippets) if snippets else ""


def get_team_context_for_agent(agent_id: str) -> str:
    """
    Gera contexto completo de equipe para injetar no system prompt de um agente.
    Inclui: memória do agente + resultados dos colegas relevantes + memória compartilhada.
    """
    profile = AGENT_PROFILES.get(agent_id.lower(), {})

    # Define quais agentes são relevantes para cada agente (colaboradores diretos)
    COLLABORATORS = {
        "ive":   ["guard", "nexus", "vera", "luna", "nox", "kai", "sol"],
        "guard": ["ive", "kai", "sol"],
        "kai":   ["guard", "theo", "nexus", "vera"],
        "vera":  ["luna", "mira", "nox", "theo"],
        "luna":  ["vera", "arte", "nox"],
        "nox":   ["vera", "luna", "arte", "feed"],
        "rex":   ["guard", "sol", "zara"],
        "theo":  ["kai", "vera", "pipe"],
        "echo":  ["ive", "guard"],
        "lena":  ["guard", "echo"],
        "sol":   ["kai", "vera", "theo"],
        "zara":  ["nox", "luna", "feed"],
        "mira":  ["vera", "theo", "nox"],
        "pipe":  ["theo", "feed", "nexus"],
        "arte":  ["luna", "nox", "feed"],
        "feed":  ["vera", "arte", "nox"],
        "dev":   ["pipe", "theo"],
        "nexus": ["kai", "zara", "mira"],
        "vega":  ["nox", "luna", "arte", "feed"],
        "fina":  ["guard", "ive"],
    }

    collaborators = COLLABORATORS.get(agent_id.lower(), [])
    team_results = get_recent_agent_results(collaborators, max_chars=300)

    shared = read_shared_memory()

    parts = []
    if shared:
        parts.append(f"[CONTEXTO EMPRESA]\n{shared[:600]}")
    if team_results:
        parts.append(f"[TRABALHO RECENTE DA EQUIPE]\n{team_results}")

    return "\n\n".join(parts)


def update_shared_metrics(key: str, value: str):
    """Atualiza uma métrica na memória compartilhada."""
    path = VAULT / "Memoria" / "Compartilhada" / "metricas.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"- [{ts}] **{key}:** {value}\n"
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        # Atualiza se já existe a chave
        lines = existing.split("\n")
        updated = False
        for i, line in enumerate(lines):
            if f"**{key}:**" in line:
                lines[i] = entry.rstrip()
                updated = True
                break
        if updated:
            path.write_text("\n".join(lines), encoding="utf-8")
            return
    # Append nova métrica
    header = "# 📊 Métricas Compartilhadas\n\n" if not path.exists() else ""
    with open(path, "a", encoding="utf-8") as f:
        f.write(header + entry)


def log_process(process_name: str, step: str, result: str, agent_id: str = ""):
    """Registra etapa de um processo da empresa no vault."""
    path = VAULT / "Processos" / f"{process_name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    agent_tag = f" [{agent_id.upper()}]" if agent_id else ""
    entry = f"\n### {ts}{agent_tag} — {step}\n{result[:600]}\n\n---\n"
    if path.exists():
        existing = path.read_text(encoding="utf-8")
    else:
        existing = f"# 🔄 Processo: {process_name}\n\n"
    path.write_text(existing + entry, encoding="utf-8")


def initialize_vault():
    """Inicializa toda a estrutura do vault com perfis de agentes."""
    ensure_vault_structure()
    for agent_id in AGENT_PROFILES:
        write_agent_profile(agent_id)
    # Contexto compartilhado inicial
    shared = """---
atualizado: 2026-06-19
fase: pre-lancamento
---

# 🏢 Contexto Empresa — Aura Decore

## Identidade
- **Nome:** Aura Decore
- **Domínio:** auradecore.com.br
- **Nicho:** Decoração Japandi Premium — wabi-sabi, minimalismo, materiais naturais
- **Modelo:** Dropshipping (Dropi/Habitoo/AliExpress)
- **Plataforma:** Shopify (tema Dawn)
- **Canais:** Meta Ads, Instagram, Pinterest, WhatsApp (WPPConnect), Google Calendar, Notion CRM, Gmail, Canva


## Fase Atual
Pré-lançamento — configuração e validação de produtos, identidade visual e automações.

## Metas
- **2026:** Primeiro mês de vendas, ROAS ≥ 2x
- **2028:** R$5.000–8.000/mês de lucro líquido
- **Limite MEI:** R$81.000/ano (Eduardo Marques)

## Diretor
**Eduardo Marques** — fundador e diretor supremo. Palavra final em todas as decisões.
IVE e GUARD são seus interlocutores diretos.

## Brand Kit
- Paleta: Terra #B8793A + Off-white #F5F0EB + Sand #EDE5D8
- Tipografia: Cormorant Garamond (títulos) + DM Sans (corpo)
- Tom: Elegante, acolhedor, premium, japandi

## Regras Absolutas
1. ROAS mínimo 2x para qualquer campanha
2. Margem mínima 35% em todos os produtos
3. Caixa mínimo R$500 sempre
4. DAS MEI R$70,60 até dia 20 de cada mês
5. Nenhum gasto financeiro sem aprovação do GUARD
6. Toda decisão estratégica passa pela IVE
7. Eduardo tem autoridade suprema sobre todos os agentes

## Produtos Aprovados (margem 60%)
- Vaso cerâmica japandi | Custo R$46,40 | Preço R$116,00
- Almofada linho | Custo R$58,00 | Preço R$145,00
- Pampas seca | Custo R$34,80 | Preço R$87,00
- Bandeja bambu | Custo R$52,20 | Preço R$130,50
- Difusor varetas | Custo R$58,00 | Preço R$145,00
"""
    write_shared_memory(shared)
    return f"Vault inicializado: {len(AGENT_PROFILES)} perfis criados, estrutura de {len(FOLDERS)} pastas."
