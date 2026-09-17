#!/usr/bin/env python3
"""
dev_yaml_check.py — YAML/Syntax/State validation (v1.0.0)

R89 Phase 6: Script-replacement for sub_mas-recovery-immune.yaml.
Replaces LLM-wrapped deterministic checks (yaml.safe_load, compile, bash -n)
with one deterministic tool.

Commands:
  CHECK_YAML <file>        — validate single YAML file, return JSON {status, error?, warnings[]}
  CHECK_SYNTAX <file> <py|sh|auto>  — validate Python (compile) or Shell (bash -n) syntax
  VERIFY_STATE <workspace> — recursive scan of all YAMLs in workspace, report statistics
  CHECK_ALL <file> <file_type>      — run all applicable checks (yaml + syntax)

Output: JSON to stdout. Exit 0=PASS, 1=ERROR, 2=WARN.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


def check_yaml(filepath: str) -> dict[str, Any]:
    """Validate a single YAML file via yaml.safe_load.

    Edge cases (per Coronashield spec):
      - File not found      → P1 error
      - File empty (0 bytes) → P2 warning + ok
      - YAML with non-YAML exception → P1 error
      - Unicode error       → P3 info
      - Binary file         → P1 error
    """
    result: dict[str, Any] = {
        "file": filepath,
        "check": "yaml",
        "status": "ok",
        "warnings": [],
        "error": None,
        "lines": 0,
    }

    if not os.path.isfile(filepath):
        result["status"] = "error"
        result["error"] = f"File not found: {filepath}"
        return result

    # Empty file → P2 warning
    size = os.path.getsize(filepath)
    if size == 0:
        result["status"] = "warning"
        result["warnings"].append({
            "severity": "P2",
            "title": "Empty file",
            "description": "File is 0 bytes — valid YAML but no content",
        })
        return result

    # Binary detection: try to read as text
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        result["status"] = "error"
        result["error"] = "Binary file detected — not a valid text/YAML file"
        return result
    except Exception as e:
        result["status"] = "error"
        result["error"] = f"Read error: {e}"
        return result

    result["lines"] = content.count("\n") + 1

    # YAML parse
    try:
        import yaml
        yaml.safe_load(content)
    except yaml.YAMLError as e:
        result["status"] = "error"
        result["error"] = f"YAML syntax error: {e}"
        return result
    except Exception as e:
        result["status"] = "error"
        result["error"] = f"Non-YAML exception: {type(e).__name__}: {e}"
        return result

    return result


def detect_file_type(filepath: str) -> str:
    """Detect file type for syntax check. Returns 'py', 'sh', or 'unknown'."""
    # Shebang first
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            first = f.readline(200)
        if first.startswith("#!"):
            if "python" in first:
                return "py"
            if "bash" in first or "/sh" in first:
                return "sh"
    except Exception:
        pass

    # Extension
    if filepath.endswith(".py"):
        return "py"
    if filepath.endswith(".sh") or filepath.endswith(".bash"):
        return "sh"
    if filepath.endswith(".yaml") or filepath.endswith(".yml"):
        return "yaml"

    return "unknown"


def check_python_syntax(filepath: str) -> dict[str, Any]:
    """Python syntax check via compile()."""
    result: dict[str, Any] = {
        "file": filepath,
        "check": "python",
        "status": "ok",
        "error": None,
    }
    if not os.path.isfile(filepath):
        result["status"] = "error"
        result["error"] = f"File not found: {filepath}"
        return result

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        compile(source, filepath, "exec")
    except SyntaxError as e:
        result["status"] = "error"
        result["error"] = f"Python syntax error at line {e.lineno}: {e.msg}"
    except Exception as e:
        result["status"] = "error"
        result["error"] = f"{type(e).__name__}: {e}"

    return result


def check_shell_syntax(filepath: str) -> dict[str, Any]:
    """Shell syntax check via bash -n."""
    result: dict[str, Any] = {
        "file": filepath,
        "check": "shell",
        "status": "ok",
        "error": None,
        "warning": None,
    }
    if not os.path.isfile(filepath):
        result["status"] = "error"
        result["error"] = f"File not found: {filepath}"
        return result

    # Check if bash is available
    bash_check = subprocess.run(["which", "bash"], capture_output=True, text=True)
    if bash_check.returncode != 0:
        result["status"] = "warning"
        result["warning"] = "bash not installed — skipped shell syntax check"
        return result

    # bash -n: parse only, no execution
    proc = subprocess.run(
        ["bash", "-n", filepath],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        result["status"] = "error"
        result["error"] = (proc.stderr or proc.stdout).strip()
    return result


def check_syntax(filepath: str, file_type: str = "auto") -> dict[str, Any]:
    """Dispatch syntax check by file type."""
    if file_type == "auto":
        file_type = detect_file_type(filepath)
        if file_type == "yaml":
            return check_yaml(filepath)

    if file_type == "py":
        return check_python_syntax(filepath)
    elif file_type == "sh":
        return check_shell_syntax(filepath)
    elif file_type == "yaml":
        return check_yaml(filepath)
    else:
        return {
            "file": filepath,
            "check": "syntax",
            "status": "warning",
            "warning": f"Unknown file type: {file_type}. Use py|sh|yaml|auto.",
        }


def verify_state(workspace: str) -> dict[str, Any]:
    """Recursive YAML validation across workspace.

    Per Coronashield spec:
      - Find all *.yaml in workspace, excluding .backups/, checkpoints/
      - Validate each via yaml.safe_load
      - Statistics: total/ok/failed + score (0-100)
    """
    result: dict[str, Any] = {
        "workspace": workspace,
        "check": "state",
        "total": 0,
        "ok": 0,
        "failed": 0,
        "score": 0,
        "failures": [],
        "score_band": "unknown",
    }

    if not os.path.isdir(workspace):
        result["error"] = f"Workspace not found: {workspace}"
        result["status"] = "error"
        return result

    # Find all yaml files (exclude backups, checkpoints, dotfiles)
    yaml_files = []
    for root, dirs, files in os.walk(workspace):
        # Prune excluded directories
        dirs[:] = [d for d in dirs if d not in {".backups", "checkpoints", ".git",
                                                  "__pycache__", "node_modules",
                                                  ".venv", "venv"}]
        for f in files:
            if f.endswith((".yaml", ".yml")) and not f.startswith("."):
                yaml_files.append(os.path.join(root, f))

    result["total"] = len(yaml_files)

    if result["total"] == 0:
        result["status"] = "warning"
        result["warning"] = "No YAML files to check"
        return result

    for f in yaml_files:
        r = check_yaml(f)
        if r["status"] == "ok":
            result["ok"] += 1
        else:
            result["failed"] += 1
            result["failures"].append({
                "file": f,
                "error": r.get("error", "unknown"),
            })

    if result["total"] > 0:
        result["score"] = (result["ok"] * 100) // result["total"]

    if result["score"] == 100:
        result["score_band"] = "perfect"
        result["status"] = "ok"
    elif result["score"] >= 80:
        result["score_band"] = "good"
        result["status"] = "warning"
    else:
        result["score_band"] = "critical"
        result["status"] = "error"

    return result


def check_all(filepath: str, file_type: str = "auto") -> dict[str, Any]:
    """Run yaml + syntax check for given file."""
    results = {"file": filepath, "checks": []}

    if file_type == "auto":
        file_type = detect_file_type(filepath)

    # Always try YAML (most config files are yaml)
    if file_type in ("yaml", "auto"):
        results["checks"].append(check_yaml(filepath))

    if file_type == "py":
        results["checks"].append(check_python_syntax(filepath))
    elif file_type == "sh":
        results["checks"].append(check_shell_syntax(filepath))

    # Aggregate
    errors = sum(1 for c in results["checks"] if c["status"] == "error")
    warnings = sum(1 for c in results["checks"] if c["status"] == "warning")

    if errors > 0:
        results["status"] = "error"
    elif warnings > 0:
        results["status"] = "warning"
    else:
        results["status"] = "ok"

    return results


def print_usage() -> None:
    print(__doc__)


def main() -> int:
    if len(sys.argv) < 2:
        print_usage()
        return 2

    cmd = sys.argv[1].upper()

    if cmd == "CHECK_YAML":
        if len(sys.argv) < 3:
            print("Usage: CHECK_YAML <file>", file=sys.stderr)
            return 2
        result = check_yaml(sys.argv[2])
    elif cmd == "CHECK_SYNTAX":
        if len(sys.argv) < 3:
            print("Usage: CHECK_SYNTAX <file> [py|sh|yaml|auto]", file=sys.stderr)
            return 2
        ftype = sys.argv[3] if len(sys.argv) > 3 else "auto"
        result = check_syntax(sys.argv[2], ftype)
    elif cmd == "VERIFY_STATE":
        if len(sys.argv) < 3:
            print("Usage: VERIFY_STATE <workspace>", file=sys.stderr)
            return 2
        result = verify_state(sys.argv[2])
    elif cmd == "CHECK_ALL":
        if len(sys.argv) < 3:
            print("Usage: CHECK_ALL <file> [py|sh|yaml|auto]", file=sys.stderr)
            return 2
        ftype = sys.argv[3] if len(sys.argv) > 3 else "auto"
        result = check_all(sys.argv[2], ftype)
    elif cmd in ("-h", "--help", "HELP"):
        print_usage()
        return 0
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print_usage()
        return 2

    print(json.dumps(result, indent=2))

    if result.get("status") == "error":
        return 1
    if result.get("status") == "warning":
        return 0  # warnings don't fail
    return 0


if __name__ == "__main__":
    sys.exit(main())
