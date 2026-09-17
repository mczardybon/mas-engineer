#!/usr/bin/env python3
"""
R110-518: Coverage test for tools/dev_auto_project.py (32 lines, 0% → 100%).

Context: dev_auto_project.py auto-detects the framework structure of a
project directory. Output: JSON dict with keys
{project, main_recipe, mode, has_tests, has_docs, prefix, project_path}.

Module structure (32 lines):
  - detect(path) — abspath(path), check .mas-mode file (3 valid modes:
    'mas', 'framework', 'generic'; default 'generic'). Then check
    framework/dev-team/recipes/ for non-sub_*.yaml → sets
    project='dev-team', prefix='fw-'. Then check recipes/ in path →
    sets project=basename, prefix='ag-'. Always sets has_tests,
    has_docs, project_path.
  - __main__ guard: takes sys.argv[1] (or cwd) and prints JSON.

Branch coverage strategy:
  - .mas-mode exists + valid mode
  - .mas-mode exists + invalid mode (no update)
  - .mas-mode absent (no update)
  - framework/recipes/ has yaml → first one wins
  - framework/recipes/ no yaml
  - framework/recipes/ has only sub_*.yaml (filtered out)
  - framework/recipes/ absent
  - recipes/ has yaml
  - recipes/ absent
  - has_tests True / False
  - has_docs True / False

This file covers every branch via 12 focused tests.
"""

import json
import runpy
import sys
from pathlib import Path

import pytest

# Import as tools.X for pytest-cov name tracking
import tools.dev_auto_project as ap  # noqa: E402


# ─── detect() ──────────────────────────────────────────────────────

def test_detect_minimal_project_returns_defaults(tmp_path):
    """Covers lines 7-9 + 25-28: empty dir → all defaults."""
    result = ap.detect(str(tmp_path))
    assert result['project'] is None
    assert result['main_recipe'] is None
    assert result['mode'] == 'generic'
    assert result['prefix'] is None
    assert result['has_tests'] is False
    assert result['has_docs'] is False
    assert result['project_path'] == str(tmp_path.resolve())  # abspath


def test_detect_mode_from_mas_mode_file(tmp_path):
    """Covers line 11-14: .mas-mode present + valid mode 'mas'."""
    (tmp_path / ".mas-mode").write_text("mas\n")
    result = ap.detect(str(tmp_path))
    assert result['mode'] == 'mas'


def test_detect_mode_framework_from_mas_mode_file(tmp_path):
    """Covers line 14 second valid value: 'framework'."""
    (tmp_path / ".mas-mode").write_text("framework")
    result = ap.detect(str(tmp_path))
    assert result['mode'] == 'framework'


def test_detect_invalid_mode_value_keeps_generic(tmp_path):
    """Covers line 14 False branch: .mas-mode has invalid value →
    mode stays at default 'generic'."""
    (tmp_path / ".mas-mode").write_text("invalid_mode\n")
    result = ap.detect(str(tmp_path))
    assert result['mode'] == 'generic'


def test_detect_finds_framework_dev_team_recipe(tmp_path):
    """Covers lines 15-19: framework/dev-team/recipes/ with yaml →
    project='dev-team', prefix='fw-', main_recipe=filename."""
    fw_dir = tmp_path / "framework" / "dev-team" / "recipes"
    fw_dir.mkdir(parents=True)
    (fw_dir / "main.yaml").write_text("recipe: x")
    # Add a sub_ to verify it gets filtered (line 18 startswith check)
    (fw_dir / "sub_helper.yaml").write_text("sub: y")
    result = ap.detect(str(tmp_path))
    assert result['main_recipe'] == "main.yaml"
    assert result['project'] == 'dev-team'
    assert result['prefix'] == 'fw-'


def test_detect_framework_dir_with_only_sub_recipes_no_match(tmp_path):
    """Covers line 18 filter: only sub_*.yaml → no main_recipe set
    from framework path (but recipes/ may still match)."""
    fw_dir = tmp_path / "framework" / "dev-team" / "recipes"
    fw_dir.mkdir(parents=True)
    (fw_dir / "sub_a.yaml").write_text("a: 1")
    (fw_dir / "sub_b.yaml").write_text("b: 2")
    result = ap.detect(str(tmp_path))
    # main_recipe not set because sub_* filtered out
    assert result['main_recipe'] is None
    assert result['project'] is None


