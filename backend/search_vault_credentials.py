import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

vault_dir = r"C:\Users\erick\AURA-decor-vault"
matches = []

print(f"Searching vault: {vault_dir}")
if os.path.exists(vault_dir):
    for root, dirs, files in os.walk(vault_dir):
        for f in files:
            if f.endswith('.md') or f.endswith('.txt') or f.endswith('.json'):
                path = os.path.join(root, f)
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
                        content = fh.read()
                        if 'yampi' in content.lower() or 'appmax' in content.lower():
                            matches.append((path, content))
                except Exception as e:
                    pass
    
    print(f"Found {len(matches)} files in vault referencing Yampi or Appmax:")
    for path, content in matches:
        print(f"\n======================================")
        print(f"File: {path}")
        print(f"======================================")
        # Print lines that might contain keys/tokens
        for line in content.split('\n'):
            line_lower = line.lower()
            if any(k in line_lower for k in ['token', 'key', 'secret', 'alias', 'senha', 'api', 'credencial', 'passwd', 'password']):
                print(f"  {line.strip()}")
else:
    print("Vault directory does not exist.")
