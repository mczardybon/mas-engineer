"""
test_r110302_mcp_dashboard_server.py — R110-302 Coverage Sprint for
tools/mcp_dashboard_server.py.

Target: mcp_dashboard_server.py (81 lines, 40 stmts).
Pattern: see test_r110302_mq_topic_depth.py — import tool as a library,
exercise the class, then subprocess + runpy for the __main__ guard.

Branch map for DashboardMCP:
  __init__         L17: workspace=arg OR env['MAS_WORKSPACE'] OR '.'
                   L18: dashboard_dir = workspace/.mase/dashboards
  get_data         L24: data.json missing        → _generate_fresh_data
                   L24-27: data.json valid        → return parsed JSON
                   L24-29: data.json invalid JSON → except: pass → fallback
  _generate_fresh  L37-39: dev_dashboard_data importable → call generate_data
                   L40-45: ImportError            → return error stub
  handle_request   L49-50: 'ui/dashboard/data' OR 'dashboard:data' → get_data()
                   L51-52: 'ui/dashboard/refresh'                 → _generate_fresh_data()
                   L53-58: 'ui/dashboard/subscribe'               → subscribed+events
                   L59-60: unknown method                          → {"error": ...}
  notify_update    L66: with data  → {"method": event, "params": data}
                   L66: without    → params = get_data() (recursive branch)

Module-level:
  get_dashboard_data(workspace)  L70-73:  instantiates DashboardMCP + get_data()

__main__ block:
  L78-81: import sys, parse argv[1] (default '.'), call get_dashboard_data,
          print(json.dumps(...))

Total: 20 tests covering all branches.
"""
import importlib
import json
import os
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOL = REPO_ROOT / "tools" / "mcp_dashboard_server.py"
TOOLS_DIR = TOOL.parent


def _import_tool():
    """Import mcp_dashboard_server as a library.

    The module is safe to import (only stdlib; no module-level sys.argv
    parsing). Returns the loaded module.
    """
    sys.path.insert(0, str(TOOLS_DIR))
    if "mcp_dashboard_server" in sys.modules:
        # Force a fresh import in case a prior test mutated env vars
        # or sys.path; tests in this file monkeypatch the module.
        del sys.modules["mcp_dashboard_server"]
    import mcp_dashboard_server
    return mcp_dashboard_server


# ─────────────────────────────────────────────────────────────────────
# DashboardMCP.__init__ — branch coverage for workspace resolution
# ─────────────────────────────────────────────────────────────────────

def test_init_uses_workspace_arg(monkeypatch):
    """Passing workspace= explicitly → uses that value (no env fallback)."""
    monkeypatch.delenv("MAS_WORKSPACE", raising=False)
    mod = _import_tool()
    h = mod.DashboardMCP(workspace="/tmp/arg-ws")
    assert h.workspace == "/tmp/arg-ws"
    assert h.dashboard_dir == "/tmp/arg-ws/.mase/dashboards"


def test_init_falls_back_to_env_when_workspace_none(monkeypatch):
    """workspace=None → os.environ['MAS_WORKSPACE'] is consulted."""
    monkeypatch.setenv("MAS_WORKSPACE", "/tmp/env-ws")
    mod = _import_tool()
    h = mod.DashboardMCP(workspace=None)
    assert h.workspace == "/tmp/env-ws"
    assert h.dashboard_dir == "/tmp/env-ws/.mase/dashboards"


def test_init_falls_back_to_dot_when_workspace_and_env_missing(monkeypatch):
    """workspace=None AND MAS_WORKSPACE unset → defaults to '.'."""
    monkeypatch.delenv("MAS_WORKSPACE", raising=False)
    mod = _import_tool()
    h = mod.DashboardMCP(workspace=None)
    assert h.workspace == "."
    assert h.dashboard_dir == os.path.join(".", ".mase", "dashboards")


# ─────────────────────────────────────────────────────────────────────
# DashboardMCP.get_data — three branches
# ─────────────────────────────────────────────────────────────────────

def test_get_data_returns_parsed_json_when_data_file_valid(tmp_path, monkeypatch):
    """data.json exists & is valid JSON → returned verbatim (no fallback)."""
    monkeypatch.delenv("MAS_WORKSPACE", raising=False)
    mod = _import_tool()
    # Build workspace/.mase/dashboards/data.json
    dash_dir = tmp_path / ".mase" / "dashboards"
    dash_dir.mkdir(parents=True)
    (dash_dir / "data.json").write_text(json.dumps({"k": "v", "n": 42}))

    h = mod.DashboardMCP(workspace=str(tmp_path))
    out = h.get_data()
    assert out == {"k": "v", "n": 42}


