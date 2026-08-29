"""
test_r110302_pre_check_phoenix.py — R110-302 Coverage Sprint for
tools/pre_check_lib/phoenix.py.

Target: tools/pre_check_lib/phoenix.py (169 lines, 62 stmts).

Pattern: see test_r110302_pre_check_german.py — import tool as a library,
exercise each function with comprehensive branch coverage.

Branch map for phoenix.py:

  _check_recovery_workflow(wf_name, step_keyword) (lines 25-54):
    - workflow not found in task_workflows           → passed=False, "workflow X not found"
    - workflow found + has step with keyword in cmd  → passed=True, "N steps"
    - workflow found + no step with keyword          → passed=False, "no cmd with 'kw' (step-ids: ...)"
    - exception (file missing, bad yaml, etc.)       → passed=False, "error: <e>"

  _check_yaml_loads() (lines 57-68):
    - yaml valid + task_workflows populated          → passed=True, "N task_workflows, M recovery"
    - yaml valid + task_workflows empty              → passed=False, "0 task_workflows, 0 recovery"
    - exception                                      → passed=False, "yaml parse error: <e>"

  _check_workflow_count() (lines 71-82):
    - exactly 5 recovery workflows                   → passed=True, "5/5 recovery workflows: ..."
    - not 5 recovery workflows                       → passed=False, "X/5 recovery workflows: ..."
    - exception                                      → passed=False, "error: <e>"

  _check_workflow_exists(name) (lines 85-95):
    - workflow present                               → passed=True, "found"
    - workflow missing                               → passed=False, "missing"
    - exception                                      → passed=False, "error: <e>"

  run(workspace) (lines 98-169):
    - WORKFLOWS_FILE exists at ".mase/workflows.yaml" after chdir  → uses it directly
    - WORKFLOWS_FILE does NOT exist, falls back to workspace/.mase/workflows.yaml
    - aggregates all 7 checks into final dict

Note: this file has NO `if __name__ == "__main__":` block, so no
subprocess/runpy tests are needed. All 62 stmts are reachable via
direct module imports + WORKFLOWS_FILE monkeypatching.

Total: ~20 tests covering all branches.
"""
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOLS_DIR = REPO_ROOT / "tools"


def _import_tool():
    """Import phoenix as a library, return the module.

    Inserts the `tools/` dir onto sys.path so `pre_check_lib.phoenix`
    resolves via the package __init__.py.

    The module sets `WORKFLOWS_FILE = Path(".mase/workflows.yaml")` at
    module load time. We monkeypatch this in every test to point at a
    tmp_path-controlled file so the tests are hermetic.
    """
    sys.path.insert(0, str(TOOLS_DIR))
    if "pre_check_lib.phoenix" in sys.modules:
        del sys.modules["pre_check_lib.phoenix"]
    if "pre_check_lib" in sys.modules:
        del sys.modules["pre_check_lib"]
    from pre_check_lib import phoenix
    return phoenix


def _write_workflows(tmp_path: Path, payload: dict) -> Path:
    """Write a workflows.yaml under tmp_path/.mase/ and return the path."""
    mase_dir = tmp_path / ".mase"
    mase_dir.mkdir(parents=True, exist_ok=True)
    wf_path = mase_dir / "workflows.yaml"
    with open(wf_path, "w") as f:
        yaml.dump(payload, f, default_flow_style=False)
    return wf_path


# ─────────────────────────────────────────────────────────────────────
# _check_recovery_workflow() — workflow not found
# ─────────────────────────────────────────────────────────────────────

def test_check_recovery_workflow_not_found(tmp_path):
    """When wf_name is not in task_workflows → passed=False, 'not found'."""
    mod = _import_tool()
    _write_workflows(tmp_path, {
        "task_workflows": {
            "wf_other": {"steps": [{"cmd": "echo hi"}]},
        }
    })
    mod.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"

    result = mod._check_recovery_workflow("wf_recovery_checkpoint", "restore")

    assert result["passed"] is False
    assert "workflow wf_recovery_checkpoint not found" in result["detail"]


# ─────────────────────────────────────────────────────────────────────
# _check_recovery_workflow() — passed (has step with keyword)
# ─────────────────────────────────────────────────────────────────────

