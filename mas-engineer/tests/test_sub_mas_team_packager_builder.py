"""
test_sub_mas_team_packager_builder.py — sanity tests for team-packager-builder.

team-packager-builder v1.0.0 is the team-package BUILDER (MAS-internal):
Builds standalone, goose-installable team packages.
Single role: PACKAGE_TEAM.

Per R101 EVIDENCE: 0 R-number rules (tool wrapper, single-role).
Part of team-packager-director 2-way split (builder+validator).

Run with:
    python3 -m pytest tests/test_sub_mas_team_packager_builder.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-team-packager-builder.yaml"


def test_builder_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_builder_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_builder_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_builder_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_builder_role():
    """Spec: MAS-internal: Builds standalone, goose-installable team packages.
    Single role: PACKAGE_TEAM.
    """
    content = RECIPE.read_text()
    assert "Build" in content or "build" in content, \
        "team-packager-builder must declare build role"
    assert "standalone" in content.lower() or "self-contained" in content \
        or "self_contained" in content or "goose-installable" in content \
        or "goose_installable" in content, \
        "team-packager-builder must declare standalone scope"


def test_builder_task_package_team():
    """Spec: Single role: PACKAGE_TEAM."""
    content = RECIPE.read_text()
    assert "PACKAGE_TEAM" in content, \
        "team-packager-builder must reference PACKAGE_TEAM task"


def test_builder_no_validation():
    """Spec: builder does NOT validate — that's the validator's job."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "NO validation" in flat or "no validation" in flat.lower(), \
        "team-packager-builder must forbid validation (combined-list)"


def test_builder_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "team-packager-builder must be single-role leaf"


def test_builder_settings():
    """Spec: sub-agent settings (timeout=600, max_steps=100, deepseek)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "team-packager-builder must have timeout=600"
    assert settings.get("max_steps") == 100, \
        "team-packager-builder must have max_steps=100"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "team-packager-builder must use deepseek model"


def test_builder_no_r_rules():
    """Spec: 0 R-number rules (tool wrapper, single-role).
    Per R101 EVIDENCE: tool wrappers don't restate R-rules
    (unlike workflow executors / action-takers).
    """
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert flat.count("R0") == 0, \
        f"team-packager-builder must not restate R-rules. " \
        f"Found: {flat.count('R0')}"


def test_builder_part_of_team_packager_director():
    """Spec: builder is one of 2 team-packager-director sub-agents.
    Per R101 EVIDENCE: 2-way split (builder+validator).
    """
    content = RECIPE.read_text()
    assert "BUILDER" in content or "builder" in content.lower(), \
        "team-packager-builder must declare builder scope"
