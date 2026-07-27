"""
test_sub_mas_json_utility.py — sanity tests for json-utility.

json-utility v1.0.0 is a script-wrapper recipe (R85):
JSON validate | format | append. Delegates to dev_* tools.
NO Python/YAML/MD validation.

Per R101 EVIDENCE: R01+R09+R10 (2x) (script-wrapper with YAML output).

Run with:
    python3 -m pytest tests/test_sub_mas_json_utility.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-json-utility.yaml"


def test_json_utility_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_json_utility_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_json_utility_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_json_utility_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_json_utility_role():
    """Spec: MAS-internal: JSON validate | format | append."""
    content = RECIPE.read_text()
    assert "JSON" in content or "json" in content.lower(), \
        "json-utility must reference JSON"
    for op in ("VALIDATE", "FORMAT", "APPEND"):
        assert op in content, \
            f"json-utility must support operation {op}"


def test_json_utility_only_json():
    """Spec: NO Python/YAML/MD — ONLY JSON."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "NO Python" in flat or "no python" in flat.lower() \
        or "no Python" in flat, \
        "json-utility must forbid Python validation"
    assert "NO YAML" in flat or "no yaml" in flat.lower(), \
        "json-utility must forbid YAML validation"
    assert "MD" in flat or "md" in flat.lower(), \
        "json-utility must forbid MD validation"


def test_json_utility_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "json-utility must be single-role leaf"


def test_json_utility_settings():
    """Spec: script-wrapper settings (timeout=60, max_steps=15, deepseek)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 60, \
        "json-utility must have timeout=60 (script-wrapper)"
    assert settings.get("max_steps") == 15, \
        "json-utility must have max_steps=15 (script-wrapper)"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "json-utility must use deepseek model"


def test_json_utility_r01_r09_r10_x2():
    """Spec: R01, R09, R10 (2x) (script-wrapper with YAML output,
    heavily CORONASHIELD-enforced).
    """
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert flat.count("R01") >= 1, "json-utility must declare R01"
    assert flat.count("R09") >= 1, "json-utility must declare R09"
    assert flat.count("R10") >= 2, \
        f"json-utility must declare R10 2x. Found: {flat.count('R10')}"
    assert flat.count("CORONASHIELD") >= 2, \
        f"json-utility must declare CORONASHIELD 2x. " \
        f"Found: {flat.count('CORONASHIELD')}"


def test_json_utility_uses_recovery_immune():
    """Spec: R10 CORONASHIELD delegates YAML validation to
    sub_mas-recovery-immune.
    """
    content = RECIPE.read_text()
    assert "sub_mas-recovery-immune" in content, \
        "json-utility must reference sub_mas-recovery-immune for YAML validation"


def test_json_utility_uses_dev_rule_checker():
    """Spec: sub_mas-recovery-immune uses tools/dev_rule_checker.py."""
    content = RECIPE.read_text()
    assert "dev_rule_checker" in content, \
        "json-utility must reference dev_rule_checker tool"
