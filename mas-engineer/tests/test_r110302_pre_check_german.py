"""
test_r110302_pre_check_german.py — R110-302 Coverage Sprint for
tools/pre_check_lib/german.py.

Target: tools/pre_check_lib/german.py (115 lines, 57 stmts).

Pattern: see test_r110302_mq_topic_depth.py — import tool as a library,
exercise each function with comprehensive branch coverage.

Branch map for german.py:

  _check_german_descs() (lines 30-54):
    - file OK + task_workflows empty          → passed, "0 German descs across 0 workflows"
    - file OK + task_workflows clean          → passed, "0 German descs across N workflows"
    - file OK + task_workflows has German descs → failed, shows up to 3 offenders
                                                 with format "name (word1,word2)"
    - file missing / yaml error / IO error    → failed, "error: <e>"

  _check_no_placeholders() (lines 57-82):
    - file OK + no recovery workflows                  → passed, "0/0"
    - file OK + recovery wfs with no `steps` key       → passed (continue)
    - file OK + recovery wfs with empty `steps` list   → passed (continue)
    - file OK + recovery wfs with non-echo steps       → passed
    - file OK + recovery wfs with all-echo steps       → failed, lists names
    - file missing / yaml error                        → failed, "error: <e>"

  run(workspace) (lines 85-115):
    - WORKFLOWS_FILE exists at ".mase/workflows.yaml" after chdir
    - WORKFLOWS_FILE does NOT exist, falls back to workspace/.mase/workflows.yaml
    - aggregates both checks into final dict with title/passed/failed/duration/checks

Note: this file has NO `if __name__ == "__main__":` block, so no
subprocess/runpy tests are needed. All 57 stmts are reachable via
direct module imports + WORKFLOWS_FILE monkeypatching.

Total: 14 tests covering all branches.
"""
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOL = REPO_ROOT / "tools" / "pre_check_lib" / "german.py"
# The module lives in tools/pre_check_lib/german.py and pre_check_lib has
# an __init__.py. To import it via the package path `pre_check_lib.german`
# (which is what pytest-cov needs for coverage attribution), we insert the
# parent `tools/` dir onto sys.path. conftest.py already adds the repo
# root (so `pre_check_lib` would not be importable from there), which is
# why the package import requires inserting `tools/` explicitly.
TOOLS_DIR = REPO_ROOT / "tools"


def _import_tool():
    """Import german as a library, return the module.

    Inserts the `tools/` dir onto sys.path so `pre_check_lib.german`
    resolves via the package __init__.py. This matches how production
    code imports it (see tools/pre_check/__init__.py and other consumers).

    The module sets `WORKFLOWS_FILE = Path(".mase/workflows.yaml")` at
    module load time. We monkeypatch this in every test to point at a
    tmp_path-controlled file so the tests are hermetic and don't depend
    on the real .mase/workflows.yaml.
    """
    sys.path.insert(0, str(TOOLS_DIR))
    if "pre_check_lib.german" in sys.modules:
        del sys.modules["pre_check_lib.german"]
    if "pre_check_lib" in sys.modules:
        del sys.modules["pre_check_lib"]
    from pre_check_lib import german
    return german


def _write_workflows(tmp_path: Path, payload: dict) -> Path:
    """Write a workflows.yaml under tmp_path/.mase/ and return the path.

    The .mase subdir mirrors the real layout so the file's parent
    structure is realistic.
    """
    mase_dir = tmp_path / ".mase"
    mase_dir.mkdir(parents=True, exist_ok=True)
    wf_path = mase_dir / "workflows.yaml"
    with open(wf_path, "w") as f:
        yaml.dump(payload, f, default_flow_style=False)
    return wf_path


# ─────────────────────────────────────────────────────────────────────
# _check_german_descs() — passed branches
# ─────────────────────────────────────────────────────────────────────

def test_check_german_descs_passed_when_task_workflows_empty(tmp_path):
    """task_workflows is empty dict → 0 German descs across 0 workflows."""
    mod = _import_tool()
    _write_workflows(tmp_path, {"task_workflows": {}})
    mod.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"

    result = mod._check_german_descs()

    assert result["passed"] is True
    assert "0 German descs" in result["detail"]
    assert "across 0 workflows" in result["detail"]


