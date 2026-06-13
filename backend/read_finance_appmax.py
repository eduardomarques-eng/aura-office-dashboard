import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

p = r"C:\Users\erick\AURA-decor-vault\Financeiro\appmax-2026-06-13.md"
if os.path.exists(p):
    with open(p, 'r', encoding='utf-8') as f:
        print(f.read())
else:
    print("File does not exist")
