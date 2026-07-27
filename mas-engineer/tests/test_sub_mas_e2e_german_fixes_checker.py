"""
test_sub_mas_e2e_german_fixes_checker.py — sanity tests for e2e-german-fixes-checker.

e2e-german-fixes-checker v1.0.0 is the test-runner (MAS-internal)
for the e2e-verify-german-fixes workflow. Runs T4 (workflow count)
and T5 (YAML parse validation) — does NOT change anything.

Per R101 EVIDENCE: 0 R-number rules (test-runner, no YAML storage,
no framework changes).

Run with:
    python3 -m pytest tests/test_sub_mas_e2e_german_fixes_checker.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-e2e-german-fixes-checker.yaml"


def test_checker_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_checker_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_checker_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_checker_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_checker_role():
    """Spec: Runs T4 (workflow count) and T5 (YAML parse validation)."""
    content = RECIPE.read_text()
    assert "T4" in content, "checker must reference T4 test"
    assert "T5" in content, "checker must reference T5 test"
    assert "workflow count" in content.lower() or "workflow_count" in content.lower() \
        or "still shows 130" in content, \
        "checker must declare workflow-count scope"
    assert "YAML parse" in content or "yaml parse" in content.lower() \
        or "validation" in content.lower(), \
        "checker must declare YAML-validation scope"


def test_checker_no_changes():
    """Spec: ONLY T4+T5 checking — no changes."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "ONLY T4" in flat or "only T4" in flat.lower() \
        or "ONLY T4+T5" in flat, \
        "checker must declare ONLY-T4+T5 rule"
    assert "no changes" in flat.lower(), \
        "checker must forbid changes"


def test_checker_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "checker must be single-role leaf"


def test_checker_settings():
    """Spec: sub-agent settings (timeout=600, max_steps=50, temperature=0.3)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "checker must have timeout=600"
    assert settings.get("max_steps") == 50, \
        "checker must have max_steps=50"
    assert settings.get("temperature") == 0.3, \
        "checker must have temperature=0.3"


def test_checker_no_r_rules():
    """Spec: checker has 0 R-number rules (test-runner only)."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert flat.count("R0") == 0, \
        f"checker must not restate R-rules. Found: {flat.count('R0')}"


def test_checker_mas_internal():
    """Spec: MAS-internal scope."""
    content = RECIPE.read_text()
    assert "MAS-internal" in content or "mas-engineer" in content.lower(), \
        "checker must declare MAS-internal scope"
