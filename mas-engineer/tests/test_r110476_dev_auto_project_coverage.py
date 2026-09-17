"""R110-476 — coverage-push r13: tools/dev_auto_project.py 87% → 100%

23 stmts, 3 missed (lines 17-19: framework/dev-team/recipes branch).

KEY OBSERVATIONS:
- Pure detect() function: takes path string, returns dict.
- Reads .mas-mode file (optional). Accepts 'mas','framework','generic'.
- Scans framework/dev-team/recipes/ for *.yaml NOT starting with sub_
- Scans recipes/ for same (only if main_recipe not set yet)
- has_tests/has_docs: bool flags from dir existence
- project_path = abspath of input

PITFALLS:
- detect() uses os.path.abspath() → test paths MUST be real
  (use tmp_path which exists on disk).
- The two scan loops both set r['main_recipe'] AND r['project']
  AND r['prefix'] in one pass → 'framework' branch wins if both
  dirs exist.
- 'sub_*.yaml' files are SKIPPED in both scans (not main recipes).
- has_tests/has_docs use os.path.isdir which returns False for
  missing dirs.
"""

import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools import dev_auto_project as ap  # noqa: E402


@pytest.fixture
def empty_dir(tmp_path):
    """Bare directory — no framework/, recipes/, tests/, docs/"""
    return str(tmp_path)


@pytest.fixture
def framework_dir(tmp_path):
    """framework/dev-team/recipes/ structure with one main recipe"""
    fw = tmp_path / "framework" / "dev-team" / "recipes"
    fw.mkdir(parents=True)
    (fw / "main.yaml").write_text("recipe: x")
    (fw / "sub_other.yaml").write_text("recipe: y")
    return str(tmp_path)


@pytest.fixture
def recipes_dir(tmp_path):
    """recipes/ structure with one main recipe"""
    rc = tmp_path / "recipes"
    rc.mkdir()
    (rc / "main.yaml").write_text("recipe: x")
    (rc / "sub_other.yaml").write_text("recipe: y")
    return str(tmp_path)


@pytest.fixture
def full_dir(tmp_path):
    """All features present"""
    base = tmp_path
    (base / ".mas-mode").write_text("framework")
    (base / "tests").mkdir()
    (base / "docs").mkdir()
    fw = base / "framework" / "dev-team" / "recipes"
    fw.mkdir(parents=True)
    (fw / "main.yaml").write_text("recipe: x")
    rc = base / "recipes"
    rc.mkdir()
    (rc / "other.yaml").write_text("recipe: y")
    return str(base)


