# -*- coding: utf-8 -*-
"""
run_agents.py — Orquestrador central da frota de agentes Aura Decore
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ponto único para acionar qualquer agente e ver o status da frota.

Uso:
  python run_agents.py status          # status de todos os agentes + credenciais
  python run_agents.py social          # posta no FB/IG (texto)
  python run_agents.py creative        # gera imagem + posta
  python run_agents.py fb-token        # captura/valida token FB
  python run_agents.py google-status   # testa Gemini/Imagen/Veo
  python run_agents.py all             # roda a rotina diária completa
"""
import os, sys, subprocess, pathlib
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = pathlib.Path(__file__).parent
load_dotenv(HERE / ".env", override=True)

# ── Registro da frota de agentes ───────────────────────────────
AGENTS = {
    "social": {
        "file": "social_agent.py",
        "desc": "Postagem diária IG/FB (captions via Gemini)",
        "needs": ["GOOGLE_AI_KEY", "FB_PAGE_TOKEN"],
        "schedule": "09:08 diário",
    },
    "creative": {
        "file": "creative_agent.py",
        "desc": "Pipeline criativo: imagem + caption + publicação",
        "needs": ["GOOGLE_AI_KEY", "FB_PAGE_TOKEN", "(imagem: HIGGSFIELD/TOGETHER/billing)"],
        "schedule": "09:32 diário",
    },
    "fb-token": {
        "file": "get_fb_token.py",
        "desc": "Captura/renova FB_PAGE_TOKEN (OAuth localhost:8765)",
        "needs": ["META_APP_ID"],
        "schedule": "08:09 diário (health check)",
    },
    "google-status": {
        "file": "google_ai.py",
        "args": ["status"],
        "desc": "Diagnóstico Gemini Pro + Imagen 4 + Veo 3",
        "needs": ["GOOGLE_AI_KEY"],
        "schedule": "sob demanda",
    },
    "meta-check": {
        "file": "meta_check.py",
        "desc": "Diagnóstico Meta Pixel + CAPI",
        "needs": ["META_PIXEL_ID", "META_CAPI_TOKEN"],
        "schedule": "sob demanda",
    },
}


def cred_ok(name: str) -> bool:
    if name.startswith("("):
        return False
    return bool(os.getenv(name, "").strip())


def status():
    print("=" * 60)
    print("  FROTA DE AGENTES — Aura Decore")
    print("=" * 60)
    for key, a in AGENTS.items():
        exists = (HERE / a["file"]).exists()
        creds = [(n, cred_ok(n)) for n in a["needs"]]
        ready = exists and all(ok for n, ok in creds if not n.startswith("("))
        icon = "🟢" if ready else "🟡"
        print(f"\n  {icon} {key}  —  {a['desc']}")
        print(f"     arquivo: {a['file']} {'✅' if exists else '❌ AUSENTE'}")
        print(f"     agenda:  {a['schedule']}")
        miss = [n for n, ok in creds if not ok]
        if miss:
            print(f"     falta:   {', '.join(miss)}")
    print("\n" + "=" * 60)
    print("  Credenciais-chave:")
    for c in ["GOOGLE_AI_KEY", "GOOGLE_AI_KEY_2", "FB_PAGE_TOKEN",
              "META_ACCESS_TOKEN", "SHOPIFY_ADMIN_API_TOKEN", "HIGGSFIELD_API_KEY"]:
        print(f"    {'✅' if cred_ok(c) else '❌'} {c}")
    print("=" * 60)


def run(agent_key: str):
    a = AGENTS.get(agent_key)
    if not a:
        print(f"Agente desconhecido: {agent_key}")
        print(f"Disponíveis: {', '.join(AGENTS)}")
        return
    cmd = [sys.executable, str(HERE / a["file"])] + a.get("args", [])
    print(f"▶ Executando {agent_key}: {a['desc']}\n")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    subprocess.run(cmd, env=env, cwd=str(HERE))


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "status"
    if arg == "status":
        status()
    elif arg == "all":
        for k in ["fb-token", "creative", "social"]:
            run(k)
    else:
        run(arg)
