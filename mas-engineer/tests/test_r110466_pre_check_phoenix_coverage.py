"""R110-466 — coverage-push r9: tools/pre_check_lib/phoenix.py 0% → 100%

Phoenix Fixes pre-check (T1-T7). Mirrors the 7 tests from
sub_mas-e2e-phoenix-fixes-director.yaml.

Targets:
- _check_recovery_workflow(wf_name, step_keyword):
  - workflow missing → passed=False "not found"
  - cmd contains keyword (lower-case) → passed=True "N steps"
  - no cmd with keyword → passed=False with step-ids list

- _check_yaml_loads():
  - yaml valid + non-empty → passed=True "N twfs, M recovery"
  - yaml error → passed=False "yaml parse error: ..."

- _check_workflow_count():
  - exactly 5 recovery → passed=True "5/5: ..."
  - != 5 → passed=False with list

- _check_workflow_exists(name):
  - found → passed=True "found"
  - missing → passed=False "missing"

- run(workspace): 7 checks, returns {title, passed, failed,
  duration_s, checks}
"""

import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.pre_check_lib import phoenix as ph  # noqa: E402


def _write_workflows(workspace, content):
    p = workspace / ".mase" / "workflows.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w') as f:
        yaml.safe_dump(content, f)
    return p


# ─────────────────────────────────────────────────────────────────────
# _check_recovery_workflow
# ─────────────────────────────────────────────────────────────────────
class TestCheckRecoveryWorkflow:
    def test_workflow_missing(self, tmp_path):
        _write_workflows(tmp_path, {"task_workflows": {}})
        ph.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"
        r = ph._check_recovery_workflow("wf_recovery_x", "restore")
        assert r["passed"] is False
        assert "not found" in r["detail"]

    def test_workflow_with_keyword(self, tmp_path):
        _write_workflows(tmp_path, {"task_workflows": {
            "wf_recovery_x": {"steps": [
                {"id": "s1", "cmd": "echo restore"},
                {"id": "s2", "cmd": "echo done"},
            ]},
        }})
        ph.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"
        r = ph._check_recovery_workflow("wf_recovery_x", "restore")
        assert r["passed"] is True
        assert "2 steps" in r["detail"]

    def test_workflow_keyword_missing(self, tmp_path):
        _write_workflows(tmp_path, {"task_workflows": {
            "wf_recovery_x": {"steps": [
                {"id": "s1", "cmd": "echo other"},
            ]},
        }})
        ph.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"
        r = ph._check_recovery_workflow("wf_recovery_x", "restore")
        assert r["passed"] is False
        assert "no cmd with 'restore'" in r["detail"]
        assert "s1" in r["detail"]  # step-ids shown

    def test_workflow_keyword_case_insensitive(self, tmp_path):
        # "RESTORE" upper-case in cmd, keyword "restore" lower
        _write_workflows(tmp_path, {"task_workflows": {
            "wf_recovery_x": {"steps": [
                {"id": "s1", "cmd": "echo RESTORE"},
            ]},
        }})
        ph.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"
        r = ph._check_recovery_workflow("wf_recovery_x", "restore")
        assert r["passed"] is True

    def test_workflow_yaml_error(self, tmp_path):
        p = tmp_path / ".mase" / "workflows.yaml"
        p.parent.mkdir(parents=True)
        with open(p, 'w') as f:
            f.write("not: : : yaml")
        ph.WORKFLOWS_FILE = p
        r = ph._check_recovery_workflow("wf_recovery_x", "x")
        assert r["passed"] is False
        assert "error" in r["detail"]


# ─────────────────────────────────────────────────────────────────────
# _check_yaml_loads (T6)
# ─────────────────────────────────────────────────────────────────────
class TestCheckYamlLoads:
    def test_valid_yaml_with_workflows(self, tmp_path):
        _write_workflows(tmp_path, {"task_workflows": {
            "wf_recovery_immune": {"steps": []},
            "wf_recovery_x": {"steps": []},
        }})
        ph.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"
        r = ph._check_yaml_loads()
        assert r["passed"] is True
        assert "2 task_workflows" in r["detail"]
        assert "2 recovery" in r["detail"]

    def test_empty_workflows(self, tmp_path):
        _write_workflows(tmp_path, {"task_workflows": {}})
        ph.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"
        r = ph._check_yaml_loads()
        # len(twfs) > 0 is False → passed=False
        assert r["passed"] is False
        assert "0 task_workflows" in r["detail"]

    def test_yaml_error(self, tmp_path):
        p = tmp_path / ".mase" / "workflows.yaml"
        p.parent.mkdir(parents=True)
        with open(p, 'w') as f:
            f.write("invalid: : :\n  broken:")
        ph.WORKFLOWS_FILE = p
        r = ph._check_yaml_loads()
        assert r["passed"] is False
        assert "yaml parse error" in r["detail"]


