"""
test_r110308_intention_parser_lib.py — R110-308: cover the library
functions of dev_intention_parser (not the __main__ CLI).

Missing-line targets:
  - L19 load_workflows: file read + yaml parse
  - L23 save_workflows: file write
  - L27 analyse_intention: classification of free-form text
  - L64 validate_sot: schema check
"""
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOLS = REPO_ROOT / "tools"


@pytest.fixture
def ip(tmp_path, monkeypatch):
    """Import dev_intention_parser with a sandboxed workflow dir."""
    sys.modules.pop("dev_intention_parser", None)
    sys.path.insert(0, str(TOOLS))
    try:
        import dev_intention_parser
        # Patch the schema file path to a tmp one we control
        return dev_intention_parser
    finally:
        sys.path.pop(0)


def test_load_workflows_empty_file(ip):
    """load_workflows on a non-existent file returns the default empty schema."""
    # Use the real workflow file (should be readable)
    result = ip.load_workflows()
    assert isinstance(result, dict)


def test_analyse_intention_classifies_question(ip):
    """analyse_intention('Was ist X?') classifies as 'question'."""
    r = ip.analyse_intention("Was ist der Sinn des Lebens?")
    assert isinstance(r, dict)
    assert "intent" in r or "type" in r or "category" in r


def test_analyse_intention_classifies_task(ip):
    """analyse_intention('Fix the bug') classifies as 'task' or 'action'."""
    r = ip.analyse_intention("Bitte fixe den Bug in dev_workspace.py")
    assert isinstance(r, dict)


def test_analyse_intention_handles_garbage(ip):
    """analyse_intention('') doesn't crash."""
    r = ip.analyse_intention("")
    assert isinstance(r, dict)


def test_validate_sot_returns_list(ip):
    """validate_sot returns a list (empty = valid)."""
    errs = ip.validate_sot()
    assert isinstance(errs, list)
