# llm_engine.py — Motor LLM compartilhado da Aura Decore
# Cascata: Groq/70b → Groq/8b → OpenRouter → Google AI → Anthropic → Ollama
# Importado por main.py, whatsapp_agent.py e qualquer outro módulo

# ── Desabilita telemetria indesejada (deve ser feito ANTES de qualquer import) ─
import os as _os_telem
_os_telem.environ.setdefault("OTEL_SDK_DISABLED", "true")
_os_telem.environ.setdefault("CREWAI_TELEMETRY_OPT_OUT", "true")
_os_telem.environ.setdefault("CREWAI__TELEMETRY_OPT_OUT", "true")  # alias alternativo
_os_telem.environ.setdefault("ANONYMIZED_TELEMETRY", "false")
_os_telem.environ.setdefault("LITELLM_TELEMETRY", "false")

import asyncio
import os
import pathlib as _pl
from dotenv import load_dotenv

_ENV = _pl.Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV, override=True)

import httpx

GROQ_KEY       = os.getenv("GROQ_API_KEY", "")
ANTHROPIC_KEY  = os.getenv("ANTHROPIC_API_KEY", "")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
GOOGLE_KEY     = os.getenv("GOOGLE_AI_KEY", "")
TOGETHER_KEY   = os.getenv("TOGETHER_API_KEY", "")
OLLAMA_URL     = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL   = os.getenv("OLLAMA_MODEL", "llama3.2")


async def llm(
    system: str,
    messages: list,
    max_tokens: int = 400,
    temperature: float = 0.72,
) -> tuple[str, str]:
    """
    Cascata LLM de 6 camadas. Retorna (texto, provider_label).
    messages = lista de {"role": "user"|"assistant", "content": str}
    """
    full_msgs = [{"role": "system", "content": system}] + messages

    # 1. Groq — 70B → 8B (100k tokens/dia gratuito)
    if GROQ_KEY:
        for model in ("llama-3.3-70b-versatile", "llama-3.1-8b-instant"):
            try:
                from groq import Groq
                gc = Groq(api_key=GROQ_KEY, timeout=12)
                loop = asyncio.get_event_loop()
                resp = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda m=model: gc.chat.completions.create(
                        model=m,
                        messages=full_msgs,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )),
                    timeout=14,
                )
                text = resp.choices[0].message.content.strip()
                if text:
                    return text, f"groq/{model.split('-')[2]}"
            except Exception:
                continue

    # 2. Together AI — gratuito (Llama 3.3 70B)
    if TOGETHER_KEY:
        try:
            from together import Together
            loop = asyncio.get_event_loop()
            tc = Together(api_key=TOGETHER_KEY)
            resp = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: tc.chat.completions.create(
                    model="meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
                    messages=full_msgs,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )),
                timeout=20,
            )
            text = resp.choices[0].message.content.strip()
            if text:
                return text, "together/llama-70b"
        except Exception:
            pass

    # 3. OpenRouter — modelos gratuitos em cascata
    if OPENROUTER_KEY:
        or_models = [
            ("meta-llama/llama-3.3-70b-instruct:free", "openrouter/llama-70b"),
            ("deepseek/deepseek-v4-flash:free",         "openrouter/deepseek"),
            ("moonshotai/kimi-k2.6:free",               "openrouter/kimi"),
        ]
        for model_id, label in or_models:
            try:
                async with httpx.AsyncClient(timeout=25) as hc:
                    r = await hc.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {OPENROUTER_KEY}",
                            "HTTP-Referer": "https://auradecore.com.br",
                            "X-Title": "Aura Decore",
                        },
                        json={"model": model_id, "messages": full_msgs, "max_tokens": max_tokens},
                    )
                    if r.status_code == 200:
                        text = r.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                        if text and len(text) > 5:
                            return text, label
            except Exception:
                continue

    # 4. Google AI Studio — Gemini 2.5 Flash (1500 req/dia gratuito)
    if GOOGLE_KEY:
        try:
            gemini_msgs = [{"role": "user", "parts": [{"text": f"{system}\n\n{messages[-1]['content']}"}]}] if messages else []
            async with httpx.AsyncClient(timeout=25) as hc:
                r = await hc.post(
                    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
                    params={"key": GOOGLE_KEY},
                    json={"contents": gemini_msgs, "generationConfig": {"maxOutputTokens": max_tokens}},
                )
                if r.status_code == 200:
                    parts = r.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
                    text = parts[0].get("text", "").strip() if parts else ""
                    if text and len(text) > 5:
                        return text, "google/gemini-flash"
        except Exception:
            pass

    # 5. Anthropic Claude Sonnet (créditos)
    if ANTHROPIC_KEY:
        try:
            from anthropic import Anthropic
            ac = Anthropic(api_key=ANTHROPIC_KEY)
            loop = asyncio.get_event_loop()
            resp = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: ac.messages.create(
                    model="claude-3-5-sonnet-20240620",
                    max_tokens=max_tokens,
                    system=system,
                    messages=messages,
                )),
                timeout=20,
            )
            text = resp.content[0].text.strip()
            if text:
                return text, "anthropic/sonnet"
        except Exception:
            pass

    # 6. Ollama local — sempre disponível
    try:
        async with httpx.AsyncClient(timeout=30) as hc:
            r = await hc.post(
                f"{OLLAMA_URL}/api/chat",
                json={"model": OLLAMA_MODEL, "messages": full_msgs, "stream": False},
            )
            if r.status_code == 200:
                text = r.json().get("message", {}).get("content", "").strip()
                if text:
                    return text, "ollama/local"
    except Exception:
        pass

    return "Olá! Recebi sua mensagem. Nossa equipe responde em breve. 💚", "fallback"
