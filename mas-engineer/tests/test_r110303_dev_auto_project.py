"""R110-303: 100% coverage tests for tools/dev_auto_project.py.

CRITICAL — pre-existing count-assertion pitfall (R110-300a):
  Do NOT use `assert "N type" in output` literals anywhere in this file
  (not in asserts, not in function names, not in docstrings, not in
  comments). See skill `mas-engineer-count-assert-re-pitfall`.
"""
import importlib.util
import json
import os
import runpy
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parent.parent / "tools" / "dev_auto_project.py"


def _import_tool():
    """Load the tool by file path so tests run in isolation.

    Coverage-attribution trick: `pytest-cov` instruments any module whose
    `__name__` starts with the `--cov` prefix (e.g. `tools.X`). Even
    though `tools/` has no `__init__.py` (intentional — the tools are
    loaded as standalone scripts in production), we can still expose
    the file under the dotted name `tools.<name>` by:

      1. Inserting the parent of `tools/` (the repo root) onto sys.path
         — conftest.py already does this.
      2. Creating a synthetic `tools` module in `sys.modules` with
         `__path__ = [<the tools dir>]`, so Python treats it as a
         package even without an `__init__.py` on disk.
      3. Using `importlib.util.spec_from_file_location` to load
         `tools.<name>` from the file path. The `__name__` becomes
         `tools.<name>` and `pytest-cov` attributes coverage to
         `tools/<name>.py` correctly.

    This pattern is REUSED for all R110-303 top-level-tool tests.
    """
    REPO_ROOT = str(Path(TOOL).parent.parent)  # parent of `tools/`
    TOOLS_DIR = str(Path(TOOL).parent)         # the `tools/` dir
    if REPO_ROOT not in sys.path:
        sys.path.insert(0, REPO_ROOT)
    if "tools" not in sys.modules:
        import types
        pkg = types.ModuleType("tools")
        pkg.__path__ = [TOOLS_DIR]
        sys.modules["tools"] = pkg
    full_name = f"tools.{Path(TOOL).stem}"
    spec = importlib.util.spec_from_file_location(full_name, TOOL)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_detect_empty_directory_returns_all_defaults(tmp_path):
    """No framework/, no recipes/, no .mas-mode → main_recipe=None, mode='generic'."""
    mod = _import_tool()
    r = mod.detect(str(tmp_path))
    assert r["main_recipe"] is None
    assert r["mode"] == "generic"
    assert r["prefix"] is None
    assert r["has_tests"] is False
    assert r["has_docs"] is False


def test_detect_reads_mas_mode_mas(tmp_path):
    """`.mas-mode` containing 'mas' → mode='mas'."""
    mod = _import_tool()
    (tmp_path / ".mas-mode").write_text("mas")
    r = mod.detect(str(tmp_path))
    assert r["mode"] == "mas"


def test_detect_reads_mas_mode_framework(tmp_path):
    """`.mas-mode` containing 'framework' → mode='framework'."""
    mod = _import_tool()
    (tmp_path / ".mas-mode").write_text("framework")
    r = mod.detect(str(tmp_path))
    assert r["mode"] == "framework"


def test_detect_mas_mode_unknown_value_falls_back_to_generic(tmp_path):
    """`.mas-mode` containing an unknown mode (not mas/framework/generic) → mode stays 'generic'."""
    mod = _import_tool()
    (tmp_path / ".mas-mode").write_text("custom_unknown_mode")
    r = mod.detect(str(tmp_path))
    assert r["mode"] == "generic"


def test_detect_finds_framework_recipe(tmp_path):
    """`framework/dev-team/recipes/<file>.yaml` (not sub_) → main_recipe set, prefix 'fw-', project 'dev-team'."""
    mod = _import_tool()
    fw = tmp_path / "framework" / "dev-team" / "recipes"
    fw.mkdir(parents=True)
    (fw / "myrecipe.yaml").write_text("name: x")
    (fw / "sub_ignoreme.yaml").write_text("name: y")  # must be skipped
    r = mod.detect(str(tmp_path))
    assert r["main_recipe"] == "myrecipe.yaml"
    assert r["project"] == "dev-team"
    assert r["prefix"] == "fw-"


def test_detect_finds_recipes_dir_when_no_framework(tmp_path):
    """`<base>/recipes/<file>.yaml` (not sub_) → main_recipe set, prefix 'ag-', project = basename."""
    mod = _import_tool()
    rc = tmp_path / "recipes"
    rc.mkdir()
    (rc / "alpha.yaml").write_text("name: x")
    (rc / "sub_skip.yaml").write_text("name: y")
    r = mod.detect(str(tmp_path))
    assert r["main_recipe"] == "alpha.yaml"
    assert r["project"] == os.path.basename(str(tmp_path))
    assert r["prefix"] == "ag-"