def test_get_data_falls_back_when_data_file_invalid_json(tmp_path, monkeypatch):
    """data.json exists but is NOT valid JSON → except: pass → fallback.

    The fallback path calls _generate_fresh_data() which tries to
    import dev_dashboard_data. If that import succeeds (it does in
    the real repo) we get a dict back. To make this test independent
    of the actual generator's behavior we mock the import via
    sys.modules so it returns a known stub.
    """
    monkeypatch.delenv("MAS_WORKSPACE", raising=False)
    mod = _import_tool()
    dash_dir = tmp_path / ".mase" / "dashboards"
    dash_dir.mkdir(parents=True)
    # Garbage JSON
    (dash_dir / "data.json").write_text("{this is not valid JSON")

    # Stub dev_dashboard_data.generate_data so we don't have to run
    # the real generator (which shells out to git/python).
    fake_mod = type(sys)("dev_dashboard_data")
    fake_mod.generate_data = lambda ws: {"from": "fallback", "workspace": ws}
    sys.modules["dev_dashboard_data"] = fake_mod
    try:
        h = mod.DashboardMCP(workspace=str(tmp_path))
        out = h.get_data()
        assert out == {"from": "fallback", "workspace": str(tmp_path)}
    finally:
        del sys.modules["dev_dashboard_data"]


def test_get_data_falls_back_when_data_file_missing(tmp_path, monkeypatch):
    """data.json does not exist → fallback to _generate_fresh_data()."""
    monkeypatch.delenv("MAS_WORKSPACE", raising=False)
    mod = _import_tool()
    # Create dashboard dir but NO data.json
    (tmp_path / ".mase" / "dashboards").mkdir(parents=True)

    fake_mod = type(sys)("dev_dashboard_data")
    fake_mod.generate_data = lambda ws: {"from": "fresh", "workspace": ws}
    sys.modules["dev_dashboard_data"] = fake_mod
    try:
        h = mod.DashboardMCP(workspace=str(tmp_path))
        out = h.get_data()
        assert out == {"from": "fresh", "workspace": str(tmp_path)}
    finally:
        del sys.modules["dev_dashboard_data"]


# ─────────────────────────────────────────────────────────────────────
# DashboardMCP._generate_fresh_data — ImportError branch
# ─────────────────────────────────────────────────────────────────────

def test_generate_fresh_data_import_error_returns_stub(tmp_path, monkeypatch):
    """If dev_dashboard_data cannot be imported, return the error stub
    with timestamp=None and workspace=echoed.

    We force ImportError by installing a meta_path finder that blocks
    dev_dashboard_data. (Removing the module from sys.modules is not
    enough because the real file is on sys.path and would be re-found.)
    """
    monkeypatch.delenv("MAS_WORKSPACE", raising=False)
    mod = _import_tool()

    class _BlockFinder:
        """Meta-path finder that raises ImportError for one specific name."""
        def find_spec(self, fullname, path, target=None):
            if fullname == "dev_dashboard_data":
                raise ImportError(f"blocked: {fullname}")
            return None

    blocker = _BlockFinder()
    sys.meta_path.insert(0, blocker)
    try:
        h = mod.DashboardMCP(workspace=str(tmp_path))
        out = h._generate_fresh_data()
        assert out == {
            "error": "Dashboard generator not available",
            "timestamp": None,
            "workspace": str(tmp_path),
        }
    finally:
        try:
            sys.meta_path.remove(blocker)
        except ValueError:
            pass


def test_generate_fresh_data_calls_generate_data_when_available(tmp_path, monkeypatch):
    """When dev_dashboard_data IS importable, _generate_fresh_data
    delegates to generate_data(workspace).
    """
    monkeypatch.delenv("MAS_WORKSPACE", raising=False)
    mod = _import_tool()
    fake_mod = type(sys)("dev_dashboard_data")
    fake_mod.generate_data = lambda ws: {"via": "generator", "ws": ws}
    sys.modules["dev_dashboard_data"] = fake_mod
    try:
        h = mod.DashboardMCP(workspace=str(tmp_path))
        out = h._generate_fresh_data()
        assert out == {"via": "generator", "ws": str(tmp_path)}
    finally:
        del sys.modules["dev_dashboard_data"]


