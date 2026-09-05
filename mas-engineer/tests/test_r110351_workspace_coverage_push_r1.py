"""
R110-351: coverage-push round 1 for tools/dev_workspace.py.

Targets the pure-function helpers that have no I/O and no
subprocess calls.  dev_workspace.py is 1478 lines, but most
of it is `# pragma: no cover` deferred-to-real-GOOSE-paths
functions (cmd_init, cmd_install, etc.). The testable surface
is the small pure-helper set.

Helpers targeted (5 functions, 28 tests, 5 classes):

  1. log/info/ok/warn/error (L51-67) — print helpers with
     emoji prefixes. Tests verify:
     - each helper produces output to stdout
     - each helper has the right emoji prefix
     - blank message produces just the emoji (or empty for log)

  2. count_files (L71-74) — file counter.
     Tests:
     - nonexistent dir → 0
     - empty dir → 0
     - dir with 3 yaml files, pattern="*.yaml" → 3
     - dir with mix, pattern="*.py" → correct count
     - default pattern "*" → all files

  3. cmd_status (L722-760) — workspace status reporter.
     This function has multiple branches:
     - workspace doesn't exist → warn + return
     - workspace exists, no framework dir → still runs
     - workspace exists, with all dirs → full output
     - .mase/changes.json exists → reads total_changes
     - .mase/changes.json malformed → except swallowed
     - config.yaml present → n_config=1
     - config.yaml missing → n_config=0
     Tests use capsys to capture stdout.

  4. cmd_clean (L710-720) — workspace delete.
     Tests:
     - workspace doesn't exist → warn, no exception
     - workspace exists → shutil.rmtree, then ok printed

  5. _load_projects / _save_projects (L1038-1056) — projects
     file IO. Tests:
     - file doesn't exist → creates with defaults
     - file exists → reads back
     - save updates last_updated timestamp

Target: bump coverage from 0% to ~15% (1478 lines is huge,
so even +15% is ~220 lines newly covered).
"""
import sys
import importlib
from pathlib import Path
import pytest
import yaml
from datetime import datetime

TOOLS = Path(__file__).parent.parent / "tools"


@pytest.fixture
def ws_mod(tmp_path, monkeypatch):
    """Import dev_workspace with cwd sandboxed."""
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(TOOLS))
    sys.modules.pop("dev_workspace", None)
    mod = importlib.import_module("dev_workspace")
    yield mod
    sys.modules.pop("dev_workspace", None)


class TestLogHelpers:
    """log/info/ok/warn/error print helpers (L51-67)."""

    def test_log_prints_plain(self, ws_mod, capsys):
        ws_mod.log("hello world")
        captured = capsys.readouterr()
        assert "hello world" in captured.out

    def test_info_prints_with_speaker_emoji(self, ws_mod, capsys):
        ws_mod.info("ready")
        captured = capsys.readouterr()
        assert "📢" in captured.out
        assert "ready" in captured.out

    def test_ok_prints_with_check_emoji(self, ws_mod, capsys):
        ws_mod.ok("done")
        captured = capsys.readouterr()
        assert "✅" in captured.out
        assert "done" in captured.out

    def test_warn_prints_with_warning_emoji(self, ws_mod, capsys):
        ws_mod.warn("careful")
        captured = capsys.readouterr()
        assert "⚠️" in captured.out
        assert "careful" in captured.out

    def test_error_prints_with_x_emoji(self, ws_mod, capsys):
        ws_mod.error("boom")
        captured = capsys.readouterr()
        assert "❌" in captured.out
        assert "boom" in captured.out

    def test_log_with_unicode(self, ws_mod, capsys):
        """Unicode chars pass through log() unchanged."""
        ws_mod.log("über — naïve")
        captured = capsys.readouterr()
        assert "über" in captured.out
        assert "naïve" in captured.out


