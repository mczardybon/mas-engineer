"""
test_sub_mas_framework_auditor.py — sanity tests for framework-auditor.

framework-auditor v1.0.0 audits and validates framework
configuration and structure. ONLY auditing and validation.
Single-role leaf.

Per R101 EVIDENCE: framework-auditor has fewer R-number rules than
other framework recipes (R01/R04/R05 not declared).

Run with:
    python3 -m pytest tests/test_sub_mas_framework_auditor.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-framework-auditor.yaml"


def test_framework_auditor_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_framework_auditor_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_framework_auditor_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_framework_auditor_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_framework_auditor_only_auditing():
    """Spec: ONLY framework auditing and validation."""
    content = RECIPE.read_text()
    assert "ONLY framework auditing" in content, \
        "framework-auditor must declare ONLY-auditing rule"
    assert "validation" in content, \
        "framework-auditor must declare validation role"


def test_framework_auditor_audit_validation_role():
    """Spec: audits and validates framework configuration and structure."""
    content = RECIPE.read_text()
    assert "audit" in content.lower() or "Audit" in content, \
        "framework-auditor must declare audit role"
    assert "validation" in content.lower(), \
        "framework-auditor must declare validation"
    assert "structure" in content.lower(), \
        "framework-auditor must declare structure audit"


def test_framework_auditor_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "framework-auditor must be single-role leaf"


def test_framework_auditor_settings():
    """Spec: standard settings (timeout=600, max_steps=100, deepseek-v4-flash)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "framework-auditor must have timeout=600"
    assert settings.get("max_steps") == 100, \
        "framework-auditor must have max_steps=100"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "framework-auditor must use deepseek model"


def test_framework_auditor_auditor_vs_audit_agent():
    """Spec: framework-auditor is the orchestrator (vs framework-audit-agent
    leaf). Per R101 EVIDENCE: framework-auditor has no sub_recipes
    (single-role), so this test distinguishes it as a specialized
    audit-only validator (vs audit-agent which audits architecture).
    """
    content = RECIPE.read_text()
    assert "validation report" in content.lower() \
        or "Validation report" in content, \
        "framework-auditor must return validation report"


def test_framework_auditor_r00_constitution_only():
    """Spec: this is a minimal recipe — no R-number rules.
    Per R101 EVIDENCE: framework-auditor has 0 R-number declarations
    (R01/R04/R05/R09/R10 all absent). It references the master
    constitution but doesn't restate R-rules.
    """
    content = RECIPE.read_text()
    # This recipe delegates all R-rules to master-constitution
    # (no per-recipe rule restatement)
    import re
    flat = re.sub(r"\s+", " ", content)
    assert flat.count("R0") == 0, \
        f"framework-auditor must not restate R-rules (uses constitution). Found: {flat.count('R0')}"
