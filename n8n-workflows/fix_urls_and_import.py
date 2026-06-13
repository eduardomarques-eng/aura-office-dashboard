# -*- coding: utf-8 -*-
"""
fix_urls_and_import.py — Corrige URLs hardcoded nos workflows n8n
e gera versoes prontas para importação no n8n Cloud.

Substitui http://localhost:8000 pela RAILWAY_URL real.
Os workflows que usam $env.RAILWAY_URL ficam intactos (n8n resolve).
"""
import json, pathlib, sys

RAILWAY_URL = "https://web-production-f1cb5.up.railway.app"
HERE = pathlib.Path(__file__).parent
OUTPUT = HERE / "ready-to-import"
OUTPUT.mkdir(exist_ok=True)

workflows = sorted(HERE.glob("*.json"))
fixed = 0

for wf_path in workflows:
    if wf_path.name == "fix_urls_and_import.py":
        continue
    text = wf_path.read_text(encoding="utf-8")
    original = text
    
    # Substitui localhost:8000 hardcoded pela URL do Railway
    text = text.replace("http://localhost:8000", RAILWAY_URL)
    
    # Garante que $env.RAILWAY_URL tenha fallback correto
    text = text.replace(
        "'http://localhost:8000'",
        f"'{RAILWAY_URL}'"
    )
    
    if text != original:
        fixed += 1
        print(f"  [FIX] {wf_path.name} — URLs corrigidas")
    else:
        print(f"  [OK]  {wf_path.name} — sem alteração necessária")
    
    # Salva versão corrigida no diretório de saída
    out_path = OUTPUT / wf_path.name
    out_path.write_text(text, encoding="utf-8")

print(f"\n✅ {fixed} workflows corrigidos")
print(f"📂 Workflows prontos em: {OUTPUT}")
print(f"\n{'='*60}")
print("PRÓXIMO PASSO: Importar no n8n Cloud")
print("="*60)
print(f"""
1. Acesse: https://aura-refugio.app.n8n.cloud
2. Vá em: Settings > Environment Variables
3. Adicione: RAILWAY_URL = {RAILWAY_URL}
4. Para cada workflow em {OUTPUT.name}/:
   - Clique no menu ☰ > Import from File
   - Selecione o arquivo .json
   - Ative o workflow (toggle ON)

Ordem de importação:
  01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10 → 11 → 12
""")
