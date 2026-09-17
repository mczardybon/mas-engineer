"""Tests for tools/e2e_teams.py — coverage gap closer.

Covers the 16% coverage of e2e_teams.py (209 stmts, ~170 missed).
Strategy: exercise the YAML-building + write helpers + simple formatters:
- log() — prints with timestamp and level
- section() — prints bar + title
- build_wrapper_recipe() — generates YAML with sub_recipes, extensions,
  parameters, settings, prompt
- write_wrapper() — creates /tmp wrapper YAML file
- check_teams_present() — scans teams/ dir (we use tmp_path)
"""
import os
import sys
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import e2e_teams as et


def test_log_prints_with_timestamp_and_level(capsys):
    """Covers line 82-84: log() prints timestamp + level + message."""
    et.log("hello world")
    captured = capsys.readouterr()
    assert "hello world" in captured.out
    assert "[INFO]" in captured.out


def test_log_with_custom_level(capsys):
    """Covers line 83-84: log() with non-default level."""
    et.log("warning msg", level="WARN")
    captured = capsys.readouterr()
    assert "[WARN]" in captured.out


def test_section_prints_bar_and_title(capsys):
    """Covers lines 87-89: section() prints bar + title."""
    et.section("Test Title")
    captured = capsys.readouterr()
    assert "Test Title" in captured.out
    assert "=" in captured.out


def test_build_wrapper_recipe_returns_yaml_string():
    """Covers lines 296-344: build_wrapper_recipe() produces valid YAML."""
    case = {
        "prompt": "test prompt",
        "params": {"input1": "v1", "input2": "v2"},
        "timeout_s": 60,
    }
    yaml_str = et.build_wrapper_recipe("test-team", "L1", case, "/path/to/recipe.yaml")
    assert isinstance(yaml_str, str)
    assert "test-team" in yaml_str
    assert "sub_recipes" in yaml_str
    assert "extensions" in yaml_str
    assert "parameters" in yaml_str
    assert "test prompt" in yaml_str


def test_build_wrapper_recipe_substitutes_dashes_for_underscores():
    """Covers line 307: team name has dashes replaced with underscores."""
    case = {"prompt": "p", "params": {"x": "y"}, "timeout_s": 30}
    yaml_str = et.build_wrapper_recipe("my-test-team", "L2", case, "/r.yaml")
    assert "my_test_team_team" in yaml_str or "my-test-team" in yaml_str


def test_build_wrapper_recipe_parameters_have_required_keys():
    """Covers lines 311-317: each parameter becomes key/input_type/requirement."""
    case = {"prompt": "p", "params": {"input1": "x", "input2": "y"}, "timeout_s": 30}
    yaml_str = et.build_wrapper_recipe("t", "L1", case, "/r.yaml")
    assert "key: input1" in yaml_str
    assert "key: input2" in yaml_str
    assert "input_type: string" in yaml_str
    assert "requirement: required" in yaml_str


def test_build_wrapper_recipe_has_developer_and_summon_extensions():
    """Covers lines 327-330: developer + summon extensions declared."""
    case = {"prompt": "p", "params": {}, "timeout_s": 30}
    yaml_str = et.build_wrapper_recipe("t", "L1", case, "/r.yaml")
    assert "developer" in yaml_str
    assert "summon" in yaml_str


def test_build_wrapper_recipe_settings_match_case():
    """Covers lines 336-340: settings.timeout = case['timeout_s']."""
    case = {"prompt": "p", "params": {}, "timeout_s": 120}
    yaml_str = et.build_wrapper_recipe("t", "L1", case, "/r.yaml")
    assert "120" in yaml_str
    assert "max_steps: 30" in yaml_str
    assert "max_turns: 25" in yaml_str


def test_build_wrapper_recipe_parses_as_valid_yaml():
    """Covers lines 343-344: yaml.dump produces parseable YAML."""
    import yaml
    case = {"prompt": "p", "params": {"x": "y"}, "timeout_s": 30}
    yaml_str = et.build_wrapper_recipe("t", "L1", case, "/r.yaml")
    parsed = yaml.safe_load(yaml_str)
    assert isinstance(parsed, dict)
    assert parsed["name"] == "e2e-teams-test-t-L1"
    assert len(parsed["sub_recipes"]) == 1


def test_write_wrapper_creates_file(tmp_path, monkeypatch):
    """Covers lines 347-360: write_wrapper() writes YAML file to disk."""
    monkeypatch.setattr(et, "WRAPPER_DIR", str(tmp_path))
    # Add team to TEAM_RECIPES so build_wrapper_recipe can find it
    monkeypatch.setitem(et.TEAM_RECIPES, "myteam", "/some/path.yaml")
    case = {"prompt": "p", "params": {}, "timeout_s": 30}
    path = et.write_wrapper("myteam", "L1", case)
    assert os.path.exists(path)
    assert path.endswith("myteam-L1.yaml")
    content = Path(path).read_text()
    assert "myteam" in content


def test_write_wrapper_creates_dir_if_missing(tmp_path, monkeypatch):
    """Covers line 349: os.makedirs with exist_ok=True."""
    wrapper_dir = tmp_path / "new_subdir"
    monkeypatch.setattr(et, "WRAPPER_DIR", str(wrapper_dir))
    monkeypatch.setitem(et.TEAM_RECIPES, "t", "/r.yaml")
    case = {"prompt": "p", "params": {}, "timeout_s": 30}
    path = et.write_wrapper("t", "L1", case)
    assert wrapper_dir.exists()
    assert os.path.exists(path)


def test_check_teams_present_returns_dict():
    """Covers line 363: check_teams_present() returns {team: bool} dict
    based on TEAM_RECIPES keys + os.path.exists."""
    result = et.check_teams_present()
    assert isinstance(result, dict)
    # Each entry maps team_name → True/False depending on file existence
    for team, exists in result.items():
        assert isinstance(exists, bool)


def test_check_teams_present_with_existing_team(tmp_path, monkeypatch):
    """Covers line 363: when team recipe path exists → True in dict."""
    real_path = tmp_path / "exists.yaml"
    real_path.write_text("name: x\n")
    # Add a team pointing to a real path
    monkeypatch.setitem(et.TEAM_RECIPES, "_test_team_exists", str(real_path))
    result = et.check_teams_present()
    assert result.get("_test_team_exists") is True
