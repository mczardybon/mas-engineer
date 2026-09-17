"""Tests for tools/dev_dispatch_live.py — coverage gap closer.

Covers the missed statements in dev_dispatch_live.py. Focus on the
simplest branch first: line 45 (OSError when reading the dispatch log).
"""
import json
import sys
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import dev_dispatch_live


def test_read_dispatch_log_returns_empty_on_oserror(tmp_path, monkeypatch):
    """Covers line 45: when the dispatch log file can't be opened
    (OSError, e.g. permission denied), _read_dispatch_log() returns []."""
    # Make Path() resolve to a non-existent + un-creatable location
    # by patching open() to raise OSError
    import builtins
    real_open = builtins.open

    def fake_open(path, *args, **kwargs):
        if "dispatch.log" in str(path):
            raise OSError("simulated permission denied")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)
    monkeypatch.setattr(dev_dispatch_live, "DISPATCH_LOG", str(tmp_path / "dispatch.log"))
    entries = dev_dispatch_live._read_dispatch_log()
    assert entries == []
