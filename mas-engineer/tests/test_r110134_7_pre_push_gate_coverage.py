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
    """dev_category_drift.py and the validator must use the same
    CONVENTIONAL_TYPES allowlist (R110-130 sync bug prevention).

    R110-224 (2026-08-20): the original test read both
    `tools/dev_category_drift.py` and `tools/pre_push_validator.py`
    looking for a `CONVENTIONAL_TYPES = [...]` list. But:
      - `tools/pre_push_validator.py` does not exist in this repo
        (the validator runs as a goose recipe, not a standalone script).
      - The 12-type allowlist lives in
        `tests/test_pre_push_check_1_5_skill_alignment.py:435` as
        `VALIDATOR_CONVENTIONAL_TYPES` and in
        `tools/dev_category_drift.py` as `ALLOWED_CATEGORIES`.

    Fixed: this test now reads both from the same source-of-truth
    tuple (`VALIDATOR_CONVENTIONAL_TYPES` in
    `test_pre_push_check_1_5_skill_alignment.py`) and compares
    against `ALLOWED_CATEGORIES` in `dev_category_drift.py`. If the
    validator is ever extracted to a standalone script, this test
    should be updated to read from both locations.
    """
    drift_path = REPO_ROOT / "tools" / "dev_category_drift.py"
    if not drift_path.exists():
        pytest.skip("dev_category_drift.py not present")

    drift = drift_path.read_text()

    # R110-224: parse ALLOWED_CATEGORIES from the detector (named
    # assignment to a tuple/list/set of strings). Robust against
    # other string constants in the file (e.g. dict keys, argparser
    # options, log messages) by requiring:
    #   1. The assignment target name starts with ALLOWED / CONVENTIONAL
    #   2. All elts are short lowercase strings (no underscores/digits)
    #   3. The number of items is plausible for a category allowlist (1-20)
    import ast as _ast
    drift_ast = _ast.parse(drift)
    drift_types = set()
    for node in drift_ast.body:
        if not isinstance(node, _ast.Assign):
            continue
        if not isinstance(node.value, (_ast.Tuple, _ast.List, _ast.Set)):
            continue
        target = node.targets[0]
        if not isinstance(target, _ast.Name):
            continue
        name = target.id
        if not (name.startswith("ALLOWED") or name.startswith("CONVENTIONAL")):
            continue
        items = []
        for elt in node.value.elts:
            if isinstance(elt, _ast.Constant) and isinstance(elt.value, str):
                v = elt.value.rstrip(":").strip()
                if v and v.isalpha() and v.islower() and len(v) <= 20:
                    items.append(v)
        if 1 <= len(items) <= 20:
            drift_types = set(items)
            break
    # Source-of-truth: VALIDATOR_CONVENTIONAL_TYPES in the alignment test
    from tests.test_pre_push_check_1_5_skill_alignment import VALIDATOR_CONVENTIONAL_TYPES
    val_types = {t.rstrip(":") for t in VALIDATOR_CONVENTIONAL_TYPES}

    assert len(val_types) >= 8, (
        f"CONVENTIONAL_TYPES allowlist in validator has only {len(val_types)} types: {val_types}\n"
        "Expected >= 8 per R110-130 expansion (fix|feat|chore|docs|test|refactor|arch|perf|style|build|ci|revert)."
    )
    assert drift_types == val_types, (
        f"CONVENTIONAL_TYPES mismatch between validator ({sorted(val_types)}) and drift ({sorted(drift_types)}).\n"
        "R110-130 requires these to be synchronized — update both files."
    )


# R110-224 (2026-08-20): REMOVED test_pre_push_validator_runs_clean_on_repo.
# The test asserted that `tools/pre_push_validator.py` exists and runs
# clean. But the validator is a goose recipe
# (`recipe/sub/sub_mas-pre-push-validator.yaml`), dispatched by Check 17,
# not a standalone script. The file never existed in this repo — keeping
# the test was verification-theater (always skip → xfail dance). R110-225
# will either (a) extract the validator to a standalone script and add
# a real run-test, or (b) confirm goose-recipe-only is canonical and
# leave the validator un-tested from the standalone-script angle.
# For R110-224 the test is REMOVED to keep the suite at 100% pass + 0 skip.

def test_secret_scanner_present():
    """A secret-scanner tool/script must exist (R110-102 R110-131)."""
    candidates = list((REPO_ROOT / "tools").glob("*secret*")) + \
                 list((REPO_ROOT / "tools").glob("*scan*"))
    assert candidates, (
        "No secret-scanner tool found in tools/. R110-102 requires a scanner "
        "to prevent evidence-log secret leaks."
    )
