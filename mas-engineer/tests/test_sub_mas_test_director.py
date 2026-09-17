"""
test_sub_mas_test_director.py — sanity tests for test-director.

test-director v1.0.0 is the orchestrator (MAS-internal) for
test operations. Delegates to 4 specialized sub-agents:
- run/execute/verify → sub_mas-test-executor
- analyze/reporter → sub_mas-test-reporter
- scan → sub_mas-test-scanner
- validate → sub_mas-test-validator

ONLY orchestration — NO direct test execution.

Run with:
    python3 -m pytest tests/test_sub_mas_test_director.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-test-director.yaml"


def test_director_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_director_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_director_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_director_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_director_orchestrator_role():
    """Spec: MAS-internal orchestrator for test operations."""
    content = RECIPE.read_text()
    assert "Orchestrator" in content or "orchestrat" in content.lower(), \
        "test-director must declare orchestrator role"
    assert "MAS-internal" in content, \
        "test-director must declare MAS-internal scope"
    assert "7 roles split into 4 focused subs" in content, \
        "test-director must declare 7→4 sub-split"


def test_director_only_orchestration():
    """Spec: ONLY orchestration — NO direct test execution."""
    content = RECIPE.read_text()
    assert "ONLY orchestration" in content, \
        "test-director must declare ONLY-orchestration rule"
    assert "NO direct test execution" in content \
        or "NO direct" in content, \
        "test-director must forbid direct execution"


def test_director_delegation_map():
    """Spec: 4-way delegation map (NN1 split)."""
    content = RECIPE.read_text()
    for sub in ("sub_mas-test-executor", "sub_mas-test-reporter",
                "sub_mas-test-scanner", "sub_mas-test-validator"):
        assert sub in content, \
            f"test-director must reference {sub} in delegation map"


def test_director_4_sub_recipes():
    """Spec: exactly 4 sub_recipes (one per NN1 split)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = [s.get("name") for s in data.get("sub_recipes", [])]
    assert len(subs) == 4, \
        f"test-director must have 4 sub_recipes, got {len(subs)}: {subs}"


def test_director_settings():
    """Spec: standard settings (timeout=600, max_turns=100, deepseek-v4-flash)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "test-director must have timeout=600"
    assert settings.get("max_turns") == 100, \
        "test-director must have max_turns=100"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "test-director must use deepseek model"


def test_director_r01_r09_r10():
    """Spec: R01, R09, R10 (full controller pattern)."""
    content = RECIPE.read_text()
    assert "R01" in content, "test-director must declare R01"
    assert "R09" in content, "test-director must declare R09"
    assert "R10" in content, "test-director must declare R10"
    assert "CORONASHIELD" in content, \
        "test-director must declare CORONASHIELD"
