"""
test_sub_mas_unix_test_runner.py — sanity tests for unix-test-runner.

unix-test-runner v2.0.0 is the POSIX test-builtin wrapper (R85
refactor). Calls tools/dev_test_runner.py with test_unix_test_word.py
for file-system integrity checks (NOT detected by pytest).

Run with:
    python3 -m pytest tests/test_sub_mas_unix_test_runner.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-unix-test-runner.yaml"
SCRIPT = REPO_ROOT / "tools" / "dev_test_runner.py"
TEST_FILE = REPO_ROOT / "tests" / "test_unix_test_word.py"


def test_unix_test_runner_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_unix_test_runner_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_unix_test_runner_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_unix_test_runner_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_unix_test_runner_posix_test_builtin():
    """Spec: POSIX test-builtin ([ -f file ], [ -d dir ], etc.)."""
    content = RECIPE.read_text()
    assert "POSIX" in content or "posix" in content, \
        "unix-test-runner must declare POSIX test builtin"
    assert "test -f" in content or "[ -f" in content or "-f" in content, \
        "unix-test-runner must reference file-exists check"


def test_unix_test_runner_r85_refactor():
    """Spec: R85 refactor — script-wrapper for tools/dev_test_runner.py."""
    content = RECIPE.read_text()
    assert "R85" in content, "unix-test-runner must reference R85 refactor"
    assert "tools/dev_test_runner.py" in content, \
        "unix-test-runner must delegate to tools/dev_test_runner.py"


def test_unix_test_runner_checks():
    """Spec: 4 file-system integrity checks (combined-list, 2-line wrap).
    Note: 'non-executable\\n  scripts' has multi-space wrap (3 spaces
    after flatten) — check for 'non-executable' + 'scripts' as 2 strings.
    """
    content = RECIPE.read_text()
    # Strip newlines AND collapse multi-spaces for substring matching
    import re
    flat = re.sub(r"\s+", " ", content)
    for check in ("missing recipe files", "empty dirs",
                  "broken symlinks", "non-executable", "scripts",
                  "YAML extensions"):
        assert check in flat, \
            f"unix-test-runner must declare check: {check}"


def test_unix_test_runner_yaml_extension_check():
    """Spec: detects wrong YAML extensions."""
    content = RECIPE.read_text()
    assert "YAML" in content or "yaml" in content, \
        "unix-test-runner must check YAML files"
    assert "extension" in content or "ext" in content, \
        "unix-test-runner must check file extensions"


def test_unix_test_runner_script_exists():
    """EVIDENCE: tools/dev_test_runner.py must exist for wrapper to work."""
    assert SCRIPT.exists(), f"Missing: {SCRIPT} (R85 refactor target)"


def test_unix_test_runner_test_file_exists():
    """EVIDENCE: tests/test_unix_test_word.py must exist (POSIX checks)."""
    assert TEST_FILE.exists(), \
        f"Missing: {TEST_FILE} (POSIX test-builtin regression-suite)"
