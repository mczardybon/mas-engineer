"""
test_sub_mas_dev_tester.py — sanity tests for dev-tester.

Dev-tester v1.0.0 is a single-role agent. ONLY testing — NO direct
changes. Executes tests and reports results to dev-director.
Capabilities: test-runner, unix-test-runner, verification-runner,
e2e testing, pre-push validation.

Run with:
    python3 -m pytest tests/test_sub_mas_dev_tester.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-dev-tester.yaml"


def test_dev_tester_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_dev_tester_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_dev_tester_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_dev_tester_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_dev_tester_only_testing():
    """Spec: ONLY testing — NO direct changes."""
    content = RECIPE.read_text()
    assert "ONLY testing" in content, \
        "dev-tester must declare ONLY-testing rule"
    assert "NO direct changes" in content, \
        "dev-tester must forbid direct changes"


def test_dev_tester_5_capabilities():
    """Spec: 5 sub-capabilities for testing."""
    content = RECIPE.read_text()
    for cap in ("sub_mas-test-runner", "sub_mas-unix-test-runner",
                "sub_mas-verification-runner", "e2e-",
                "sub_mas-pre-push-validator"):
        assert cap in content, \
            f"dev-tester must list capability: {cap}"


def test_dev_tester_r01_r09_r10():
    """Spec: R01 (no changes w/o user), R09 (domain), R10 (CORONASHIELD)."""
    content = RECIPE.read_text()
    assert "R01" in content, "dev-tester must declare R01"
    assert "R09" in content, "dev-tester must declare R09"
    assert "R10" in content, "dev-tester must declare R10"
    assert "CORONASHIELD" in content, \
        "dev-tester must declare CORONASHIELD"


def test_dev_tester_reports_to_director():
    """Spec: reports results to dev-director."""
    content = RECIPE.read_text()
    assert "dev-director" in content, \
        "dev-tester must report to dev-director"


def test_dev_tester_no_sub_recipes():
    """Tester is a single-role leaf (capabilities listed but not sub_recipes)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "dev-tester must be a single-role leaf node"


def test_dev_tester_test_validate_verify():
    """Spec: tests, validates, and verifies correctness."""
    content = RECIPE.read_text()
    for verb in ("Test", "validate", "verify"):
        assert verb in content, \
            f"dev-tester must declare verb: {verb}"
