"""R110-465 — coverage-push r9: tools/pre_check_lib/german.py 0% → 100%

German Fixes pre-check profile (T1-T2). Validates that workflows.yaml
has no German descs and no placeholder (echo-only) steps in
wf_recovery_*.

Targets:
- _check_german_descs(): scans task_workflows for German words in desc
  - 0 found → passed=True
  - >=1 found → passed=False with up-to-3 offender sample (name, first 2
    words)
  - yaml error → passed=False "error: ..."

- _check_no_placeholders(): wf_recovery_* workflows
  - empty/missing steps → skip
  - all steps start with "echo " → placeholder
  - 0 placeholders → passed=True "0/N"
  - some → passed=False "M/N placeholders: ..."

- run(workspace):
  - os.chdir to workspace
  - sets WORKFLOWS_FILE to .mase/workflows.yaml (resolved); if missing
    falls back to workspace/.mase/workflows.yaml
  - runs both checks, returns {title, passed, failed, duration_s, checks}
"""

import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.pre_check_lib import german as g  # noqa: E402


def _write_workflows(workspace, content):
    p = workspace / ".mase" / "workflows.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w') as f:
        yaml.safe_dump(content, f)
    return p


# ─────────────────────────────────────────────────────────────────────
# _check_german_descs (T1)
# ─────────────────────────────────────────────────────────────────────
class TestCheckGermanDescs:
    def test_no_german(self, tmp_path):
        _write_workflows(tmp_path, {
            "task_workflows": {
                "wf1": {"desc": "english clean desc",
                        "steps": [{"cmd": "true"}]},
            },
        })
        # Reset module-global to point at our test file
        g.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"
        r = g._check_german_descs()
        assert r["passed"] is True
        assert "0 German" in r["detail"]
        assert "1 workflows" in r["detail"]

    def test_with_german_words(self, tmp_path):
        # "Schritt" is in the GERMAN_WORDS list
        _write_workflows(tmp_path, {
            "task_workflows": {
                "wf_bad": {"desc": "Schritt 1 für Setup",
                           "steps": []},
            },
        })
        g.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"
        r = g._check_german_descs()
        assert r["passed"] is False
        assert "1 workflows" in r["detail"]
        assert "wf_bad" in r["detail"]

    def test_multiple_offenders_sample_3(self, tmp_path):
        _write_workflows(tmp_path, {
            "task_workflows": {
                f"wf_{i}": {"desc": "Schritt setup",
                            "steps": []}
                for i in range(5)
            },
        })
        g.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"
        r = g._check_german_descs()
        assert r["passed"] is False
        # 5 workflows with German descs
        assert "5 workflows" in r["detail"]

    def test_yaml_error(self, tmp_path):
        p = tmp_path / ".mase" / "workflows.yaml"
        p.parent.mkdir(parents=True)
        with open(p, 'w') as f:
            f.write("invalid: : :\n  broken:")
        g.WORKFLOWS_FILE = p
        r = g._check_german_descs()
        assert r["passed"] is False
        assert "error" in r["detail"]

    def test_case_insensitive(self, tmp_path):
        # "SCHRITT" should still match
        _write_workflows(tmp_path, {
            "task_workflows": {
                "wf_upper": {"desc": "SCHRITT eins",
                             "steps": []},
            },
        })
        g.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"
        r = g._check_german_descs()
        assert r["passed"] is False


