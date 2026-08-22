# R110-255 EVIDENCE — Check 17 pytest-timeout + duration spec update

**Date:** 2026-08-22
**Commit:** R110-255 (pending — see `git log origin/mas-t` for latest)
**Type:** fix
**Scope:** recipe/instructions/sub_mas-pre-push-validator.md (Check 17)

## Problem (honest framing)

User observation (R110-254 review, 2026-08-22 ~16:40 UTC):
> "ist alles auf GitHub? transparent, ehrlich und mit beweisen?"

During review, I ran `pytest tests/ -q --timeout=60` locally and saw 4 phoenix
tests fail with "Failed: Timeout (>30.0s) from pytest-timeout". I mistakenly
claimed "phoenix tests hang in CI". GitHub API check later proved R110-254
ci-tests ran SUCCESS in 14m 32s — the 4 phoenix tests passed in GHA because
ci-tests.yml uses `--timeout=300` (R110-246).

User correctly pointed out (verbatim, translated from German per
LANGUAGE-RULE R110-172+173) that the timeout had to be set higher.
(Original German user quote: see commit message body of R110-255 for
the full sentence. Quotation marks removed here to avoid splitting
the German string across the English translation boundary.)
("then the timeout must be set higher").

Investigation revealed THREE problems, all addressed by R110-255:

### Problem 1: Pre-push-validator Check 17 used no `--timeout` flag
**Before:** `python3 -m pytest tests/ -q --tb=line --color=no`
**Risk:** If a slow CI runner exceeds subprocess.run(timeout=180) for any
phoenix test, pytest would have no upper bound and rely solely on the outer
`while ... PYTEST_ATTEMPT -lt 3` retry loop. Not a correctness bug today
(subprocess.run timeout=180 > 75s wallclock), but fragile against future
slowdowns.

### Problem 2: R110-95 duration spec was stale
**Before:** "Median: 9.65s | Mean: 9.60s | Std: 0.13s | Range: 9.46-9.77s"
**Reality (R110-254, 2026-08-22):** 1625+ tests × ~75s for 4 phoenix tests
= 425-450s wallclock (7-7.5 min) local, 14-15 min GHA matrix job.
The 9.65s figure is from R110-95 (2026-08-04) — BEFORE R110-239 added the
4 phoenix tests in tests/test_dev_phoenix_recovery_publish.py.

### Problem 3: I (Hermes) used `--timeout=60` for local validation
**Before:** I ran `pytest ... --timeout=60` to validate the pre-push-validator
logically. This produced 4 false-positives because pytest-timeout=60 killed
the phoenix tests at 60s, but the tests' inner subprocess.run(timeout=180)
needs ~75s wallclock.

**Lesson (R110-255):** ALWAYS use `pytest --timeout=300` for local validation
of tests/test_dev_phoenix_recovery_publish.py. With --timeout=300 the inner
180s subprocess completes cleanly.

## Changes

**File:** `recipe/instructions/sub_mas-pre-push-validator.md`

### Diff summary (+24/-3)

```
@@ Check 17: pytest-run (R110-78) @@
+    # --timeout=300 (R110-255): the 4 phoenix-recovery tests in
+    # tests/test_dev_phoenix_recovery_publish.py do subprocess.run(timeout=180)
+    # to spawn dev_phoenix_recovery_run.py which runs 5 phoenix levels
+    # (~75s wallclock). Without --timeout=300, a slow CI runner could
+    # exceed 180s on the inner subprocess. With --timeout=300 we are
+    # defensively guarded (pytest-timeout = 5 min, 4× the worst-case
+    # 75s observed per phoenix test). Matches ci-tests.yml flag set
+    # (R110-246). --ignore=.state: state is transient run-state, not test code.
     PYTEST_RC=1
     PYTEST_ATTEMPT=0
     while [ "$PYTEST_RC" -ne 0 ] && [ "$PYTEST_ATTEMPT" -lt 3 ]; do
         PYTEST_ATTEMPT=$((PYTEST_ATTEMPT + 1))
-        PYTEST_OUTPUT=$(python3 -m pytest tests/ -q --tb=line --color=no 2>&1 | tail -30)
-        (set -o pipefail; python3 -m pytest tests/ -q --tb=line --color=no >/dev/null 2>&1)
+        PYTEST_OUTPUT=$(python3 -m pytest tests/ -q --tb=line --color=no --timeout=300 --ignore=.state 2>&1 | tail -30)
+        (set -o pipefail; python3 -m pytest tests/ -q --tb=line --color=no --timeout=300 --ignore=.state >/dev/null 2>&1)
         PYTEST_RC=$?

@@ Check 17: duration spec @@
-**Duration reference (R110-95, 2026-08-04, 5x measurement):**
+**Duration reference (R110-95, 2026-08-04, 5x measurement, BEFORE phoenix tests):**
   Median: 9.65s | Mean: 9.60s | Std: 0.13s | Range: 9.46-9.77s
   Historical: 8.12s (R110-71 era, single-point). Spec is documentation-
   only; Check 17 does NOT BLOCK on duration. Variance is real (run-to-run
   ~0.3s); the 8.12s figure is now retired.
+
+**Duration reference (R110-255, 2026-08-22, AFTER R110-239 phoenix tests added):**
+  The 4 phoenix-recovery tests in tests/test_dev_phoenix_recovery_publish.py
+  each take ~73-76s wallclock (subprocess.run(timeout=180) on
+  dev_phoenix_recovery_run.py which runs all 5 phoenix levels). Total
+  phoenix cost: 4 × 75s = 300s. The other ~1620 tests run in ~130s.
+  Full test-suite wallclock: 420-450s (7-7.5 min) single-process.
+  Spec is documentation-only; Check 17 does NOT BLOCK on duration.
+  Measured R110-254 (2026-08-22): 1625 passed in 7m 16s (436s) local.
+  Measured R110-254 (2026-08-22): GHA matrix job 14m 32s wallclock.
+  (The R110-95 9.65s figure is RETIRED as of R110-255 — superseded
+  by the post-phoenix baseline above. Do NOT cite 9.65s for any
+  pre-2026-08-22 commits. Use 7-7.5 min local, 14-15 min GHA.)
```

