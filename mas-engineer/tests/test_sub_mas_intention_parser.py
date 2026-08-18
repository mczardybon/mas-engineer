"""
test_sub_mas_intention_parser.py — sanity tests for intention-parser.

intention-parser v1.0.0 is the user-intent analyzer (MAS-internal):
Analyzes user description → detects agent type, extracts boundaries
+ workflow, calls template generator → YAML + SOT entry.
Delegates to sub_mas-generic-init + sub_mas-team-packager.

Per R101 EVIDENCE: R10 only (no R01, no R09 — read-only analyzer
that calls a generator).

Run with:
    python3 -m pytest tests/test_sub_mas_intention_parser.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-intention-parser.yaml"


def test_intention_parser_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_intention_parser_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_intention_parser_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_intention_parser_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_intention_parser_role():
    """Spec: MAS-internal: Analyzes user description → generates YAML + SOT."""
    content = RECIPE.read_text()
    assert "Analyzes" in content or "analyzes" in content \
        or "ANALYSIS" in content.upper(), \
        "intention-parser must declare analysis role"
    assert "user description" in content.lower() \
        or "user_description" in content.lower(), \
        "intention-parser must declare user-description scope"
    # Should detect agent type
    assert "agent type" in content.lower() or "detect" in content.lower(), \
        "intention-parser must declare agent-type detection"


def test_intention_parser_delegates_to_generator():
    """Spec: ALWAYS calls template generator (no manual template)."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "generator" in flat.lower(), \
        "intention-parser must call generator"
    assert "ALWAYS" in flat or "always" in flat.lower(), \
        "intention-parser must ALWAYS call generator (no manual template)"


def test_intention_parser_delegation_map():
    """Spec: 2-way delegation map (generic-init + team-packager)."""
    content = RECIPE.read_text()
    for sub in ("sub_mas-generic-init", "sub_mas-team-packager"):
        assert sub in content, \
            f"intention-parser must reference {sub} in delegation map"


def test_intention_parser_2_sub_recipes():
    """Spec: exactly 2 sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = [s.get("name") for s in data.get("sub_recipes", [])]
    assert len(subs) == 2, \
        f"intention-parser must have 2 sub_recipes, got {len(subs)}: {subs}"


def test_intention_parser_settings():
    """Spec: sub-agent settings (timeout=600, max_turns=100, deepseek)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "intention-parser must have timeout=600"
    assert settings.get("max_turns") == 100, \
        "intention-parser must have max_turns=100"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "intention-parser must use deepseek model"


def test_intention_parser_r10_only():
    """Spec: R10 only — no R01, no R09.
    Per R101 EVIDENCE: read-only analyzer, calls generator
    but doesn't modify general-improver.
    """
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "R10" in flat, "intention-parser must declare R10"
    assert "CORONASHIELD" in flat, \
        "intention-parser must declare CORONASHIELD"
    assert "R01" not in flat, \
        "intention-parser must NOT have R01 (read-only analyzer)"
    assert "R09" not in flat, \
        "intention-parser must NOT have R09 (read-only analyzer)"
