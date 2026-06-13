import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

vault_dir = r"C:\Users\erick\AURA-decor-vault"
matches = []

if os.path.exists(vault_dir):
    for root, dirs, files in os.walk(vault_dir):
        for f in files:
            if f.endswith('.md') or f.endswith('.txt') or f.endswith('.json'):
                path = os.path.join(root, f)
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
                        lines = fh.readlines()
                        for idx, line in enumerate(lines):
                            line_lower = line.lower()
                            if 'yampi' in line_lower or 'appmax' in line_lower:
                                # Extract context
                                start = max(0, idx - 2)
                                end = min(len(lines), idx + 3)
                                context = "".join(lines[start:end])
                                matches.append((path, idx+1, line.strip(), context))
                except Exception as e:
                    pass

    print(f"Total matching lines: {len(matches)}")
    for path, line_num, line_text, context in matches:
        # print relative path
        rel_path = os.path.relpath(path, vault_dir)
        print(f"\n======================================")
        print(f"File: {rel_path} | Line: {line_num}")
        print(f"======================================")
        print(context.strip())
        print("-" * 50)
else:
    print("Vault does not exist")
