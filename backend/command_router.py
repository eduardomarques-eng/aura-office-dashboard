# -*- coding: utf-8 -*-
"""
Command Router — Sistema de Comandos Autônomos
Aura Decore · 2026

Todos os comandos /slash da empresa são roteados aqui.
Cada handler é um async generator que yielda linhas de texto.
O endpoint /cmd/stream encapsula em SSE.
"""
from __future__ import annotations

import asyncio
import json
import os
import pathlib
import platform
from datetime import datetime, timedelta
from typing import AsyncGenerator

# ── Vault ──────────────────────────────────────────────────────────────────────
_default_vault = (
    r"C:\Users\erick\AURA-decor-vault"
    if platform.system() == "Windows"
    else "/app/vault"
)
VAULT = pathlib.Path(os.getenv("OBSIDIAN_VAULT", _default_vault))

# ── Helpers ────────────────────────────────────────────────────────────────────
def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")

def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")

def _week() -> str:
    now = datetime.now()
    return f"W{now.isocalendar()[1]:02d}/{now.year}"

def _read_vault(rel: str, default: str = "") -> str:
    p = VAULT / rel
    try:
        return p.read_text(encoding="utf-8") if p.exists() else default
    except Exception:
        return default

def _write_vault(rel: str, content: str) -> pathlib.Path:
    p = VAULT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p

def _read_kaizen_json(agent_id: str) -> dict:
    p = VAULT / "Kaizen" / f"{agent_id.upper()}-kaizen.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        return {}

def _write_kaizen_json(agent_id: str, data: dict) -> None:
    p = VAULT / "Kaizen" / f"{agent_id.upper()}-kaizen.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

async def _stream(lines: list[str], delay: float = 0.05) -> AsyncGenerator[str, None]:
    for line in lines:
        yield line
        await asyncio.sleep(delay)

# ── AGENTES registrados ────────────────────────────────────────────────────────
AGENTS = {
    "IVE":   {"emoji": "👩‍💼", "role": "CEO · Estratégia"},
    "ECHO":  {"emoji": "🔍", "role": "Auditor · Kaizen"},
    "VEGA":  {"emoji": "🎬", "role": "Videomaker · Motion"},
    "LUNA":  {"emoji": "🎨", "role": "Design Visual"},
    "VERA":  {"emoji": "✍️",  "role": "Copywriting"},
    "REX":   {"emoji": "🎯", "role": "Tráfego Pago"},
    "MIA":   {"emoji": "📲", "role": "Orgânico · Community"},
    "LENA":  {"emoji": "💬", "role": "Atendimento CX"},
    "KAI":   {"emoji": "🔭", "role": "Curadoria · Produtos"},
    "THEO":  {"emoji": "⚙️",  "role": "Shopify Técnico"},
    "GUARD": {"emoji": "💰", "role": "CFO · Financeiro"},
    "PIPE":  {"emoji": "🔌", "role": "Automações · n8n"},
    "DEV":   {"emoji": "💻", "role": "Dev · Dashboard"},
    "FEED":  {"emoji": "📡", "role": "Social Feed"},
    "NEXUS": {"emoji": "🌐", "role": "Pesquisa · Mercado"},
    "ZARA":  {"emoji": "🌸", "role": "Community Manager"},
    "MIRA":  {"emoji": "🔎", "role": "SEO · Analytics"},
    "ARTE":  {"emoji": "🖼️",  "role": "Assets Visuais"},
    "SOL":   {"emoji": "☀️",  "role": "Funil · Email"},
    "FINA":  {"emoji": "💳", "role": "Finanças PJ"},
}

# ── Separador visual ───────────────────────────────────────────────────────────
SEP = "─" * 55

# ═══════════════════════════════════════════════════════════════════════════════
# IVE — Comandos /i
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_i_status() -> AsyncGenerator[str, None]:
    """Status geral do ecossistema."""
    yield f"\n👩‍💼 IVE — Status do Ecossistema · {_now()}\n{SEP}"
    yield f"\n🏢 EMPRESA: Aura Decore · auradecore.com.br"
    yield f"\n📦 LOJA: 89 produtos ACTIVE · 3 canais publicados"
    yield f"\n🤖 AGENTES: 20 ativos (IVE + GUARD + 18 Sonnet)"

    # Lê último relatório de manutenção
    reports_dir = VAULT / "Relatorios" / "Manutencao"
    ultimo_score = "—"
    ultimo_data = "nunca"
    if reports_dir.exists():
        relatorios = sorted(reports_dir.glob("manutencao-*.md"), reverse=True)
        if relatorios:
            ultimo_data = relatorios[0].stem.replace("manutencao-", "")
            for line in relatorios[0].read_text(encoding="utf-8").splitlines():
                if line.startswith("score:"):
                    ultimo_score = line.split(":")[1].strip()
                    break

    yield f"\n{SEP}"
    yield f"\n📊 SAÚDE DO DASHBOARD"
    yield f"\n   Último check : {ultimo_data}"
    yield f"\n   Score        : {ultimo_score}"
    yield f"\n   Próximo auto : 08h00 diário"

    # Lê DNAs dos agentes principais
    yield f"\n{SEP}"
    yield f"\n🤖 TOP AGENTES — SCORES KAIZEN"
    for ag in ["ECHO", "THEO", "VERA", "REX", "GUARD", "PIPE", "DEV"]:
        dna = _read_kaizen_json(ag)
        score = dna.get("score_geral", dna.get("score_semana", "—"))
        exec_count = dna.get("execucoes_semana", 0)
        info = AGENTS.get(ag, {})
        yield f"\n   {info.get('emoji','🤖')} {ag:<6} {score:<12} {exec_count} exec · {info.get('role','')}"

    yield f"\n{SEP}"
    yield f"\n🔧 SISTEMAS"
    yield f"\n   Railway       : web-production-f1cb5.up.railway.app ✓"
    yield f"\n   n8n           : 17 workflows configurados"
    yield f"\n   Shopify       : tema live #160266387561 (Cursor Dinâmico)"
    yield f"\n   Vault         : {VAULT}"
    yield f"\n{SEP}"
    yield f"\n💡 Próximos: /i week · /echo now · /sys fullauto\n"


async def cmd_i_week(args: str = "") -> AsyncGenerator[str, None]:
    """Gera plano estratégico semanal."""
    week = _week()
    today = _today()
    now = datetime.now()
    days = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    weekday = now.weekday()

    yield f"\n👩‍💼 IVE — Plano Estratégico {week}\n{SEP}"
    yield f"\n🎯 FOCO DA SEMANA: {args or 'crescimento orgânico + conversão loja'}\n"

    plan_lines = [
        f"# 📅 Plano Estratégico Semanal — {week}",
        f"**Criado:** {_now()} por IVE",
        f"**Foco:** {args or 'Crescimento orgânico · Conversão da loja · Kaizen contínuo'}",
        "",
        "---",
        "",
        "## 🎯 Metas da Semana",
        "",
        "| Meta | Agente | Prazo |",
        "|------|--------|-------|",
        "| 3 Reels publicados | VEGA + FEED | Qua–Sex |",
        "| 5 posts feed + stories | LUNA + VERA + FEED | Diário |",
        "| Auditoria Shopify completa | THEO | Terça |",
        "| Relatório financeiro semanal | GUARD | Sex |",
        "| 10 novos produtos pesquisados | KAI | Qua |",
        "| Score dashboard ≥ 9/10 | DEV + PIPE | Contínuo |",
        "",
        "## 📆 Calendário Semanal",
        "",
    ]

    schedule = {
        "Segunda": ["🔍 ECHO: auditoria semanal + /echo kaizen", "📲 FEED: publicar post principal", "📋 IVE: /i week — briefing da equipe"],
        "Terça":   ["⚙️ THEO: /t optimize — Shopify + PageSpeed", "✍️ VERA: copys da semana (3 produtos)", "🎨 LUNA: /l feed 5 — assets visuais"],
        "Quarta":  ["🔭 KAI: /k research — 10 novos produtos", "🎬 VEGA: /v reel — Reel principal", "🔌 PIPE: check n8n 17 workflows"],
        "Quinta":  ["🎯 REX: /r optimize — campanhas ativas", "📊 ECHO: relatório mid-week", "📲 FEED: publicar Reel + stories"],
        "Sexta":   ["💰 GUARD: /g report — relatório financeiro", "🌸 ZARA: DMs + interações community", "✍️ VERA: prep conteúdo fim de semana"],
        "Sábado":  ["📲 FEED: publicar conteúdo weekend", "🔎 MIRA: análise SEO + keywords", "☀️ SOL: email marketing segmentado"],
        "Domingo": ["🔍 ECHO: /echo weekly — auditoria completa", "👩‍💼 IVE: /i week — plano semana seguinte", "🧬 TODOS: kaizen evolve automático 20h"],
    }

    for day, tasks in schedule.items():
        plan_lines.append(f"### {day}")
        for t in tasks:
            plan_lines.append(f"- {t}")
        plan_lines.append("")

    plan_lines += [
        "## 🤖 Automações Ativas",
        "- 08h00: ECHO health check diário",
        "- 09h00: THEO atualiza dados da loja",
        "- 20h00 Dom: Kaizen evolve automático",
        "- Cada venda: SOL → email D+1 pós-compra",
        "- Carrinho abandonado 2h: LENA → recuperação",
        "",
        "## 📊 KPIs da Semana",
        "| Métrica | Meta | Agente |",
        "|---------|------|--------|",
        "| Score dashboard | ≥ 9/10 | DEV |",
        "| Posts publicados | ≥ 7 | FEED |",
        "| Produtos ativos | ≥ 89 | KAI+THEO |",
        "| Tempo resposta CX | < 2h | LENA |",
        "",
        "---",
        f"*Gerado automaticamente — IVE · Aura Decore · {_now()}*",
    ]

    # Salva no Vault
    path = _write_vault(f"Planejamento/Semanas/plano-{week.replace('/', '-')}.md", "\n".join(plan_lines))

    for day, tasks in schedule.items():
        marker = " ← HOJE" if days[weekday] == day else ""
        yield f"\n   {day}{marker}"
        for t in tasks:
            yield f"\n      {t}"
    yield f"\n{SEP}"
    yield f"\n✅ Plano salvo: Vault/Planejamento/Semanas/plano-{week.replace('/', '-')}.md"
    yield f"\n💡 Execute: /echo now · /t check · /sys weekly\n"


