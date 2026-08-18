"""
test_sub_mas_test_scanner.py — sanity tests for test-scanner.

test-scanner v1.0.0 is the SCANNING/MONITORING agent. ONLY scanning
and monitoring — NO test execution. Delegates to 4 sub-agents
for actual health-scanning work.

Run with:
    python3 -m pytest tests/test_sub_mas_test_scanner.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-test-scanner.yaml"


def test_test_scanner_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_test_scanner_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_test_scanner_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_test_scanner_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_test_scanner_only_scanning():
    """Spec: ONLY scanning and monitoring — NO test execution."""
    content = RECIPE.read_text()
    assert "ONLY scanning" in content, \
        "test-scanner must declare ONLY-scanning rule"
    assert "NO test execution" in content, \
        "test-scanner must forbid test execution"


def test_test_scanner_4_capabilities():
    """Spec: 4 sub-capabilities — agent-guardian, framework-scanner,
    config-auditor, session-analyst.
    """
    content = RECIPE.read_text()
    for sub in ("sub_mas-agent-guardian", "sub_mas-framework-scanner",
                "sub_mas-config-auditor", "sub_mas-session-analyst"):
        assert sub in content, \
            f"test-scanner must declare capability: {sub}"


def test_test_scanner_reports_to_test_director():
    """Spec: reports to test-director."""
    content = RECIPE.read_text()
    assert "test-director" in content.lower() or "test director" in content.lower(), \
        "test-scanner must report to test-director"


def test_test_scanner_r01_r09_r10():
    """Spec: R01, R09, R10."""
    content = RECIPE.read_text()
    assert "R01" in content, "test-scanner must declare R01"
    assert "R09" in content, "test-scanner must declare R09"
    assert "R10" in content, "test-scanner must declare R10"
    assert "CORONASHIELD" in content, \
        "test-scanner must declare CORONASHIELD"


def test_test_scanner_no_sub_recipes_block():
    """test-scanner has capabilities in instructions, not as sub_recipes
    (soft-delegation pattern, R101 EVIDENCE).
    """
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = [s.get("name") for s in data.get("sub_recipes", [])]
    # If sub_recipes exist, they should be the 4 capabilities
    if subs:
        for sub in ("sub_mas-agent-guardian", "sub_mas-framework-scanner",
                    "sub_mas-config-auditor", "sub_mas-session-analyst"):
            assert sub in subs, \
                f"if sub_recipes declared, must include: {sub}. subs: {subs}"


def test_test_scanner_settings():
    """Spec: has settings (timeout, max_turns, goose_provider)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert "timeout" in settings, "test-scanner must have timeout setting"
    assert "max_turns" in settings, \
        "test-scanner must have max_turns setting"
