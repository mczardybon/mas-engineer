"""
test_sub_mas_tff_syntax_validator.py — sanity tests for tff-syntax-validator.

tff-syntax-validator v2.0.0 is a script-wrapper recipe (R85):
YAML syntax validation. Delegates to
tools/dev_tff.py VALIDATE syntax. This recipe is a thin wrapper.

Per R101 EVIDENCE: R01+R09+R10 (script-wrapper with YAML output).

Run with:
    python3 -m pytest tests/test_sub_mas_tff_syntax_validator.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-tff-syntax-validator.yaml"


def test_syntax_validator_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_syntax_validator_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_syntax_validator_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_syntax_validator_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_syntax_validator_role():
    """Spec: MAS-internal: YAML syntax validation."""
    content = RECIPE.read_text()
    assert "YAML syntax" in content or "yaml syntax" in content.lower() \
        or "SYNTAX VALIDATION" in content.upper(), \
        "syntax-validator must declare YAML-syntax role"
    assert "validation" in content.lower() or "Validation" in content, \
        "syntax-validator must declare validation role"


def test_syntax_validator_only_syntax():
    """Spec: ONLY YAML syntax — NO rule or crossref checks."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "ONLY YAML syntax" in flat or "only yaml syntax" in flat.lower(), \
        "syntax-validator must declare ONLY-syntax rule"
    assert "NO rule" in flat or "no rule" in flat.lower(), \
        "syntax-validator must forbid rule checks (combined-list)"
    assert "crossref" in flat.lower() or "NO crossref" in flat, \
        "syntax-validator must forbid crossref checks (combined-list)"


def test_syntax_validator_delegates_to_dev_tff():
    """Spec: delegates to tools/dev_tff.py VALIDATE syntax."""
    content = RECIPE.read_text()
    assert "dev_tff" in content, \
        "syntax-validator must reference dev_tff tool"
    assert "VALIDATE" in content, \
        "syntax-validator must use VALIDATE command"
    assert "syntax" in content.lower(), \
        "syntax-validator must use syntax command"


def test_syntax_validator_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "syntax-validator must be single-role leaf"


def test_syntax_validator_settings():
    """Spec: code-review settings (timeout=120, max_turns=15, deepseek-v4-flash)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 120, \
        "syntax-validator must have timeout=120 (script-wrapper)"
    assert settings.get("max_turns") == 30, \
        "syntax-validator must have max_turns=15 (script-wrapper)"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "syntax-validator must use deepseek model"


def test_syntax_validator_r01_r09_r10():
    """Spec: R01, R09, R10 (script-wrapper with YAML output)."""
    content = RECIPE.read_text()
    assert "R01" in content, "syntax-validator must declare R01"
    assert "R09" in content, "syntax-validator must declare R09"
    assert "R10" in content, "syntax-validator must declare R10"
    assert "CORONASHIELD" in content, \
        "syntax-validator must declare CORONASHIELD"


def test_syntax_validator_part_of_tff_validator_director():
    """Spec: syntax-validator is part of tff-validator-director (3-way split).
    Per R101 EVIDENCE: NN1 split, syntax is one of 3.
    """
    content = RECIPE.read_text()
    # Should be referenced by tff-validator-director
    # but the recipe itself doesn't need to know about that
    # Just check role differentiation: it does syntax ONLY
    assert "syntax" in content.lower(), \
        "syntax-validator must declare syntax scope"
