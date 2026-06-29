#!/usr/bin/env python3
"""
dev_editor_large.py — Zeilen-basiertes Edit for files >1000 Zeilen
Replaces YAML-Blocks zwischen zwei Zeilen-Nummern.
No yaml-Parse — only Text-Operation. Validierung via yaml.safe_load() danach.

Usage:
  python3 dev_editor_large.py edit <file> <start_line> <end_line> <replacement_text>
  python3 dev_editor_large.py find <file> <regex_pattern>
  python3 dev_editor_large.py insert <file> <after_line> <text>
"""

import sys, os, re, json

def edit_between_lines(filepath, start, end, text):
    """Erset Zeile start..end (1-based, inclusive) mit text."""
    if not os.path.exists(filepath):
        return {"error": f"file not found: {filepath}"}
    with open(filepath, 'r') as f:
        lines = f.readlines()
    n = len(lines)
    if start < 1 or end > n:
        return {"error": f"Zeilen {start}-{end} outside (1-{n})"}
    before = lines[:start-1]
    after = lines[end:]
    new_lines = before + [text.rstrip('\n') + '\n'] + after
    with open(filepath, 'w') as f:
        f.writelines(new_lines)
    return {"ok": True, "alte_zeilen": end-start+1, "neue_zeilen": 1}

def find_line(filepath, pattern):
    """Finde erste Zeile die regex pattern matched. Return Zeilen-Nr (1-based) oder null."""
    with open(filepath, 'r') as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if re.search(pattern, line):
            return i + 1
    return None

def insert_after(filepath, after_line, text):
    """Add text NACH Zeile after_line ein."""
    with open(filepath, 'r') as f:
        lines = f.readlines()
    if after_line < 1 or after_line > len(lines):
        return {"error": f"Zeile {after_line} outside (1-{len(lines)})"}
    lines.insert(after_line, text.rstrip('\n') + '\n')
    with open(filepath, 'w') as f:
        f.writelines(lines)
    return {"ok": True, "zeilen_insgesamt": len(lines)}

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'edit' and len(sys.argv) == 6:
        result = edit_between_lines(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5])
        print(json.dumps(result))
    elif cmd == 'find' and len(sys.argv) == 4:
        result = find_line(sys.argv[2], sys.argv[3])
        print(json.dumps({"line": result}))
    elif cmd == 'insert' and len(sys.argv) == 5:
        result = insert_after(sys.argv[2], int(sys.argv[3]), sys.argv[4])
        print(json.dumps(result))
    else:
        print(__doc__)
        sys.exit(1)