# ─────────────────────────────────────────────────────────────────────
# _check_workflow_count (T2)
# ─────────────────────────────────────────────────────────────────────
class TestCheckWorkflowCount:
    def test_exactly_5_recovery(self, tmp_path):
        _write_workflows(tmp_path, {"task_workflows": {
            f"wf_recovery_{n}": {"steps": []}
            for n in ["immune", "checkpoint", "defib", "safezone", "timeline"]
        }})
        ph.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"
        r = ph._check_workflow_count()
        assert r["passed"] is True
        assert "5/5" in r["detail"]

    def test_too_few_recovery(self, tmp_path):
        _write_workflows(tmp_path, {"task_workflows": {
            "wf_recovery_immune": {"steps": []},
            "wf_recovery_x": {"steps": []},
        }})
        ph.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"
        r = ph._check_workflow_count()
        assert r["passed"] is False
        assert "2/5" in r["detail"]

    def test_too_many_recovery(self, tmp_path):
        _write_workflows(tmp_path, {"task_workflows": {
            f"wf_recovery_{n}": {"steps": []}
            for n in ["a", "b", "c", "d", "e", "f"]
        }})
        ph.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"
        r = ph._check_workflow_count()
        assert r["passed"] is False
        assert "6/5" in r["detail"]

    def test_yaml_error(self, tmp_path):
        p = tmp_path / ".mase" / "workflows.yaml"
        p.parent.mkdir(parents=True)
        with open(p, 'w') as f:
            f.write("not: : : yaml: :")
        ph.WORKFLOWS_FILE = p
        r = ph._check_workflow_count()
        assert r["passed"] is False
        assert "error" in r["detail"]


# ─────────────────────────────────────────────────────────────────────
# _check_workflow_exists (T1)
# ─────────────────────────────────────────────────────────────────────
class TestCheckWorkflowExists:
    def test_found(self, tmp_path):
        _write_workflows(tmp_path, {"task_workflows": {
            "wf_recovery_immune": {"steps": []},
        }})
        ph.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"
        r = ph._check_workflow_exists("wf_recovery_immune")
        assert r["passed"] is True
        assert r["detail"] == "found"

    def test_missing(self, tmp_path):
        _write_workflows(tmp_path, {"task_workflows": {}})
        ph.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"
        r = ph._check_workflow_exists("wf_recovery_immune")
        assert r["passed"] is False
        assert r["detail"] == "missing"

    def test_yaml_error(self, tmp_path):
        p = tmp_path / ".mase" / "workflows.yaml"
        p.parent.mkdir(parents=True)
        with open(p, 'w') as f:
            f.write("invalid: : yaml: :")
        ph.WORKFLOWS_FILE = p
        r = ph._check_workflow_exists("wf_recovery_immune")
        assert r["passed"] is False
        assert "error" in r["detail"]


# ─────────────────────────────────────────────────────────────────────
# run (entry point)
# ─────────────────────────────────────────────────────────────────────
class TestRun:
    def test_run_all_7_checks(self, tmp_path):
        # Build a complete valid setup
        _write_workflows(tmp_path, {"task_workflows": {
            "wf_recovery_immune": {"steps": [
                {"cmd": "echo step"},
            ]},
            "wf_recovery_checkpoint": {"steps": [
                {"cmd": "echo restore checkpoint"},
            ]},
            "wf_recovery_defib": {"steps": [
                {"cmd": "echo defib now"},
            ]},
            "wf_recovery_safezone": {"steps": [
                {"cmd": "echo safezone"},
            ]},
            "wf_recovery_timeline": {"steps": [
                {"cmd": "echo timeline"},
            ]},
        }})
        r = ph.run(tmp_path)
        assert r["title"] == "Phoenix Fixes (T1-T7)"
        assert len(r["checks"]) == 7
        ids = [c["id"] for c in r["checks"]]
        assert ids == ["T1", "T2", "T3", "T4", "T5", "T6", "T7"]
        # T1 should pass (immune exists)
        assert r["checks"][0]["passed"] is True
        assert r["checks"][1]["passed"] is True  # 5 recovery
        # T3-T5, T7 should pass (keywords present)
        for c in r["checks"][2:]:
            if c["id"] in ("T3", "T4", "T5", "T7"):
                assert c["passed"] is True
        # T6 yaml loads
        assert r["checks"][5]["passed"] is True
        assert r["passed"] >= 6
        assert r["failed"] <= 1
        assert "duration_s" in r

    def test_run_missing_recovery(self, tmp_path):
        # Empty workflows → T1 fails (immune missing), T2 fails
        _write_workflows(tmp_path, {"task_workflows": {}})
        r = ph.run(tmp_path)
        assert r["failed"] >= 2

    def test_run_with_real_repo(self):
        # Use real workspace to exercise the full run path
        real_ws = REPO_ROOT
        r = ph.run(real_ws)
        assert r["title"] == "Phoenix Fixes (T1-T7)"
        assert len(r["checks"]) == 7