# ─────────────────────────────────────────────────────────────────────
# DashboardMCP.handle_request — five branches
# ─────────────────────────────────────────────────────────────────────

def test_handle_request_dashboard_data_method(tmp_path, monkeypatch):
    """method='ui/dashboard/data' → routes to get_data()."""
    monkeypatch.delenv("MAS_WORKSPACE", raising=False)
    mod = _import_tool()
    fake_mod = type(sys)("dev_dashboard_data")
    fake_mod.generate_data = lambda ws: {"routed": "get_data"}
    sys.modules["dev_dashboard_data"] = fake_mod
    try:
        h = mod.DashboardMCP(workspace=str(tmp_path))
        out = h.handle_request("ui/dashboard/data", {})
        assert out == {"routed": "get_data"}
    finally:
        del sys.modules["dev_dashboard_data"]


def test_handle_request_dashboard_colon_data_alias(tmp_path, monkeypatch):
    """method='dashboard:data' (colon alias) is also routed to get_data()."""
    monkeypatch.delenv("MAS_WORKSPACE", raising=False)
    mod = _import_tool()
    fake_mod = type(sys)("dev_dashboard_data")
    fake_mod.generate_data = lambda ws: {"routed": "via_colon_alias"}
    sys.modules["dev_dashboard_data"] = fake_mod
    try:
        h = mod.DashboardMCP(workspace=str(tmp_path))
        out = h.handle_request("dashboard:data", {})
        assert out == {"routed": "via_colon_alias"}
    finally:
        del sys.modules["dev_dashboard_data"]


def test_handle_request_refresh_method(tmp_path, monkeypatch):
    """method='ui/dashboard/refresh' → routes to _generate_fresh_data()."""
    monkeypatch.delenv("MAS_WORKSPACE", raising=False)
    mod = _import_tool()
    fake_mod = type(sys)("dev_dashboard_data")
    fake_mod.generate_data = lambda ws: {"routed": "fresh", "ws": ws}
    sys.modules["dev_dashboard_data"] = fake_mod
    try:
        h = mod.DashboardMCP(workspace=str(tmp_path))
        out = h.handle_request("ui/dashboard/refresh", {})
        assert out == {"routed": "fresh", "ws": str(tmp_path)}
    finally:
        del sys.modules["dev_dashboard_data"]


def test_handle_request_subscribe_method(tmp_path, monkeypatch):
    """method='ui/dashboard/subscribe' → returns subscribed+events from params."""
    monkeypatch.delenv("MAS_WORKSPACE", raising=False)
    mod = _import_tool()
    h = mod.DashboardMCP(workspace=str(tmp_path))
    out = h.handle_request("ui/dashboard/subscribe", {"events": ["a", "b"]})
    assert out == {"subscribed": True, "events": ["a", "b"]}


def test_handle_request_subscribe_method_events_default_empty(tmp_path, monkeypatch):
    """subscribe without 'events' key in params → events=[]."""
    monkeypatch.delenv("MAS_WORKSPACE", raising=False)
    mod = _import_tool()
    h = mod.DashboardMCP(workspace=str(tmp_path))
    out = h.handle_request("ui/dashboard/subscribe", {})
    assert out == {"subscribed": True, "events": []}


def test_handle_request_unknown_method(tmp_path, monkeypatch):
    """Unknown method → {"error": "Unknown method: <name>"}."""
    monkeypatch.delenv("MAS_WORKSPACE", raising=False)
    mod = _import_tool()
    h = mod.DashboardMCP(workspace=str(tmp_path))
    out = h.handle_request("nope/not/a/method", {})
    assert out == {"error": "Unknown method: nope/not/a/method"}


# ─────────────────────────────────────────────────────────────────────
# DashboardMCP.notify_update — data vs get_data() branches
# ─────────────────────────────────────────────────────────────────────

def test_notify_update_uses_supplied_data(tmp_path, monkeypatch):
    """data= supplied → params=data, no get_data() call needed."""
    monkeypatch.delenv("MAS_WORKSPACE", raising=False)
    mod = _import_tool()
    h = mod.DashboardMCP(workspace=str(tmp_path))
    payload = {"x": 1, "y": 2}
    out = h.notify_update("ui/dashboard/refresh", data=payload)
    assert out == {"method": "ui/dashboard/refresh", "params": payload}


