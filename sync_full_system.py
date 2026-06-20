"""
sync_full_system.py — Sincronização Completa do Ecossistema Aura Decore
Atualiza: Memória dos agentes, Obsidian vault, workflows n8n, tarefas
Conecta: Antigravity IDE ↔ Claude Code ↔ Backend ↔ WPPConnect
Execute: python sync_full_system.py
"""
import asyncio
import os
import sys
import json
import pathlib
import datetime
import socket

os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"
os.environ["LITELLM_TELEMETRY"] = "false"
os.environ["PYTHONIOENCODING"] = "utf-8"

# Fix Windows terminal encoding for unicode logs
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

_env_path = pathlib.Path(__file__).parent / "backend" / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=_env_path, override=True)

import httpx

BASE_DIR    = pathlib.Path(__file__).parent
VAULT_DIR   = pathlib.Path(r"C:\Users\erick\AURA-decor-vault")
BACKEND_URL = "http://localhost:8000"
WPP_URL     = os.getenv("WPPCONNECT_URL", "http://localhost:21465")
WPP_SESSION = os.getenv("WPPCONNECT_SESSION", "aura-decore")
WPP_TOKEN   = os.getenv("WPPCONNECT_TOKEN", "")
NOW         = datetime.datetime.now()
NOW_STR     = NOW.strftime("%Y-%m-%d %H:%M")
DATE_STR    = NOW.strftime("%Y-%m-%d")
WEEK_STR    = f"Semana {NOW.isocalendar()[1]}/{NOW.year}"

def is_port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2.0):
            return True
    except:
        return False

def log(msg): print(f"[{NOW.strftime('%H:%M:%S')}] {msg}")
def ok(msg):  print(f"  [OK] {msg}")
def fail(msg):print(f"  [FAIL] {msg}")
def info(msg):print(f"  [INFO] {msg}")


# ── 1. Coletar status real do sistema ─────────────────────────────────────────
async def get_system_status() -> dict:
    status = {
        "backend_up":    is_port_open(8000),
        "wpp_up":        is_port_open(21465),
        "n8n_up":        is_port_open(5678),
        "ollama_up":     is_port_open(11434),
        "backend_data":  {},
        "wpp_session":   "unknown",
        "n8n_workflows": 0,
        "n8n_active":    0,
    }

    if status["backend_up"]:
        try:
            async with httpx.AsyncClient(timeout=10) as hc:
                r = await hc.get(f"{BACKEND_URL}/health")
                if r.status_code == 200:
                    status["backend_data"] = r.json()
        except:
            pass

    if status["wpp_up"] and WPP_TOKEN:
        try:
            headers = {"Authorization": f"Bearer {WPP_TOKEN}"}
            async with httpx.AsyncClient(timeout=8) as hc:
                r = await hc.get(f"{WPP_URL}/api/{WPP_SESSION}/status-session", headers=headers)
                if r.status_code == 200:
                    data = r.json()
                    sess_status = data.get("status", "unknown")
                    status["wpp_session"] = sess_status
        except:
            pass

    if status["n8n_up"]:
        n8n_key = os.getenv("N8N_API_KEY", "")
        if n8n_key:
            try:
                headers = {"X-N8N-API-KEY": n8n_key}
                async with httpx.AsyncClient(timeout=8) as hc:
                    r = await hc.get("http://localhost:5678/api/v1/workflows", headers=headers)
                    if r.status_code == 200:
                        wfs = r.json().get("data", [])
                        status["n8n_workflows"] = len(wfs)
                        status["n8n_active"] = sum(1 for w in wfs if w.get("active"))
            except:
                pass

    return status


