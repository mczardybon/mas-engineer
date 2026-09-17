"""
test_r110302_dashboard_prd_template.py — R110-302 Coverage Sprint for
tools/dashboard_prd_template.py.

Target: dashboard_prd_template.py (159 lines, 61 stmts).

Functions and statements we need to cover:

  - _resolve_workspace()      (4 branches: env var valid, env var
                              missing/empty, walk-up finds .mase/dashboards/,
                              walk-up finds nothing → fallback)
  - Module-level constants    (WORKSPACE, DASHBOARD_DIR, STATUS_FILE,
                              SIGNAL_FILE, OUTPUT_FILE) — covered
                              implicitly on import
  - load_data()               (reads STATUS_FILE + SIGNAL_FILE, returns
                              (data, sig))
  - generate_prd(d, sig)      (builds the PRD string from data + sig,
                              writes OUTPUT_FILE, prints to stdout)
  - if __name__ == "__main__": (2 paths: status file missing → sys.exit(1),
                              status present but signal missing → sys.exit(1),
                              both present → generate_prd + sys.exit(0)
                              implicitly)

Pitfall: the module computes WORKSPACE / DASHBOARD_DIR / STATUS_FILE /
SIGNAL_FILE / OUTPUT_FILE at IMPORT TIME (module-level statements, not
function calls). To exercise different branches of _resolve_workspace() we
must (a) set the env var BEFORE import, and (b) re-import the module after
deleting it from sys.modules. This is the same pattern as test_r110302_mq_topic_depth.

Pitfall: the if __name__ == "__main__": block does NOT call sys.exit(0)
explicitly — it just falls off the end. So runpy.run_path() returns None
when both files are present. The "missing status" / "missing signal"
branches do call sys.exit(1) → SystemExit with code=1.

Pitfall: generate_prd() opens OUTPUT_FILE for writing at the end, so we
must make sure DASHBOARD_DIR exists (we can monkeypatch the OUTPUT_FILE
constant to point inside tmp_path).

Total: 11 new tests.
"""
import json
import os
import pathlib
import runpy
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOLS_DIR = REPO_ROOT / "tools"
TOOL = TOOLS_DIR / "dashboard_prd_template.py"


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def _make_full_data():
    """Return a complete synthetic status dict matching the schema that
    generate_prd() expects.

    The real mas-dashboard-status.json in the repo uses a newer schema
    (no `mas`, `framework`, `user_framework`, `history` top-level keys),
    so we have to build our own minimal-but-complete dataset here.
    """
    return {
        "timestamp": "2026-08-29T20:00:00Z",
        "mas": {
            "agents": 14,
            "agents_at_10": 2,
            "prompt_score_avg": 8.7,
            "tools": 42,
            "changes": 17,
            "checkpoints": 5,
            "fleet_active": True,
            "fleet_max_paralll": 4,
            "agent_health": {"healthy": 14, "total": 14},
            "self_improve": {"total_runs": 9, "last_run": "2026-08-29T18:00:00Z"},
            "session_stats": {"total_sessions": 120, "total_cost": 4.21, "active_hours": 38.5},
            "build": {"count": 7, "latest": {"size_kb": 234}},
            "agent_scores": [
                {"name": "sub_mas-agent-guardian", "score": 10.0},
                {"name": "sub_mas-goose-expert", "score": 10.0},
                {"name": "sub_mas-yaml-editor", "score": 9.0},
            ],
            "changes_by_type": {"feature": 12, "fix": 3, "docs": 2},
        },
        "framework": {
            "recipes": {"total": 28, "specialists": 5, "subs": 19, "core": 4},
            "config": {
                "provider": "deepseek",
                "extensions": ["mas-mcp", "mas-im", "mas-guardian"],
            },
        },
        "dispatch": {
            "done": 31, "running": 2, "errors": 1,
            "tree": [
                "R110 (root)",
                "  R110-300 (active)",
                "    R110-302 (running)",
                "  R110-200 (done)",
            ],
        },
        "user_framework": {
            "recipes": 6,
            "workspace": "/tmp/user-ws",
            "detected": True,
        },
        "history": {
            "health_trend": [
                {"time": "t0", "mas": 80, "framework": 75},
                {"time": "t1", "mas": 82, "framework": 76},
                {"time": "t2", "mas": 85, "framework": 78},
            ],
        },
    }


