"""
test_sub_mas_dev_observer.py — sanity tests for dev-observer.

Dev-observer v1.0.0 is a single-role agent. ONLY observation — NO
direct changes. Researches and monitors. Capabilities: web-researcher,
agent-guardian, health-reporter, monitor-runtime, monitor-session,
monitor-recovery, dashboard-refresh.

Run with:
    python3 -m pytest tests/test_sub_mas_dev_observer.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-dev-observer.yaml"


def test_dev_observer_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_dev_observer_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_dev_observer_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_dev_observer_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_dev_observer_only_observation():
    """Spec: ONLY observation — NO direct changes."""
    content = RECIPE.read_text()
    assert "ONLY observation" in content, \
        "dev-observer must declare ONLY-observation rule"
    assert "NO direct changes" in content, \
        "dev-observer must forbid direct changes"


def test_dev_observer_7_capabilities():
    """Spec: 7 sub-capabilities for research & monitoring."""
    content = RECIPE.read_text()
    for cap in ("sub_mas-web-researcher", "sub_mas-agent-guardian",
                "sub_mas-health-reporter", "sub_mas-monitor-runtime",
                "sub_mas-monitor-session", "sub_mas-monitor-recovery",
                "sub_mas-dashboard-refresh"):
        assert cap in content, \
            f"dev-observer must list capability: {cap}"


def test_dev_observer_r01_r09_r10():
    """Spec: R01 (no changes w/o user), R09 (domain), R10 (CORONASHIELD)."""
    content = RECIPE.read_text()
    assert "R01" in content, "dev-observer must declare R01"
    assert "R09" in content, "dev-observer must declare R09"
    assert "R10" in content, "dev-observer must declare R10"
    assert "CORONASHIELD" in content, \
        "dev-observer must declare CORONASHIELD"


def test_dev_observer_researches_techniques():
    """Spec: researches techniques and monitors system health."""
    content = RECIPE.read_text()
    assert "Research" in content or "research" in content, \
        "dev-observer must declare research role"


def test_dev_observer_no_sub_recipes():
    """Observer is a single-role leaf (capabilities listed but not sub_recipes)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "dev-observer must be a single-role leaf node"


def test_dev_observer_reports_to_director():
    """Spec: reports findings to dev-director."""
    content = RECIPE.read_text()
    assert "dev-director" in content, \
        "dev-observer must report to dev-director"