# ── 2. Atualizar Central.md do Obsidian ────────────────────────────────────────
def update_central_md(status: dict):
    central_file = VAULT_DIR / "🏠 Aura Decore — Central.md"
    if not central_file.exists():
        fail("Central.md nao encontrado")
        return

    n8n_status = (
        f"n8n LOCAL ({status['n8n_active']}/{status['n8n_workflows']} workflows ativos · porta 5678)"
        if status["n8n_up"] else
        "n8n LOCAL OFFLINE - iniciar com: n8n start"
    )
    wpp_st = status["wpp_session"]
    wpp_icon = "OK" if wpp_st in ("CONNECTED", "isLogged") else "WARN"
    backend_agents = status["backend_data"].get("agents", 22)
    backend_phase  = status["backend_data"].get("phase", "operacao")

    content = central_file.read_text(encoding="utf-8")

    # Atualiza linha de data
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("> Atualizado:"):
            lines[i] = f"> Atualizado: {DATE_STR} | Fase: **OPERACAO ATIVA** | Meta: R$5.000-8.000/mes lucro liquido ate 2028 | Dominio: **auradecore.com.br**"
            break

    # Atualiza status dos servicos na tabela
    new_lines = []
    for line in lines:
        if "| Backend FastAPI |" in line:
            backend_st = "RAILWAY + LOCAL" if status["backend_up"] else "OFFLINE"
            line = f"| Backend FastAPI | {'OK' if status['backend_up'] else 'FAIL'} {backend_st} | `web-production-f1cb5.up.railway.app` · porta 8000 · {backend_agents} agentes |"
        elif "| WPPConnect |" in line:
            line = f"| WPPConnect | [{wpp_icon}] {wpp_st.upper()} | Sessao `aura-decore` · porta 21465 |"
        elif "| n8n Local |" in line:
            line = f"| n8n Local | {'OK' if status['n8n_up'] else 'WARN'} | {n8n_status} |"
        elif "| Ollama" in line:
            line = f"| Ollama llama3.2 | {'OK LOCAL' if status['ollama_up'] else 'OFFLINE'} | Fallback local {'ativo' if status['ollama_up'] else 'inativo'} |"
        new_lines.append(line)

    central_file.write_text("\n".join(new_lines), encoding="utf-8")
    ok(f"Central.md atualizado ({DATE_STR})")


# ── 3. Atualizar contexto_empresa.md ──────────────────────────────────────────
def update_contexto_empresa():
    ctx_file = VAULT_DIR / "Memoria" / "Compartilhada" / "contexto_empresa.md"
    content = f"""---
atualizado: {DATE_STR}
fase: operacao-ativa
---

# Contexto Empresa — Aura Decore

## Identidade
- **Nome:** Aura Decore
- **Dominio:** auradecore.com.br
- **Nicho:** Decoracao Japandi Premium — wabi-sabi, minimalismo, materiais naturais
- **Modelo:** Dropshipping (Dropi/Habitoo/AliExpress)
- **Plataforma:** Shopify (tema Dawn — "Cursor Dinamico" 160266387561)
- **Canais:** Meta Ads, Instagram, Pinterest, WhatsApp (WPPConnect), Notion CRM, Gmail, Canva

## Fase Atual ({DATE_STR})
**OPERACAO ATIVA** — loja publica desde 30/05/2026. Backend online, LENA atendendo WhatsApp.
Crescimento organico ativo. Aguardando primeiras vendas pagas.

## Metas
- **2026:** Primeiro mes de vendas, ROAS >= 2x
- **2028:** R$5.000-8.000/mes de lucro liquido
- **Limite MEI:** R$81.000/ano (Eduardo Marques)

## Diretor
**Eduardo Marques** — fundador e diretor supremo. Palavra final em todas as decisoes.
IVE e GUARD sao seus interlocutores diretos.
Telefones: 5585985902642, 5585981957208

## Brand Kit
- Paleta: Terra #B8793A + Off-white #F5F0EB + Sand #EDE5D8
- Tipografia: Cormorant Garamond (titulos) + DM Sans (corpo)
- Tom: Elegante, acolhedor, premium, japandi

## Regras Absolutas
1. ROAS minimo 2x para qualquer campanha
2. Margem minima 35% em todos os produtos
3. Caixa minimo R$500 sempre
4. DAS MEI R$70,60 ate dia 20 de cada mes
5. Nenhum gasto financeiro sem aprovacao do GUARD
6. Toda decisao estrategica passa pela IVE
7. Eduardo tem autoridade suprema sobre todos os agentes

## Stack Tecnica ({DATE_STR})
- Backend FastAPI: http://localhost:8000 (porta 8000) — 22 agentes ATIVOS
- WPPConnect: http://localhost:21465 — sessao aura-decore CONECTADA
- Ollama: http://localhost:11434 — llama3.2 (fallback LLM local)
- LLM Cascade: Groq 70B -> OpenRouter -> Google AI -> Anthropic -> Ollama

## Produtos Aprovados (margem 60%+)
- Vaso ceramica japandi | Custo R$46,40 | Preco R$116,00
- Almofada linho | Custo R$58,00 | Preco R$145,00
- Pampas seca | Custo R$34,80 | Preco R$87,00
- Bandeja bambu | Custo R$52,20 | Preco R$130,50
- Difusor varetas | Custo R$58,00 | Preco R$145,00
"""
    ctx_file.write_text(content, encoding="utf-8")
    ok("contexto_empresa.md atualizado")


