"""
test_sub_mas_team_packager_validator.py — sanity tests for team-packager-validator.

team-packager-validator v1.0.0 is the team-package VALIDATOR (MAS-internal):
Validates existing team packages for completeness and correctness.
Single role: VALIDATE_PACKAGE.

Per R101 EVIDENCE: 0 R-number rules (tool wrapper, single-role).
Part of team-packager-director 2-way split (builder+validator).

Run with:
    python3 -m pytest tests/test_sub_mas_team_packager_validator.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-team-packager-validator.yaml"


def test_validator_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_validator_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_validator_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_validator_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_validator_role():
    """Spec: MAS-internal: Validates existing team packages for completeness
    and correctness.
    Single role: VALIDATE_PACKAGE.
    """
    content = RECIPE.read_text()
    assert "Validates" in content or "validate" in content.lower() \
        or "VALIDATE" in content, \
        "team-packager-validator must declare validate role"
    assert "completeness" in content.lower() or "Completeness" in content \
        or "correctness" in content.lower() or "Correctness" in content, \
        "team-packager-validator must declare completeness/correctness scope"


def test_validator_task_validate_package():
    """Spec: Single role: VALIDATE_PACKAGE."""
    content = RECIPE.read_text()
    assert "VALIDATE_PACKAGE" in content, \
        "team-packager-validator must reference VALIDATE_PACKAGE task"


def test_validator_no_building():
    """Spec: validator does NOT build — that's the builder's job."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "NO building" in flat or "no building" in flat.lower(), \
        "team-packager-validator must forbid building (combined-list)"


def test_validator_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "team-packager-validator must be single-role leaf"


def test_validator_settings():
    """Spec: sub-agent settings (timeout=600, max_steps=100, deepseek)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "team-packager-validator must have timeout=600"
    assert settings.get("max_steps") == 100, \
        "team-packager-validator must have max_steps=100"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "team-packager-validator must use deepseek model"


def test_validator_no_r_rules():
    """Spec: 0 R-number rules (tool wrapper, single-role).
    Per R101 EVIDENCE: tool wrappers don't restate R-rules
    (unlike workflow executors / action-takers).
    """
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert flat.count("R0") == 0, \
        f"team-packager-validator must not restate R-rules. " \
        f"Found: {flat.count('R0')}"


def test_validator_part_of_team_packager_director():
    """Spec: validator is one of 2 team-packager-director sub-agents.
    Per R101 EVIDENCE: 2-way split (builder+validator).
    """
    content = RECIPE.read_text()
    assert "VALIDATOR" in content or "validator" in content.lower() \
        or "Validates" in content, \
        "team-packager-validator must declare validator scope"
