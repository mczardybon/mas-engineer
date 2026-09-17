# R110-361 — im_finder_scan coverage-push (Prio-3, queue position 2)

**Date:** 2026-09-06
**Author:** Hermes-MAS-Engineer <Hermes@mas-engineer.local>
**Sprint:** R110 (continuous)
**Predecessor:** R110-360 (SOT-cleanup, 28→0)

## Goal

Push coverage on `tools/dev_im_finder_scan.py` from ~30% to ~50%
(additive +20pp on 1681 stmts).

## Current State (baseline measured 2026-09-06)

- File: `tools/dev_im_finder_scan.py` (1681 stmts, 1660 in R110-323 inventory)
- Existing tests: 8 test files, 94 tests total
  - `test_dev_im_finder_scan_dedup.py` (3 tests)
  - `test_dev_im_finder_scan_lib.py` (29 tests, **75 ERRORS** — pre-existing)
  - `test_r110309_im_finder_scan_lib.py` (~16 tests, errors)
  - `test_r110323_im_finder_scan_bug_fixes.py` (~10 tests)
  - `test_r110345_im_finder_scan_coverage_push.py` (~14 tests)
  - `test_r110347_im_finder_scan_coverage_push_r2.py` (29 tests, OK)
  - `test_r110349_im_finder_scan_coverage_push_r3.py` (~25 tests, OK)
  - `test_sub_mas_im_finder.py` (~15 tests, OK)
- Module import side-effect: `check_spec_drift(findings, '.')` runs at L1578
  - With `SCAN_SCOPE=/tmp/nonexistent` + sandboxed CWD, import takes 0.04s
  - Without sandbox, import takes 15s+ and times out (root cause of 75 errors)
- Coverage measured on the 8 OK test files: ~30% on the 1681 stmts

## Pre-Existing Test Errors (75 in test_dev_im_finder_scan_lib.py)

The fixture `mod()` uses `importlib.util.spec_from_file_location` which
runs the module's import side-effect (the L1578 `check_spec_drift` call)
WITHOUT setting `SCAN_SCOPE` first. The scan on the real repo
(`'.'` = `/workspace/dev-branch/mas-engineer-cleanup/mas-engineer/`)
is too slow (>15s) and the test times out.

R110-361 strategy: write NEW tests using the R110-347 monkeypatch-env
pattern (NOT fix the 75 pre-existing errors — that's a separate
"3-source lockstep" R-sprint).

## Targets for R110-361 (Prio-3 round 1)

The following functions are still at low coverage despite 8 prior test
files. They are the "low-hanging" targets because they're pure functions
(no I/O, no `sys.exit`, no network) and have well-defined branches:

1. **add_finding (L195-235)** — central function, every finding goes through it
   - Branches: severity filter (filter by SEVERITY_FILTER), finding_id increment,
     finding_dict mutation, JSON-serializable check
   - Target: 5-8 tests covering all severity levels + filter

2. **_collect_scope_dirs (L109-159)** — env + recipe-based scope detection
   - Branches: SCAN_SCOPE env set/not set, multi-dir, dedup, fallback
   - Already partially covered by r110349. Target: 2-3 additional edge cases.

3. **compute_issue_hash / compute_structural_pattern (L89-107)** — pure helpers
   - Branches: empty input, special chars, length boundaries
   - Target: 4-5 tests

4. **_is_path_excluded (L160-194)** — path-filter logic
   - Branches: SCOPE_PREFIXES, SUB_RECIPE_SKIP, etc.
   - Target: 4-6 tests

5. **check_spec_drift / check_spec_drift_reverse (L989, L1191)** — main detectors
   - Many branches not covered (the import-side-effect issue means the existing
     tests can't easily exercise these without sandboxing)
   - Target: 8-12 tests using sandboxed tmp dirs

6. **check_hardcode_stale / check_stale_literal (L1390, L1500)** — string-match detectors
   - Target: 5-8 tests using real-looking but stale literals

## Implementation Plan

1. Write `mas-engineer/tests/test_r110361_im_finder_scan_coverage_push_r1.py`
   - 30-40 tests across the 6 target functions
   - Use `monkeypatch.setenv("SCAN_SCOPE", str(tmp_path))` + `monkeypatch.chdir(tmp_path)`
     so the import side-effect is a no-op (0.04s, not 15s timeout)
   - Use `tmp_path` for all file system interactions
   - Use `capsys` / `caplog` for stdout / stderr assertions
2. Run pytest on the new file only
3. Run pytest on the FULL im_finder test set with `--cov=tools/dev_im_finder_scan`
4. Verify coverage went from 30% to ~50% (+20pp)
5. Commit per mas-engineer-commit-protocol

## Constraints

- **DO NOT touch the pre-existing 75 test errors** — they're a separate R-sprint
- **DO NOT use `monkeypatch.chdir` alone** — must combine with `SCAN_SCOPE` env
- **DO NOT use `importlib.util.spec_from_file_location` without env-sandboxing**
  — that's the cause of the pre-existing errors
- Use `subprocess.run + cwd=tmp_path + env=SCAN_SCOPE` (R110-322 pattern) for tests
  that need the full main() path

## Expected Output

- 30-40 new tests, all PASS
- Coverage: 30% → 50% (+20pp on 1681 stmts)
- Net stmts covered: ~340 additional
- Per-file delta: `tools/dev_im_finder_scan.py  1681  840  50%` (was 30%)

## Refs

- R110-359 (template_gen 68→94% — pattern reference)
- R110-322 (subprocess-cov fix)
- R110-347 (monkeypatch-env-import pattern, this round's model)
- Skills: mas-engineer-coverage-push-workflow, pre-push-gate,
  pre-push-body-claim-verification