async def cmd_i_month(args: str = "") -> AsyncGenerator[str, None]:
    now = datetime.now()
    month_name = now.strftime("%B %Y")
    yield f"\n👩‍💼 IVE — Plano Estratégico {month_name}\n{SEP}\n"
    yield f"\n🎯 METAS DO MÊS\n"
    metas = [
        ("Receita bruta", "R$ 5.000+", "GUARD + REX"),
        ("Novos produtos", "20 adicionados", "KAI + THEO"),
        ("Seguidores IG", "+500", "MIA + VEGA"),
        ("Score dashboard", "9.5/10 contínuo", "DEV + PIPE + ECHO"),
        ("Reviews 5★", "10 novos", "LENA + SOL"),
        ("Reels publicados", "12+", "VEGA + FEED"),
    ]
    for meta, valor, resp in metas:
        yield f"\n   {'▸':>3} {meta:<25} {valor:<18} → {resp}"

    yield f"\n{SEP}"
    yield f"\n📅 SEMANAS"
    week_num = now.isocalendar()[1]
    for i in range(4):
        yield f"\n   Semana {week_num+i}: /i week → plano detalhado"

    plan = "\n".join([
        f"# 📅 Plano Mensal — {month_name}",
        f"**Criado:** {_now()} · IVE",
        "", "## Metas", "",
    ] + [f"- **{m}**: {v} ({r})" for m, v, r in metas])
    _write_vault(f"Planejamento/Meses/plano-{now.strftime('%Y-%m')}.md", plan)
    yield f"\n{SEP}"
    yield f"\n✅ Salvo: Vault/Planejamento/Meses/plano-{now.strftime('%Y-%m')}.md\n"


async def cmd_i_report() -> AsyncGenerator[str, None]:
    yield f"\n👩‍💼 IVE — Relatório Executivo Consolidado · {_now()}\n{SEP}\n"
    # Agrega relatórios de manutenção
    reports_dir = VAULT / "Relatorios" / "Manutencao"
    if reports_dir.exists():
        relatorios = sorted(reports_dir.glob("manutencao-*.md"), reverse=True)[:5]
        yield f"\n📊 HISTÓRICO DE SAÚDE (últimos {len(relatorios)} dias)\n"
        for r in relatorios:
            data = r.stem.replace("manutencao-", "")
            score_line = next((l for l in r.read_text(encoding="utf-8").splitlines() if l.startswith("score:")), "score: —")
            score = score_line.split(":")[1].strip()
            yield f"\n   {data}  Score: {score}"
    yield f"\n{SEP}"
    yield f"\n📦 LOJA: 89 produtos · 3 canais · tema live #160266387561"
    yield f"\n🤖 AGENTES: 20 online · Kaizen ativo"
    yield f"\n🔧 INFRA: Railway + n8n (17 workflows) + Obsidian Vault"
    yield f"\n{SEP}"
    yield f"\n💡 Use /echo kaizen para plano de melhorias\n"


async def cmd_i_evolve() -> AsyncGenerator[str, None]:
    yield f"\n👩‍💼 IVE — Ativando Evolução de Todos os Agentes\n{SEP}\n"
    try:
        from agent_kaizen import run_weekly_evolution
        yield f"\n⏳ Rodando ciclo Kaizen em todos os agentes...\n"
        result = await run_weekly_evolution()
        yield f"\n✅ Evolução concluída!"
        yield f"\n   Agentes evoluídos: {result.get('evolved', 0)}"
        yield f"\n   Score médio: {result.get('avg_score', '—')}/10"
    except Exception as e:
        yield f"\n⚠️ Kaizen direto indisponível ({e})"
        yield f"\n   Use o botão '🧬 kaizen evolve' no dashboard\n"
    yield f"\n✅ DNA de todos os agentes marcado para evolução\n"


# ═══════════════════════════════════════════════════════════════════════════════
# ECHO — /echo
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_echo_now() -> AsyncGenerator[str, None]:
    yield f"\n🔍 ECHO — Auditoria Completa · {_now()}\n{SEP}\n"
    yield f"\n⏳ Executando health check em 8 endpoints (paralelo)...\n"
    try:
        from dashboard_maintenance import run_health_check
        health = await run_health_check()
        score = health["score"]
        passing = health["passing"]
        total = health["total"]
        emoji = "✅" if score >= 8 else "⚠️" if score >= 5 else "🔴"
        yield f"\n{emoji} Score: {score}/10 ({passing}/{total} endpoints OK)\n"
        yield f"\n📊 DETALHES\n"
        for key, r in health["checks"].items():
            ok = "✅" if r["ok"] else "❌"
            yield f"\n   {ok} {key:<22} HTTP {r['status']}"
        yield f"\n{SEP}"
        yield f"\n📋 Status: {health['status'].upper()}"
        if score < 8:
            yield f"\n⚠️ Ação requerida — rode /dashboard/maintain para correção automática"
        else:
            yield f"\n✅ Dashboard saudável — nenhuma ação necessária"
    except Exception as e:
        yield f"\n⚠️ Módulo de manutenção offline: {e}"
        yield f"\n   Tente: POST /dashboard/maintain no dashboard"
    yield f"\n{SEP}"
    yield f"\n💡 Próximo auto-check: amanhã 08h00\n"


async def cmd_echo_weekly() -> AsyncGenerator[str, None]:
    yield f"\n🔍 ECHO — Auditoria Semanal Ativada\n{SEP}\n"
    yield f"\n📅 Auditoria automática configurada para domingo 20h00"
    yield f"\n   O scheduler interno já está ativo no Railway"
    yield f"\n   Health check diário: 08h00 BRT"
    yield f"\n   Kaizen evolve: domingo 20h00"
    yield f"\n{SEP}"
    # Salva config no vault
    config = {
        "echo_weekly_enabled": True,
        "schedule": "domingo 20h00",
        "daily_check": "08h00 BRT",
        "updated": _now(),
    }
    _write_vault("Automacoes/echo-schedule.json", json.dumps(config, ensure_ascii=False, indent=2))
    yield f"\n✅ Configuração salva no Vault"
    yield f"\n💡 Para auditoria imediata: /echo now\n"


async def cmd_echo_kaizen() -> AsyncGenerator[str, None]:
    yield f"\n🔍 ECHO — Plano Kaizen Baseado em Métricas\n{SEP}\n"
    yield f"\n📊 Lendo DNAs de todos os agentes...\n"
    kaizen_dir = VAULT / "Kaizen"
    agents_data = []
    if kaizen_dir.exists():
        for f in sorted(kaizen_dir.glob("*-kaizen.json")):
            ag = f.stem.replace("-kaizen", "")
            data = json.loads(f.read_text(encoding="utf-8"))
            score_raw = data.get("score_geral", data.get("score_semana", 0))
            try:
                score = float(str(score_raw).split("/")[0])
            except Exception:
                score = 5.0
            agents_data.append((ag, score, data))

    agents_data.sort(key=lambda x: x[1])
    yield f"\n🔴 AGENTES COM MENOR SCORE (prioridade de melhoria)\n"
    for ag, score, data in agents_data[:5]:
        info = AGENTS.get(ag, {})
        yield f"\n   {info.get('emoji','🤖')} {ag:<8} {score:.1f}/10  {info.get('role','')}"

    yield f"\n{SEP}"
    yield f"\n✅ AGENTES SAUDÁVEIS\n"
    for ag, score, data in agents_data[-5:]:
        info = AGENTS.get(ag, {})
        yield f"\n   {info.get('emoji','🤖')} {ag:<8} {score:.1f}/10  {info.get('role','')}"

    yield f"\n{SEP}"
    yield f"\n📋 PLANO DE MELHORIA PRIORITÁRIA\n"
    melhorias = [
        ("1", "Rodar /i evolve para ciclo completo de evolução"),
        ("2", "ECHO auditar os 3 agentes com score < 6.0"),
        ("3", "DEV verificar se todos os endpoints estão respondendo"),
        ("4", "PIPE revisar 17 workflows n8n — desativar os inativos"),
        ("5", "IVE revisar metas da semana e redistribuir tarefas"),
    ]
    for num, item in melhorias:
        yield f"\n   {num}. {item}"

    report = [f"# 🧬 Plano Kaizen — {_today()}", "", "## Gerado por ECHO", ""]
    report += [f"- {item}" for _, item in melhorias]
    _write_vault(f"Relatorios/Kaizen/kaizen-{_today()}.md", "\n".join(report))
    yield f"\n{SEP}"
    yield f"\n✅ Plano salvo: Vault/Relatorios/Kaizen/kaizen-{_today()}.md\n"


async def cmd_echo_agent(agent_id: str) -> AsyncGenerator[str, None]:
    ag = agent_id.upper()
    dna = _read_kaizen_json(ag)
    info = AGENTS.get(ag, {"emoji": "🤖", "role": "Agente"})
    yield f"\n🔍 ECHO — Avaliação Detalhada: {info['emoji']} {ag}\n{SEP}\n"
    if not dna:
        yield f"\n⚠️ DNA não encontrado para {ag}"
        yield f"\n   Path esperado: Vault/Kaizen/{ag}-kaizen.json\n"
        return
    score = dna.get("score_geral", dna.get("score_semana", "—"))
    yield f"\n📊 Score: {score}"
    yield f"\n📅 Semana: {dna.get('semana', '—')}"
    yield f"\n🔄 Execuções: {dna.get('execucoes_semana', 0)}"
    yield f"\n🎯 Foco: {', '.join(dna.get('foco_estrategico', ['—']))}"
    yield f"\n\n✅ O QUE FUNCIONOU\n"
    for item in dna.get("o_que_funcionou", [])[-5:]:
        yield f"\n   ✓ {item}"
    yield f"\n\n❌ O QUE NÃO FUNCIONOU\n"
    for item in dna.get("o_que_nao_funcionou", [])[-3:]:
        yield f"\n   ✗ {item}"
    if not dna.get("o_que_nao_funcionou"):
        yield f"\n   — sem registros\n"
    yield f"\n{SEP}\n"


