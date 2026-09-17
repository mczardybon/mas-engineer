"""R110-441 — coverage-push r8: tools/dev_auto_project.py 0% → 100%.

Auto-detects framework structure (32 lines). Reads .mas-mode,
scans recipes dirs, returns JSON spec.

Targets:
- detect: defaults (project=None, main_recipe=None, mode='generic',
  prefix=None, has_tests=False, has_docs=False), .mas-mode set
  to "mas"/"framework"/"generic" → mode set, .mas-mode with other
  value → mode stays default 'generic', framework/dev-team/recipes/
  has main yaml (non sub_) → project='dev-team', prefix='fw-',
  main_recipe=filename; sub_*.yaml ignored; recipes/ in base has
  main yaml → project=basename(base), prefix='ag-', main_recipe
  set; framework recipe wins over recipes/, both dirs absent →
  project=None/main_recipe=None; has_tests=True if tests/ exists,
  has_docs=True if docs/ exists; project_path=abspath always set
- __main__: no args → uses os.getcwd(), prints JSON to stdout
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.dev_auto_project as ap  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# detect
# ─────────────────────────────────────────────────────────────────────
class TestDetect:
    def test_empty_dir_defaults(self, tmp_path):
        r = ap.detect(str(tmp_path))
        assert r["project"] is None
        assert r["main_recipe"] is None
        assert r["mode"] == "generic"
        assert r["prefix"] is None
        assert r["has_tests"] is False
        assert r["has_docs"] is False
        assert r["project_path"] == str(tmp_path.resolve())

    def test_mas_mode_file_mas(self, tmp_path):
        (tmp_path / ".mas-mode").write_text("mas\n")
        r = ap.detect(str(tmp_path))
        assert r["mode"] == "mas"

    def test_mas_mode_file_framework(self, tmp_path):
        (tmp_path / ".mas-mode").write_text("framework\n")
        r = ap.detect(str(tmp_path))
        assert r["mode"] == "framework"

    def test_mas_mode_file_generic(self, tmp_path):
        (tmp_path / ".mas-mode").write_text("generic\n")
        r = ap.detect(str(tmp_path))
        assert r["mode"] == "generic"

    def test_mas_mode_file_invalid_value(self, tmp_path):
        # Invalid mode value → stays default 'generic'
        (tmp_path / ".mas-mode").write_text("bogus\n")
        r = ap.detect(str(tmp_path))
        assert r["mode"] == "generic"

    def test_mas_mode_file_empty(self, tmp_path):
        # Empty .mas-mode → stays default
        (tmp_path / ".mas-mode").write_text("\n")
        r = ap.detect(str(tmp_path))
        assert r["mode"] == "generic"

    def test_framework_dev_team_recipes(self, tmp_path):
        fw_dir = tmp_path / "framework" / "dev-team" / "recipes"
        fw_dir.mkdir(parents=True)
        (fw_dir / "main.yaml").write_text("name: main")
        r = ap.detect(str(tmp_path))
        assert r["main_recipe"] == "main.yaml"
        assert r["project"] == "dev-team"
        assert r["prefix"] == "fw-"

    def test_framework_recipes_sub_ignored(self, tmp_path):
        fw_dir = tmp_path / "framework" / "dev-team" / "recipes"
        fw_dir.mkdir(parents=True)
        # Only sub_*.yaml → no main recipe found in framework
        (fw_dir / "sub_helper.yaml").write_text("name: helper")
        r = ap.detect(str(tmp_path))
        # Falls through to recipes/ check, which also doesn't exist
        assert r["main_recipe"] is None
        assert r["project"] is None

    def test_framework_recipes_mixed(self, tmp_path):
        # sub_*.yaml AND main.yaml → main picked
        fw_dir = tmp_path / "framework" / "dev-team" / "recipes"
        fw_dir.mkdir(parents=True)
        (fw_dir / "sub_helper.yaml").write_text("name: helper")
        (fw_dir / "main.yaml").write_text("name: main")
        r = ap.detect(str(tmp_path))
        assert r["main_recipe"] == "main.yaml"
        assert r["project"] == "dev-team"

    def test_recipes_dir_only(self, tmp_path):
        rc_dir = tmp_path / "recipes"
        rc_dir.mkdir()
        (rc_dir / "agent.yaml").write_text("name: agent")
        r = ap.detect(str(tmp_path))
        assert r["main_recipe"] == "agent.yaml"
        assert r["project"] == tmp_path.name
        assert r["prefix"] == "ag-"

    def test_recipes_dir_sub_ignored(self, tmp_path):
        rc_dir = tmp_path / "recipes"
        rc_dir.mkdir()
        (rc_dir / "sub_inner.yaml").write_text("name: inner")
        r = ap.detect(str(tmp_path))
        assert r["main_recipe"] is None

    def test_framework_wins_over_recipes(self, tmp_path):
        # Both dirs present → framework wins
        fw_dir = tmp_path / "framework" / "dev-team" / "recipes"
        fw_dir.mkdir(parents=True)
        (fw_dir / "fw_main.yaml").write_text("name: fw")
        rc_dir = tmp_path / "recipes"
        rc_dir.mkdir()
        (rc_dir / "rc_main.yaml").write_text("name: rc")
        r = ap.detect(str(tmp_path))
        assert r["main_recipe"] == "fw_main.yaml"
        assert r["project"] == "dev-team"
        assert r["prefix"] == "fw-"

    def test_recipes_dir_not_a_dir(self, tmp_path):
        # recipes/ as a file → not a dir → no detection
        (tmp_path / "recipes").write_text("not a dir")
        r = ap.detect(str(tmp_path))
        assert r["main_recipe"] is None

    def test_has_tests(self, tmp_path):
        (tmp_path / "tests").mkdir()
        r = ap.detect(str(tmp_path))
        assert r["has_tests"] is True

    def test_has_docs(self, tmp_path):
        (tmp_path / "docs").mkdir()
        r = ap.detect(str(tmp_path))
        assert r["has_docs"] is True

    def test_has_tests_and_docs(self, tmp_path):
        (tmp_path / "tests").mkdir()
        (tmp_path / "docs").mkdir()
        r = ap.detect(str(tmp_path))
        assert r["has_tests"] is True
        assert r["has_docs"] is True

    def test_project_path_abspath(self, tmp_path):
        # Relative path gets absolutified
        cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            r = ap.detect(".")
            assert r["project_path"] == str(tmp_path.resolve())
        finally:
            os.chdir(cwd)

    def test_recipes_dir_empty(self, tmp_path):
        rc_dir = tmp_path / "recipes"
        rc_dir.mkdir()
        # No yaml files
        r = ap.detect(str(tmp_path))
        assert r["main_recipe"] is None
        assert r["project"] is None


# Need os for project_path test
import os


# ─────────────────────────────────────────────────────────────────────
# __main__
# ─────────────────────────────────────────────────────────────────────
class TestMainExec:
    def test_no_args_uses_cwd(self, tmp_path, monkeypatch, capsys):
        # .mas-mode in tmp_path, run from tmp_path
        (tmp_path / ".mas-mode").write_text("mas\n")
        monkeypatch.chdir(tmp_path)
        old_argv = sys.argv
        sys.argv = ["dev_auto_project.py"]
        try:
            exec(compile(Path(__file__).resolve().parents[1]
                         .joinpath("tools/dev_auto_project.py")
                         .read_text(),
                         "dev_auto_project.py", "exec"),
                 {"__name__": "__main__",
                  "__file__": "dev_auto_project.py",
                  "os": os,
                  "sys": sys,
                  "json": json,
                  "Path": Path})
        finally:
            sys.argv = old_argv
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["mode"] == "mas"

    def test_with_arg(self, tmp_path, capsys):
        (tmp_path / ".mas-mode").write_text("framework\n")
        old_argv = sys.argv
        sys.argv = ["dev_auto_project.py", str(tmp_path)]
        try:
            exec(compile(Path(__file__).resolve().parents[1]
                         .joinpath("tools/dev_auto_project.py")
                         .read_text(),
                         "dev_auto_project.py", "exec"),
                 {"__name__": "__main__",
                  "__file__": "dev_auto_project.py",
                  "os": os,
                  "sys": sys,
                  "json": json,
                  "Path": Path})
        finally:
            sys.argv = old_argv
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["mode"] == "framework"
