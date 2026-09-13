"""Tests for tools/dev_agent_doctor.py — coverage gap closer.

Covers lines 25-26 (yaml ImportError fallback) in dev_agent_doctor.py.
"""
import importlib
import sys
import builtins
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))


def test_yaml_import_error_fallback_prints_and_exits(monkeypatch):
    """Covers lines 25-26: when yaml is not importable, the module
    prints a friendly error and sys.exit(1)s.

    Strategy: temporarily remove yaml from sys.modules and patch
    __import__ to raise ImportError for any 'yaml' import. Then reload
    dev_agent_doctor with sys.exit monkeypatched to raise SystemExit.
    """
    # Remove yaml from sys.modules
    saved_yaml = sys.modules.pop("yaml", None)

    # Patch __import__ to raise ImportError when trying to import yaml
    real_import = builtins.__import__
    def fake_import(name, *args, **kwargs):
        if name == "yaml" or name.startswith("yaml."):
            raise ImportError(f"No module named '{name}'")
        return real_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", fake_import)

    # Patch sys.exit to raise SystemExit instead of killing the test
    exits = []
    def fake_exit(code):
        exits.append(code)
        raise SystemExit(code)
    monkeypatch.setattr(sys, "exit", fake_exit)

    # Capture stdout
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()

    # Remove cached dev_agent_doctor so the import re-runs the try/except
    sys.modules.pop("dev_agent_doctor", None)

    try:
        with redirect_stdout(buf):
            with pytest.raises(SystemExit):
                importlib.import_module("dev_agent_doctor")
    finally:
        # Restore yaml + import
        if saved_yaml is not None:
            sys.modules["yaml"] = saved_yaml
        sys.modules.pop("dev_agent_doctor", None)
        builtins.__import__ = real_import

    out = buf.getvalue()
    assert "yaml not installed" in out
    assert "pip3 install pyyaml" in out
    assert exits == [1]
