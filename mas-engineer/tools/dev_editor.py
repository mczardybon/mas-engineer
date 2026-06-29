#!/usr/bin/env python3
"""
dev_editor.py — ✏️ Die Hand des dev-mas-engineer
=================================================
Version: 1.0.0
Author: dev-mas-engineer (autonomous)

Changes YAML-files im agent/ Framework.
Sicher: Backup VOR jeder Change, Validierung NACH jeder Change,
Automatischer Rollback bei Error.

VERWENDUNG:
    python3 dev_editor.py --patch <file> --von "<old>" --nach "<new>" --grund "<grund>"
    python3 dev_editor.py --validate <file>
    python3 dev_editor.py --backup <file>
    python3 dev_editor.py --rollback <backup-dir> <file>

BEISPIELE:
    python3 dev_editor.py --patch "<workspace>/recipes/planner.yaml" \\
        --von "max_steps: 300" --nach "max_steps: 150" \\
        --grund "User-Request"

    python3 dev_editor.py --validate "<workspace>/recipes/planner.yaml"

KEINE Framework-Dependency. Reine Standardbibliothek + subprocess.
"""

import sys, os, subprocess, shutil, json, yaml, re
from pathlib import Path
from datetime import datetime

AGENT_DIR = None
# --workspace <dir> has Vorrang
for i, arg in enumerate(sys.argv):
    if arg == "--workspace" and i + 1 < len(sys.argv):
        AGENT_DIR = Path(sys.argv[i + 1]).resolve()
        break
# Fallback: relativer Path from Tool aus
if not AGENT_DIR:
    default = Path(__file__).parent.parent.parent.resolve()
    if (default / "recipes").exists() or any((d / "recipes").exists() for d in default.iterdir() if d.is_dir()):
        AGENT_DIR = default
    else:
        AGENT_DIR = Path.home() / ".config" / "goose" / "recipes"

BACKUP_DIR = Path(__file__).parent.parent / ".backups"
CHANGES_SCRIPT = Path(__file__).parent / "dev_changes.py"


def log(msg):
    print(msg)


def error(msg):
    print(f"❌ {msg}")


def ok(msg):
    print(f"✅ {msg}")


def warn(msg):
    print(f"⚠️  {msg}")


def ensure_dir(path: Path):
    """Stelle sicher dass a Directory exists."""
    path.mkdir(parents=True, exist_ok=True)


