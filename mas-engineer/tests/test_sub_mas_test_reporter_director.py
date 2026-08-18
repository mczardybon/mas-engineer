"""
test_sub_mas_test_reporter_director.py — sanity tests for test-reporter-director.

test-reporter-director v1.0.0 is the orchestrator (MAS-internal)
for test result analysis and report generation. Delegates to
2 specialized sub-agents (NN1 split):
- analyze → sub_mas-test-reporter-analyzer
- generate → sub_mas-test-reporter-generator

ONLY orchestration — NO direct analysis/generation.

Run with:
    python3 -m pytest tests/test_sub_mas_test_reporter_director.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-test-reporter-director.yaml"


def test_reporter_director_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_reporter_director_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_reporter_director_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_reporter_director_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_reporter_director_orchestrator_role():
    """Spec: MAS-internal orchestrator for test result analysis."""
    content = RECIPE.read_text()
    assert "Orchestrator" in content or "orchestrat" in content.lower(), \
        "test-reporter-director must declare orchestrator role"
    assert "MAS-internal" in content, \
        "test-reporter-director must declare MAS-internal scope"
    assert "test result" in content.lower() or "Test result" in content, \
        "test-reporter-director must declare test-result scope"
    assert "report generation" in content.lower() \
        or "report" in content.lower(), \
        "test-reporter-director must declare report generation scope"


def test_reporter_director_only_orchestration():
    """Spec: ONLY orchestration — NO direct analysis/generation."""
    content = RECIPE.read_text()
    assert "ONLY" in content, \
        "test-reporter-director must declare ONLY rule"
    flat = re.sub(r"\s+", " ", content)
    # Should forbid direct analysis and generation
    assert "NO direct" in flat or "no direct" in flat.lower(), \
        "test-reporter-director must forbid direct work"


def test_reporter_director_delegation_map():
    """Spec: 2-way delegation map (NN1 split)."""
    content = RECIPE.read_text()
    for sub in ("sub_mas-test-reporter-analyzer",
                "sub_mas-test-reporter-generator"):
        assert sub in content, \
            f"test-reporter-director must reference {sub} in delegation map"


def test_reporter_director_2_sub_recipes():
    """Spec: exactly 2 sub_recipes (NN1 split)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = [s.get("name") for s in data.get("sub_recipes", [])]
    assert len(subs) == 2, \
        f"test-reporter-director must have 2 sub_recipes, got {len(subs)}: {subs}"


def test_reporter_director_settings():
    """Spec: standard settings (timeout=600, max_turns=100, deepseek-v4-flash)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "test-reporter-director must have timeout=600"
    assert settings.get("max_turns") == 100, \
        "test-reporter-director must have max_turns=100"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "test-reporter-director must use deepseek model"


def test_reporter_director_r01_r09_r10():
    """Spec: R01, R09, R10 (full controller pattern)."""
    content = RECIPE.read_text()
    assert "R01" in content, "test-reporter-director must declare R01"
    assert "R09" in content, "test-reporter-director must declare R09"
    assert "R10" in content, "test-reporter-director must declare R10"
    assert "CORONASHIELD" in content, \
        "test-reporter-director must declare CORONASHIELD"