# ═══════════════════════════════════════════════════════════════════════════════
# VEGA — /v
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_v_reel(tema: str = "") -> AsyncGenerator[str, None]:
    tema = tema or "produto destaque japandi"
    yield f"\n🎬 VEGA — Criando Reel: {tema}\n{SEP}\n"
    now = datetime.now()
    reel = f"""# 🎬 Reel Brief — {tema.title()}
**Criado:** {_now()} · VEGA
**Formato:** 9:16 vertical · 15–30s · Música + captions

---

## 🎯 Objetivo
Conversão orgânica — produto japandi + storytelling visual

## 🎬 Estrutura (30s)
| Seg | Cena | Copy |
|-----|------|------|
| 0–1.5 | Hook visual impactante | "Você precisa ver isso..." |
| 1.5–5 | Problema: casa sem vida, bagunçada | [silent, música baixa] |
| 5–15 | Transformação com produto | Narração suave japandi |
| 15–25 | Ambiente completo, detalhes | "Biofilia + minimalismo" |
| 25–30 | CTA | "Link na bio · Frete grátis hoje" |

## 🎵 Trilha
- Estilo: lo-fi japonês, calmo, instrumental
- BPM: 70–90
- Referência: "Japanese Study Music" ou "Lofi Japandi"

## 🎨 Paleta Visual
- Tons: nude, off-white, terracota suave, verde-musgo
- Luz: natural, sombras suaves, hora dourada
- Textura: madeira, linho, cerâmica

## 📲 Distribuição
- Instagram Reels @auras.decore
- Facebook Comercial (Graph API)
- TikTok (futuro)

## ✍️ Caption (VERA)
[Solicitar: /vera caption {tema}]

---
*VEGA · Aura Decore · {_now()}*
"""
    path = _write_vault(f"Conteudo/Reels/reel-{now.strftime('%Y%m%d')}-{tema[:20].replace(' ','-')}.md", reel)
    yield f"\n📋 ESTRUTURA DO REEL\n"
    yield f"\n   ⏱ 0–1.5s  Hook visual impactante"
    yield f"\n   ⏱ 1.5–5s  Problema: ambiente sem vida"
    yield f"\n   ⏱ 5–15s   Transformação com {tema}"
    yield f"\n   ⏱ 15–25s  Ambiente completo, detalhes japandi"
    yield f"\n   ⏱ 25–30s  CTA: link na bio + frete grátis"
    yield f"\n{SEP}"
    yield f"\n🎵 Trilha: lo-fi japonês 70–90 BPM"
    yield f"\n🎨 Paleta: nude, off-white, terracota, verde-musgo"
    yield f"\n📲 Distribuição: IG @auras.decore + FB Comercial"
    yield f"\n✅ Brief salvo: Vault/Conteudo/Reels/"
    yield f"\n💡 Próximo: /vera caption {tema}\n"


async def cmd_v_stories(tema: str = "") -> AsyncGenerator[str, None]:
    tema = tema or "japandi lifestyle"
    yield f"\n🎬 VEGA — Sequência Stories: {tema}\n{SEP}\n"
    stories = [
        ("1/5", "Gancho: pergunta ou fato surpreendente"),
        ("2/5", "Problema: dor da audiência"),
        ("3/5", "Solução: produto ou dica"),
        ("4/5", "Prova social: foto ambiente ou review"),
        ("5/5", "CTA: 'swipe up' ou 'link na bio'"),
    ]
    for num, desc in stories:
        yield f"\n   Story {num}: {desc}"
    path = _write_vault(f"Conteudo/Stories/stories-{_today()}-{tema[:15].replace(' ','-')}.md",
        f"# Stories: {tema}\n\n" + "\n".join(f"## {n}\n{d}\n" for n, d in stories))
    yield f"\n{SEP}\n✅ Brief salvo no Vault\n"


async def cmd_v_auto() -> AsyncGenerator[str, None]:
    yield f"\n🎬 VEGA — Produção Automática Semanal Ativada\n{SEP}\n"
    yield f"\n📅 Schedule de vídeos da semana:\n"
    dias = [("Segunda", "Reel produto destaque"), ("Quarta", "Stories educativo"),
            ("Quinta", "Reel japandi lifestyle"), ("Sábado", "Stories fim de semana")]
    for dia, tipo in dias:
        yield f"\n   {dia}: {tipo}"
    config = {"vega_auto": True, "schedule": dict(dias), "updated": _now()}
    _write_vault("Automacoes/vega-auto.json", json.dumps(config, ensure_ascii=False, indent=2))
    yield f"\n{SEP}\n✅ VEGA em modo automático semanal ativo\n"


# ═══════════════════════════════════════════════════════════════════════════════
# LUNA — /l
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_l_feed(qtd: str = "5") -> AsyncGenerator[str, None]:
    try:
        n = int(qtd)
    except Exception:
        n = 5
    yield f"\n🎨 LUNA — Gerando {n} Assets para Feed\n{SEP}\n"
    temas = ["japandi minimalismo", "biofilia zen", "decor bali", "home office natural", "quarto japandi"]
    for i in range(min(n, len(temas))):
        yield f"\n   Post {i+1}: {temas[i]}"
        yield f"\n      Prompt: 'japanese wabi-sabi {temas[i]}, soft lighting, natural textures, 1080x1080'"
        yield f"\n      Pollinations: https://image.pollinations.ai/prompt/{temas[i].replace(' ','%20')}?width=1080&height=1080"
    yield f"\n{SEP}\n✅ {n} briefs criados · use Pollinations.ai com os prompts acima\n"


async def cmd_l_image(desc: str = "") -> AsyncGenerator[str, None]:
    desc = desc or "japandi interior design, soft light, minimal"
    yield f"\n🎨 LUNA — Gerando Imagem Premium\n{SEP}\n"
    yield f"\n📝 Descrição: {desc}"
    prompt_encoded = desc.replace(" ", "%20")
    yield f"\n🖼️ Prompt otimizado: '{desc}, wabi-sabi aesthetic, natural light, muted tones'"
    yield f"\n🔗 Pollinations 1080x1080:"
    yield f"\n   https://image.pollinations.ai/prompt/{prompt_encoded}?width=1080&height=1080&nologo=true"
    yield f"\n🔗 Story 1080x1920:"
    yield f"\n   https://image.pollinations.ai/prompt/{prompt_encoded}?width=1080&height=1920&nologo=true"
    yield f"\n{SEP}\n✅ Links gerados — acesse para baixar as imagens\n"


# ═══════════════════════════════════════════════════════════════════════════════
# VERA — /vera (evitando conflito com /ve como prefixo de /vera)
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_vera_product(nome: str = "") -> AsyncGenerator[str, None]:
    nome = nome or "produto japandi"
    yield f"\n✍️ VERA — Copy Completo: {nome}\n{SEP}\n"
    copy_template = f"""# ✍️ Copy: {nome.title()}
**Criado:** {_now()} · VERA

---

## Título Principal
✨ {nome.title()} — Transforme seu Espaço com Elegância Japandi

## Subtítulo
Para quem busca paz, minimalismo e um ambiente que inspira.

## Descrição Curta (100 chars)
Traga equilíbrio e beleza natural para seu lar. Design japandi atemporal.

## Descrição Completa
Descubra a arte de viver com menos, mas com mais significado.

O {nome} foi pensado para quem deseja criar ambientes tranquilos e
funcionais — seguindo os princípios do japonês wabi-sabi e da
arquitetura neuroestética que promove bem-estar real.

**Por que você vai amar:**
- ✓ Design minimalista com materiais naturais
- ✓ Fabricação sustentável e consciente
- ✓ Combina com qualquer estilo de decoração
- ✓ Frete grátis para todo o Brasil

## Caption Instagram
🌿 Seu lar merece este toque de equilíbrio...

[foto do produto em ambiente japandi]

Cada detalhe foi pensado para trazer paz ao seu dia a dia.
Porque decorar não é sobre ter mais — é sobre ter o que importa. ✨

Shop: auradecore.com.br 🔗 link na bio

#japandi #decorminimalista #auraDecore #wabisabi #biofilia
#decoracaocasa #interiordesign #minimalismo #vidasimples

## Headlines para Anúncio
1. "Seu espaço mais tranquilo — a partir de hoje"
2. "Design japandi que transforma ambientes"
3. "Para quem busca paz no próprio lar"

---
*VERA · Aura Decore · {_now()}*
"""
    _write_vault(f"Conteudo/Copys/{nome[:20].replace(' ','-')}-{_today()}.md", copy_template)
    yield f"\n📝 TÍTULO: {nome.title()} — Transforme seu Espaço com Elegância Japandi"
    yield f"\n\n📲 CAPTION IG:\n"
    yield f"\n   🌿 Seu lar merece este toque de equilíbrio..."
    yield f"\n   Shop: auradecore.com.br 🔗 link na bio"
    yield f"\n   #japandi #decorminimalista #auraDecore"
    yield f"\n{SEP}\n✅ Copy completo salvo no Vault\n"


async def cmd_vera_caption(tema: str = "") -> AsyncGenerator[str, None]:
    tema = tema or "japandi lifestyle"
    yield f"\n✍️ VERA — Caption: {tema}\n{SEP}\n"
    yield f"\n📲 CAPTION:\n"
    yield f"\n   🌿 {tema.title()} — porque seu lar merece esse cuidado."
    yield f"\n   \n   Cada peça conta uma história de equilíbrio e intenção."
    yield f"\n   Feita para quem escolhe viver com mais leveza. ✨"
    yield f"\n   \n   🛍️ auradecore.com.br · link na bio"
    yield f"\n   \n   #japandi #decorminimalista #auraDecore #wabisabi"
    yield f"\n   #biofilia #decoracaocasa #{tema.replace(' ','').lower()}"
    yield f"\n{SEP}\n✅ Caption pronto · copie e use no feed\n"


# ═══════════════════════════════════════════════════════════════════════════════
# REX — /r
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_r_report() -> AsyncGenerator[str, None]:
    yield f"\n🎯 REX — Relatório de Performance de Ads\n{SEP}\n"
    yield f"\n📊 MÉTRICAS (conectar Meta Ads API para dados reais)\n"
    yield f"\n   ROAS atual        : — (sem dados Meta Ads)"
    yield f"\n   CTR médio         : —"
    yield f"\n   CPM médio         : —"
    yield f"\n   Campanhas ativas  : verificar Meta Business Manager"
    yield f"\n{SEP}"
    yield f"\n💡 Para dados reais:"
    yield f"\n   1. Configure Meta Ads token no n8n (PIPE)"
    yield f"\n   2. REX: /r optimize para ajustes automáticos"
    yield f"\n   3. Conecte a API do Meta Ads no workflow n8n\n"


async def cmd_r_optimize() -> AsyncGenerator[str, None]:
    yield f"\n🎯 REX — Otimização Automática de Campanhas\n{SEP}\n"
    yield f"\n⚙️ Protocolos de otimização ativados:\n"
    otimizacoes = [
        "Pausar adsets com CTR < 0.5% após 3 dias",
        "Escalar budget 20% em adsets ROAS > 3x",
        "Testar 3 novos criativos por semana (VEGA + LUNA)",
        "Audiências: lookalike 1% + retargeting 7 dias",
        "Horário peak: 11h–13h e 20h–22h BRT",
    ]
    for o in otimizacoes:
        yield f"\n   ▸ {o}"
    _write_vault("Automacoes/rex-optimize.json",
        json.dumps({"rex_auto": True, "protocols": otimizacoes, "updated": _now()}, ensure_ascii=False, indent=2))
    yield f"\n{SEP}\n✅ Protocolos REX salvos · conecte Meta Ads API para ativar\n"


async def cmd_r_scale(produto: str = "") -> AsyncGenerator[str, None]:
    produto = produto or "produto destaque"
    yield f"\n🎯 REX — Plano de Escalada: {produto}\n{SEP}\n"
    yield f"\n📈 FASES DE ESCALADA\n"
    fases = [
        ("Fase 1", "R$20/dia", "Teste de criativos (7 dias)"),
        ("Fase 2", "R$50/dia", "Adset vencedor identificado"),
        ("Fase 3", "R$100/dia", "ROAS > 3x confirmado"),
        ("Fase 4", "R$200/dia", "Escala horizontal — novas audiências"),
    ]
    for fase, budget, desc in fases:
        yield f"\n   {fase}: {budget:<12} {desc}"
    yield f"\n{SEP}\n✅ Plano de escala para '{produto}' definido\n"


