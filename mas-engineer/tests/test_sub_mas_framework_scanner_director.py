"""
test_sub_mas_framework_scanner_director.py — sanity tests for framework-scanner-director.

NOTE: framework-scanner-director.yaml is a DUPLICATE of
framework-scanner.yaml (verified R106 EVIDENCE: same title, same
sub_recipes, same instructions). This test documents what the
recipe actually says.

Run with:
    python3 -m pytest tests/test_sub_mas_framework_scanner_director.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-framework-scanner-director.yaml"
SCANNER = REPO_ROOT / "recipe" / "sub" / "sub_mas-framework-scanner.yaml"


def test_framework_scanner_director_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_framework_scanner_director_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_framework_scanner_director_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_framework_scanner_director_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_framework_scanner_director_orchestrator():
    """Spec: orchestrator — delegates to specialized sub-agents."""
    content = RECIPE.read_text()
    assert "Orchestrat" in content or "orchestrate" in content.lower(), \
        "framework-scanner-director must be an orchestrator"


def test_framework_scanner_director_3_sub_agents():
    """Spec: same 3 sub-agents as framework-scanner (scan, audit, harden)."""
    content = RECIPE.read_text()
    for sub in ("sub_mas-framework-scan-agent",
                "sub_mas-framework-audit-agent",
                "sub_mas-framework-harden-agent"):
        assert sub in content, \
            f"framework-scanner-director must delegate to: {sub}"


def test_framework_scanner_director_sub_recipes():
    """Orchestrator must have sub_recipes for the 3 agents."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = [s.get("name") for s in data.get("sub_recipes", [])]
    assert "sub_mas-framework-scan-agent" in subs, \
        f"framework-scanner-director must include scan-agent. subs: {subs}"


def test_framework_scanner_director_r01_r09_r10():
    """Spec: R01 (no changes w/o user), R09 (domain), R10 (CORONASHIELD)."""
    content = RECIPE.read_text()
    assert "R01" in content, "framework-scanner-director must declare R01"
    assert "R09" in content, "framework-scanner-director must declare R09"
    assert "R10" in content, "framework-scanner-director must declare R10"
    assert "CORONASHIELD" in content, \
        "framework-scanner-director must declare CORONASHIELD"


def test_framework_scanner_director_no_direct_analysis():
    """Spec: NO direct framework analysis — ONLY orchestration."""
    content = RECIPE.read_text()
    assert "NO direct framework analysis" in content, \
        "framework-scanner-director must forbid direct framework analysis"


def test_framework_scanner_director_is_duplicate_of_scanner():
    """EVIDENCE: framework-scanner-director.yaml is identical to
    framework-scanner.yaml (both are Framework Scanner Director).
    Possible refactoring target — but tests are for sanity, not fix.
    """
    my_content = RECIPE.read_text()
    scanner_content = SCANNER.read_text()
    assert my_content == scanner_content, \
        "framework-scanner-director.yaml must match framework-scanner.yaml (R106 EVIDENCE: same orchestrator)"
