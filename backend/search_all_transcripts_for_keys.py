import os
import glob
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

brain_dir = r"C:\Users\erick\.gemini\antigravity-ide\brain"
pattern = os.path.join(brain_dir, "*", ".system_generated", "logs", "transcript.jsonl")
files = glob.glob(pattern)

print(f"Found {len(files)} files. Scanning for Yampi/Appmax tokens/keys...")

matches = []
for f in files:
    parts = f.split(os.sep)
    conv_id = parts[-4]
    try:
        with open(f, 'r', encoding='utf-8', errors='ignore') as fh:
            for line in fh:
                line_lower = line.lower()
                if any(x in line_lower for x in ['yampi', 'appmax', 'pax']):
                    # Check if there is something resembling a token or key
                    # (like a string of letters and numbers or specific variables)
                    if any(v in line_lower for v in ['token', 'key', 'secret', 'alias', 'shpat_', 'atkn_', 'yampi_']):
                        try:
                            obj = json.loads(line)
                            content = obj.get('content', '')
                            thinking = obj.get('thinking', '')
                            source = obj.get('source', '')
                            stype = obj.get('type', '')
                            
                            text_to_check = (content or '') + '\n' + (thinking or '')
                            for l in text_to_check.split('\n'):
                                l_lower = l.lower()
                                if any(x in l_lower for x in ['yampi', 'appmax', 'pax']) and any(v in l_lower for v in ['token', 'key', 'secret', 'alias', 'shpat_', 'atkn_']):
                                    matches.append((conv_id, source, stype, l.strip()))
                        except:
                            pass
    except Exception as e:
        pass

print(f"Found {len(matches)} matching lines in transcripts:")
for conv_id, source, stype, line in matches:
    print(f"\n- Conv: {conv_id} ({source} | {stype})")
    print(f"  Line: {line[:300]}")