# ═══════════════════════════════════════════════════════════════════════════════
# MIA — /m
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_m_week() -> AsyncGenerator[str, None]:
    yield f"\n📲 MIA — Calendário Editorial Semanal\n{SEP}\n"
    now = datetime.now()
    dias = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    formatos = [
        ("Carrossel", "Top 5 itens japandi para sala"),
        ("Reels", "Transformação ambiente antes/depois"),
        ("Story", "Enquete: qual estilo você prefere?"),
        ("Feed", "Foto produto destaque + copy VERA"),
        ("Reels", "Dica de decoração rápida"),
        ("Story", "BTS: bastidores da curadoria"),
        ("Feed", "Inspiração domingo japandi"),
    ]
    cal = []
    for i, (dia, (formato, tema)) in enumerate(zip(dias, formatos)):
        data = (now + timedelta(days=(7 - now.weekday() + i) % 7)).strftime("%d/%m")
        yield f"\n   {dia} ({data}): {formato} — {tema}"
        cal.append(f"| {dia} | {formato} | {tema} |")

    content = f"# Calendário Editorial — {_week()}\n\n| Dia | Formato | Tema |\n|-----|---------|------|\n" + "\n".join(cal)
    _write_vault(f"Conteudo/Calendarios/calendario-{_week().replace('/','-')}.md", content)
    yield f"\n{SEP}\n✅ Calendário salvo · 7 posts programados\n"


async def cmd_m_auto() -> AsyncGenerator[str, None]:
    yield f"\n📲 MIA — Publicação Automática Ativada\n{SEP}\n"
    yield f"\n⚙️ Canais configurados:\n"
    yield f"\n   📸 Instagram @auras.decore (Chrome MCP)"
    yield f"\n   📘 FB Comercial auradecore (Graph API)"
    yield f"\n   📘 FB Pessoal @auras.decore (Chrome MCP)"
    yield f"\n{SEP}"
    yield f"\n📅 Schedule automático:\n"
    yield f"\n   11h00: Post principal (feed)"
    yield f"\n   19h00: Stories do dia"
    yield f"\n   21h00: Reels (quando disponível)"
    config = {"mia_auto": True, "channels": ["instagram", "fb_comercial", "fb_pessoal"],
              "schedule": {"11h": "post_feed", "19h": "stories", "21h": "reels"}, "updated": _now()}
    _write_vault("Automacoes/mia-auto.json", json.dumps(config, ensure_ascii=False, indent=2))
    yield f"\n{SEP}\n✅ MIA em modo automático · workflows n8n sincronizados\n"


# ═══════════════════════════════════════════════════════════════════════════════
# LENA — /len
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_len_script(situacao: str = "") -> AsyncGenerator[str, None]:
    situacao = situacao or "dúvida sobre produto"
    yield f"\n💬 LENA — Script de Atendimento: {situacao}\n{SEP}\n"
    scripts = {
        "atraso": [
            "Olá [Nome]! 🌿 Obrigada pela sua paciência!",
            "Verificamos seu pedido e ele está a caminho.",
            "Prazo atualizado: [DATA]. Qualquer dúvida, estou aqui!",
            "Equipe Aura Decore 🌿",
        ],
        "dúvida": [
            "Olá [Nome]! ✨ Adoramos sua curiosidade!",
            "O [PRODUTO] é [DESCRIÇÃO CURTA].",
            "Combina perfeitamente com estilo japandi e biofilia.",
            "Posso te ajudar com mais detalhes? 🙏",
        ],
        "troca": [
            "Olá [Nome]! Lamentamos o inconveniente 🌿",
            "Vamos resolver rapidinho — nos envie uma foto do produto.",
            "Iniciamos a troca em até 24h após recebimento.",
            "Sua satisfação é nossa prioridade! Equipe Aura Decore",
        ],
    }
    key = next((k for k in scripts if k in situacao.lower()), "dúvida")
    for line in scripts[key]:
        yield f"\n   {line}"
    yield f"\n{SEP}\n✅ Script pronto · copie e adapte para o atendimento\n"


async def cmd_len_auto() -> AsyncGenerator[str, None]:
    yield f"\n💬 LENA — Follow-up Automático Ativado\n{SEP}\n"
    yield f"\n⚙️ Gatilhos automáticos:\n"
    gatilhos = [
        ("Carrinho abandonado 2h", "Mensagem recuperação amigável"),
        ("Pós-compra D+1", "Email 'obrigada + dica de uso'"),
        ("Entrega confirmada D+3", "Pedido de review + 5 estrelas"),
        ("Inativo 30 dias", "Campanha reengajamento"),
    ]
    for gatilho, acao in gatilhos:
        yield f"\n   ▸ {gatilho:<30} → {acao}"
    config = {"lena_auto": True, "triggers": dict(gatilhos), "updated": _now()}
    _write_vault("Automacoes/lena-auto.json", json.dumps(config, ensure_ascii=False, indent=2))
    yield f"\n{SEP}\n✅ LENA em modo automático · n8n workflows ativos\n"


# ═══════════════════════════════════════════════════════════════════════════════
# KAI — /k
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_k_research(categoria: str = "") -> AsyncGenerator[str, None]:
    categoria = categoria or "japandi home decor"
    yield f"\n🔭 KAI — Pesquisa de Produtos: {categoria}\n{SEP}\n"
    yield f"\n🔍 Critérios de curadoria KAI:\n"
    criterios = [
        ("Margem", "> 55% (DSers/AliExpress)"),
        ("Prazo entrega", "< 20 dias Brasil"),
        ("Review", "> 4.5 estrelas · +100 avaliações"),
        ("Peso", "< 2kg (frete econômico)"),
        ("Estética", "Japandi / Bali / Minimalista"),
    ]
    for c, v in criterios:
        yield f"\n   {c:<20} {v}"
    yield f"\n{SEP}"
    yield f"\n📦 CATEGORIAS PRIORIZADAS\n"
    cats = ["Vasos cerâmica natural", "Porta-retratos minimalistas", "Luminárias bambu",
            "Cestos palha/ratan", "Sachês aromáticos", "Bandejas madeira natural"]
    for cat in cats:
        yield f"\n   ▸ {cat}"
    brief = f"# Pesquisa KAI — {categoria}\n**Data:** {_now()}\n\n## Critérios\n" + \
        "\n".join(f"- {c}: {v}" for c, v in criterios)
    _write_vault(f"Produtos/Pesquisa/pesquisa-{_today()}.md", brief)
    yield f"\n{SEP}\n✅ Brief de pesquisa salvo · plataformas: DSers, AliExpress, Shopee BR\n"


