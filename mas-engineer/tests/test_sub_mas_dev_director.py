"""
test_sub_mas_dev_director.py — sanity tests for dev-director.

Dev-director orchestrates dev-mas-engineer operations across 5
delegation domains: analyze, build, test, observe, git.

Run with:
    python3 -m pytest tests/test_sub_mas_dev_director.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-dev-director.yaml"


def test_dev_director_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_dev_director_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_dev_director_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_dev_director_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_dev_director_orchestrator():
    """Spec: orchestrator — delegates based on task domain."""
    content = RECIPE.read_text()
    assert "Orchestrat" in content or "orchestrate" in content.lower(), \
        "dev-director must be an orchestrator"
    assert "Delegate" in content or "delegate" in content, \
        "dev-director must delegate to sub-agents"


def test_dev_director_only_orchestration():
    """Spec: ONLY orchestration — NO direct execution."""
    content = RECIPE.read_text()
    assert "ONLY orchestration" in content, \
        "dev-director must declare ONLY-orchestration rule"
    assert "NO direct execution" in content, \
        "dev-director must forbid direct execution"


def test_dev_director_5_delegation_domains():
    """Spec: 5 delegation domains — analyze, build, test, observe, git."""
    content = RECIPE.read_text()
    for sub in ("sub_mas-dev-analyzer", "sub_mas-dev-builder",
                "sub_mas-dev-tester", "sub_mas-dev-observer",
                "sub_mas-git-operator"):
        assert sub in content, \
            f"dev-director must delegate to: {sub}"


def test_dev_director_r01_r09_r10():
    """Spec: R01 (no changes w/o user), R09 (domain separation), R10 (CORONASHIELD)."""
    content = RECIPE.read_text()
    assert "R01" in content, "dev-director must declare R01"
    assert "R09" in content, "dev-director must declare R09"
    assert "R10" in content, "dev-director must declare R10"
    assert "CORONASHIELD" in content, \
        "dev-director must declare CORONASHIELD"


def test_dev_director_sub_recipes():
    """Director must have sub_recipes for its delegation domains."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = [s.get("name") for s in data.get("sub_recipes", [])]
    # At least 4 of 5 expected
    expected = {"sub_mas-dev-analyzer", "sub_mas-dev-builder",
                "sub_mas-dev-tester", "sub_mas-dev-observer"}
    found = set(subs) & expected
    assert len(found) >= 4, \
        f"dev-director must have ≥4 dev sub_recipes. subs: {subs}"


def test_dev_director_git_clean_commit():
    """Spec: git-operator is v2.0.0 CLEAN-COMMIT (NO `git add -A`)."""
    content = RECIPE.read_text()
    assert "CLEAN-COMMIT" in content, \
        "dev-director must declare git-operator CLEAN-COMMIT"
    assert "git add -A" in content, \
        "dev-director must explicitly forbid git add -A"
