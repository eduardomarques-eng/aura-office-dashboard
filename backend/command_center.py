# -*- coding: utf-8 -*-
"""
command_center.py — Centro de Comando Aura Decore
Eduardo → IVE (plano) → GUARD (validação financeira) → Agentes (execução)

Fluxo:
  1. Eduardo envia ordem via POST /command
  2. IVE analisa, decompõe em tarefas por agente, propõe plano
  3. GUARD valida impacto financeiro e riscos
  4. Eduardo confirma via POST /command/{id}/confirm
  5. Tarefas são disparadas para os agentes com logging no vault
"""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

# ── Storage em memória (substituível por Redis/DB) ────────────────────────────
_COMMANDS: dict[str, dict] = {}          # id → command dict
_COMMAND_LOCK = asyncio.Lock()

# ── Perfis dos agentes (resumo para IVE/GUARD) ────────────────────────────────
AGENT_SUMMARY = {
    "KAI":  "Análise de preços, custos, margem, planilhas financeiras",
    "VERA": "Copywriting, textos produto, e-mail, blog, SEO on-page",
    "LUNA": "Design visual, briefs criativos, paletas, direção de arte",
    "NOX":  "Calendário de conteúdo, pauta semanal/mensal, campanhas",
    "REX":  "Estratégia de crescimento, metas, KPIs, plano de negócio",
    "THEO": "Catálogo Shopify, ficha técnica, cadastro de produtos",
    "ECHO": "Suporte ao cliente, respostas, SAC, pós-venda",
    "LENA": "Logística, fornecedores, prazos, estoque, custo frete",
    "SOL":  "CRO, conversão, A/B tests, checkout, página de produto",
    "ZARA": "Tendências de mercado, análise concorrência, nicho",
    "MIRA": "SEO, palavras-chave, tráfego orgânico, blog posts",
    "PIPE": "Automações n8n, integrações, workflows, webhooks",
    "ARTE": "Criação de imagens IA (Pollinations), assets visuais",
    "FEED": "Publicação redes sociais (Instagram, Facebook)",
    "DEV":  "Desenvolvimento, bugs, melhorias técnicas, scripts",
    "NEXUS":"Coordenação entre agentes, sincronização de tarefas",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _local_ts() -> str:
    from datetime import timedelta
    brt = timezone(timedelta(hours=-3))
    return datetime.now(brt).strftime("%Y-%m-%d %H:%M BRT")


# ── Prompts IVE e GUARD ───────────────────────────────────────────────────────

def _ive_system() -> str:
    return (
        "Você é IVE — Inteligência e Visão Estratégica da Aura Decore, "
        "assistente pessoal de Eduardo Marques.\n"
        "Sua função: receber ordens de Eduardo, decompô-las em tarefas claras "
        "para cada agente especializado, e apresentar um plano de ação estruturado.\n\n"
        "Formato de resposta OBRIGATÓRIO (JSON puro, sem markdown):\n"
        "{\n"
        "  \"resumo\": \"Uma linha descrevendo o objetivo\",\n"
        "  \"tarefas\": [\n"
        "    {\"agente\": \"NOME\", \"tarefa\": \"Instrução clara e específica\", "
        "\"prioridade\": 1, \"depende_de\": []},\n"
        "    ...\n"
        "  ],\n"
        "  \"prazo_estimado\": \"X minutos\",\n"
        "  \"resultado_esperado\": \"O que Eduardo terá ao final\"\n"
        "}\n\n"
        f"Agentes disponíveis: {json.dumps(AGENT_SUMMARY, ensure_ascii=False)}\n"
        "Seja direto. Máximo 6 tarefas por plano. Prioridade 1=urgente."
    )


def _guard_system() -> str:
    return (
        "Você é GUARD — Guardião Financeiro e de Riscos da Aura Decore.\n"
        "Sua função: validar planos propostos pela IVE quanto ao impacto financeiro, "
        "riscos operacionais, viabilidade e alinhamento estratégico.\n\n"
        "Formato de resposta OBRIGATÓRIO (JSON puro, sem markdown):\n"
        "{\n"
        "  \"aprovado\": true,\n"
        "  \"score_viabilidade\": 0-100,\n"
        "  \"custo_estimado\": \"R$ X (em tempo de agente/API)\",\n"
        "  \"riscos\": [\"Risco 1\", \"Risco 2\"],\n"
        "  \"recomendacoes\": [\"Ação preventiva 1\"],\n"
        "  \"parecer\": \"Parágrafo final de validação GUARD\"\n"
        "}\n\n"
        "Considere: consumo de tokens Groq (limite 100k/dia), calls de API externas "
        "(Shopify, Meta Graph API), tempo estimado de execução, retorno esperado em "
        "vendas ou engajamento. Seja conservador mas não bloqueie progresso legítimo."
    )


def _ive_user_msg(order: str) -> str:
    return (
        f"Eduardo deu a seguinte ordem às {_local_ts()}:\n\n"
        f"\"{order}\"\n\n"
        "Decomponha em tarefas para os agentes. Responda APENAS com o JSON do plano."
    )


def _guard_user_msg(order: str, plan: dict) -> str:
    return (
        f"Ordem original de Eduardo: \"{order}\"\n\n"
        f"Plano proposto pela IVE:\n{json.dumps(plan, ensure_ascii=False, indent=2)}\n\n"
        "Valide financeiramente e operacionalmente. Responda APENAS com o JSON de validação."
    )


# ── Função principal: criar comando ───────────────────────────────────────────

async def create_command(
    order: str,
    llm_call: Callable[[str, str, int], Coroutine[Any, Any, tuple[str, str]]],
) -> dict:
    """
    Recebe ordem de Eduardo, executa IVE → GUARD e retorna o comando pendente de confirmação.
    `llm_call` é a função llm_call_cascade do main.py.
    """
    cmd_id = str(uuid.uuid4())[:8]
    created_at = _ts()

    # 1. IVE propõe plano
    ive_raw, ive_provider = await llm_call(_ive_system(), _ive_user_msg(order), 800)
    try:
        # Remove possíveis blocos de markdown ```json ... ```
        clean = ive_raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        ive_plan = json.loads(clean.strip())
    except Exception:
        ive_plan = {
            "resumo": order,
            "tarefas": [{"agente": "NEXUS", "tarefa": order, "prioridade": 1, "depende_de": []}],
            "prazo_estimado": "15 minutos",
            "resultado_esperado": "Execução da ordem de Eduardo",
            "_parse_error": ive_raw[:200],
        }

    # 2. GUARD valida
    guard_raw, guard_provider = await llm_call(
        _guard_system(), _guard_user_msg(order, ive_plan), 600
    )
    try:
        clean_g = guard_raw.strip()
        if clean_g.startswith("```"):
            clean_g = clean_g.split("```")[1]
            if clean_g.startswith("json"):
                clean_g = clean_g[4:]
        guard_validation = json.loads(clean_g.strip())
    except Exception:
        guard_validation = {
            "aprovado": True,
            "score_viabilidade": 75,
            "custo_estimado": "Baixo",
            "riscos": ["Parsing de resposta GUARD falhou"],
            "recomendacoes": ["Revisar manualmente o plano"],
            "parecer": guard_raw[:300],
        }

    cmd = {
        "id": cmd_id,
        "ordem": order,
        "status": "aguardando_confirmacao",
        "created_at": created_at,
        "ive_plan": ive_plan,
        "ive_provider": ive_provider,
        "guard_validation": guard_validation,
        "guard_provider": guard_provider,
        "tasks_dispatched": [],
        "tasks_results": {},
        "confirmed_at": None,
        "completed_at": None,
    }

    async with _COMMAND_LOCK:
        _COMMANDS[cmd_id] = cmd

    # Salva no vault
    await _save_command_to_vault(cmd)

    return cmd


async def confirm_command(
    cmd_id: str,
    llm_call: Callable[[str, str, int], Coroutine[Any, Any, tuple[str, str]]],
    dispatch_fn: Callable[[str, str, str], Coroutine[Any, Any, dict]],
) -> dict:
    """
    Eduardo confirma o comando. Dispara todas as tarefas do plano.
    `dispatch_fn(agent_name, task_title, task_description)` → task dict
    """
    async with _COMMAND_LOCK:
        cmd = _COMMANDS.get(cmd_id)
        if not cmd:
            return {"error": f"Comando {cmd_id} não encontrado"}
        if cmd["status"] != "aguardando_confirmacao":
            return {"error": f"Comando {cmd_id} já está em status '{cmd['status']}'"}
        cmd["status"] = "em_execucao"
        cmd["confirmed_at"] = _ts()

    tarefas = cmd["ive_plan"].get("tarefas", [])
    dispatched = []

    # Ordena por prioridade
    tarefas_sorted = sorted(tarefas, key=lambda t: t.get("prioridade", 99))

    for t in tarefas_sorted:
        agente = t.get("agente", "NEXUS")
        tarefa_desc = t.get("tarefa", "Executar tarefa")
        title = f"[{agente}] {tarefa_desc[:60]}"

        try:
            task = await dispatch_fn(agente, title, tarefa_desc)
            dispatched.append({"agente": agente, "task_id": task.get("id"), "title": title})
        except Exception as e:
            dispatched.append({"agente": agente, "error": str(e), "title": title})

    async with _COMMAND_LOCK:
        cmd["tasks_dispatched"] = dispatched
        cmd["status"] = "executando"

    await _save_command_to_vault(cmd)
    return cmd


async def cancel_command(cmd_id: str) -> dict:
    async with _COMMAND_LOCK:
        cmd = _COMMANDS.get(cmd_id)
        if not cmd:
            return {"error": f"Comando {cmd_id} não encontrado"}
        cmd["status"] = "cancelado"
    return cmd


def get_command(cmd_id: str) -> dict | None:
    return _COMMANDS.get(cmd_id)


def list_commands(limit: int = 20) -> list[dict]:
    cmds = list(_COMMANDS.values())
    cmds.sort(key=lambda c: c["created_at"], reverse=True)
    return cmds[:limit]


# ── Persistência no Vault ─────────────────────────────────────────────────────

async def _save_command_to_vault(cmd: dict) -> None:
    try:
        vault_base = r"C:\Users\erick\AURA-decor-vault"
        decisions_dir = os.path.join(vault_base, "Decisoes")
        os.makedirs(decisions_dir, exist_ok=True)

        date_str = datetime.now().strftime("%Y-%m-%d")
        fname = os.path.join(decisions_dir, f"cmd-{cmd['id']}-{date_str}.md")

        guard = cmd.get("guard_validation", {})
        tarefas_md = ""
        for i, t in enumerate(cmd.get("ive_plan", {}).get("tarefas", []), 1):
            tarefas_md += (
                f"{i}. **{t.get('agente','?')}** — {t.get('tarefa','')}\n"
                f"   - Prioridade: {t.get('prioridade','?')} | Depende de: {t.get('depende_de',[])}\n\n"
            )

        dispatched_md = ""
        for d in cmd.get("tasks_dispatched", []):
            status = f"Task ID: {d.get('task_id','?')}" if "task_id" in d else f"❌ Erro: {d.get('error')}"
            dispatched_md += f"- **{d.get('agente')}**: {d.get('title','')[:60]} → {status}\n"

        content = f"""# Comando {cmd['id']} — {cmd['status'].upper()}

**Criado:** {cmd['created_at']}
**Confirmado:** {cmd.get('confirmed_at') or '—'}

## Ordem de Eduardo
> {cmd['ordem']}

## Plano IVE ({cmd.get('ive_provider','?')})
**Resumo:** {cmd.get('ive_plan',{}).get('resumo','')}
**Prazo estimado:** {cmd.get('ive_plan',{}).get('prazo_estimado','')}
**Resultado esperado:** {cmd.get('ive_plan',{}).get('resultado_esperado','')}

### Tarefas
{tarefas_md or '—'}

## Validação GUARD ({cmd.get('guard_provider','?')})
- **Aprovado:** {'✅ Sim' if guard.get('aprovado') else '❌ Não'}
- **Score viabilidade:** {guard.get('score_viabilidade','?')}/100
- **Custo estimado:** {guard.get('custo_estimado','?')}
- **Riscos:** {', '.join(guard.get('riscos', [])) or '—'}
- **Recomendações:** {', '.join(guard.get('recomendacoes', [])) or '—'}

> {guard.get('parecer','')}

## Tarefas Despachadas
{dispatched_md or '—'}

---
*Gerado automaticamente pelo Command Center — {_local_ts()}*
"""
        with open(fname, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        print(f"[COMMAND CENTER] Erro ao salvar vault: {e}")


# ── Formatação para resposta da API ──────────────────────────────────────────

def format_command_for_api(cmd: dict) -> dict:
    """Remove dados internos verbosos, retorna resumo limpo para Eduardo."""
    guard = cmd.get("guard_validation", {})
    return {
        "id": cmd["id"],
        "status": cmd["status"],
        "ordem": cmd["ordem"],
        "created_at": cmd["created_at"],
        "confirmed_at": cmd.get("confirmed_at"),
        "ive": {
            "resumo": cmd.get("ive_plan", {}).get("resumo", ""),
            "prazo": cmd.get("ive_plan", {}).get("prazo_estimado", ""),
            "resultado_esperado": cmd.get("ive_plan", {}).get("resultado_esperado", ""),
            "num_tarefas": len(cmd.get("ive_plan", {}).get("tarefas", [])),
            "tarefas": [
                {
                    "agente": t.get("agente"),
                    "tarefa": t.get("tarefa"),
                    "prioridade": t.get("prioridade"),
                }
                for t in cmd.get("ive_plan", {}).get("tarefas", [])
            ],
            "provider": cmd.get("ive_provider"),
        },
        "guard": {
            "aprovado": guard.get("aprovado", False),
            "score": guard.get("score_viabilidade", 0),
            "custo": guard.get("custo_estimado", "?"),
            "riscos": guard.get("riscos", []),
            "recomendacoes": guard.get("recomendacoes", []),
            "parecer": guard.get("parecer", ""),
            "provider": cmd.get("guard_provider"),
        },
        "execucao": {
            "tarefas_despachadas": cmd.get("tasks_dispatched", []),
        },
    }
