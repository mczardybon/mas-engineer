"""R110-424 — coverage-push r6: dev_auto_project.py 0% → 100%.

Tiny pure-stdlib module: detect() + __main__ CLI. 22 stmts.
Targets:
- detect: empty path, mas-mode=mas, mas-mode=framework, mas-mode=generic,
  mas-mode=invalid, framework/dev-team/recipes (project=dev-team, prefix=fw-),
  recipes-only (project=basename, prefix=ag-), neither (project=None),
  has_tests+has_docs detection, sub_* skipped
- __main__ CLI: with arg, no arg (uses cwd)
"""

import io
import json
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.dev_auto_project as dap  # noqa: E402


@pytest.fixture
def ws(tmp_path):
    """Empty workspace."""
    return tmp_path


# =============================================================================
# detect()
# =============================================================================
class TestDetect:
    def test_empty_path_returns_defaults(self, ws):
        r = dap.detect(str(ws))
        assert r["project"] is None
        assert r["main_recipe"] is None
        assert r["mode"] == "generic"
        assert r["prefix"] is None
        assert r["has_tests"] is False
        assert r["has_docs"] is False
        assert r["project_path"] == str(ws)

    def test_mas_mode_marker(self, ws):
        (ws / ".mas-mode").write_text("mas")
        r = dap.detect(str(ws))
        assert r["mode"] == "mas"

    def test_framework_mode_marker(self, ws):
        (ws / ".mas-mode").write_text("framework")
        r = dap.detect(str(ws))
        assert r["mode"] == "framework"

    def test_generic_mode_marker(self, ws):
        (ws / ".mas-mode").write_text("generic")
        r = dap.detect(str(ws))
        assert r["mode"] == "generic"

    def test_invalid_mode_marker_falls_back(self, ws):
        (ws / ".mas-mode").write_text("bogus-mode")
        r = dap.detect(str(ws))
        # Invalid value → kept as default "generic"
        assert r["mode"] == "generic"

    def test_framework_dev_team_recipes(self, ws):
        fw = ws / "framework" / "dev-team" / "recipes"
        fw.mkdir(parents=True)
        (fw / "main.yaml").write_text("foo: bar")
        r = dap.detect(str(ws))
        assert r["project"] == "dev-team"
        assert r["main_recipe"] == "main.yaml"
        assert r["prefix"] == "fw-"

    def test_framework_sub_yaml_skipped(self, ws):
        fw = ws / "framework" / "dev-team" / "recipes"
        fw.mkdir(parents=True)
        (fw / "sub_a.yaml").write_text("x: 1")
        (fw / "main.yaml").write_text("foo: bar")
        r = dap.detect(str(ws))
        # Only "main.yaml" matches (sub_* skipped)
        assert r["main_recipe"] == "main.yaml"

    def test_recipes_only_no_framework(self, ws):
        rc = ws / "recipes"
        rc.mkdir()
        (rc / "myrecipe.yaml").write_text("a: 1")
        r = dap.detect(str(ws))
        assert r["project"] == ws.name
        assert r["main_recipe"] == "myrecipe.yaml"
        assert r["prefix"] == "ag-"

    def test_framework_takes_priority_over_recipes(self, ws):
        # Both framework and recipes exist → framework wins
        fw = ws / "framework" / "dev-team" / "recipes"
        fw.mkdir(parents=True)
        (fw / "fw_main.yaml").write_text("x: 1")
        rc = ws / "recipes"
        rc.mkdir()
        (rc / "rc_main.yaml").write_text("x: 1")
        r = dap.detect(str(ws))
        assert r["main_recipe"] == "fw_main.yaml"
        assert r["project"] == "dev-team"

    def test_has_tests_and_docs(self, ws):
        (ws / "tests").mkdir()
        (ws / "docs").mkdir()
        r = dap.detect(str(ws))
        assert r["has_tests"] is True
        assert r["has_docs"] is True

    def test_has_tests_only(self, ws):
        (ws / "tests").mkdir()
        r = dap.detect(str(ws))
        assert r["has_tests"] is True
        assert r["has_docs"] is False


# =============================================================================
# __main__ block (in-process via runpy, then directly via exec)
# =============================================================================
class TestCliMain:
    """Run the if __name__ == '__main__' block directly so coverage tracks it."""

    def _run_main(self, script_text, argv):
        """Exec the script's __main__ body in-process."""
        # Extract the __main__ block manually
        old_argv = sys.argv
        try:
            sys.argv = argv
            buf = io.StringIO()
            with redirect_stdout(buf):
                # Execute the whole script — detect() is defined at module level
                # and __main__ block runs at the end
                exec(compile(script_text, "dev_auto_project.py", "exec"),
                     {"__name__": "__main__", "__file__": "dev_auto_project.py"})
            return buf.getvalue()
        finally:
            sys.argv = old_argv

    def test_main_with_arg(self, tmp_path):
        script = (Path(__file__).resolve().parents[1] /
                  "tools" / "dev_auto_project.py").read_text()
        out = self._run_main(script, ["dev_auto_project.py", str(tmp_path)])
        data = json.loads(out)
        assert data["mode"] == "generic"
        assert data["project"] is None

    def test_main_no_arg_uses_cwd(self, tmp_path, monkeypatch):
        (tmp_path / ".mas-mode").write_text("framework")
        monkeypatch.chdir(tmp_path)
        script = (Path(__file__).resolve().parents[1] /
                  "tools" / "dev_auto_project.py").read_text()
        out = self._run_main(script, ["dev_auto_project.py"])
        data = json.loads(out)
        assert data["mode"] == "framework"
        assert data["project_path"] == str(tmp_path)

    def test_main_with_mas_mode(self, tmp_path):
        (tmp_path / ".mas-mode").write_text("mas")
        script = (Path(__file__).resolve().parents[1] /
                  "tools" / "dev_auto_project.py").read_text()
        out = self._run_main(script, ["dev_auto_project.py", str(tmp_path)])
        data = json.loads(out)
        assert data["mode"] == "mas"