def test_notify_update_falls_back_to_get_data(tmp_path, monkeypatch):
    """data= omitted → params = self.get_data()."""
    monkeypatch.delenv("MAS_WORKSPACE", raising=False)
    mod = _import_tool()
    fake_mod = type(sys)("dev_dashboard_data")
    fake_mod.generate_data = lambda ws: {"from": "notify_fallback", "ws": ws}
    sys.modules["dev_dashboard_data"] = fake_mod
    try:
        h = mod.DashboardMCP(workspace=str(tmp_path))
        out = h.notify_update("ui/dashboard/data")
        assert out == {
            "method": "ui/dashboard/data",
            "params": {"from": "notify_fallback", "ws": str(tmp_path)},
        }
    finally:
        del sys.modules["dev_dashboard_data"]


# ─────────────────────────────────────────────────────────────────────
# Module-level get_dashboard_data — sanity check
# ─────────────────────────────────────────────────────────────────────

def test_get_dashboard_data_module_function(tmp_path, monkeypatch):
    """The module-level get_dashboard_data() instantiates the class
    and calls get_data() — both branches covered (workspace arg
    forwarded, default None handled).
    """
    monkeypatch.delenv("MAS_WORKSPACE", raising=False)
    mod = _import_tool()
    fake_mod = type(sys)("dev_dashboard_data")
    fake_mod.generate_data = lambda ws: {"via": "module_func", "ws": ws}
    sys.modules["dev_dashboard_data"] = fake_mod
    try:
        out = mod.get_dashboard_data(workspace=str(tmp_path))
        assert out == {"via": "module_func", "ws": str(tmp_path)}
    finally:
        del sys.modules["dev_dashboard_data"]


# ─────────────────────────────────────────────────────────────────────
# __main__ guard — subprocess invocation (full script)
# ─────────────────────────────────────────────────────────────────────

def test_main_subprocess_no_workspace_arg(tmp_path, monkeypatch):
    """Running the tool with no argv[1] → uses '.', prints JSON, rc=0."""
    monkeypatch.chdir(tmp_path)
    # Stub dev_dashboard_data so the import inside _generate_fresh_data
    # works predictably (the subprocess will import the real one,
    # which is fine — it returns a valid dict). We only assert that
    # the output is valid JSON and rc==0.
    result = subprocess.run(
        [sys.executable, str(TOOL)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    # The CLI does json.dumps(..., indent=2) — must be valid JSON.
    parsed = json.loads(result.stdout)
    assert isinstance(parsed, dict)


def test_main_subprocess_with_workspace_arg(tmp_path, monkeypatch):
    """Running with argv[1]='/some/path' → uses that path."""
    monkeypatch.chdir(tmp_path)
    result = subprocess.run(
        [sys.executable, str(TOOL), str(tmp_path)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    parsed = json.loads(result.stdout)
    assert isinstance(parsed, dict)


# ─────────────────────────────────────────────────────────────────────
# __main__ guard — runpy in-process for precise line attribution
# ─────────────────────────────────────────────────────────────────────

def test_main_runpy_under_dunder_main(monkeypatch, capsys, tmp_path):
    """Execute the script via `runpy.run_path(run_name='__main__')` to
    hit the `if __name__ == "__main__":` block IN-PROCESS, so coverage
    attributes the line to this test. We pass argv[1]=tmp_path so the
    generator runs against a known directory; the result is json.dump'd
    to stdout.
    """
    # Stub dev_dashboard_data so we don't shell out to git/python.
    fake_mod = type(sys)("dev_dashboard_data")
    fake_mod.generate_data = lambda ws: {"runpy": True, "ws": ws}
    sys.modules["dev_dashboard_data"] = fake_mod
    try:
        monkeypatch.setattr(sys, "argv", ["mcp_dashboard_server.py", str(tmp_path)])
        runpy.run_path(str(TOOL), run_name="__main__")
        captured = capsys.readouterr()
        # The script's last line is `print(json.dumps(data, indent=2, ensure_ascii=False))`
        parsed = json.loads(captured.out)
        assert parsed == {"runpy": True, "ws": str(tmp_path)}
    finally:
        del sys.modules["dev_dashboard_data"]