def _make_signal():
    return {"ts": "2026-08-29T20:00:01Z", "extra": "ignored"}


# ─────────────────────────────────────────────────────────────────────
# _resolve_workspace() — 4 branches
# ─────────────────────────────────────────────────────────────────────

def test_resolve_workspace_uses_env_var_when_set(monkeypatch):
    """Branch 1: MAS_WORKSPACE env var set AND points to an existing dir.

    We set the env var BEFORE import and remove the module from
    sys.modules to force a fresh import so the module-level constant
    WORKSPACE is re-evaluated.
    """
    fake_ws = tempfile.mkdtemp()
    monkeypatch.setenv("MAS_WORKSPACE", fake_ws)
    if "dashboard_prd_template" in sys.modules:
        del sys.modules["dashboard_prd_template"]
    sys.path.insert(0, str(TOOLS_DIR))
    import dashboard_prd_template as mod
    assert mod.WORKSPACE == fake_ws
    # Constants derived from WORKSPACE:
    assert mod.DASHBOARD_DIR == os.path.join(fake_ws, ".mase", "dashboards")
    assert mod.STATUS_FILE == os.path.join(
        fake_ws, ".mase", "dashboards", "mas-dashboard-status.json"
    )
    assert mod.SIGNAL_FILE == os.path.join(
        fake_ws, ".mase", "dashboards", "mas-dashboard-signal.json"
    )
    assert mod.OUTPUT_FILE == os.path.join(
        fake_ws, ".mase", "dashboards", "dashboard_prd_current.txt"
    )


def test_resolve_workspace_falls_back_when_env_var_empty(monkeypatch):
    """Branch 2: MAS_WORKSPACE is set but to '' (empty string).

    `_resolve_workspace` treats empty as falsy → falls through to the
    walk-up loop. We run from a tmp dir with NO .mase/dashboards
    ancestor → fallback returns os.path.abspath('.').
    """
    empty_ws = tempfile.mkdtemp()
    monkeypatch.setenv("MAS_WORKSPACE", "")  # explicit empty
    monkeypatch.chdir(empty_ws)
    if "dashboard_prd_template" in sys.modules:
        del sys.modules["dashboard_prd_template"]
    sys.path.insert(0, str(TOOLS_DIR))
    import dashboard_prd_template as mod
    # Neither the env var branch nor the walk-up branch matched, so we
    # get the absolute path of cwd.
    assert mod.WORKSPACE == os.path.abspath(empty_ws)


def test_resolve_workspace_falls_back_when_env_var_invalid(monkeypatch):
    """Branch 2b: MAS_WORKSPACE set to a non-existent path.

    `_resolve_workspace` checks `os.path.isdir(ws)` → False → falls
    through to the walk-up loop. Same fallback as the empty case.
    """
    monkeypatch.setenv("MAS_WORKSPACE", "/definitely/does/not/exist/r110302")
    tmp = tempfile.mkdtemp()
    monkeypatch.chdir(tmp)
    if "dashboard_prd_template" in sys.modules:
        del sys.modules["dashboard_prd_template"]
    sys.path.insert(0, str(TOOLS_DIR))
    import dashboard_prd_template as mod
    assert mod.WORKSPACE == os.path.abspath(tmp)


def test_resolve_workspace_walks_up_to_find_mase(monkeypatch):
    """Branch 3: No valid MAS_WORKSPACE; some ancestor has .mase/dashboards/.

    We create a tmp tree:
        tmp/
          .mase/dashboards/        <-- target
          sub/
            deep/
              (cwd here)
    _resolve_workspace() should walk up from deep → sub → tmp and find
    `.mase/dashboards/` in tmp.
    """
    tmp = pathlib.Path(tempfile.mkdtemp())
    (tmp / ".mase" / "dashboards").mkdir(parents=True)
    deep = tmp / "sub" / "deep"
    deep.mkdir(parents=True)
    monkeypatch.delenv("MAS_WORKSPACE", raising=False)
    monkeypatch.chdir(str(deep))
    if "dashboard_prd_template" in sys.modules:
        del sys.modules["dashboard_prd_template"]
    sys.path.insert(0, str(TOOLS_DIR))
    import dashboard_prd_template as mod
    assert mod.WORKSPACE == str(tmp)


