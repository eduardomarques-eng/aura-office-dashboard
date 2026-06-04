# -*- coding: utf-8 -*-
"""
daily_report.py — Relatório Diário Automático às 21h BRT
Coleta todas as atividades do dia, gera sumário por agente,
decisões necessárias e próximos passos. Salva no Vault e envia
via endpoint /report/daily da API.
"""
from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Coroutine

BRT = timezone(timedelta(hours=-3))

# ── Agentes com foco para relatório ──────────────────────────────────────────
AGENTS_IN_REPORT = [
    "IVE", "GUARD", "NEXUS", "KAI", "VERA", "LUNA", "NOX",
    "REX", "THEO", "ECHO", "LENA", "SOL", "ZARA", "MIRA",
    "PIPE", "ARTE", "FEED", "DEV",
]

# ── Storage em memória ────────────────────────────────────────────────────────
_REPORTS: list[dict] = []
_REPORT_LOCK = asyncio.Lock()


def _today_brt() -> str:
    return datetime.now(BRT).strftime("%Y-%m-%d")


def _now_brt() -> str:
    return datetime.now(BRT).strftime("%Y-%m-%d %H:%M BRT")


# ── Coleta de atividades do dia ───────────────────────────────────────────────

def collect_daily_activities(tasks_db: dict) -> dict[str, list[dict]]:
    """
    Lê todas as tasks do dia e agrupa por agente.
    `tasks_db` é o dicionário _TASKS do main.py.
    """
    today = _today_brt()
    by_agent: dict[str, list[dict]] = {a: [] for a in AGENTS_IN_REPORT}

    for task in tasks_db.values():
        created = task.get("created_at", "")
        if not created.startswith(today):
            continue
        # Identifica agente pelo nome da task
        title_upper = (task.get("title", "") + " " + task.get("agent", "")).upper()
        matched = False
        for agent in AGENTS_IN_REPORT:
            if agent in title_upper:
                by_agent[agent].append(task)
                matched = True
                break
        if not matched:
            by_agent.setdefault("NEXUS", []).append(task)

    return by_agent


def collect_vault_activities(vault_base: str, date_str: str) -> dict[str, str]:
    """
    Lê logs do vault de hoje para enriquecer o relatório.
    Retorna dict agent_id → snippets de atividade.
    """
    activities: dict[str, str] = {}
    agents_dir = os.path.join(vault_base, "Agentes")
    if not os.path.exists(agents_dir):
        return activities

    for agent_folder in os.listdir(agents_dir):
        diary_dir = os.path.join(vault_base, "Relatorios", "Diarios", agent_folder)
        if not os.path.exists(diary_dir):
            continue
        diary_file = os.path.join(diary_dir, f"{date_str}.md")
        if os.path.exists(diary_file):
            try:
                with open(diary_file, "r", encoding="utf-8") as f:
                    activities[agent_folder.upper()] = f.read()[:1500]
            except Exception:
                pass

    return activities


# ── Geração do relatório com LLM ─────────────────────────────────────────────

async def generate_daily_report(
    tasks_db: dict,
    commands_db: list[dict],
    llm_call: Callable[[str, str, int], Coroutine[Any, Any, tuple[str, str]]],
    vault_base: str = r"C:\Users\erick\AURA-decor-vault",
) -> dict:
    """
    Gera relatório diário completo. Chamado automaticamente às 21h BRT.
    """
    today = _today_brt()
    by_agent = collect_daily_activities(tasks_db)
    vault_acts = collect_vault_activities(vault_base, today)

    # Resumo de tasks para o LLM
    tasks_summary = []
    for agent, tasks in by_agent.items():
        if tasks:
            completed = [t for t in tasks if t.get("status") == "completed"]
            failed = [t for t in tasks if t.get("status") == "error"]
            pending = [t for t in tasks if t.get("status") in ("pending", "running")]
            tasks_summary.append(
                f"{agent}: {len(completed)} concluídas, "
                f"{len(failed)} com erro, {len(pending)} pendentes"
            )

    # Comandos do dia
    today_commands = [
        c for c in commands_db
        if c.get("created_at", "").startswith(today)
    ]
    commands_summary = []
    for cmd in today_commands:
        status_icon = "✅" if cmd["status"] in ("executando", "concluido") else "⏳" if cmd["status"] == "aguardando_confirmacao" else "❌"
        commands_summary.append(f"{status_icon} [{cmd['id']}] {cmd['ordem'][:80]}")

    # Prompt para IVE gerar o relatório
    system = (
        "Você é IVE — gerente executiva da Aura Decore. "
        "Gere o Relatório Diário Executivo para Eduardo Marques. "
        "Formato: texto humanizado, estruturado, claro. "
        "Eduardo precisa tomar decisões para o dia seguinte. "
        "Seja específica, mencione números e resultados reais."
    )

    tasks_md = "\n".join(tasks_summary) if tasks_summary else "Nenhuma task registrada hoje."
    cmds_md = "\n".join(commands_summary) if commands_summary else "Nenhum comando hoje."
    vault_md = ""
    for agent, content in list(vault_acts.items())[:5]:
        vault_md += f"\n### {agent}\n{content[:400]}\n"

    user_msg = f"""Data: {today} | Hora: {_now_brt()}

## Atividade de Tasks por Agente
{tasks_md}

## Comandos Executados
{cmds_md}

## Logs do Vault (amostra)
{vault_md if vault_md else 'Vault sem entradas hoje.'}

---
Gere um RELATÓRIO DIÁRIO EXECUTIVO com:
1. **Resumo Executivo** (3 pontos-chave do dia)
2. **O que foi feito** (por área: design, marketing, loja, financeiro, tech)
3. **Resultados e métricas** (qualquer número disponível)
4. **Problemas identificados** (com causa raiz e solução proposta)
5. **Decisões para Eduardo** (máx 3 decisões que precisam da aprovação dele)
6. **Plano para amanhã** (top 5 prioridades dos agentes)
7. **Status dos agentes** (quem está ativo, ocioso, com gargalo)

Máximo 600 palavras. Seja direta e acionável."""

    report_text, provider = await llm_call(system, user_msg, 1000)

    # Lê contexto financeiro do vault se disponível
    fin_context = _read_financial_context(vault_base, today)

    report = {
        "date": today,
        "generated_at": _now_brt(),
        "provider": provider,
        "report_text": report_text,
        "tasks_summary": tasks_summary,
        "commands_today": len(today_commands),
        "total_tasks_today": sum(len(v) for v in by_agent.values()),
        "financial_context": fin_context,
    }

    # Salva no vault
    await _save_report_to_vault(report, vault_base)

    async with _REPORT_LOCK:
        _REPORTS.insert(0, report)
        if len(_REPORTS) > 30:
            _REPORTS.pop()

    return report