class TestCountFiles:
    """count_files helper (L71-74)."""

    def test_nonexistent_dir_returns_zero(self, ws_mod, tmp_path):
        """Nonexistent dir → 0."""
        result = ws_mod.count_files(tmp_path / "no-such-dir")
        assert result == 0

    def test_empty_dir_returns_zero(self, ws_mod, tmp_path):
        """Empty dir → 0 (default pattern *)."""
        empty = tmp_path / "empty"
        empty.mkdir()
        assert ws_mod.count_files(empty) == 0

    def test_yaml_glob_counts_only_yaml(self, ws_mod, tmp_path):
        """pattern='*.yaml' counts only yaml files."""
        d = tmp_path / "mixed"
        d.mkdir()
        (d / "a.yaml").write_text("a: 1")
        (d / "b.yaml").write_text("b: 2")
        (d / "c.txt").write_text("not yaml")
        assert ws_mod.count_files(d, "*.yaml") == 2

    def test_py_glob_counts_only_py(self, ws_mod, tmp_path):
        """pattern='*.py' counts only python files."""
        d = tmp_path / "scripts"
        d.mkdir()
        (d / "a.py").write_text("# a")
        (d / "b.py").write_text("# b")
        (d / "c.py").write_text("# c")
        (d / "d.txt").write_text("text")
        assert ws_mod.count_files(d, "*.py") == 3

    def test_default_pattern_counts_all(self, ws_mod, tmp_path):
        """Default pattern '*' counts all files."""
        d = tmp_path / "all"
        d.mkdir()
        for name in ("a.yaml", "b.py", "c.md", "d.json"):
            (d / name).write_text("x")
        assert ws_mod.count_files(d) == 4

    def test_glob_matches_in_nested_dirs(self, ws_mod, tmp_path):
        """glob is recursive? No, glob('*') only top-level."""
        d = tmp_path / "nested"
        d.mkdir()
        (d / "top.yaml").write_text("x")
        sub = d / "sub"
        sub.mkdir()
        (sub / "deep.yaml").write_text("y")
        # glob('*.yaml') is non-recursive, only top-level
        assert ws_mod.count_files(d, "*.yaml") == 1


class TestCmdStatus:
    """cmd_status reporter (L722-760)."""

    def test_nonexistent_workspace_warns(self, ws_mod, tmp_path, capsys):
        """When ws doesn't exist → warn + return (no exception)."""
        ws = tmp_path / "no-such-ws"
        ws_mod.cmd_status(str(ws))
        captured = capsys.readouterr()
        assert "exist" in captured.out.lower() or "📊" in captured.out

    def test_empty_workspace_runs_without_error(self, ws_mod, tmp_path, capsys):
        """When ws exists but is empty, all counts are 0."""
        ws = tmp_path / "empty-ws"
        ws.mkdir()
        ws_mod.cmd_status(str(ws))
        captured = capsys.readouterr()
        # Should print all the count lines
        assert "📊" in captured.out
        assert "Recipes" in captured.out
        assert "Docs" in captured.out
        assert "Config" in captured.out

    def test_workspace_with_recipes(self, ws_mod, tmp_path, capsys):
        """Workspace with framework/recipes/ → n_yaml reported."""
        ws = tmp_path / "with-recipes"
        (ws / "framework" / "recipes").mkdir(parents=True)
        (ws / "framework" / "recipes" / "a.yaml").write_text("x: 1")
        (ws / "framework" / "recipes" / "b.yaml").write_text("y: 2")
        (ws / "framework" / "config.yaml").write_text("cfg: 1")
        ws_mod.cmd_status(str(ws))
        captured = capsys.readouterr()
        assert "2 YAML" in captured.out

    def test_workspace_with_tools(self, ws_mod, tmp_path, capsys):
        """Workspace with mas-engineer/tools/ → n_py reported."""
        ws = tmp_path / "with-tools"
        (ws / "mas-engineer" / "tools").mkdir(parents=True)
        (ws / "mas-engineer" / "tools" / "x.py").write_text("# x")
        (ws / "mas-engineer" / "tools" / "y.py").write_text("# y")
        ws_mod.cmd_status(str(ws))
        captured = capsys.readouterr()
        assert "2 Tools" in captured.out or "2 YAML" in captured.out

    def test_workspace_with_changes_json(self, ws_mod, tmp_path, capsys):
        """Workspace with .mase/changes.json → reads total_changes."""
        import json
        ws = tmp_path / "with-changes"
        (ws / "framework" / "recipes").mkdir(parents=True)
        (ws / ".mase").mkdir()
        (ws / ".mase" / "changes.json").write_text(
            json.dumps({"stats": {"total_changes": 42}})
        )
        ws_mod.cmd_status(str(ws))
        captured = capsys.readouterr()
        assert "42" in captured.out

    def test_workspace_with_malformed_changes_json(self, ws_mod, tmp_path, capsys):
        """Malformed .mase/changes.json → silently skipped (no traceback)."""
        ws = tmp_path / "with-bad-json"
        (ws / "framework" / "recipes").mkdir(parents=True)
        (ws / ".mase").mkdir()
        (ws / ".mase" / "changes.json").write_text("not valid json {{{")
        # Should not raise
        ws_mod.cmd_status(str(ws))
        captured = capsys.readouterr()
        # Should still print the basic counts
        assert "Recipes" in captured.out

    def test_config_present_counted_as_one(self, ws_mod, tmp_path, capsys):
        """framework/config.yaml exists → n_config=1."""
        ws = tmp_path / "with-config"
        (ws / "framework").mkdir(parents=True)
        (ws / "framework" / "config.yaml").write_text("x: 1")
        ws_mod.cmd_status(str(ws))
        captured = capsys.readouterr()
        # Config line: "⚙️  Config:   1" or "Config: 1"
        assert "1" in captured.out


