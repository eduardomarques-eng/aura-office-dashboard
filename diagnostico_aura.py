"""
diagnostico_aura.py — Diagnóstico e Teste Completo do Sistema Aura Decore
Testa: Backend FastAPI, WPPConnect, LLM Engine, Webhook LENA
Execute: python diagnostico_aura.py
"""
import asyncio
import os
import sys
import json
import socket
import pathlib
import time
import datetime

# Fix Windows terminal encoding for unicode logs
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"
os.environ["LITELLM_TELEMETRY"] = "false"

# Carrega o .env antes de qualquer coisa
_env_path = pathlib.Path(__file__).parent / "backend" / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=_env_path, override=True)

import httpx

# ── Cores de terminal ─────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):   print(f"  {GREEN}[OK] {msg}{RESET}")
def fail(msg): print(f"  {RED}[FAIL] {msg}{RESET}")
def warn(msg): print(f"  {YELLOW}[WARN] {msg}{RESET}")
def info(msg): print(f"  {BLUE}[INFO] {msg}{RESET}")
def title(msg):print(f"\n{BOLD}{BLUE}{'='*55}{RESET}\n{BOLD}  {msg}{RESET}\n{BOLD}{BLUE}{'='*55}{RESET}")

def check_port(port: int, host: str = "127.0.0.1") -> bool:
    try:
        with socket.create_connection((host, port), timeout=2.0):
            return True
    except OSError:
        return False

# ── 1. Variáveis de ambiente ───────────────────────────────────────────────────
async def check_env_vars():
    title("1. Variáveis de Ambiente Críticas")
    required = {
        "GROQ_API_KEY":      "LLM principal (Groq Llama-70B) — gratuito 100k/dia",
        "GOOGLE_AI_KEY":     "LLM fallback (Gemini 2.5 Flash) — 1500 req/dia",
        "OPENROUTER_API_KEY":"LLM fallback (OpenRouter free models)",
        "WPPCONNECT_URL":    "URL do servidor WPPConnect",
        "WPPCONNECT_SECRET": "Chave secreta do WPPConnect",
        "WPPCONNECT_TOKEN":  "Bearer token da sessão WPPConnect",
        "WPPCONNECT_SESSION":"Nome da sessão WPP (ex: aura-decore)",
        "SHOPIFY_DOMAIN":    "Domínio Shopify (lookup de pedidos)",
        "SHOPIFY_ADMIN_TOKEN":"Token admin Shopify",
    }
    optional = {
        "ANTHROPIC_API_KEY": "Claude Sonnet fallback",
        "TOGETHER_API_KEY":  "Together AI fallback",
        "OPENAI_API_KEY":    "OpenAI (não usado na cascata, apenas CrewAI)",
        "EDUARDO_PHONE":     "Telefone do Eduardo para ordens executivas",
    }
    
    for key, desc in required.items():
        val = os.getenv(key, "")
        if val and len(val) > 5:
            ok(f"{key}: configurado ({val[:8]}...)")
        else:
            fail(f"{key}: VAZIO — {desc}")
    
    print()
    for key, desc in optional.items():
        val = os.getenv(key, "")
        if val and len(val) > 3:
            ok(f"{key}: configurado")
        else:
            warn(f"{key}: vazio — {desc}")

# ── 2. Portas e serviços ───────────────────────────────────────────────────────
async def check_services():
    title("2. Serviços e Conectividade")
    wpp_url = os.getenv("WPPCONNECT_URL", "http://localhost:21465")
    n8n_url = os.getenv("N8N_BASE_URL", "http://localhost:5678")
    
    # 1. Backend FastAPI (local)
    if check_port(8000):
        ok("FastAPI Backend local (porta 8000) — UP")
    else:
        warn("FastAPI Backend local (porta 8000) — DOWN (Não crítico se rodando no Railway)")

    # 2. WPPConnect Server (local ou remoto)
    import urllib.parse
    wpp_parsed = urllib.parse.urlparse(wpp_url)
    wpp_host = wpp_parsed.hostname or "127.0.0.1"
    is_wpp_local = wpp_host in ("localhost", "127.0.0.1")
    
    if is_wpp_local:
        if check_port(21465):
            ok("WPPConnect Server local (porta 21465) — UP")
        else:
            fail("WPPConnect Server local (porta 21465) — DOWN ⚠️ CRÍTICO")
    else:
        # Check remote connectivity
        try:
            async with httpx.AsyncClient(timeout=5) as hc:
                r = await hc.get(f"{wpp_url}/api-docs/")
                if r.status_code == 200:
                    ok(f"WPPConnect Server remoto ({wpp_host}) — UP (HTTP 200)")
                else:
                    fail(f"WPPConnect Server remoto ({wpp_host}) — DOWN (HTTP {r.status_code})")
        except Exception as e:
            fail(f"WPPConnect Server remoto ({wpp_host}) — INACESSÍVEL: {e}")

    # 3. n8n (local ou remoto)
    n8n_parsed = urllib.parse.urlparse(n8n_url)
    n8n_host = n8n_parsed.hostname or "127.0.0.1"
    is_n8n_local = n8n_host in ("localhost", "127.0.0.1")
    
    if is_n8n_local:
        if check_port(5678):
            ok("n8n local (porta 5678) — UP")
        else:
            warn("n8n local (porta 5678) — offline (opcional)")
    else:
        # Check remote connectivity
        try:
            async with httpx.AsyncClient(timeout=5) as hc:
                r = await hc.get(f"{n8n_url}/healthz")
                if r.status_code == 200:
                    ok(f"n8n remoto ({n8n_host}) — UP (HTTP 200)")
                else:
                    warn(f"n8n remoto ({n8n_host}) — DOWN (HTTP {r.status_code})")
        except Exception as e:
            warn(f"n8n remoto ({n8n_host}) — INACESSÍVEL: {e}")

    # 4. Ollama (local)
    if check_port(11434):
        ok("Ollama local (porta 11434) — UP")
    else:
        warn("Ollama local (porta 11434) — offline (opcional)")