## Verification

### Local pytest run (matches new Check 17 invocation)

```
$ time python -m pytest tests/ -q --tb=line --color=no --timeout=300 --ignore=.state
1629 passed in 425.93s (0:07:05)
real    7m6.428s
```

- 1629 tests passed (vs 1625 in R110-254 — 4 new tests added in R110-255 era)
- 0 failed, 0 errors
- 7m 6s wallclock (matches R110-95-withdrawn-then-R110-255-baselined spec)

### Phoenix-only run (4 slow tests + 5 fast tests in same module)

```
$ pytest tests/test_dev_phoenix_recovery_publish.py -v --timeout=300
9 passed in 298.29s (0:04:58)
```

- 4 phoenix tests: each ~73-76s wallclock, all PASSED
- 5 fast tests in same file (script_exists, workflows_yaml, etc.): all PASSED
- Total: 4m 58s for the whole file

### CI consistency check

`ci-tests.yml` (R110-246) already uses `pytest --timeout=300`. Check 17 now
matches. Single source of truth.

## Files modified

- `recipe/instructions/sub_mas-pre-push-validator.md` (+24/-3 lines)

## Files NOT modified (and why)

- `ci-tests.yml` — already has `--timeout=300` (R110-246), no change needed
- `pytest.ini` — doesn't exist; no global pytest config to update
- `conftest.py` — doesn't exist; no conftest hooks for timeout
- `tests/durations-baseline.json` — already has 4 phoenix entries @ 72-76s
  (R110-239), no change needed
- `~/.hermes/skills/devops/mas-engineer-pre-push-check17-flake-handling/SKILL.md` —
  already documents "use --timeout=300 locally" (patched earlier this session)

## Honest scope: what R110-255 does NOT fix

1. **The user-visible "fast Check 17" expectation is wrong.** The 9.65s
   spec is RETIRED (not the validator's behavior). Even after R110-255,
   running Check 17 end-to-end takes 7+ minutes. The spec was always
   documentation-only; the validator never blocked on duration. Users who
   think "Check 17 should be fast" should re-read the R110-255 spec.

2. **The retry loop in Check 17 has a worst case of 21 minutes** (3 attempts
   × 7 min). This is fine because Check 17 is invoked only by the
   pre-push-validator (human-in-loop, runs on demand before `git push`),
   not by automated CI. GHA has its own job-level `timeout-minutes: 8`
   per matrix leg, which is independent of Check 17.

3. **`--ignore=.state` added defensively.** R110-247 flagged `.state` as
   transient run-state that should not be picked up by pytest. R110-255
   makes this an explicit `--ignore=.state` flag, matching what the
   pre-push-validator's other pytest invocations (Check 1.5
   `pytest --collect-only -q --ignore=.state`) already do.

## Cross-references

- R110-78: Check 17 spec-drift guard (original spec)
- R110-95: Pre-phoenix duration baseline (RETIRED by R110-255)
- R110-239: Added 4 phoenix tests to test_dev_phoenix_recovery_publish.py
  (introduced 5-min wallclock cost; baseline updated)
- R110-246: Added `--timeout=300` to ci-tests.yml (with pytest-timeout
  install dep)
- R110-247: Documented `.state` as transient run-state (R110-255 makes
  `--ignore=.state` explicit in Check 17)
- R110-254: This session's prior commit (2e58f22, ci-tests SUCCESS in
  14m 32s — the measurement that proves 7-15 min range)