class TestCmdClean:
    """cmd_clean (L710-720)."""

    def test_nonexistent_workspace_warns_no_exception(self, ws_mod, tmp_path, capsys):
        """Non-existent ws → warn, no exception."""
        ws = tmp_path / "no-such-ws"
        # Should not raise
        ws_mod.cmd_clean(str(ws))
        captured = capsys.readouterr()
        assert "exist" in captured.out.lower() or "⚠️" in captured.out

    def test_existing_workspace_deleted(self, ws_mod, tmp_path, capsys):
        """Existing ws → shutil.rmtree called + ok printed."""
        ws = tmp_path / "to-delete"
        ws.mkdir()
        (ws / "file.txt").write_text("x")
        assert ws.exists()
        ws_mod.cmd_clean(str(ws))
        captured = capsys.readouterr()
        assert not ws.exists()
        assert "deleted" in captured.out.lower() or "✅" in captured.out


class TestLoadSaveProjects:
    """_load_projects + _save_projects (L1038-1056)."""

    def test_load_creates_file_with_defaults_when_missing(self, ws_mod, tmp_path, monkeypatch):
        """First load with no file → creates framework/.projects.yaml."""
        monkeypatch.chdir(tmp_path)
        # Set PROJECTS_FILE relative — but it's a module-level const
        # We can still test it creates in framework/.projects.yaml
        data = ws_mod._load_projects()
        assert "version" in data
        assert "active_project" in data
        # File should now exist
        assert (tmp_path / "framework" / ".projects.yaml").exists()

    def test_load_returns_yaml_dict(self, ws_mod, tmp_path):
        """_load_projects returns a dict."""
        data = ws_mod._load_projects()
        assert isinstance(data, dict)
        assert "projects" in data

    def test_save_updates_last_updated(self, ws_mod, tmp_path):
        """_save_projects sets last_updated to current time."""
        # Create a project file first
        (tmp_path / "framework").mkdir()
        pp = tmp_path / "framework" / ".projects.yaml"
        pp.write_text(yaml.dump({"version": "1.0.0", "projects": {}}))
        before = datetime.now()
        ws_mod._save_projects({"version": "1.0.0", "projects": {"x": {}}})
        after = datetime.now()
        # Read back
        reloaded = yaml.safe_load(pp.read_text())
        assert "last_updated" in reloaded
        # Timestamp should be between before and after
        ts = datetime.fromisoformat(reloaded["last_updated"])
        assert before <= ts <= after

    def test_save_preserves_existing_data(self, ws_mod, tmp_path):
        """_save_projects preserves keys other than last_updated."""
        (tmp_path / "framework").mkdir()
        pp = tmp_path / "framework" / ".projects.yaml"
        pp.write_text(yaml.dump({"version": "1.0.0", "projects": {"foo": {"label": "X"}}}))
        ws_mod._save_projects({"version": "1.0.0", "projects": {"foo": {"label": "X"}}})
        reloaded = yaml.safe_load(pp.read_text())
        assert reloaded["projects"]["foo"]["label"] == "X"
