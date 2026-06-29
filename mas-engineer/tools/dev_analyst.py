#!/usr/bin/env python3
"""
dev_analyst.py — 🔍 The quality checker des dev-mas-engineer
============================================================
Version: 1.0.0
Author: dev-mas-engineer (autonomous)

Checks die Quality des Frameworks:
  - YAML-Syntax allr files
  - File sizes und Anomalies
  - settings-Completeness
  - slash_command-Konflikte
  - UTF-8 Kodierung

KEINE Framework-Dependency. Reine Standardbibliothek.

VERWENDUNG:
    python3 dev_analyst.py --check-all         # All Checks perform
    python3 dev_analyst.py --yaml-syntax       # Only YAML-Syntax check
    python3 dev_analyst.py --sizes             # Only File sizes check
    python3 dev_analyst.py --settings          # Only settings check
    python3 dev_analyst.py --slashes           # Only slash_command check
"""

import sys, subprocess, json
from pathlib import Path
from datetime import datetime

OBSERVER_DIR = Path(__file__).parent / "dev_observer.py"
sys.path.insert(0, str(Path(__file__).parent))

import importlib.util
spec = importlib.util.spec_from_file_location("dev_observer", OBSERVER_DIR)
observer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(observer)


# ─────────────────────────────────────────────────────────
# CHECKS
# ─────────────────────────────────────────────────────────

