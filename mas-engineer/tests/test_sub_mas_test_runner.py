"""
test_sub_mas_test_runner.py — sanity tests for the test-runner recipe.

Test-runner is a thin wrapper around tools/dev_test_runner.py (R85
refactor). It runs pytest in the target workspace, returns JSON.

Run with:
    python3 -m pytest tests/test_sub_mas_test_runner.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-test-runner.yaml"
TOOL = REPO_ROOT / "tools" / "dev_test_runner.py"


def test_test_runner_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_test_runner_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_test_runner_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "instructions", "prompt", "settings"):
        assert field in data


def test_test_runner_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_test_runner_delegates_to_script():
    """R85: recipe must delegate to tools/dev_test_runner.py (no inline logic)."""
    content = RECIPE.read_text()
    assert "dev_test_runner.py" in content, \
        "Recipe must reference tools/dev_test_runner.py (R85 refactor)"


def test_test_runner_tool_script_exists():
    """The delegated tool must exist (R85 created it)."""
    assert TOOL.exists(), f"Missing delegated tool: {TOOL}"


def test_test_runner_tool_imports_correctly():
    """R10 CORONASHIELD: tool must be valid Python."""
    import py_compile
    try:
        py_compile.compile(str(TOOL), doraise=True)
    except py_compile.PyCompileError as e:
        raise AssertionError(f"Tool has Python syntax errors: {e}")


def test_test_runner_tool_has_subcommands():
    """Tool must define CHECK_DEPS, RUN, COMPARE, VERIFY subcommands."""
    content = TOOL.read_text()
    for cmd in ("CHECK_DEPS", "RUN", "COMPARE", "VERIFY"):
        assert cmd in content, f"Tool must implement subcommand: {cmd}"


def test_test_runner_mentions_pytest():
    """Tool must use pytest as the test framework."""
    content = TOOL.read_text()
    assert "pytest" in content, "Tool must use pytest"


def test_test_runner_does_not_edit_recipes():
    """R85: test-runner is read-only, must not write to recipe/ or tools/."""
    content = RECIPE.read_text()
    # Should explicitly say NO changes
    assert "NO changes" in content or "ONLY run" in content, \
        "Test-runner must declare it's read-only (R85)"
