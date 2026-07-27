"""
test_sub_mas_im_session_reader.py — sanity tests for im-session-reader.

im-session-reader reads goose sessions.db via tools/dev_session_query.py
(R89 Phase 7 refactor). v2.0.0 thin-wrapper around deterministic script
(replaces LLM-interpreted sqlite3 calls).

Run with:
    python3 -m pytest tests/test_sub_mas_im_session_reader.py -v
"""
import yaml
from pathlib import Path
import py_compile

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-im-session-reader.yaml"
TOOL = REPO_ROOT / "tools" / "dev_session_query.py"


def test_im_session_reader_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_im_session_reader_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_im_session_reader_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_im_session_reader_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_im_session_reader_delegates_to_script():
    """R89 Phase 7: must reference tools/dev_session_query.py (no inline sqlite)."""
    content = RECIPE.read_text()
    assert "dev_session_query.py" in content, \
        "Recipe must reference tools/dev_session_query.py (R89 Phase 7)"


def test_im_session_reader_tool_script_exists():
    assert TOOL.exists(), f"Missing delegated tool: {TOOL}"


def test_im_session_reader_tool_imports_correctly():
    """R10 CORONASHIELD: tool must be valid Python."""
    try:
        py_compile.compile(str(TOOL), doraise=True)
    except py_compile.PyCompileError as e:
        raise AssertionError(f"Tool has Python syntax errors: {e}")


def test_im_session_reader_subcommands():
    """Tool must define ANALYZE, FILTER_LEVEL, SHOW_DB_INFO, STALE."""
    content = TOOL.read_text()
    for cmd in ("ANALYZE", "FILTER_LEVEL", "SHOW_DB_INFO", "STALE"):
        assert cmd in content, f"Tool must implement subcommand: {cmd}"


def test_im_session_reader_mentions_coronashield():
    """R10: must validate YAML before storage."""
    content = RECIPE.read_text()
    assert "CORONASHIELD" in content, \
        "im-session-reader must declare R10 CORONASHIELD YAML validation"


def test_im_session_reader_no_sub_recipes():
    """im-session-reader is a leaf node (no further delegation)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "im-session-reader must be a leaf node (no sub_recipes)"
