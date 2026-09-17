"""
test_sub_mas_recovery_immune.py — sanity tests for recovery-immune.

recovery-immune v2.0.0 is the R10 CORONASHIELD. Thin-wrapper around
tools/dev_yaml_check.py (R89 Phase 6). Replaces LLM-interpreted
yaml.safe_load/compile/bash -n with deterministic tool.

Run with:
    python3 -m pytest tests/test_sub_mas_recovery_immune.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-recovery-immune.yaml"
SCRIPT = REPO_ROOT / "tools" / "dev_yaml_check.py"


def test_recovery_immune_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_recovery_immune_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_recovery_immune_recipe_has_required_fields():
    """Adapted: has description+instructions+prompt but no 'settings'."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "description", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_recovery_immune_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_recovery_immune_r10_coronashield():
    """Spec: R10 CORONASHIELD — every YAML validated before storage."""
    content = RECIPE.read_text()
    assert "R10" in content, "recovery-immune must declare R10"
    assert "CORONASHIELD" in content, \
        "recovery-immune must declare CORONASHIELD"
    assert "Coronashield" in content or "coronashield" in content.lower(), \
        "recovery-immune must declare coronashield role"


def test_recovery_immune_dev_yaml_check_script():
    """Spec: delegates to tools/dev_yaml_check.py (R89 Phase 6)."""
    content = RECIPE.read_text()
    assert "tools/dev_yaml_check.py" in content, \
        "recovery-immune must delegate to tools/dev_yaml_check.py"
    assert "R89" in content, \
        "recovery-immune must reference R89 Phase 6 refactor"


def test_recovery_immune_thin_wrapper():
    """Spec: thin-wrapper around deterministic script."""
    content = RECIPE.read_text()
    assert "THIN-WRAPPER" in content or "thin wrapper" in content.lower() \
        or "Thin-wrapper" in content, \
        "recovery-immune must declare thin-wrapper pattern"


def test_recovery_immune_4_commands():
    """Spec: 4 commands — CHECK_YAML, CHECK_SYNTAX, VERIFY_STATE, CHECK_ALL."""
    content = RECIPE.read_text()
    for cmd in ("CHECK_YAML", "CHECK_SYNTAX", "VERIFY_STATE", "CHECK_ALL"):
        assert cmd in content, \
            f"recovery-immune must declare command: {cmd}"


def test_recovery_immune_replaces_llm_validation():
    """Spec: R89 replaced LLM-based yaml.safe_load/compile/bash -n."""
    content = RECIPE.read_text()
    for replaced in ("yaml.safe_load", "compile", "bash -n"):
        assert replaced in content, \
            f"recovery-immune must declare LLM-replacement of: {replaced}"


def test_recovery_immune_script_exists():
    """EVIDENCE: tools/dev_yaml_check.py must exist."""
    assert SCRIPT.exists(), \
        f"Missing: {SCRIPT} (R89 Phase 6 target)"


def test_recovery_immune_r01_r09():
    """Spec: R01 (no changes w/o confirmation), R09 (no domain overreach)."""
    content = RECIPE.read_text()
    assert "Confirmation" in content or "confirmation" in content, \
        "recovery-immune must declare R01 confirmation"
    assert "domain-overreach" in content or "domain" in content.lower(), \
        "recovery-immune must declare R09 domain protection"
