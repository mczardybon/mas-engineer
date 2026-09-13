"""Tests for tools/dev_changes.py — focus on coverage gaps.

The R110-493 coverage push needs tests for the 2 missed statements in
dev_changes.py:
- line 135: `meta = next((d for d in data if "changes" in d), {"changes": [], "stats": {}})`
  → triggered when CHANGES_FILE contains legacy list-format with mixed entries
- line 245: `output.append(f"      User: {c['user_comment']}")`
  → triggered when a change entry has a truthy `user_comment`

Both branches were not exercised by existing tests; this module adds
unit-tests that:
1. Trigger line 135 by writing a legacy-format list (not dict) into CHANGES_FILE
2. Trigger line 245 by formatting a change with a user_comment

These tests use a tmp_path fixture and monkeypatch CHANGES_FILE +
STATE_DIR so we don't touch real state.
"""
import importlib
import json
import sys
from pathlib import Path

import pytest

# Ensure tools/ is importable (R110-377 pattern)
REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))


@pytest.fixture
def dev_changes_loaded(tmp_path, monkeypatch):
    """Load dev_changes.py with CHANGES_FILE redirected to tmp_path."""
    # Make sure a fresh import happens (not cached from earlier)
    if "dev_changes" in sys.modules:
        del sys.modules["dev_changes"]
    # Create the tmp state dir + changes file before import
    fake_state = tmp_path / ".mase"
    fake_state.mkdir()
    fake_changes = fake_state / "changes.json"
    # Initialize with current dict format
    fake_changes.write_text(json.dumps({
        "metadata": {"agent": "test", "version": "1.0.0", "last_updated": "2026-01-01T00:00:00Z", "total_changes": 0},
        "changes": [],
        "stats": {"harden": 0, "evolve": 0, "patch": 0, "other": 0, "rolled_back": 0, "last_24h": 0},
    }))
    # Patch sys.argv so resolve_state_dir() doesn't pick up --workspace
    monkeypatch.setattr(sys, "argv", ["pytest"])
    # Patch Path(__file__).parent.parent to point to our tmp_path
    # dev_changes.py uses: (Path(__file__).parent.parent / ".mase").resolve()
    # We'll override the module-level constants after import.
    import dev_changes
    monkeypatch.setattr(dev_changes, "STATE_DIR", fake_state)
    monkeypatch.setattr(dev_changes, "CHANGES_FILE", fake_changes)
    return dev_changes


def test_add_change_handles_legacy_list_with_meta_block(dev_changes_loaded, tmp_path):
    """Covers line 135: meta = next(...) when CHANGES_FILE is legacy list-format
    that contains a metadata dict with 'changes' key.

    This path is hit by R110-233-migrated legacy data; without this test
    the branch was 0% covered."""
    # Rewrite CHANGES_FILE to legacy list-format with one meta-block
    legacy = [
        {"timestamp": "2026-08-14T10:00:00Z", "action": "CREATE sub_mas-clone"},
        {"changes": [{"id": "ch_legacy_001", "file": "legacy.py", "timestamp": "2026-08-14T10:00:00Z"}], "stats": {}, "timestamp": "2026-08-14T10:00:00Z"},
    ]
    dev_changes_loaded.CHANGES_FILE.write_text(json.dumps(legacy))
    # add_change should detect list, find meta block, append new change
    change = dev_changes_loaded.add_change({
        "file": "test.py", "von": "v1", "nach": "v2",
        "grund": "test", "type": "patch", "user_comment": ""
    })
    assert isinstance(change, dict)
    assert change["id"].startswith("ch_")
    # And the resulting file should be in dict-format
    data = json.loads(dev_changes_loaded.CHANGES_FILE.read_text())
    assert "changes" in data
    assert any("id" in c for c in data["changes"])


def test_show_history_with_user_comment(dev_changes_loaded):
    """Covers line 245: output.append(f"      User: {c['user_comment']}")
    when a change has a truthy user_comment."""
    change = dev_changes_loaded.add_change({
        "file": "f.py", "von": "a", "nach": "b",
        "grund": "g", "type": "patch",
        "user_comment": "this is my comment"
    })
    history = dev_changes_loaded.show_history()
    assert "User: this is my comment" in history
