"""
Auto Repair pre-check profile (T1, T4-T10).

Mirrors the 7 tests from sub_mas-e2e-auto-repair-validator.yaml:
  T1, T4, T5, T6: auto_repair step exists in 4 recovery workflows
  T7: auto_repair step is present in all 4 workflows (cross-check)
  T8: auto_repair step has cmd or action
  T9: auto_repair step is not placeholder (echo-only)
  T10: auto_repair step references recipe/restore

Source of truth: recipe/sub/sub_mas-e2e-auto-repair-validator.yaml
"""
import time
import yaml
from pathlib import Path
from typing import Any, Dict, List

DESCRIPTION = "Auto-repair step validation across 4 recovery workflows (T1, T4-T10, mirrors e2e-verify-auto-repair)"

WORKFLOWS_FILE = Path(".state/workflows.yaml")

RECOVERY_WORKFLOWS = [
    "wf_recovery_checkpoint",
    "wf_recovery_defib",
    "wf_recovery_safezone",
    "wf_recovery_timeline",
]


def _get_auto_repair_step(workflows: dict, wf_name: str):
    """Get the auto_repair step from a workflow, or None."""
    wf = workflows.get(wf_name, {})
    for s in wf.get("steps", []):
        if s.get("id") == "auto_repair":
            return s
    return None


def _check_workflow_has_auto_repair(workflows: dict, wf_name: str) -> Dict[str, Any]:
    """T1/T4/T5/T6: workflow has an auto_repair step."""
    step = _get_auto_repair_step(workflows, wf_name)
    if step is None:
        return {
            "passed": False,
            "detail": f"{wf_name} has no auto_repair step",
        }
    return {
        "passed": True,
        "detail": f"auto_repair step found (id=auto_repair)",
    }


def _check_all_have_auto_repair(workflows: dict) -> Dict[str, Any]:
    """T7: all 4 workflows have auto_repair step."""
    missing = [n for n in RECOVERY_WORKFLOWS if _get_auto_repair_step(workflows, n) is None]
    if missing:
        return {
            "passed": False,
            "detail": f"missing in: {', '.join(missing)}",
        }
    return {
        "passed": True,
        "detail": f"all {len(RECOVERY_WORKFLOWS)} workflows have auto_repair step",
    }


def _check_all_have_cmd_or_action(workflows: dict) -> Dict[str, Any]:
    """T8: auto_repair step has cmd or action in all workflows."""
    bad = []
    for n in RECOVERY_WORKFLOWS:
        step = _get_auto_repair_step(workflows, n)
        if step is None:
            continue  # covered by T7
        if not (step.get("cmd") or step.get("action")):
            bad.append(n)
    if bad:
        return {
            "passed": False,
            "detail": f"empty cmd/action in: {', '.join(bad)}",
        }
    return {
        "passed": True,
        "detail": f"all auto_repair steps have cmd or action",
    }


def _check_no_placeholders(workflows: dict) -> Dict[str, Any]:
    """T9: auto_repair step is not placeholder (echo-only) in any workflow."""
    placeholders = []
    for n in RECOVERY_WORKFLOWS:
        step = _get_auto_repair_step(workflows, n)
        if step is None:
            continue
        cmd = str(step.get("cmd", "")).strip()
        if cmd.startswith("echo "):
            placeholders.append(n)
    if placeholders:
        return {
            "passed": False,
            "detail": f"placeholders in: {', '.join(placeholders)}",
        }
    return {
        "passed": True,
        "detail": f"no echo-only placeholders in {len(RECOVERY_WORKFLOWS)} workflows",
    }


def _check_recipe_restore_ref(workflows: dict) -> Dict[str, Any]:
    """T10: auto_repair step references 'recipe/restore' (cmd or action)."""
    missing = []
    for n in RECOVERY_WORKFLOWS:
        step = _get_auto_repair_step(workflows, n)
        if step is None:
            continue
        combined = (str(step.get("cmd", "")) + str(step.get("action", ""))).lower()
        if "restore" not in combined:
            missing.append(n)
    if missing:
        return {
            "passed": False,
            "detail": f"no 'restore' in: {', '.join(missing)}",
        }
    return {
        "passed": True,
        "detail": f"all auto_repair steps reference 'restore'",
    }


def run(workspace: Path) -> Dict[str, Any]:
    import os
    os.chdir(workspace)
    global WORKFLOWS_FILE
    WORKFLOWS_FILE = Path(".state/workflows.yaml").resolve()
    if not WORKFLOWS_FILE.exists():
        WORKFLOWS_FILE = workspace / ".state" / "workflows.yaml"

    start = time.time()
    checks: List[Dict[str, Any]] = []

    # Load workflows once
    try:
        data = yaml.safe_load(open(WORKFLOWS_FILE))
        workflows = data.get("task_workflows", {})
    except Exception as e:
        return {
            "title": "Auto Repair (T1, T4-T10)",
            "passed": 0,
            "failed": 7,
            "duration_s": time.time() - start,
            "checks": [{
                "id": "T0",
                "name": "workflows.yaml loads",
                "passed": False,
                "detail": f"yaml parse error: {e}",
            }],
        }

    # T1, T4, T5, T6 — one per workflow
    for idx, wf in enumerate(RECOVERY_WORKFLOWS):
        test_id = {0: "T1", 1: "T4", 2: "T5", 3: "T6"}[idx]
        checks.append({
            "id": test_id,
            "name": f"{wf} has auto_repair step",
            **_check_workflow_has_auto_repair(workflows, wf),
        })

    # T7: all 4 have auto_repair
    checks.append({
        "id": "T7",
        "name": "all 4 workflows have auto_repair step",
        **_check_all_have_auto_repair(workflows),
    })

    # T8: auto_repair has cmd/action
    checks.append({
        "id": "T8",
        "name": "auto_repair has cmd or action",
        **_check_all_have_cmd_or_action(workflows),
    })

    # T9: no placeholders
    checks.append({
        "id": "T9",
        "name": "auto_repair is not echo-only placeholder",
        **_check_no_placeholders(workflows),
    })

    # T10: references recipe/restore
    checks.append({
        "id": "T10",
        "name": "auto_repair references recipe/restore",
        **_check_recipe_restore_ref(workflows),
    })

    passed = sum(1 for c in checks if c.get("passed"))
    failed = sum(1 for c in checks if not c.get("passed"))
    return {
        "title": "Auto Repair (T1, T4-T10)",
        "passed": passed,
        "failed": failed,
        "duration_s": time.time() - start,
        "checks": checks,
    }