def test_check_recovery_workflow_passed_when_cmd_has_keyword(tmp_path):
    """Workflow has a step with keyword in cmd → passed=True, 'N steps'."""
    mod = _import_tool()
    _write_workflows(tmp_path, {
        "task_workflows": {
            "wf_recovery_checkpoint": {
                "steps": [
                    {"id": "step1", "cmd": "echo 'starting'"},
                    {"id": "step2", "cmd": "python3 restore_data.py"},
                    {"id": "step3", "cmd": "echo 'done'"},
                ]
            },
        }
    })
    mod.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"

    result = mod._check_recovery_workflow("wf_recovery_checkpoint", "restore")

    assert result["passed"] is True
    assert "3 steps" in result["detail"]


def test_check_recovery_workflow_passed_with_keyword_case_insensitive(tmp_path):
    """The keyword is matched in lowercase of cmd → case-insensitive match.

    `_check_recovery_workflow` uses `step_keyword in str(s.get('cmd','')).lower()`,
    so uppercase keywords in cmd still match because we lower the cmd string.
    """
    mod = _import_tool()
    _write_workflows(tmp_path, {
        "task_workflows": {
            "wf_recovery_timeline": {
                "steps": [
                    {"id": "step1", "cmd": "python3 Build_Timeline.py"},
                ]
            },
        }
    })
    mod.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"

    # The lookup keyword "timeline" is checked against cmd.lower() = "build_timeline.py"
    result = mod._check_recovery_workflow("wf_recovery_timeline", "timeline")

    assert result["passed"] is True
    assert "1 steps" in result["detail"]


# ─────────────────────────────────────────────────────────────────────
# _check_recovery_workflow() — failed (workflow exists, no step with keyword)
# ─────────────────────────────────────────────────────────────────────

def test_check_recovery_workflow_failed_no_keyword_in_cmd(tmp_path):
    """Workflow exists but no step's cmd contains the keyword → passed=False
    with detail showing the step-ids.
    """
    mod = _import_tool()
    _write_workflows(tmp_path, {
        "task_workflows": {
            "wf_recovery_defib": {
                "steps": [
                    {"id": "alpha", "cmd": "echo 'start'"},
                    {"id": "beta", "cmd": "python3 do_work.py"},
                    {"id": "gamma", "cmd": "echo 'end'"},
                ]
            },
        }
    })
    mod.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"

    result = mod._check_recovery_workflow("wf_recovery_defib", "defib")

    assert result["passed"] is False
    assert "no cmd with 'defib'" in result["detail"]
    assert "step-ids:" in result["detail"]
    # All step-ids should be listed
    assert "alpha" in result["detail"]
    assert "beta" in result["detail"]
    assert "gamma" in result["detail"]


def test_check_recovery_workflow_failed_no_keyword_with_missing_step_ids(tmp_path):
    """Steps without `id` key → uses '?' as placeholder in the step-ids list."""
    mod = _import_tool()
    _write_workflows(tmp_path, {
        "task_workflows": {
            "wf_recovery_safezone": {
                "steps": [
                    {"cmd": "echo 'no id here'"},
                ]
            },
        }
    })
    mod.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"

    result = mod._check_recovery_workflow("wf_recovery_safezone", "safezone")

    assert result["passed"] is False
    assert "?" in result["detail"]


# ─────────────────────────────────────────────────────────────────────
# _check_recovery_workflow() — exception branch
# ─────────────────────────────────────────────────────────────────────

def test_check_recovery_workflow_exception_on_missing_file(tmp_path):
    """File missing → open() raises → caught by except branch."""
    mod = _import_tool()
    mod.WORKFLOWS_FILE = tmp_path / "does_not_exist.yaml"

    result = mod._check_recovery_workflow("wf_recovery_checkpoint", "restore")

    assert result["passed"] is False
    assert "error:" in result["detail"]


def test_check_recovery_workflow_exception_on_invalid_yaml(tmp_path):
    """Bad yaml → yaml.safe_load raises → caught by except branch."""
    mod = _import_tool()
    bad_path = tmp_path / "bad.yaml"
    bad_path.write_text("a: b\n  c: d\n e: f\n:bad")
    mod.WORKFLOWS_FILE = bad_path

    result = mod._check_recovery_workflow("wf_recovery_timeline", "timeline")

    assert result["passed"] is False
    assert "error:" in result["detail"]


