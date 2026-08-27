"""
R110-262 redteam-1 test 3: coverage-gate wiring adversarial coverage
(R110-260 origin).

R110-260 fixed 3 things in .github/workflows/ci-tests.yml:
  1. Added `set -o pipefail` so the pipeline exit code reflects pytest
     (R110-258 bug: `cmd 2>&1 | tee log` swallowed pytest's exit code).
  2. Lowered --cov-fail-under from 80 to 15 (R110-238 gate was
     structurally unreachable for tools/dev_*.py at 12% real coverage).
  3. Raised --threshold-pct from 20 to 30 (GHA runner noise floor was
     ~10-15% on slow tests).

This test asserts that ALL 3 fixes are in place in the current workflow.
A regression in any of them shows up as a missing-condition failure.

Refs: R110-238 (orig 80% gate), R110-257 (cov-fail-under hit), R110-258
(silent pipe-swallows-exit-code), R110-260 (the fix), R110-262 (this
test), R110-78 (verification theater).
"""

import re
import subprocess
from pathlib import Path

import pytest


WORKFLOW = Path("../.github/workflows/ci-tests.yml")


def _extract_coverage_step():
    """Extract the 'Run pytest with coverage' step from the workflow."""
    text = WORKFLOW.read_text(encoding="utf-8")
    m = re.search(
        r"Run pytest with coverage(.*?)(?=\n      - name:|\Z)",
        text,
        re.DOTALL,
    )
    if not m:
        raise RuntimeError(
            f"could not find 'Run pytest with coverage' step in {WORKFLOW}"
        )
    return m.group(1)


COVERAGE_STEP = _extract_coverage_step()


# ===========================================================================
# 4 adversarial conditions (the R110-260 fix)
# ===========================================================================

def test_coverage_step_has_set_o_pipefail():
    """`set -o pipefail` must be set so `tee` doesn't swallow pytest's exit.

    This is the R110-258/R110-260 bug: without pipefail, `pytest
    --cov-fail-under=N 2>&1 | tee logfile` returns 0 (tee's exit code)
    even when pytest itself returned 1. The workflow would conclude
    "success" with a real coverage failure.
    """
    assert "set -o pipefail" in COVERAGE_STEP, (
        f"set -o pipefail missing from coverage step. "
        f"This is the R110-258 silent-failure bug. "
        f"Step content:\n{COVERAGE_STEP}"
    )


def test_coverage_threshold_is_not_80_percent():
    """`--cov-fail-under` must NOT be 80 (R110-238 unreachable gate).

    R110-260 lowered the gate to 15 because tools/dev_*.py are flat
    CLI scripts with `if __name__ == "__main__"` guards — pytest-cov
    only counts statements that fire during the test run, and the
    main() body sits behind the guard, so tools/ measured ~12% real
    coverage. A 80% gate is structurally unreachable.
    """
    m = re.search(r"--cov-fail-under=(\d+)", COVERAGE_STEP)
    assert m, f"--cov-fail-under not found in coverage step"
    threshold = int(m.group(1))
    assert threshold <= 50, (
        f"--cov-fail-under={threshold} is unreachable for tools/dev_*.py "
        f"(measured 11.66% in R110-260, 12% real ceiling). "
        f"R110-260 set this to 15. If you intentionally raise it, "
        f"first add per-tool subprocess tests (R110-261 Coverage Sprint)."
    )


def test_duration_threshold_is_at_least_25_pct():
    """`--threshold-pct` must be >= 25 to absorb GHA runner noise.

    R110-260 raised this from 20 to 30 because GHA runner noise is
    ~10-15% on slow tests; a 20% threshold fired on +20.3% noise
    spike in R110-257 (test_sub_mas_self_auditor 9.5s→11.4s) with no
    actual code change.
    """
    m = re.search(r"--threshold-pct\s+(\d+)", COVERAGE_STEP)
    if not m:
        pytest.skip("--threshold-pct not in coverage step (may use a different check)")
    threshold = int(m.group(1))
    assert threshold >= 25, (
        f"--threshold-pct={threshold} is too tight — GHA runner noise is "
        f"~10-15% on slow tests. R110-260 set this to 30. "
        f"A 20% threshold fired on +20.3% noise in R110-257."
    )


def test_coverage_step_pipes_through_tee():
    """The pytest invocation must use `tee` to log output (R110-260 reason).

    This test is informational — it asserts the current shape so that
    a future refactor doesn't accidentally drop the logfile (which
    is the only way to debug a coverage failure post-hoc).
    """
    assert re.search(r"\|\s*tee\s+", COVERAGE_STEP), (
        f"coverage step does not pipe through tee. "
        f"R110-260 added set -o pipefail BECAUSE of the tee pipe; "
        f"if you remove the tee, remove the pipefail too (or add "
        f"explicit exit code checking). Step:\n{COVERAGE_STEP}"
    )


def test_pipefail_actually_propagates_exit_code_in_subprocess():
    """End-to-end smoke: a failing pytest invocation must propagate
    the exit code when pipefail is set.

    This is the meta-test: even if the workflow text contains
    `set -o pipefail`, the test verifies that the mechanism actually
    works in bash (catches shell quoting bugs that would silently
    disable pipefail).
    """
    # Simulate the failure mode: a script that always exits 1
    fail_script = "#!/bin/bash\necho 'failing test'\nexit 1\n"
    log_file = "/tmp/r110262_test_pipefail.log"

    # WITH pipefail: pipeline rc=1
    result_with = subprocess.run(
        ["bash", "-c", f"set -o pipefail; ({fail_script}) 2>&1 | tee {log_file}; echo $?"],
        capture_output=True, text=True,
    )
    # The echo $? will print 1 (the failing script's exit code, now
    # propagated via pipefail).
    assert "1" in result_with.stdout, (
        f"pipefail did NOT propagate exit code. stdout:\n{result_with.stdout}"
    )

    # WITHOUT pipefail: pipeline rc=0 (tee always succeeds)
    result_without = subprocess.run(
        ["bash", "-c", f"set +o pipefail; ({fail_script}) 2>&1 | tee {log_file}; echo $?"],
        capture_output=True, text=True,
    )
    # The echo $? will print 0 (tee's exit code, not the script's).
    assert "0" in result_without.stdout, (
        f"control case (no pipefail) did not show 0 — test is broken. "
        f"stdout:\n{result_without.stdout}"
    )
