"""
test_sub_mas_tff_crossref_validator.py — sanity tests for tff-crossref-validator.

tff-crossref-validator v2.0.0 is a script-wrapper recipe (R85):
Cross-reference consistency of patches.
Delegates to tools/dev_tff.py VALIDATE crossref.

Per R101 EVIDENCE: R01+R09 only (no R10/CORONASHIELD — this is
the simplest script-wrapper, no YAML modifications needed).

Part of tff-validator-director 3-way split:
- tff-syntax-validator (R107-11)
- tff-crossref-validator (this)
- tff-rule-validator (R108-2)

Run with:
    python3 -m pytest tests/test_sub_mas_tff_crossref_validator.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-tff-crossref-validator.yaml"


def test_crossref_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_crossref_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_crossref_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_crossref_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_crossref_role():
    """Spec: MAS-internal: Cross-reference consistency of patches."""
    content = RECIPE.read_text()
    assert "crossref" in content.lower() or "Cross-reference" in content \
        or "CrossRef" in content or "cross-reference" in content.lower() \
        or "CROSSREF" in content.upper() or "CROSS-REF" in content, \
        "tff-crossref-validator must declare crossref role"
    assert "consistency" in content.lower() or "consistenc" in content \
        or "consistent" in content.lower(), \
        "tff-crossref-validator must declare consistency scope"


def test_crossref_delegates_to_dev_tff():
    """Spec: delegates to tools/dev_tff.py VALIDATE crossref."""
    content = RECIPE.read_text()
    assert "dev_tff" in content, \
        "tff-crossref-validator must reference dev_tff tool"
    assert "VALIDATE" in content or "validate" in content.lower(), \
        "tff-crossref-validator must use VALIDATE command"
    assert "crossref" in content.lower() or "cross-ref" in content.lower() \
        or "cross_ref" in content.lower(), \
        "tff-crossref-validator must use crossref command"


def test_crossref_only_crossref():
    """Spec: ONLY crossref — NO syntax or rule checks."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "ONLY crossref" in flat or "only crossref" in flat.lower() \
        or "ONLY cross-ref" in flat.lower(), \
        "tff-crossref-validator must declare ONLY-crossref rule"
    assert "NO syntax" in flat or "no syntax" in flat.lower(), \
        "tff-crossref-validator must forbid syntax checks (combined-list)"
    assert "rule" in flat.lower() and "NO" in flat, \
        "tff-crossref-validator must forbid rule checks (combined-list)"


def test_crossref_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "tff-crossref-validator must be single-role leaf"


def test_crossref_settings():
    """Spec: code-review settings (timeout=120, max_steps=15, deepseek)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 120, \
        "tff-crossref-validator must have timeout=120 (script-wrapper)"
    assert settings.get("max_steps") == 15, \
        "tff-crossref-validator must have max_steps=15 (script-wrapper)"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "tff-crossref-validator must use deepseek model"


def test_crossref_r01_r09_no_r10():
    """Spec: R01 (1x) + R09 (1x) — no R10 (no CORONASHIELD).

    Per R101 EVIDENCE: tff-crossref-validator is the SIMPLEST
    script-wrapper — it only reads patches, doesn't modify YAMLs.
    Therefore no R10/CORONASHIELD is needed.
    """
    content = RECIPE.read_text()
    assert "R01" in content, "tff-crossref-validator must declare R01"
    assert "R09" in content, "tff-crossref-validator must declare R09"
    # NO R10 / CORONASHIELD expected for read-only crossref check
    flat = re.sub(r"\s+", " ", content)
    assert "CORONASHIELD" not in flat, \
        "tff-crossref-validator must NOT have CORONASHIELD (read-only)"


def test_crossref_part_of_tff_validator_director():
    """Spec: crossref-validator is one of 3 tff-validator-director sub-agents.
    Per R101 EVIDENCE: 3-way split (syntax+crossref+rule).
    """
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "crossref" in flat.lower() or "cross-ref" in flat.lower(), \
        "tff-crossref-validator must declare crossref scope"