def check_yaml_syntax(scanner: "observer.Scanner") -> str:
    """Checks ALL YAML-files auf Syntax-Error."""
    scanner._collect()
    
    python = sys.executable
    ok = 0
    fail = 0
    errors = []
    
    for info in scanner.files:
        if not info.is_yaml:
            continue
        
        cmd = [python, "-c", 
               f"import yaml; yaml.safe_load(open('{info.path}'))"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            ok += 1
        else:
            fail += 1
            errors.append(f"    ❌ {info.rel_path}: {result.stderr.strip()[:80]}")
    
    out = []
    out.append("🔍 [Q1] YAML-SYNTAX")
    out.append("━" * 40)
    out.append(f"  ✅ OK:     {ok}")
    out.append(f"  ❌ Error: {fail}")
    out.append("")
    
    if errors:
        out.append("  Errorhafte files:")
        out.extend(errors)
    else:
        out.append("  ✅ All YAML-files syntaktisch korrekt.")
    
    return "\n".join(out)


def check_sizes(scanner: "observer.Scanner") -> str:
    """Checks File sizes auf Anomalies."""
    scanner._collect()
    
    MAX_LINES = 800
    MIN_LINES = 10
    
    too_big = []
    too_small = []
    for info in scanner.files:
        if info.is_yaml and info.lines > MAX_LINES:
            too_big.append(info)
        if info.is_yaml and info.lines < MIN_LINES:
            too_small.append(info)
    
    # Sort after size
    all_sorted = sorted([f for f in scanner.files if f.is_yaml], key=lambda x: x.lines, reverse=True)
    
    out = []
    out.append("🔍 [Q2] FILE SIZES")
    out.append("━" * 40)
    
    if too_big:
        out.append(f"  ⚠️  Large (> {MAX_LINES} Zeilen):")
        for f in too_big:
            out.append(f"      {f.rel_path} ({f.lines} Zeilen)")
    else:
        out.append(f"  ✅ No file > {MAX_LINES} Zeilen")
    
    out.append("")
    
    if too_small:
        out.append(f"  ⚠️  Kla (< {MIN_LINES} Zeilen):")
        for f in too_small:
            out.append(f"      {f.rel_path} ({f.lines} Zeilen)")
    
    out.append("")
    
    # Top 5 largest
    out.append("  📊 Top 5 largest YAMLs:")
    for f in all_sorted[:5]:
        out.append(f"      {f.rel_path} ({f.lines} Zeilen)")
    
    out.append("")
    out.append("  📊 Top 5 kleinste YAMLs:")
    for f in all_sorted[-5:]:
        out.append(f"      {f.rel_path} ({f.lines} Zeilen)")
    
    return "\n".join(out)


def check_settings(scanner: "observer.Scanner") -> str:
    """Checks ob all YAMLs settings have."""
    scanner._collect()
    
    total = len(scanner.yamls)
    with_settings = sum(1 for y in scanner.yamls if y.has_settings)
    without = [y for y in scanner.yamls if not y.has_settings]
    
    out = []
    out.append("🔍 [Q3] SETTINGS COMPLETENESS")
    out.append("━" * 40)
    out.append(f"  Mit settings:  {with_settings}/{total}")
    out.append(f"  Ohne settings: {len(without)}/{total}")
    out.append("")
    
    if without:
        out.append("  ⚠️  YAMLs ohne settings-Block:")
        for y in without:
            out.append(f"      {y.rel_path}")
    else:
        out.append("  ✅ All YAMLs have settings.")
    
    return "\n".join(out)


def check_slashes(scanner: "observer.Scanner") -> str:
    """Checks slash_command auf Konflikte."""
    scanner._collect()
    
    cmds = {}
    for y in scanner.yamls:
        if y.has_slash:
            if y.slash_cmd not in cmds:
                cmds[y.slash_cmd] = []
            cmds[y.slash_cmd].append(y.rel_path)
    
    conflicts = {cmd: paths for cmd, paths in cmds.items() if len(paths) > 1}
    unique = {cmd: paths for cmd, paths in cmds.items() if len(paths) == 1}
    
    out = []
    out.append("🔍 [Q4] SLASH-COMMAND-KONFLIKTE")
    out.append("━" * 40)
    
    if conflicts:
        out.append(f"  ❌ KONFLIKTE ({len(conflicts)}):")
        for cmd, paths in conflicts.items():
            out.append(f"      /{cmd}  →  {', '.join(paths)}")
    else:
        out.append("  ✅ No Konflikte.")
    
    out.append("")
    out.append(f"  Eindeutige Commands ({len(unique)}):")
    for cmd in sorted(unique.keys()):
        out.append(f"      /{cmd}")
    
    return "\n".join(out)


def check_utf8(scanner: "observer.Scanner") -> str:
    """Checks UTF-8 Kodierung allr files."""
    scanner._collect()
    
    ok = 0
    fail = 0
    errors = []
    
    for info in scanner.files:
        try:
            with open(info.path, "r", encoding="utf-8") as f:
                f.read()
            ok += 1
        except UnicodeDecodeError:
            fail += 1
            errors.append(f"    ❌ {info.rel_path}: Nicht UTF-8")
        except Exception as e:
            fail += 1
            errors.append(f"    ❌ {info.rel_path}: {e}")
    
    out = []
    out.append("🔍 [Q5] UTF-8 KODIERUNG")
    out.append("━" * 40)
    out.append(f"  ✅ UTF-8: {ok}")
    out.append(f"  ❌ Error: {fail}")
    out.append("")
    
    if errors:
        out.extend(errors)
    else:
        out.append("  ✅ All files UTF-8 kodiert.")
    
    return "\n".join(out)


def check_titles(scanner: "observer.Scanner") -> str:
    """Checks ob all YAMLs a Titel have."""
    scanner._collect()
    
    with_title = sum(1 for y in scanner.yamls if y.title)
    without = [y for y in scanner.yamls if not y.title]
    
    out = []
    out.append("🔍 [Q6] TITEL")
    out.append("━" * 40)
    out.append(f"  Mit Titel:  {with_title}/{len(scanner.yamls)}")
    out.append("")
    
    if without:
        out.append(f"  ⚠️  Ohne Titel ({len(without)}):")
        for y in without:
            out.append(f"      {y.rel_path}")
    else:
        out.append("  ✅ All YAMLs have a Titel.")
    
    return "\n".join(out)


def check_all(scanner: "observer.Scanner") -> str:
    """All Checks nacheinander."""
    parts = []
    parts.append("#" * 60)
    parts.append(f"🔍 QUALITYS-ANALYSE")
    parts.append(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    parts.append("#" * 60)
    parts.append("")
    
    parts.append(check_yaml_syntax(scanner))
    parts.append("")
    parts.append(check_sizes(scanner))
    parts.append("")
    parts.append(check_settings(scanner))
    parts.append("")
    parts.append(check_slashes(scanner))
    parts.append("")
    parts.append(check_utf8(scanner))
    parts.append("")
    parts.append(check_titles(scanner))
    parts.append("")
    
    # Fazit
    out_text = "\n".join(parts)
    
    # Schnell-Check ob alls OK
    has_errors = "❌" in out_text or "⚠️" in out_text
    
    parts.append("📋 FAZIT")
    parts.append("━" * 40)
    if has_errors:
        parts.append("  ⚠️  Es givet Anomalies (siehe oben).")
    else:
        parts.append("  ✅ Framework-Quality: No offensichtlichen Probleme.")
    
    return "\n".join(parts)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="dev_analyst.py — Quality check")
    parser.add_argument("--check-all", action="store_true", help="All Checks")
    parser.add_argument("--yaml-syntax", action="store_true")
    parser.add_argument("--sizes", action="store_true")
    parser.add_argument("--settings", action="store_true")
    parser.add_argument("--slashes", action="store_true")
    
    args = parser.parse_known_args()[0]
    
    scanner = observer.Scanner(observer.AGENT_DIR)
    
    if args.yaml_syntax:
        print(check_yaml_syntax(scanner))
    elif args.sizes:
        print(check_sizes(scanner))
    elif args.settings:
        print(check_settings(scanner))
    elif args.slashes:
        print(check_slashes(scanner))
    else:
        print(check_all(scanner))


if __name__ == "__main__":
    main()
