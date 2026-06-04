import urllib.request, json, time, sys

crews = [
    {"crew_type": "mining",      "context": "vaso japandi ceramica wabi-sabi flores secas decoracao minimalista"},
    {"crew_type": "social_post", "product": "vaso ceramica japandi flores secas ambiente minimalista"},
    {"crew_type": "design",      "product": "bandeja madeira japandi organizar mesa de jantar"},
]

for crew_cfg in crews:
    slug = crew_cfg["crew_type"]
    sys.stdout.write(f"[RUNNER] Disparando crew: {slug}\n"); sys.stdout.flush()
    try:
        req = urllib.request.Request(
            "http://localhost:8000/crew/run",
            data=json.dumps(crew_cfg).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        resp = urllib.request.urlopen(req, timeout=600)
        result = json.loads(resp.read().decode())
        sys.stdout.write(f"[RUNNER] {slug} status={result.get('status')}\n"); sys.stdout.flush()
        sys.stdout.write(f"[RUNNER] resultado: {str(result.get('result',''))[:500]}\n"); sys.stdout.flush()
    except Exception as e:
        sys.stdout.write(f"[RUNNER] {slug} ERRO: {e}\n"); sys.stdout.flush()
    sys.stdout.write(f"[RUNNER] Aguardando 30s...\n"); sys.stdout.flush()
    time.sleep(30)

sys.stdout.write("[RUNNER] Pipeline completo.\n"); sys.stdout.flush()
