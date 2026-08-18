"""
test_sub_mas_test_fix_failures_ranker.py — sanity tests for test-fix-failures-ranker.

test-fix-failures-ranker v2.0.0 is a script-wrapper recipe
(R85 Phase 4 REFACTOR): All ranking logic moved to
tools/dev_tff.py RANK. This recipe is a thin wrapper.

Per R101 EVIDENCE: R01+R09, no R10 (script-wrapper, no YAML storage).

Run with:
    python3 -m pytest tests/test_sub_mas_test_fix_failures_ranker.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-test-fix-failures-ranker.yaml"


def test_ranker_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_ranker_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_ranker_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_ranker_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_ranker_role():
    """Spec: MAS-internal: Ranks e2e failures by priority."""
    content = RECIPE.read_text()
    assert "Ranks" in content or "PRIORITY SORTING" in content.upper() \
        or "priority sorting" in content.lower(), \
        "ranker must declare ranking role"
    assert "priority" in content.lower(), \
        "ranker must declare priority-scope"
    assert "e2e" in content.lower() or "failures" in content.lower(), \
        "ranker must declare e2e/failures scope"


def test_ranker_only_sorting():
    """Spec: ONLY priority sorting — NO detection or design."""
    content = RECIPE.read_text()
    assert "ONLY priority sorting" in content, \
        "ranker must declare ONLY-sorting rule"
    assert "NO detection" in content or "no detection" in content.lower(), \
        "ranker must forbid detection (combined-list)"
    assert "design" in content.lower() or "NO design" in content, \
        "ranker must forbid design (combined-list)"


def test_ranker_delegates_to_dev_tff():
    """Spec: R85 Phase 4 REFACTOR — delegates to tools/dev_tff.py RANK."""
    content = RECIPE.read_text()
    assert "dev_tff" in content, \
        "ranker must reference dev_tff tool"
    assert "RANK" in content, \
        "ranker must use RANK command"
    assert "R85" in content, \
        "ranker must reference R85 refactor"
    assert "Phase 4" in content, \
        "ranker must reference Phase 4 refactor"
    assert "Script-wrapper" in content or "script-wrapper" in content.lower() \
        or "thin wrapper" in content.lower(), \
        "ranker must declare script-wrapper architecture"


def test_ranker_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "ranker must be single-role leaf"


def test_ranker_settings():
    """Spec: code-review settings (timeout=120, max_turns=15, deepseek-v4-flash)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 120, \
        "ranker must have timeout=120 (script-wrapper)"
    assert settings.get("max_turns") == 30, \
        "ranker must have max_turns=15 (script-wrapper)"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "ranker must use deepseek model"


def test_ranker_r01_r09_no_r10():
    """Spec: R01, R09 — no R10 (script-wrapper, no YAML storage)."""
    content = RECIPE.read_text()
    assert "R01" in content, "ranker must declare R01"
    assert "R09" in content, "ranker must declare R09"
    flat = re.sub(r"\s+", " ", content)
    assert flat.count("R10") == 0, \
        "ranker must NOT have R10 (script-wrapper)"
    assert flat.count("CORONASHIELD") == 0, \
        "ranker must NOT have CORONASHIELD (script-wrapper)"


def test_ranker_differs_from_finder():
    """Spec: ranker and finder are both R85 refactored, but ranker
    uses RANK command while finder uses FIND command.
    Per R101 EVIDENCE: this distinguishes ranker as RANK-wrapper.
    """
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert flat.count("FIND") == 0, \
        "ranker must NOT have FIND (only RANK)"
    assert flat.count("RANK") >= 2, \
        "ranker must have RANK multiple times (command + action)"