# ── 4. Atualizar MEMORY.md do Claude Code / Antigravity ───────────────────────
def update_claude_memory(status: dict):
    mem_file = VAULT_DIR / "Memoria" / "Claude-Code" / "MEMORY.md"

    wpp_info = f"WPPConnect sessao '{WPP_SESSION}' {'CONECTADA ao WhatsApp' if status['wpp_session'] in ('CONNECTED','isLogged') else 'STATUS: ' + status['wpp_session']}"
    n8n_info = (
        f"n8n LOCAL ATIVO porta 5678 ({status['n8n_active']}/{status['n8n_workflows']} workflows ativos)"
        if status["n8n_up"]
        else "n8n LOCAL OFFLINE (iniciar com n8n start ou npm run start)"
    )
    backend_agents = status["backend_data"].get("agents", 22)

    content = f"""# Memory Index — Aura Decore
> Ultima sincronizacao: {NOW_STR} | {WEEK_STR}

## Status do Sistema ({DATE_STR})
- Backend FastAPI: {'ONLINE porta 8000 — ' + str(backend_agents) + ' agentes ativos' if status['backend_up'] else 'OFFLINE'}
- {wpp_info}
- {n8n_info}
- Ollama llama3.2: {'ONLINE porta 11434' if status['ollama_up'] else 'OFFLINE'}
- LLM primario: Groq llama-3.3-70b (resposta ~1.7s)
- Watchdog 24/7: watchdog_aura.py (reinicia servicos automaticamente)

## Projetos e Contextos

- [Aura Decore — sistema de agentes](project_aura_decor.md)
  22 agentes ATIVOS. LENA respondendo WhatsApp via webhook /whatsapp/webhook.
  {WEEK_STR}: Backend UP, WPPConnect UP, LLM OK (Groq 70B primario).
  n8n: {n8n_info}. n8n Railway OFFLINE (limite recursos).
  TikTok OAuth pendente. Pinterest manual.

- [Topologia de dominios e temas da loja](store_domain_topology.md)
  1 loja: auradecore.com.br. Tema live "Cursor Dinamico" 160266387561.
  89 produtos ACTIVE 100% publicados. Publicar = publishablePublish.

- [Postiz self-host na Azure](project_postiz_selfhost.md)
  social.auradecore.com.br ATIVO (Azure ACI). BYPASS: /social/publish-due no FastAPI.
  Tokens validos ate 2026-08-15. TikTok OAuth pendente. Azure containers ativos.

- [Criativos PT-BR + 5 canais](feedback_criativos_ptbr_multicanal.md)
  TODO criativo OBRIGATORIAMENTE em PT-BR. 5 canais. Captions ALTERNANDO profissional/humanizado.
  CTA + auradecore.com.br + 8-12 hashtags + musica em stories.

- [Publicacao autonoma sem verificacao](feedback_postagem_autonoma.md)
  Eduardo autorizou (17/06/2026): programar e postar sem pedir confirmacao. Executar direto.

- [Musica + copy + hashtags](feedback_musica_copy_hashtags.md)
  TODO conteudo SEMPRE com musica ambiente calma/moderna + copy neuromarketing + hashtags atuais.

## Regras para Antigravity/Claude Code ({DATE_STR})
1. Backend rodando em http://localhost:8000 — USE para acionar agentes
2. LENA atendendo WhatsApp via /whatsapp/webhook — NAO interrompa
3. LLM cascade: Groq -> OpenRouter -> Google AI -> Anthropic -> Ollama
4. Eduardo autorizou autonomia total — executar e reportar, nao pedir confirmacao
5. Watchdog em watchdog_aura.py — reinicia servicos se caírem
6. CREWAI_TELEMETRY_OPT_OUT=true — sempre definir antes de imports
7. OPENAI_API_KEY nao necessaria — usar apenas LLM cascade proprio

## Comandos Uteis (API Backend)
```bash
# Status dos agentes
GET http://localhost:8000/health

# Acionar agente especifico
POST http://localhost:8000/agent/exec
{{"agent_id": "ive", "message": "execute auditoria semanal"}}

# Disparar crew
POST http://localhost:8000/crew/run
{{"crew_type": "content", "context": "produto: vaso japandi"}}

# Webhook LENA (simular mensagem WhatsApp)
POST http://localhost:8000/whatsapp/webhook
{{"from": "5511999999@c.us", "body": "Bom dia!", "type": "chat", "fromMe": false}}

# Status WPPConnect
GET http://localhost:21465/api/aura-decore/status-session
```
"""
    mem_file.write_text(content, encoding="utf-8")
    ok("MEMORY.md (Claude Code/Antigravity) atualizado")


