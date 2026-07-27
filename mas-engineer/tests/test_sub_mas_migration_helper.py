"""
test_sub_mas_migration_helper.py — sanity tests for migration-helper.

migration-helper v1.0.0 is the migration-planner (MAS-internal):
Analyzes breaking changes between framework versions, generates
migration plan. Read-only analyzer — produces plan but doesn't
apply it.

Per R101 EVIDENCE: R10 (1x) only (read-only planner, no R01/R09).

Run with:
    python3 -m pytest tests/test_sub_mas_migration_helper.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-migration-helper.yaml"


def test_migration_helper_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_migration_helper_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_migration_helper_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_migration_helper_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_migration_helper_role():
    """Spec: MAS-internal: Analyzes breaking changes between framework
    versions, generates migration plan.
    """
    content = RECIPE.read_text()
    assert "breaking" in content.lower() or "Breaking" in content \
        or "BREAKING" in content, \
        "migration-helper must reference breaking changes"
    assert "version" in content.lower() or "Version" in content \
        or "VERSION" in content, \
        "migration-helper must reference versions"
    assert "migration" in content.lower() or "Migration" in content \
        or "MIGRATION" in content, \
        "migration-helper must declare migration role"


def test_migration_helper_read_only():
    """Spec: Read-only analyzer — produces plan but doesn't apply it.

    Note: the recipe delegates to .md file which has:
    L21: "Perform NO changes" (DRY_RUN only)
    L26: "NEVER without Confirmation" (R01 rule)
    """
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    # Recipe delegates to external .md file — check the .md file
    md_path = REPO_ROOT / "recipe" / "instructions" / "sub_mas-migration-helper.md"
    if md_path.exists():
        md_content = md_path.read_text()
        md_flat = re.sub(r"\s+", " ", md_content)
        assert "NO changes" in md_flat \
            or "no changes" in md_flat.lower() \
            or "Perform ANALYZE" in md_flat \
            or "ONLY plan" in md_flat, \
            "migration-helper .md must declare NO-changes or Perform-ANALYZE"
    # The recipe itself has 'ONLY plan migration' in instructions
    assert "ONLY plan" in flat or "only plan" in flat.lower() \
        or "generates migration plan" in flat, \
        "migration-helper must reference ONLY plan or generates migration plan"


def test_migration_helper_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "migration-helper must be single-role leaf"


def test_migration_helper_settings():
    """Spec: sub-agent settings (timeout=600, max_steps=100, deepseek)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "migration-helper must have timeout=600"
    assert settings.get("max_steps") == 100, \
        "migration-helper must have max_steps=100"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "migration-helper must use deepseek model"


def test_migration_helper_r10_only():
    """Spec: R10 (1x) only — no R01, no R09.
    Per R101 EVIDENCE: read-only planner, doesn't modify YAMLs.
    """
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert flat.count("R10") >= 1, \
        f"migration-helper must declare R10. Found: {flat.count('R10')}"
    assert "CORONASHIELD" in flat, \
        "migration-helper must declare CORONASHIELD"
    assert "R01" not in flat, \
        "migration-helper must NOT have R01 (read-only planner)"
    assert "R09" not in flat, \
        "migration-helper must NOT have R09 (read-only planner)"


def test_migration_helper_uses_recovery_immune():
    """Spec: R10 CORONASHIELD delegates YAML validation to
    sub_mas-recovery-immune.
    """
    content = RECIPE.read_text()
    assert "sub_mas-recovery-immune" in content, \
        "migration-helper must reference sub_mas-recovery-immune"
