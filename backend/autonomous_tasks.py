# -*- coding: utf-8 -*-
"""
autonomous_tasks.py — Tarefas Autônomas dos 15 Agentes Aura Decore
Define as tarefas periódicas que cada agente executa sem ordem explícita.
Integrado ao scheduler do main.py via APScheduler.

Hierarquia de autonomia:
  NEXUS → coordena todos
  IVE/GUARD → validam antes de executar
  Agentes operacionais → executam no horário programado
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Coroutine

BRT = timezone(timedelta(hours=-3))


def _now_brt() -> str:
    return datetime.now(BRT).strftime("%Y-%m-%d %H:%M BRT")


def _today() -> str:
    return datetime.now(BRT).strftime("%Y-%m-%d")


# ── Definições de tarefas autônomas por agente ────────────────────────────────
# Formato: lista de dicts com campos:
#   agent, title, prompt_system, prompt_user, schedule (cron-like desc), max_tokens

AUTONOMOUS_TASKS = [

    # ── KAI — Análise financeira diária ──────────────────────────────────────
    {
        "agent": "KAI",
        "id": "kai_daily_margin",
        "title": "KAI · Revisão de margem diária",
        "schedule": "daily_9h",
        "max_tokens": 500,
        "system": (
            "Você é KAI — analista financeiro da Aura Decore. "
            "Especialista em margens, custos e precificação de produtos dropshipping japandi. "
            "Seja preciso, use números, foco em decisão imediata."
        ),
        "user": (
            f"Data: {_today()}\n"
            "Execute sua revisão financeira matinal:\n"
            "1. Analise se os produtos principais da Aura Decore (vasos, almofadas, bandejas, difusores, quadros) "
            "estão com margem de pelo menos 55% (considerando custo dropship + frete + plataforma)\n"
            "2. Identifique qual produto tem maior ROI potencial para impulsionar hoje\n"
            "3. Alerta de preço se algum concorrente pratica preço muito abaixo\n"
            "Resposta: relatório financeiro conciso com recomendação de ação para Eduardo."
        ),
    },

    # ── VERA — Copy diária para produto destaque ──────────────────────────────
    {
        "agent": "VERA",
        "id": "vera_daily_copy",
        "title": "VERA · Copy produto destaque do dia",
        "schedule": "daily_8h30",
        "max_tokens": 600,
        "system": (
            "Você é VERA — copywriter da Aura Decore. "
            "Especialista em textos persuasivos para decoração japandi/wabi-sabi. "
            "Tom: elegante, emocional, premium. Nunca use clichês genéricos."
        ),
        "user": (
            f"Data: {_today()}\n"
            "Gere a copy do PRODUTO DESTAQUE do dia:\n"
            "Produto: Vaso Cerâmica Japandi com Flores Secas\n"
            "Entregue:\n"
            "1. Título SEO (até 60 chars)\n"
            "2. Subtítulo emocional (até 100 chars)\n"
            "3. Descrição produto Shopify (150-200 palavras, HTML simples)\n"
            "4. Caption Instagram (até 150 chars + 10 hashtags)\n"
            "5. CTA para stories ('Deslize para ver' estilo)\n"
            "Use linguagem que ressoa com mulheres 28-45 anos, classe B/A, que buscam calma e estética."
        ),
    },

    # ── LUNA — Brief criativo semanal ─────────────────────────────────────────
    {
        "agent": "LUNA",
        "id": "luna_weekly_brief",
        "title": "LUNA · Brief criativo semanal",
        "schedule": "weekly_monday_8h",
        "max_tokens": 600,
        "system": (
            "Você é LUNA — diretora de arte da Aura Decore. "
            "Especialista em estética japandi, wabi-sabi, minimalismo. "
            "Guia a identidade visual da marca com sensibilidade e precisão."
        ),
        "user": (
            f"Semana iniciando {_today()}\n"
            "Crie o BRIEF CRIATIVO DA SEMANA para a Aura Decore:\n"
            "1. Tema visual da semana (conceito + palavras-chave estéticas)\n"
            "2. Paleta de cores dominante (3 cores + hex)\n"
            "3. Produtos para destacar visualmente (3 produtos)\n"
            "4. Estilo fotográfico (mood, ângulos, props sugeridos)\n"
            "5. Prompt ImageGen para imagem hero da semana\n"
            "6. Diretrizes para ARTE e FEED seguirem esta semana\n"
            "Alinhado com a identidade: terracota #B8793A, off-white #F5F0EB, japandi lifestyle."
        ),
    },

    # ── NOX — Calendário de conteúdo semanal ─────────────────────────────────
    {
        "agent": "NOX",
        "id": "nox_weekly_calendar",
        "title": "NOX · Calendário de conteúdo semanal",
        "schedule": "weekly_monday_9h",
        "max_tokens": 700,
        "system": (
            "Você é NOX — estrategista de conteúdo da Aura Decore. "
            "Planeja e organiza toda a pauta de conteúdo nas redes sociais. "
            "Foco em consistência, engajamento e conversão."
        ),
        "user": (
            f"Semana iniciando {_today()}\n"
            "Crie o CALENDÁRIO DE CONTEÚDO DA SEMANA:\n"
            "- Instagram: 1 post/dia (seg a sáb) + 3 stories/dia\n"
            "- Facebook: 3 posts/semana\n"
            "Para cada post defina: tema, formato (feed/carrossel/reel/story), "
            "produto/assunto, horário ideal, objetivo (awareness/engajamento/conversão)\n"
            "Inclua 2 datas comemorativas ou tendências relevantes da semana.\n"
            "Formato tabela markdown."
        ),
    },

    # ── REX — Crescimento orgânico semanal ───────────────────────────────────
    {
        "agent": "REX",
        "id": "rex_weekly_organic_growth",
        "title": "REX · Estratégia de crescimento orgânico semanal",
        "schedule": "weekly_friday_17h",
        "max_tokens": 600,
        "system": (
            "Você é REX — estrategista de crescimento ORGÂNICO da Aura Decore. "
            "IMPORTANTE: tráfego pago ainda NÃO foi iniciado. Foco 100% em orgânico: "
            "Instagram, Pinterest, SEO, parcerias, conteúdo viral, UGC. "
            "Nunca mencione Meta Ads, CPA, ROAS, CPM ou qualquer métrica de anúncio pago."
        ),
        "user": (
            f"Encerrando semana de {_today()}\n"
            "Gere a ANÁLISE DE CRESCIMENTO ORGÂNICO da semana:\n"
            "1. Crescimento de seguidores @auras.decore (Instagram + Facebook)\n"
            "2. Desempenho de conteúdo orgânico: quais formatos engajaram mais?\n"
            "3. Oportunidades de crescimento orgânico para a próxima semana\n"
            "4. 3 perfis de micro-influenciadores japandi/home decor para abordar\n"
            "5. Tendências de conteúdo orgânico que podemos explorar (TikTok, Pinterest, Reels)\n"
            "6. Ação orgânica #1 para Eduardo aprovar\n"
            "Foco: crescimento sem custo de mídia paga."
        ),
    },

    # ── THEO — Auditoria de catálogo ─────────────────────────────────────────
    {
        "agent": "THEO",
        "id": "theo_daily_catalog",
        "title": "THEO · Auditoria de catálogo Shopify",
        "schedule": "daily_10h",
        "max_tokens": 500,
        "system": (
            "Você é THEO — gerente de catálogo da Aura Decore. "
            "Responsável por manter os produtos na Shopify completos, otimizados e vendedores."
        ),
        "user": (
            f"Data: {_today()}\n"
            "Execute a AUDITORIA DIÁRIA DE CATÁLOGO:\n"
            "1. Identifique produtos que precisam de atualização (descrição, fotos, SEO)\n"
            "2. Verifique se algum produto está sem estoque ou com preço desatualizado\n"
            "3. Recomende produto para criar/adicionar ao catálogo hoje\n"
            "4. Liste top 3 produtos com maior potencial de conversão\n"
            "Produtos principais: vasos cerâmica, almofadas linho, bandejas bambu, "
            "difusores varetas, quadros minimalistas, velas perfumadas, porta-retratos."
        ),
    },

    # ── ECHO — Monitoramento SAC ──────────────────────────────────────────────
    {
        "agent": "ECHO",
        "id": "echo_daily_sac",
        "title": "ECHO · Monitoramento SAC e pós-venda",
        "schedule": "daily_8h",
        "max_tokens": 400,
        "system": (
            "Você é ECHO — agente de suporte e relacionamento da Aura Decore. "
            "Garante a satisfação total do cliente e transforma problemas em oportunidades."
        ),
        "user": (
            f"Data: {_today()}\n"
            "Execute o CHECK MATINAL DE SAC:\n"
            "1. Gere modelo de resposta para os 3 problemas mais comuns "
            "(atraso no prazo, produto diferente da foto, dúvida de tamanho)\n"
            "2. Crie 1 mensagem de pós-venda para enviar 3 dias após entrega\n"
            "3. Sugira 1 ação de fidelização (ex: cupom especial, brinde, upsell)\n"
            "Tom: acolhedor, gentil, resolutivo. Reflete os valores japandi da marca."
        ),
    },

    # ── LENA — Análise de fornecedores ───────────────────────────────────────
    {
        "agent": "LENA",
        "id": "lena_weekly_suppliers",
        "title": "LENA · Análise de fornecedores e logística",
        "schedule": "weekly_wednesday_10h",
        "max_tokens": 500,
        "system": (
            "Você é LENA — gestora de logística e fornecedores da Aura Decore. "
            "Garante prazos, qualidade dos produtos e eficiência da cadeia de dropshipping."
        ),
        "user": (
            f"Data: {_today()}\n"
            "Execute a REVISÃO SEMANAL DE FORNECEDORES:\n"
            "1. Avalie os principais fornecedores dropshipping de decoração japandi "
            "(AliExpress, Shopee, fornecedores nacionais)\n"
            "2. Compare prazos de entrega: SE vs SP vs Nacional\n"
            "3. Recomende 1 novo produto/fornecedor para testar\n"
            "4. Calcule custo-benefício frete para margem 55%+ com frete grátis\n"
            "5. Alerta se algum fornecedor tem estoque crítico"
        ),
    },

    # ── SOL — CRO diário ─────────────────────────────────────────────────────
    {
        "agent": "SOL",
        "id": "sol_daily_cro",
        "title": "SOL · Otimização de conversão diária",
        "schedule": "daily_11h",
        "max_tokens": 500,
        "system": (
            "Você é SOL — especialista em CRO (Conversion Rate Optimization) da Aura Decore. "
            "Obsecado em transformar visitantes em compradores. "
            "Data-driven, criativo com testes A/B, foco no checkout."
        ),
        "user": (
            f"Data: {_today()}\n"
            "Execute a ANÁLISE CRO DIÁRIA:\n"
            "1. Identifique o maior gargalo de conversão na jornada do cliente "
            "(awareness → interesse → desejo → compra)\n"
            "2. Proponha 1 teste A/B para implementar hoje (elemento, hipótese, métrica)\n"
            "3. Revise o checkout: há alguma fricção para remover?\n"
            "4. Sugira 1 trigger psicológico para adicionar na página de produto "
            "(urgência, prova social, escassez, autoridade)\n"
            "5. Meta de taxa de conversão: qual seria realista para loja japandi nicho?"
        ),
    },

    # ── ZARA — Análise de tendências ─────────────────────────────────────────
    {
        "agent": "ZARA",
        "id": "zara_weekly_trends",
        "title": "ZARA · Tendências e análise de mercado",
        "schedule": "weekly_tuesday_9h",
        "max_tokens": 600,
        "system": (
            "Você é ZARA — analista de tendências e mercado da Aura Decore. "
            "Antecipa movimentos do mercado de decoração, identifica oportunidades "
            "e monitora a concorrência no segmento japandi brasileiro."
        ),
        "user": (
            f"Semana de {_today()}\n"
            "Execute a ANÁLISE DE TENDÊNCIAS SEMANAL:\n"
            "1. Top 3 tendências em decoração/home decor no Brasil agora "
            "(Pinterest, TikTok, Instagram BR)\n"
            "2. Análise de 2 concorrentes diretos (marcas que vendem japandi online BR)\n"
            "3. Oportunidade de nicho sub-explorada no mercado\n"
            "4. Sazonalidade: o que está em alta nos próximos 30 dias?\n"
            "5. Produto japonês/nórdico/wabi-sabi que devemos importar/adicionar\n"
            "Formato: insights acionáveis, não ensaio teórico."
        ),
    },

    # ── MIRA — SEO semanal ───────────────────────────────────────────────────
    {
        "agent": "MIRA",
        "id": "mira_weekly_seo",
        "title": "MIRA · Análise SEO e palavras-chave",
        "schedule": "weekly_thursday_9h",
        "max_tokens": 600,
        "system": (
            "Você é MIRA — especialista em SEO da Aura Decore. "
            "Domina pesquisa de palavras-chave, otimização técnica e conteúdo orgânico. "
            "Foco em tráfego qualificado para loja de decoração japandi."
        ),
        "user": (
            f"Semana de {_today()}\n"
            "Execute a ANÁLISE SEO SEMANAL:\n"
            "1. Top 10 palavras-chave prioritárias para Aura Decore "
            "(decoração japandi, wabi-sabi, home decor minimalista BR)\n"
            "2. Identifique 3 keywords de cauda longa com baixa concorrência\n"
            "3. Proponha 1 post de blog para esta semana (título, estrutura H2/H3, keywords)\n"
            "4. Meta title e meta description para produto principal (vaso cerâmica)\n"
            "5. Ação técnica SEO prioritária para Shopify (schema, velocidade, alt text)"
        ),
    },

    # ── PIPE — Auditoria de automações ───────────────────────────────────────
    {
        "agent": "PIPE",
        "id": "pipe_weekly_automations",
        "title": "PIPE · Auditoria de automações e integrações",
        "schedule": "weekly_wednesday_14h",
        "max_tokens": 500,
        "system": (
            "Você é PIPE — arquiteto de automações da Aura Decore. "
            "Especialista em n8n, webhooks, Zapier e integrações entre sistemas. "
            "Elimina trabalho manual e cria fluxos inteligentes."
        ),
        "user": (
            f"Data: {_today()}\n"
            "Execute a AUDITORIA DE AUTOMAÇÕES:\n"
            "1. Liste as 5 automações mais críticas para a Aura Decore rodar hoje\n"
            "2. Identifique 1 processo manual que pode ser automatizado esta semana\n"
            "3. Proponha workflow n8n para: novo pedido Shopify → notificação WhatsApp Eduardo\n"
            "4. Como automatizar o agendamento de posts do NOX com o FEED?\n"
            "5. Integração prioritária: qual sistema conectar ao Shopify agora?"
        ),
    },

    # ── ARTE — Assets visuais diários ────────────────────────────────────────
    {
        "agent": "ARTE",
        "id": "arte_daily_assets",
        "title": "ARTE · Geração de assets visuais",
        "schedule": "daily_9h30",
        "max_tokens": 400,
        "system": (
            "Você é ARTE — criador de assets visuais IA da Aura Decore. "
            "Especialista em gerar imagens via Pollinations.ai no estilo japandi/wabi-sabi. "
            "Cada imagem deve ser específica, rica em detalhes visuais."
        ),
        "user": (
            f"Data: {_today()}\n"
            "Gere o BRIEFING DE ASSETS VISUAIS DO DIA:\n"
            "1. Prompt para imagem do produto destaque de hoje (feed Instagram 1080x1080)\n"
            "2. Prompt para story do dia (1080x1920 vertical)\n"
            "3. Prompt para imagem ambiente/lifestyle (produto em uso)\n"
            "Cada prompt deve ter: produto principal, cenário, iluminação, ângulo, mood, "
            "referência de estilo. Use vocabulário visual rico. "
            "Inclua no prompt: japandi minimalist, wabi-sabi, natural earth tones, warm light."
        ),
    },

    # ── DEV — Health check técnico ───────────────────────────────────────────
    {
        "agent": "DEV",
        "id": "dev_daily_health",
        "title": "DEV · Health check do sistema",
        "schedule": "daily_7h",
        "max_tokens": 400,
        "system": (
            "Você é DEV — desenvolvedor técnico da Aura Decore. "
            "Mantém o sistema de agentes funcionando, corrige bugs e melhora a infra."
        ),
        "user": (
            f"Data: {_today()}\n"
            "Execute o HEALTH CHECK MATINAL DO SISTEMA:\n"
            "1. Pontos de atenção técnica do sistema de agentes (APIs, LLM cascade, banco)\n"
            "2. Groq: qual o status do limite diário? Estratégia se esgotar?\n"
            "3. Shopify API: há chamadas pendentes ou erros recentes?\n"
            "4. Pollinations.ai: status do serviço de geração de imagens\n"
            "5. 1 melhoria técnica prioritária para implementar hoje\n"
            "Resposta técnica e acionável. Alerte se há risco de downtime."
        ),
    },

    # ── NEXUS — Sincronização de agentes ─────────────────────────────────────
    {
        "agent": "NEXUS",
        "id": "nexus_daily_sync",
        "title": "NEXUS · Sincronização e briefing de agentes",
        "schedule": "daily_8h",
        "max_tokens": 600,
        "system": (
            "Você é NEXUS — coordenador central dos agentes da Aura Decore. "
            "Garante que todos os agentes estejam alinhados, sem conflitos, "
            "e trabalhando em sinergia para os objetivos da empresa."
        ),
        "user": (
            f"Data: {_today()}\n"
            "Execute a SINCRONIZAÇÃO MATINAL DOS AGENTES:\n"
            "1. Briefing do dia: qual é a prioridade #1 de hoje para a Aura Decore?\n"
            "2. Distribuição de foco: quais agentes devem colaborar hoje?\n"
            "   (ex: LUNA + ARTE para assets, VERA + MIRA para SEO+copy, KAI + SOL para conversão)\n"
            "3. Alerta de dependência: alguma tarefa de um agente bloqueia outro?\n"
            "4. Check de comunicação: há algo que Eduardo precisa decidir AGORA?\n"
            "5. Motivação do dia: uma frase de foco para toda a equipe de agentes\n"
            "Resposta estruturada, como um briefing de reunião matinal de equipe."
        ),
    },

    # ══════════════════════════════════════════════════════════════
    # ESTRATÉGIA LOW-TICKET — Adicionada após lançamento dos 8 novos
    # produtos de entrada (R$19-49) em 2026-05-29
    # ══════════════════════════════════════════════════════════════

    # ── KAI — Análise de conversão low-ticket ────────────────────
    {
        "agent": "KAI",
        "id": "kai_lowticket_analysis",
        "title": "KAI · Análise de conversão dos produtos low-ticket",
        "schedule": "daily_9h",
        "max_tokens": 500,
        "system": (
            "Você é KAI — curador de produtos da Aura Decore. "
            "Especialista em funil de produtos: low-ticket como porta de entrada para premium."
        ),
        "user": (
            f"Data: {_today()}\n"
            "PRODUTOS LOW-TICKET ATIVOS (R$19-49):\n"
            "Sachê Aromático R$19,90 | Marcadores Bambu R$22,90 | Pedras Suiseki R$24,90 | "
            "Palo Santo R$24,90 | Kit Incenso R$29,90 | Porta-Incenso R$29,90 | "
            "Mini Vaso Pocket R$39,90 | Mini Kit Zen R$49,90\n\n"
            "Análise diária:\n"
            "1. Qual produto low-ticket tem maior potencial de conversão HOJE?\n"
            "2. Sugira 1 combo irresistível (low + mid-ticket, total abaixo de R$100)\n"
            "3. Qual produto de entrada leva mais facilmente ao upsell premium?\n"
            "4. Recomendação de produto para destacar no feed/stories hoje\n"
            "5. Alerta: algum produto low-ticket precisa de ajuste de preço ou copy?"
        ),
    },

    # ── SOL — Funil low→premium ──────────────────────────────────
    {
        "agent": "SOL",
        "id": "sol_lowticket_funnel",
        "title": "SOL · Funil low-ticket → premium — CRO diário",
        "schedule": "daily_11h",
        "max_tokens": 500,
        "system": (
            "Você é SOL — especialista em CRO da Aura Decore. "
            "Foco em funil: primeira compra low-ticket → upsell mid/premium."
        ),
        "user": (
            f"Data: {_today()}\n"
            "FUNIL ATUAL:\n"
            "Entrada: Sachê R$19,90, Marcadores R$22,90, Pedras R$24,90, Palo Santo R$24,90, "
            "Incenso R$29,90, Porta-Incenso R$29,90, Mini Vaso R$39,90, Mini Kit Zen R$49,90\n"
            "Mid: Difusor Lavanda R$109, Vela Soja R$89, Bandeja Bambu R$79-139\n"
            "Premium: Vaso Wabi-Sabi R$129, Vaso Oval R$149\n\n"
            "Otimize o funil hoje:\n"
            "1. Sequência de email pós-compra low-ticket: D+1, D+3, D+7 (produto sugerido em cada)\n"
            "2. Qual produto mid-ticket oferece no checkout junto com o Mini Kit Zen?\n"
            "3. Gatilho de urgência para converter visitantes em compradores do sachet (R$19,90)\n"
            "4. Como aumentar o ticket médio de R$25 para R$89 em 30 dias?\n"
            "5. Bundle flash recomendado para esta semana (nome + itens + preço bundle + desconto)"
        ),
    },

    # ── REX — Crescimento orgânico low-ticket ────────────────────
    {
        "agent": "REX",
        "id": "rex_lowticket_organic",
        "title": "REX · Crescimento orgânico — estratégia low-ticket",
        "schedule": "weekly_monday_9h",
        "max_tokens": 600,
        "system": (
            "Você é REX — estrategista de crescimento ORGÂNICO da Aura Decore. "
            "Tráfego pago não iniciado. Foco exclusivo em crescimento orgânico: "
            "conteúdo, SEO, comunidade, parcerias gratuitas, viralização."
        ),
        "user": (
            f"Semana de {_today()}\n"
            "ESTRATÉGIA ORGÂNICA para os produtos low-ticket da Aura Decore:\n\n"
            "PRODUTOS DE ENTRADA:\n"
            "Sachê Aromático R$19,90 / Mini Kit Zen R$49,90 / Palo Santo R$24,90 / "
            "Pedras Suiseki R$24,90 / Kit Incenso R$29,90 / Mini Vaso Pocket R$39,90\n\n"
            "Crie a estratégia orgânica da semana:\n"
            "1. Qual produto baixo ticket tem maior potencial de viralizar no Reels? Por quê?\n"
            "2. Estratégia de hashtags para aumentar alcance orgânico desta semana\n"
            "3. Ideia de parceria gratuita: qual nicho de conta para fazer collab sem custo?\n"
            "4. Como usar o Palo Santo/Incenso para criar série de conteúdo educativo?\n"
            "5. Pinterest: como criar boards que trazem tráfego orgânico para a loja?\n"
            "6. Meta orgânica da semana: quantos seguidores novos é realista alcançar?"
        ),
    },

    # ── VERA — Copy low-ticket ────────────────────────────────────
    {
        "agent": "VERA",
        "id": "vera_lowticket_copy",
        "title": "VERA · Copy especial — produtos de entrada e presentes",
        "schedule": "weekly_tuesday_9h",
        "max_tokens": 600,
        "system": (
            "Você é VERA — copywriter da Aura Decore. "
            "Para produtos low-ticket, o ângulo é: presente para si mesma, ritual acessível, "
            "começo da jornada japandi. Tom: cálido, acessível, sem parecer barato."
        ),
        "user": (
            f"Semana de {_today()}\n"
            "Crie COPY ESPECIAL para os produtos de entrada da Aura Decore:\n\n"
            "1. SACHÊ AROMÁTICO R$19,90:\n"
            "   - Headline Instagram: (até 100 chars, gancho emocional)\n"
            "   - Caption completa (até 200 chars + 10 hashtags)\n\n"
            "2. MINI KIT ZEN R$49,90:\n"
            "   - Headline 'presente' (foco em dar de presente para si mesma)\n"
            "   - Descrição produto (100 palavras, foco em unboxing e emoção)\n\n"
            "3. PALO SANTO R$24,90:\n"
            "   - Hook de reel (3 segundos — texto na tela)\n"
            "   - Caption Instagram (foco em ritual matinal)\n\n"
            "4. EMAIL pós-compra de qualquer low-ticket:\n"
            "   Assunto + preview text + corpo (100 palavras) com upsell suave para o produto mid-ticket\n\n"
            "Tom: elegante mas acessível. Nunca use 'barato' ou 'econômico'."
        ),
    },

    # ── NOX — Conteúdo low-ticket viral ──────────────────────────
    {
        "agent": "NOX",
        "id": "nox_lowticket_content",
        "title": "NOX · Conteúdo low-ticket — ideias virais e séries",
        "schedule": "weekly_wednesday_10h",
        "max_tokens": 600,
        "system": (
            "Você é NOX — estrategista de conteúdo da Aura Decore. "
            "Produtos de baixo ticket são o melhor conteúdo: acessíveis, aspiracionais, presentáveis."
        ),
        "user": (
            f"Semana de {_today()}\n"
            "Crie PLANO DE CONTEÚDO focado em low-ticket para esta semana:\n\n"
            "PRODUTOS: Sachê R$19,90 / Palo Santo R$24,90 / Pedras Suiseki R$24,90 / "
            "Kit Incenso R$29,90 / Mini Vaso R$39,90 / Mini Kit Zen R$49,90\n\n"
            "1. SÉRIE 'Presente Perfeito Abaixo de R$50' (3 posts carrossel):\n"
            "   Slides, textos e CTA para cada post\n\n"
            "2. REEL viral: 'Transforme sua mesa de trabalho por R$25'\n"
            "   Roteiro completo: hook + desenvolvimento + reveal + CTA\n\n"
            "3. STORIES da semana — 4 stories sobre ritual matinal com Palo Santo:\n"
            "   Segunda a quinta, 1 story/dia sobre como usar\n\n"
            "4. UGC prompt: como pedir que clientes postem com #auradecore?\n"
            "   (texto da mensagem de follow-up pós-compra)"
        ),
    },

    # ── IVE — Relatório semanal geral ─────────────────────────────────────────
    {
        "agent": "IVE",
        "id": "ive_weekly_report",
        "title": "IVE · Compilação e envio do relatório semanal",
        "schedule": "weekly_sunday_21h",
        "max_tokens": 2000,
        "system": (
            "Você é IVE — CEO da Aura Decore. "
            "Sua missão é consolidar os relatórios diários, as tarefas da semana e as métricas da operação "
            "e elaborar o relatório geral para Eduardo Marques (Diretor), com foco em estratégias de crescimento e decisões urgentes."
        ),
        "user": (
            f"Fim de semana iniciando {_today()}.\n"
            "Compile e consolide o Relatório Semanal Executivo Geral da Aura Decore contendo:\n"
            "1. Resumo Geral da Semana da CEO\n"
            "2. Métricas Consolidadas de Operação (tarefas concluídas, falhas e pendentes)\n"
            "3. Análise por Área de Ação dos Agentes\n"
            "4. Problemas e Gargalos da Semana\n"
            "5. Decisões Estratégicas para o Diretor Eduardo Marques\n"
            "6. Plano de Ação e Prioridades da Próxima Semana\n"
            "Salve o relatório no vault e envie para o e-mail eduardo.marques.arq@gmail.com."
        ),
    },
]


# ── Mapa de schedule → horário UTC ──────────────────────────────────────────
# BRT = UTC-3
SCHEDULE_MAP = {
    "daily_7h":              {"hour": 10, "minute": 0,  "day_of_week": None},  # 7h BRT = 10h UTC
    "daily_8h":              {"hour": 11, "minute": 0,  "day_of_week": None},  # 8h BRT
    "daily_8h30":            {"hour": 11, "minute": 30, "day_of_week": None},  # 8h30 BRT
    "daily_9h":              {"hour": 12, "minute": 0,  "day_of_week": None},  # 9h BRT
    "daily_9h30":            {"hour": 12, "minute": 30, "day_of_week": None},  # 9h30 BRT
    "daily_10h":             {"hour": 13, "minute": 0,  "day_of_week": None},  # 10h BRT
    "daily_11h":             {"hour": 14, "minute": 0,  "day_of_week": None},  # 11h BRT
    "weekly_monday_8h":      {"hour": 11, "minute": 0,  "day_of_week": "mon"},
    "weekly_monday_9h":      {"hour": 12, "minute": 0,  "day_of_week": "mon"},
    "weekly_tuesday_9h":     {"hour": 12, "minute": 0,  "day_of_week": "tue"},
    "weekly_wednesday_10h":  {"hour": 13, "minute": 0,  "day_of_week": "wed"},
    "weekly_wednesday_14h":  {"hour": 17, "minute": 0,  "day_of_week": "wed"},
    "weekly_thursday_9h":    {"hour": 12, "minute": 0,  "day_of_week": "thu"},
    "weekly_friday_17h":     {"hour": 20, "minute": 0,  "day_of_week": "fri"},
    "weekly_sunday_21h":     {"hour": 0,  "minute": 0,  "day_of_week": "mon"},  # Domingo 21h BRT = Segunda 0h UTC
}


def get_task_by_id(task_id: str) -> dict | None:
    return next((t for t in AUTONOMOUS_TASKS if t["id"] == task_id), None)


def get_tasks_by_agent(agent: str) -> list[dict]:
    return [t for t in AUTONOMOUS_TASKS if t["agent"].upper() == agent.upper()]


def get_tasks_by_schedule(schedule: str) -> list[dict]:
    return [t for t in AUTONOMOUS_TASKS if t["schedule"] == schedule]


def list_all_schedules() -> dict[str, list[str]]:
    """Retorna mapa schedule → lista de agent:title."""
    result: dict[str, list[str]] = {}
    for task in AUTONOMOUS_TASKS:
        sch = task["schedule"]
        result.setdefault(sch, []).append(f"{task['agent']}: {task['title']}")
    return result
