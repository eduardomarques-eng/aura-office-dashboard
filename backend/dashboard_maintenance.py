# -*- coding: utf-8 -*-
"""
Dashboard Maintenance — Sistema de Auto-Manutenção Diária
Aura Decore · 2026

Responsáveis:
  ECHO  — auditoria e relatório diário (08h)
  PIPE  — mantém workflows e endpoints vivos
  DEV   — detecta e propõe fixes de código
  THEO  — atualiza dados da loja no dashboard

Fluxo diário:
  1. run_daily_maintenance() → checa saúde de todos os componentes
  2. Registra relatório no Vault
  3. Atualiza DNA dos agentes responsáveis
  4. Retorna resumo para IVE
"""
from __future__ import annotations

import json
import os
import pathlib
import platform
import httpx
import asyncio
from datetime import datetime
from typing import Any

# ── Vault ──────────────────────────────────────────────────────────────────────
_default_vault = (
    r"C:\Users\erick\AURA-decor-vault"
    if platform.system() == "Windows"
    else "/app/vault"
)
VAULT = pathlib.Path(os.getenv("OBSIDIAN_VAULT", _default_vault))

RAILWAY_URL = os.getenv(
    "RAILWAY_URL", "https://web-production-f1cb5.up.railway.app"
)

# ── Checklist de saúde do dashboard ───────────────────────────────────────────
HEALTH_CHECKS: dict[str, tuple[str, str]] = {
    "backend_health":    ("/health",                    "Backend FastAPI online"),
    "agents_endpoint":   ("/agents",                    "20 agentes carregados"),
    "kaizen_endpoint":   ("/agents/kaizen",             "Sistema Kaizen respondendo"),
    "store_status":      ("/store/status",              "Dados da loja atualizados"),
    "events_sse":        ("/events",                    "SSE de eventos ativo"),
    "terminal_stream":   ("/terminal/stream?cmd=ping",  "Terminal streaming ok"),
    "social_status":     ("/social/status",             "Integração social ok"),
    "activity_log":      ("/activity/log?limit=1",      "Log de atividade ok"),
}

# ── Agentes responsáveis pela manutenção ──────────────────────────────────────
MAINTENANCE_AGENTS = {
    "echo": "Auditor diário — roda health check e gera relatório",
    "pipe": "Mantém endpoints, webhooks e workflows n8n ativos",
    "dev":  "Detecta bugs no dashboard e propõe correções de código",
    "theo": "Atualiza dados da loja (produtos, estoque, pedidos) no dashboard",
}

# ── Checagem de um endpoint ────────────────────────────────────────────────────
async def _check_endpoint(client: httpx.AsyncClient, path: str) -> dict:
    try:
        r = await client.get(f"{RAILWAY_URL}{path}", timeout=8)
        ok = r.status_code < 400
        body = r.text[:120] if ok else r.text[:80]
        return {"ok": ok, "status": r.status_code, "preview": body}
    except Exception as e:
        return {"ok": False, "status": 0, "preview": str(e)[:80]}

# ── Health check completo ──────────────────────────────────────────────────────
async def run_health_check() -> dict:
    """Checa todos os endpoints críticos do dashboard. Retorna relatório estruturado."""
    results: dict[str, dict] = {}
    async with httpx.AsyncClient() as client:
        for key, (path, _) in HEALTH_CHECKS.items():
            results[key] = await _check_endpoint(client, path)

    total = len(results)
    passing = sum(1 for r in results.values() if r["ok"])
    score = round(passing / total * 10, 1)

    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "score": score,
        "passing": passing,
        "total": total,
        "checks": results,
        "status": "saudavel" if score >= 8 else "degradado" if score >= 5 else "critico",
    }

