"""
test_githooks_pre_push_empty_file_check.py — R110-403

Verifies that the .githooks/pre-push hook (R108-8) correctly
rejects 0-byte YAML files in recipe/.

Why this test exists (R110-403):
- R110-399 deleted the 0-byte junk file `recipe/sub/sub_-.yaml`
- It was auto-recreated by the IDE save hook (Hermes-MAS-Engineer
  committer) in commit a77ad55 (R110-399 followup) and again
  in 9dc1911, 5a9e391, e382acd (3 prior occurrences)
- The pre-push hook's existing checks (R108-8) only check:
  1. YAML parses (empty doc is valid YAML → passes)
  2. Has `name` and `version` fields (empty doc has no fields →
     but the case-statement only matches `recipe/sub/sub_mas-*.yaml`
     so `sub_-.yaml` was skipped)
- Result: every R-sprint that touches recipe/ has to do
  `git rm -f recipe/sub/sub_-.yaml` as a manual cleanup
  (R110-399, R110-401, R110-402)
- R110-403 adds a `[ ! -s "$f" ]` check to the pre-push hook
  and this test to verify the check works

What this test does:
1. Read .githooks/pre-push and verify it has the empty-file check
2. Run the hook in a temp directory with a synthetic 0-byte
   YAML file, verify the hook exits non-zero
3. Run the hook with a valid 1-line YAML file, verify it
   passes (regression check)
4. Run the hook with a malformed YAML file, verify it
   still fails (regression check for R108-8)

Run with:
    cd mas-engineer && pytest tests/test_githooks_pre_push_empty_file_check.py -v
"""
from __future__ import annotations
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from _recipe_helpers import REPO_ROOT  # noqa: E402

GITHOOK = REPO_ROOT / ".githooks" / "pre-push"


def _read_githook() -> str:
    assert GITHOOK.exists(), f"githook missing: {GITHOOK}"
    return GITHOOK.read_text()


def test_githook_has_empty_file_check():
    """The pre-push hook must have a 0-byte file check (R110-403)."""
    content = _read_githook()
    # The check should be a [ ! -s "$f" ] test
    assert '[ ! -s "$f" ]' in content, (
        "R110-403: pre-push hook missing 0-byte file check.\n"
        "Expected `[ ! -s \"$f\" ]` test that rejects 0-byte files in recipe/.\n"
        "Without this, IDE auto-save junk like `recipe/sub/sub_-.yaml`\n"
        "passes pre-push (empty doc is valid YAML) and pollutes the repo."
    )


def test_githook_empty_file_check_message_is_descriptive():
    """The error message should help the user understand the issue."""
    content = _read_githook()
    # Find the empty-file check block (between [ ! -s and the echo error)
    match = re.search(
        r'\[ ! -s "\$f" \].*?fi',
        content,
        re.DOTALL,
    )
    assert match, "Empty-file check block not found in githook"
    block = match.group(0)
    # Should mention "EMPTY" or "0 bytes" or similar
    assert re.search(r'EMPTY|0 bytes|empty', block, re.IGNORECASE), (
        f"Empty-file check error message should mention EMPTY/0 bytes/empty.\n"
        f"Got block:\n{block}"
    )


def test_githook_executable():
    """The pre-push hook must be executable (git won't run it otherwise)."""
    assert os.access(GITHOOK, os.X_OK), (
        f"pre-push hook not executable: {GITHOOK}\n"
        f"Run: chmod +x {GITHOOK}"
    )


