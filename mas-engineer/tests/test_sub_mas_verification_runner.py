"""
test_sub_mas_verification_runner.py — sanity tests for verification-runner.

verification-runner v2.0.0 is a script-wrapper recipe (R85):
Post-commit verify via tools/dev_test_runner.py VERIFY — NO changes.
Original 24-line instruction manual was redundant.

Per R101 EVIDENCE: R01+R04+R09+R10 (script-wrapper with YAML output,
includes R04 for post-commit verification).

Run with:
    python3 -m pytest tests/test_sub_mas_verification_runner.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-verification-runner.yaml"


def test_verification_runner_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_verification_runner_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_verification_runner_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_verification_runner_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_verification_runner_role():
    """Spec: MAS-internal: Post-commit verify."""
    content = RECIPE.read_text()
    assert "verify" in content.lower() or "Verify" in content \
        or "VERIFICATION" in content.upper(), \
        "verification-runner must declare verify role"
    assert "post-commit" in content.lower() or "post_commit" in content \
        or "Post-commit" in content, \
        "verification-runner must declare post-commit scope"


def test_verification_runner_no_changes():
    """Spec: NO changes — read-only verification."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "NO changes" in flat or "no changes" in flat.lower(), \
        "verification-runner must forbid changes"


def test_verification_runner_delegates_to_test_runner():
    """Spec: delegates to tools/dev_test_runner.py VERIFY command."""
    content = RECIPE.read_text()
    assert "dev_test_runner" in content, \
        "verification-runner must reference dev_test_runner tool"
    assert "VERIFY" in content, \
        "verification-runner must use VERIFY command"


def test_verification_runner_r85_refactor():
    """Spec: R85 refactor — original 24-line instruction manual
    was redundant.
    """
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "R85" in flat or "r85" in flat.lower() or "R85 refactor" in flat, \
        "verification-runner must reference R85 refactor"
    assert "24-line" in flat or "24 line" in flat.lower() \
        or "redundant" in flat.lower(), \
        "verification-runner must reference 24-line original"


def test_verification_runner_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "verification-runner must be single-role leaf"


def test_verification_runner_settings():
    """Spec: sub-agent settings (timeout=600, max_turns=50, deepseek)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "verification-runner must have timeout=600"
    assert settings.get("max_turns") == 50, \
        "verification-runner must have max_turns=50"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "verification-runner must use deepseek model"


def test_verification_runner_r01_r04_r09_r10():
    """Spec: R01, R04, R09, R10 (script-wrapper with YAML output,
    includes R04 for post-commit verification).

    Per R101 EVIDENCE: R04 is for post-commit verification
    (uniquely required by verification-runner).
    """
    content = RECIPE.read_text()
    assert "R01" in content, "verification-runner must declare R01"
    assert "R04" in content, "verification-runner must declare R04 (post-commit)"
    assert "R09" in content, "verification-runner must declare R09"
    assert "R10" in content, "verification-runner must declare R10"
    assert "CORONASHIELD" in content, \
        "verification-runner must declare CORONASHIELD"
