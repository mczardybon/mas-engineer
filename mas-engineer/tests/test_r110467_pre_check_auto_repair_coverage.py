"""R110-467 — coverage-push r9: tools/pre_check_lib/auto_repair.py 0% → 100%

Auto-repair pre-check (T1, T4-T10). Validates that 4 recovery
workflows (checkpoint, defib, safezone, timeline) each have an
auto_repair step that is real (cmd/action, no echo-only,
references recipe/restore).

Targets:
- _get_auto_repair_step(wfs, name): returns step with
  id='auto_repair' or None
- _check_workflow_has_auto_repair(wfs, name): pass/fail
- _check_all_have_auto_repair(wfs): T7 — all 4 have step
- _check_all_have_cmd_or_action(wfs): T8 — non-empty cmd/action
- _check_no_placeholders(wfs): T9 — not echo-only
- _check_recipe_restore_ref(wfs): T10 — 'restore' in cmd+action
- run(workspace): 7 checks, plus yaml-error fallback
"""

import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.pre_check_lib import auto_repair as ar  # noqa: E402


def _write_workflows(workspace, content):
    """Write workflows.yaml. Wraps in {task_workflows: ...} if not already."""
    if "task_workflows" not in content:
        content = {"task_workflows": content}
    p = workspace / ".mase" / "workflows.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w') as f:
        yaml.safe_dump(content, f)
    return p


def _full_valid_workflows():
    """All 4 recovery workflows with proper auto_repair steps.

    Returns the EXTRACTED task_workflows dict (not wrapped), since the
    check_* helpers expect `workflows.get(wf_name, ...)`.
    """
    repair = {"id": "auto_repair",
              "cmd": "python3 recipe/restore.py --auto"}
    return {
        "wf_recovery_checkpoint": {"steps": [repair]},
        "wf_recovery_defib": {"steps": [repair]},
        "wf_recovery_safezone": {"steps": [repair]},
        "wf_recovery_timeline": {"steps": [repair]},
    }


# ─────────────────────────────────────────────────────────────────────
# _get_auto_repair_step
# ─────────────────────────────────────────────────────────────────────
class TestGetAutoRepairStep:
    def test_step_found(self):
        wfs = {"wf_recovery_x": {"steps": [
            {"id": "other", "cmd": "x"},
            {"id": "auto_repair", "cmd": "y"},
        ]}}
        s = ar._get_auto_repair_step(wfs, "wf_recovery_x")
        assert s is not None
        assert s["cmd"] == "y"

    def test_step_not_found(self):
        wfs = {"wf_recovery_x": {"steps": [
            {"id": "other", "cmd": "x"},
        ]}}
        s = ar._get_auto_repair_step(wfs, "wf_recovery_x")
        assert s is None

    def test_workflow_missing(self):
        s = ar._get_auto_repair_step({}, "wf_recovery_x")
        assert s is None

    def test_no_steps_key(self):
        wfs = {"wf_recovery_x": {}}
        s = ar._get_auto_repair_step(wfs, "wf_recovery_x")
        assert s is None


# ─────────────────────────────────────────────────────────────────────
# _check_workflow_has_auto_repair (T1, T4-T6)
# ─────────────────────────────────────────────────────────────────────
class TestCheckWorkflowHasAutoRepair:
    def test_pass(self):
        wfs = {"wf_recovery_x": {"steps": [
            {"id": "auto_repair", "cmd": "x"},
        ]}}
        r = ar._check_workflow_has_auto_repair(wfs, "wf_recovery_x")
        assert r["passed"] is True
        assert "found" in r["detail"]

    def test_fail(self):
        wfs = {"wf_recovery_x": {"steps": [{"id": "other"}]}}
        r = ar._check_workflow_has_auto_repair(wfs, "wf_recovery_x")
        assert r["passed"] is False
        assert "no auto_repair" in r["detail"]


