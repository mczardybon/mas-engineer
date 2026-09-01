# R110-316 — recipe-exclude 3-source lockstep test

**Status**: planned
**Round**: R110-316
**Date**: 2026-09-01

## Bug

RECIPE_EXCLUDE (the 0-byte-fixture allowlist) lives in 2 places:

- A: `tests/test_unix_test_word.py::RECIPE_EXCLUDE` (pytest-side, R110-34 + R110-315)
- B: `tools/e2e_run_all.py::artifacts` (e2e-runner-side, R110-34)

These 2 sources can DRIFT independently:

- R110-315 added `sub_-.yaml` to RECIPE_EXCLUDE (pytest) but the e2e-runner
  artifacts list does NOT contain it. If `sub_-.yaml` is created during a
  pytest run AND e2e is invoked next, the runner doesn't clean it up; if
  pytest is invoked next, it tolerates it but the e2e cycle may see a
  "spurious" 0-byte file as part of its recipe-yaml scope.

This is a 3-source lockstep problem (validator/detector/test pattern from
R110-78, generalized here to A:RECIPE_EXCLUDE / B:e2e-artifacts / C:fs-reality).

## Fix

Add `test_check_1_5_recipe_exclude_3_source_lockstep` to
`tests/test_pre_push_check_1_5_skill_alignment.py`. The test reads all 3
sources and asserts:

1. Every 0-byte `recipe/sub/*.yaml` file MUST be in A (RECIPE_EXCLUDE) OR
   in B (e2e artifacts cleanup list) — otherwise e2e-theater
2. RECIPE_EXCLUDE entries that are not actually fixtures (file > 0 bytes
   OR doesn't exist) get a soft warning, not a hard fail
3. e2e artifacts entries that are not actually fixtures get a soft warning
4. Overlap (entries in BOTH A and B) is allowed and expected (defence
   in depth)

Also add `sub_-.yaml` to the e2e_run_all.py artifacts list (1 line) so
A and B agree on R110-315's new fixture.

## Files

- `tests/test_pre_push_check_1_5_skill_alignment.py` — add new test
  (~30 lines), import subprocess + glob at top
- `tools/e2e_run_all.py` — add `sub_-.yaml` to artifacts list (1 line)

## Pre-push gate

- Step 0 secret scan: OK
- Step 1 pytest targeted: new test PASS + all 10 existing 1.5 tests PASS
- Step 2 body claim: verify with pytest output before writing
- Step 3 R-format + numstats verified against `git diff --cached --numstat`

## Related

- R110-315: added sub_-.yaml to RECIPE_EXCLUDE (pytest only)
- R110-78 + R110-304: 3-source lockstep pattern (validator/detector/test)
- R110-314: detector/test regex alignment fix
- skill `mas-engineer-pre-existing-test-fix-3-source-lockstep` (this
  sprint's playbook)