# ─────────────────────────────────────────────────────────────────────
# load_data()
# ─────────────────────────────────────────────────────────────────────

def test_load_data_reads_both_files(monkeypatch, tmp_path):
    """load_data() opens STATUS_FILE then SIGNAL_FILE, returns (data, sig)."""
    fake_ws = tmp_path
    (fake_ws / ".mase" / "dashboards").mkdir(parents=True)
    status_path = fake_ws / ".mase" / "dashboards" / "mas-dashboard-status.json"
    signal_path = fake_ws / ".mase" / "dashboards" / "mas-dashboard-signal.json"
    status_path.write_text(json.dumps({"hello": "world"}))
    signal_path.write_text(json.dumps({"ts": "2026-01-01T00:00:00Z"}))

    monkeypatch.setenv("MAS_WORKSPACE", str(fake_ws))
    if "dashboard_prd_template" in sys.modules:
        del sys.modules["dashboard_prd_template"]
    sys.path.insert(0, str(TOOLS_DIR))
    import dashboard_prd_template as mod

    data, sig = mod.load_data()
    assert data == {"hello": "world"}
    assert sig == {"ts": "2026-01-01T00:00:00Z"}


# ─────────────────────────────────────────────────────────────────────
# generate_prd(d, sig) — exercises the full string template
# ─────────────────────────────────────────────────────────────────────

def test_generate_prd_writes_output_and_prints(monkeypatch, tmp_path, capsys):
    """generate_prd() builds the PRD string, writes it to OUTPUT_FILE,
    and prints it to stdout. We pass a fully-populated dataset so every
    field in the f-string template is exercised.
    """
    fake_ws = tmp_path
    (fake_ws / ".mase" / "dashboards").mkdir(parents=True)
    monkeypatch.setenv("MAS_WORKSPACE", str(fake_ws))
    if "dashboard_prd_template" in sys.modules:
        del sys.modules["dashboard_prd_template"]
    sys.path.insert(0, str(TOOLS_DIR))
    import dashboard_prd_template as mod

    d = _make_full_data()
    sig = _make_signal()

    mod.generate_prd(d, sig)

    # Output file should now exist. f.write() writes the prd string
    # verbatim; print() adds a trailing newline. So on_disk equals
    # captured.out with the trailing newline that print() added
    # stripped off.
    out_path = mod.OUTPUT_FILE
    assert os.path.exists(out_path)
    on_disk = open(out_path).read()
    captured = capsys.readouterr()
    assert on_disk + "\n" == captured.out

    # Spot-check a handful of template substitutions.
    assert "MAS-FRAMEWORK-HUB - Live Dashboard v2.4" in on_disk
    # KPI from mas section:
    assert "Agents: 14" in on_disk
    # Fleet active branch:
    assert "active 4" in on_disk
    # Timestamp and signal ts in header:
    assert "2026-08-29T20:00:00Z" in on_disk
    assert "2026-08-29T20:00:01Z" in on_disk
    # Build size:
    assert "234KB" in on_disk
    # Framework provider + extensions count:
    assert "deepseek" in on_disk
    assert "Extensions=3" in on_disk
    # User-framework active branch:
    assert "● active" in on_disk
    # Agent scores rows (one per agent):
    assert "sub_mas-agent-guardian" in on_disk
    assert "10.0" in on_disk
    # Dispatch tree: joined with single space (the "dt_html" variable
    # is computed in the function but never interpolated into the
    # template, so the actual PRD just uses " ".join(dt)).
    assert "R110 (root)" in on_disk
    assert "R110-302 (running)" in on_disk
    # Health chart labels: 't0', 't1', 't2' joined:
    assert "t0', 't1', 't2" in on_disk


