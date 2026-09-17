"""
test_dev_dashboard_refresh_r110367.py — coverage push for
tools/dev_dashboard_refresh.py (R110-367, 2026-09-07).

The python module tools/dev_dashboard_refresh.py is currently
0%-covered (the existing tests/test_sub_mas_dashboard_refresh.py
only validates the recipe YAML, not the python module). R110-367
adds direct unit tests for every public function:

  - shell(cmd, timeout=10)
  - get_git_log(path, count=10)
  - load_json(path, default=None)
  - generate_dashboard(ws)
  - yaml_load(path)
  - format_dashboard(data)
  - __main__ block (subprocess smoke)

generate_dashboard has many optional side-effecting code paths
(guardian.yaml exists/missing, changes.json in 2 formats,
dist zips present/absent, improve-log.md parsed, dispatch from
_dispatch.json OR from dev_dispatch_tracer.py fallback). The
tests below cover each path explicitly with tmp_path fixtures.

This module has no module-level side effects (no
check_spec_drift or SCAN_SCOPE calls), so the simpler import
pattern works (no r110347 sandbox needed).
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ═══════════════════════════════════════════════
#  Module-level import
# ═══════════════════════════════════════════════

TOOLS_DIR = Path(__file__).parent.parent / "tools"


def _import_dashboard_refresh():
    """Import via sys.path so coverage.py tracks the module.
    (importlib.util.spec_from_file_location does NOT register
    the module in a way that pytest-cov can follow.)"""
    import sys
    if str(TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(TOOLS_DIR))
    import dev_dashboard_refresh
    return dev_dashboard_refresh


@pytest.fixture(scope="module")
def ddr():
    """Module fixture — import once for the whole test file."""
    return _import_dashboard_refresh()


# ═══════════════════════════════════════════════
#  shell()
# ═══════════════════════════════════════════════

class TestShell:
    def test_shell_returns_stdout_stripped(self, ddr):
        assert ddr.shell("echo hello") == "hello"

    def test_shell_returns_empty_on_error(self, ddr):
        # A command that doesn't exist
        assert ddr.shell("__definitely_not_a_real_command_xyz__ 2>/dev/null") == ""

    def test_shell_timeout_returns_empty(self, ddr):
        # sleep longer than timeout
        assert ddr.shell("sleep 5", timeout=1) == ""


# ═══════════════════════════════════════════════
#  get_git_log()
# ═══════════════════════════════════════════════

class TestGetGitLog:
    def test_returns_recent_commits(self, ddr):
        # We run this test from a real git repo (the mas-engineer repo itself)
        result = ddr.get_git_log(".", 5)
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(line, str) for line in result)

    def test_count_limits(self, ddr):
        result = ddr.get_git_log(".", 1)
        assert len(result) <= 1

    def test_non_git_dir_returns_empty(self, ddr, tmp_path):
        result = ddr.get_git_log(str(tmp_path), 5)
        assert result == []


# ═══════════════════════════════════════════════
#  load_json()
# ═══════════════════════════════════════════════

class TestLoadJson:
    def test_load_existing_file(self, ddr, tmp_path):
        p = tmp_path / "data.json"
        p.write_text('{"a": 1, "b": [2, 3]}')
        assert ddr.load_json(str(p)) == {"a": 1, "b": [2, 3]}

    def test_load_missing_file_returns_default(self, ddr, tmp_path):
        p = tmp_path / "missing.json"
        assert ddr.load_json(str(p)) == {}
        assert ddr.load_json(str(p), default={"x": 1}) == {"x": 1}

    def test_load_corrupt_file_returns_default(self, ddr, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text('{"a": not valid json')
        assert ddr.load_json(str(p)) == {}
        assert ddr.load_json(str(p), default=42) == 42


# ═══════════════════════════════════════════════
#  yaml_load()
# ═══════════════════════════════════════════════

class TestYamlLoad:
    def test_load_valid_yaml(self, ddr, tmp_path):
        p = tmp_path / "g.yaml"
        p.write_text("guardian:\n  agents:\n    a1:\n      status: healthy\n      score: 0.9\n")
        result = ddr.yaml_load(str(p))
        assert result["guardian"]["agents"]["a1"]["status"] == "healthy"

    def test_load_missing_file_returns_empty_dict(self, ddr, tmp_path):
        # yaml.safe_load on nonexistent file raises — should be caught
        result = ddr.yaml_load(str(tmp_path / "nope.yaml"))
        assert result == {}

    def test_load_invalid_yaml_returns_empty_dict(self, ddr, tmp_path):
        p = tmp_path / "bad.yaml"
        p.write_text("not: valid: yaml: at: all:\n  - mixed")
        # Should not raise
        result = ddr.yaml_load(str(p))
        assert result == {}


# ═══════════════════════════════════════════════
#  generate_dashboard() — the big one
# ═══════════════════════════════════════════════

def _make_minimal_workspace(ws):
    """Create the minimum directory tree that
    generate_dashboard expects under <ws>/.

    Per the source code, generate_dashboard looks at:
      <ws>/mas-engineer/.mase/guardian.yaml
      <ws>/mas-engineer/.mase/changes.json
      <ws>/mas-engineer/recipe/sub/sub_mas-*.yaml
      <ws>/mas-engineer/tools/dev_*.py
      <ws>/mas-engineer/tools/dev_dispatch_tracer.py
      <ws>/mas-engineer/docs/improve-log.md
      <ws>/mas-engineer/docs/session-analysis-report.md
      <ws>/dist/mas-framework-*.zip
      <ws>/.mas-mode
      <ws>/.monitor/memory/summary-*.md
      <ws>/.mase/dashboards/_dispatch.json
    """
    ws = Path(ws)
    mas_dir = ws / "mas-engineer"
    state_dir = mas_dir / ".mase"
    recipe_dir = mas_dir / "recipe" / "sub"
    tools_dir = mas_dir / "tools"
    docs_dir = mas_dir / "docs"
    dist_dir = ws / "dist"
    mem_dir = ws / ".monitor" / "memory"
    dash_dir = state_dir / "dashboards"

    for d in (state_dir, recipe_dir, tools_dir, docs_dir,
              dist_dir, mem_dir, dash_dir):
        d.mkdir(parents=True, exist_ok=True)

    # No actual recipe/tool files needed — empty dirs are fine.
    return ws


class TestGenerateDashboard:
    def test_minimal_empty_workspace(self, ddr, tmp_path):
        """Empty workspace (no state files) — should still return
        a valid dict with the schema populated."""
        ws = _make_minimal_workspace(tmp_path)
        # Run inside tmp_path so get_git_log doesn't try the real repo
        os.chdir(ws)
        try:
            data = ddr.generate_dashboard(str(ws))
        finally:
            os.chdir("/")
        # Schema sanity
        assert data["dashboard_version"] == "1.0.0"
        assert "generated_at" in data
        assert data["mode"] == "mas"  # default
        assert data["agents"]["total"] == 0
        assert data["agents"]["healthy"] == 0
        assert data["changes"]["total"] == 0
        assert data["build"]["count"] == 0
        assert data["dispatch"]["total"] == 0
        assert data["tools"] == 0  # no dev_*.py in tools_dir
        assert "history" in data
        assert data["history"]["health_trend"]  # at least 1 entry

    def test_mas_mode_file_overrides_default(self, ddr, tmp_path):
        ws = _make_minimal_workspace(tmp_path)
        (ws / ".mas-mode").write_text("mas+")
        os.chdir(ws)
        try:
            data = ddr.generate_dashboard(str(ws))
        finally:
            os.chdir("/")
        assert data["mode"] == "mas+"

    def test_agents_count_from_recipe_subdir(self, ddr, tmp_path):
        """NOTE (R110-367 documentation): `agents.total` in the
        output dict comes from `len(glob.glob(sub_mas-*.yaml))`,
        NOT from `guardian.yaml`. This is inconsistent with
        `agents.healthy/degraded/critical` (which DO come from
        guardian.yaml). R110-368 is proposed to fix this bug in
        the function — the test below documents the CURRENT
        (buggy) behavior to lock in coverage."""
        ws = _make_minimal_workspace(tmp_path)
        recipe_dir = ws / "mas-engineer" / "recipe" / "sub"
        (recipe_dir / "sub_mas-foo.yaml").write_text("name: foo\n")
        (recipe_dir / "sub_mas-bar.yaml").write_text("name: bar\n")
        os.chdir(ws)
        try:
            data = ddr.generate_dashboard(str(ws))
        finally:
            os.chdir("/")
        # BUG: agents.total counts recipe files, not guardian agents
        assert data["agents"]["total"] == 2

    def test_tools_count(self, ddr, tmp_path):
        ws = _make_minimal_workspace(tmp_path)
        tools_dir = ws / "mas-engineer" / "tools"
        (tools_dir / "dev_a.py").write_text("pass\n")
        (tools_dir / "dev_b.py").write_text("pass\n")
        (tools_dir / "dev_c.sh").write_text("pass\n")
        (tools_dir / "not_dev.py").write_text("pass\n")  # should NOT count
        os.chdir(ws)
        try:
            data = ddr.generate_dashboard(str(ws))
        finally:
            os.chdir("/")
        assert data["tools"] == 3  # 2 .py + 1 .sh, not the not_dev one

    def test_guardian_yaml_parsed(self, ddr, tmp_path):
        """guardian.yaml's agents are counted into
        healthy/degraded/critical/avg_score but NOT into total
        (total comes from recipe glob — see R110-368 bug doc)."""
        ws = _make_minimal_workspace(tmp_path)
        gf = ws / "mas-engineer" / ".mase" / "guardian.yaml"
        gf.write_text(
            "guardian:\n"
            "  agents:\n"
            "    a1:\n"
            "      status: healthy\n"
            "      score: 0.95\n"
            "    a2:\n"
            "      status: degraded\n"
            "      score: 0.4\n"
            "    a3:\n"
            "      status: critical\n"
            "      score: 0.1\n"
        )
        os.chdir(ws)
        try:
            data = ddr.generate_dashboard(str(ws))
        finally:
            os.chdir("/")
        agents = data["agents"]
        # Status counts (from guardian.yaml)
        assert agents["healthy"] == 1
        assert agents["degraded"] == 1
        assert agents["critical"] == 1
        # avg_score = (0.95 + 0.4 + 0.1) / 3 = 0.483, rounds to 0.5
        assert agents["avg_score"] == 0.5
        # BUG (R110-368): total does NOT include guardian agents,
        # only recipe files. Empty recipe dir → total=0.
        assert agents["total"] == 0  # see test_agents_count_from_recipe_subdir

    def test_guardian_yaml_corrupt_returns_zeros(self, ddr, tmp_path):
        ws = _make_minimal_workspace(tmp_path)
        gf = ws / "mas-engineer" / ".mase" / "guardian.yaml"
        gf.write_text("not: valid: yaml: at: all:\n  - mixed")
        os.chdir(ws)
        try:
            data = ddr.generate_dashboard(str(ws))
        finally:
            os.chdir("/")
        assert data["agents"]["total"] == 0
        assert data["agents"]["healthy"] == 0
        assert data["agents"]["avg_score"] == 0

    def test_changes_json_array_format(self, ddr, tmp_path):
        ws = _make_minimal_workspace(tmp_path)
        cf = ws / "mas-engineer" / ".mase" / "changes.json"
        changes = [
            {"action": "FIX bug X", "timestamp": "2026-09-01T10:00:00Z"},
            {"action": "SI-RUN optimization", "timestamp": "2026-09-02T11:00:00Z"},
            {"action": "Prompt-Update", "timestamp": "2026-09-03T12:00:00Z"},
            {"action": "DASHBOARD rebuild", "timestamp": "2026-09-04T13:00:00Z"},
            {"action": "CHECKPOINT save", "timestamp": "2026-09-05T14:00:00Z"},
            {"action": "Random other", "timestamp": "2026-09-06T15:00:00Z"},
        ]
        cf.write_text(json.dumps(changes))
        os.chdir(ws)
        try:
            data = ddr.generate_dashboard(str(ws))
        finally:
            os.chdir("/")
        assert data["changes"]["total"] == 6
        by_type = data["changes"]["by_type"]
        # FIX maps to "Fixes", SI-RUN to "SI-RUN / Self-Improve",
        # Prompt-Update to "Prompt-Optimierung", DASHBOARD to "Dashboard",
        # CHECKPOINT to "Checkpoints", "Random other" to "Other"
        assert by_type["Fixes"] == 1
        assert by_type["SI-RUN / Self-Improve"] == 1
        assert by_type["Prompt-Optimierung"] == 1
        assert by_type["Dashboard"] == 1
        assert by_type["Checkpoints"] == 1
        assert by_type["Other"] == 1
        # last_10 has all 6 (less than 10)
        assert len(data["changes"]["last_10"]) == 6

    def test_changes_json_ndjson_format(self, ddr, tmp_path):
        ws = _make_minimal_workspace(tmp_path)
        cf = ws / "mas-engineer" / ".mase" / "changes.json"
        lines = [
            json.dumps({"action": "FIX a", "timestamp": "2026-09-01T10:00:00Z"}),
            json.dumps({"action": "FIX b", "timestamp": "2026-09-02T10:00:00Z"}),
            "this is not json, should be skipped",
            json.dumps({"action": "FIX c", "timestamp": "2026-09-03T10:00:00Z"}),
        ]
        cf.write_text("\n".join(lines))  # no leading '['
        os.chdir(ws)
        try:
            data = ddr.generate_dashboard(str(ws))
        finally:
            os.chdir("/")
        assert data["changes"]["total"] == 3  # one line was invalid

    def test_changes_json_dict_format(self, ddr, tmp_path):
        """If changes.json is a dict (e.g. {"changes": [...]}), it
        should unwrap the inner list."""
        ws = _make_minimal_workspace(tmp_path)
        cf = ws / "mas-engineer" / ".mase" / "changes.json"
        cf.write_text(json.dumps({
            "changes": [
                {"action": "FIX a", "timestamp": "2026-09-01T10:00:00Z"},
            ]
        }))
        os.chdir(ws)
        try:
            data = ddr.generate_dashboard(str(ws))
        finally:
            os.chdir("/")
        assert data["changes"]["total"] == 1

    def test_dist_zip_parsing(self, ddr, tmp_path):
        ws = _make_minimal_workspace(tmp_path)
        dist_dir = ws / "dist"
        (dist_dir / "mas-framework-old.zip").write_bytes(b"x" * 2048)
        (dist_dir / "mas-framework-new.zip").write_bytes(b"x" * 4096)
        os.chdir(ws)
        try:
            data = ddr.generate_dashboard(str(ws))
        finally:
            os.chdir("/")
        b = data["build"]
        assert b["count"] == 2
        # Latest is the one sorted last (newest by mtime)
        assert b["latest"]["name"].endswith(".zip")
        assert b["latest"]["size_kb"] >= 2
        assert "size_trend" in b
        assert len(b["size_trend"]) == 2

    def test_no_dist_dir(self, ddr, tmp_path):
        ws = _make_minimal_workspace(tmp_path)
        (ws / "dist").rmdir()  # remove the empty dist dir
        os.chdir(ws)
        try:
            data = ddr.generate_dashboard(str(ws))
        finally:
            os.chdir("/")
        assert data["build"]["count"] == 0
        # build_size history should NOT have an entry if no dist
        # (the code only appends to history if latest is truthy)

    def test_improve_log_parsed(self, ddr, tmp_path):
        ws = _make_minimal_workspace(tmp_path)
        il = ws / "mas-engineer" / "docs" / "improve-log.md"
        il.write_text(
            "# Improve Log\n\n"
            "## Run 1 — first optimization\n"
            "Did stuff\n\n"
            "## Run 2 — second optimization\n"
            "Did more stuff\n\n"
            "## Run 3 — third optimization\n"
            "Did even more stuff\n"
        )
        os.chdir(ws)
        try:
            data = ddr.generate_dashboard(str(ws))
        finally:
            os.chdir("/")
        si = data["self_improve"]
        assert si["runs"] == 3
        assert si["last"] == "Run 3 — third optimization"
        assert len(si["last_10"]) == 3

    def test_no_improve_log(self, ddr, tmp_path):
        ws = _make_minimal_workspace(tmp_path)
        os.chdir(ws)
        try:
            data = ddr.generate_dashboard(str(ws))
        finally:
            os.chdir("/")
        assert data["self_improve"]["runs"] == 0
        assert data["self_improve"]["last"] == "No SI-RUN"

    def test_session_analysis_report_parsed(self, ddr, tmp_path):
        ws = _make_minimal_workspace(tmp_path)
        sa = ws / "mas-engineer" / "docs" / "session-analysis-report.md"
        sa.write_text(
            "| Stat | Value |\n"
            "| Gesamtsessions | 42 |\n"
            "| Total-Tokens | 1.2M |\n"
            "| Gesamtkosten | 12.34€ |\n"
            "| Activitysdauer | 5h |\n"
        )
        os.chdir(ws)
        try:
            data = ddr.generate_dashboard(str(ws))
        finally:
            os.chdir("/")
        s = data["sessions"]
        assert s["total"] == "42"
        assert s["tokens"] == "1.2M"
        assert s["cost"] == "12.34€"
        assert s["hours"] == "5h"

    def test_no_session_report(self, ddr, tmp_path):
        ws = _make_minimal_workspace(tmp_path)
        os.chdir(ws)
        try:
            data = ddr.generate_dashboard(str(ws))
        finally:
            os.chdir("/")
        assert data["sessions"] == {}

    def test_dispatch_from_file(self, ddr, tmp_path):
        """NOTE (R110-367): DASH_DIR is a MODULE-LEVEL constant
        based on `os.environ.get('MAS_WORKSPACE', '.')` at IMPORT
        time — NOT the `ws` argument to generate_dashboard(). So
        the dispatch file is read from
        `<cwd-at-import-time>/.mase/dashboards/_dispatch.json`.
        The test chdir's to ws before the call, so the resolved
        path is `<ws>/.mase/dashboards/_dispatch.json`."""
        ws = _make_minimal_workspace(tmp_path)
        # The actual location: <ws>/.mase/dashboards/_dispatch.json
        df = ws / ".mase" / "dashboards" / "_dispatch.json"
        df.parent.mkdir(parents=True, exist_ok=True)
        df.write_text(json.dumps({
            "total": 100, "active": 5, "done": 90,
            "failed": 5, "avg_duration_ms": 250
        }))
        os.chdir(ws)
        try:
            data = ddr.generate_dashboard(str(ws))
        finally:
            os.chdir("/")
        d = data["dispatch"]
        assert d["total"] == 100
        assert d["active"] == 5
        assert d["done"] == 90
        assert d["failed"] == 5
        assert d["avg_duration_ms"] == 250

    def test_dispatch_from_tracer_fallback(self, ddr, tmp_path):
        """When _dispatch.json doesn't exist, dev_dispatch_tracer.py
        is invoked as a subprocess."""
        ws = _make_minimal_workspace(tmp_path)
        # Create a fake dev_dispatch_tracer.py that emits Total:/Active:/Done: etc.
        tracer = ws / "mas-engineer" / "tools" / "dev_dispatch_tracer.py"
        tracer.write_text(
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "if sys.argv[-1] == 'status':\n"
            "    print('Total: 50')\n"
            "    print('Active: 3')\n"
            "    print('Done: 45')\n"
            "    print('Failed: 2')\n"
            "    print('Avg: 150ms')\n"
        )
        tracer.chmod(0o755)
        os.chdir(ws)
        try:
            data = ddr.generate_dashboard(str(ws))
        finally:
            os.chdir("/")
        d = data["dispatch"]
        assert d["total"] == 50
        assert d["active"] == 3
        assert d["done"] == 45
        assert d["failed"] == 2
        assert d["avg_duration_ms"] == 150

    def test_dispatch_tracer_failure_returns_zeros(self, ddr, tmp_path):
        """If dev_dispatch_tracer.py is missing AND _dispatch.json
        is missing, dispatch stays at all-zeros."""
        ws = _make_minimal_workspace(tmp_path)
        os.chdir(ws)
        try:
            data = ddr.generate_dashboard(str(ws))
        finally:
            os.chdir("/")
        d = data["dispatch"]
        assert d["total"] == 0
        assert d["active"] == 0
        assert d["done"] == 0
        assert d["failed"] == 0
        assert d["avg_duration_ms"] == 0

    def test_execution_status_from_monitor(self, ddr, tmp_path):
        ws = _make_minimal_workspace(tmp_path)
        mem_dir = ws / ".monitor" / "memory"
        (mem_dir / "summary-20260907.md").write_text(
            "# Monitor Summary\n\n"
            "Tasks: 5/10/2/1\n"
        )
        os.chdir(ws)
        try:
            data = ddr.generate_dashboard(str(ws))
        finally:
            os.chdir("/")
        ex = data["execution"]
        assert ex["done"] == 5
        assert ex["total"] == 10
        assert ex["last_status"] == "completed"

    def test_no_monitor_dir(self, ddr, tmp_path):
        ws = _make_minimal_workspace(tmp_path)
        import shutil
        shutil.rmtree(ws / ".monitor")
        os.chdir(ws)
        try:
            data = ddr.generate_dashboard(str(ws))
        finally:
            os.chdir("/")
        ex = data["execution"]
        assert ex["done"] == 0
        assert ex["total"] == 0
        assert ex["last_status"] is None

    def test_mas_health_with_degraded_agents(self, ddr, tmp_path):
        """When there's at least 1 degraded agent, mas_health = 70."""
        ws = _make_minimal_workspace(tmp_path)
        gf = ws / "mas-engineer" / ".mase" / "guardian.yaml"
        gf.write_text(
            "guardian:\n  agents:\n    a1:\n      status: healthy\n      score: 0.9\n"
            "    a2:\n      status: degraded\n      score: 0.5\n"
        )
        os.chdir(ws)
        try:
            data = ddr.generate_dashboard(str(ws))
        finally:
            os.chdir("/")
        # Check the health_trend for the 70 value
        last_health = data["history"]["health_trend"][-1]["mas"]
        assert last_health == 70

    def test_mas_health_zero_when_no_agents(self, ddr, tmp_path):
        """When there are 0 agents, mas_health = 0."""
        ws = _make_minimal_workspace(tmp_path)
        os.chdir(ws)
        try:
            data = ddr.generate_dashboard(str(ws))
        finally:
            os.chdir("/")
        last_health = data["history"]["health_trend"][-1]["mas"]
        assert last_health == 0

    def test_mas_health_100_all_healthy(self, ddr, tmp_path):
        """When all agents are healthy, mas_health = 100."""
        ws = _make_minimal_workspace(tmp_path)
        gf = ws / "mas-engineer" / ".mase" / "guardian.yaml"
        gf.write_text(
            "guardian:\n  agents:\n    a1:\n      status: healthy\n      score: 0.9\n"
        )
        os.chdir(ws)
        try:
            data = ddr.generate_dashboard(str(ws))
        finally:
            os.chdir("/")
        last_health = data["history"]["health_trend"][-1]["mas"]
        assert last_health == 100

    def test_history_key_backcompat(self, ddr, tmp_path):
        """If history.json is missing all 3 keys, they're added
        with empty lists."""
        ws = _make_minimal_workspace(tmp_path)
        hf = ws / "mas-engineer" / ".mase" / "dashboards" / "history.json"
        hf.write_text(json.dumps({"old_key": []}))
        os.chdir(ws)
        try:
            data = ddr.generate_dashboard(str(ws))
        finally:
            os.chdir("/")
        h = data["history"]
        assert h["health_trend"]
        assert h["build_size"] == []
        assert h["dispatch_volume"]