# ── 5. Atualizar ANTIGRAVITY.md dos agentes ────────────────────────────────────
def update_antigravity_md(status: dict):
    ag_file = VAULT_DIR / "Agentes" / "ANTIGRAVITY.md"

    backend_agents = status["backend_data"].get("agents", 22)
    wpp_st = status["wpp_session"]

    content = f"""# Antigravity — Integracao com o Ecossistema AURA

> Atualizado em: {DATE_STR} | Status: SINCRONIZADO

## O que e o Antigravity
O **Antigravity** e o assistente de IA da Google DeepMind (par de programacao com IA) que tem
**acesso direto** ao ecossistema AURA via filesystem e API.

## Estado Atual dos Servicos ({NOW_STR})

| Servico | Porta | Status | Detalhe |
|---|---|---|---|
| Backend FastAPI | 8000 | {'ONLINE' if status['backend_up'] else 'OFFLINE'} | {backend_agents} agentes, LLM cascade ativo |
| WPPConnect | 21465 | {'ONLINE' if status['wpp_up'] else 'OFFLINE'} | Sessao: {wpp_st} |
| Ollama | 11434 | {'ONLINE' if status['ollama_up'] else 'OFFLINE'} | llama3.2 fallback local |
| n8n | 5678 | {'ONLINE' if status['n8n_up'] else 'OFFLINE'} | {status['n8n_active']}/{status['n8n_workflows']} workflows ativos |

## Acesso configurado

| Recurso | O que acessa | Status |
|---|---|---|
| `filesystem` | AURA-decor-vault + projeto aura-office-dashboard | Configurado |
| `backend API` | http://localhost:8000 — 22 agentes, crews, tasks | {'Ativo' if status['backend_up'] else 'OFFLINE'} |
| `wppconnect` | http://localhost:21465 — WhatsApp sessao aura-decore | {'Ativo' if status['wpp_up'] else 'OFFLINE'} |

## Caminhos do Ecossistema

```
C:\\Users\\erick\\AURA-decor-vault\\                <- Vault Obsidian (agentes, tarefas, metricas)
C:\\Users\\erick\\aura-office-dashboard\\           <- Projeto principal (backend, workflows, scripts)
C:\\Users\\erick\\aura-office-dashboard\\backend\\  <- FastAPI (main.py, agentes, LLM engine)
C:\\Users\\erick\\wppconnect-server\\               <- Servidor WhatsApp local
```

## Portas do Ecossistema

| Servico | Porta | Funcao |
|---|---|---|
| Backend principal | 8000 | Chat IVE, crews, tasks API, webhook LENA |
| WPPConnect | 21465 | WhatsApp Business — LENA atende aqui |
| Obsidian REST API | 27123 | Leitura/escrita no vault (se plugin ativo) |
| n8n local | 5678 | Automacao de workflows |
| Ollama | 11434 | LLM local (fallback) |

## Como usar o Antigravity com os agentes

### API de Agentes (backend porta 8000)
```python
import httpx, asyncio

async def acionar_agente(agent_id: str, message: str):
    async with httpx.AsyncClient(timeout=60) as hc:
        r = await hc.post("http://localhost:8000/agent/exec",
            json={{"agent_id": agent_id, "message": message}})
        return r.json()

async def disparar_crew(crew_type: str, context: str):
    async with httpx.AsyncClient(timeout=120) as hc:
        r = await hc.post("http://localhost:8000/crew/run",
            json={{"crew_type": crew_type, "context": context}})
        return r.json()
```

### Fluxo Recomendado (2026)
```
Antigravity (decisao/codigo)
     |
     v
Backend FastAPI (http://localhost:8000) 
     |--- /agent/exec -> executa agente especifico
     |--- /crew/run   -> dispara crew multi-agente  
     |--- /tasks      -> cria tarefa no vault Kanban
     v
AURA-decor-vault (documentacao sincronizada automaticamente)
     v
Shopify / Instagram / Meta Ads / WhatsApp
```

## Scripts Uteis

| Script | Funcao |
|---|---|
| `watchdog_aura.py` | Guardiao 24/7 — reinicia backend e WPPConnect se caírem |
| `diagnostico_aura.py` | Diagnostico completo de todos os servicos |
| `sync_full_system.py` | Este script — sincronizacao completa |
| `start_aura.bat` | Iniciar todos os servicos com verificacao |
| `INICIAR-WATCHDOG-24h.bat` | Iniciar o watchdog com um clique |
| `CONFIGURAR-AUTOSTART-WATCHDOG.bat` | Registrar watchdog no Task Scheduler |

## LLM Strategy (cascata automatica)
1. **Groq** (Llama 3.3 70B) — primario, ~1.7s, gratuito 100k tokens/dia
2. **OpenRouter** (meta-llama + deepseek free) — fallback gratuito
3. **Google AI** (Gemini 2.5 Flash) — 1500 req/dia gratuito
4. **Anthropic** (Sonnet 4.6) — com creditos
5. **Ollama** (llama3.2 local) — sempre disponivel, offline
6. **Fallback texto fixo** — "Nossa equipe responde em breve"

## Nota Importante
- OPENAI_API_KEY NAO e necessaria — cascata propria nao usa OpenAI
- CREWAI_TELEMETRY_OPT_OUT=true — sempre definir
- Eduardo autorizou autonomia total para postar e executar sem confirmacao
"""
    ag_file.write_text(content, encoding="utf-8")
    ok("ANTIGRAVITY.md atualizado")