# ── 3. Health check do backend ────────────────────────────────────────────────
async def check_backend_health():
    title("3. Backend FastAPI — Health Check")
    # Tenta local
    try:
        async with httpx.AsyncClient(timeout=5) as hc:
            r = await hc.get("http://localhost:8000/health")
            if r.status_code == 200:
                data = r.json()
                ok(f"Backend Local: {r.status_code} OK")
                info(f"Resposta Local: {json.dumps(data, ensure_ascii=False)[:200]}")
                return
    except Exception:
        pass

    # Tenta remoto
    prod_url = os.getenv("RAILWAY_URL", "https://backend.auradecore.com.br")
    if "localhost" in prod_url or "127.0.0.1" in prod_url:
        prod_url = "https://backend.auradecore.com.br"
    
    info(f"Local offline. Testando Backend Remoto em: {prod_url}/health")
    try:
        async with httpx.AsyncClient(timeout=10) as hc:
            r = await hc.get(f"{prod_url}/health")
            if r.status_code == 200:
                data = r.json()
                ok(f"Backend Remoto: {r.status_code} OK")
                info(f"Resposta Remota: {json.dumps(data, ensure_ascii=False)[:200]}")
            else:
                fail(f"Backend Remoto retornou {r.status_code}: {r.text[:100]}")
    except Exception as e:
        fail(f"Backend Remoto inacessível: {e}")

# ── 4. Teste do motor LLM ─────────────────────────────────────────────────────
async def check_llm_engine():
    title("4. Motor LLM — Cascata de Provedores")
    try:
        sys.path.insert(0, str(pathlib.Path(__file__).parent / "backend"))
        from llm_engine import llm as _llm, GROQ_KEY, GOOGLE_KEY, OPENROUTER_KEY, ANTHROPIC_KEY
        
        info(f"Groq key: {'✅ configurada' if GROQ_KEY else '❌ vazia'}")
        info(f"Google key: {'✅ configurada' if GOOGLE_KEY else '❌ vazia'}")
        info(f"OpenRouter key: {'✅ configurada' if OPENROUTER_KEY else '❌ vazia'}")
        info(f"Anthropic key: {'✅ configurada' if ANTHROPIC_KEY else '❌ vazia'}")
        
        print(f"\n  Testando chamada LLM (timeout 30s)...")
        start = time.time()
        text, provider = await asyncio.wait_for(
            _llm(
                "Você é LENA. Responda só 'ok' em português.",
                [{"role": "user", "content": "teste de conexão"}],
                max_tokens=20
            ),
            timeout=35.0
        )
        elapsed = time.time() - start
        ok(f"LLM respondeu via [{provider}] em {elapsed:.1f}s: \"{text[:80]}\"")
    except asyncio.TimeoutError:
        fail("LLM timeout (>35s) — todos os provedores falharam ou lentos demais")
    except Exception as e:
        fail(f"Erro no LLM engine: {e}")