# ─────────────────────────────────────────────────────────────────────
# _check_yaml_loads() — passed branch (task_workflows populated)
# ─────────────────────────────────────────────────────────────────────

def test_check_yaml_loads_passed_when_task_workflows_populated(tmp_path):
    """Yaml valid + task_workflows non-empty → passed=True with counts."""
    mod = _import_tool()
    _write_workflows(tmp_path, {
        "task_workflows": {
            "wf_recovery_immune": {"steps": [{"cmd": "echo 'a'"}]},
            "wf_recovery_checkpoint": {"steps": [{"cmd": "echo 'b'"}]},
            "wf_other": {"steps": [{"cmd": "echo 'c'"}]},
        }
    })
    mod.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"

    result = mod._check_yaml_loads()

    assert result["passed"] is True
    assert "3 task_workflows" in result["detail"]
    assert "2 recovery" in result["detail"]


# ─────────────────────────────────────────────────────────────────────
# _check_yaml_loads() — failed branch (task_workflows empty)
# ─────────────────────────────────────────────────────────────────────

def test_check_yaml_loads_failed_when_task_workflows_empty(tmp_path):
    """Yaml valid + task_workflows empty → passed=False (0 task_workflows)."""
    mod = _import_tool()
    _write_workflows(tmp_path, {"task_workflows": {}})
    mod.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"

    result = mod._check_yaml_loads()

    assert result["passed"] is False
    assert "0 task_workflows" in result["detail"]
    assert "0 recovery" in result["detail"]


# ─────────────────────────────────────────────────────────────────────
# _check_yaml_loads() — exception branch
# ─────────────────────────────────────────────────────────────────────

def test_check_yaml_loads_exception_on_missing_file(tmp_path):
    """File missing → open() raises → caught by except branch."""
    mod = _import_tool()
    mod.WORKFLOWS_FILE = tmp_path / "does_not_exist.yaml"

    result = mod._check_yaml_loads()

    assert result["passed"] is False
    assert "yaml parse error:" in result["detail"]


def test_check_yaml_loads_exception_on_invalid_yaml(tmp_path):
    """Invalid yaml → yaml.safe_load raises → caught by except branch."""
    mod = _import_tool()
    bad_path = tmp_path / "bad.yaml"
    bad_path.write_text("not: valid: yaml: at: all")
    mod.WORKFLOWS_FILE = bad_path

    result = mod._check_yaml_loads()

    assert result["passed"] is False
    assert "yaml parse error:" in result["detail"]


# ─────────────────────────────────────────────────────────────────────
# _check_workflow_count() — passed branch (exactly 5)
# ─────────────────────────────────────────────────────────────────────

def test_check_workflow_count_passed_with_exactly_5_recovery(tmp_path):
    """Exactly 5 wf_recovery_* workflows → passed=True."""
    mod = _import_tool()
    _write_workflows(tmp_path, {
        "task_workflows": {
            "wf_recovery_immune": {"steps": []},
            "wf_recovery_checkpoint": {"steps": []},
            "wf_recovery_defib": {"steps": []},
            "wf_recovery_safezone": {"steps": []},
            "wf_recovery_timeline": {"steps": []},
            "wf_other": {"steps": []},  # non-recovery, not counted
        }
    })
    mod.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"

    result = mod._check_workflow_count()

    assert result["passed"] is True
    assert "5/5 recovery workflows" in result["detail"]
    # All 5 names should be listed (sorted)
    assert "wf_recovery_immune" in result["detail"]
    assert "wf_recovery_checkpoint" in result["detail"]
    assert "wf_recovery_defib" in result["detail"]
    assert "wf_recovery_safezone" in result["detail"]
    assert "wf_recovery_timeline" in result["detail"]


# ─────────────────────────────────────────────────────────────────────
# _check_workflow_count() — failed branch (not 5)
# ─────────────────────────────────────────────────────────────────────

def test_check_workflow_count_failed_with_too_few_recovery(tmp_path):
    """3 recovery workflows → passed=False, '3/5 recovery workflows'."""
    mod = _import_tool()
    _write_workflows(tmp_path, {
        "task_workflows": {
            "wf_recovery_a": {"steps": []},
            "wf_recovery_b": {"steps": []},
            "wf_recovery_c": {"steps": []},
        }
    })
    mod.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"

    result = mod._check_workflow_count()

    assert result["passed"] is False
    assert "3/5 recovery workflows" in result["detail"]


