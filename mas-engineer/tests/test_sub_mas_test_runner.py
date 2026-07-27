"""
test_sub_mas_test_runner.py — sanity tests for test-runner.

test-runner v2.0.0 is a SCRIPT-WRAPPER (R85 refactor). All logic
moved to tools/dev_test_runner.py. Recipe is a thin wrapper that
delegates to the script via 'bash' extension.

Note: this recipe has 'description:' but NO 'settings:' field.
Required-fields test adapted accordingly.

Run with:
    python3 -m pytest tests/test_sub_mas_test_runner.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-test-runner.yaml"
SCRIPT = REPO_ROOT / "tools" / "dev_test_runner.py"


def test_test_runner_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_test_runner_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_test_runner_recipe_has_required_fields():
    """Adapted: has description+instructions+prompt but no 'settings'."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "description", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_test_runner_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_test_runner_script_wrapper():
    """Spec: R85 refactor — script-wrapper for tools/dev_test_runner.py."""
    content = RECIPE.read_text()
    assert "R85" in content, "test-runner must reference R85 refactor"
    assert "tools/dev_test_runner.py" in content, \
        "test-runner must delegate to tools/dev_test_runner.py"
    assert "Script-wrapper" in content or "script" in content.lower(), \
        "test-runner must declare script-wrapper pattern"


def test_test_runner_4_operations():
    """Spec: 4 operations — CHECK_DEPS, RUN, COMPARE, VERIFY."""
    content = RECIPE.read_text()
    for op in ("CHECK_DEPS", "RUN", "COMPARE", "VERIFY"):
        assert op in content, \
            f"test-runner must declare operation: {op}"


def test_test_runner_no_changes():
    """Spec: ONLY run tests — NO changes to recipes/tools."""
    content = RECIPE.read_text()
    assert "ONLY run tests" in content, \
        "test-runner must declare ONLY-run-tests rule"
    assert "NO changes to recipes/tools" in content or "NO changes" in content, \
        "test-runner must forbid changes"


def test_test_runner_json_output():
    """Spec: JSON output — exit code 0/1/2 (PASS/FAIL/ERROR)."""
    content = RECIPE.read_text()
    assert "JSON" in content, "test-runner must declare JSON output"
    assert "Exit code" in content or "exit code" in content, \
        "test-runner must declare exit-code semantics"


def test_test_runner_script_exists():
    """EVIDENCE: tools/dev_test_runner.py must exist for wrapper to work."""
    assert SCRIPT.exists(), f"Missing: {SCRIPT} (R85 refactor target)"


def test_test_runner_r01_r04_r09_r10():
    """Spec: R01, R04 (no general-improver edit), R09, R10."""
    content = RECIPE.read_text()
    assert "R01" in content, "test-runner must declare R01"
    assert "R04" in content, "test-runner must declare R04"
    assert "R09" in content, "test-runner must declare R09"
    assert "R10" in content, "test-runner must declare R10"
    assert "CORONASHIELD" in content, \
        "test-runner must declare CORONASHIELD"
