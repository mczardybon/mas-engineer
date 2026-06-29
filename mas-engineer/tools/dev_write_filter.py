#!/usr/bin/env python3
"""
dev_write_filter.py — Write filter (content check before writing)
Will VOM GATEKEEPER aufgerufen.
Checks: Target-Path, YAML-Syntax, Encoding, Duplikate.

Aufruf: python3 dev_write_filter.py --file path --content "inhalt"
        python3 dev_write_filter.py --file path --stdin
        python3 dev_write_filter.py --file path --content "..." --skip-yaml
"""

import sys, os, json, re

MAS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def check_target(file):
    abs_f = os.path.abspath(file)
    if not abs_f.startswith(os.path.abspath(MAS_DIR)):
        return (False, f"Target {file} outside MAS")
    for v in [".git/", "checkpoints/", "audit.log.jsonl", ".disziplin_lock",
              ".last_confirmation", "action.log"]:
        if v in abs_f: return (False, f"Protected: {v}")
    return (True, "")

def check_yaml(content):
    if not content.strip(): return (True, "")
    try:
        import yaml; yaml.safe_load(content); return (True, "")
    except Exception as e:
        return (False, f"YAML-Error: {e}")

def check_encoding(content):
    try:
        if isinstance(content, str): content.encode('utf-8')
        else: content.decode('utf-8')
        return (True, "")
    except UnicodeError:
        return (False, "No valides UTF-8")

def check_duplicates(file, content):
    if not file.endswith(('.yaml','.yml')): return (True, "")
    try:
        import yaml; data = yaml.safe_load(content)
        if isinstance(data, list):
            gesehen = []
            for item in data:
                if isinstance(item, dict):
                    k = json.dumps(item, sort_keys=True)
                    if k in gesehen:
                        n = item.get('name', item.get('id', '?'))
                        return (False, f"Duplikat: {n}")
                    gesehen.append(k)
        return (True, "")
    except: return (True, "")

def main():
    if len(sys.argv) < 3:
        print("❌ Aufruf: dev_write_filter.py --file path --content '...'"); sys.exit(1)
    if "--file" not in sys.argv:
        print("❌ --file required"); sys.exit(1)
    file = sys.argv[sys.argv.index("--file") + 1]
    if "--content" in sys.argv:
        idx = sys.argv.index("--content"); content = sys.argv[idx + 1]
        for j in range(idx+2, len(sys.argv)):
            if not sys.argv[j].startswith("--"): content += " " + sys.argv[j]
            else: break
    elif "--stdin" in sys.argv:
        content = sys.stdin.read()
    else:
        print("❌ --content oder --stdin"); sys.exit(1)

    skip_yaml = "--skip-yaml" in sys.argv
    checks = [("Target-Path", check_target(file)),
              ("Encoding", check_encoding(content)),
              ("YAML", check_yaml(content)) if file.endswith(('.yaml','.yml')) and not skip_yaml else ("YAML", (True,"")),
              ("Duplikate", check_duplicates(file, content))]
    error = [f"{n}: {m}" for n,(o,m) in checks if not o]
    if error:
        print(f"❌ WRITE-FILTER: {len(error)} Error")
        for f in error: print(f"  {f}")
        sys.exit(1)
    print(f"✅ Write-Filter: OK for {file}")
    sys.exit(0)

if __name__ == "__main__":
    main()