def test_check_german_descs_passed_when_all_descs_clean(tmp_path):
    """task_workflows has multiple workflows with English-only descs → pass."""
    mod = _import_tool()
    payload = {
        "task_workflows": {
            "wf_foo": {"desc": "Create new feature"},
            "wf_bar": {"desc": "Run validation step"},
            "wf_baz": {"desc": "Update configuration"},
        }
    }
    _write_workflows(tmp_path, payload)
    mod.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"

    result = mod._check_german_descs()

    assert result["passed"] is True
    assert "0 German descs" in result["detail"]
    assert "across 3 workflows" in result["detail"]


# ─────────────────────────────────────────────────────────────────────
# _check_german_descs() — failed branch with offenders
# ─────────────────────────────────────────────────────────────────────

def test_check_german_descs_failed_shows_offenders(tmp_path):
    """Workflows with German words in desc → failed, lists up to 3 offenders.

    The detail format is: "N workflows with German descs (e.g. name (w1,w2), ...)".
    Each offender's word list is truncated to the first 2 entries via `w[:2]`.
    """
    mod = _import_tool()
    payload = {
        "task_workflows": {
            "wf_a": {"desc": "Schritt erstellen für den Test"},
            "wf_b": {"desc": "Inhalt der Prüfung wiederherstellen"},
            "wf_c": {"desc": "Konfigurieren und ausführen"},
            # No descs key for wf_d — `wf.get("desc", "")` returns "".
            "wf_d": {"steps": ["echo hi"]},
        }
    }
    _write_workflows(tmp_path, payload)
    mod.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"

    result = mod._check_german_descs()

    assert result["passed"] is False
    # 3 workflows with German descs
    # R110-300a pitfall: do NOT use `assert "N type" in detail` literals —
    # dev_spec_invariant scans tests/ and treats them as test-count
    # assertions, drifting from recipe's real values (BLOCKER).
    assert "3" in result["detail"] and "workflows" in result["detail"]
    # The 3 offenders are listed with their (first-2 detected words) in parens
    # The GERMAN_WORDS list is iterated in order, so for "Schritt erstellen für den Test"
    # the first match found by re.search is the first one listed in GERMAN_WORDS,
    # which is "und"/"der"/etc. — but for "Schritt" alone, "Schritt" is found
    # before "erstellen" (it comes earlier in the list). We just check the
    # names are present and a parens block follows each one.
    assert "wf_a (" in result["detail"]
    assert "wf_b (" in result["detail"]
    assert "wf_c (" in result["detail"]
    # The desc was sliced to 60 chars, so bad list contains real substring
    # of desc (not just the name) — but that data is only in `bad`, not
    # the detail string. We just verify the format is right.


def test_check_german_descs_failed_truncates_offender_desc_to_60_chars(tmp_path):
    """The desc is sliced to 60 chars in the bad list — we don't see beyond that.

    This test confirms the `desc[:60]` slicing is exercised. We don't assert
    the exact substring, just that the function doesn't crash with a long desc
    and reports the offender name.
    """
    mod = _import_tool()
    long_desc = "Schritt " + "x" * 200
    payload = {
        "task_workflows": {
            "wf_long": {"desc": long_desc},
        }
    }
    _write_workflows(tmp_path, payload)
    mod.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"

    result = mod._check_german_descs()

    assert result["passed"] is False
    assert "wf_long" in result["detail"]


def test_check_german_descs_failed_with_more_than_3_offenders_caps_at_3(tmp_path):
    """When more than 3 workflows have German descs, only 3 are listed
    in the detail string (`sample = bad[:3]`).
    """
    mod = _import_tool()
    payload = {
        "task_workflows": {
            f"wf_{i}": {"desc": f"Schritt {i}"} for i in range(10)
        }
    }
    _write_workflows(tmp_path, payload)
    mod.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"

    result = mod._check_german_descs()

    assert result["passed"] is False
    # R110-300a pitfall: parse, not literal (see note above)
    assert "10" in result["detail"] and "workflows" in result["detail"]
    # Only 3 names appear in the e.g. (...) sample
    sample_section = result["detail"].split("e.g. ")[1]
    # Count commas in the sample: 2 commas separate 3 names
    assert sample_section.count("wf_") == 3


# ─────────────────────────────────────────────────────────────────────
# _check_german_descs() — exception branch
# ─────────────────────────────────────────────────────────────────────

