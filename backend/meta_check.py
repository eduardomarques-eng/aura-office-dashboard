# -*- coding: utf-8 -*-
"""
meta_check.py — Diagnóstico rápido da integração Meta para Aura Decore
Execute: python meta_check.py
"""
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from meta_integration import MetaInsights, MetaCAPI, PIXEL_ID, CAPI_TOKEN

# Relatório de status
insights = MetaInsights()
report = insights.print_report()

# Teste rápido de evento se credenciais OK
if PIXEL_ID and CAPI_TOKEN:
    print("\n[TESTE] Enviando evento PageView de teste...")
    capi = MetaCAPI()
    result = capi.page_view(
        url="https://auradecore.com.br",
        ip="177.0.0.1",
        ua="Mozilla/5.0 (Test)"
    )
    if "events_received" in result:
        print(f"  ✅ CAPI OK — {result['events_received']} evento(s) recebido(s)")
    elif "error" in result:
        print(f"  ❌ CAPI ERRO — {result['error']}")
    else:
        print(f"  ⚠️  Resposta: {result}")
else:
    print("\n⚠️  Configure META_PIXEL_ID e META_CAPI_TOKEN no .env para testar eventos.")
    print("   Guia completo: AURA-decor-vault/Meta Business/META-FULL-SETUP.md")
