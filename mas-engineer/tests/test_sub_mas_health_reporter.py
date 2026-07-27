"""
test_sub_mas_health_reporter.py — sanity tests for the health-reporter recipe.

The health-reporter is run every commit and aggregates framework state
into a human-readable health report. Structural breaks here mean we
lose visibility into the IM-pipeline's success rate.

Run with:
    python3 -m pytest tests/test_sub_mas_health_reporter.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-health-reporter.yaml"
INSTRUCTIONS = REPO_ROOT / "recipe" / "instructions" / "sub_mas-health-reporter.md"


def test_health_reporter_recipe_exists():
    """Recipe must exist at canonical location."""
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_health_reporter_recipe_is_valid_yaml():
    """R10 CORONASHIELD: recipe must be parseable YAML."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), "Recipe must be a YAML mapping"


def test_health_reporter_recipe_has_required_fields():
    """Constitution requires: name, version, instructions, prompt, settings."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "instructions", "prompt", "settings"):
        assert field in data, f"Missing required field: {field}"


def test_health_reporter_references_master_constitution():
    """R10 traceability: must declare master constitution."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_health_reporter_instructions_file_exists():
    """Health reporter has external instructions file (per R37 maintainability rule)."""
    assert INSTRUCTIONS.exists(), f"Missing: {INSTRUCTIONS}"


def test_health_reporter_mentions_success_signal():
    """Health report must use the canonical DONE/BLOCKED signal pattern (R36-IM)."""
    content = INSTRUCTIONS.read_text()
    # At least 2 of the canonical signal types must appear
    signals = [s for s in ("DONE", "BLOCKED", "TIMEOUT")
               if s in content]
    assert len(signals) >= 2, \
        f"Instructions must reference at least 2 DONE/BLOCKED/TIMEOUT signals. Found: {signals}"


def test_health_reporter_reads_state_dir():
    """Health report must read from .state/ directory (R99 health-evidence pattern)."""
    content = INSTRUCTIONS.read_text()
    assert ".state/" in content, "Health reporter must read from .state/ directory"


def test_health_reporter_mentions_recovery_system():
    """Health report must reference the 5-stage recovery system (R36 phoenix)."""
    content = INSTRUCTIONS.read_text()
    recovery_stages = [s for s in ("immune", "checkpoint", "safezone", "timeline", "defib")
                       if s in content]
    assert len(recovery_stages) >= 3, \
        f"Instructions must reference at least 3 recovery stages. Found: {recovery_stages}"


def test_health_reporter_has_mode_detection():
    """Health report must support multi-mode detection (R37 maintainability)."""
    content = INSTRUCTIONS.read_text()
    assert "MODE-DETECTION" in content or "DETECTED_MODE" in content, \
        "Health reporter must support mode detection (R37)"


def test_health_reporter_has_coronashield():
    """R10: must validate YAML before storage."""
    content = INSTRUCTIONS.read_text()
    assert "CORONASHIELD" in content, "Must include CORONASHIELD YAML validation rule"


def test_health_reporter_recipe_does_not_run_sub_recipes():
    """Health reporter is a leaf node — must not have sub_recipes (would create recursion)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "Health reporter must be a leaf node (no sub_recipes)"


def test_health_reporter_no_hardcoded_user_paths():
    """R101: no /home/<user>/ patterns in the recipe itself (only in Check 2 examples)."""
    content = RECIPE.read_text()
    # Only allow /home/ in the prompt (where it could be a generic placeholder)
    # but not in instructions or paths
    bad = ["/home/user", "/home/runner", "/home/ubuntu"]
    for pattern in bad:
        assert pattern not in content, f"Hardcoded user path found: {pattern}"