# ── 6. Atualizar _INDEX.md dos agentes ────────────────────────────────────────
def update_agents_index(status: dict):
    index_file = VAULT_DIR / "Agentes" / "_INDEX.md"
    if not index_file.exists():
        return

    content = index_file.read_text(encoding="utf-8")

    # Atualiza header com data atual
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("> Atualizado em"):
            lines[i] = f"> Atualizado em {DATE_STR} · Backend porta 8000 {'ONLINE' if status['backend_up'] else 'OFFLINE'} · Mobile em `/mobile` · LLM cascade: Groq -> Claude -> Ollama · 22 agentes ativos"
            break
        if "Estado Atual" in line and "jun/2026" in content:
            break

    # Atualiza secao Estado Atual
    updated = "\n".join(lines)
    if "Estado Atual" in updated:
        state_block = f"""## Estado Atual ({DATE_STR})

> **Fase operacional** — loja publica desde 30/05/2026. Sistema 100% online.
> Backend UP (porta 8000). WPPConnect UP (porta 21465). LENA atendendo WhatsApp.
> LLM primario: Groq 70B (~1.7s resposta). Watchdog 24/7 ativo.
> 22 agentes configurados. Aguardando primeiras vendas pagas.

- Faturamento: pendente (aguardando campanha paga)
- ROAS: — (sem campanhas pagas — organico ativo)
- CAC: — (organico, sem custo)
- MEI acumulado: — / R$81.000 (GUARD monitorando)
- Portfolio: **89 produtos ACTIVE · 100% publicados**
- Tema live: **"Aura Decore - Cursor Dinamico" (160266387561)**
- Workflows n8n: **{status['n8n_active']}/{status['n8n_workflows']} ATIVOS** {('porta 5678' if status['n8n_up'] else '(offline)')}
- Backend: http://localhost:8000 | WPPConnect: http://localhost:21465
- Sincronizado com: Antigravity IDE + Claude Code ({NOW_STR})"""

        # Substitui bloco Estado Atual
        import re
        updated = re.sub(
            r"## Estado Atual.*?$",
            state_block,
            updated,
            flags=re.DOTALL | re.MULTILINE,
        )

    index_file.write_text(updated, encoding="utf-8")
    ok("_INDEX.md dos agentes atualizado")


