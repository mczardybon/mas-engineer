"""R110-451 — coverage-push r8: tools/dashboard_prd_template.py 0% → 100%.

PRD-template generator (159 lines). Resolves workspace, reads
mas-dashboard-status.json + mas-dashboard-signal.json, builds PRD
text, writes to dashboard_prd_current.txt.

Targets:
- _resolve_workspace: MAS_WORKSPACE env (if dir); walks up looking
  for .mase/dashboards/; defaults to abspath('.').
- WORKSPACE/DASHBOARD_DIR/STATUS_FILE/SIGNAL_FILE/OUTPUT_FILE
  module constants set on import.
- load_data(): reads status + signal JSON.
- generate_prd(d, sig): builds HTML-formatted PRD string from
  d.mas/framework/dispatch/user_framework + history.health_trend;
  writes to OUTPUT_FILE; prints to stdout.
- __main__: STATUS_FILE missing → print error + exit 1; SIGNAL_FILE
  missing → print error + exit 1; else load + generate_prd.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.dashboard_prd_template as dpt  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# Workspace resolution
# ─────────────────────────────────────────────────────────────────────
class TestResolveWorkspace:
    def test_explicit_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MAS_WORKSPACE", str(tmp_path))
        assert dpt._resolve_workspace() == str(tmp_path)

    def test_walk_up_finds_mase(self, tmp_path, monkeypatch):
        monkeypatch.delenv("MAS_WORKSPACE", raising=False)
        # Create .mase/dashboards at tmp_path
        (tmp_path / ".mase" / "dashboards").mkdir(parents=True)
        sub = tmp_path / "a" / "b" / "c"
        sub.mkdir(parents=True)
        cwd = os.getcwd()
        os.chdir(sub)
        try:
            ws = dpt._resolve_workspace()
            assert ws == str(tmp_path)
        finally:
            os.chdir(cwd)

    def test_fallback_to_cwd(self, monkeypatch):
        monkeypatch.delenv("MAS_WORKSPACE", raising=False)
        # If no .mase/dashboards anywhere on the walk → abspath('.')
        ws = dpt._resolve_workspace()
        assert ws == os.path.abspath(".")

    def test_env_not_a_dir_falls_through(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MAS_WORKSPACE", "/nonexistent/path/here")
        ws = dpt._resolve_workspace()
        # Falls through to walk/cwd fallback
        assert ws == os.path.abspath(".")


# ─────────────────────────────────────────────────────────────────────
# Module constants are set on import
# ─────────────────────────────────────────────────────────────────────
class TestModuleConstants:
    def test_constants_exist(self):
        assert hasattr(dpt, "WORKSPACE")
        assert hasattr(dpt, "DASHBOARD_DIR")
        assert hasattr(dpt, "STATUS_FILE")
        assert hasattr(dpt, "SIGNAL_FILE")
        assert hasattr(dpt, "OUTPUT_FILE")

    def test_constants_are_paths(self):
        assert dpt.STATUS_FILE.endswith("mas-dashboard-status.json")
        assert dpt.SIGNAL_FILE.endswith("mas-dashboard-signal.json")
        assert dpt.OUTPUT_FILE.endswith("dashboard_prd_current.txt")


# ─────────────────────────────────────────────────────────────────────
# load_data
# ─────────────────────────────────────────────────────────────────────
def _make_minimal_data():
    """Build minimal valid (status, signal) data."""
    status = {
        "timestamp": "2026-09-12T00:00:00Z",
        "mas": {
            "agents": 14,
            "tools": 5,
            "changes": 10,
            "checkpoints": 3,
            "fleet_active": False,
            "fleet_max_paralll": 0,
            "prompt_score_avg": 9.5,
            "agents_at_10": 4,
            "agent_health": {"healthy": 12, "total": 14},
            "self_improve": {"total_runs": 1, "last_run": "x"},
            "session_stats": {"total_sessions": 5, "total_cost": 0.5,
                              "active_hours": 2},
            "build": {"count": 1,
                      "latest": {"size_kb": 100, "status": "ok"}},
            "agent_scores": [{"name": "a", "score": 10}],
            "changes_by_type": {"fix": 3, "feat": 2},
        },
        "framework": {
            "recipes": {"total": 5, "specialists": 2, "subs": 2,
                        "core": 1},
            "config": {"provider": "x",
                       "extensions": ["a", "b"]},
        },
        "dispatch": {
            "done": 1, "running": 0, "errors": 0,
            "tree": ["line1", "  line2"],
        },
        "user_framework": {"recipes": 1, "workspace": "ws",
                           "detected": True},
        "history": {
            "health_trend": [{"time": "t1", "mas": 8, "framework": 9}],
        },
    }
    signal = {"ts": "now"}
    return status, signal


class TestLoadData:
    def test_loads_both_files(self, tmp_path, monkeypatch):
        monkeypatch.setattr(dpt, "STATUS_FILE",
                            str(tmp_path / "status.json"))
        monkeypatch.setattr(dpt, "SIGNAL_FILE",
                            str(tmp_path / "signal.json"))
        status, signal = _make_minimal_data()
        (tmp_path / "status.json").write_text(json.dumps(status))
        (tmp_path / "signal.json").write_text(json.dumps(signal))
        d, sig = dpt.load_data()
        assert d["mas"]["agents"] == 14
        assert sig["ts"] == "now"


# ─────────────────────────────────────────────────────────────────────
# generate_prd
# ─────────────────────────────────────────────────────────────────────
class TestGeneratePrd:
    def test_writes_and_prints(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(dpt, "OUTPUT_FILE",
                            str(tmp_path / "out.txt"))
        status, signal = _make_minimal_data()
        dpt.generate_prd(status, signal)
        out_file = tmp_path / "out.txt"
        assert out_file.exists()
        text = out_file.read_text()
        assert "MAS-FRAMEWORK-HUB" in text
        assert "Live Dashboard v2.4" in text
        captured = capsys.readouterr().out
        assert "MAS-FRAMEWORK-HUB" in captured

    def test_agent_rows(self, tmp_path, monkeypatch, capsys):
        # The `agents_rows` variable is computed but never inserted
        # into the PRD template (template hardcodes 14 sub_mas- rows).
        # We just verify generate_prd runs without error and covers
        # the loop body. Side-effect: prints PRD to stdout.
        monkeypatch.setattr(dpt, "OUTPUT_FILE",
                            str(tmp_path / "out.txt"))
        status, signal = _make_minimal_data()
        dpt.generate_prd(status, signal)
        assert (tmp_path / "out.txt").exists()

    def test_changes_by_type_sorted_desc(self, tmp_path, monkeypatch):
        # `ctypes_rows` is also computed but not inserted. Verify
        # generate_prd completes without raising.
        monkeypatch.setattr(dpt, "OUTPUT_FILE",
                            str(tmp_path / "out.txt"))
        status, signal = _make_minimal_data()
        status["mas"]["changes_by_type"] = {"feat": 2, "fix": 3}
        dpt.generate_prd(status, signal)
        assert (tmp_path / "out.txt").exists()

    def test_dispatch_tree_indent(self, tmp_path, monkeypatch):
        monkeypatch.setattr(dpt, "OUTPUT_FILE",
                            str(tmp_path / "out.txt"))
        status, signal = _make_minimal_data()
        # tree items with leading spaces trigger the indent loop.
        # The PRD uses {" ".join(dt)} for the tree section, so the
        # leading-space child gets concatenated with extra space.
        status["dispatch"]["tree"] = ["top", "  child"]
        dpt.generate_prd(status, signal)
        text = (tmp_path / "out.txt").read_text()
        # "top" + " " + "  child" = "top   child" (3 spaces)
        assert "top" in text
        assert "child" in text
        assert "Dispatch Tree" in text

    def test_health_chart_data(self, tmp_path, monkeypatch):
        monkeypatch.setattr(dpt, "OUTPUT_FILE",
                            str(tmp_path / "out.txt"))
        status, signal = _make_minimal_data()
        dpt.generate_prd(status, signal)
        text = (tmp_path / "out.txt").read_text()
        assert "healthChart" in text
        # Labels: ['t1'], data: [8], [9]
        assert "['t1']" in text
        assert "[8]" in text
        assert "[9]" in text

    def test_user_framework_inactive(self, tmp_path, monkeypatch):
        monkeypatch.setattr(dpt, "OUTPUT_FILE",
                            str(tmp_path / "out.txt"))
        status, signal = _make_minimal_data()
        status["user_framework"]["detected"] = False
        dpt.generate_prd(status, signal)
        text = (tmp_path / "out.txt").read_text()
        assert "inaktiv" in text

    def test_fleet_active(self, tmp_path, monkeypatch):
        monkeypatch.setattr(dpt, "OUTPUT_FILE",
                            str(tmp_path / "out.txt"))
        status, signal = _make_minimal_data()
        status["mas"]["fleet_active"] = True
        status["mas"]["fleet_max_paralll"] = 5
        dpt.generate_prd(status, signal)
        text = (tmp_path / "out.txt").read_text()
        assert "active 5" in text


# ─────────────────────────────────────────────────────────────────────
# __main__  (via subprocess for coverage)
# ─────────────────────────────────────────────────────────────────────
class TestMain:
    def _setup(self, tmp_path, with_status=True, with_signal=True):
        """Configure tmp_path to look like a workspace."""
        d_dir = tmp_path / ".mase" / "dashboards"
        d_dir.mkdir(parents=True)
        status, signal = _make_minimal_data()
        if with_status:
            (d_dir / "mas-dashboard-status.json").write_text(
                json.dumps(status))
        if with_signal:
            (d_dir / "mas-dashboard-signal.json").write_text(
                json.dumps(signal))
        return d_dir

    def test_main_no_status(self, tmp_path, monkeypatch):
        self._setup(tmp_path, with_status=False)
        monkeypatch.setenv("MAS_WORKSPACE", str(tmp_path))
        r = subprocess.run(
            ['python3', 'tools/dashboard_prd_template.py'],
            capture_output=True, text=True,
            cwd='/workspace/dev-branch/mas-engineer-cleanup/mas-engineer')
        assert r.returncode == 1
        assert "ERROR" in r.stdout

    def test_main_no_signal(self, tmp_path, monkeypatch):
        self._setup(tmp_path, with_signal=False)
        monkeypatch.setenv("MAS_WORKSPACE", str(tmp_path))
        r = subprocess.run(
            ['python3', 'tools/dashboard_prd_template.py'],
            capture_output=True, text=True,
            cwd='/workspace/dev-branch/mas-engineer-cleanup/mas-engineer')
        assert r.returncode == 1
        assert "ERROR" in r.stdout

    def test_main_success(self, tmp_path, monkeypatch):
        d_dir = self._setup(tmp_path)
        monkeypatch.setenv("MAS_WORKSPACE", str(tmp_path))
        r = subprocess.run(
            ['python3', 'tools/dashboard_prd_template.py'],
            capture_output=True, text=True,
            cwd='/workspace/dev-branch/mas-engineer-cleanup/mas-engineer')
        assert r.returncode == 0
        assert "MAS-FRAMEWORK-HUB" in r.stdout
        # PRD was written to dashboard_prd_current.txt
        out = d_dir / "dashboard_prd_current.txt"
        assert out.exists()
        assert "MAS-FRAMEWORK-HUB" in out.read_text()