# ═══════════════════════════════════════════════
#  format_dashboard()
# ═══════════════════════════════════════════════

class TestFormatDashboard:
    def _sample_data(self, ddr, tmp_path):
        """Reuse generate_dashboard to get realistic data."""
        ws = _make_minimal_workspace(tmp_path)
        os.chdir(ws)
        try:
            return ddr.generate_dashboard(str(ws))
        finally:
            os.chdir("/")

    def test_empty_data_does_not_crash(self, ddr):
        out = ddr.format_dashboard({})
        assert "DASHBOARD" in out
        assert "║" in out  # box-drawing chars present

    def test_full_data_renders_all_sections(self, ddr, tmp_path):
        data = self._sample_data(ddr, tmp_path)
        out = ddr.format_dashboard(data)
        # Sections
        for marker in ["AGENTEN", "CHANGES", "BUILD", "DISPATCH",
                       "SELF-IMPROVE", "TOOLS"]:
            assert marker in out, f"Missing section: {marker}"

    def test_build_section_with_latest(self, ddr):
        data = {"build": {
            "count": 3,
            "latest": {"date": "01.09 12:00", "size_kb": 4096}
        }}
        out = ddr.format_dashboard(data)
        assert "BUILD" in out
        assert "01.09 12:00" in out
        assert "4096" in out

    def test_build_section_no_latest(self, ddr):
        data = {"build": {"count": 0}}
        out = ddr.format_dashboard(data)
        assert "No Distribution" in out

    def test_line_function_truncates(self, ddr):
        """The nested `line()` truncates strings to 60 chars."""
        data = {"workspace": "x" * 200}
        out = ddr.format_dashboard(data)
        # The workspace line should be truncated
        for line in out.split("\n"):
            if "x" * 20 in line:
                # If there are 20+ x's, it should be at most 60
                assert "x" * 61 not in line
                break

    def test_health_icon_warning(self, ddr):
        """When degraded > 0, show ⚠️ in the AGENTEN line."""
        data = {"agents": {"total": 1, "healthy": 0, "degraded": 1, "avg_score": 0.5}}
        out = ddr.format_dashboard(data)
        # Find the AGENTEN line specifically
        agent_lines = [l for l in out.split("\n") if "AGENTEN" in l]
        assert len(agent_lines) == 1
        assert "⚠️" in agent_lines[0]


