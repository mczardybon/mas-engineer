"""
test_sub_mas_pre_push_validator.py — sanity tests for the validator recipe.

The validator is dogfooded (it validates the framework that defines it).
This test ensures the validator's own structure is conformant so it
doesn't break itself.

Run with:
    python3 -m pytest tests/test_sub_mas_pre_push_validator.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-pre-push-validator.yaml"
INSTRUCTIONS = REPO_ROOT / "recipe" / "instructions" / "sub_mas-pre-push-validator.md"


def test_validator_recipe_exists():
    """Recipe must exist at canonical location."""
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_validator_recipe_is_valid_yaml():
    """R10 CORONASHIELD: recipe must be parseable YAML."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), "Recipe must be a YAML mapping"


def test_validator_recipe_has_required_fields():
    """Constitution requires: name, version, instructions, prompt, settings."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "instructions", "prompt", "settings"):
        assert field in data, f"Missing required field: {field}"


def test_validator_references_master_constitution():
    """R10 traceability: validator must declare its constitution."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "constitution" in data, "Missing constitution reference"
    assert data["constitution"] == "sub_mas-master-constitution.yaml"


def test_validator_instructions_define_checks():
    """Instructions must define the check structure (Check 1, Check 2, ...)."""
    content = INSTRUCTIONS.read_text()
    assert "Check 1" in content, "Validator must define Check 1"
    assert "Check 12" in content, "Validator must define Check 12 (test coverage gate)"


def test_validator_check_2_defines_home_path_rule():
    """R101: Check 2 must define a rule about hardcoded /home/<user>/ paths."""
    content = INSTRUCTIONS.read_text()
    # Check 2 must be present AND must use /home/ as the pattern (intentional)
    check_2_start = content.find("### Check 2")
    check_3_start = content.find("### Check 3")
    assert check_2_start > 0, "Check 2 section not found"
    check_2 = content[check_2_start:check_3_start if check_3_start > 0 else None]
    assert "/home/" in check_2, "Check 2 must use /home/ as the grep pattern"
    assert "grep" in check_2, "Check 2 must include a grep command"


def test_validator_check_4_uses_correct_exit_code_pattern():
    """R101 EC: Check 4 (Python compile) must use `if ! cmd; then ...` not
    `cmd && echo` (which exits 1 on success)."""
    content = INSTRUCTIONS.read_text()
    # Find Check 4 section
    check_4_start = content.find("### Check 4")
    check_5_start = content.find("### Check 5")
    assert check_4_start > 0, "Check 4 section not found"
    check_4 = content[check_4_start:check_5_start if check_5_start > 0 else None]
    # The bad pattern: `python3 -c "..." && echo "..."` exits 1 on success
    # The good pattern: `if ! python3 -c "..."; then echo "..."; fi` exits 0
    assert "if ! python3" in check_4 or "if ! py" in check_4, \
        "Check 4 must use 'if ! python3 ...; then ...; fi' pattern (R101 fix)"


def test_validator_check_10_no_removed_flag():
    """R102: Check 10 must NOT use --no-write-results (e2e_run_all.py doesn't know it)."""
    content = INSTRUCTIONS.read_text()
    assert "--no-write-results" not in content, \
        "R102 fix removed --no-write-results; if this fails, the flag regressed"


def test_validator_mentions_test_coverage_policy():
    """R103: validator must reference TEST-COVERAGE-POLICY.md (escape hatch doc)."""
    content = INSTRUCTIONS.read_text()
    assert "TEST-COVERAGE-POLICY.md" in content, \
        "Check 12 escape hatch must reference docs/TEST-COVERAGE-POLICY.md (R103)"


def test_test_coverage_policy_doc_exists():
    """R103: the policy doc must exist (was created to fix broken link in line 408)."""
    policy = REPO_ROOT / "docs" / "TEST-COVERAGE-POLICY.md"
    assert policy.exists(), f"Missing: {policy}"
