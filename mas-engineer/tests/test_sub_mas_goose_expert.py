"""
test_sub_mas_goose_expert.py — sanity tests for goose-expert.

goose-expert v1.0.0 is the Goose-knowledge validator (MAS-internal):
Checks EACH change against goose-docs.ai before execution.
14 scopes — apply nothing automatically. Delegates research to
sub_mas-web-researcher.

Per R101 EVIDENCE: R10 (3x) (heavily CORONASHIELD-enforced),
R01/R09 NOT required (read-only validator).

Run with:
    python3 -m pytest tests/test_sub_mas_goose_expert.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-goose-expert.yaml"


def test_goose_expert_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_goose_expert_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_goose_expert_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_goose_expert_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_goose_expert_role():
    """Spec: MAS-internal: Checks EACH change against goose-docs.ai."""
    content = RECIPE.read_text()
    assert "Goose" in content or "goose" in content.lower(), \
        "goose-expert must reference Goose"
    assert "goose-docs" in content or "goose-docs.ai" in content, \
        "goose-expert must reference goose-docs.ai"
    assert "checks" in content.lower() or "Checks" in content \
        or "EACH change" in content, \
        "goose-expert must declare check-role"


def test_goose_expert_only_validation():
    """Spec: 14 scopes — apply nothing automatically."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "14 scopes" in flat or "14 scope" in flat, \
        "goose-expert must declare 14 scopes"
    assert "apply nothing automatically" in flat \
        or "apply nothing" in flat.lower(), \
        "goose-expert must declare no-auto-apply rule"


def test_goose_expert_delegates_to_web_researcher():
    """Spec: delegates research to sub_mas-web-researcher."""
    content = RECIPE.read_text()
    assert "sub_mas-web-researcher" in content, \
        "goose-expert must reference sub_mas-web-researcher"
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = [s.get("name") for s in data.get("sub_recipes", [])]
    assert "sub_mas-web-researcher" in subs, \
        f"goose-expert must have sub_mas-web-researcher as sub_recipe. " \
        f"Got: {subs}"


def test_goose_expert_settings():
    """Spec: sub-agent settings (timeout=600, max_steps=100, deepseek)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "goose-expert must have timeout=600"
    assert settings.get("max_steps") == 100, \
        "goose-expert must have max_steps=100"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "goose-expert must use deepseek model"


def test_goose_expert_r10_x3_no_r01_r09():
    """Spec: R10 (3x), R01/R09 NOT required (read-only validator).
    Per R101 EVIDENCE: goose-expert is read-only (checks docs),
    so R01 (no general-improver changes) and R09 (no unconstrained
    changes) are NOT relevant.
    """
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert flat.count("R10") >= 3, \
        f"goose-expert must declare R10 3x. Found: {flat.count('R10')}"
    assert flat.count("CORONASHIELD") >= 3, \
        f"goose-expert must declare CORONASHIELD 3x. " \
        f"Found: {flat.count('CORONASHIELD')}"
    # Read-only validator — R01/R09 not applicable
    assert "R01" not in flat, \
        "goose-expert must NOT have R01 (read-only validator)"
    assert "R09" not in flat, \
        "goose-expert must NOT have R09 (read-only validator)"


def test_goose_expert_differs_from_goose_admin():
    """Spec: goose-expert is read-only validator (R10 only).
    goose-admin is action-taker (R01+R09+R10).
    Per R101 EVIDENCE: role-based R-rule distribution.
    """
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    # Has 1 sub_recipe (web-researcher), unlike goose-admin
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = [s.get("name") for s in data.get("sub_recipes", [])]
    assert len(subs) == 1, \
        f"goose-expert must have 1 sub_recipe (web-researcher). Got: {subs}"