def test_check_workflow_count_failed_with_too_many_recovery(tmp_path):
    """7 recovery workflows → passed=False, '7/5 recovery workflows'."""
    mod = _import_tool()
    _write_workflows(tmp_path, {
        "task_workflows": {
            f"wf_recovery_{i}": {"steps": []} for i in range(7)
        }
    })
    mod.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"

    result = mod._check_workflow_count()

    assert result["passed"] is False
    assert "7/5 recovery workflows" in result["detail"]


# ─────────────────────────────────────────────────────────────────────
# _check_workflow_count() — exception branch
# ─────────────────────────────────────────────────────────────────────

def test_check_workflow_count_exception_on_missing_file(tmp_path):
    """File missing → caught by except branch."""
    mod = _import_tool()
    mod.WORKFLOWS_FILE = tmp_path / "does_not_exist.yaml"

    result = mod._check_workflow_count()

    assert result["passed"] is False
    assert "error:" in result["detail"]


# ─────────────────────────────────────────────────────────────────────
# _check_workflow_exists() — passed branch
# ─────────────────────────────────────────────────────────────────────

def test_check_workflow_exists_passed_when_present(tmp_path):
    """Workflow present → passed=True, 'found'."""
    mod = _import_tool()
    _write_workflows(tmp_path, {
        "task_workflows": {
            "wf_recovery_immune": {"steps": []},
        }
    })
    mod.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"

    result = mod._check_workflow_exists("wf_recovery_immune")

    assert result["passed"] is True
    assert result["detail"] == "found"


# ─────────────────────────────────────────────────────────────────────
# _check_workflow_exists() — failed branch (missing)
# ─────────────────────────────────────────────────────────────────────

def test_check_workflow_exists_failed_when_missing(tmp_path):
    """Workflow missing → passed=False, 'missing'."""
    mod = _import_tool()
    _write_workflows(tmp_path, {
        "task_workflows": {
            "wf_other": {"steps": []},
        }
    })
    mod.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"

    result = mod._check_workflow_exists("wf_recovery_immune")

    assert result["passed"] is False
    assert result["detail"] == "missing"


# ─────────────────────────────────────────────────────────────────────
# _check_workflow_exists() — exception branch
# ─────────────────────────────────────────────────────────────────────

def test_check_workflow_exists_exception_on_missing_file(tmp_path):
    """File missing → caught by except branch."""
    mod = _import_tool()
    mod.WORKFLOWS_FILE = tmp_path / "does_not_exist.yaml"

    result = mod._check_workflow_exists("wf_recovery_immune")

    assert result["passed"] is False
    assert "error:" in result["detail"]


# ─────────────────────────────────────────────────────────────────────
# run(workspace) — happy path (workflows.yaml exists, all 7 pass)
# ─────────────────────────────────────────────────────────────────────

def test_run_all_seven_checks_pass(tmp_path):
    """When .mase/workflows.yaml has all 5 recovery workflows with
    correct cmd keywords → all 7 checks pass.
    """
    mod = _import_tool()
    _write_workflows(tmp_path, {
        "task_workflows": {
            "wf_recovery_immune": {"steps": [{"id": "i1", "cmd": "echo 'immune'"}]},
            "wf_recovery_checkpoint": {
                "steps": [{"id": "c1", "cmd": "python3 restore.py"}]
            },
            "wf_recovery_defib": {
                "steps": [{"id": "d1", "cmd": "python3 defibrillate.py"}]
            },
            "wf_recovery_safezone": {
                "steps": [{"id": "s1", "cmd": "python3 safezone.py"}]
            },
            "wf_recovery_timeline": {
                "steps": [{"id": "t1", "cmd": "python3 timeline.py"}]
            },
        }
    })

    result = mod.run(tmp_path)

    assert result["title"] == "Phoenix Fixes (T1-T7)"
    assert result["passed"] == 7
    assert result["failed"] == 0
    assert isinstance(result["duration_s"], (int, float))
    assert len(result["checks"]) == 7
    # Verify all 7 IDs are present in order
    expected_ids = ["T1", "T2", "T3", "T4", "T5", "T6", "T7"]
    actual_ids = [c["id"] for c in result["checks"]]
    assert actual_ids == expected_ids
    # All should be passed
    for c in result["checks"]:
        assert c["passed"] is True
    # Verify T1-T7 names
    assert result["checks"][0]["name"] == "wf_recovery_immune exists"
    assert result["checks"][1]["name"] == "5 recovery workflows exist (immune + 4 new)"
    assert result["checks"][2]["name"] == "recovery_checkpoint has restore-step"
    assert result["checks"][3]["name"] == "recovery_defib has defibrillate-step"
    assert result["checks"][4]["name"] == "recovery_safezone has safezone-step"
    assert result["checks"][5]["name"] == "workflows.yaml parses + 5 recovery load"
    assert result["checks"][6]["name"] == "recovery_timeline has timeline-step"
    # WORKFLOWS_FILE was updated to the resolved path
    assert mod.WORKFLOWS_FILE == (tmp_path / ".mase" / "workflows.yaml").resolve()


