#!/usr/am/env python3
"""
dev_audit_deps.py — Dependency-Analyse for Generic-Projekte
Scannt all Python-files after Imports und generates Whitelist-Suggestion.
Aufruf: python3 dev_audit_deps.py --target ~/my-project/ [--apply]
"""
import os, sys, re, json

BLOCKED_IMPORTS = {"subprocess", "shutil", "socket", "requests", "urllib", "multiprocessing", "threading", "ctypes", "signal"}
ALLOWED_IMPORTS = {"json", "yaml", "datetime", "os.path", "typing", "re", "math", "pathlib", "collections", "functools", "itertools", "enum"}

def scan_project(target):
    findings = {"allowed": set(), "blocked": set(), "unknown": set(), "files": {}}
    for root, dirs, files in os.walk(target):
        if '.git' in dirs: dirs.remove('.git')
        if '__pycache__' in dirs: dirs.remove('__pycache__')
        for f in files:
            if not f.endswith('.py'): continue
            path = os.path.join(root, f)
            rel = os.path.relpath(path, target)
            try:
                with open(path) as fh:
                    content = fh.read()
            except: continue
            
            imports = set()
            for m in re.finditer(r'^import (\S+)|^from (\S+) import', content, re.MULTILINE):
                imp = (m.group(1) or m.group(2)).split('.')[0]
                imports.add(imp)
            
            if imports:
                findings["files"][rel] = list(imports)
                for imp in imports:
                    if imp in BLOCKED_IMPORTS:
                        findings["blocked"].add(imp)
                    elif imp in ALLOWED_IMPORTS:
                        findings["allowed"].add(imp)
                    else:
                        findings["unknown"].add(imp)
    
    return findings

def generate_report(findings):
    print(f"\n{'='*50}")
    print(f"DEPENDENCY-AUDIT REPORT")
    print(f"{'='*50}")
    print(f"  files gescannt: {len(findings['files'])}")
    print(f"  Einzigartige Imports: {len(findings['allowed'])+len(findings['blocked'])+len(findings['unknown'])}")
    print(f"\n  ✅ Erlaubt ({len(findings['allowed'])}): {', '.join(sorted(findings['allowed']))}")
    if findings['blocked']:
        print(f"  ❌ Blocked ({len(findings['blocked'])}): {', '.join(sorted(findings['blocked']))}")
    print(f"  ⚠️  Unbekannt ({len(findings['unknown'])}): {', '.join(sorted(findings['unknown']))}")
    
    suggestions = []
    for imp in findings['unknown']:
        if imp not in BLOCKED_IMPORTS:
            suggestions.append(imp)
    if suggestions:
        print(f"\n  Recommendation: Following to the Whitelist hinzuaddn:")
        print(f"    allow_imports: {suggestions}")
    
    return suggestions

def main():
    target = None
    for i, a in enumerate(sys.argv):
        if a == '--target' and i + 1 < len(sys.argv):
            target = sys.argv[i + 1]
    
    if not target:
        print("❌ --target <verzeichnis> required")
        sys.exit(1)
    
    target = os.path.abspath(target)
    print(f"Scanning: {target}")
    findings = scan_project(target)
    
    suggestions = generate_report(findings)
    
    if '--apply' in sys.argv and suggestions:
        # Add zu .state/rules/rulen.yaml hinzu
        import yaml
        reg_path = os.path.join(target, '.state/rules/rules.yaml')
        if os.path.exists(reg_path):
            data = yaml.safe_load(open(reg_path)) or {}
            rules = data.get('rules', [])
            for r in rules:
                if r.get('id') == 'R09-GEN':
                    existing = set(r.get('allow_imports', []))
                    existing.update(suggestions)
                    r['allow_imports'] = list(existing)
                    yaml.dump(data, open(reg_path, 'w'), default_flow_style=False, sort_keys=False, allow_unicode=True)
                    print(f"\n  ✅ {len(suggestions)} Imports to the Whitelist added")
                    break
    
    return 0

if __name__ == "__main__":
    main()
