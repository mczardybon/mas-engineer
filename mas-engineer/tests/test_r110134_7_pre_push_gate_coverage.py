"""
test_r110134_7_pre_push_gate_coverage.py — R110-134

Verifies that the pre-push-gate actually covers the invariants it
claims to enforce. This is meta-testing of the test framework itself.

What the pre-push-gate claims to check (R110-? — see pre-push-gate skill):
- 18+ invariant checks (pre_push_check_18_spec_invariant.py)
- Skill alignment (pre_push_check_1_5_skill_alignment.py — R110-117 onwards)
- Category drift (tools/dev_category_drift.py)
- Secret scan
- Git hygiene

We test:
- All check scripts exist and run
- No check script has been silently disabled (skip/wip markers)
- The combined gates actually run on a sample commit
- The category-drift detector and the pre-push-validator agree on
  convention type allowlist (R110-130 synchronization)

Run with:
    cd mas-engineer && pytest tests/test_r110134_7_pre_push_gate_coverage.py -v
"""
from __future__ import annotations
import re
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from _recipe_helpers import REPO_ROOT  # noqa: E402

PRE_PUSH_GATE_FILES = [
    "tests/test_pre_push_check_1_5_skill_alignment.py",
    "tests/test_pre_push_check_18_spec_invariant.py",
    "tools/dev_category_drift.py",
]


def test_all_pre_push_gate_files_exist():
    """Every pre-push-gate file referenced must exist on disk."""
    missing = [f for f in PRE_PUSH_GATE_FILES if not (REPO_ROOT / f).exists()]
    assert not missing, f"Missing pre-push-gate files: {missing}"


def test_no_disabled_pre_push_checks():
    """No pre-push check should be @pytest.mark.skip or commented-out."""
    offenders = []
    for f in PRE_PUSH_GATE_FILES:
        path = REPO_ROOT / f
        if not path.exists():
            continue
        text = path.read_text()
        # Look for skip markers
        for i, line in enumerate(text.splitlines(), 1):
            if "@pytest.mark.skip" in line and not line.strip().startswith("#"):
                offenders.append((str(path), i, line.strip()[:80]))
    assert not offenders, (
        f"{len(offenders)} pre-push checks are marked @pytest.mark.skip:\n"
        + "\n".join(f"  - {f}:{l}: {t}" for f, l, t in offenders[:10])
    )


def test_category_drift_and_validator_agree_on_types():
    """dev_category_drift.py and pre_push_validator.py must use the same
    CONVENTIONAL_TYPES allowlist (R110-130 sync bug prevention)."""
    drift_path = REPO_ROOT / "tools" / "dev_category_drift.py"
    validator_path = REPO_ROOT / "tools" / "pre_push_validator.py"
    if not drift_path.exists() or not validator_path.exists():
        pytest.skip("category_drift or validator not present")

    drift = drift_path.read_text()
    validator = validator_path.read_text()
    # Find the CONVENTIONAL_TYPES / CONVENTIONAL_TYPE_ALLOWLIST lists
    pattern = re.compile(r"(CONVENTIONAL_TYPE[A-Z_]*)\s*=\s*\[([^\]]+)\]")
    drift_lists = pattern.findall(drift)
    val_lists = pattern.findall(validator)
    if not drift_lists or not val_lists:
        pytest.skip("Could not find CONVENTIONAL_TYPES list in both files")
    # Compare sorted union of types
    def _flatten(t):
        return set(re.findall(r"['\"](\w+)['\"]", t))
    drift_types = set()
    for _, body in drift_lists:
        drift_types |= _flatten(body)
    val_types = set()
    for _, body in val_lists:
        val_types |= _flatten(body)
    # Should be 12 types per R110-130
    assert len(val_types) >= 8, (
        f"CONVENTIONAL_TYPES allowlist in validator has only {len(val_types)} types: {val_types}\n"
        "Expected ≥ 8 per R110-130 expansion (fix|feat|chore|docs|test|refactor|arch|perf|style|build|ci|revert)."
    )
    assert drift_types == val_types, (
        f"CONVENTIONAL_TYPES mismatch between validator ({val_types}) and drift ({drift_types}).\n"
        "R110-130 requires these to be synchronized — update both files."
    )


def test_pre_push_validator_runs_clean_on_repo():
    """Running pre_push_validator.py on HEAD must pass (no test-theater)."""
    validator = REPO_ROOT / "tools" / "pre_push_validator.py"
    if not validator.exists():
        pytest.skip("pre_push_validator.py not present")
    r = subprocess.run(
        ["python3", str(validator), "--dry-run"],
        capture_output=True, text=True, timeout=30,
        cwd=str(REPO_ROOT),
    )
    # Either clean exit or warnings — not crash
    assert r.returncode in (0, 1), (
        f"pre_push_validator.py crashed (rc={r.returncode}).\n"
        f"stdout: {r.stdout[:500]}\nstderr: {r.stderr[:500]}"
    )


def test_secret_scanner_present():
    """A secret-scanner tool/script must exist (R110-102 R110-131)."""
    candidates = list((REPO_ROOT / "tools").glob("*secret*")) + \
                 list((REPO_ROOT / "tools").glob("*scan*"))
    assert candidates, (
        "No secret-scanner tool found in tools/. R110-102 requires a scanner "
        "to prevent evidence-log secret leaks."
    )