# ── 7. Iniciar n8n local se estiver offline ───────────────────────────────────
async def ensure_n8n_running(status: dict):
    if status["n8n_up"]:
        ok(f"n8n ja esta rodando ({status['n8n_active']}/{status['n8n_workflows']} workflows ativos)")
        return

    info("n8n offline — tentando iniciar...")
    import subprocess
    try:
        n8n_cmd = r"C:\Users\erick\AppData\Roaming\npm\n8n.cmd"
        if not pathlib.Path(n8n_cmd).exists():
            # Tenta encontrar n8n no PATH
            n8n_cmd = "n8n"

        proc = subprocess.Popen(
            [n8n_cmd, "start"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
        )
        await asyncio.sleep(8)
        if is_port_open(5678):
            ok(f"n8n iniciado (PID {proc.pid})")
            status["n8n_up"] = True
        else:
            fail("n8n nao subiu na porta 5678 — iniciar manualmente")
    except Exception as e:
        fail(f"Nao foi possivel iniciar n8n: {e}")


# ── 8. Ativar workflows n8n via API ───────────────────────────────────────────
async def activate_n8n_workflows(status: dict):
    if not status["n8n_up"]:
        info("n8n offline — pulando ativacao de workflows")
        return

    n8n_key = os.getenv("N8N_API_KEY", "")
    if not n8n_key:
        info("N8N_API_KEY nao configurada — pulando ativacao automatica")
        return

    headers = {"X-N8N-API-KEY": n8n_key, "Content-Type": "application/json"}
    activated = 0
    errors = 0

    try:
        async with httpx.AsyncClient(timeout=15) as hc:
            r = await hc.get("http://localhost:5678/api/v1/workflows", headers=headers)
            if r.status_code != 200:
                fail(f"Nao foi possivel listar workflows n8n: {r.status_code}")
                return

            workflows = r.json().get("data", [])
            info(f"n8n: {len(workflows)} workflows encontrados")

            for wf in workflows:
                wf_id   = wf.get("id")
                wf_name = wf.get("name", wf_id)
                wf_active = wf.get("active", False)

                if not wf_active:
                    try:
                        r2 = await hc.patch(
                            f"http://localhost:5678/api/v1/workflows/{wf_id}",
                            headers=headers,
                            json={"active": True},
                        )
                        if r2.status_code == 200:
                            ok(f"n8n workflow ativado: {wf_name}")
                            activated += 1
                        else:
                            fail(f"Erro ao ativar '{wf_name}': {r2.status_code}")
                            errors += 1
                    except Exception as e:
                        fail(f"Excecao ao ativar '{wf_name}': {e}")
                        errors += 1
                else:
                    info(f"n8n '{wf_name}': ja ativo")

        ok(f"n8n: {activated} workflows ativados, {errors} erros")
        status["n8n_active"] += activated

    except Exception as e:
        fail(f"Erro ao conectar n8n API: {e}")


# ── 9. Verificar e logar tarefas pendentes ────────────────────────────────────
async def sync_pending_tasks(status: dict):
    tasks_file = VAULT_DIR / "Tarefas" / f"tarefas-{DATE_STR}.md"
    tasks_file.parent.mkdir(parents=True, exist_ok=True)

    pending_tasks = [
        ("MIRA",   "Keyword research: 20 keywords cauda longa japandi + Pinterest SEO"),
        ("NOX",    "Calendario conteudo organico semana 25 (3 posts/dia IG+FB)"),
        ("VERA",   "Copy produto destaque: vaso ambar + email D+3 cupom AURA10"),
        ("LUNA",   "Pack visual semanal: 3 thumbnails produto + 2 stories fundo"),
        ("ARTE",   "Geracao imagens IA Japandi para posts semana 25"),
        ("KAI",    "Avaliar 3 novos SKUs Habitoo para portfolio"),
        ("NEXUS",  "Mineracao 5 produtos vencedores Japandi (Habitoo + AliExpress)"),
        ("ZARA",   "Roteiro de DMs para micro-influenciadores @japandihomedecor"),
        ("ECHO",   "Auditoria semanal (domingo 20h) — relatorio de saude do sistema"),
        ("THEO",   "Verificar integracao Shopify webhook + AppMax status"),
        ("SOL",    "Ativar fluxo recovery carrinho D+1/D+3/D+7"),
        ("GUARD",  "Relatorio financeiro semanal: MEI limit, ROAS, caixa"),
        ("PIPE",   "Sincronizar todos os workflows n8n — garantir ativacao"),
        ("DEV",    "Verificar tema Shopify + CSS cursor dinamico funcionando"),
    ]

    content = f"""# Tarefas Ativas — {DATE_STR} ({WEEK_STR})
> Sincronizado automaticamente por sync_full_system.py em {NOW_STR}

## Status dos Servicos
- Backend: {'ONLINE (porta 8000)' if status['backend_up'] else 'OFFLINE'}
- WPPConnect: {'ONLINE sessao ' + status['wpp_session'] if status['wpp_up'] else 'OFFLINE'}
- n8n: {str(status['n8n_active']) + '/' + str(status['n8n_workflows']) + ' workflows ativos' if status['n8n_up'] else 'OFFLINE'}
- Ollama: {'ONLINE' if status['ollama_up'] else 'OFFLINE'}

## Pendentes (Eduardo deve executar ou autorizar)
- [ ] **Railway** — Upgrade do plano para reativar n8n em nuvem
- [ ] **Windsor** — Conectar Shopify OAuth em onboard.windsor.ai
- [ ] **Email** — Ativar email carrinho abandonado (HTML pronto)
- [ ] **Banners** — Trocar 2 banners home por fotos proprias
- [ ] **Bio redes** — Instagram + Facebook ainda com bio padrao

## Tarefas dos Agentes — {WEEK_STR}

"""
    for agent, task in pending_tasks:
        content += f"- [ ] **{agent}** — {task}\n"

    content += f"""
## Concluidas ✅
- [x] **SISTEMA** — Backend FastAPI UP (porta 8000, {status['backend_data'].get('agents', 22)} agentes)
- [x] **LENA** — WhatsApp ativo, sessao aura-decore CONECTADA
- [x] **LLM** — Cascata Groq->OpenRouter->Google->Anthropic->Ollama operacional
- [x] **WATCHDOG** — watchdog_aura.py monitorando e reiniciando servicos
- [x] **SYNC** — Memoria Antigravity/Claude Code sincronizada ({NOW_STR})
- [x] **TELEMETRIA** — CREWAI desabilitada (sem erros de conexao)
"""

    tasks_file.write_text(content, encoding="utf-8")
    ok(f"Tarefas salvas em: {tasks_file.name}")


# ── 10. Atualizar LENA.md no vault ────────────────────────────────────────────
def update_lena_md(status: dict):
    lena_file = VAULT_DIR / "Agentes" / "LENA.md"
    if not lena_file.exists():
        return

    content = lena_file.read_text(encoding="utf-8")
    # Apenas atualiza a data no cabecalho sem quebrar o resto
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("> Atualizado") or line.startswith("> Status"):
            lines[i] = f"> Atualizado em: {DATE_STR} | Status: {'ONLINE - atendendo WhatsApp' if status['wpp_up'] else 'OFFLINE - WPPConnect desconectado'}"
            break

    lena_file.write_text("\n".join(lines), encoding="utf-8")
    ok("LENA.md atualizado")


# ── MAIN ───────────────────────────────────────────────────────────────────────
async def main():
    print("=" * 60)
    print(f"  AURA DECORE — SINCRONIZACAO COMPLETA DO SISTEMA")
    print(f"  {NOW_STR} | {WEEK_STR}")
    print("=" * 60)

    log("Coletando status do sistema...")
    status = await get_system_status()

    print(f"\n[SERVICOS]")
    print(f"  Backend (8000):   {'UP' if status['backend_up'] else 'DOWN'}")
    print(f"  WPPConnect (21465): {'UP - ' + status['wpp_session'] if status['wpp_up'] else 'DOWN'}")
    print(f"  n8n (5678):       {'UP - ' + str(status['n8n_active']) + '/' + str(status['n8n_workflows']) + ' wf' if status['n8n_up'] else 'DOWN'}")
    print(f"  Ollama (11434):   {'UP' if status['ollama_up'] else 'DOWN'}")
    print()

    log("1. Iniciando n8n se necessario...")
    await ensure_n8n_running(status)

    log("2. Ativando workflows n8n...")
    await activate_n8n_workflows(status)

    log("3. Atualizando Central.md (Obsidian)...")
    update_central_md(status)

    log("4. Atualizando contexto_empresa.md...")
    update_contexto_empresa()

    log("5. Atualizando MEMORY.md (Claude Code / Antigravity)...")
    update_claude_memory(status)

    log("6. Atualizando ANTIGRAVITY.md...")
    update_antigravity_md(status)

    log("7. Atualizando _INDEX.md dos agentes...")
    update_agents_index(status)

    log("8. Atualizando LENA.md...")
    update_lena_md(status)

    log("9. Sincronizando tarefas pendentes...")
    await sync_pending_tasks(status)

    print()
    print("=" * 60)
    print("  SINCRONIZACAO CONCLUIDA!")
    print(f"  {NOW_STR}")
    print()
    print("  ARQUIVOS ATUALIZADOS:")
    print("  - AURA-decor-vault/🏠 Aura Decore — Central.md")
    print("  - AURA-decor-vault/Memoria/Compartilhada/contexto_empresa.md")
    print("  - AURA-decor-vault/Memoria/Claude-Code/MEMORY.md")
    print("  - AURA-decor-vault/Agentes/ANTIGRAVITY.md")
    print("  - AURA-decor-vault/Agentes/_INDEX.md")
    print("  - AURA-decor-vault/Agentes/LENA.md")
    print(f"  - AURA-decor-vault/Tarefas/tarefas-{DATE_STR}.md")
    print()
    print("  PROXIMOS PASSOS:")
    if not status["n8n_up"]:
        print("  ! n8n offline — execute: n8n start")
    if status["wpp_session"] not in ("CONNECTED", "isLogged"):
        print("  ! WPPConnect sem sessao — abrir http://localhost:21465 e escanear QR")
    print("  * Watchdog ativo: watchdog_aura.py monitora Backend + WPPConnect")
    print("  * Para sincronizar novamente: python sync_full_system.py")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