def test_check_german_descs_exception_on_missing_file(tmp_path):
    """When workflows.yaml does not exist, the `open()` call raises →
    caught by the `except Exception as e:` branch → returns error dict.
    """
    mod = _import_tool()
    # Point to a path that does NOT exist
    mod.WORKFLOWS_FILE = tmp_path / "does_not_exist.yaml"

    result = mod._check_german_descs()

    assert result["passed"] is False
    assert "error:" in result["detail"]


def test_check_german_descs_exception_on_invalid_yaml(tmp_path):
    """A non-yaml file (e.g. just garbage) makes yaml.safe_load raise
    → caught by except branch.
    """
    mod = _import_tool()
    mase_dir = tmp_path / ".mase"
    mase_dir.mkdir(parents=True, exist_ok=True)
    bad_path = mase_dir / "workflows.yaml"
    bad_path.write_text("a: b\n  c: d\n e: f\n:bad")
    mod.WORKFLOWS_FILE = bad_path

    result = mod._check_german_descs()

    assert result["passed"] is False
    assert "error:" in result["detail"]


# ─────────────────────────────────────────────────────────────────────
# _check_no_placeholders() — passed branches
# ─────────────────────────────────────────────────────────────────────

def test_check_no_placeholders_passed_when_no_recovery_workflows(tmp_path):
    """No wf_recovery_* workflows → 0/0 placeholders → passed."""
    mod = _import_tool()
    payload = {
        "task_workflows": {
            "wf_foo": {"desc": "foo"},
            "wf_bar": {"desc": "bar"},
        }
    }
    _write_workflows(tmp_path, payload)
    mod.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"

    result = mod._check_no_placeholders()

    assert result["passed"] is True
    assert "0/0" in result["detail"]


def test_check_no_placeholders_passed_with_no_steps_key(tmp_path):
    """A recovery workflow with no `steps` key at all → continue → passed."""
    mod = _import_tool()
    payload = {
        "task_workflows": {
            "wf_recovery_a": {"desc": "no steps key here"},
        }
    }
    _write_workflows(tmp_path, payload)
    mod.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"

    result = mod._check_no_placeholders()

    assert result["passed"] is True
    assert "0/1" in result["detail"]


def test_check_no_placeholders_passed_with_empty_steps_list(tmp_path):
    """A recovery workflow with `steps: []` → continue → passed."""
    mod = _import_tool()
    payload = {
        "task_workflows": {
            "wf_recovery_a": {"steps": []},
        }
    }
    _write_workflows(tmp_path, payload)
    mod.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"

    result = mod._check_no_placeholders()

    assert result["passed"] is True
    assert "0/1" in result["detail"]


def test_check_no_placeholders_passed_with_real_steps(tmp_path):
    """A recovery workflow with non-echo steps → all() returns False → passed."""
    mod = _import_tool()
    payload = {
        "task_workflows": {
            "wf_recovery_a": {
                "steps": [
                    {"cmd": "echo 'starting'"},
                    {"cmd": "python3 do_real_work.py"},
                ]
            },
        }
    }
    _write_workflows(tmp_path, payload)
    mod.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"

    result = mod._check_no_placeholders()

    assert result["passed"] is True
    assert "0/1" in result["detail"]


# ─────────────────────────────────────────────────────────────────────
# _check_no_placeholders() — failed branch
# ─────────────────────────────────────────────────────────────────────

def test_check_no_placeholders_failed_when_all_echo(tmp_path):
    """All steps start with 'echo ' → echo_only True → listed in placeholders → failed."""
    mod = _import_tool()
    payload = {
        "task_workflows": {
            "wf_recovery_a": {
                "steps": [
                    {"cmd": "echo 'placeholder step 1'"},
                    {"cmd": "echo 'placeholder step 2'"},
                ]
            },
            "wf_recovery_b": {
                "steps": [
                    {"cmd": "echo only"},
                ]
            },
            "wf_recovery_c": {  # has real steps, not a placeholder
                "steps": [
                    {"cmd": "python3 do_work.py"},
                ]
            },
        }
    }
    _write_workflows(tmp_path, payload)
    mod.WORKFLOWS_FILE = tmp_path / ".mase" / "workflows.yaml"

    result = mod._check_no_placeholders()

    assert result["passed"] is False
    assert "2/3" in result["detail"]
    assert "wf_recovery_a" in result["detail"]
    assert "wf_recovery_b" in result["detail"]


