# R110-175 — pre-push-validator Check 17 timeout fix (MAS-side)

## Problem

pre-push-validator Check 17 (pytest-run) times out at the current
spec-script's internal cap (180s) + the framework's 200s cap + the
spec runs pytest twice (sequential + xdist) when 1544+ tests are
in the suite. Even 420s outer timeout (R110-69 precedent) is not
enough; needs ~560s for the double-run.

Hit: 2026-08-17 R110-173 push (48813e1) — validator crashed at
Check 17 step 3 (sequential pytest-run in progress when 180s
spec-script cap fired). Same on retry with 420s outer.

Hermes-side workaround (since 2026-08-17 R110-173): run pytest
manually outside the validator, document results in commit body.
That works but is fragile (validator gives false-negative on
Check 17 every push).

## Goal

Fix mas-side: pre-push-validator Check 17 spec should:
1. Detect test-count and choose pytest-flavor accordingly:
   - <= 800 tests: run sequential + xdist -n 4
   - > 800 tests: run only xdist -n 4 (skip sequential,
     single-run is enough for pre-push gate)
2. Increase the spec-script's internal cap from 180s to 600s
   for the > 800 branch
3. Document the test-count threshold (800) in the spec
   so future test-growth is automatic

## Files (to be modified, mas-side)

- `recipe/sub/sub_mas-pre-push-validator.yaml`:
  - Add test-count detection at Check 17 start
  - Branch on threshold
  - Update timeout caps
- `tools/dev_pre_push_validator.py` (if it exists):
  - Same fix at the tool-level (the recipe may be a wrapper)
- `tests/test_sub_mas_pre_push_validator.py`:
  - Add tests for the new branching logic
  - Verify cap values

## Verification (post-fix)

- `goose run --recipe recipe/sub/sub_mas-pre-push-validator.yaml --no-session`
  on HEAD = R110-175: should reach Check 18+ (not stuck at 17)
- Outer wall-clock: <= 360s for the full validator run
  (Check 17 single xdist -n 4 at 1544 tests = ~260s, plus
  17 prior checks = ~100s, total ~360s)
- `pytest tests/ -n 4` still passes 1528/16/0
- pre-push-gate Step 5 (sub_recipe_ref): unchanged, 114/77/0/100.0%

## Out of scope (for R110-175)

- No code change in mas-engineer/src/
- No recipe renames
- No test additions (the recipe itself changes, but the test-suite
  is unchanged in size)
- No changes to the 17 other pre-push-validator checks (only
  Check 17 is broken)

## Status

CLOSED 2026-09-15. Check 17 was completely re-architected by subsequent sprints (R110-403, R110-414, R110-413) with much more robust timeout strategy than the 800-threshold branching originally proposed. Current spec: OUTER_TIMEOUT=1800s (30min), --timeout=600 per-test. Real-time validation: full sweep 7776 PASSED in 730.51s (well under 1800s cap).

Evidence: recipe/instructions/sub_mas-pre-push-validator.md L880 (OUTER_TIMEOUT=1800), L887 (--timeout=600). R110-414 commit bumped 1500→1800. Full sweep evidence: 7776 passed in 730.51s = 41% of cap.

Sibling fixes: R110-403 (outer 720→1500), R110-414 (1500→1800), R110-413 (subprocess.run cap), R110-171 (xdist flake-retry)
