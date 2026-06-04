#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
railway_fix.py — Diagnostica e reconfigura URL do Railway
Execute: python railway_fix.py
"""
import os, sys, subprocess, pathlib
from dotenv import load_dotenv

load_dotenv(pathlib.Path(__file__).parent / ".env")

print("=" * 55)
print("  RAILWAY DIAGNÓSTICO — Aura Decore")
print("=" * 55)

current_url = os.getenv("RAILWAY_URL", "")
print(f"\n  URL atual no .env: {current_url}")

# Tenta detectar URL via Railway CLI
print("\n  Tentando Railway CLI...")
try:
    result = subprocess.run(["railway", "status"], capture_output=True, text=True, timeout=15)
    if result.returncode == 0:
        print(f"  ✅ CLI output:\n{result.stdout}")
    else:
        print(f"  ⚠️  Railway CLI: {result.stderr[:200]}")
except FileNotFoundError:
    print("  ❌ Railway CLI não instalado")
    print("     Instale: npm install -g @railway/cli")
    print("     Login:   railway login")
    print("     Status:  railway status")

print("\n  📋 PASSOS MANUAIS:")
print("  1. Acesse: https://railway.app/dashboard")
print("  2. Abra o projeto 'aura-office-dashboard'")
print("  3. Clique no serviço > Settings > Domains")
print("  4. Copie a URL atual")
print("  5. Atualize RAILWAY_URL no .env")
print("  6. Execute: python meta_full_deploy.py")
print()
print("  OU redeploy via git:")
print("  git commit --allow-empty -m 'trigger: Railway redeploy'")
print("  git push")
print("=" * 55)