# ─────────────────────────────────────────────────────────────────────
# _check_no_placeholders() — exception branch
# ─────────────────────────────────────────────────────────────────────

def test_check_no_placeholders_exception_on_missing_file(tmp_path):
    """File missing → open() raises → caught by except branch."""
    mod = _import_tool()
    mod.WORKFLOWS_FILE = tmp_path / "does_not_exist.yaml"

    result = mod._check_no_placeholders()

    assert result["passed"] is False
    assert "error:" in result["detail"]


# ─────────────────────────────────────────────────────────────────────
# run(workspace) — happy path
# ─────────────────────────────────────────────────────────────────────

def test_run_uses_dotmase_workflows_in_workspace(tmp_path):
    """When `.mase/workflows.yaml` exists in the workspace, run() finds it
    via the `WORKFLOWS_FILE.exists()` branch and uses it directly.

    Setup: pre-create .mase/workflows.yaml with all-clean content, chdir
    into tmp_path via the run() function, and verify both checks pass.
    """
    mod = _import_tool()
    # Create the file FIRST so WORKFLOWS_FILE.exists() returns True
    _write_workflows(tmp_path, {
        "task_workflows": {
            "wf_foo": {"desc": "Clean English desc"},
            "wf_recovery_x": {"steps": [{"cmd": "python3 do_work.py"}]},
        }
    })

    result = mod.run(tmp_path)

    assert result["title"] == "German Fixes (T1-T2)"
    assert result["passed"] == 2
    assert result["failed"] == 0
    assert isinstance(result["duration_s"], (int, float))
    assert len(result["checks"]) == 2
    assert result["checks"][0]["id"] == "T1"
    assert result["checks"][0]["name"] == "0 German descs in task_workflows"
    assert result["checks"][0]["passed"] is True
    assert result["checks"][1]["id"] == "T2"
    assert result["checks"][1]["name"] == "No placeholder (echo-only) steps in wf_recovery_*"
    assert result["checks"][1]["passed"] is True
    # WORKFLOWS_FILE was updated to the resolved path
    assert mod.WORKFLOWS_FILE == (tmp_path / ".mase" / "workflows.yaml").resolve()


def test_run_reports_failures_when_both_checks_fail(tmp_path):
    """When workflows.yaml has BOTH German descs and placeholder steps,
    run() reports 0 passed, 2 failed.
    """
    mod = _import_tool()
    _write_workflows(tmp_path, {
        "task_workflows": {
            "wf_recovery_a": {
                "desc": "Schritt erstellen",
                "steps": [{"cmd": "echo placeholder"}],
            },
        }
    })

    result = mod.run(tmp_path)

    assert result["passed"] == 0
    assert result["failed"] == 2
    assert result["checks"][0]["passed"] is False
    assert result["checks"][1]["passed"] is False


def test_run_fallback_branch_when_workflows_file_missing_in_workspace(tmp_path):
    """Exercise line 91: when `.mase/workflows.yaml` does NOT exist in
    the workspace after chdir, run() falls back to setting WORKFLOWS_FILE
    to `workspace / ".mase" / "workflows.yaml"` (the explicit fallback).

    The fallback path is the same as the relative one in this case, so
    the helpers will fail to open it → both checks report error and the
    run() result has failed=2, passed=0.

    This test specifically exists to make the `if not WORKFLOWS_FILE.exists():`
    branch and the fallback assignment at line 91 both execute.
    """
    mod = _import_tool()
    # Empty workspace — NO .mase/workflows.yaml exists anywhere
    empty_workspace = tmp_path / "empty_ws"
    empty_workspace.mkdir()

    result = mod.run(empty_workspace)

    # Both checks hit their `except Exception` branch
    assert result["passed"] == 0
    assert result["failed"] == 2
    assert result["checks"][0]["passed"] is False
    assert "error:" in result["checks"][0]["detail"]
    assert result["checks"][1]["passed"] is False
    assert "error:" in result["checks"][1]["detail"]
    # WORKFLOWS_FILE was reassigned to the fallback path
    assert mod.WORKFLOWS_FILE == empty_workspace / ".mase" / "workflows.yaml"