# ═══════════════════════════════════════════════
#  __main__ block
# ═══════════════════════════════════════════════

class TestMain:
    def test_main_runs_and_creates_json(self, tmp_path):
        """Invoke as a subprocess to cover the __main__ block.
        Creates a minimal workspace, then runs the script.

        NOTE (R110-367): The __main__ block writes output files
        to DASH_DIR which is a MODULE-LEVEL constant based on
        `os.environ.get('MAS_WORKSPACE', '.')` at import time —
        NOT the --workspace argument. So project.json, history.json
        and .updated are written to <cwd>/.mase/dashboards/, where
        cwd is the directory the script was invoked from."""
        ws = _make_minimal_workspace(tmp_path)
        # Run from inside the workspace dir so the relative DASH_DIR
        # resolves under our tmp_path.
        os.chdir(ws)
        try:
            r = subprocess.run(
                [sys.executable, str(TOOLS_DIR / "dev_dashboard_refresh.py"),
                 "--workspace", str(ws)],
                capture_output=True, text=True, timeout=30,
            )
        finally:
            os.chdir("/")
        assert r.returncode == 0, f"stderr: {r.stderr}\nstdout: {r.stdout}"
        # project.json was written to <ws>/.mase/dashboards/
        project_json = ws / ".mase" / "dashboards" / "project.json"
        assert project_json.exists()
        data = json.loads(project_json.read_text())
        assert data["dashboard_version"] == "1.0.0"
        # history.json was written to <ws>/.mase/dashboards/
        history = ws / ".mase" / "dashboards" / "history.json"
        assert history.exists()
        # .updated flag was written
        flag = ws / ".mase" / "dashboards" / ".updated"
        assert flag.exists()
        # stdout contains dashboard and OK message
        assert "DASHBOARD" in r.stdout
        assert "[OK] Dashboard refreshed" in r.stdout

    def test_main_with_positional_workspace(self, tmp_path):
        """The main also supports positional workspace arg."""
        ws = _make_minimal_workspace(tmp_path)
        os.chdir(ws)
        try:
            r = subprocess.run(
                [sys.executable, str(TOOLS_DIR / "dev_dashboard_refresh.py"),
                 str(ws)],
                capture_output=True, text=True, timeout=30,
            )
        finally:
            os.chdir("/")
        assert r.returncode == 0, f"stderr: {r.stderr}"
        project_json = ws / ".mase" / "dashboards" / "project.json"
        assert project_json.exists()
