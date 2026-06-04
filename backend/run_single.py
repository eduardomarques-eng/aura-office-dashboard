import urllib.request, json, sys, time

def run_crew(cfg):
    slug = cfg["crew_type"]
    sys.stdout.write(f"[RUNNER] Disparando: {slug}\n"); sys.stdout.flush()
    req = urllib.request.Request(
        "http://localhost:8000/crew/run",
        data=json.dumps(cfg).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    resp = urllib.request.urlopen(req, timeout=600)
    result = json.loads(resp.read().decode())
    sys.stdout.write(f"[RUNNER] {slug} status={result.get('status')}\n"); sys.stdout.flush()
    if result.get("result"):
        sys.stdout.write(f"[RUNNER] RESULTADO:\n{result['result'][:800]}\n"); sys.stdout.flush()
    elif result.get("detail"):
        sys.stdout.write(f"[RUNNER] DETALHE: {result['detail'][:300]}\n"); sys.stdout.flush()
    return result.get("status") == "done"

# Roda 1 crew por vez, 60s entre cada
crews = [
    {"crew_type": "design", "product": "vaso ceramica japandi wabi-sabi flores secas"},
]

for c in crews:
    try:
        ok = run_crew(c)
    except Exception as e:
        sys.stdout.write(f"[RUNNER] ERRO: {e}\n"); sys.stdout.flush()
    sys.stdout.write("[RUNNER] Aguardando 60s...\n"); sys.stdout.flush()
    time.sleep(60)

sys.stdout.write("[RUNNER] Pipeline completo.\n"); sys.stdout.flush()
