"""
test_sub_mas_team_packager.py — sanity tests for team-packager.

team-packager v1.0.0 is the team-packaging tool (MAS-internal):
Bundles a MAS-Engineer team (1 root + N sub-agents) into a
self-contained, goose-installable package. The resulting directory
runs WITHOUT MAS-Engineer.
Tasks: PACKAGE_TEAM.

Per R101 EVIDENCE: 0 R-number rules (tool wrapper, not a
workflow-executor). The recipe is the user-facing entry point
for packaging.

Run with:
    python3 -m pytest tests/test_sub_mas_team_packager.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-team-packager.yaml"


def test_team_packager_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_team_packager_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_team_packager_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_team_packager_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_team_packager_role():
    """Spec: Bundles team (1 root + N sub-agents) into self-contained package."""
    content = RECIPE.read_text()
    assert "package" in content.lower() or "Package" in content \
        or "PACKAGE" in content.upper(), \
        "team-packager must declare package role"
    assert "team" in content.lower() or "Team" in content, \
        "team-packager must declare team scope"
    # Self-contained package
    assert "self-contained" in content or "self_contained" in content \
        or "standalone" in content.lower() \
        or "self-contained" in content.lower(), \
        "team-packager must declare self-contained scope"


def test_team_packager_no_mas_engineer_dependency():
    """Spec: The resulting directory runs WITHOUT MAS-Engineer."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "WITHOUT MAS-Engineer" in flat \
        or "without mas-engineer" in flat.lower() \
        or "WITHOUT MAS" in flat, \
        "team-packager must declare WITHOUT-MAS-Engineer result"


def test_team_packager_tasks():
    """Spec: Supports PACKAGE_TEAM task."""
    content = RECIPE.read_text()
    assert "PACKAGE_TEAM" in content, \
        "team-packager must reference PACKAGE_TEAM task"


def test_team_packager_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "team-packager must be single-role leaf"


def test_team_packager_settings():
    """Spec: sub-agent settings (timeout=600, deepseek)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "team-packager must have timeout=600"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "team-packager must use deepseek model"


def test_team_packager_differs_from_director():
    """Spec: team-packager is the user-facing tool (no R-rules).
    team-packager-director is the orchestrator (R01+R09+R10).
    Per R101 EVIDENCE: role-based R-rule distribution.
    """
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    # Has 0 R-number rules (vs director which has 3+)
    assert flat.count("R0") == 0, \
        f"team-packager must not restate R-rules. Found: {flat.count('R0')}"
    # Uses openai_host for deepseek API
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert "openai_host" in settings or "deepseek" in settings.get("goose_model", "").lower(), \
        "team-packager must use deepseek API"
