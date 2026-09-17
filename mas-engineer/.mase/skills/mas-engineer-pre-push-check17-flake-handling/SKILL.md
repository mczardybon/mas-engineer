---
name: mas-engineer-pre-push-check17-flake-handling
description: How to handle pre-push validator Check 17 (pytest-run) flake from `test_dev_phoenix_recovery_publish.py` and other long-running tests (3-5min). Trigger when a pre-push-validator run shows 1-2 test failures in long-running tests, but pytest directly passes — typically R110-279-style: kill the validator too early (60s) instead of waiting 3-5min. Also covers: how to identify "structural flake" (the test was always slow) vs "real regression" (your commit broke it).
category: devops
---

# Pre-Push Check 17 Flake Handling (MAS-Engineer)

## The problem (R110-279, 2026-08-28)

The goose pre-push-validator runs Check 17 = full pytest sweep. Some tests
take **3-5 minutes** to complete:

- `test_dev_phoenix_recovery_publish.py` (9 tests, ~296s = 4:56)
- `test_dev_im_finder_scan_lib.py` (~224s = 3:44)
- Any test that exercises real LLM calls, real subprocess, real network

If the validator's outer `timeout 120` or `timeout 180` fires BEFORE these
tests finish, the test appears as "failed" in `.state/pipeline/pre_push_validation.yaml`,
but the test is actually STILL RUNNING. You then think your commit broke
the test and waste 30+ minutes debugging phantom failures.

## Trigger

A pre-push-validator run shows:
- 1 or 2 test failures in a long-running test file
- The same test passes when run directly with `pytest`
- The validator log shows the test is still running when timeout fired
- No code in your commit touches the long-running test or its dependencies

## The 3-step flake-handling protocol

### Step 1: Confirm the test PASSES directly

```bash
cd <repo>
# run the allegedly-failing test directly with the same timeout the validator would use
python3 -m pytest tests/test_dev_phoenix_recovery_publish.py -v
# expected: all 9 pass in ~5 minutes
```

If the test passes directly, the validator's failure is a flake. Do NOT
debug your code.

### Step 2: Verify it's "structural" slow (not your commit)

```bash
# Reproduce the flake on the parent commit (without your changes)
git stash push -m "test-r110279-flake-debug"
git checkout HEAD~1
python3 -m pytest tests/test_dev_phoenix_recovery_publish.py -v
# if it ALSO takes 4-5min and passes: structural slow, not your commit
git checkout -
git stash pop
```

### Step 3: Deselect from Check 17, document, push

There are 3 valid ways to handle a structural flake:

**Option A (recommended for known-flake, R110-279-style): deselect in the
validator config**

```bash
# Find the validator's pytest invocation in:
#   mas-engineer/recipe/sub/sub_mas-pre-push-validator.yaml
# Add --deselect to the pytest command for the specific long-running test:
pytest_args:
  - --deselect=tests/test_dev_phoenix_recovery_publish.py
  # OR per-test:
  - --deselect=tests/test_dev_phoenix_recovery_publish.py::test_publish_step_4
```

Document in commit message: "Check 17 deselected `test_dev_phoenix_recovery_publish.py`
(structural 5min runtime, verified passing 9/9 directly in 296s, R110-279)."

**Option B: bump the validator's outer timeout**

The validator's `timeout_secs: 200` cap (see `pre-push-gate` §"Pitfall —
validator internal 200s cap") can be too tight. Bump to `420` for tests
that genuinely need 5-7min.

**Option C: accept the flake, document, push anyway**

If the validator is non-blocking (warning, not error) and the test passes
on direct run, push and add a follow-up commit to either deselect or
optimize the slow test.

## PHOENIX_RECOVERY specifically (R110-279 lesson)

**`test_dev_phoenix_recovery_publish.py` is intentionally slow** (~5min).
The test exercises a real recovery scenario: simulated crash, multi-step
restart, real LLM call to recover, full validation. **Do not** try to
"speed it up" — the slowness IS the test.

When this test "fails" in Check 17:
- 99% of the time: the validator killed the test at 60-90s before it could finish
- Real fix: `git checkout HEAD~1 && pytest` confirms the test takes 5min
- Real action: deselect from Check 17 (Option A)

## Decision tree

```
Pre-push Check 17 fails on test_X
│
├─ Does test_X pass with `pytest test_X.py` directly?
│   ├─ NO → Real failure. Debug. (Not a flake.)
│   └─ YES → Continue ↓
│
├─ Does test_X take >60s to run?
│   ├─ NO → Suspicious. Check validator timeout config.
│   └─ YES → Probably structural slow. Continue ↓
│
├─ Does `git checkout HEAD~1 && pytest test_X.py` ALSO take >60s and pass?
│   ├─ NO → Your commit caused the slowness. Debug.
│   └─ YES → PRE-EXISTING STRUCTURAL SLOW. Deselect from Check 17.
│
└─ Is test_X in a known-flake list (R110-279)?
    ├─ YES → Use Option A (deselect) directly.
    └─ NO → Use Option B (bump timeout) or Option C (accept + follow-up).
```

## Pitfalls

1. **Don't blame your commit first**: R110-279 agent spent 30min debugging
   `dev_im_finder_scan.py` before realizing the failure was a known flake
   in `test_check_1_5_origin_cleanup_recent_commits_match`. Always reproduce
   on parent commit FIRST.

2. **Don't disable the test entirely**: structural slow ≠ broken. The test
   still provides value. Deselect from Check 17, but keep the test
   running in CI / direct runs.

3. **Don't increase timeout blindly**: if 420s isn't enough, the test is
   probably hanging on a real bug. Investigate.

4. **Document the deselection**: every deselect must have a reason in the
   commit message + a reference to the R-number that diagnosed the flake.
   Otherwise the next agent will re-add it and hit the same issue.

## Verification step

After deselecting, run the validator again:
```bash
cd <repo>
timeout 420 goose run --recipe recipe/sub/sub_mas-pre-push-validator.yaml --no-session
# expected: all checks pass, including Check 17 with the deselected test
```

## Reference

- R110-69 (2026-08-03): pre-push-validator 200s cap, bump to 420
- R110-279 (2026-08-28): phoenix_recovery 3-5min lesson, deselect pattern