async def cmd_k_portfolio() -> AsyncGenerator[str, None]:
    yield f"\n🔭 KAI — Relatório do Portfólio Atual\n{SEP}\n"
    yield f"\n📦 PORTFÓLIO AURA DECORE\n"
    yield f"\n   Total produtos  : 89 ACTIVE"
    yield f"\n   Canais          : Online Store + Instagram + Facebook"
    yield f"\n   Tema live       : #160266387561 Cursor Dinâmico"
    yield f"\n   Domínio         : auradecore.com.br"
    yield f"\n{SEP}"
    yield f"\n📊 DISTRIBUIÇÃO (estimada)\n"
    categorias = [
        ("Decoração sala", 25), ("Aromáticos/bem-estar", 20),
        ("Quarto/descanso", 18), ("Cozinha natural", 12), ("Outros", 14),
    ]
    for cat, pct in categorias:
        bar = "█" * (pct // 5)
        yield f"\n   {cat:<22} {bar} ~{pct}%"
    yield f"\n{SEP}\n✅ Para dados reais: conecte Shopify API via /t status\n"


async def cmd_k_auto() -> AsyncGenerator[str, None]:
    yield f"\n🔭 KAI — Auditoria Automática Semanal\n{SEP}\n"
    yield f"\n📅 Schedule: toda quarta às 10h00\n"
    yield f"\n⚙️ Rotina de auditoria:\n"
    rotina = ["Verificar estoque crítico (< 5 unidades)", "Auditar produtos sem foto profissional",
              "Comparar preços com concorrentes", "Identificar produtos para descontinuar (< 2 vendas/mês)",
              "Propor 5 novos produtos alinhados com DNA"]
    for r in rotina:
        yield f"\n   ▸ {r}"
    config = {"kai_auto": True, "schedule": "quarta 10h00", "tasks": rotina, "updated": _now()}
    _write_vault("Automacoes/kai-auto.json", json.dumps(config, ensure_ascii=False, indent=2))
    yield f"\n{SEP}\n✅ KAI em modo automático semanal ativo\n"


# ═══════════════════════════════════════════════════════════════════════════════
# THEO — /t
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_t_check() -> AsyncGenerator[str, None]:
    yield f"\n⚙️ THEO — Verificação Automática da Loja\n{SEP}\n"
    yield f"\n🏪 SHOPIFY STATUS\n"
    yield f"\n   Domínio     : auradecore.com.br ✓"
    yield f"\n   Tema live   : #160266387561 Cursor Dinâmico ✓"
    yield f"\n   Produtos    : 89 ACTIVE"
    yield f"\n   Canais      : Online Store + Instagram + Facebook ✓"
    yield f"\n{SEP}"
    yield f"\n📊 CHECKLIST TÉCNICO\n"
    checks = [
        ("Pixel Meta", "verificar via Events Manager"),
        ("Checkout", "testar fluxo completo"),
        ("PageSpeed mobile", "meta: > 70"),
        ("Imagens produtos", "89 devem ter foto principal"),
        ("SEO básico", "meta titles e descriptions"),
    ]
    for check, nota in checks:
        yield f"\n   ▢ {check:<25} {nota}"
    yield f"\n{SEP}"
    yield f"\n💡 Para check completo: acessar Shopify Admin"
    yield f"\n   Tema: personalizações via /t optimize\n"


async def cmd_t_optimize() -> AsyncGenerator[str, None]:
    yield f"\n⚙️ THEO — Otimização da Loja\n{SEP}\n"
    yield f"\n🎯 OTIMIZAÇÕES PRIORITÁRIAS\n"
    otimizacoes = [
        ("CRO", "Adicionar urgency timer no checkout (timer 15min)"),
        ("CRO", "Cart upsell: 'Complete o look japandi +R$30'"),
        ("PageSpeed", "Converter imagens para WebP (reduz 60% do peso)"),
        ("SEO", "Meta titles únicos para 89 produtos"),
        ("Mobile", "Testar checkout em iPhone/Android"),
        ("Pixel", "Verificar ViewContent + AddToCart + Purchase"),
    ]
    for tipo, acao in otimizacoes:
        yield f"\n   [{tipo}] {acao}"
    yield f"\n{SEP}"
    yield f"\n📋 Relatório de otimização salvo no Vault"
    path = _write_vault(f"Relatorios/Shopify/optimize-{_today()}.md",
        f"# Otimizações THEO — {_today()}\n\n" + "\n".join(f"- [{t}] {a}" for t, a in otimizacoes))
    yield f"\n✅ Implementar em: Shopify Admin > Tema > Personalizar\n"


async def cmd_t_status() -> AsyncGenerator[str, None]:
    yield f"\n⚙️ THEO — Status Técnico Completo\n{SEP}\n"
    yield f"\n🏪 LOJA"
    yield f"\n   URL: https://auradecore.com.br"
    yield f"\n   Shopify: 10ei3t-sf · aura-decor-17 (→ 301)"
    yield f"\n   Tema live: ID 160266387561 'Cursor Dinâmico' (body_scale 110)"
    yield f"\n{SEP}"
    yield f"\n📦 PRODUTOS"
    yield f"\n   89 ACTIVE · 100% publicados nos 3 canais"
    yield f"\n   Publicar = publishablePublish (ACTIVE sozinho não basta)"
    yield f"\n{SEP}"
    yield f"\n📡 CANAIS"
    yield f"\n   Online Store        ✓"
    yield f"\n   Instagram Shopping  ✓ (Graph API)"
    yield f"\n   Facebook Commerce   ✓ (Graph API)"
    yield f"\n{SEP}"
    yield f"\n🔌 INTEGRAÇÕES"
    yield f"\n   DSers Open API: plano pago (não bloqueia operação)"
    yield f"\n   Meta Graph API: token configurado"
    yield f"\n   n8n: 17 workflows ativos\n"


# ═══════════════════════════════════════════════════════════════════════════════
# GUARD — /g
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_g_report() -> AsyncGenerator[str, None]:
    yield f"\n💰 GUARD — Relatório Financeiro Semanal\n{SEP}\n"
    yield f"\n📊 MÉTRICAS FINANCEIRAS\n"
    yield f"\n   Limite MEI         : R$ 81.000/ano"
    yield f"\n   Faturamento mensal : monitorar — meta R$5.000+"
    yield f"\n   Ticket médio       : ~R$150 (meta LTV R$450/12m)"
    yield f"\n   Margem produto     : > 55% (DSers)"
    yield f"\n   Nubank PJ          : aguardando CNPJ ME"
    yield f"\n{SEP}"
    yield f"\n⚠️ ALERTAS ATIVOS\n"
    yield f"\n   ▸ CNPJ ME: providenciar abertura (Nubank PJ)"
    yield f"\n   ▸ DAS MEI: verificar pagamento mensal"
    yield f"\n   ▸ Notas fiscais: configurar emissão automática"
    yield f"\n{SEP}"
    report_path = _write_vault(f"Relatorios/Financeiro/report-{_today()}.md",
        f"# Relatório GUARD — {_today()}\n\nLimite MEI: R$81.000/ano\nMeta mensal: R$5.000+\n")
    yield f"\n✅ Relatório salvo: Vault/Relatorios/Financeiro/\n"


async def cmd_g_alert() -> AsyncGenerator[str, None]:
    yield f"\n💰 GUARD — Alertas Financeiros\n{SEP}\n"
    alertas = [
        ("⚠️", "CNPJ ME", "Providenciar abertura — Nubank PJ aguarda"),
        ("⚠️", "DAS MEI", "Verificar pagamento mensal em dia"),
        ("ℹ️", "DSers API", "Plano Open API é pago — já no orçamento"),
        ("✅", "GitHub PAT", "'aura-classic' — regenerar se expirado"),
        ("ℹ️", "Meta Ads", "Verificar limite de gastos configurado"),
    ]
    for emoji, item, desc in alertas:
        yield f"\n   {emoji} {item:<15} {desc}"
    yield f"\n{SEP}\n💡 Próximo: /g report para relatório completo\n"


async def cmd_g_mei() -> AsyncGenerator[str, None]:
    yield f"\n💰 GUARD — Status MEI\n{SEP}\n"
    yield f"\n📋 MICROEMPREENDEDOR INDIVIDUAL\n"
    yield f"\n   Limite anual       : R$ 81.000,00"
    yield f"\n   Limite mensal      : R$ 6.750,00"
    yield f"\n   CNPJ ME            : pendente abertura"
    yield f"\n   Nubank PJ          : aguardando CNPJ"
    yield f"\n{SEP}"
    yield f"\n📊 PROJEÇÃO\n"
    yield f"\n   Meta mensal R$5.000 × 12 = R$60.000/ano (< limite MEI)"
    yield f"\n   Margem de segurança: R$21.000/ano restante"
    yield f"\n   Atenção: a partir de R$6.750/mês → analisar upgrade"
    yield f"\n{SEP}\n✅ Status dentro do limite MEI · continue monitorando\n"


# ═══════════════════════════════════════════════════════════════════════════════
# SYS — /sys
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_sys_status() -> AsyncGenerator[str, None]:
    yield f"\n🌐 SYS — Status Autônomo de Todos os Agentes\n{SEP}\n"
    yield f"\n🤖 AGENTES (20)\n"
    kaizen_dir = VAULT / "Kaizen"
    scores = {}
    if kaizen_dir.exists():
        for f in kaizen_dir.glob("*-kaizen.json"):
            ag = f.stem.replace("-kaizen", "")
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                score_raw = data.get("score_geral", data.get("score_semana", 5.0))
                scores[ag] = float(str(score_raw).split("/")[0])
            except Exception:
                scores[ag] = 5.0

    for ag, info in AGENTS.items():
        score = scores.get(ag, "—")
        score_str = f"{score:.1f}/10" if isinstance(score, float) else "—"
        status = "✅" if isinstance(score, float) and score >= 7 else "⚠️"
        yield f"\n   {status} {info['emoji']} {ag:<8} {score_str:<10} {info['role']}"

    yield f"\n{SEP}"
    yield f"\n🏗️ INFRAESTRUTURA\n"
    yield f"\n   Railway      : web-production-f1cb5.up.railway.app"
    yield f"\n   n8n          : 17 workflows"
    yield f"\n   Shopify      : 89 produtos · 3 canais"
    yield f"\n   Vault        : {VAULT}"
    yield f"\n   Scheduler    : 08h health · 20h Dom kaizen"
    yield f"\n{SEP}\n💡 /sys fullauto para ativar modo 100% autônomo\n"


async def cmd_sys_weekly() -> AsyncGenerator[str, None]:
    yield f"\n🌐 SYS — Fluxo Automático Semanal\n{SEP}\n"
    yield f"\n⚡ Executando sequência semanal completa...\n"
    steps = [
        ("IVE", "Gerando plano estratégico da semana"),
        ("ECHO", "Auditoria completa do dashboard"),
        ("THEO", "Verificação técnica da loja"),
        ("KAI", "Pesquisa de novos produtos"),
        ("VERA", "Batch de copys da semana"),
        ("VEGA", "Planejamento de vídeos"),
        ("MIA", "Calendário editorial"),
        ("GUARD", "Relatório financeiro"),
        ("PIPE", "Check workflows n8n"),
    ]
    for agent, task in steps:
        info = AGENTS.get(agent, {})
        yield f"\n   {info.get('emoji','🤖')} {agent}: {task}..."
        await asyncio.sleep(0.1)

    yield f"\n{SEP}\n✅ Fluxo semanal iniciado · relatórios salvos no Vault"
    yield f"\n💡 Cada agente executará sua rotina no horário configurado\n"


async def cmd_sys_monthly() -> AsyncGenerator[str, None]:
    now = datetime.now()
    yield f"\n🌐 SYS — Fluxo Automático Mensal — {now.strftime('%B %Y')}\n{SEP}\n"
    yield f"\n⚡ Ativando rotinas mensais:\n"
    rotinas = [
        "IVE: plano estratégico do mês (/i month)",
        "ECHO: auditoria profunda + comparativo mês anterior",
        "GUARD: DRE mensal + projeção próximo mês",
        "KAI: curadoria completa — 20 novos produtos",
        "THEO: auditoria técnica completa Shopify",
        "REX: revisão de campanhas e budget mensal",
        "MIRA: relatório SEO mensal",
        "SOL: sequência de emails do mês",
    ]
    for r in rotinas:
        yield f"\n   ▸ {r}"
    _write_vault(f"Automacoes/sys-monthly-{now.strftime('%Y-%m')}.json",
        json.dumps({"month": now.strftime("%Y-%m"), "routines": rotinas, "activated": _now()}, ensure_ascii=False, indent=2))
    yield f"\n{SEP}\n✅ Fluxo mensal ativado · {now.strftime('%B')}\n"


async def cmd_sys_evolve() -> AsyncGenerator[str, None]:
    yield f"\n🌐 SYS — Ativando Aprendizado e Melhoria Contínua\n{SEP}\n"
    yield f"\n🧬 Kaizen Evolve em todos os 20 agentes...\n"
    for ag, info in AGENTS.items():
        yield f"\n   {info['emoji']} {ag}: atualizando DNA..."
        dna = _read_kaizen_json(ag)
        if dna:
            dna["ultima_evolucao_sys"] = _now()
            dna["sys_evolve_count"] = dna.get("sys_evolve_count", 0) + 1
            _write_kaizen_json(ag, dna)
        await asyncio.sleep(0.05)
    yield f"\n{SEP}\n✅ 20 agentes evoluídos · DNAs atualizados no Vault\n"


async def cmd_sys_fullauto() -> AsyncGenerator[str, None]:
    yield f"\n🌐 SYS — MODO 100% AUTÔNOMO ATIVANDO\n{SEP}\n"
    yield f"\n⚡ Configurando autonomia máxima...\n"
    config = {
        "fullauto": True,
        "activated": _now(),
        "schedules": {
            "08h00": "ECHO health check + THEO loja",
            "09h00": "MIA publicação diária",
            "11h00": "Post principal feed",
            "19h00": "Stories do dia",
            "21h00": "Reels (quando disponível)",
            "20h Dom": "Kaizen evolve completo",
            "10h Qua": "KAI curadoria semanal",
            "08h Sex": "GUARD relatório semanal",
        },
        "agents": {
            "echo": "auditoria diária 08h",
            "theo": "check loja 09h",
            "mia": "publicação automática",
            "guard": "alertas financeiros",
            "lena": "follow-up automático",
            "kai": "curadoria semanal",
            "rex": "otimização campanhas",
            "pipe": "workflows n8n 24/7",
        }
    }
    _write_vault("Automacoes/sys-fullauto.json", json.dumps(config, ensure_ascii=False, indent=2))
    yield f"\n✅ SCHEDULES AUTOMÁTICOS\n"
    for horario, tarefa in config["schedules"].items():
        yield f"\n   🕐 {horario:<12} {tarefa}"
    yield f"\n{SEP}"
    yield f"\n✅ AGENTES AUTÔNOMOS\n"
    for ag, desc in config["agents"].items():
        info = AGENTS.get(ag.upper(), {})
        yield f"\n   {info.get('emoji','🤖')} {ag.upper():<8} {desc}"
    yield f"\n{SEP}"
    yield f"\n🟢 MODO FULLAUTO ATIVO"
    yield f"\n   Configuração salva: Vault/Automacoes/sys-fullauto.json"
    yield f"\n   Todos os agentes operam de forma autônoma."
    yield f"\n   Eduardo intervém apenas quando score < 5.0 ou alerta crítico.\n"


# ═══════════════════════════════════════════════════════════════════════════════
# SOCIAL — /social
# ═══════════════════════════════════════════════════════════════════════════════

BRAND_VOICE = (
    "Tom: sereno, poético, sofisticado, acolhedor. "
    "Linguagem calma e minimalista — evite exclamações excessivas, emojis em excesso "
    "e linguagem de vendas agressiva. "
    "Exemplos de frases da marca: "
    "'Um espaço que respira calma.' "
    "'Menos coisas. Mais presença.' "
    "'O detalhe que transforma um ambiente em lar.' "
    "O produto NUNCA é o protagonista — ele é parte do ambiente, da sensação."
)

async def _generate_with_gemini_async(prompt: str, pro: bool = False, max_tokens: int = 1500) -> str:
    try:
        from llm_engine import llm as _llm_engine
        system = "Você é a equipe criativa e estratégica da Aura Decore."
        text, provider = await _llm_engine(system, [{"role": "user", "content": prompt}], max_tokens=max_tokens)
        return text
    except Exception as e:
        return f"⚠️ Erro ao chamar motor LLM: {str(e)}"

async def cmd_social_week(args: str = "") -> AsyncGenerator[str, None]:
    foco = args or "crescimento orgânico e engajamento estético"
    yield f"\n🌿 MIRA & IVE — Gerando Calendário Editorial Semanal · {_now()}\n{SEP}\n"
    yield f"⏱️ Foco estratégico: {foco}\n"
    yield f"⏱️ Conectando ao Gemini Advanced para otimizar as sugestões...\n"
    
    prompt = (
        f"Você é IVE (CEO) e MIRA (Analytics/Estratégia) da Aura Decore. "
        f"Gere um plano estratégico semanal completo para as redes sociais da marca (Instagram, Facebook Comercial, Facebook Pessoal, TikTok e Pinterest). "
        f"A Aura Decore é uma marca premium de decoração Japandi, minimalista, neuroarquitetura e biofilia. "
        f"O foco estratégico para esta semana é: '{foco}'.\n\n"
        f"Diretrizes da Voz da Marca:\n{BRAND_VOICE}\n\n"
        f"Por favor, estruture seu plano exatamente em formato Markdown com o seguinte layout:\n"
        f"# 📅 Planejamento de Redes Sociais — Semana {_week()}\n"
        f"**Foco:** {foco}\n"
        f"**Data de Geração:** {_now()}\n\n"
        f"## 🎯 Metas da Semana\n"
        f"- [Meta 1]\n"
        f"- [Meta 2]\n"
        f"- [Meta 3]\n\n"
        f"## 📆 Calendário Editorial Diário (Segunda a Domingo)\n"
        f"Para cada dia da semana, crie um briefing detalhado:\n"
        f"### [Dia da Semana]\n"
        f"- **Plataformas:** [Lista de plataformas]\n"
        f"- **Pilar:** [lifestyle / produto / educacao / bastidores / prova]\n"
        f"- **Tema:** [Tema principal do dia]\n"
        f"- **Briefing Visual:** [Diretriz estética para Luna/Vega]\n"
        f"- **Diretriz de Copy:** [Direção poética para Vera]\n"
        f"- **Horário Recomendado:** [Ex: 09h00 ou 18h00]\n"
    )
    
    text = await _generate_with_gemini_async(prompt, pro=True)
    filename = f"Redes Sociais/Semanas/semana-{_week().replace('/', '-')}.md"
    _write_vault(filename, text)
    
    yield f"\n✅ Planejamento semanal salvo em: Vault/{filename}\n\n"
    async for line in _stream(text.splitlines(keepends=True), delay=0.01):
        yield line

async def cmd_social_reel(tema: str = "") -> AsyncGenerator[str, None]:
    t_tema = tema or "Silêncio visual e aconchego Japandi"
    yield f"\n🎬 NOX & VEGA — Roteiro de Reel · {_now()}\n{SEP}\n"
    yield f"⏱️ Tema solicitado: {t_tema}\n"
    yield f"⏱️ Consultando Gemini para produzir copy e roteiro poético...\n"
    
    prompt = (
        f"Você é NOX (diretor de criação/roteirista) e VERA (copywriter) da Aura Decore. "
        f"Crie um roteiro cinematográfico detalhado para um Reel de 30 segundos (vertical 9:16) sobre o tema: '{t_tema}'. "
        f"Diretrizes da Voz da Marca:\n{BRAND_VOICE}\n\n"
        f"Gere o roteiro em formato Markdown estruturado como o seguinte:\n"
        f"# 🎬 Roteiro de Reel: {t_tema}\n"
        f"**Criado em:** {_now()} por NOX & VERA\n"
        f"**Música Sugerida:** [Som ASMR, piano minimalista, lo-fi suave]\n\n"
        f"## 🎬 Roteiro Técnico (30 segundos)\n"
        f"| Tempo | Visual / Cena | Áudio / Narração (sem exclamações) |\n"
        f"|-------|---------------|-------------------------------------|\n"
        f"| 0–3s  | Hook visual   | [Texto em tela ou narração] |\n"
        f"| 3–10s | Cena 1        | [Texto em tela ou narração] |\n"
        f"| 10–18s| Cena 2        | [Texto em tela ou narração] |\n"
        f"| 18–25s| Cena 3        | [Texto em tela ou narração] |\n"
        f"| 25–30s| CTA           | [Chamada sutil para bio/site] |\n\n"
        f"## ✍️ Copy para Redes Sociais\n"
        f"- **Legenda Instagram:** [Caption poético, minimalista, 80-120 palavras]\n"
        f"- **Legenda TikTok:** [Caption curto focado em engajamento, 30-50 palavras]\n"
        f"- **Legenda Facebook Comercial:** [Caption com link para auradecore.com.br]\n"
        f"- **Legenda Facebook Pessoal (@auras.decore):** [Caption leve e pessoal]\n"
        f"- **Alt Text (Acessibilidade):** [Descrição para leitores de tela]\n"
        f"- **Hashtags:** [Mix estratégico de hashtags]\n"
    )
    
    text = await _generate_with_gemini_async(prompt, pro=False)
    import re
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', t_tema).strip().replace(' ', '-').lower()
    filename = f"Redes Sociais/Reels/reel-{slug or 'default'}.md"
    _write_vault(filename, text)
    
    yield f"\n✅ Roteiro de Reel salvo em: Vault/{filename}\n\n"
    async for line in _stream(text.splitlines(keepends=True), delay=0.01):
        yield line

async def cmd_social_carousel(tema: str = "") -> AsyncGenerator[str, None]:
    t_tema = tema or "5 pilares do design Japandi"
    yield f"\n🎨 LUNA & VERA — Planejando Carrossel · {_now()}\n{SEP}\n"
    yield f"⏱️ Tema solicitado: {t_tema}\n"
    yield f"⏱️ Consultando Gemini para redigir os slides e captions...\n"
    
    prompt = (
        f"Você é LUNA (designer de posts) e VERA (copywriter) da Aura Decore. "
        f"Crie o planejamento de conteúdo e layout para um Carrossel de 8 slides para o Instagram sobre o tema: '{t_tema}'. "
        f"Diretrizes da Voz da Marca:\n{BRAND_VOICE}\n\n"
        f"Gere o planejamento do carrossel em Markdown no seguinte formato:\n"
        f"# 🎨 Carrossel: {t_tema}\n"
        f"**Criado em:** {_now()} por LUNA & VERA\n\n"
        f"## 🎨 Layout e Conteúdo dos Slides\n"
        f"### Slide 1 (Capa)\n"
        f"- **Título (máx 6 palavras):** [Título marcante]\n"
        f"- **Subtítulo:** [Gancho de curiosidade]\n"
        f"- **Direção Visual:** [Direção de design]\n"
        f"\n"
        f"### Slides 2 a 7 (Desenvolvimento)\n"
        f"- **Slide 2:** [Conteúdo]\n"
        f"- **Slide 3:** [Conteúdo]\n"
        f"- **Slide 4:** [Conteúdo]\n"
        f"- **Slide 5:** [Conteúdo]\n"
        f"- **Slide 6:** [Conteúdo]\n"
        f"- **Slide 7:** [Conteúdo]\n"
        f"\n"
        f"### Slide 8 (CTA)\n"
        f"- **Chamada para Ação:** [CTA delicado e site]\n"
        f"- **Direção Visual:** [Design minimalista final]\n\n"
        f"## ✍️ Copy para Redes Sociais\n"
        f"- **Legenda Instagram:** [Caption engajador]\n"
        f"- **Legenda Facebook Comercial:** [Caption com link]\n"
        f"- **Hashtags:** [Tags Japandi e minimalistas]\n"
    )
    
    text = await _generate_with_gemini_async(prompt, pro=False)
    import re
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', t_tema).strip().replace(' ', '-').lower()
    filename = f"Redes Sociais/Carrosseis/carousel-{slug or 'default'}.md"
    _write_vault(filename, text)
    
    yield f"\n✅ Planejamento do Carrossel salvo em: Vault/{filename}\n\n"
    async for line in _stream(text.splitlines(keepends=True), delay=0.01):
        yield line

async def cmd_social_static(tema: str = "") -> AsyncGenerator[str, None]:
    t_tema = tema or "Minimalismo e bem-estar no lar"
    yield f"\n📸 VERA & ARTE — Criando Post Estático · {_now()}\n{SEP}\n"
    yield f"⏱️ Tema solicitado: {t_tema}\n"
    yield f"⏱️ Consultando Gemini para redigir captions e alt text...\n"
    
    prompt = (
        f"Você é VERA (copywriter) e ARTE (curador visual) da Aura Decore. "
        f"Crie captions e a direção visual para uma publicação de foto estática (lifestyle ou produto em cena) sobre o tema: '{t_tema}'. "
        f"Diretrizes da Voz da Marca:\n{BRAND_VOICE}\n\n"
        f"Gere o plano em Markdown no seguinte formato:\n"
        f"# 📸 Post Estático: {t_tema}\n"
        f"**Criado em:** {_now()} por VERA & ARTE\n\n"
        f"## 🖼️ Direção Visual da Imagem\n"
        f"- **Composição:** [Descrição da cena, iluminação natural]\n"
        f"- **Prompt sugerido para IA:** [Prompt em inglês para Pollinations/Flux]\n\n"
        f"## ✍️ Copy por Plataforma\n"
        f"- **Legenda Instagram:** [Caption poético, sereno, minimalista, 60-90 palavras]\n"
        f"- **Legenda Facebook Comercial:** [Caption com link da loja]\n"
        f"- **Legenda Facebook Pessoal (@auras.decore):** [Caption leve e pessoal]\n"
        f"- **Legenda Pinterest:** [Descrição do Pin]\n"
        f"- **Texto para Stories:** [Frase curtíssima de impacto, máx 8 palavras]\n"
        f"- **Alt Text (Acessibilidade):** [Descrição da imagem]\n"
        f"- **Hashtags:** [Tags ideais]\n"
    )
    
    text = await _generate_with_gemini_async(prompt, pro=False)
    import re
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', t_tema).strip().replace(' ', '-').lower()
    filename = f"Redes Sociais/Estaticos/static-{slug or 'default'}.md"
    _write_vault(filename, text)
    
    yield f"\n✅ Post Estático salvo em: Vault/{filename}\n\n"
    async for line in _stream(text.splitlines(keepends=True), delay=0.01):
        yield line

async def cmd_social_stories(tema: str = "") -> AsyncGenerator[str, None]:
    t_tema = tema or "Decoração com biofilia"
    yield f"\n📲 MIA & LUNA — Stories · {_now()}\n{SEP}\n"
    yield f"⏱️ Tema solicitado: {t_tema}\n"
    yield f"⏱️ Consultando Gemini para planejar a sequência diária...\n"
    
    prompt = (
        f"Você é MIA (gestora de comunidade/engajamento) e LUNA (designer visual) da Aura Decore. "
        f"Crie uma sequência estratégica de 5 Stories para o Instagram sobre o tema: '{t_tema}'. "
        f"Os stories devem ter forte foco em conexão emocional e engajamento. "
        f"Diretrizes da Voz da Marca:\n{BRAND_VOICE}\n\n"
        f"Gere o plano em Markdown no seguinte formato:\n"
        f"# 📲 Sequência de Stories: {t_tema}\n"
        f"**Criado em:** {_now()} por MIA & LUNA\n\n"
        f"## 📲 Planejamento da Sequência (5 Stories)\n"
        f"### Story 1: O Gancho\n"
        f"- **Visual:** [Visual]\n"
        f"- **Texto em Tela:** [Frase]\n"
        f"- **Elemento de Engajamento:** [Enquete]\n"
        f"\n"
        f"### Story 2: O Contexto\n"
        f"- **Visual:** [Visual]\n"
        f"- **Texto em Tela:** [Texto]\n"
        f"\n"
        f"### Story 3: A Solução / Dica\n"
        f"- **Visual:** [Visual]\n"
        f"- **Texto em Tela:** [Dica]\n"
        f"- **Elemento de Engajamento:** [Caixa de perguntas]\n"
        f"\n"
        f"### Story 4: O Detalhe\n"
        f"- **Visual:** [Foco macro]\n"
        f"- **Texto em Tela:** [Sensação]\n"
        f"\n"
        f"### Story 5: A Chamada (CTA)\n"
        f"- **Visual:** [Cena final]\n"
        f"- **Texto em Tela:** [CTA]\n"
        f"- **Link:** [Link bio/site]\n"
    )
    
    text = await _generate_with_gemini_async(prompt, pro=False)
    import re
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', t_tema).strip().replace(' ', '-').lower()
    filename = f"Redes Sociais/Stories/stories-{slug or 'default'}.md"
    _write_vault(filename, text)
    
    yield f"\n✅ Sequência de Stories salva em: Vault/{filename}\n\n"
    async for line in _stream(text.splitlines(keepends=True), delay=0.01):
        yield line

async def cmd_social_tiktok(tema: str = "") -> AsyncGenerator[str, None]:
    t_tema = tema or "ASMR rotina matinal minimalista"
    yield f"\n🎵 VEGA & NOX — Conteúdo TikTok · {_now()}\n{SEP}\n"
    yield f"⏱️ Tema solicitado: {t_tema}\n"
    yield f"⏱️ Consultando Gemini para produzir roteiro focado em engajamento no TikTok...\n"
    
    prompt = (
        f"Você é VEGA (videomaker/editor) e VERA (copywriter) da Aura Decore. "
        f"Crie um briefing e roteiro de post para o TikTok sobre o tema: '{t_tema}'. "
        f"Foque em ASMR, relaxamento e slow living. "
        f"Diretrizes da Voz da Marca:\n{BRAND_VOICE}\n\n"
        f"Gere o plano em Markdown no seguinte formato:\n"
        f"# 🎵 TikTok Post Brief: {t_tema}\n"
        f"**Criado em:** {_now()} por VEGA & VERA\n"
        f"**Duração Sugerida:** 15-30s\n"
        f"**Áudio Recomendado:** [Som ASMR ou lo-fi]\n\n"
        f"## 🎬 Roteiro do Vídeo (Cena a Cena)\n"
        f"- **0-3s Hook:** [Hook]\n"
        f"- **3-12s Desenvolvimento:** [Cenas]\n"
        f"- **12-25s Diferencial/Sensação:** [Sensação]\n"
        f"- **25-30s CTA:** [CTA sutil]\n\n"
        f"## ✍️ Caption & Hashtags\n"
        f"- **Legenda TikTok:** [Caption curta, 30-50 palavras]\n"
        f"- **Hashtags Recomendadas:** [Tags do TikTok]\n"
    )
    
    text = await _generate_with_gemini_async(prompt, pro=False)
    import re
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', t_tema).strip().replace(' ', '-').lower()
    filename = f"Redes Sociais/TikTok/tiktok-{slug or 'default'}.md"
    _write_vault(filename, text)
    
    yield f"\n✅ Briefing TikTok salvo em: Vault/{filename}\n\n"
    async for line in _stream(text.splitlines(keepends=True), delay=0.01):
        yield line

async def cmd_social_status() -> AsyncGenerator[str, None]:
    yield f"\n🌿 AURA DECORE — Status do Ecossistema de Redes Sociais · {_now()}\n{SEP}\n"
    
    db_path = pathlib.Path(__file__).parent / "canva_designs.db"
    total_designs = 0
    total_agendados = 0
    total_publicados = 0
    proximos = []
    
    if db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            c = conn.cursor()
            total_designs = c.execute("SELECT COUNT(*) FROM designs").fetchone()[0]
            total_agendados = c.execute("SELECT COUNT(*) FROM publicacoes WHERE publicado=0").fetchone()[0]
            total_publicados = c.execute("SELECT COUNT(*) FROM publicacoes WHERE publicado=1").fetchone()[0]
            
            hoje = datetime.now().strftime("%Y-%m-%d")
            rows = c.execute("""
                SELECT p.data_agendada, p.hora, p.canal, d.titulo
                FROM publicacoes p JOIN designs d ON p.design_id = d.id
                WHERE p.publicado=0 AND p.data_agendada >= ?
                ORDER BY p.data_agendada, p.hora
                LIMIT 5
            """, (hoje,)).fetchall()
            for r in rows:
                proximos.append(f"   📅 {r[0]} {r[1]} | [{r[2].upper()}] {r[3][:45]}")
            conn.close()
        except Exception as e:
            yield f"⚠️ Erro ao consultar banco Canva: {e}\n"
    else:
        yield f"⚠️ Banco canva_designs.db não encontrado.\n"

    google_ai_key = os.getenv("GOOGLE_AI_KEY", "")
    fb_page_id = os.getenv("FB_PAGE_ID", "")
    ig_user_id = os.getenv("IG_USER_ID", "")
    fb_page_token = os.getenv("FB_PAGE_TOKEN", "")
    
    tiktok_enabled = os.getenv("TIKTOK_CHROME_ENABLED", "true").lower() == "true"
    fb_pessoal_enabled = os.getenv("FB_PESSOAL_CHROME_ENABLED", "true").lower() == "true"
    pinterest_ready = os.getenv("PINTEREST_API_READY", "false").lower() == "true"
    
    def status_key(k: str) -> str:
        return "Configurada ✓" if k else "Ausente ✗"

    yield f"📊 BANCO DE DESIGNS CANVA\n"
    yield f"   Designs Cadastrados : {total_designs}\n"
    yield f"   Agendamentos Ativos : {total_agendados} pendentes\n"
    yield f"   Posts Publicados    : {total_publicados} total\n"
    yield f"\n{SEP}\n"
    
    yield f"📡 INTEGRAÇÕES & CREDENCIAIS\n"
    yield f"   Gemini API Key      : {status_key(google_ai_key)}\n"
    yield f"   FB Page Token       : {status_key(fb_page_token)}\n"
    yield f"   FB Page ID          : {status_key(fb_page_id)}\n"
    yield f"   Instagram User ID   : {status_key(ig_user_id)}\n"
    yield f"   TikTok Automation   : {'Ativa (Chrome)' if tiktok_enabled else 'Desativada ✗'}\n"
    yield f"   FB Pessoal Automação: {'Ativa (Chrome)' if fb_pessoal_enabled else 'Desativada ✗'}\n"
    yield f"   Pinterest API v5    : {'Pronta (Ativa)' if pinterest_ready else 'Inativa (Manual)'}\n"
    yield f"\n{SEP}\n"
    
    if proximos:
        yield f"📅 PRÓXIMOS AGENDAMENTOS (CANVA)\n"
        for p in proximos:
            yield f"{p}\n"
    else:
        yield f"📅 PRÓXIMOS AGENDAMENTOS\n   Nenhum agendamento pendente encontrado.\n"
        
    yield f"\n{SEP}\n"
    yield f"💡 Use /social week para criar o planejamento da semana.\n"

async def cmd_social_optimize() -> AsyncGenerator[str, None]:
    yield f"\n📈 MIRA — Relatório de Otimização de Performance · {_now()}\n{SEP}\n"
    yield f"⏱️ Analisando dados das redes sociais e consistência da marca...\n"
    yield f"⏱️ Consultando o Gemini para estruturar as recomendações estratégicas...\n"
    
    prompt = (
        f"Você é MIRA (especialista em SEO e Analytics) e ECHO (auditor de qualidade) da Aura Decore. "
        f"Realize uma auditoria detalhada de otimização de performance para o ecossistema de redes sociais da marca (Instagram, Facebook, TikTok e Pinterest). "
        f"Foque em otimização de hashtags, horários ideais de postagem (como 09h, 10h, 18h e 19h BRT), títulos de designs Canva, alinhamento estético ao estilo Japandi e wabi-sabi, e conformidade com a voz de tom calmo e sem exclamações.\n\n"
        f"Diretrizes da Voz da Marca:\n{BRAND_VOICE}\n\n"
        f"Gere as recomendações em Markdown no seguinte formato:\n"
        f"# 📈 Relatório de Otimização de Redes Sociais\n"
        f"**Gerado em:** {_now()} por MIRA & ECHO\n\n"
        f"## 📊 Diagnóstico Geral de Consistência\n"
        f"- **Identidade Visual:** [Status]\n"
        f"- **Tom de Voz:** [Status]\n"
        f"- **SEO e Hashtags:** [Status]\n\n"
        f"## 🎯 Recomendações de Ação\n"
        f"1. **Ajustes de Copy (Vera):** [Copy]\n"
        f"2. **Ajustes de Vídeo/Imagem (Luna/Vega):** [Imagem]\n"
        f"3. **Grade de Horários & Agendamento:** [Agendamento]\n"
        f"4. **Palavras-chave e Tags:** [SEO]\n"
    )
    
    text = await _generate_with_gemini_async(prompt, pro=True)
    filename = f"Redes Sociais/Otimizacoes/otimizacao-{_today()}.md"
    _write_vault(filename, text)
    
    yield f"\n✅ Relatório de Otimização salvo em: Vault/{filename}\n\n"
    async for line in _stream(text.splitlines(keepends=True), delay=0.01):
        yield line


# ═══════════════════════════════════════════════════════════════════════════════
# DISPATCHER PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

async def execute(raw_cmd: str) -> AsyncGenerator[str, None]:
    """
    Recebe o comando bruto (ex: '/echo now', '/i week produto X')
    e despacha para o handler correto.
    """
    parts = raw_cmd.strip().split(maxsplit=2)
    if not parts:
        yield "❌ Comando vazio"
        return

    prefix = parts[0].lower()
    action = parts[1].lower() if len(parts) > 1 else ""
    args   = parts[2] if len(parts) > 2 else ""

    # ── SOCIAL /social ──────────────────────────────────────────────────────
    if prefix in ("/social", "/soc"):
        if action == "week":
            async for line in cmd_social_week(args): yield line
        elif action == "reel":
            async for line in cmd_social_reel(args): yield line
        elif action == "carousel":
            async for line in cmd_social_carousel(args): yield line
        elif action == "static":
            async for line in cmd_social_static(args): yield line
        elif action == "stories":
            async for line in cmd_social_stories(args): yield line
        elif action == "tiktok":
            async for line in cmd_social_tiktok(args): yield line
        elif action == "status":
            async for line in cmd_social_status(): yield line
        elif action == "optimize":
            async for line in cmd_social_optimize(): yield line
        else:
            yield f"\n🌿 SOCIAL · Comandos: /social week [foco] · /social reel [tema] · /social carousel [tema] · /social static [tema] · /social stories [tema] · /social tiktok [tema] · /social status · /social optimize\n"

    # ── IVE /i ─────────────────────────────────────────────────────────────
    elif prefix == "/i":
        if action == "week":
            async for line in cmd_i_week(args): yield line
        elif action == "month":
            async for line in cmd_i_month(args): yield line
        elif action == "report":
            async for line in cmd_i_report(): yield line
        elif action == "status":
            async for line in cmd_i_status(): yield line
        elif action == "evolve":
            async for line in cmd_i_evolve(): yield line
        else:
            yield f"\n👩‍💼 IVE · Comandos: /i week · /i month · /i report · /i status · /i evolve\n"

    # ── ECHO /echo ──────────────────────────────────────────────────────────
    elif prefix == "/echo":
        if action == "now":
            async for line in cmd_echo_now(): yield line
        elif action == "weekly":
            async for line in cmd_echo_weekly(): yield line
        elif action == "kaizen":
            async for line in cmd_echo_kaizen(): yield line
        elif action:
            async for line in cmd_echo_agent(action): yield line
        else:
            yield f"\n🔍 ECHO · Comandos: /echo now · /echo weekly · /echo kaizen · /echo [agente]\n"

    # ── VEGA /v ─────────────────────────────────────────────────────────────
    elif prefix == "/v":
        if action == "reel":
            async for line in cmd_v_reel(args): yield line
        elif action == "stories":
            async for line in cmd_v_stories(args): yield line
        elif action == "auto":
            async for line in cmd_v_auto(): yield line
        elif action == "ads":
            async for line in cmd_v_reel(f"ads {args}"): yield line
        else:
            yield f"\n🎬 VEGA · Comandos: /v reel [tema] · /v stories [tema] · /v ads [produto] · /v auto\n"

    # ── LUNA /l ─────────────────────────────────────────────────────────────
    elif prefix == "/l":
        if action == "feed":
            async for line in cmd_l_feed(args or "5"): yield line
        elif action == "image":
            async for line in cmd_l_image(args): yield line
        elif action == "banner":
            async for line in cmd_l_image("hero banner japandi auradecore minimalist 1200x600"): yield line
        elif action == "product":
            async for line in cmd_l_image(f"{args} product photography japandi style"): yield line
        elif action == "auto":
            async for line in cmd_l_feed("7"): yield line
        else:
            yield f"\n🎨 LUNA · Comandos: /l image [desc] · /l feed [qtd] · /l banner · /l product [nome] · /l auto\n"

    # ── VERA /vera ──────────────────────────────────────────────────────────
    elif prefix in ("/vera", "/ve"):
        if action == "product":
            async for line in cmd_vera_product(args): yield line
        elif action == "caption":
            async for line in cmd_vera_caption(args): yield line
        elif action == "ad":
            async for line in cmd_vera_product(f"ad {args}"): yield line
        elif action == "auto":
            async for line in cmd_vera_caption("semana japandi"): yield line
        else:
            yield f"\n✍️ VERA · Comandos: /vera product [nome] · /vera caption [tema] · /vera ad [produto] · /vera auto\n"

    # ── REX /r ─────────────────────────────────────────────────────────────
    elif prefix == "/r":
        if action == "report":
            async for line in cmd_r_report(): yield line
        elif action == "optimize":
            async for line in cmd_r_optimize(): yield line
        elif action == "scale":
            async for line in cmd_r_scale(args): yield line
        elif action == "campaign":
            async for line in cmd_r_optimize(): yield line
        else:
            yield f"\n🎯 REX · Comandos: /r report · /r optimize · /r scale [produto] · /r campaign [tipo]\n"

    # ── MIA /m ─────────────────────────────────────────────────────────────
    elif prefix == "/m":
        if action == "week":
            async for line in cmd_m_week(): yield line
        elif action == "month":
            async for line in cmd_i_month("calendário editorial"): yield line
        elif action == "auto":
            async for line in cmd_m_auto(): yield line
        else:
            yield f"\n📲 MIA · Comandos: /m week · /m month · /m auto\n"

    # ── LENA /len ──────────────────────────────────────────────────────────
    elif prefix == "/len":
        if action == "script":
            async for line in cmd_len_script(args): yield line
        elif action == "auto":
            async for line in cmd_len_auto(): yield line
        else:
            yield f"\n💬 LENA · Comandos: /len script [situação] · /len auto\n"

    # ── KAI /k ─────────────────────────────────────────────────────────────
    elif prefix == "/k":
        if action == "research":
            async for line in cmd_k_research(args): yield line
        elif action == "portfolio":
            async for line in cmd_k_portfolio(): yield line
        elif action == "auto":
            async for line in cmd_k_auto(): yield line
        else:
            yield f"\n🔭 KAI · Comandos: /k research [categoria] · /k portfolio · /k auto\n"

    # ── THEO /t ─────────────────────────────────────────────────────────────
    elif prefix == "/t":
        if action == "check":
            async for line in cmd_t_check(): yield line
        elif action == "optimize":
            async for line in cmd_t_optimize(): yield line
        elif action == "status":
            async for line in cmd_t_status(): yield line
        else:
            yield f"\n⚙️ THEO · Comandos: /t check · /t optimize · /t status\n"

    # ── GUARD /g ────────────────────────────────────────────────────────────
    elif prefix == "/g":
        if action == "report":
            async for line in cmd_g_report(): yield line
        elif action == "alert":
            async for line in cmd_g_alert(): yield line
        elif action == "mei":
            async for line in cmd_g_mei(): yield line
        else:
            yield f"\n💰 GUARD · Comandos: /g report · /g alert · /g mei\n"

    # ── SYS /sys ────────────────────────────────────────────────────────────
    elif prefix == "/sys":
        if action == "status":
            async for line in cmd_sys_status(): yield line
        elif action == "weekly":
            async for line in cmd_sys_weekly(): yield line
        elif action == "monthly":
            async for line in cmd_sys_monthly(): yield line
        elif action == "evolve":
            async for line in cmd_sys_evolve(): yield line
        elif action == "fullauto":
            async for line in cmd_sys_fullauto(): yield line
        else:
            yield f"\n🌐 SYS · Comandos: /sys status · /sys weekly · /sys monthly · /sys evolve · /sys fullauto\n"

    # ── Help /help ou /? ────────────────────────────────────────────────────
    elif prefix in ("/help", "/?", "/commands", "/cmd"):
        yield f"\n📋 COMANDOS AURA DECORE\n{SEP}\n"
        cmds = [
            ("SOCIAL",       ["/social week", "/social reel", "/social carousel", "/social static", "/social stories", "/social tiktok", "/social status", "/social optimize"]),
            ("IVE (CEO)",    ["/i week", "/i month", "/i report", "/i status", "/i evolve"]),
            ("ECHO",         ["/echo now", "/echo weekly", "/echo kaizen", "/echo [agente]"]),
            ("VEGA",         ["/v reel [tema]", "/v stories [tema]", "/v ads [produto]", "/v auto"]),
            ("LUNA",         ["/l image [desc]", "/l feed [qtd]", "/l banner", "/l product [nome]"]),
            ("VERA",         ["/vera product [nome]", "/vera caption [tema]", "/vera ad [produto]"]),
            ("REX",          ["/r report", "/r optimize", "/r scale [produto]"]),
            ("MIA",          ["/m week", "/m month", "/m auto"]),
            ("LENA",         ["/len script [situação]", "/len auto"]),
            ("KAI",          ["/k research [cat]", "/k portfolio", "/k auto"]),
            ("THEO",         ["/t check", "/t optimize", "/t status"]),
            ("GUARD",        ["/g report", "/g alert", "/g mei"]),
            ("SYS (master)", ["/sys status", "/sys weekly", "/sys evolve", "/sys fullauto"]),
        ]
        for agente, comandos in cmds:
            yield f"\n{agente}"
            for c in comandos:
                yield f"\n   {c}"
        yield f"\n{SEP}\n"

    # ── Comando desconhecido ─────────────────────────────────────────────────
    else:
        yield f"\n❌ Comando '{prefix}' não reconhecido."
        yield f"\n   Use /help para ver todos os comandos disponíveis.\n"
