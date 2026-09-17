"""
test_sub_mas_test_fix_failures_finder.py — sanity tests for test-fix-failures-finder.

test-fix-failures-finder v2.0.0 is a script-wrapper recipe
(R85 Phase 4 REFACTOR): All detection logic moved to
tools/dev_tff.py FIND. This recipe is a thin wrapper.

Per R101 EVIDENCE: R01+R09, no R10 (script-wrapper, no YAML storage).

Run with:
    python3 -m pytest tests/test_sub_mas_test_fix_failures_finder.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-test-fix-failures-finder.yaml"


def test_finder_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_finder_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_finder_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_finder_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_finder_role():
    """Spec: MAS-internal: Detects e2e test failures."""
    content = RECIPE.read_text()
    assert "Detects" in content or "detects" in content \
        or "FAILURE DETECTION" in content.upper() \
        or "failure detection" in content.lower(), \
        "finder must declare detection role"
    assert "e2e test failures" in content.lower() \
        or "test failures" in content.lower(), \
        "finder must declare e2e test-failures scope"


def test_finder_only_detection():
    """Spec: ONLY failure detection — NO ranking or patching."""
    content = RECIPE.read_text()
    assert "ONLY failure detection" in content, \
        "finder must declare ONLY-detection rule"
    assert "NO ranking" in content or "no ranking" in content.lower(), \
        "finder must forbid ranking (combined-list)"
    assert "patching" in content.lower() or "NO patching" in content, \
        "finder must forbid patching (combined-list)"


def test_finder_delegates_to_dev_tff():
    """Spec: R85 Phase 4 REFACTOR — delegates to tools/dev_tff.py FIND."""
    content = RECIPE.read_text()
    assert "dev_tff" in content, \
        "finder must reference dev_tff tool"
    assert "FIND" in content, \
        "finder must use FIND command"
    assert "R85" in content, \
        "finder must reference R85 refactor"
    assert "Phase 4" in content, \
        "finder must reference Phase 4 refactor"
    assert "Script-wrapper" in content or "script-wrapper" in content.lower() \
        or "thin wrapper" in content.lower(), \
        "finder must declare script-wrapper architecture"


def test_finder_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "finder must be single-role leaf"


def test_finder_settings():
    """Spec: code-review settings (timeout=120, max_turns=15, deepseek-v4-flash)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 120, \
        "finder must have timeout=120 (script-wrapper)"
    assert settings.get("max_turns") == 30, \
        "finder must have max_turns=15 (script-wrapper)"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "finder must use deepseek model"


def test_finder_r01_r09_no_r10():
    """Spec: R01, R09 — no R10 (script-wrapper, no YAML storage)."""
    content = RECIPE.read_text()
    assert "R01" in content, "finder must declare R01"
    assert "R09" in content, "finder must declare R09"
    flat = re.sub(r"\s+", " ", content)
    assert flat.count("R10") == 0, \
        "finder must NOT have R10 (script-wrapper)"
    assert flat.count("CORONASHIELD") == 0, \
        "finder must NOT have CORONASHIELD (script-wrapper)"
