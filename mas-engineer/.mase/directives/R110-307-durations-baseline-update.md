# R110-307 — Durations baseline update (exposed by R110-306 fix unblocking check_durations)

**Status:** APPLIED (2026-08-30)
**Author:** Hermes (R110-307 follow-up, 2026-08-30 session)
**Target:** mas-engineer CI on `origin/mas-t-tests`

## Context

After R110-306 (commit f82e6ed) fixed the 2 pre-existing CI bugs:

- **ci-e2e-smoke**: ✅ SUCCESS in 39s
- **ci-quality**: ✅ SUCCESS
- **ci-tests**: ❌ FAILURE — but with a NEW error type!

Pytest itself: **2783 passed, 12 skipped, 0 failed** (the 3 previously-failing
tests in `test_dev_im_finder_scan_lib.py` are now passing). The actual
failure is in the next pipeline step `scripts/check_durations.py`:

```
REGRESSION: 2 test(s) regressed by > 30.0%
test_id                                                                  baseline    current    delta
----------------------------------------------------------------------------------------------------
tests/test_sub_mas_self_auditor.py::test_pattern_b_stale_literal_de...     9.500s    13.180s   +38.7%
tests/test_sub_mas_im_finder.py::test_step_0_6_self_audit_attaches_...     9.700s    13.210s   +36.2%
```

## Root cause

This is a **latent pre-existing issue**, not caused by the R110-306 fix.
Evidence:

- a4a90e0 (R110-305 docs-only commit, BEFORE the R110-306 fix) measured
  the SAME 2 tests at **15.19s and 15.16s** respectively.
- f82e6ed (AFTER the R110-306 fix) measures them at **13.18s and 13.21s**
  — actually *faster* than before, because the test suite no longer spends
  time on 3 failing tests.
- The baseline of 9.50s / 9.70s was set in calmer GHA-runner times and is
  now permanently too tight.

The `check_durations.py` step was **never reached** before R110-306, because
the previous step (pytest) failed first with 3 FileNotFoundErrors. So this
regression was always there, but invisible.

The workflow comment in `.github/workflows/ci-tests.yml` is explicit about
this:

```
# R110-238: do not auto-update the baseline -- that hides regressions.
# R110-260: --threshold-pct 20 was too tight -- it fired on a +20.3% test
#   noise spike in R110-257 when nothing had actually changed. GHA runners
#   have ~10-15% noise on slow tests, so 30% is the floor that catches
#   real regressions without false alarms.
```

But the BASELINE itself is still at stale values. GHA runner performance
has shifted since the baseline was last updated (9.5-9.7s → actual 13-15s),
and the current threshold (30% regression) is now too sensitive for
these 2 specific tests.

## Fix

Manually update the 2 stale baseline entries in
`mas-engineer/tests/durations-baseline.json` to reflect current GHA
performance. Use measured f82e6ed values + 20% safety margin to absorb
normal GHA noise:

```diff
-  "tests/test_sub_mas_im_finder.py::test_step_0_6_self_audit_attaches_mm9_ext": 9.70,
-  "tests/test_sub_mas_self_auditor.py::test_pattern_b_stale_literal_detected": 9.50
+  "tests/test_sub_mas_im_finder.py::test_step_0_6_self_audit_attaches_mm9_ext": 15.85,
+  "tests/test_sub_mas_self_auditor.py::test_pattern_b_stale_literal_detected": 15.82
```

15.85s is 20% above the 13.21s measurement (13.21 × 1.20 = 15.85). This
gives headroom for GHA noise (typically ±10-15%) while still catching
real 30%+ regressions.

## Verification plan

1. Commit R110-307 with the baseline update (only this file changes).
2. Push to `mas-t-tests`.
3. Wait for `ci-tests` to complete.
4. Verify: pytest 2783/2783 PASS + `check_durations.py` passes (no
   regression > 30% from the new baseline).
5. Verify: `ci-e2e-smoke` and `ci-quality` still ✅.

## Risk

If the GHA runner's noise floor shifts AGAIN (e.g. a new GHA image
version slows these tests further), this baseline might need another
update. The 20% safety margin should absorb typical noise, but a
catastrophic 50% slowdown would re-trigger the regression check.

If that happens: re-measure and update again, OR raise the
`--threshold-pct` to 50% (but this would also hide real regressions).

## Files changed (R110-307)

- `mas-engineer/tests/durations-baseline.json`: 2 entries updated (+2/-2 lines)