# ── 5. WPPConnect status ───────────────────────────────────────────────────────
async def check_wppconnect():
    title("5. WPPConnect — Status da Sessão WhatsApp")
    wpp_url  = os.getenv("WPPCONNECT_URL", "http://localhost:21465")
    wpp_sess = os.getenv("WPPCONNECT_SESSION", "aura-decore")
    wpp_tok  = os.getenv("WPPCONNECT_TOKEN", "")
    
    import urllib.parse
    wpp_parsed = urllib.parse.urlparse(wpp_url)
    wpp_host = wpp_parsed.hostname or "127.0.0.1"
    is_wpp_local = wpp_host in ("localhost", "127.0.0.1")
    
    if is_wpp_local and not check_port(21465):
        fail("WPPConnect local offline (porta 21465 fechada)")
        info("Para iniciar: cd C:\\Users\\erick\\wppconnect-server && npm run start")
        return
    
    if not wpp_tok:
        warn("WPPCONNECT_TOKEN não configurado")
        return
    
    headers = {"Authorization": f"Bearer {wpp_tok}"}
    try:
        async with httpx.AsyncClient(timeout=10) as hc:
            # Primeiro tenta check-connection-session que é mais estável quando já logado
            try:
                r_conn = await hc.get(f"{wpp_url}/api/{wpp_sess}/check-connection-session", headers=headers)
                if r_conn.status_code == 200:
                    conn_data = r_conn.json()
                    if conn_data.get("status") is True or conn_data.get("message") == "Connected":
                        ok(f"Sessão '{wpp_sess}': CONECTADA ao WhatsApp ✅")
                        return
            except Exception:
                pass

            # Se não retornar sucesso, tenta status-session
            r = await hc.get(f"{wpp_url}/api/{wpp_sess}/status-session", headers=headers)
            data = r.json()
            status = data.get("status", "unknown")
            if status in ("CONNECTED", "isLogged", "PAIRED", "NORMAL", "MAIN"):
                ok(f"Sessão '{wpp_sess}': CONECTADA ao WhatsApp ({status}) ✅")
            else:
                warn(f"Sessão '{wpp_sess}': {status} — QR Code pode ser necessário")
                if is_wpp_local:
                    info(f"Abra: http://localhost:21465 para escanear o QR")
                else:
                    info(f"Abra: https://wpp.auradecore.com.br/ para escanear o QR")
    except Exception as e:
        warn(f"Não foi possível verificar status da sessão: {e}")

# ── 6. Teste do webhook LENA ──────────────────────────────────────────────────
async def test_lena_webhook():
    title("6. Simulação: Webhook WhatsApp → LENA")
    
    # Check if we should call local backend or Remote backend
    prod_url = os.getenv("RAILWAY_URL", "https://backend.auradecore.com.br")
    if "localhost" in prod_url or "127.0.0.1" in prod_url:
        prod_url = "https://backend.auradecore.com.br"
    target_url = "http://localhost:8000" if check_port(8000) else prod_url
    
    info(f"Usando target backend: {target_url}")
    
    payload = {
        "from":       "5511999999999@c.us",
        "senderName": "Teste Diagnóstico",
        "body":       "Bom dia, tudo bem?",
        "type":       "chat",
        "id":         f"test_{int(time.time())}",
        "fromMe":     False,
        "isGroupMsg": False,
    }
    
    info(f"Enviando payload: {json.dumps(payload, ensure_ascii=False)}")
    try:
        async with httpx.AsyncClient(timeout=40) as hc:
            start = time.time()
            r = await hc.post(f"{target_url}/whatsapp/webhook", json=payload)
            elapsed = time.time() - start
            
            if r.status_code == 200:
                data = r.json()
                ok(f"Webhook respondeu em {elapsed:.1f}s | Status: {r.status_code}")
                info(f"Agente: {data.get('agent', '?')}")
                info(f"Intenção: {data.get('intent', '?')}")
                reply = data.get('reply', '')
                if reply:
                    ok(f"Resposta LENA: \"{reply[:150]}\"")
                else:
                    warn("LENA não gerou resposta!")
            else:
                fail(f"Webhook retornou {r.status_code}: {r.text[:200]}")
    except asyncio.TimeoutError:
        fail("Webhook timeout (>40s) — LENA não processou a mensagem")
    except Exception as e:
        fail(f"Erro ao chamar webhook: {e}")

# ── Relatório final ───────────────────────────────────────────────────────────
async def main():
    print(f"\n{BOLD}{'='*55}")
    print("  AURA DECORE - DIAGNOSTICO COMPLETO DO SISTEMA")
    print(f"  {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{'='*55}{RESET}")
    
    await check_env_vars()
    await check_services()
    await check_backend_health()
    await check_llm_engine()
    await check_wppconnect()
    await test_lena_webhook()
    
    print(f"\n{BOLD}{GREEN}{'='*55}")
    print("  Diagnostico concluido!")
    print(f"{'='*55}{RESET}")
    print()

if __name__ == "__main__":
    asyncio.run(main())
