"""
test_sub_mas_e2e_german_fixes_validator.py — sanity tests for german-fixes-validator.

German-fixes-validator runs T1 (0 German descs in task_workflows) +
T2 (no placeholder detection in wf_recovery_immune) for the
e2e-verify-german-fixes workflow.

Run with:
    python3 -m pytest tests/test_sub_mas_e2e_german_fixes_validator.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-e2e-german-fixes-validator.yaml"


def test_german_fixes_validator_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_german_fixes_validator_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_german_fixes_validator_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "instructions", "settings"):
        assert field in data, f"Missing required field: {field}"


def test_german_fixes_validator_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_german_fixes_validator_t1_german_descs():
    """Spec: T1 — 0 German descs remaining in task_workflows.

    German keywords list: und, der, die, das, mit, für, von, aus, bei,
    Schritt, Inhalt, Prüfung, Erstellen, etc.
    """
    content = RECIPE.read_text()
    assert "T1" in content, "german-fixes-validator must declare T1"
    assert "task_workflows" in content, \
        "german-fixes-validator T1 must check task_workflows section"
    # German keywords must be present
    for kw in ("Schritt", "Inhalt", "Prüfung"):
        assert kw in content, \
            f"german-fixes-validator T1 must include keyword: {kw}"


def test_german_fixes_validator_t2_placeholders():
    """Spec: T2 — no placeholder (echo-only) steps in wf_recovery_*
    workflows (wildcard, applies to all 5 recovery workflows)."""
    content = RECIPE.read_text()
    assert "T2" in content, "german-fixes-validator must declare T2"
    assert "placeholder" in content.lower(), \
        "german-fixes-validator T2 must check for placeholders"
    assert "wf_recovery_" in content, \
        "german-fixes-validator T2 must reference wf_recovery_ prefix"


def test_german_fixes_validator_reads_workflows_yaml():
    """Spec: reads .state/workflows.yaml SOT."""
    content = RECIPE.read_text()
    assert "workflows.yaml" in content, \
        "german-fixes-validator must read .state/workflows.yaml"


def test_german_fixes_validator_python_yaml():
    """Spec: uses python3 yaml.safe_load for inspection."""
    content = RECIPE.read_text()
    assert "yaml.safe_load" in content, \
        "german-fixes-validator must use Python yaml inspection"


def test_german_fixes_validator_no_modifications():
    """Spec: T1+T2 only, no modifications."""
    content = RECIPE.read_text()
    assert "T1" in content and "T2" in content, \
        "german-fixes-validator must declare T1+T2 only"


def test_german_fixes_validator_returns_structured_output():
    """Spec: returns {t1: {passed, details}, t2: {passed, details}}."""
    content = RECIPE.read_text()
    assert "structured" in content.lower() or "passed" in content, \
        "german-fixes-validator must declare structured output"