# ─────────────────────────────────────────────────────────────────────
# run(workspace) — mixed results (some pass, some fail)
# ─────────────────────────────────────────────────────────────────────

def test_run_mixed_pass_and_fail(tmp_path):
    """When some checks pass and some fail → counts are correct."""
    mod = _import_tool()
    _write_workflows(tmp_path, {
        "task_workflows": {
            "wf_recovery_immune": {"steps": [{"id": "i1", "cmd": "echo 'immune'"}]},
            # Only 1 recovery, but need 5 → T2 fails
            "wf_recovery_checkpoint": {
                "steps": [{"id": "c1", "cmd": "python3 no_keyword.py"}]  # no 'restore' → T3 fails
            },
            "wf_recovery_defib": {
                "steps": [{"id": "d1", "cmd": "python3 defibrillate.py"}]  # has 'defib' → T4 passes
            },
            # No recovery_safezone → T5 fails (workflow not found)
            "wf_recovery_timeline": {
                "steps": [{"id": "t1", "cmd": "python3 timeline.py"}]  # has 'timeline' → T7 passes
            },
        }
    })

    result = mod.run(tmp_path)

    # T1: wf_recovery_immune exists → pass
    assert result["checks"][0]["passed"] is True
    # T2: 4 recovery workflows ≠ 5 → fail
    assert result["checks"][1]["passed"] is False
    # T3: checkpoint has 'no_keyword' but need 'restore' → fail
    assert result["checks"][2]["passed"] is False
    # T4: defib has 'defibrillate' → pass
    assert result["checks"][3]["passed"] is True
    # T5: safezone not found → fail
    assert result["checks"][4]["passed"] is False
    # T6: yaml valid + 4 task_workflows → pass
    assert result["checks"][5]["passed"] is True
    # T7: timeline has 'timeline' → pass
    assert result["checks"][6]["passed"] is True
    # Counts: 4 passed, 3 failed
    assert result["passed"] == 4
    assert result["failed"] == 3


# ─────────────────────────────────────────────────────────────────────
# run(workspace) — fallback branch when .mase/workflows.yaml missing
# ─────────────────────────────────────────────────────────────────────

def test_run_fallback_when_workflows_file_missing_in_workspace(tmp_path):
    """When `.mase/workflows.yaml` does NOT exist in the workspace after
    chdir, run() falls back to setting WORKFLOWS_FILE to
    `workspace / ".mase" / "workflows.yaml"` (the explicit fallback).

    The fallback path is the same as the relative one in this case, so
    the helpers will fail to open it → all 7 checks report error and
    the run() result has failed=7, passed=0.

    This test specifically exists to make the
    `if not WORKFLOWS_FILE.exists():` branch and the fallback
    assignment at line 107 both execute.
    """
    mod = _import_tool()
    # Empty workspace — NO .mase/workflows.yaml exists
    empty_workspace = tmp_path / "empty_ws"
    empty_workspace.mkdir()

    result = mod.run(empty_workspace)

    # All checks hit their `except Exception` branch
    assert result["passed"] == 0
    assert result["failed"] == 7
    for c in result["checks"]:
        assert c["passed"] is False
        assert "error:" in c["detail"]
    # WORKFLOWS_FILE was reassigned to the fallback path
    assert mod.WORKFLOWS_FILE == empty_workspace / ".mase" / "workflows.yaml"
