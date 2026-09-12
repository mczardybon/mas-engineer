"""R110-450 — coverage-push r8: tools/mcp_dashboard_server.py 0% → 100%.

MCP dashboard server (81 lines): caches data.json, falls back to
fresh generator, handles MCP methods, notifies updates.

Targets:
- DashboardMCP.__init__: workspace=arg or env MAS_WORKSPACE or '.'.
  dashboard_dir = workspace + '.mase/dashboards'.
- get_data: if data.json exists and loads → that dict. On JSON
  decode error → fresh data. If file missing → fresh data.
- _generate_fresh_data: tries `from dev_dashboard_data import
  generate_data`; on ImportError → {"error", timestamp:None,
  workspace}; otherwise calls generate_data(workspace).
  Note: import is bare so requires dev_dashboard_data on sys.path.
- handle_request: 'ui/dashboard/data' or 'dashboard:data' →
  get_data(); 'ui/dashboard/refresh' → _generate_fresh_data();
  'ui/dashboard/subscribe' → {"subscribed": True, "events":
  params.get('events', [])}; else → {"error": "Unknown method: ..."}.
- notify_update(event, data=None): returns {"method": event,
  "params": data or self.get_data()}.
- get_dashboard_data(workspace=None): instantiates and returns
  get_data().
- __main__: argv[1]=workspace (or '.'); prints json.dumps.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.mcp_dashboard_server as ds  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# __init__
# ─────────────────────────────────────────────────────────────────────
class TestInit:
    def test_explicit_workspace(self):
        h = ds.DashboardMCP(workspace="/tmp/foo")
        assert h.workspace == "/tmp/foo"
        assert h.dashboard_dir == "/tmp/foo/.mase/dashboards"

    def test_env_workspace(self, monkeypatch):
        monkeypatch.setenv("MAS_WORKSPACE", "/env/ws")
        h = ds.DashboardMCP()
        assert h.workspace == "/env/ws"
        assert h.dashboard_dir == "/env/ws/.mase/dashboards"

    def test_default_dot(self, monkeypatch):
        monkeypatch.delenv("MAS_WORKSPACE", raising=False)
        h = ds.DashboardMCP()
        assert h.workspace == "."
        assert h.dashboard_dir == "./.mase/dashboards"


# ─────────────────────────────────────────────────────────────────────
# get_data
# ─────────────────────────────────────────────────────────────────────
class TestGetData:
    def test_no_data_file(self, tmp_path, monkeypatch):
        # Empty workspace → falls through to _generate_fresh_data.
        # Stub generate_data so we don't need real dev_dashboard_data.
        monkeypatch.setattr(ds.DashboardMCP,
                            "_generate_fresh_data",
                            lambda self: {"fresh": True})
        h = ds.DashboardMCP(workspace=str(tmp_path))
        assert h.get_data() == {"fresh": True}

    def test_valid_data_file(self, tmp_path):
        dash_dir = tmp_path / ".mase" / "dashboards"
        dash_dir.mkdir(parents=True)
        data_file = dash_dir / "data.json"
        data_file.write_text(json.dumps({"cached": 1}))
        h = ds.DashboardMCP(workspace=str(tmp_path))
        assert h.get_data() == {"cached": 1}

    def test_corrupt_data_file(self, tmp_path, monkeypatch):
        dash_dir = tmp_path / ".mase" / "dashboards"
        dash_dir.mkdir(parents=True)
        (dash_dir / "data.json").write_text("{ invalid json")
        monkeypatch.setattr(ds.DashboardMCP,
                            "_generate_fresh_data",
                            lambda self: {"fresh": True})
        h = ds.DashboardMCP(workspace=str(tmp_path))
        # JSON decode error → fresh data fallback
        assert h.get_data() == {"fresh": True}


# ─────────────────────────────────────────────────────────────────────
# _generate_fresh_data
# ─────────────────────────────────────────────────────────────────────
class TestGenerateFreshData:
    def test_import_error_fallback(self, tmp_path, monkeypatch):
        # Force ImportError on dev_dashboard_data import.
        import builtins
        orig_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "dev_dashboard_data":
                raise ImportError("simulated")
            return orig_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        h = ds.DashboardMCP(workspace=str(tmp_path))
        data = h._generate_fresh_data()
        assert "error" in data
        assert "timestamp" in data
        assert data["timestamp"] is None
        assert data["workspace"] == str(tmp_path)


# ─────────────────────────────────────────────────────────────────────
# handle_request
# ─────────────────────────────────────────────────────────────────────
class TestHandleRequest:
    def test_data_method_slash(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ds.DashboardMCP, "get_data",
                            lambda self: {"k": 1})
        h = ds.DashboardMCP(workspace=str(tmp_path))
        assert h.handle_request("ui/dashboard/data", {}) == {"k": 1}

    def test_data_method_colon(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ds.DashboardMCP, "get_data",
                            lambda self: {"k": 2})
        h = ds.DashboardMCP(workspace=str(tmp_path))
        assert h.handle_request("dashboard:data", {}) == {"k": 2}

    def test_refresh_method(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ds.DashboardMCP,
                            "_generate_fresh_data",
                            lambda self: {"refreshed": True})
        h = ds.DashboardMCP(workspace=str(tmp_path))
        assert h.handle_request("ui/dashboard/refresh", {}) == \
            {"refreshed": True}

    def test_subscribe_method(self, tmp_path):
        h = ds.DashboardMCP(workspace=str(tmp_path))
        result = h.handle_request(
            "ui/dashboard/subscribe",
            {"events": ["x", "y"]})
        assert result == {"subscribed": True, "events": ["x", "y"]}

    def test_subscribe_no_events(self, tmp_path):
        h = ds.DashboardMCP(workspace=str(tmp_path))
        result = h.handle_request("ui/dashboard/subscribe", {})
        assert result == {"subscribed": True, "events": []}

    def test_unknown_method(self, tmp_path):
        h = ds.DashboardMCP(workspace=str(tmp_path))
        result = h.handle_request("foo/bar", {})
        assert "error" in result
        assert "foo/bar" in result["error"]


# ─────────────────────────────────────────────────────────────────────
# notify_update
# ─────────────────────────────────────────────────────────────────────
class TestNotifyUpdate:
    def test_with_data(self, tmp_path):
        h = ds.DashboardMCP(workspace=str(tmp_path))
        r = h.notify_update("evt", {"x": 1})
        assert r == {"method": "evt", "params": {"x": 1}}

    def test_data_none_uses_get_data(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ds.DashboardMCP, "get_data",
                            lambda self: {"auto": True})
        h = ds.DashboardMCP(workspace=str(tmp_path))
        r = h.notify_update("evt2")
        assert r == {"method": "evt2", "params": {"auto": True}}


# ─────────────────────────────────────────────────────────────────────
# get_dashboard_data (module-level)
# ─────────────────────────────────────────────────────────────────────
class TestModuleFn:
    def test_with_workspace(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ds.DashboardMCP, "get_data",
                            lambda self: {"ws": self.workspace})
        d = ds.get_dashboard_data(str(tmp_path))
        assert d == {"ws": str(tmp_path)}

    def test_default_none(self, monkeypatch):
        monkeypatch.setattr(ds.DashboardMCP, "get_data",
                            lambda self: {"x": True})
        d = ds.get_dashboard_data()
        assert d == {"x": True}


# ─────────────────────────────────────────────────────────────────────
# __main__  (via subprocess for coverage)
# ─────────────────────────────────────────────────────────────────────
class TestMain:
    def test_main_with_arg(self, tmp_path):
        # Write a data.json so it has something to print
        d = tmp_path / ".mase" / "dashboards"
        d.mkdir(parents=True)
        (d / "data.json").write_text(json.dumps({"hello": "world"}))
        r = subprocess.run(
            ['python3', 'tools/mcp_dashboard_server.py', str(tmp_path)],
            capture_output=True, text=True,
            cwd='/workspace/dev-branch/mas-engineer-cleanup/mas-engineer')
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data == {"hello": "world"}

    def test_main_default_dot(self):
        # Run with no arg → defaults to '.', prints fallback (likely
        # import-error dict since dev_dashboard_data isn't on path).
        r = subprocess.run(
            ['python3', 'tools/mcp_dashboard_server.py'],
            capture_output=True, text=True,
            cwd='/workspace/dev-branch/mas-engineer-cleanup/mas-engineer')
        assert r.returncode == 0
        # Either fresh generator succeeded, or import-error fallback
        data = json.loads(r.stdout)
        assert "workspace" in data or "error" in data