# ─────────────────────────────────────────────────────────────────────
# _check_no_placeholders (T2)
# ─────────────────────────────────────────────────────────────────────
class TestCheckNoPlaceholders:
    def test_no_recovery_workflows(self, tmp_path):
        _write_workflows(tmp_path, {
            "task_workflows": {
                "wf_other": {"desc": "x", "steps": []},
            },
        })
        g.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"
        r = g._check_no_placeholders()
        assert r["passed"] is True
        assert "0/0" in r["detail"]

    def test_recovery_with_real_steps(self, tmp_path):
        _write_workflows(tmp_path, {
            "task_workflows": {
                "wf_recovery_x": {"desc": "x", "steps": [
                    {"cmd": "echo 'before'"},
                    {"cmd": "python3 real_work.py"},
                ]},
            },
        })
        g.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"
        r = g._check_no_placeholders()
        assert r["passed"] is True
        assert "0/1" in r["detail"]

    def test_recovery_with_placeholder(self, tmp_path):
        _write_workflows(tmp_path, {
            "task_workflows": {
                "wf_recovery_y": {"desc": "x", "steps": [
                    {"cmd": "echo '1'"},
                    {"cmd": "echo '2'"},
                ]},
            },
        })
        g.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"
        r = g._check_no_placeholders()
        assert r["passed"] is False
        assert "1/1" in r["detail"]
        assert "wf_recovery_y" in r["detail"]

    def test_recovery_empty_steps_skip(self, tmp_path):
        # Empty steps → continue (not counted as placeholder)
        _write_workflows(tmp_path, {
            "task_workflows": {
                "wf_recovery_empty": {"desc": "x", "steps": []},
            },
        })
        g.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"
        r = g._check_no_placeholders()
        assert r["passed"] is True

    def test_recovery_no_steps_key(self, tmp_path):
        # No steps key at all → continue (not placeholder)
        _write_workflows(tmp_path, {
            "task_workflows": {
                "wf_recovery_nostep": {"desc": "x"},
            },
        })
        g.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"
        r = g._check_no_placeholders()
        assert r["passed"] is True

    def test_yaml_error(self, tmp_path):
        p = tmp_path / ".mase" / "workflows.yaml"
        p.parent.mkdir(parents=True)
        with open(p, 'w') as f:
            f.write("not: : yaml: :")
        g.WORKFLOWS_FILE = p
        r = g._check_no_placeholders()
        assert r["passed"] is False
        assert "error" in r["detail"]

    def test_mixed_recovery(self, tmp_path):
        # Some placeholder, some real
        _write_workflows(tmp_path, {
            "task_workflows": {
                "wf_recovery_real": {"desc": "x", "steps": [
                    {"cmd": "python3 work.py"},
                ]},
                "wf_recovery_placeholder": {"desc": "x", "steps": [
                    {"cmd": "echo x"},
                ]},
            },
        })
        g.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"
        r = g._check_no_placeholders()
        assert r["passed"] is False
        assert "1/2" in r["detail"]


# ─────────────────────────────────────────────────────────────────────
# run (entry point)
# ─────────────────────────────────────────────────────────────────────
class TestRun:
    def test_run_all_pass(self, tmp_path):
        _write_workflows(tmp_path, {
            "task_workflows": {
                "wf_recovery_x": {"desc": "clean desc", "steps": [
                    {"cmd": "echo x"},
                    {"cmd": "python3 work.py"},
                ]},
                "wf_other": {"desc": "english only", "steps": []},
            },
        })
        r = g.run(tmp_path)
        assert r["title"] == "German Fixes (T1-T2)"
        assert r["passed"] == 2
        assert r["failed"] == 0
        assert len(r["checks"]) == 2
        assert r["checks"][0]["id"] == "T1"
        assert r["checks"][1]["id"] == "T2"
        assert "duration_s" in r

    def test_run_chdir_and_file_fallback(self, tmp_path):
        # No .mase/workflows.yaml in cwd → fall back to
        # workspace/.mase/workflows.yaml
        _write_workflows(tmp_path, {
            "task_workflows": {},
        })
        r = g.run(tmp_path)
        # Should run without FileNotFoundError
        assert "checks" in r

    def test_run_fallback_path_used(self, tmp_path):
        # The cwd inside run() = workspace (because run does os.chdir
        # first). So we need two distinct dirs: cwd (no .mase/) and
        # workspace (has .mase/workflows.yaml). Then line 91 fires.
        empty_cwd = tmp_path / "empty_cwd"
        empty_cwd.mkdir()
        workspace = tmp_path / "ws"
        workspace.mkdir()
        # Write workflows only in workspace, NOT in empty_cwd
        _write_workflows(workspace, {"task_workflows": {}})
        # Run with cwd outside, workspace pointing at the dir with file
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(empty_cwd)
            r = g.run(workspace)
        finally:
            os.chdir(old_cwd)
        assert "checks" in r

    def test_run_with_real_repo_workflows(self):
        # Use real workspace to test the chdir + workflow loading path
        real_ws = REPO_ROOT
        r = g.run(real_ws)
        assert r["title"] == "German Fixes (T1-T2)"
        assert len(r["checks"]) == 2
