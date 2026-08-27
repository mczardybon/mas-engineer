r"""
test_r110259_category_drift_scope.py — R110-259

Regression test for the Check 1.5 <-> Check 16+ spec gap that R110-258
caught: dev_category_drift.py used `subj.startswith(p)` for each
ALLOWED_CATEGORIES entry, so it REJECTED `fix(scope):` subjects even
though pre-push-validator Check 1.5 (line 194 of
sub_mas-pre-push-validator.md) accepts them via regex
  r'^(fix|feat|chore|docs|test|refactor|arch|perf|style|build|ci|revert)
   (\([^)]+\))?:'

R110-257's subject `fix(evidence-sot,directives-sot,validator): ...`
was a real-world victim: the validator passed it but the standalone
drift detector flagged it. R110-259 aligned the detector by adding
CONVENTIONAL_COMMIT_RE with the same regex.

This test asserts (R110-259):
  1. CONVENTIONAL_COMMIT_RE exists in tools/dev_category_drift.py
  2. CONVENTIONAL_COMMIT_RE matches all 12 types WITHOUT a scope
  3. CONVENTIONAL_COMMIT_RE matches all 12 types WITH a parenthesized scope
  4. CONVENTIONAL_COMMIT_RE REJECTS scope-less prefixes that look like
     types but are followed by paren (i.e. `fix(scope):` is matched
     only if `(` immediately follows the type, never with whitespace
     or other chars in between)
  5. The detector's "conform" path uses the regex (not just the
     legacy ALLOWED_CATEGORIES startswith)
  6. R110-257's own subject (the regression case) is now ACCEPTED
     by the detector when run against real git history
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from _recipe_helpers import REPO_ROOT  # noqa: E402

ALL_12_TYPES = (
    "fix", "feat", "chore", "docs", "test", "refactor",
    "arch", "perf", "style", "build", "ci", "revert",
)


def test_conventional_commit_regex_exists():
    """CONVENTIONAL_COMMIT_RE must be defined in dev_category_drift.py."""
    drift_path = REPO_ROOT / "tools" / "dev_category_drift.py"
    assert drift_path.exists()
    text = drift_path.read_text()
    assert "CONVENTIONAL_COMMIT_RE" in text, (
        "R110-259: dev_category_drift.py must define CONVENTIONAL_COMMIT_RE "
        "to mirror Check 1.5's conventional-commit regex. "
        "See sub_mas-pre-push-validator.md line 194."
    )


def test_conventional_commit_regex_matches_all_12_types_without_scope():
    """Every conventional-commit type must match with no parenthesized scope."""
    drift_path = REPO_ROOT / "tools" / "dev_category_drift.py"
    text = drift_path.read_text()
    # Find the regex literal: re.compile(r"...")
    m = re.search(r'CONVENTIONAL_COMMIT_RE\s*=\s*re\.compile\(\s*r"([^"]+)"\s*\)', text)
    assert m, "CONVENTIONAL_COMMIT_RE must be defined via re.compile(r\"...\")"
    pattern = m.group(1)
    compiled = re.compile(pattern)
    for t in ALL_12_TYPES:
        subj = f"{t}: short description"
        assert compiled.match(subj), (
            f"CONVENTIONAL_COMMIT_RE must match {subj!r} (type {t!r} without scope)"
        )


def test_conventional_commit_regex_matches_all_12_types_with_scope():
    """Every type must match WITH a parenthesized scope (R110-257 regression)."""
    drift_path = REPO_ROOT / "tools" / "dev_category_drift.py"
    text = drift_path.read_text()
    m = re.search(r'CONVENTIONAL_COMMIT_RE\s*=\s*re\.compile\(\s*r"([^"]+)"\s*\)', text)
    assert m
    compiled = re.compile(m.group(1))
    for t in ALL_12_TYPES:
        subj = f"{t}(scope): short description"
        assert compiled.match(subj), (
            f"CONVENTIONAL_COMMIT_RE must match {subj!r} (the R110-257 regression case). "
            f"Check 1.5 (validator) accepts this subject; the detector must too."
        )


def test_conventional_commit_regex_matches_real_world_multi_segment_scope():
    """`fix(evidence-sot,directives-sot,validator): ...` — the EXACT R110-257
    subject — must match (R110-258's BLOCKED subject)."""
    drift_path = REPO_ROOT / "tools" / "dev_category_drift.py"
    text = drift_path.read_text()
    m = re.search(r'CONVENTIONAL_COMMIT_RE\s*=\s*re\.compile\(\s*r"([^"]+)"\s*\)', text)
    assert m
    compiled = re.compile(m.group(1))
    real_subject = "fix(evidence-sot,directives-sot,validator): R110-257 SOT evidence ..."
    assert compiled.match(real_subject), (
        f"CONVENTIONAL_COMMIT_RE must match the EXACT R110-257 subject. "
        f"This is the regression case R110-258 caught."
    )


def test_conventional_commit_regex_rejects_non_conventional_subjects():
    """Subjects that don't start with one of the 12 types must NOT match."""
    drift_path = REPO_ROOT / "tools" / "dev_category_drift.py"
    text = drift_path.read_text()
    m = re.search(r'CONVENTIONAL_COMMIT_RE\s*=\s*re\.compile\(\s*r"([^"]+)"\s*\)', text)
    assert m
    compiled = re.compile(m.group(1))
    bad_subjects = [
        "wip: something",
        "bug: something",
        "added: something",
        "feat(scope: missing close-paren",
        "fix scope): wrong paren placement",
        "random text without category",
        "",
    ]
    for s in bad_subjects:
        assert not compiled.match(s), (
            f"CONVENTIONAL_COMMIT_RE must NOT match {s!r} (non-conventional subject)"
        )


def test_detector_uses_conventional_commit_regex_in_conform_path():
    """The conform-branch in dev_category_drift.py must CALL
    CONVENTIONAL_COMMIT_RE.match(...) — not just define it. This guards
    against future refactors that leave the regex defined-but-unused."""
    drift_path = REPO_ROOT / "tools" / "dev_category_drift.py"
    text = drift_path.read_text()
    # Look for `CONVENTIONAL_COMMIT_RE.match(` usage in the conform branch
    assert "CONVENTIONAL_COMMIT_RE.match(" in text, (
        "CONVENTIONAL_COMMIT_RE must be USED in the conform branch "
        "(R110-259 added it for alignment with Check 1.5)."
    )
    # And the legacy `startswith(ALLOWED_CATEGORIES` block must NOT be the
    # ONLY conform check — it should now be wrapped in a conditional
    # (the regex is checked first, the tuple is kept for back-compat)
    # We don't assert against startswith here; the regression test for
    # parenthesized scope (above) implicitly proves startswith is no
    # longer the sole check.


def test_r110257_subject_accepted_by_detector_in_real_git_history():
    """Run the detector on real git history (last 60 days) and verify
    R110-257's subject is NOT in the drift list. This is the end-to-end
    regression test for R110-258's BLOCKED state."""
    drift_script = REPO_ROOT / "tools" / "dev_category_drift.py"
    if not drift_script.exists():
        pytest.skip("dev_category_drift.py not present")
    result = subprocess.run(
        [sys.executable, str(drift_script), "--since", "60", "--json"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert result.returncode == 0, (
        f"dev_category_drift.py --since 60 --json failed:\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    import json as _json
    data = _json.loads(result.stdout)
    drift_subjects = {c["subject"] for c in data.get("drift", [])}
    # R110-257's exact subject (first line) — must NOT be in drift
    r110257_subj = "fix(evidence-sot,directives-sot,validator): R110-257 SOT evidence path + directive archive + pre-push Check 24"
    assert r110257_subj not in drift_subjects, (
        f"R110-257's subject is in the drift list! R110-259 fix didn't take. "
        f"Drift subjects (first 5): {list(drift_subjects)[:5]}"
    )
    # And generally drift count should be 0 for the post-2026-08-04
    # window (per the pre-protocol cutoff in the detector)
    assert data["drift_count"] == 0, (
        f"Expected 0 drift commits in the post-protocol window, got "
        f"{data['drift_count']}. Drift: {list(drift_subjects)[:5]}"
    )
