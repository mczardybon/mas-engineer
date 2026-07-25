#!/usr/bin/env python3
"""
dev_tff.py — replaces sub_mas-test-fix-failures-finder, -ranker, -validator (×3).

Single script that handles the deterministic parts of the test-fix-failures pipeline:

  FIND [test_dir] [e2e_log]  — parse e2e output, list failures (was finder)
  RANK [failures_json]       — sort failures by priority/impact (was ranker)
  VALIDATE <patch> [type]    — run syntax/rule/crossref validation (was tff-syntax/rule/crossref)

Deterministic leaves only. designer + applier stay as LLM recipes (real design work).
finder → ranker → designer → applier → validator-director (3x validate) → done.

Called from recipes via `bash` extension as:
  python3 tools/dev_tff.py <command> [args...]

Output: JSON to stdout (machine-readable). Exit: 0=OK, 1=ISSUES_FOUND, 2=ERROR.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent


def find_failures(test_dir: str = "tests", e2e_log: str = None) -> dict:
    """
    FIND: parse e2e output, list failures.

    If e2e_log given: parse pytest output for FAIL/ERROR lines.
    If not: run pytest, capture output, parse.
    """
    if e2e_log and os.path.exists(e2e_log):
        with open(e2e_log) as f:
            output = f.read()
        source = f"log:{e2e_log}"
    else:
        r = subprocess.run(["python3", "-m", "pytest", test_dir, "-v", "--tb=short", "--no-header"],
                          capture_output=True, text=True, timeout=300,
                          cwd=os.path.dirname(REPO_ROOT) if REPO_ROOT.name == "mas-engineer" else ".")
        output = r.stdout + r.stderr
        source = "fresh pytest run"

    # Parse pytest output: FAILED <path>::<name> - <reason>
    failures = []
    for line in output.split("\n"):
        m = re.match(r"FAILED\s+([\w/\.\-]+)::(\w+)\s*-\s*(.*)", line)
        if m:
            failures.append({
                "file": m.group(1),
                "test": m.group(2),
                "reason": m.group(3).strip()[:200],
                "type": "FAILED",
                "priority": 5,  # default medium
            })
        m = re.match(r"ERROR\s+([\w/\.\-]+)::(\w+)\s*-\s*(.*)", line)
        if m:
            failures.append({
                "file": m.group(1),
                "test": m.group(2),
                "reason": m.group(3).strip()[:200],
                "type": "ERROR",
                "priority": 8,  # higher priority (often setup issues)
            })
    # also short summary
    summary_m = re.search(r"=+\s*(\d+)\s+failed.*?(\d+)\s+passed", output, re.DOTALL)
    summary = {}
    if summary_m:
        summary = {"failed": int(summary_m.group(1)), "passed": int(summary_m.group(2))}

    return {
        "command": "FIND",
        "source": source,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "failures": failures,
        "summary": summary,
        "count": len(failures),
        "issues_found": len(failures) > 0,
    }


def rank_failures(failures_json: str) -> dict:
    """
    RANK: sort failures by priority (ERROR > FAILED, then by file/test).

    Input: path to JSON file with failures[] (or '-' for stdin).
    Output: sorted list, highest priority first.
    """
    if failures_json == "-":
        data = json.load(sys.stdin)
    else:
        with open(failures_json) as f:
            data = json.load(f)

    failures = data.get("failures", [])

    # Sort: priority desc, then file, then test
    ranked = sorted(failures, key=lambda f: (-f.get("priority", 0),
                                              f.get("file", ""),
                                              f.get("test", "")))

    # Assign rank numbers
    for i, f in enumerate(ranked, 1):
        f["rank"] = i

    return {
        "command": "RANK",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ranked_failures": ranked,
        "count": len(ranked),
        "top_priority": ranked[0] if ranked else None,
    }


def validate_patch(patch: str, vtype: str = "syntax") -> dict:
    """
    VALIDATE: syntax/rule/crossref check on a patch.

    vtype: 'syntax' (yaml.safe_load), 'rule' (R01-R18 grep), 'crossref' (ref consistency)
    """
    if vtype == "syntax":
        return _validate_syntax(patch)
    elif vtype == "rule":
        return _validate_rule(patch)
    elif vtype == "crossref":
        return _validate_crossref(patch)
    else:
        return {"command": "VALIDATE", "error": f"unknown vtype: {vtype}"}


def _validate_syntax(patch: str) -> dict:
    """YAML syntax check on patch file or patch diff."""
    findings = []
    if os.path.isfile(patch):
        try:
            import yaml
            with open(patch) as f:
                yaml.safe_load(f)
            ok = True
        except Exception as e:
            findings.append({"level": "ERROR", "code": "YAML-SYNTAX", "detail": str(e)})
            ok = False
    elif patch.startswith("--") or "\n--" in patch:  # diff format
        # Just check that all YAML-looking blocks parse
        try:
            import yaml
            yaml_blocks = re.findall(r"^\+\+\+\s+[^\n]*\n(?:[+][^\n]*\n)+", patch, re.MULTILINE)
            for i, block in enumerate(yaml_blocks):
                # Strip leading +
                content = "\n".join(l[1:] for l in block.split("\n")[1:] if l.startswith("+"))
                if content.strip():
                    try:
                        yaml.safe_load(content)
                    except yaml.YAMLError as e:
                        findings.append({"level": "WARN", "code": f"YAML-SYNTAX block {i}",
                                        "detail": str(e)})
            ok = not findings
        except ImportError:
            ok = True
            findings.append({"level": "WARN", "code": "PyYAML not installed", "detail": "skipped"})
    else:
        # Treat as inline YAML
        try:
            import yaml
            yaml.safe_load(patch)
            ok = True
        except Exception as e:
            findings.append({"level": "ERROR", "code": "YAML-SYNTAX", "detail": str(e)})
            ok = False

    return {
        "command": "VALIDATE",
        "vtype": "syntax",
        "patch": patch[:50] + ("..." if len(patch) > 50 else ""),
        "ok": ok,
        "findings": findings,
        "issues_found": not ok,
    }


def _validate_rule(patch: str) -> dict:
    """R01-R18 rule compliance check on patch file/diff."""
    findings = []
    rules = {
        "R01": r"no confirmation",
        "R04": r"general-improver",
        "R09": r"cross-domain",
        "R10": r"coronashield|yaml.safe_load",
        "R18": r"delegate",
    }

    content = ""
    if os.path.isfile(patch):
        with open(patch) as f:
            content = f.read()
    else:
        content = patch

    # Check for rule violations
    for rule, pattern in rules.items():
        # Look for negation patterns (e.g., "no confirmation required", "skip R01")
        m = re.search(rf"({pattern})", content, re.IGNORECASE)
        if m and re.search(rf"(skip|ignore|bypass|disable)\s+{rule}\b", content, re.IGNORECASE):
            findings.append({"level": "ERROR", "code": f"{rule}-BYPASS", "detail": m.group(0)[:100]})

    # Check if R10 is referenced when YAML is added
    if "yaml" in content.lower() and ".yaml" in content and "R10" not in content:
        findings.append({"level": "WARN", "code": "R10",
                        "detail": "YAML change detected but R10 (CORONASHIELD) not referenced"})

    ok = not any(f["level"] == "ERROR" for f in findings)
    return {
        "command": "VALIDATE",
        "vtype": "rule",
        "patch": patch[:50] + ("..." if len(patch) > 50 else ""),
        "ok": ok,
        "findings": findings,
        "issues_found": not ok,
    }


def _validate_crossref(patch: str) -> dict:
    """Cross-reference consistency check on patch."""
    findings = []
    content = ""
    if os.path.isfile(patch):
        with open(patch) as f:
            content = f.read()
    else:
        content = patch

    # Extract agent references: sub_mas-*, workflows.yaml, etc.
    refs = set(re.findall(r"sub_mas-[\w\-]+", content))

    # Check that each referenced file exists
    repo = REPO_ROOT
    for ref in refs:
        # Map: sub_mas-X → recipe/sub/sub_mas-X.yaml
        candidate = repo / "recipe" / "sub" / f"{ref}.yaml"
        if not candidate.exists():
            findings.append({"level": "WARN", "code": "CROSSREF-MISSING",
                            "detail": f"{ref} referenced but not found"})

    # Check workflows.yaml consistency
    workflows = repo / "recipe" / "workflows.yaml"
    if workflows.exists():
        try:
            import yaml
            with open(workflows) as f:
                wf = yaml.safe_load(f) or {}
            for ref in refs:
                # Convert to workflows.yaml key (replace - with _)
                wf_key = ref.replace("-", "_")
                if wf_key not in str(wf):
                    findings.append({"level": "INFO", "code": "CROSSREF-WORKFLOW",
                                    "detail": f"{ref} not in workflows.yaml ({wf_key})"})
        except Exception:
            pass

    ok = not any(f["level"] == "ERROR" for f in findings)
    return {
        "command": "VALIDATE",
        "vtype": "crossref",
        "patch": patch[:50] + ("..." if len(patch) > 50 else ""),
        "ok": ok,
        "findings": findings,
        "issues_found": not ok,
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: dev_tff.py <FIND|RANK|VALIDATE> [args]"}))
        sys.exit(2)

    cmd = sys.argv[1].upper()

    if cmd == "FIND":
        test_dir = sys.argv[2] if len(sys.argv) > 2 else "tests"
        e2e_log = sys.argv[3] if len(sys.argv) > 3 else None
        result = find_failures(test_dir, e2e_log)
    elif cmd == "RANK":
        failures_json = sys.argv[2] if len(sys.argv) > 2 else "-"
        result = rank_failures(failures_json)
    elif cmd == "VALIDATE":
        patch = sys.argv[2] if len(sys.argv) > 2 else ""
        vtype = sys.argv[3] if len(sys.argv) > 3 else "syntax"
        result = validate_patch(patch, vtype)
    else:
        result = {"error": f"unknown command: {cmd}"}

    print(json.dumps(result, indent=2))
    if result.get("issues_found") or result.get("findings") and any(
       f.get("level") == "ERROR" for f in result.get("findings", [])):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
