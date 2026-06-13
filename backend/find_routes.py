import sys
sys.stdout.reconfigure(encoding='utf-8')

p = r"C:\Users\erick\aura-office-dashboard\backend\main.py"
with open(p, 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f):
        if line.strip().startswith('@app.') or line.strip().startswith('@router.'):
            # Print the line and the next line (def ...)
            print(f"Line {idx+1}: {line.strip()}")