# ─────────────────────────────────────────────────────────────────────
# _check_all_have_auto_repair (T7)
# ─────────────────────────────────────────────────────────────────────
class TestCheckAllHaveAutoRepair:
    def test_all_have(self):
        r = ar._check_all_have_auto_repair(_full_valid_workflows())
        assert r["passed"] is True
        assert "all 4 workflows" in r["detail"]

    def test_some_missing(self):
        # _check_* helpers expect workflows dict directly (no
        # 'task_workflows' wrapper).
        wfs = {
            "wf_recovery_checkpoint": {"steps": [
                {"id": "auto_repair", "cmd": "x"}]},
            # defib, safezone, timeline missing
        }
        r = ar._check_all_have_auto_repair(wfs)
        assert r["passed"] is False
        assert "wf_recovery_defib" in r["detail"]
        assert "wf_recovery_safezone" in r["detail"]
        assert "wf_recovery_timeline" in r["detail"]


# ─────────────────────────────────────────────────────────────────────
# _check_all_have_cmd_or_action (T8)
# ─────────────────────────────────────────────────────────────────────
class TestCheckCmdOrAction:
    def test_all_have_cmd(self):
        r = ar._check_all_have_cmd_or_action(_full_valid_workflows())
        assert r["passed"] is True

    def test_all_have_action(self):
        wfs = {
            n: {"steps": [{"id": "auto_repair", "action": "do thing"}]}
            for n in ar.RECOVERY_WORKFLOWS
        }
        r = ar._check_all_have_cmd_or_action(wfs)
        assert r["passed"] is True

    def test_some_empty(self):
        wfs = {
            "wf_recovery_checkpoint": {"steps": [
                {"id": "auto_repair", "cmd": "x"}]},
            "wf_recovery_defib": {"steps": [
                {"id": "auto_repair"}]},   # no cmd/action
            "wf_recovery_safezone": {"steps": [
                {"id": "auto_repair", "cmd": "y"}]},
            "wf_recovery_timeline": {"steps": [
                {"id": "auto_repair", "cmd": "z"}]},
        }
        r = ar._check_all_have_cmd_or_action(wfs)
        assert r["passed"] is False
        assert "wf_recovery_defib" in r["detail"]

    def test_missing_step_skipped(self):
        # If step is None (covered by T7), skip → not in bad list
        wfs = {
            "wf_recovery_checkpoint": {"steps": []},
        }
        r = ar._check_all_have_cmd_or_action(wfs)
        assert r["passed"] is True


# ─────────────────────────────────────────────────────────────────────
# _check_no_placeholders (T9)
# ─────────────────────────────────────────────────────────────────────
class TestCheckNoPlaceholders:
    def test_no_placeholders(self):
        r = ar._check_no_placeholders(_full_valid_workflows())
        assert r["passed"] is True
        assert "no echo-only" in r["detail"]

    def test_placeholder(self):
        wfs = {
            "wf_recovery_checkpoint": {"steps": [
                {"id": "auto_repair", "cmd": "echo placeholder"}]},
            "wf_recovery_defib": {"steps": [
                {"id": "auto_repair", "cmd": "real work"}]},
            "wf_recovery_safezone": {"steps": [
                {"id": "auto_repair", "cmd": "real"}]},
            "wf_recovery_timeline": {"steps": [
                {"id": "auto_repair", "cmd": "real"}]},
        }
        r = ar._check_no_placeholders(wfs)
        assert r["passed"] is False
        assert "wf_recovery_checkpoint" in r["detail"]

    def test_missing_step_skipped(self):
        wfs = {}
        r = ar._check_no_placeholders(wfs)
        assert r["passed"] is True

    def test_cmd_is_not_string(self):
        # cmd = 123 (int) → str(123).strip() = "123" → not echo
        wfs = {
            n: {"steps": [{"id": "auto_repair", "cmd": 123}]}
            for n in ar.RECOVERY_WORKFLOWS
        }
        r = ar._check_no_placeholders(wfs)
        assert r["passed"] is True


