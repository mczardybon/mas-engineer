"""
test_sub_mas_test_fix_failures_validator_director.py — sanity tests for test-fix-failures-validator-director.

test-fix-failures-validator-director v1.0.0 is the orchestrator
(MAS-internal) for patch validation. Delegates to 3 specialized
sub-agents (NN1 split):
- syntax/yaml → sub_mas-tff-syntax-validator
- rules/compliance → sub_mas-tff-rule-validator
- crossref/consistency → sub_mas-tff-crossref-validator

ONLY orchestration — NO direct validation.

Per R101 EVIDENCE: R01+R09+R10 (full controller pattern).

Run with:
    python3 -m pytest tests/test_sub_mas_test_fix_failures_validator_director.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-test-fix-failures-validator-director.yaml"


def test_validator_director_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_validator_director_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_validator_director_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_validator_director_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_validator_director_orchestrator_role():
    """Spec: MAS-internal orchestrator for patch validation."""
    content = RECIPE.read_text()
    assert "Orchestrates" in content or "orchestrat" in content.lower() \
        or "Orchestrator" in content, \
        "validator-director must declare orchestrator role"
    assert "patch validation" in content.lower() or "validation" in content.lower(), \
        "validator-director must declare patch-validation scope"
    assert "MAS-internal" in content, \
        "validator-director must declare MAS-internal scope"


def test_validator_director_only_orchestration():
    """Spec: ONLY orchestration — NO direct validation."""
    content = RECIPE.read_text()
    assert "ONLY orchestration" in content, \
        "validator-director must declare ONLY-orchestration rule"
    assert "NO direct validation" in content \
        or "no direct validation" in content.lower(), \
        "validator-director must forbid direct validation (combined-list)"


def test_validator_director_delegation_map():
    """Spec: 3-way delegation map (syntax/rule/crossref)."""
    content = RECIPE.read_text()
    for sub in ("sub_mas-tff-syntax-validator",
                "sub_mas-tff-rule-validator",
                "sub_mas-tff-crossref-validator"):
        assert sub in content, \
            f"validator-director must reference {sub} in delegation map"


def test_validator_director_3_sub_recipes():
    """Spec: exactly 3 sub_recipes (NN1 split)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = [s.get("name") for s in data.get("sub_recipes", [])]
    assert len(subs) == 3, \
        f"validator-director must have 3 sub_recipes, got {len(subs)}: {subs}"


def test_validator_director_settings():
    """Spec: sub-agent settings (timeout=300, max_steps=50, temperature=0.3)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 300, \
        "validator-director must have timeout=300"
    assert settings.get("max_steps") == 50, \
        "validator-director must have max_steps=50"
    assert settings.get("temperature") == 0.3, \
        "validator-director must have temperature=0.3"


def test_validator_director_r01_r09_r10():
    """Spec: R01, R09, R10 (full controller pattern)."""
    content = RECIPE.read_text()
    assert "R01" in content, "validator-director must declare R01"
    assert "R09" in content, "validator-director must declare R09"
    assert "R10" in content, "validator-director must declare R10"
    assert "CORONASHIELD" in content, \
        "validator-director must declare CORONASHIELD"


def test_validator_director_no_direct_acting():
    """Spec: validator-director delegates to 3 sub-agents,
    does NOT directly perform validation.
    Per R101 EVIDENCE: this is a controller pattern.
    """
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    # Should forbid direct execution
    assert "NO direct" in flat, \
        "validator-director must forbid direct work"
    # Should delegate
    assert "Delegate" in content or "delegate" in content, \
        "validator-director must declare delegation"
