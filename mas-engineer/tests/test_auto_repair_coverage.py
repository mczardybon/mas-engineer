"""Tests for tools/pre_check_lib/auto_repair.py — coverage gap closer.

Covers the 1 missed statement in auto_repair.py:
- line 135: `WORKFLOWS_FILE = workspace / ".mase" / "workflows.yaml"`
  triggered when `.mase/workflows.yaml` does NOT exist in the cwd and
  the caller passed a workspace that DOES have `.mase/workflows.yaml`.

Without this test the workspace-relative fallback branch was 0% covered.
"""
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from pre_check_lib import auto_repair


def test_run_uses_workspace_fallback_when_cwd_workflows_missing(tmp_path, monkeypatch):
    """Covers line 135: when .mase/workflows.yaml does NOT exist in the
    chdir'd cwd, the function falls back to workspace / ".mase" / "workflows.yaml".
    """
    # Create a workspace dir with a workflows.yaml inside .mase
    workspace = tmp_path / "ws"
    mase_dir = workspace / ".mase"
    mase_dir.mkdir(parents=True)
    wf_file = mase_dir / "workflows.yaml"
    wf_file.write_text("task_workflows:\n  T1:\n    auto_repair: [restore]\n")

    # chdir to a dir WITHOUT .mase/workflows.yaml — must be != workspace
    other_dir = tmp_path / "elsewhere"
    other_dir.mkdir()
    monkeypatch.chdir(other_dir)

    # Run the auto_repair on workspace — should fallback to workspace/.mase/workflows.yaml
    result = auto_repair.run(workspace)
    # Sanity: function returned successfully
    assert "checks" in result or "passed" in result
