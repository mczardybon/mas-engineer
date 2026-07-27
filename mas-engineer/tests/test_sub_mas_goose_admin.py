"""
test_sub_mas_goose_admin.py — sanity tests for goose-admin.

goose-admin v1.0.0 is the Goose-component manager (MAS-internal):
Manages sessions, skills, logs via dev_goose_manager.py.
ONLY goose — no framework-changes.

Per R101 EVIDENCE: R01+R09+R10 (2x) (script-wrapper with YAML output,
heavily CORONASHIELD-enforced).

Run with:
    python3 -m pytest tests/test_sub_mas_goose_admin.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-goose-admin.yaml"


def test_goose_admin_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_goose_admin_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_goose_admin_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_goose_admin_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_goose_admin_role():
    """Spec: MAS-internal: Manages Goose components (sessions/skills/logs)."""
    content = RECIPE.read_text()
    assert "Goose" in content or "goose" in content.lower(), \
        "goose-admin must reference Goose"
    assert "manage" in content.lower() or "Manage" in content, \
        "goose-admin must declare manage-role"
    # Should mention sessions/skills/logs
    for kw in ("session", "skill", "log"):
        assert kw.lower() in content.lower(), \
            f"goose-admin must mention {kw} component"


def test_goose_admin_only_goose():
    """Spec: ONLY goose — no framework-changes."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "ONLY goose" in flat or "only goose" in flat.lower() \
        or "ONLY Goose" in flat, \
        "goose-admin must declare ONLY-goose rule"
    assert "no framework" in flat.lower() or "framework-changes" in flat.lower(), \
        "goose-admin must forbid framework changes"


def test_goose_admin_delegates_to_dev_goose_manager():
    """Spec: delegates to tools/dev_goose_manager.py."""
    content = RECIPE.read_text()
    assert "dev_goose_manager" in content, \
        "goose-admin must reference dev_goose_manager tool"


def test_goose_admin_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "goose-admin must be single-role leaf"


def test_goose_admin_settings():
    """Spec: sub-agent settings (timeout=600, max_steps=100, deepseek)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "goose-admin must have timeout=600"
    assert settings.get("max_steps") == 100, \
        "goose-admin must have max_steps=100"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "goose-admin must use deepseek model"


def test_goose_admin_r01_r09_r10_x2():
    """Spec: R01, R09, R10 (2x) (heavily CORONASHIELD-enforced)."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert flat.count("R01") >= 1, "goose-admin must declare R01"
    assert flat.count("R09") >= 1, "goose-admin must declare R09"
    assert flat.count("R10") >= 2, \
        f"goose-admin must declare R10 2x. Found: {flat.count('R10')}"
    assert flat.count("CORONASHIELD") >= 2, \
        f"goose-admin must declare CORONASHIELD 2x. Found: {flat.count('CORONASHIELD')}"


def test_goose_admin_uses_recovery_immune():
    """Spec: R10 CORONASHIELD delegates YAML validation to
    sub_mas-recovery-immune (the YAML validator).
    """
    content = RECIPE.read_text()
    assert "sub_mas-recovery-immune" in content, \
        "goose-admin must reference sub_mas-recovery-immune for YAML validation"
