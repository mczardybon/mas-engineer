"""
test_sub_mas_security_deserialize_scanner.py — sanity tests for security-deserialize-scanner.

security-deserialize-scanner v2.0.0 is a Code-Review-Team
scanner for unsafe deserialization. Delegates to
tools/dev_security_scan.py SCAN deserialize.

Per R101 EVIDENCE: R01+R09, no R10 (script-wrapper, no storage).

Run with:
    python3 -m pytest tests/test_sub_mas_security_deserialize_scanner.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-security-deserialize-scanner.yaml"


def test_deserialize_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_deserialize_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_deserialize_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_deserialize_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_deserialize_scanner_role():
    """Spec: Code-Review-Team scanner for unsafe deserialization."""
    content = RECIPE.read_text()
    assert "deserialization" in content.lower() \
        or "deserialize" in content.lower(), \
        "deserialize-scanner must declare deserialization role"
    assert "unsafe" in content.lower(), \
        "deserialize-scanner must declare unsafe-deserialization focus"
    assert "Code-Review" in content or "code-review" in content.lower(), \
        "deserialize-scanner must declare Code-Review-Team"


def test_deserialize_delegates_to_dev_security_scan():
    """Spec: delegates to tools/dev_security_scan.py SCAN deserialize."""
    content = RECIPE.read_text()
    assert "dev_security_scan" in content, \
        "deserialize-scanner must reference dev_security_scan tool"
    assert "SCAN" in content, \
        "deserialize-scanner must use SCAN command"
    assert "deserialize" in content, \
        "deserialize-scanner must pass deserialize feature flag"


def test_deserialize_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "deserialize-scanner must be single-role leaf"


def test_deserialize_settings():
    """Spec: code-review settings (timeout=120, max_steps=15, deepseek-v4-flash)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 120, \
        "deserialize-scanner must have timeout=120"
    assert settings.get("max_steps") == 15, \
        "deserialize-scanner must have max_steps=15"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "deserialize-scanner must use deepseek model"


def test_deserialize_r01_r09():
    """Spec: R01, R09 (per R101 EVIDENCE — no R10)."""
    content = RECIPE.read_text()
    assert "R01" in content, "deserialize-scanner must declare R01"
    assert "R09" in content, "deserialize-scanner must declare R09"


def test_deserialize_no_r10():
    """Spec: deserialize-scanner has NO R10 (script-wrapper, no storage)."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert flat.count("R10") == 0, \
        "deserialize-scanner must NOT have R10 (no YAML storage)"
    assert flat.count("CORONASHIELD") == 0, \
        "deserialize-scanner must NOT have CORONASHIELD"