def test_generate_prd_inactive_fleet_branch(monkeypatch, tmp_path, capsys):
    """When m['fleet_active'] is False, the template renders
    "inaktiv" instead of "active N". This exercises the False branch of
    the inline conditional on the m["fleet_active"] / "active ..."
    expression.
    """
    fake_ws = tmp_path
    (fake_ws / ".mase" / "dashboards").mkdir(parents=True)
    monkeypatch.setenv("MAS_WORKSPACE", str(fake_ws))
    if "dashboard_prd_template" in sys.modules:
        del sys.modules["dashboard_prd_template"]
    sys.path.insert(0, str(TOOLS_DIR))
    import dashboard_prd_template as mod

    d = _make_full_data()
    d["mas"]["fleet_active"] = False
    d["mas"]["fleet_max_paralll"] = 0
    sig = _make_signal()

    mod.generate_prd(d, sig)

    captured = capsys.readouterr()
    assert "inaktiv" in captured.out
    assert "active 0" not in captured.out


def test_generate_prd_user_framework_missing_keys(monkeypatch, tmp_path, capsys):
    """user_framework.get(...) fallbacks: recipes=0, workspace='-',
    detected=False → '○ inaktiv' branch.
    """
    fake_ws = tmp_path
    (fake_ws / ".mase" / "dashboards").mkdir(parents=True)
    monkeypatch.setenv("MAS_WORKSPACE", str(fake_ws))
    if "dashboard_prd_template" in sys.modules:
        del sys.modules["dashboard_prd_template"]
    sys.path.insert(0, str(TOOLS_DIR))
    import dashboard_prd_template as mod

    d = _make_full_data()
    d["user_framework"] = {}  # all .get() defaults trigger
    sig = _make_signal()

    mod.generate_prd(d, sig)

    captured = capsys.readouterr()
    # recipes defaults to 0
    assert "Recipes: 0" in captured.out
    # workspace defaults to '-'
    assert "Workspace: -" in captured.out
    # detected=False → '○ inaktiv'
    assert "○ inaktiv" in captured.out


def test_generate_prd_health_trend_more_than_10(monkeypatch, tmp_path, capsys):
    """The template slices health_trend to the last 10 entries. We feed
    12 entries and verify only the last 10 appear in the chart labels.
    """
    fake_ws = tmp_path
    (fake_ws / ".mase" / "dashboards").mkdir(parents=True)
    monkeypatch.setenv("MAS_WORKSPACE", str(fake_ws))
    if "dashboard_prd_template" in sys.modules:
        del sys.modules["dashboard_prd_template"]
    sys.path.insert(0, str(TOOLS_DIR))
    import dashboard_prd_template as mod

    d = _make_full_data()
    d["history"]["health_trend"] = [
        {"time": f"t{i}", "mas": 50 + i, "framework": 60 + i} for i in range(12)
    ]
    sig = _make_signal()

    mod.generate_prd(d, sig)

    captured = capsys.readouterr()
    # t0..t1 are not in the last 10; t2..t11 are.
    assert "'t0'" not in captured.out
    assert "'t1'" not in captured.out
    assert "'t2'" in captured.out
    assert "'t11'" in captured.out


# ─────────────────────────────────────────────────────────────────────
# if __name__ == "__main__": — 3 branches
# ─────────────────────────────────────────────────────────────────────

