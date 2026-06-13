import os
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

wf_dir = r"C:\Users\erick\aura-office-dashboard\n8n-workflows"
matches = []

if os.path.exists(wf_dir):
    for root, dirs, files in os.walk(wf_dir):
        for f in files:
            if f.endswith('.json'):
                path = os.path.join(root, f)
                try:
                    with open(path, 'r', encoding='utf-8') as fh:
                        data = json.load(fh)
                        # Search inside json recursively
                        data_str = json.dumps(data).lower()
                        if 'yampi' in data_str or 'appmax' in data_str or 'pax' in data_str:
                            matches.append((path, data))
                except Exception as e:
                    pass

    print(f"Found {len(matches)} JSON workflow files containing Yampi/Appmax:")
    for path, data in matches:
        print(f"\n- {os.path.relpath(path, wf_dir)}")
        # Let's inspect nodes in data
        nodes = data.get("nodes", []) if isinstance(data, dict) else (data[0].get("nodes", []) if isinstance(data, list) and data else [])
        for n in nodes:
            n_str = json.dumps(n).lower()
            if 'yampi' in n_str or 'appmax' in n_str or 'pax' in n_str:
                print(f"  Node: {n.get('name')} ({n.get('type')})")
                params = n.get('parameters', {})
                print(f"    Params: {params}")
else:
    print("Workflow directory does not exist.")