def _read_financial_context(vault_base: str, today: str) -> str:
    """Lê contexto financeiro recente do vault."""
    try:
        fin_dir = os.path.join(vault_base, "Financeiro")
        if not os.path.exists(fin_dir):
            return ""
        files = sorted([
            f for f in os.listdir(fin_dir)
            if f.endswith(".md")
        ], reverse=True)
        if files:
            fpath = os.path.join(fin_dir, files[0])
            with open(fpath, "r", encoding="utf-8") as f:
                return f.read()[:800]
    except Exception:
        pass
    return ""


async def _save_report_to_vault(report: dict, vault_base: str) -> None:
    try:
        # Relatório diário
        daily_dir = os.path.join(vault_base, "Relatorios", "Diarios")
        os.makedirs(daily_dir, exist_ok=True)
        fname = os.path.join(daily_dir, f"relatorio-{report['date']}.md")

        content = f"""# Relatório Diário — {report['date']}

**Gerado às:** {report['generated_at']}
**Provider LLM:** {report['provider']}
**Total tasks:** {report['total_tasks_today']} | **Comandos:** {report['commands_today']}

---

{report['report_text']}

---

## Métricas Brutas
**Tasks por status:**
{chr(10).join(report['tasks_summary']) or 'Sem dados'}

{'## Contexto Financeiro' + chr(10) + report['financial_context'] if report.get('financial_context') else ''}

---
*Relatório gerado automaticamente pelo Daily Report System — Aura Decore*
"""
        with open(fname, "w", encoding="utf-8") as f:
            f.write(content)

        # Também salva na pasta semanal
        week_num = datetime.now(BRT).isocalendar()[1]
        year = datetime.now(BRT).year
        weekly_dir = os.path.join(vault_base, "Relatorios", "Semanais")
        os.makedirs(weekly_dir, exist_ok=True)
        weekly_file = os.path.join(weekly_dir, f"semana-{year}-W{week_num:02d}.md")

        # Appende ao semanal
        entry = f"\n\n## {report['date']}\n{report['report_text'][:500]}...\n"
        mode = "a" if os.path.exists(weekly_file) else "w"
        with open(weekly_file, mode, encoding="utf-8") as f:
            if mode == "w":
                f.write(f"# Relatório Semanal — Semana {week_num}/{year}\n\n")
            f.write(entry)

    except Exception as e:
        print(f"[DAILY REPORT] Erro ao salvar vault: {e}")


# ── Getter para API ────────────────────────────────────────────────────────────

def get_latest_report() -> dict | None:
    return _REPORTS[0] if _REPORTS else None


def get_all_reports(limit: int = 7) -> list[dict]:
    return _REPORTS[:limit]


# ── Quick Status (sem LLM) ─────────────────────────────────────────────────────

def quick_status(tasks_db: dict, commands_db: list[dict]) -> dict:
    """Status rápido sem chamar LLM — para /status endpoint."""
    today = _today_brt()
    by_agent = collect_daily_activities(tasks_db)

    total = sum(len(v) for v in by_agent.values())
    completed = sum(
        len([t for t in tasks if t.get("status") == "completed"])
        for tasks in by_agent.values()
    )
    errors = sum(
        len([t for t in tasks if t.get("status") == "error"])
        for tasks in by_agent.values()
    )
    active_agents = [a for a, tasks in by_agent.items() if tasks]

    pending_commands = [
        c for c in commands_db
        if c.get("status") == "aguardando_confirmacao"
    ]

    return {
        "date": today,
        "timestamp": _now_brt(),
        "tasks": {
            "total": total,
            "completed": completed,
            "errors": errors,
            "pending": total - completed - errors,
        },
        "active_agents": active_agents,
        "pending_confirmations": [
            {"id": c["id"], "ordem": c["ordem"][:80]}
            for c in pending_commands
        ],
        "last_report": _REPORTS[0]["generated_at"] if _REPORTS else None,
    }