def test_main_subprocess_status_missing(monkeypatch, tmp_path):
    """Run the script as a subprocess with no status file present.
    Expect returncode=1 and the "ERROR: No status data" stderr message.
    """
    fake_ws = tmp_path
    (fake_ws / ".mase" / "dashboards").mkdir(parents=True)
    monkeypatch.setenv("MAS_WORKSPACE", str(fake_ws))

    result = subprocess.run(
        [sys.executable, str(TOOL)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 1
    assert "ERROR: No status data" in result.stdout
    assert "mas-dashboard-status.json" in result.stdout


def test_main_subprocess_signal_missing(monkeypatch, tmp_path):
    """Status file is present, signal file is missing → returncode=1
    and the "ERROR: No signal" message is printed.
    """
    fake_ws = tmp_path
    (fake_ws / ".mase" / "dashboards").mkdir(parents=True)
    status_path = fake_ws / ".mase" / "dashboards" / "mas-dashboard-status.json"
    status_path.write_text(json.dumps(_make_full_data()))

    monkeypatch.setenv("MAS_WORKSPACE", str(fake_ws))

    result = subprocess.run(
        [sys.executable, str(TOOL)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 1
    assert "ERROR: No signal" in result.stdout


def test_main_runpy_both_files_present(monkeypatch, tmp_path, capsys):
    """runpy.run_path(..., run_name='__main__') with both files
    present so the full `if __name__ == "__main__":` block runs through
    to the end (which has no explicit sys.exit → runpy returns None).
    This is what attributes line 159 (the bare `generate_prd(d, sig)`
    call) to coverage.
    """
    fake_ws = tmp_path
    (fake_ws / ".mase" / "dashboards").mkdir(parents=True)
    status_path = fake_ws / ".mase" / "dashboards" / "mas-dashboard-status.json"
    signal_path = fake_ws / ".mase" / "dashboards" / "mas-dashboard-signal.json"
    status_path.write_text(json.dumps(_make_full_data()))
    signal_path.write_text(json.dumps(_make_signal()))

    monkeypatch.setenv("MAS_WORKSPACE", str(fake_ws))
    monkeypatch.setattr(sys, "argv", ["dashboard_prd_template.py"])

    rc = runpy.run_path(str(TOOL), run_name="__main__")
    # The if __name__ == "__main__" block has no explicit sys.exit(0)
    # on success — runpy returns the script's globals dict.
    assert isinstance(rc, dict)
    assert rc.get("__name__") == "__main__"

    captured = capsys.readouterr()
    # generate_prd prints the PRD to stdout. Spot-check header.
    assert "MAS-FRAMEWORK-HUB - Live Dashboard v2.4" in captured.out

    # The output file was also written.
    out_path = fake_ws / ".mase" / "dashboards" / "dashboard_prd_current.txt"
    assert out_path.exists()
    assert "MAS-FRAMEWORK-HUB" in out_path.read_text()


# ─────────────────────────────────────────────────────────────────────
# if __name__ == "__main__": — IN-PROCESS branches via runpy.
#
# Subprocess invocations do not contribute to in-process coverage; the
# `__main__` block only attributes to coverage when it runs IN this
# test process. runpy.run_path with run_name='__main__' achieves that
# while still letting STATUS_FILE / SIGNAL_FILE be the module-level
# constants (since they're recomputed at import time, and runpy does
# a fresh import of the script body).
# ─────────────────────────────────────────────────────────────────────

def test_main_runpy_status_missing(monkeypatch, tmp_path, capsys):
    """In-process: STATUS_FILE does not exist → sys.exit(1) at line 153
    AND the "ERROR: No status data under ..." print at line 152 are
    attributed to coverage.
    """
    fake_ws = tmp_path
    (fake_ws / ".mase" / "dashboards").mkdir(parents=True)
    # Do NOT create mas-dashboard-status.json → os.path.exists returns False.
    monkeypatch.setenv("MAS_WORKSPACE", str(fake_ws))
    monkeypatch.setattr(sys, "argv", ["dashboard_prd_template.py"])

    with pytest.raises(SystemExit) as excinfo:
        runpy.run_path(str(TOOL), run_name="__main__")
    assert excinfo.value.code == 1

    captured = capsys.readouterr()
    assert "ERROR: No status data under" in captured.out
    assert "mas-dashboard-status.json" in captured.out


def test_main_runpy_signal_missing(monkeypatch, tmp_path, capsys):
    """In-process: status exists but signal is missing → sys.exit(1) at
    line 156 AND the "ERROR: No signal under ..." print at line 155 are
    attributed to coverage.
    """
    fake_ws = tmp_path
    (fake_ws / ".mase" / "dashboards").mkdir(parents=True)
    status_path = fake_ws / ".mase" / "dashboards" / "mas-dashboard-status.json"
    status_path.write_text(json.dumps(_make_full_data()))
    # Signal file deliberately not created.

    monkeypatch.setenv("MAS_WORKSPACE", str(fake_ws))
    monkeypatch.setattr(sys, "argv", ["dashboard_prd_template.py"])

    with pytest.raises(SystemExit) as excinfo:
        runpy.run_path(str(TOOL), run_name="__main__")
    assert excinfo.value.code == 1

    captured = capsys.readouterr()
    assert "ERROR: No signal under" in captured.out
    assert "mas-dashboard-signal.json" in captured.out