@pytest.fixture
def temp_recipe_repo():
    """Create a temp directory with a synthetic git repo + origin remote
    + mas-engineer/recipe/sub/. The hook compares against
    `origin/<branch>..HEAD`, so a fake remote is REQUIRED. The hook
    also greps for `^mas-engineer/recipe/.*\\.ya?ml$`, so the synthetic
    repo's recipe/ must live under mas-engineer/.
    """
    tmp = Path(tempfile.mkdtemp(prefix="r110403_test_"))
    try:
        # Init a git repo with one commit
        subprocess.run(
            ["git", "init", "-q"],
            cwd=tmp,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@r110403.local"],
            cwd=tmp,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "R110-403 tester"],
            cwd=tmp,
            check=True,
        )
        # Use a stable branch name (the hook reads `git branch --show-current`)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "test-branch"],
            cwd=tmp,
            check=True,
        )
        # Create mas-engineer/recipe/sub/ with a baseline valid file
        (tmp / "mas-engineer" / "recipe" / "sub").mkdir(parents=True)
        (tmp / "mas-engineer" / "recipe" / "sub" / "sub_mas-baseline.yaml").write_text(
            "name: test\nversion: 1.0\n"
        )
        # Initial commit
        subprocess.run(["git", "add", "-A"], cwd=tmp, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "init"],
            cwd=tmp,
            check=True,
        )
        # Set up a fake `origin` remote. We update the remote ref
        # to point at HEAD so `git diff origin/<branch>..HEAD` is
        # non-empty AFTER the test adds a commit.
        subprocess.run(
            ["git", "update-ref",
             "refs/remotes/origin/test-branch",
             "HEAD"],
            cwd=tmp,
            check=True,
        )
        yield tmp
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_githook_rejects_0_byte_yaml(temp_recipe_repo):
    """The pre-push hook must reject a 0-byte YAML file (regression)."""
    # Create a 0-byte junk file in mas-engineer/recipe/sub/
    junk = temp_recipe_repo / "mas-engineer" / "recipe" / "sub" / "sub_-.yaml"
    junk.write_text("")  # 0 bytes
    assert junk.stat().st_size == 0
    subprocess.run(["git", "add", str(junk.relative_to(temp_recipe_repo))], cwd=temp_recipe_repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "[] add junk"], cwd=temp_recipe_repo, check=True)
    # The fixture sets origin/test-branch to the previous HEAD, so
    # `git diff origin/test-branch..HEAD` now shows the junk file.

    # Run the githook
    proc = subprocess.run(
        ["bash", str(GITHOOK)],
        cwd=temp_recipe_repo,
        capture_output=True,
        text=True,
    )
    # Should fail (exit 1)
    assert proc.returncode == 1, (
        f"githook should reject 0-byte YAML, but it exited {proc.returncode}\n"
        f"stdout:\n{proc.stdout}\n"
        f"stderr:\n{proc.stderr}"
    )
    # Should mention EMPTY / 0 bytes
    combined = proc.stdout + proc.stderr
    assert re.search(r'EMPTY|0 bytes|empty', combined, re.IGNORECASE), (
        f"githook error message should mention empty/0 bytes.\n"
        f"Got:\n{combined}"
    )


def test_githook_accepts_valid_yaml(temp_recipe_repo):
    """Regression: a valid YAML file should pass (no false positive)."""
    valid = temp_recipe_repo / "mas-engineer" / "recipe" / "sub" / "sub_mas-good.yaml"
    valid.write_text("name: test\nversion: 1.0\nsub_recipes: []\n")
    subprocess.run(["git", "add", str(valid.relative_to(temp_recipe_repo))], cwd=temp_recipe_repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "[] add good"], cwd=temp_recipe_repo, check=True)

    # Run the githook
    proc = subprocess.run(
        ["bash", str(GITHOOK)],
        cwd=temp_recipe_repo,
        capture_output=True,
        text=True,
    )
    # Should pass (exit 0)
    assert proc.returncode == 0, (
        f"githook should accept valid YAML, but it exited {proc.returncode}\n"
        f"stdout:\n{proc.stdout}\n"
        f"stderr:\n{proc.stderr}"
    )


def test_githook_rejects_malformed_yaml(temp_recipe_repo):
    """Regression: a malformed YAML file should still fail (R108-8)."""
    bad = temp_recipe_repo / "mas-engineer" / "recipe" / "sub" / "sub_mas-bad.yaml"
    bad.write_text("name: [unclosed bracket\n")  # invalid YAML
    subprocess.run(["git", "add", str(bad.relative_to(temp_recipe_repo))], cwd=temp_recipe_repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "[] add bad"], cwd=temp_recipe_repo, check=True)

    # Run the githook
    proc = subprocess.run(
        ["bash", str(GITHOOK)],
        cwd=temp_recipe_repo,
        capture_output=True,
        text=True,
    )
    # Should fail (exit 1)
    assert proc.returncode == 1, (
        f"githook should reject malformed YAML, but it exited {proc.returncode}\n"
        f"stdout:\n{proc.stdout}\n"
        f"stderr:\n{proc.stderr}"
    )
    # Should mention YAML PARSE ERROR
    assert "YAML PARSE ERROR" in (proc.stdout + proc.stderr), (
        f"githook error message should mention YAML PARSE ERROR.\n"
        f"Got:\n{proc.stdout + proc.stderr}"
    )


def test_githook_rejects_0_byte_in_recipe_root(temp_recipe_repo):
    """Edge case: 0-byte file in mas-engineer/recipe/ (not recipe/sub/) is also rejected."""
    bad = temp_recipe_repo / "mas-engineer" / "recipe" / "junk.yaml"
    bad.write_text("")
    subprocess.run(["git", "add", str(bad.relative_to(temp_recipe_repo))], cwd=temp_recipe_repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "[] add recipe junk"], cwd=temp_recipe_repo, check=True)

    proc = subprocess.run(
        ["bash", str(GITHOOK)],
        cwd=temp_recipe_repo,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1, (
        f"githook should reject 0-byte file in recipe/, but it exited {proc.returncode}\n"
        f"stdout:\n{proc.stdout}\n"
        f"stderr:\n{proc.stderr}"
    )