def test_detect_recipes_dir_with_only_non_yaml_files_no_match(tmp_path):
    """Covers line 23 False branch (23->22 back-edge): recipes/ has
    files but none match the .yaml+not-sub_ filter → loop exits
    without setting main_recipe, falls through to line 25."""
    recipes = tmp_path / "recipes"
    recipes.mkdir()
    (recipes / "sub_x.yaml").write_text("x: 1")   # starts with sub_
    (recipes / "readme.txt").write_text("notes")  # not yaml
    result = ap.detect(str(tmp_path))
    assert result['main_recipe'] is None
    assert result['project'] is None


def test_detect_finds_recipes_dir_recipe(tmp_path):
    """Covers lines 20-24: recipes/ dir with yaml → project=basename,
    prefix='ag-', main_recipe=filename."""
    recipes = tmp_path / "recipes"
    recipes.mkdir()
    (recipes / "team.yaml").write_text("recipe: x")
    result = ap.detect(str(tmp_path))
    assert result['main_recipe'] == "team.yaml"
    assert result['project'] == tmp_path.name
    assert result['prefix'] == 'ag-'


def test_detect_framework_recipes_takes_precedence(tmp_path):
    """Covers line 21 guard: if framework set main_recipe, recipes/
    dir is NOT consulted."""
    fw_dir = tmp_path / "framework" / "dev-team" / "recipes"
    fw_dir.mkdir(parents=True)
    (fw_dir / "framework_main.yaml").write_text("f: 1")
    recipes = tmp_path / "recipes"
    recipes.mkdir()
    (recipes / "user_main.yaml").write_text("u: 1")
    result = ap.detect(str(tmp_path))
    # Framework wins — prefix is 'fw-' not 'ag-'
    assert result['prefix'] == 'fw-'
    assert result['main_recipe'] == "framework_main.yaml"


def test_detect_has_tests_true(tmp_path):
    """Covers line 25 True branch: tests/ dir present."""
    (tmp_path / "tests").mkdir()
    result = ap.detect(str(tmp_path))
    assert result['has_tests'] is True


def test_detect_has_docs_true(tmp_path):
    """Covers line 26 True branch: docs/ dir present."""
    (tmp_path / "docs").mkdir()
    result = ap.detect(str(tmp_path))
    assert result['has_docs'] is True


def test_detect_full_project_layout(tmp_path):
    """Covers ALL branches in one shot: .mas-mode + framework + recipes
    + tests + docs."""
    # .mas-mode valid
    (tmp_path / ".mas-mode").write_text("framework\n")
    # framework/dev-team/recipes
    fw = tmp_path / "framework" / "dev-team" / "recipes"
    fw.mkdir(parents=True)
    (fw / "main.yaml").write_text("x: 1")
    (fw / "sub_x.yaml").write_text("y: 1")
    # recipes (won't be used because framework matched first)
    rec = tmp_path / "recipes"
    rec.mkdir()
    (rec / "user.yaml").write_text("z: 1")
    # tests + docs
    (tmp_path / "tests").mkdir()
    (tmp_path / "docs").mkdir()
    result = ap.detect(str(tmp_path))
    assert result['mode'] == 'framework'
    assert result['project'] == 'dev-team'
    assert result['main_recipe'] == 'main.yaml'
    assert result['prefix'] == 'fw-'
    assert result['has_tests'] is True
    assert result['has_docs'] is True


# ─── __main__ guard ─────────────────────────────────────────────────

def test_main_block_via_runpy_no_arg_uses_cwd(tmp_path, monkeypatch, capsys):
    """Covers lines 30-32: no argv[1] → uses os.getcwd() as path.

    We need to chdir into a controlled tmp_path so the cwd test is
    deterministic. Note: chdir is not restored by runpy, so we
    monkeypatch os.getcwd instead.
    """
    # Set up the cwd layout
    (tmp_path / ".mas-mode").write_text("mas\n")
    (tmp_path / "tests").mkdir()
    # Monkeypatch os.getcwd to return our tmp_path
    import os as _os
    monkeypatch.setattr(_os, "getcwd", lambda: str(tmp_path))
    monkeypatch.setattr(sys, "argv", ["dev_auto_project.py"])
    runpy.run_path(ap.__file__, run_name="__main__")
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["mode"] == "mas"
    assert parsed["has_tests"] is True


def test_main_block_via_runpy_with_arg(tmp_path, monkeypatch, capsys):
    """Covers lines 30-32: argv[1] is the target path."""
    target = tmp_path / "myproj"
    target.mkdir()
    (target / "recipes").mkdir()
    (target / "recipes" / "main.yaml").write_text("x: 1")
    monkeypatch.setattr(sys, "argv",
                        ["dev_auto_project.py", str(target)])
    runpy.run_path(ap.__file__, run_name="__main__")
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["main_recipe"] == "main.yaml"
    assert parsed["project"] == "myproj"
    assert parsed["prefix"] == "ag-"
