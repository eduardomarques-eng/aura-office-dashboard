import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

print("Checking environment variables:")
found = False
for k, v in os.environ.items():
    if 'yampi' in k.lower() or 'appmax' in k.lower() or 'pax' in k.lower():
        print(f"  {k} = {v}")
        found = True

if not found:
    print("No matching environment variables found.")
