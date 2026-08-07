"""
German Fixes pre-check profile (T1-T2).

Mirrors the 2 tests from sub_mas-e2e-german-fixes-validator.yaml:
  T1: 0 German descs remaining in task_workflows
  T2: No placeholder (echo-only) steps in wf_recovery_*

Source of truth: recipe/sub/sub_mas-e2e-german-fixes-validator.yaml
"""
import re
import time
import yaml
from pathlib import Path
from typing import Any, Dict, List

DESCRIPTION = "German descs + placeholder step detection (T1-T2, mirrors e2e-verify-german-fixes)"

WORKFLOWS_FILE = Path(".mase/workflows.yaml")

# Same GERMAN word list as original validator (do not modify)
GERMAN_WORDS = [
    "und", "der", "die", "das", "mit", "für", "von", "aus", "bei",
    "Schritt", "Inhalt", "Prüfung", "Erstellen", "letzten", "zeigen",
    "anzeigen", "wieder", "Beliebig", "Bitt", "erzeugen", "ändern",
    "ausführen", "überprüfen", "ermitteln", "wiederherstellen",
    "initialisieren", "konfigurieren",
]


def _check_german_descs() -> Dict[str, Any]:
    """T1: 0 German descs remaining in task_workflows."""
    try:
        data = yaml.safe_load(open(WORKFLOWS_FILE))
        twfs = data.get("task_workflows", {})
        bad = []
        for name, wf in twfs.items():
            desc = wf.get("desc", "")
            found = [w for w in GERMAN_WORDS if re.search(rf"\b{w}\b", desc, re.IGNORECASE)]
            if found:
                bad.append((name, desc[:60], found))
        if len(bad) == 0:
            return {
                "passed": True,
                "detail": f"0 German descs across {len(twfs)} workflows",
            }
        # Show up to 3 offenders
        sample = bad[:3]
        offenders = ", ".join(f"{n} ({','.join(w[:2])})" for n, _, w in sample)
        return {
            "passed": False,
            "detail": f"{len(bad)} workflows with German descs (e.g. {offenders})",
        }
    except Exception as e:
        return {"passed": False, "detail": f"error: {e}"}


def _check_no_placeholders() -> Dict[str, Any]:
    """T2: No placeholder (echo-only) steps in wf_recovery_*."""
    try:
        data = yaml.safe_load(open(WORKFLOWS_FILE))
        twfs = data.get("task_workflows", {})
        recovery = [n for n in twfs if n.startswith("wf_recovery_")]
        placeholders = []
        for n in recovery:
            wf = twfs[n]
            steps = wf.get("steps", [])
            if not steps:
                continue
            echo_only = all(s.get("cmd", "").strip().startswith("echo ") for s in steps)
            if echo_only:
                placeholders.append(n)
        if len(placeholders) == 0:
            return {
                "passed": True,
                "detail": f"0/{len(recovery)} recovery workflows are placeholders",
            }
        return {
            "passed": False,
            "detail": f"{len(placeholders)}/{len(recovery)} placeholders: {', '.join(placeholders)}",
        }
    except Exception as e:
        return {"passed": False, "detail": f"error: {e}"}


def run(workspace: Path) -> Dict[str, Any]:
    import os
    os.chdir(workspace)
    global WORKFLOWS_FILE
    WORKFLOWS_FILE = Path(".mase/workflows.yaml").resolve()
    if not WORKFLOWS_FILE.exists():
        WORKFLOWS_FILE = workspace / ".mase" / "workflows.yaml"

    start = time.time()
    checks: List[Dict[str, Any]] = []

    checks.append({
        "id": "T1",
        "name": "0 German descs in task_workflows",
        **_check_german_descs(),
    })
    checks.append({
        "id": "T2",
        "name": "No placeholder (echo-only) steps in wf_recovery_*",
        **_check_no_placeholders(),
    })

    passed = sum(1 for c in checks if c.get("passed"))
    failed = sum(1 for c in checks if not c.get("passed"))
    return {
        "title": "German Fixes (T1-T2)",
        "passed": passed,
        "failed": failed,
        "duration_s": time.time() - start,
        "checks": checks,
    }