# ─────────────────────────────────────────────────────────────────────
# _check_recipe_restore_ref (T10)
# ─────────────────────────────────────────────────────────────────────
class TestCheckRecipeRestoreRef:
    def test_all_reference_restore(self):
        r = ar._check_recipe_restore_ref(_full_valid_workflows())
        assert r["passed"] is True
        assert "all auto_repair steps" in r["detail"]

    def test_action_only_restore(self):
        # restore in action, not cmd
        wfs = {
            n: {"steps": [{"id": "auto_repair",
                          "action": "call recipe/restore"}]}
            for n in ar.RECOVERY_WORKFLOWS
        }
        r = ar._check_recipe_restore_ref(wfs)
        assert r["passed"] is True

    def test_missing_restore(self):
        wfs = {
            "wf_recovery_checkpoint": {"steps": [
                {"id": "auto_repair", "cmd": "x"}]},
            "wf_recovery_defib": {"steps": [
                {"id": "auto_repair", "cmd": "y"}]},
            "wf_recovery_safezone": {"steps": [
                {"id": "auto_repair", "cmd": "z"}]},
            "wf_recovery_timeline": {"steps": [
                {"id": "auto_repair", "cmd": "restore"}]},
        }
        r = ar._check_recipe_restore_ref(wfs)
        assert r["passed"] is False
        assert "wf_recovery_checkpoint" in r["detail"]

    def test_case_insensitive(self):
        # "RESTORE" upper-case → .lower() → matched
        wfs = {
            n: {"steps": [{"id": "auto_repair", "cmd": "RESTORE"}]}
            for n in ar.RECOVERY_WORKFLOWS
        }
        r = ar._check_recipe_restore_ref(wfs)
        assert r["passed"] is True

    def test_missing_step_skipped(self):
        wfs = {}
        r = ar._check_recipe_restore_ref(wfs)
        assert r["passed"] is True


# ─────────────────────────────────────────────────────────────────────
# run (entry point)
# ─────────────────────────────────────────────────────────────────────
class TestRun:
    def test_run_all_pass(self, tmp_path):
        _write_workflows(tmp_path, _full_valid_workflows())
        r = ar.run(tmp_path)
        assert r["title"] == "Auto Repair (T1, T4-T10)"
        # run() produces 8 checks: T1+T4+T5+T6 (one per workflow) + T7+T8+T9+T10
        assert r["passed"] == 8
        assert r["failed"] == 0
        assert len(r["checks"]) == 8
        ids = [c["id"] for c in r["checks"]]
        assert ids == ["T1", "T4", "T5", "T6", "T7", "T8", "T9", "T10"]

    def test_run_yaml_error(self, tmp_path):
        p = tmp_path / ".mase" / "workflows.yaml"
        p.parent.mkdir(parents=True)
        with open(p, 'w') as f:
            f.write("invalid: : :\n  broken:")
        r = ar.run(tmp_path)
        assert r["title"] == "Auto Repair (T1, T4-T10)"
        assert r["passed"] == 0
        assert r["failed"] == 7  # declared in error fallback
        assert len(r["checks"]) == 1
        assert r["checks"][0]["id"] == "T0"
        assert "yaml parse error" in r["checks"][0]["detail"]

    def test_run_some_missing(self, tmp_path):
        _write_workflows(tmp_path, {
            "wf_recovery_checkpoint": {"steps": [
                {"id": "auto_repair", "cmd": "real restore"}]},
            # others missing
        })
        r = ar.run(tmp_path)
        assert r["passed"] >= 1  # T1 for checkpoint
        assert r["failed"] >= 3

    def test_run_real_repo(self):
        # Real workspace run
        r = ar.run(REPO_ROOT)
        assert r["title"] == "Auto Repair (T1, T4-T10)"
        assert len(r["checks"]) == 8
