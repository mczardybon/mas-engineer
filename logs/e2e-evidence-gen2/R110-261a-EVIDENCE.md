# R110-261a EVIDENCE — Library-Bug-Fixes revealed by R110-261

**Date:** 2026-08-27
**Commit:** R110-261a (pending)
**Type:** fix
**Scope:** tools/dev_fast_scan.py, tools/dev_intention_parser.py,
         tests/test_r110261a_library_bug_fixes.py

## TL;DR

R110-261's coverage-sprint revealed three small library-bugs in the
10 tools it tested. R110-261's commit body declared them "tracked as
R110-261a" and out-of-scope for the coverage-sprint. R110-261a is the
fix-up commit.

Two of the three are real library-bugs in need of a code change; the
third (dev_category_drift) turned out to be a docstring/tests-only
issue and requires no source change. Both real bugs are now fixed
and locked in with regression tests.

## What was fixed

### Bug 1: dev_fast_scan.scan_settings — per-condition `ok` counter

**Symptom** (revealed by R110-261 round-3 tests):
A single YAML with both `timeout` and `max_turns` in their acceptable
ranges reported `score=20.0` (not 10.0 as the math suggests at first
glance).

**Root cause:**
```python
# BEFORE (per-condition counter):
if 300 <= t <= 900: ok += 1
if 50 <= m <= 300:  ok += 1   # second increment, same file
# → 1 good file contributed ok=2, total=1 → score = 2/1*10 = 20.0
```

**Fix:**
```python
# AFTER (per-file pass/fail):
timeout_ok = 300 <= t <= 900
max_turns_ok = 30 <= m <= 300
if timeout_ok and max_turns_ok:
    ok += 1
# Cap at 10.0 in the return statement: min(10.0, round(ok/total*10, 1))
```

**Behavioral effect:**
- 1 perfect file: score 20.0 → 10.0 ✅
- 1 file with only one condition passing: was score=10.0 (misleading),
  now score=0.0 ✅ (a half-good file is NOT a pass)
- N perfect files: was score=10.0*min(N,∞) (uncapped), now capped at 10.0 ✅
- 0 settings files: still 10.0 (default-pass for empty corpus) — unchanged

Findings are still emitted per-condition (B1/B2/B3/B4), so the
**finding** side of the API is preserved. Only the **score** semantics
changed.

### Bug 2: dev_intention_parser — requires_confirmation only in restrictions

**Symptom** (revealed by R110-261 round-3 tests):
The R110-261 test for autonomous prompts asserted
`r["requires_confirmation"] is True`, which raised `KeyError`. The
field only existed at `r["restrictions"]["requires_confirmation"]`.

**Root cause:**
The `analyse_intention()` function only ever set
`result["restrictions"]["requires_confirmation"]`. Naive callers that
expect it at the top level get a KeyError. (No existing caller in
mas-engineer currently naively expects it at top level — this was
caught by the R110-261 tests only because the test author initially
guessed the wrong schema.)

**Fix (backward-compat, no behavior change for existing callers):**
```python
# AFTER:
result["restrictions"]["requires_confirmation"] = True
# Top-level alias for naive callers (R110-261a):
result["requires_confirmation"] = result["restrictions"]["requires_confirmation"]
```

`restrictions[...]` remains the authoritative location; top-level is
an alias that always equals the nested value. Both code paths work.

### Bug 3: dev_category_drift — false positive, no source change needed

**Investigation:**
The R110-261 test file originally used a wrong fixture shape
(`{message, files}` instead of `{hash, date, subject}`). The R110-261
tests were corrected to use the right shape. Source code's
`run_git_log` already returns `{hash, date, subject}` (verified by
reading `tools/dev_category_drift.py` lines 121-138). The docstring
of `classify_drift` (line 152) also clearly documents the correct
shape. No source change needed.

**Outcome:**
No fix. The R110-261 tests are the regression-prevention for this
issue (they will fail if a future commit changes the shape).

## What was added

- `tools/dev_fast_scan.py` — fixed scan_settings math (12 line edit,
  including new docstring explaining the cap-at-10 contract)
- `tools/dev_intention_parser.py` — added top-level
  `requires_confirmation` alias (1 line of code + comment)
- `tests/test_r110261a_library_bug_fixes.py` — 9 regression tests
  covering both fixes

## Verification

- New regression tests: 9/9 PASS in 0.07s
  `python3 -m pytest tests/test_r110261a_library_bug_fixes.py -v`
- R110-261 coverage tests: 88/88 PASS (no regression)
  `python3 -m pytest tests/test_r110261_tools_coverage*.py -q`
- e2e-test.sh: 12/12 PASS, 0 FAIL, 0 SKIP
- Full pytest (R110-261 + R110-261a combined): 1764 passed (was 1755 in
  R110-261 baseline, +9 regression tests)
- Manual sanity:
  - dev_fast_scan.scan_settings on 1 good file: now 10.0 (was 20.0)
  - dev_intention_parser.analyse_intention: top-level
    requires_confirmation == restrictions.requires_confirmation == True

## Why R110-261a is a separate commit (not folded into R110-261)

1. **Commit hygiene:** R110-261 = pure test addition (no source code
   change beyond baseline refresh). R110-261a = source code change
   with regression tests. Mixing them in one commit would make the
   "what changed" diff noisy.
2. **Bisect-ability:** If R110-261a's fix breaks something downstream,
   `git bisect` between R110-261 and R110-261a isolates the regression
   cleanly.
3. **Pre-push-gate body-claim correction pattern (R110-78 / R110-258):**
   Splitting "tests reveal bug" from "tests pass after fix" lets the
   changelog tell a cleaner story.

## Diff stat

```
 tests/test_r110261a_library_bug_fixes.py | 178 ++++++++
 tests/test_tools_framework.py            |  22 ++--  (2 tests updated to post-fix behavior)
 tools/dev_fast_scan.py                   |  21 ++-
 tools/dev_intention_parser.py            |   8 +-
 4 files changed, 211 insertions(+), 18 deletions(-)
```

(Updated: tests/test_tools_framework.py gained 2 R110-261a
explanatory comments and the score-asserts were corrected to the
post-fix per-file pass/fail math. The findings-side assertions
(B1/B2/B3/B4 still emitted) are unchanged.)

## Refs

- R110-261 (the coverage-sprint that revealed the bugs)
- R110-260 (the gate-fix that made this whole sprint possible)
- R110-78 (R110-261a's body-claim-verification pattern)
- R110-258 (body-claim-correction pattern)
- R110-246 (--timeout=300)
- R110-255 (Check 17 timeout tuning)