# ── Atualiza DNA dos agentes de manutenção ────────────────────────────────────
def _update_maintenance_agent_dna(agent_id: str, task_log: list[str]) -> None:
    kaizen_path = VAULT / "Kaizen" / f"{agent_id.upper()}-kaizen.json"
    if not kaizen_path.exists():
        return
    try:
        data = json.loads(kaizen_path.read_text(encoding="utf-8"))
        data["ultima_manutencao"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        data["execucoes_semana"] = data.get("execucoes_semana", 0) + 1
        existing = data.get("o_que_funcionou", [])
        for t in task_log:
            if t not in existing:
                existing.append(t)
        data["o_que_funcionou"] = existing[-20:]
        kaizen_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass

# ── Gera relatório no Vault ───────────────────────────────────────────────────
def _write_maintenance_report(health: dict, fixes_applied: list[str]) -> pathlib.Path:
    hoje = datetime.now().strftime("%Y-%m-%d")
    reports_dir = VAULT / "Relatorios" / "Manutencao"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"manutencao-{hoje}.md"

    score = health["score"]
    emoji = "✅" if score >= 8 else "⚠️" if score >= 5 else "🔴"

    checks_md = "\n".join(
        f"| {key} | {'✅' if r['ok'] else '❌'} | {HEALTH_CHECKS[key][1]} | {r['status']} |"
        for key, r in health["checks"].items()
    )
    fixes_md = "\n".join(f"- {f}" for f in fixes_applied) if fixes_applied else "- Nenhuma correção necessária"
    agents_md = "\n".join(f"| {a.upper()} | {desc} |" for a, desc in MAINTENANCE_AGENTS.items())

    content = f"""---
tipo: manutencao-diaria
data: {hoje}
score: {score}/10
status: {health['status']}
responsaveis: ECHO, PIPE, DEV, THEO
---

# {emoji} Relatório de Manutenção — {hoje}

**Score Dashboard:** {score}/10 ({health['passing']}/{health['total']} checks passing)
**Status:** {health['status'].upper()}
**Horário:** {health['timestamp']}

## 📊 Health Checks

| Componente | Status | Descrição | HTTP |
|------------|--------|-----------|------|
{checks_md}

## 🔧 Ações Executadas

{fixes_md}

## 👥 Agentes Responsáveis

| Agente | Papel |
|--------|-------|
{agents_md}

## 📅 Próximo Ciclo
Amanhã às 08h00 (automático via Railway cron)

---
*Gerado automaticamente — Aura Decore Maintenance System*
"""
    report_path.write_text(content, encoding="utf-8")
    return report_path

# ── Auto-fix: identifica e registra falhas ─────────────────────────────────────
async def _auto_fix_degraded(health: dict) -> list[str]:
    fixes: list[str] = []
    failing = [k for k, r in health["checks"].items() if not r["ok"]]

    if not failing:
        fixes.append("Todos os endpoints saudáveis — nenhuma ação necessária")
        return fixes

    for key in failing:
        desc = HEALTH_CHECKS[key][1]
        fixes.append(f"DETECTADO: {key} falhou ({desc}) — registrado para DEV/PIPE")

    if "kaizen_endpoint" in failing:
        fixes.append("AÇÃO DEV: Kaizen endpoint offline — verificar agent_kaizen.py no Railway")
    if "events_sse" in failing:
        fixes.append("AÇÃO PIPE: SSE /events offline — verificar EventSource no Railway")
    if "backend_health" in failing:
        fixes.append("AÇÃO CRÍTICA PIPE+THEO: Backend offline — verificar Railway deploy logs")
    if "store_status" in failing:
        fixes.append("AÇÃO THEO: /store/status offline — verificar token Shopify e conexão")

    return fixes

# ── Atualiza DNA compartilhado ────────────────────────────────────────────────
def _update_shared_dna(health: dict, fixes: list[str]) -> None:
    shared_path = VAULT / "Memoria" / "Compartilhada" / "dna-aprendizado.md"
    if not shared_path.exists():
        return
    try:
        existing = shared_path.read_text(encoding="utf-8")
        hoje = datetime.now().strftime("%Y-%m-%d")
        if hoje not in existing:
            entrada = (
                f"\n\n## 🔧 Manutenção {hoje} — Score {health['score']}/10\n"
                + "\n".join(f"- {f}" for f in fixes[:5])
            )
            shared_path.write_text(existing + entrada, encoding="utf-8")
    except Exception:
        pass

# ── Manutenção completa ────────────────────────────────────────────────────────
async def run_daily_maintenance(triggered_by: str = "cron") -> dict:
    """
    Executado diariamente às 08h (Railway cron) ou sob demanda via dashboard.
    Retorna relatório completo.
    """
    print(f"[MANUTENÇÃO] Iniciando — {datetime.now().strftime('%Y-%m-%d %H:%M')} — trigger: {triggered_by}")

    health = await run_health_check()
    fixes = await _auto_fix_degraded(health)

    for agent_id in MAINTENANCE_AGENTS:
        _update_maintenance_agent_dna(
            agent_id,
            [f"Manutenção diária {datetime.now().strftime('%Y-%m-%d')} — score {health['score']}/10"]
        )

    report_path = _write_maintenance_report(health, fixes)
    _update_shared_dna(health, fixes)

    print(f"[MANUTENÇÃO] Concluída — Score: {health['score']}/10 — {len(fixes)} ações")
    return {
        "status": "ok",
        "triggered_by": triggered_by,
        "health": health,
        "fixes_aplicados": fixes,
        "relatorio": str(report_path),
        "agentes_atualizados": list(MAINTENANCE_AGENTS.keys()),
        "proximo_ciclo": "amanha 08h00",
    }

# ── Status rápido (sem rede) ──────────────────────────────────────────────────
def quick_dashboard_status() -> dict:
    """Lê do vault sem I/O de rede — usado pelo /health estendido."""
    reports_dir = VAULT / "Relatorios" / "Manutencao"
    ultimo_relatorio = "nunca"
    ultimo_score = "—"

    if reports_dir.exists():
        relatorios = sorted(reports_dir.glob("manutencao-*.md"), reverse=True)
        if relatorios:
            ultimo_relatorio = relatorios[0].stem.replace("manutencao-", "")
            try:
                for line in relatorios[0].read_text(encoding="utf-8").splitlines():
                    if line.startswith("score:"):
                        ultimo_score = line.split(":")[1].strip()
                        break
            except Exception:
                pass

    kaizen_dir = VAULT / "Kaizen"
    agentes_com_dna = len(list(kaizen_dir.glob("*-kaizen.json"))) if kaizen_dir.exists() else 0

    return {
        "ultimo_relatorio": ultimo_relatorio,
        "score_ultimo": ultimo_score,
        "agentes_com_dna": agentes_com_dna,
        "responsaveis": list(MAINTENANCE_AGENTS.keys()),
        "proximo_ciclo": "08h00 diário",
        "status": "operacional",
    }