class TestDetect:
    def test_empty_dir(self, empty_dir):
        r = ap.detect(empty_dir)
        assert r["project"] is None
        assert r["main_recipe"] is None
        assert r["mode"] == "generic"
        assert r["prefix"] is None
        assert r["has_tests"] is False
        assert r["has_docs"] is False
        assert r["project_path"] == str(Path(empty_dir).resolve())

    def test_framework_branch(self, framework_dir):
        # framework/dev-team/recipes/main.yaml present
        r = ap.detect(framework_dir)
        assert r["project"] == "dev-team"
        assert r["main_recipe"] == "main.yaml"
        assert r["prefix"] == "fw-"
        assert r["has_tests"] is False

    def test_framework_skips_sub_files(self, framework_dir):
        r = ap.detect(framework_dir)
        # sub_other.yaml should NOT be the main_recipe
        assert r["main_recipe"] != "sub_other.yaml"

    def test_recipes_branch(self, recipes_dir):
        r = ap.detect(recipes_dir)
        assert r["main_recipe"] == "main.yaml"
        assert r["project"] == Path(recipes_dir).name  # basename
        assert r["prefix"] == "ag-"

    def test_recipes_skips_sub_files(self, recipes_dir):
        r = ap.detect(recipes_dir)
        assert r["main_recipe"] != "sub_other.yaml"

    def test_framework_wins_over_recipes(self, full_dir):
        # Both dirs exist → framework branch wins (first match)
        r = ap.detect(full_dir)
        assert r["project"] == "dev-team"
        assert r["prefix"] == "fw-"

    def test_mas_mode_mas(self, tmp_path):
        (tmp_path / ".mas-mode").write_text("mas")
        r = ap.detect(str(tmp_path))
        assert r["mode"] == "mas"

    def test_mas_mode_framework(self, tmp_path):
        (tmp_path / ".mas-mode").write_text("framework")
        r = ap.detect(str(tmp_path))
        assert r["mode"] == "framework"

    def test_mas_mode_generic(self, tmp_path):
        (tmp_path / ".mas-mode").write_text("generic")
        r = ap.detect(str(tmp_path))
        assert r["mode"] == "generic"

    def test_mas_mode_invalid_value(self, tmp_path):
        # Invalid value → falls back to default 'generic'
        (tmp_path / ".mas-mode").write_text("unknown_mode")
        r = ap.detect(str(tmp_path))
        assert r["mode"] == "generic"

    def test_mas_mode_empty_value(self, tmp_path):
        (tmp_path / ".mas-mode").write_text("")
        r = ap.detect(str(tmp_path))
        assert r["mode"] == "generic"

    def test_mas_mode_whitespace_only(self, tmp_path):
        # .strip() applied → empty after strip → falls back
        (tmp_path / ".mas-mode").write_text("   \n")
        r = ap.detect(str(tmp_path))
        assert r["mode"] == "generic"

    def test_has_tests_true(self, tmp_path):
        (tmp_path / "tests").mkdir()
        r = ap.detect(str(tmp_path))
        assert r["has_tests"] is True

    def test_has_docs_true(self, tmp_path):
        (tmp_path / "docs").mkdir()
        r = ap.detect(str(tmp_path))
        assert r["has_docs"] is True

    def test_has_tests_and_docs(self, tmp_path):
        (tmp_path / "tests").mkdir()
        (tmp_path / "docs").mkdir()
        r = ap.detect(str(tmp_path))
        assert r["has_tests"] is True
        assert r["has_docs"] is True

    def test_relative_path_becomes_absolute(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        r = ap.detect(".")
        assert r["project_path"] == os.path.abspath(".")

    def test_project_path_is_input_abspath(self, framework_dir):
        r = ap.detect(framework_dir)
        assert r["project_path"] == os.path.abspath(framework_dir)

    def test_multiple_yaml_in_recipes_picks_first(self, tmp_path):
        rc = tmp_path / "recipes"
        rc.mkdir()
        (rc / "z.yaml").write_text("z")
        (rc / "a.yaml").write_text("a")
        r = ap.detect(str(tmp_path))
        # os.listdir order is filesystem-dependent, but only ONE
        # main_recipe is set (break after first match)
        assert r["main_recipe"] in ("z.yaml", "a.yaml")


# ─────────────────────────────────────────────────────────────────────
# __main__ — CLI dispatch
# ─────────────────────────────────────────────────────────────────────
class TestMain:
    def test_main_default_cwd(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["dev_auto_project.py"])
        import runpy
        try:
            runpy.run_path("tools/dev_auto_project.py", run_name="__main__")
        except SystemExit:
            pass
        out = capsys.readouterr().out
        parsed = json.loads(out)
        # Detected against cwd (which is the repo root in test env)
        assert "project_path" in parsed

    def test_main_with_path(self, monkeypatch, capsys, tmp_path):
        monkeypatch.setattr(sys, "argv", ["dev_auto_project.py", str(tmp_path)])
        import runpy
        try:
            runpy.run_path("tools/dev_auto_project.py", run_name="__main__")
        except SystemExit:
            pass
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert parsed["project_path"] == os.path.abspath(str(tmp_path))

    def test_main_with_framework_path(self, monkeypatch, capsys, framework_dir):
        monkeypatch.setattr(sys, "argv", ["dev_auto_project.py", framework_dir])
        import runpy
        try:
            runpy.run_path("tools/dev_auto_project.py", run_name="__main__")
        except SystemExit:
            pass
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert parsed["project"] == "dev-team"
        assert parsed["main_recipe"] == "main.yaml"
