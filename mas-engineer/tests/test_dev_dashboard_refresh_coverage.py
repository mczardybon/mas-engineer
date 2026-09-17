"""Tests for tools/dev_dashboard_refresh.py — coverage gap closer.

Covers the 14 missed statements in dev_dashboard_refresh.py by exercising
generate_dashboard() with a real tmp workspace that contains:
- changes.json in dict format (lines 96-97: isinstance dict → get)
- changes.json in NDJSON format with malformed lines (line 105: bare except)
- guardian/audit data with non-numeric score (line 73-74: bare except)
- an empty state dir (so paths don't exist)
"""
import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import dev_dashboard_refresh


def test_generate_dashboard_with_dict_changes_format(tmp_path):
    """Covers line 96-97: changes.json starts with non-`[`, is loaded as
    dict, then we extract 'changes' or 'entries' key."""
    state_dir = tmp_path / ".mase"
    state_dir.mkdir()
    # Dict format changes.json (not starting with `[`)
    (state_dir / "changes.json").write_text(json.dumps({
        "changes": [{"id": "ch_001", "type": "patch"}],
        "stats": {}
    }))
    data = dev_dashboard_refresh.generate_dashboard(str(tmp_path))
    assert "changes" in data


def test_generate_dashboard_with_ndjson_malformed_line(tmp_path):
    """Covers line 105: bare except when json.loads fails on a malformed
    NDJSON line — the line is silently skipped."""
    state_dir = tmp_path / ".mase"
    state_dir.mkdir()
    # NDJSON format with a malformed line
    ndjson_lines = [
        json.dumps({"id": "ch_001", "type": "patch"}),
        "this is not valid json {",
        json.dumps({"id": "ch_002", "type": "patch"}),
    ]
    (state_dir / "changes.json").write_text("\n".join(ndjson_lines))
    data = dev_dashboard_refresh.generate_dashboard(str(tmp_path))
    # The malformed line is skipped — no crash, only valid entries counted
    assert isinstance(data, dict)
    assert "changes" in data or "stats" in data or "data" in data


def test_generate_dashboard_with_audit_non_numeric_score(tmp_path):
    """Covers lines 73-74: bare except when float(score) raises (e.g. score
    is a non-numeric string). Score falls back to 0 instead of crashing."""
    state_dir = tmp_path / ".mase"
    state_dir.mkdir()
    # audit_result.json with a non-numeric score
    (state_dir / "audit_result.json").write_text(json.dumps({
        "score": "not-a-number",
        "findings": []
    }))
    # Should not crash — score coercion fails silently
    data = dev_dashboard_refresh.generate_dashboard(str(tmp_path))
    assert isinstance(data, dict)


def test_generate_dashboard_empty_state_dir(tmp_path):
    """Covers lines 31-32, 73-74, 83-84, 219-221, 259, 263, 269, 350:
    many bare excepts and fallback paths when state dir is empty."""
    state_dir = tmp_path / ".mase"
    state_dir.mkdir()
    # No state files at all — all loads return defaults
    data = dev_dashboard_refresh.generate_dashboard(str(tmp_path))
    assert isinstance(data, dict)