def test_detect_framework_takes_priority_over_recipes(tmp_path):
    """Both `framework/dev-team/recipes/` and `recipes/` exist → framework wins, no fallthrough."""
    mod = _import_tool()
    fw = tmp_path / "framework" / "dev-team" / "recipes"
    fw.mkdir(parents=True)
    (fw / "fwyaml.yaml").write_text("name: fw")
    rc = tmp_path / "recipes"
    rc.mkdir()
    (rc / "rcyaml.yaml").write_text("name: rc")
    r = mod.detect(str(tmp_path))
    assert r["main_recipe"] == "fwyaml.yaml"
    assert r["project"] == "dev-team"


def test_detect_detects_tests_and_docs_dirs(tmp_path):
    """`tests/` and `docs/` subdirs → has_tests=True, has_docs=True."""
    mod = _import_tool()
    (tmp_path / "tests").mkdir()
    (tmp_path / "docs").mkdir()
    r = mod.detect(str(tmp_path))
    assert r["has_tests"] is True
    assert r["has_docs"] is True


def test_detect_includes_project_path_in_result(tmp_path):
    """Result dict always includes 'project_path' = absolute path."""
    mod = _import_tool()
    r = mod.detect(str(tmp_path))
    assert r["project_path"] == os.path.abspath(str(tmp_path))


def test_detect_relative_path_is_made_absolute(tmp_path):
    """Passing a relative path → result['project_path'] is absolute."""
    mod = _import_tool()
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        r = mod.detect(".")
        assert os.path.isabs(r["project_path"])
    finally:
        os.chdir(cwd)


def test_main_no_arg_uses_cwd(tmp_path, monkeypatch):
    """`__main__` with no args → detect(os.getcwd()) → JSON printed."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tests").mkdir()
    import subprocess
    result = subprocess.run(
        [sys.executable, str(TOOL)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["has_tests"] is True
    assert data["mode"] == "generic"


def test_main_with_path_arg(tmp_path):
    """`__main__ <path>` → detect(<path>) → JSON printed to stdout."""
    import subprocess
    result = subprocess.run(
        [sys.executable, str(TOOL), str(tmp_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["project_path"] == os.path.abspath(str(tmp_path))


def test_detect_recipes_dir_with_no_yaml_files_skipped(tmp_path):
    """`recipes/` exists but contains only sub_*.yaml → main_recipe stays None.
    Covers the os.listdir() branch where no .yaml without sub_ prefix is found."""
    mod = _import_tool()
    rc = tmp_path / "recipes"
    rc.mkdir()
    (rc / "sub_skipme.yaml").write_text("name: skip")
    (rc / "notyaml.txt").write_text("text")
    r = mod.detect(str(tmp_path))
    assert r["main_recipe"] is None
    assert r["prefix"] is None
    assert r["project"] is None


def test_detect_recipes_dir_when_framework_recipe_already_set_does_not_overwrite(tmp_path):
    """If framework/dev-team/recipes/ already populated main_recipe, the
    recipes/ loop's `not r['main_recipe']` guard fires (branch 22->25)."""
    mod = _import_tool()
    fw = tmp_path / "framework" / "dev-team" / "recipes"
    fw.mkdir(parents=True)
    (fw / "primary.yaml").write_text("name: p")
    rc = tmp_path / "recipes"
    rc.mkdir()
    (rc / "should_not_win.yaml").write_text("name: s")
    r = mod.detect(str(tmp_path))
    assert r["main_recipe"] == "primary.yaml"
    assert r["prefix"] == "fw-"
    assert r["project"] == "dev-team"


def test_main_block_invoked_with_no_args_from_cwd(tmp_path):
    """Run the script as a subprocess with NO args from a tmp_path cwd.
    Covers lines 31-32 (the `__main__` block) which take `sys.argv[1]`
    defaulting to `os.getcwd()`."""
    import subprocess
    # Make tmp_path have a detectable marker (tests/ dir) so we can verify
    # the script picked up the cwd.
    (tmp_path / "tests").mkdir()
    result = subprocess.run(
        [sys.executable, str(TOOL)],
        capture_output=True, text=True,
        cwd=str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["has_tests"] is True
    assert data["project_path"] == str(tmp_path)
