"""Tests for tools/dev_im_finder_scan.py — coverage gap closer.

Covers the 18 missed statements in dev_im_finder_scan.py by exercising:
- __getattr__ proxy with unknown attribute (line 178: AttributeError)
- add_finding proxy + sync logic (lines 191-203)
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import dev_im_finder_scan as mod


def test_getattr_unknown_attribute_raises():
    """Covers line 178: __getattr__ raises AttributeError for unknown
    attribute names."""
    with pytest.raises(AttributeError) as exc_info:
        _ = mod.nonexistent_attribute_xyz123
    assert "nonexistent_attribute_xyz123" in str(exc_info.value)


def test_add_finding_proxy_basic(monkeypatch):
    """Covers lines 191-203: add_finding sync logic — globals['findings']
    is synced to LIB before delegation, and back after."""
    # Reset state for test isolation
    import dev_im_finder_scan_lib as lib
    monkeypatch.setattr(lib, "findings", [], raising=False)

    # Add a finding via the CLI wrapper
    mod.add_finding(
        ftype="test_type",
        severity="low",
        file="test.py",
        issue="test issue",
        impact="test impact",
        fix="test fix",
    )
    # Sync should make mod.findings == lib.findings
    assert mod.findings is lib.findings
