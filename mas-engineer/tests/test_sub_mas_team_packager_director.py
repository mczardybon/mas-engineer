"""
test_sub_mas_team_packager_director.py — sanity tests for team-packager-director.

team-packager-director v1.0.0 is the orchestrator (MAS-internal)
for team packaging. Delegates to 2 specialized sub-agents
(NN1 split):
- sub_mas-team-packager-builder
- sub_mas-team-packager-validator

ONLY orchestration — NO direct packaging or validation.

Per R101 EVIDENCE: R01+R09+R10 (full controller pattern).

Run with:
    python3 -m pytest tests/test_sub_mas_team_packager_director.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-team-packager-director.yaml"


def test_team_packager_director_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_team_packager_director_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_team_packager_director_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_team_packager_director_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_team_packager_director_orchestrator_role():
    """Spec: MAS-internal orchestrator for team packaging."""
    content = RECIPE.read_text()
    assert "Orchestrates" in content or "orchestrat" in content.lower() \
        or "Orchestrator" in content \
        or "DIRECTOR" in content.upper() or "Director" in content, \
        "team-packager-director must declare orchestrator role"
    assert "team packaging" in content.lower() or "Team Packaging" in content \
        or "team-packaging" in content, \
        "team-packager-director must declare team-packaging scope"


def test_team_packager_director_only_orchestration():
    """Spec: ONLY orchestration — NO direct packaging or validation."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "ONLY orchestration" in flat, \
        "team-packager-director must declare ONLY-orchestration rule"
    assert "NO direct packaging" in flat or "no direct packaging" in flat.lower(), \
        "team-packager-director must forbid direct packaging (combined-list)"
    assert "validation" in flat.lower() and "NO" in flat, \
        "team-packager-director must forbid direct validation (combined-list)"


def test_team_packager_director_delegation_map():
    """Spec: 2-way delegation map (builder + validator)."""
    content = RECIPE.read_text()
    for sub in ("sub_mas-team-packager-builder",
                "sub_mas-team-packager-validator"):
        assert sub in content, \
            f"team-packager-director must reference {sub} in delegation map"


def test_team_packager_director_2_sub_recipes():
    """Spec: exactly 2 sub_recipes (NN1 split)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = [s.get("name") for s in data.get("sub_recipes", [])]
    assert len(subs) == 2, \
        f"team-packager-director must have 2 sub_recipes, got {len(subs)}: {subs}"


def test_team_packager_director_settings():
    """Spec: orchestrator settings (timeout=600, max_turns=100, deepseek)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "team-packager-director must have timeout=600 (orchestrator)"
    assert settings.get("max_turns") == 100, \
        "team-packager-director must have max_turns=100 (orchestrator)"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "team-packager-director must use deepseek model"


def test_team_packager_director_r01_r09_r10():
    """Spec: R01, R09, R10 (full controller pattern)."""
    content = RECIPE.read_text()
    assert "R01" in content, "team-packager-director must declare R01"
    assert "R09" in content, "team-packager-director must declare R09"
    assert "R10" in content, "team-packager-director must declare R10"
    assert "CORONASHIELD" in content, \
        "team-packager-director must declare CORONASHIELD"
