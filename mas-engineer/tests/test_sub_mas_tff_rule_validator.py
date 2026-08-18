"""
test_sub_mas_tff_rule_validator.py — sanity tests for tff-rule-validator.

tff-rule-validator v2.0.0 is a script-wrapper recipe (R85):
R01-R18 rule compliance. Delegates to
tools/dev_tff.py VALIDATE rule. This recipe is a thin wrapper.

Per R101 EVIDENCE: R01 (3x) + R04 (1x) + R09 (2x) + R10 (3x) — has
ALL R-rules (most R-rich script-wrapper because it validates ALL rules).

Run with:
    python3 -m pytest tests/test_sub_mas_tff_rule_validator.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-tff-rule-validator.yaml"


def test_rule_validator_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_rule_validator_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_rule_validator_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_rule_validator_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_rule_validator_role():
    """Spec: MAS-internal: R01-R18 rule compliance validation."""
    content = RECIPE.read_text()
    assert "R01-R18" in content or "R01-R18" in content.replace(" ", "") \
        or ("R01" in content and "R18" in content), \
        "rule-validator must declare R01-R18 rule scope"
    assert "rule" in content.lower() or "Rule" in content \
        or "RULE" in content.upper(), \
        "rule-validator must declare rule role"
    assert "compliance" in content.lower() or "Compliance" in content \
        or "validation" in content.lower(), \
        "rule-validator must declare compliance/validation role"


def test_rule_validator_only_rule():
    """Spec: ONLY rule compliance — NO syntax or crossref checks."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "ONLY rule" in flat or "only rule" in flat.lower(), \
        "rule-validator must declare ONLY-rule rule"
    assert "NO syntax" in flat or "no syntax" in flat.lower(), \
        "rule-validator must forbid syntax checks (combined-list)"
    assert "crossref" in flat.lower() or "NO crossref" in flat, \
        "rule-validator must forbid crossref checks (combined-list)"


def test_rule_validator_delegates_to_dev_tff():
    """Spec: delegates to tools/dev_tff.py VALIDATE rule."""
    content = RECIPE.read_text()
    assert "dev_tff" in content, \
        "rule-validator must reference dev_tff tool"
    assert "VALIDATE" in content, \
        "rule-validator must use VALIDATE command"
    assert "rule" in content.lower(), \
        "rule-validator must use rule command"


def test_rule_validator_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "rule-validator must be single-role leaf"


def test_rule_validator_settings():
    """Spec: code-review settings (timeout=120, max_turns=15, deepseek-v4-flash)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 120, \
        "rule-validator must have timeout=120 (script-wrapper)"
    assert settings.get("max_turns") == 30, \
        "rule-validator must have max_turns=15 (script-wrapper)"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "rule-validator must use deepseek model"


def test_rule_validator_r01_r04_r09_r10():
    """Spec: R01 (3x), R04 (1x), R09 (2x), R10 (3x) — most R-rich
    script-wrapper because it validates ALL rules.

    Per R101 EVIDENCE: rule-validator is the only script-wrapper
    that restates ALL R-rules (because it validates them).
    """
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert flat.count("R01") >= 3, \
        f"rule-validator must declare R01 3x. Found: {flat.count('R01')}"
    assert flat.count("R04") >= 1, \
        f"rule-validator must declare R04 1x. Found: {flat.count('R04')}"
    assert flat.count("R09") >= 2, \
        f"rule-validator must declare R09 2x. Found: {flat.count('R09')}"
    assert flat.count("R10") >= 3, \
        f"rule-validator must declare R10 3x. Found: {flat.count('R10')}"
    assert "CORONASHIELD" in flat, \
        "rule-validator must declare CORONASHIELD"


def test_rule_validator_part_of_tff_validator_director():
    """Spec: rule-validator is one of 3 tff-validator-director sub-agents.
    Per R101 EVIDENCE: tff-validator-director has 3-way split:
    - tff-syntax-validator (R107-11)
    - tff-crossref-validator (R108-2)
    - tff-rule-validator (this)
    """
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "rule" in flat.lower(), \
        "rule-validator must declare rule scope"
