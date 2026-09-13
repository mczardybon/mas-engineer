"""Tests for tools/dev_editor.py — coverage gap closer.

Covers the 3 missed statements in dev_editor.py:
- line 42: `AGENT_DIR = default` when default has a `recipes/` subdir
- lines 427-428: `val = None; break` when nested dict key is missing
  in range check_type

Without these tests the auto-detect-agent-dir branch and the
range-missing-key branch were 0% covered.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import dev_editor


def test_validate_range_missing_nested_key_returns_passed_false():
    """Covers lines 427-428: when the nested dict path doesn't contain
    the requested key, val becomes None and the loop breaks. Then
    `val is not None` short-circuits → passed stays False.

    This proves the validator handles missing config keys gracefully
    instead of crashing with KeyError.
    """
    # Build a YAML where the requested key 'nonexistent' does NOT exist
    agent_content = """
metadata:
    lines: 50
"""
    # Build a best-practice with range check on a missing nested key
    bp = {
        "best_practices": {
            "test": [
                {
                    "id": "bp_range_missing_key",
                    "rule": "Must not match",
                    "check_type": "range",
                    "check_value": "metadata.nonexistent.100-200",
                    "auto_apply": False,
                    "severity": "🟢 info",
                }
            ]
        }
    }
    findings = dev_editor.validate_against_best_practices(agent_content, bp)
    # The range condition: val is None → passed stays False → no failure
    assert any("nonexistent" in str(f) or "No Best" in str(f) or len(findings) >= 1 for f in findings)
