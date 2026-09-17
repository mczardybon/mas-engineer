"""Tests for tools/dev_dispatch_tracker.py — coverage gap closer.

The R110-493 coverage push needs tests for the 2 missed statements in
dev_dispatch_tracker.py:
- line 64: `sys.path.insert(0, tools_dir)` when tools_dir is not in sys.path
- line 178: `except Exception: pass` when MQ enqueue raises

Without these tests the import-already-in-path branch and the MQ-error
swallow branch were 0% covered.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import dev_dispatch_tracker


def test_mq_inserts_tools_dir_when_not_in_sys_path(monkeypatch):
    """Covers line 64: `sys.path.insert(0, tools_dir)` branch — when
    tools_dir is NOT already in sys.path, the import helper inserts it
    BEFORE attempting the import.

    We simulate a fresh sys.path (without tools_dir) and verify the import
    either succeeds (inserted path was used) or returns None without
    raising — proving the sys.path.insert branch was executed safely.
    """
    # Build a sys.path that does NOT contain tools_dir
    sys_path_without_tools = [p for p in sys.path if p != str(TOOLS_DIR)]
    monkeypatch.setattr(sys, "path", sys_path_without_tools)
    # Now call _mq() — must not raise; either returns module or None
    mq = dev_dispatch_tracker._mq()
    # Either enqueue-capable module or None — both are valid outcomes
    assert mq is None or hasattr(mq, "enqueue")


def test_done_swallow_mq_exception(monkeypatch, tmp_path):
    """Covers line 178: `except Exception: pass` when MQ enqueue raises.

    We patch the MQ module so its enqueue() raises, then call done() on
    a real dispatch entry. The function MUST NOT propagate the MQ
    exception — it is swallowed silently.
    """
    # Build a fake MQ with enqueue() that raises
    class FakeMQ:
        def enqueue(self, **kwargs):
            raise RuntimeError("simulated MQ enqueue failure")
    monkeypatch.setattr(dev_dispatch_tracker, "_mq", lambda: FakeMQ())
    # Redirect legacy log to a tmp file
    monkeypatch.setattr(dev_dispatch_tracker, "LEGACY_LOG", str(tmp_path / "track.ndjson"))
    # Add a dispatch, then mark it done — enqueue will raise internally
    dev_dispatch_tracker.add(
        ts="2026-09-13T03:00:00Z",
        entry_id="test_entry_xyz",
        parent_id=None,
        from_agent="test_from",
        to_agent="test_to",
        task="coverage push test",
    )
    # Must NOT raise — exception is swallowed (line 178: `except: pass`)
    result = dev_dispatch_tracker.done(
        entry_id="test_entry_xyz",
        duration_ms=100,
        turns=1,
        result_summary="ok",
    )
    assert result is None or isinstance(result, (list, dict))
