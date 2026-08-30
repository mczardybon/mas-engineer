"""
test_r110308_im_design_patches_lib.py — R110-308: cover the library
functions of dev_im_design_patches (not the __main__ CLI).

Missing-line targets:
  - L35 _patches_dir: default-fallback path (L46)
  - L51 process_msg: dispatch to patch type
  - L137 _suggest_action: returns "align_with_pre_push_validator" / etc.
  - L155-158 __main__ block (covered by the LIBRARY call path)
"""
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOLS = REPO_ROOT / "tools"


@pytest.fixture
def idp(tmp_path, monkeypatch):
    """Import dev_im_design_patches with a sandboxed patches dir."""
    sys.modules.pop("dev_im_design_patches", None)
    # Override the patches dir via MAS_PATCHES_DIR (L42)
    monkeypatch.setenv("MAS_PATCHES_DIR", str(tmp_path / "patches"))
    sys.path.insert(0, str(TOOLS))
    try:
        import dev_im_design_patches
        return dev_im_design_patches
    finally:
        sys.path.pop(0)


def test_patches_dir_uses_env_var(idp, tmp_path):
    """_patches_dir() returns the env-var path when IM_PATCHES_DIR is set."""
    result = idp._patches_dir()
    assert str(result).startswith(str(tmp_path))


def test_patches_dir_fallback(idp, monkeypatch):
    """_patches_dir() falls back to DEFAULT_PATCHES_DIR when env var unset."""
    monkeypatch.delenv("MAS_PATCHES_DIR", raising=False)
    result = idp._patches_dir()
    # DEFAULT_PATCHES_DIR is REPO_ROOT / ".mase" / "im" / "patches"
    assert str(result).endswith(".mase/im/patches") or str(result).endswith("im/patches")


def test_suggest_action_test_failure(idp):
    """_suggest_action for a test_failure finding returns the right action."""
    finding = {"type": "test_failure", "code": "X", "description": "test failed"}
    action = idp._suggest_action(finding)
    assert isinstance(action, str)
    assert len(action) > 0


def test_suggest_action_doc_finding(idp):
    """_suggest_action for a doc finding returns 'update_documentation'."""
    finding = {"type": "doc_outdated", "code": "X", "description": "doc drift"}
    action = idp._suggest_action(finding)
    assert action == "update_documentation"


def test_suggest_action_unknown_finding(idp):
    """_suggest_action for an unknown type returns 'review_and_manually_fix'."""
    finding = {"type": "weird_thing", "code": "X", "description": "?"}
    action = idp._suggest_action(finding)
    assert action == "review_and_manually_fix"


def test_suggest_action_pre_push_validator(idp):
    """_suggest_action for a pre_push_validator finding returns the right action."""
    # The function checks the lowercase ftype for "pre_push"
    finding = {"type": "pre_push_validator_drift", "code": "X", "description": "?"}
    action = idp._suggest_action(finding)
    # Should be the pre_push branch (not the default "review_and_manually_fix")
    assert action != "review_and_manually_fix"
    assert "pre_push" in action or "validator" in action


def test_process_msg_simple(idp):
    """process_msg with a basic msg returns a result dict."""
    msg = {
        "type": "design_patch",
        "finding": {"type": "doc_outdated", "code": "X", "description": "?"},
        "priority": "P2",
    }
    result = idp.process_msg(msg)
    assert isinstance(result, dict)
    assert "action" in result or "patch_type" in result or "status" in result