def validate_yaml(path: Path) -> tuple[bool, str]:
    """Check ob eine file valid YAML ist."""
    python = sys.executable
    cmd = [python, "-c", f"import yaml; yaml.safe_load(open('{path}'))"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return True, "YAML-Syntax OK"
    return False, result.stderr.strip()[:120]


def create_backup(rel_path: str) -> Path | None:
    """Erstelle a Backup der file mit Zeitstempel."""
    source = AGENT_DIR / rel_path
    if not source.exists():
        error(f"file not found: {source}")
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_subdir = BACKUP_DIR / timestamp
    ensure_dir(backup_subdir)
    
    target = backup_subdir / source.name
    shutil.copy2(source, target)
    
    if target.exists():
        ok(f"Backup creates: {target}")
        return backup_subdir
    else:
        error("Backup failed")
        return None


def restore_backup(backup_dir: Path, rel_path: str) -> bool:
    """Stelle eine file from dem Backup again her."""
    source = backup_dir / Path(rel_path).name
    target = AGENT_DIR / rel_path
    
    if not source.exists():
        error(f"Backup not found: {source}")
        return False
    
    shutil.copy2(source, target)
    
    if target.exists():
        ok(f"Rollback performed: {target}")
        return True
    else:
        error("Rollback failed")
        return False


def do_patch(rel_path: str, von: str, nach: str, grund: str,
             user: str = "Marius", risk: str = "niedrig") -> dict:
    """
    Run eine Change durch.
    
    Returns:
        dict mit: status, file, von, nach, backup, meldungen, error
    """
    result = {
        "status": "pending",
        "file": rel_path,
        "von": von,
        "nach": nach,
        "grund": grund,
        "backup": "",
        "meldungen": [],
        "error": []
    }
    
    full_path = AGENT_DIR / rel_path
    
    # ─── SCHRITT 1: VALIDATE (BEFORE) ───
    print(f"\n🔍 Check: {rel_path}")
    
    if not full_path.exists():
        result["status"] = "failed"
        result["error"].append(f"file not found: {full_path}")
        return result
    
    yaml_ok, yaml_msg = validate_yaml(full_path)
    if not yaml_ok:
        result["status"] = "failed"
        result["error"].append(f"YAML invalid: {yaml_msg}")
        return result
    ok(f"YAML valid: {full_path.name}")
    
    # Check ob old Value exists
    grep = subprocess.run(
        ["grep", "-c", von, str(full_path)],
        capture_output=True, text=True
    )
    count = int(grep.stdout.strip() or 0)
    if count == 0:
        result["status"] = "failed"
        result["error"].append(f"'{von}' not in {rel_path} found")
        return result
    if count > 1:
        warn(f"'{von}' kommt {count}x vor — erste Fundstelle will replaces")
        result["meldungen"].append(f"Mehrfachfund: {count}x")
    else:
        ok(f"'{von}' found (1x)")
    
    # ─── SCHRITT 2: BACKUP ───
    backup_dir = create_backup(rel_path)
    if backup_dir:
        result["backup"] = str(backup_dir)
    else:
        result["status"] = "failed"
        result["error"].append("Backup failed")
        return result
    
    # ─── SCHRITT 2b: GIT PRE-EDIT COMMIT ───
    ws_root = AGENT_DIR
    if ws_root and (ws_root / ".git").exists():
        subprocess.run(["git", "-C", str(ws_root), "add", rel_path],
                       capture_output=True)
        subprocess.run(["git", "-C", str(ws_root), "commit", "-m",
                        f"pre-edit: {grund}"], capture_output=True)
        result["meldungen"].append("Git: pre-edit commit")

    # ─── STEP 3: CHANGE ───
    print(f"✏️  Change: {von} → {nach}")
    
    import re
    text = full_path.read_text()
    new_text = text.replace(von, nach, 1)
    if new_text == text:
        result["status"] = "no_change"
        result["error"] = f"Text '{von}' not found in {rel_path}"
        log(f"⚠️  Text not found: '{von}' in {rel_path}")
        return result
    full_path.write_text(new_text)
    
    # ─── SCHRITT 4: VALIDATE (AFTER) ───
    yaml_ok2, yaml_msg2 = validate_yaml(full_path)
    if not yaml_ok2:
        result["status"] = "rolled_back"
        result["error"].append(f"YAML korrumpiert → Rollback: {yaml_msg2}")
        # Git-Rollback
        if ws_root and (ws_root / ".git").exists():
            subprocess.run(["git", "-C", str(ws_root), "checkout", "--", rel_path],
                           capture_output=True)
            result["meldungen"].append("Git: rollback via checkout")
        restore_backup(backup_dir, rel_path)
        return result
    ok(f"YAML after Change weiterhin valid")
    
    # ─── SCHRITT 4b: GIT POST-EDIT COMMIT ───
    if ws_root and (ws_root / ".git").exists():
        subprocess.run(["git", "-C", str(ws_root), "add", rel_path],
                       capture_output=True)
        subprocess.run(["git", "-C", str(ws_root), "commit", "-m",
                        f"edit: {grund}"], capture_output=True)
        result["meldungen"].append("Git: post-edit commit")

    # Check ob new Value exists
    grep2 = subprocess.run(
        ["grep", "-c", nach, str(full_path)],
        capture_output=True, text=True
    )
    new_count = int(grep2.stdout.strip() or 0)
    if new_count == 0:
        result["status"] = "rolled_back"
        result["error"].append("Neuer Value not in file → Rollback")
        restore_backup(backup_dir, rel_path)
        return result
    
    ok(f"'{nach}' successful gesetzt")
    
    # ─── SCHRITT 5: DOKUMENTIEREN ───
    result["status"] = "success"
    
    # dev_changes.py benachrichtigen
    change_data = json.dumps({
        "file": rel_path,
        "von": von,
        "nach": nach,
        "grund": grund,
        "user": user,
        "risk": risk,
        "art": "patch",
        "backup": str(backup_dir),
        "validated_before": True,
        "validated_after": True,
        "user_approved": True,
    })
    
    subprocess.run(
        [sys.executable, str(CHANGES_SCRIPT), "--add", change_data],
        capture_output=True, text=True
    )
    
    print("")
    print("┌─────────────────────────────────────────────┐")
    print(f"│  ✅ CHANGE SUCCESSFULLY                     │")
    print(f"│                                              │")
    print(f"│  file:  {rel_path}")
    print(f"│  Von:    {von}")
    print(f"│  Nach:   {nach}")
    print(f"│  Reason:  {grund}")
    print(f"│  Backup: {backup_dir}")
    print(f"└─────────────────────────────────────────────┘")
    
    return result


def load_best_practices(bp_path=None):
    """Loads best-practices.yaml. Givet leeres Dict bei Error."""
    if bp_path is None:
        bp_path = Path(__file__).parent.parent / ".state" / "best-practices.yaml"
    bp_path = Path(bp_path)
    if not bp_path.exists():
        return {}
    try:
        with open(bp_path) as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def validate_against_best_practices(agent_content, bp):
    """Validated YAML-String gegen Best Practices. Givet Liste von (status, msg) back."""
    if not bp or "best_practices" not in bp:
        return [("ℹ️", "No Best Practices loaded")]
    
    findings = []
    import re
    
    for category, practices in bp["best_practices"].items():
        for practice in practices:
            pid = practice["id"]
            rule = practice["rule"]
            ctype = practice.get("check_type", "")
            cval = practice.get("check_value", "")
            auto = practice.get("auto_apply", False)
            severity = practice.get("severity", "🟢 info")
            
            passed = False
            
            if ctype == "regex":
                if isinstance(cval, str):
                    try:
                        passed = bool(re.search(cval, agent_content))
                    except re.error:
                        passed = False
                        
            elif ctype == "length":
                threshold = int(cval) if cval.isdigit() else 500
                passed = len(agent_content) <= threshold
                
            elif ctype == "yaml":
                try:
                    y = yaml.safe_load(agent_content)
                    keys = cval.split(".")
                    val = y
                    for k in keys:
                        if isinstance(val, dict):
                            val = val.get(k)
                        else:
                            val = None
                            break
                    passed = val is not None
                except Exception:
                    passed = False
                    
            elif ctype == "contains":
                passed = cval in agent_content
                
            elif ctype == "contains_all":
                if isinstance(cval, list):
                    passed = all(c in agent_content for c in cval)
                else:
                    passed = False
                    
            elif ctype == "grep":
                if isinstance(cval, str):
                    try:
                        passed = not bool(re.search(cval, agent_content))
                    except re.error:
                        passed = False
            
            elif ctype == "range":
                # Format: "300-900" -> min=300, max=900
                try:
                    parts = cval.split("-")
                    y = yaml.safe_load(agent_content)
                    keys = cval.split(".")
                    val = y
                    for k in keys:
                        if isinstance(val, dict):
                            val = val.get(k)
                        else:
                            val = None
                            break
                    if val is not None:
                        passed = int(parts[0]) <= int(val) <= int(parts[1])
                except Exception:
                    passed = False
            if auto:
                status = "✅" if passed else "❌"
            else:
                status = "✅" if passed else "ℹ️"
            
            if not passed:
                findings.append((status, f"{pid}: {rule}"))
    
    return findings


def cmd_validate(args):
    """CLI for --validate: Validated YAML + checks gegen Best Practices."""
    rel_path = args[0] if args else ""
    if not rel_path:
        return "❌ --validate erfordert a File path"
    
    full_path = Path(rel_path)
    if not full_path.exists():
        full_path = AGENT_DIR / rel_path
    if not full_path.exists():
        return f"❌ file not found: {rel_path}"
    
    with open(full_path) as f:
        content = f.read()
    
    lines = content.count("\n") + 1
    size = full_path.stat().st_size
    
    # YAML-Syntax-Check
    ok = True
    yaml_msg = ""
    try:
        yaml.safe_load(content)
    except yaml.YAMLError as e:
        ok = False
        yaml_msg = str(e)
    
    # Best-Practice-Check
    bp = load_best_practices()
    bp_findings = validate_against_best_practices(content, bp)
    
    out = []
    out.append(f"🔍 VALIDIERUNG: {rel_path}")
    out.append("━" * 50)
    out.append(f"  size: {size} Bytes, {lines} Zeilen")
    out.append(f"  YAML: {'✅ Valid' if ok else f'❌ Invalid: {yaml_msg}'}")
    out.append("")
    
    if bp_findings:
        out.append(f"  Best-Practice-Checks ({len(bp_findings)}):")
        for status, msg in bp_findings:
            out.append(f"    {status} {msg}")
    else:
        out.append("  ℹ️ No Best-Practice-Checks available (best-practices.yaml empty?)")
    
    passed = sum(1 for s, _ in bp_findings if "✅" in s)
    failed = sum(1 for s, _ in bp_findings if "❌" in s)
    info = sum(1 for s, _ in bp_findings if "ℹ️" in s)
    total = passed + failed + info
    
    out.append("")
    out.append("━" * 50)
    if total > 0:
        out.append(f"  ✅ {passed}/{total} bestanden")
        if failed > 0:
            out.append(f"  ❌ {failed} failed — before dem Einsatz beheben")
        if info > 0:
            out.append(f"  ℹ️ {info} Notes")
    else:
        out.append("  ℹ️ No Checks performed")
    
    return "\n".join(out)


def do_validate(rel_path: str) -> str:
    """Only Validate a file."""
    full_path = AGENT_DIR / rel_path
    if not full_path.exists():
        return f"❌ file not found: {rel_path}"
    
    ok, msg = validate_yaml(full_path)
    lines = 0
    try:
        with open(full_path) as f:
            lines = sum(1 for _ in f)
    except:
        pass
    
    out = []
    out.append(f"🔍 VALIDIERUNG: {rel_path}")
    out.append("━" * 40)
    out.append(f"  size: {full_path.stat().st_size} Bytes, {lines} Zeilen")
    out.append(f"  Status: {'✅ Valid' if ok else '❌ Invalid'}")
    if not ok:
        out.append(f"  Error: {msg}")
    return "\n".join(out)


def do_backup(rel_path: str) -> str:
    """Only Backup a file."""
    backup_dir = create_backup(rel_path)
    if backup_dir:
        return f"✅ Backup: {backup_dir / Path(rel_path).name}"
    return f"❌ Backup failed"


def do_rollback(backup_path: str, rel_path: str) -> str:
    """Stelle eine file aus a Backup again her."""
    backup_dir = Path(backup_path)
    if not backup_dir.exists():
        return f"❌ Backup-Directory not found: {backup_path}"
    
    if restore_backup(backup_dir, rel_path):
        return f"✅ Rollback: {rel_path} againhergestellt"
    return f"❌ Rollback failed"


def main():
    import argparse
    parser = argparse.ArgumentParser(description="dev_editor.py — Framework-Editor")
    parser.add_argument("--patch", type=str, help="file (relativ zu agent/)")
    parser.add_argument("--von", type=str, default="", help="Alter Value")
    parser.add_argument("--nach", type=str, default="", help="Neuer Value")
    parser.add_argument("--grund", type=str, default="", help="Reason der Change")
    parser.add_argument("--user", type=str, default="Marius")
    parser.add_argument("--risk", type=str, default="niedrig")
    parser.add_argument("--validate", type=str, help="YAML validate + Best-Practice-Check")
    parser.add_argument("--backup", type=str, help="Only Backup")
    parser.add_argument("--rollback-dir", type=str, help="Backup-Directory")
    parser.add_argument("--rollback-file", type=str, help="file for Rollback")
    
    args = parser.parse_known_args()[0]
    
    if not AGENT_DIR or not AGENT_DIR.exists():
        print("❌ agent/ Directory not found")
        sys.exit(1)
    
    if args.validate:
        result = cmd_validate([args.validate])
        print(result)
        sys.exit(0 if "❌" not in result else 1)
    
    elif args.backup:
        print(do_backup(args.backup))
    
    elif args.rollback_dir and args.rollback_file:
        print(do_rollback(args.rollback_dir, args.rollback_file))
    
    elif args.patch:
        if not args.von or not args.nach or not args.grund:
            print("❌ --patch erfordert --von, --nach und --grund")
            sys.exit(1)
        result = do_patch(args.patch, args.von, args.nach, args.grund, args.user, args.risk)
        if result["status"] != "success":
            print(f"\n❌ Status: {result['status']}")
            for f in result["error"]:
                print(f"  • {f}")
            sys.exit(1)
    
    else:
        print("🔧 dev_editor.py — Framework-Editor")
        print("")
        print("Verwendung:")
        print("  --patch <file> --von '<old>' --nach '<new>' --grund '<grund>'")
        print("  --validate <file>")
        print("  --backup <file>")
        print("  --rollback-dir <dir> --rollback-file <file>")


if __name__ == "__main__":
    main()
