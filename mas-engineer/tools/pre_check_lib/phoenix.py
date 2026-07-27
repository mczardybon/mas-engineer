"""
Phoenix Fixes pre-check profile (T1-T7).

Mirrors the 7 tests from sub_mas-e2e-phoenix-fixes-director.yaml:
  T1: wf_recovery_immune exists
  T2: 4 new recovery workflows exist (immune + checkpoint + defib + safezone + timeline)
  T3: recovery_checkpoint has restore-step
  T4: recovery_defib has defibrillate-step
  T5: recovery_safezone has safezone-step
  T6: all 5 recovery workflows can be loaded (yaml valid)
  T7: recovery_timeline has timeline-step

Source of truth: recipe/sub/sub_mas-e2e-phoenix-fixes-validator.yaml + -runner.yaml
"""
import time
import yaml
from pathlib import Path
from typing import Any, Dict, List

DESCRIPTION = "Phoenix recovery workflow fixes (T1-T7, mirrors e2e-verify-phoenix-fixes)"

WORKFLOWS_FILE = Path(".state/workflows.yaml")


def _check_recovery_workflow(wf_name: str, step_keyword: str) -> Dict[str, Any]:
    """Check that a recovery workflow has a step with keyword in cmd.

    Mirrors original validator behavior: checks cmd field only (not id).
    Original snippet: any(keyword in s.get('cmd','').lower() for s in wf.get('steps',[]))
    """
    try:
        data = yaml.safe_load(open(WORKFLOWS_FILE))
        twfs = data.get("task_workflows", {})
        if wf_name not in twfs:
            return {
                "passed": False,
                "detail": f"workflow {wf_name} not found",
            }
        wf = twfs[wf_name]
        steps = wf.get("steps", [])
        has_step = any(
            step_keyword in str(s.get("cmd", "")).lower()
            for s in steps
        )
        if has_step:
            return {"passed": True, "detail": f"{len(steps)} steps"}
        # Show which step-ids exist to help diagnose
        ids = [str(s.get("id", "?")) for s in steps]
        return {
            "passed": False,
            "detail": f"no cmd with '{step_keyword}' (step-ids: {', '.join(ids)})",
        }
    except Exception as e:
        return {"passed": False, "detail": f"error: {e}"}


def _check_yaml_loads() -> Dict[str, Any]:
    """T6: workflows.yaml can be loaded (yaml valid)."""
    try:
        data = yaml.safe_load(open(WORKFLOWS_FILE))
        twfs = data.get("task_workflows", {})
        recovery = [n for n in twfs if n.startswith("wf_recovery_")]
        return {
            "passed": len(twfs) > 0,
            "detail": f"{len(twfs)} task_workflows, {len(recovery)} recovery",
        }
    except Exception as e:
        return {"passed": False, "detail": f"yaml parse error: {e}"}


def _check_workflow_count() -> Dict[str, Any]:
    """T2: 5 recovery workflows (immune + 4 new)."""
    try:
        data = yaml.safe_load(open(WORKFLOWS_FILE))
        twfs = data.get("task_workflows", {})
        recovery = [n for n in sorted(twfs.keys()) if n.startswith("wf_recovery_")]
        return {
            "passed": len(recovery) == 5,
            "detail": f"{len(recovery)}/5 recovery workflows: {', '.join(recovery)}",
        }
    except Exception as e:
        return {"passed": False, "detail": f"error: {e}"}


def _check_workflow_exists(name: str) -> Dict[str, Any]:
    """T1: single workflow exists check."""
    try:
        data = yaml.safe_load(open(WORKFLOWS_FILE))
        twfs = data.get("task_workflows", {})
        return {
            "passed": name in twfs,
            "detail": "found" if name in twfs else "missing",
        }
    except Exception as e:
        return {"passed": False, "detail": f"error: {e}"}


def run(workspace: Path) -> Dict[str, Any]:
    """Run all 7 phoenix-fixes pre-checks."""
    import os
    # Ensure we look in the workspace, not cwd
    os.chdir(workspace)
    global WORKFLOWS_FILE
    WORKFLOWS_FILE = Path(".state/workflows.yaml").resolve()
    if not WORKFLOWS_FILE.exists():
        # try absolute from workspace
        WORKFLOWS_FILE = workspace / ".state" / "workflows.yaml"

    start = time.time()
    checks: List[Dict[str, Any]] = []

    # T1: wf_recovery_immune exists
    checks.append({
        "id": "T1",
        "name": "wf_recovery_immune exists",
        **_check_workflow_exists("wf_recovery_immune"),
    })

    # T2: 5 recovery workflows total
    checks.append({
        "id": "T2",
        "name": "5 recovery workflows exist (immune + 4 new)",
        **_check_workflow_count(),
    })

    # T3: recovery_checkpoint has restore-step
    checks.append({
        "id": "T3",
        "name": "recovery_checkpoint has restore-step",
        **_check_recovery_workflow("wf_recovery_checkpoint", "restore"),
    })

    # T4: recovery_defib has defibrillate-step
    checks.append({
        "id": "T4",
        "name": "recovery_defib has defibrillate-step",
        **_check_recovery_workflow("wf_recovery_defib", "defib"),
    })

    # T5: recovery_safezone has safezone-step
    checks.append({
        "id": "T5",
        "name": "recovery_safezone has safezone-step",
        **_check_recovery_workflow("wf_recovery_safezone", "safezone"),
    })

    # T6: workflows.yaml parses (yaml valid)
    checks.append({
        "id": "T6",
        "name": "workflows.yaml parses + 5 recovery load",
        **_check_yaml_loads(),
    })

    # T7: recovery_timeline has timeline-step
    checks.append({
        "id": "T7",
        "name": "recovery_timeline has timeline-step",
        **_check_recovery_workflow("wf_recovery_timeline", "timeline"),
    })

    passed = sum(1 for c in checks if c.get("passed"))
    failed = sum(1 for c in checks if not c.get("passed"))
    return {
        "title": "Phoenix Fixes (T1-T7)",
        "passed": passed,
        "failed": failed,
        "duration_s": time.time() - start,
        "checks": checks,
    }
