# R110-361 EVIDENCE — im_finder_scan coverage-push r1 verified

**Date:** 2026-09-06
**Commit:** 8a824ce (🔧 R110-361)
**Branch:** mas-t-tests
**Status:** ✅ PASS — 0 test-failures, 0 fixes needed

## Summary

R110-361 added 24 NEW tests in
`mas-engineer/tests/test_r110361_im_finder_scan_coverage_push_r1.py`
across 4 under-tested pure-helper regions of
`tools/dev_im_finder_scan.py`.

Real coverage delta:
- Standalone (R110-361 alone): **22%** (152/682 stmts)
- Combined with r110347 + r110323: **27%** (184/682 stmts, +5pp delta)

## Pre-flight checks (all PASS)

| Check | Result |
|-------|--------|
| Secret scan (staged) | OK 0 secrets |
| SOT-audit (REPO-ROOT) | OK 0 violations |
| Body-claim-verification | OK 24 tests, 2 files, numbers match |
| Pre-commit-hook | OK PASS |
| Whitespace (`diff --check`) | OK no trailing whitespace |

## E2E (real-flow, 4 scenarios)

### 1. New test file alone — PASS

```bash
$ python3 -m pytest tests/test_r110361_im_finder_scan_coverage_push_r1.py \
    -p no:cacheprovider --no-header -q
........................                                                 [100%]
24 passed in 0.15s
```

### 2. Coverage on dev_im_finder_scan (R110-361 alone) — 22%

```bash
$ python3 -m pytest tests/test_r110361_im_finder_scan_coverage_push_r1.py \
    -p no:cacheprovider --no-header -q \
    --cov=tools --cov-report=term 2>&1 | grep dev_im_finder_scan
tools/dev_im_finder_scan.py             682    530    22%
```

### 3. Coverage combined with r110347 + r110323 — 27% (+5pp delta)

```bash
$ python3 -m pytest tests/test_r110361_im_finder_scan_coverage_push_r1.py \
    tests/test_r110347_im_finder_scan_coverage_push_r2.py \
    tests/test_r110323_im_finder_scan_bug_fixes.py \
    -p no:cacheprovider --no-header -q \
    --cov=tools --cov-report=term 2>&1 | grep dev_im_finder_scan
tools/dev_im_finder_scan.py             682    498    27%
```

### 4. Coverage with dedup subprocess test — 27%

Dedup's tiny synthetic scope doesn't exercise enough new lines to add coverage.

```bash
$ python3 -m pytest tests/test_r110361_im_finder_scan_coverage_push_r1.py \
    tests/test_r110347_im_finder_scan_coverage_push_r2.py \
    tests/test_r110323_im_finder_scan_bug_fixes.py \
    tests/test_dev_im_finder_scan_dedup.py \
    -p no:cacheprovider --no-header -q \
    --cov=tools --cov-report=term 2>&1 | grep dev_im_finder_scan
tools/dev_im_finder_scan.py             682    498    27%
67 passed in 5.87s
```

## Test coverage matrix (24 tests)

| Test class | Tests | Function | Lines covered |
|------------|-------|----------|---------------|
| TestCollectScopeDirs | 6 | `_collect_scope_dirs()` | L109-129 (env fallback, single, comma-split, whitespace-strip, empty-skip, dedup) |
| TestIsPathExcluded | 5 | `_is_path_excluded()` | L160-168 (external-recipe, .bak, -ORIGINAL.yaml, normal, opt-in) |
| TestAddFinding | 8 | `add_finding()` | L195-252 (severity-filter, append, id-increment, required-keys, json-serializable, line-args, no-db, filter-no-id) |
| TestComputeHelpers | 5 | `compute_issue_hash` + `compute_structural_pattern` | L89-104 (stability, type-discriminator, kwargs-ignored) |

## Import pattern (R110-322 + R110-347)

The `ifs` fixture sets up a sandbox before importing:
```python
monkeypatch.chdir(tmp_path)
monkeypatch.setenv("SCAN_SCOPE", str(tmp_path / "no-such-dir"))
monkeypatch.setenv("SEVERITY_FILTER", "...")
monkeypatch.setenv("MAS_INCLUDE_EXTERNAL_RECIPES", "")
importlib.import_module("tools.dev_im_finder_scan")  # canonical dotted name
```

This makes the module-level `check_spec_drift(findings, '.')` at L1578
a no-op (0.04s instead of 15s+ timeout). The canonical
`tools.dev_im_finder_scan` name matches the `.coveragerc [paths]
source = tools/` rewrite rule, so `--cov=tools` tracks it.

## Honest assessment (per directive + R110-323 inventory)

The R110-323 inventory listed 1660 stmts @ 30% baseline. Actual measurement:
- 1660 was an over-estimate (raw lines, not `coverage` executable-stmts)
- 682 executable stmts (coverage measurement)
- 22% with R110-361 alone, 27% with combined existing tests
- **Real delta: +5pp** (vs the +20pp target in the directive)

To reach 50%+ coverage, the pre-existing 75 errors in
`test_dev_im_finder_scan_lib.py` need to be fixed (R110-362) — they
exercise a different import path that already imports the canonical
`tools.dev_im_finder_scan` name and covers more code paths.

## Files

| File | Status | Lines | Purpose |
|------|--------|-------|---------|
| `mas-engineer/tests/test_r110361_im_finder_scan_coverage_push_r1.py` | NEW | 308 | 24 tests |
| `mas-engineer/.mase/directives/R110-361-im-finder-scan-coverage-push.md` | NEW | 108 | Directive (force-added) |

## Pre-push-gate summary

| Step | Result |
|------|--------|
| 0. Secret scan (staged) | OK 0 secrets |
| 1. SOT-audit (REPO-ROOT) | OK 0 violations |
| 2. pytest (24 tests) | OK 24/24 in 0.15s |
| 3. body-claim-verification | OK (24 tests, 2 files, numbers match) |
| 4. commit msg (🔧 R-format) | OK per protocol (em-dash, R-num) |
| 5. push | OK 8a824ce on origin/mas-t-tests |
| 6. post-flight audit | OK 0 broken, 0 references missing |

## Refs

- R110-322 (subprocess-cov fix, import pattern model)
- R110-347 (monkeypatch-env-import pattern, R110-361 model)
- R110-360 (SOT-cleanup predecessor)
- R110-323 (im_finder_scan Prio-3 inventory, baseline 30%)
- Skills: mas-engineer-coverage-push-workflow, pre-push-body-claim-verification
- **New learning:** use `--cov=tools` (package) not `--cov=tools/dev_im_finder_scan`
  (dotted-name) to avoid the "module was never imported" coverage warning

## Forward-pointer: R110-362

Pre-existing-test-fix-3-source-lockstep:
- 75 errors in `test_dev_im_finder_scan_lib.py`
- ~16 errors in `test_r110309_im_finder_scan_lib.py`
- Root cause: `importlib.util.spec_from_file_location` triggers the
  module-level `check_spec_drift(findings, '.')` side-effect with no
  SCAN_SCOPE sandbox, causing 15s+ timeouts on the real repo.
- Fix: patch the fixture to set SCAN_SCOPE/chdir BEFORE the import.
- Expected coverage boost: 27% → 50%+
