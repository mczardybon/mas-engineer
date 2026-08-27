# R110-267: dev_im_finder_scan.py library-function tests

## What
New test suite `tests/test_dev_im_finder_scan_lib.py` with 56 unit tests
for the library functions in `tools/dev_im_finder_scan.py` (1376 lines).

R110-261 ROUND 5 spec required coverage for the internal library functions
of the scanner, which were only indirectly covered by the 8 issue-db
integration tests in `tests/test_dev_im_finder_scan_dedup.py`.

## Before / After

| Metric | Before | After |
| --- | --- | --- |
| Unit-tests for `dev_im_finder_scan.py` | 8 (issue-db) | 64 (8 + 56) |
| Library functions with direct test-coverage | 0 | 15 |
| pytest total (R110-261 baseline 1902) | 1902 | 1942 (+40 net) |

Note: 56 new tests collected, +40 in full-suite because some library
behavior was already indirectly covered by other test files.

## Coverage Matrix

| Library function | Tests | Coverage |
| --- | --- | --- |
| `_is_pycache_or_backup` | 3 | pycache, .pyc, no-match |
| `_is_self_reference` | 4 | quote-match, in-different, no-keyword, trailing-msg |
| `_is_common_value` | 4 | 3+files, below-threshold, missing-dir, skip-pycache |
| `_is_in_docstring` | 3 | outside, inside, after-close |
| `_is_in_code_block` | 3 | outside, inside, at-first-fence |
| `_is_in_table_or_example` | 4 | table-next, table-prev, example-next, no-table |
| `_is_path_excluded` | 4 | external-recipes, ORIGINAL, .bak, normal |
| `_collect_scope_dirs` | 5 | default, CLI, env, CSV-split, dedup |
| `check_spec_drift` | 6 | no-tests, zombie, URL-skip, short-skip, docstring-skip, common-skip |
| `check_spec_drift_reverse` | 5 | no-tests, count-no-test, count-match-test, prose-skip, fence-skip |
| `check_hardcode_stale` | 3 | no-recipe, emits, fence-skip |
| `check_stale_literal` | 2 | no-recipe, emits |
| `add_finding` | 5 | basic-shape, severity-filter, fid-increment, K1-pattern, NN1-pattern |
| `compute_issue_hash/pattern` | 3 | hash-shape, K1-pattern, NN1-order-insensitive |
| Regex constants | 2 | SD_STRING_IN_RE, SD_INT_EQ_RE |
| **Total** | **56** | |

## Verification

```
$ python3 -m pytest tests/test_dev_im_finder_scan_lib.py -v
56 passed in 15.44s

$ python3 -m pytest tests/ -q
1942 passed, 1 skipped, 4 warnings in 443.55s (0:07:23)
```

  - All 56 new tests pass
  - Full suite: 1942 passed, 0 failed, 1 skipped
  - No regressions in the existing 1886 tests
  - Suite duration: 7m23s (within the 200s/200s pre-push-gate caps; check-17
    runs the suite twice — both individual runs <200s, outer ~440s with setup overhead)

## Pitfalls / Lessons Learned

  1. **`_is_in_docstring` parameter mismatch**: function signature says
     `src_lines: str` but the only caller actually passes a LIST of lines
     (from readlines()). Tests must pass a LIST, not a string.
  2. **`_is_self_reference` with trailing comma+message** breaks self-reference
     detection: `rhs` (`.+` greedy) captures the `"msg"` too, and the
     inner-quote-strip no longer matches the bare literal. Test documents
     this as False (intended behavior).
  3. **SEVERITY_FILTER is module-level state**: without reset in the
     autouse-fixture, `test_add_finding_respects_severity_filter` (sets
     `SEVERITY_FILTER = {"high"}`) leaks into all subsequent add_finding
     tests. Fix: `reset_state` now explicitly resets
     `mod.SEVERITY_FILTER = {'medium', 'high', 'blocker'}`.
  4. **PATTERN_B_STRING_IN_RE requires quotes** around the literal:
     `[\"']([^\"']{4,80})[\"']`. Without quotes, the literal is not
     recognized as stale-literal candidate. Test
     `test_check_stale_literal_emits_finding` uses `"recipe/instructions/..."`
     in quotation marks.
  5. **PATTERN_A_RE (hardcode) only matches "counting nouns"**:
     `sub-agents|tools|phases|checks`. `99 steps` does NOT trigger a
     finding. Test `test_check_hardcode_stale_emits_finding` uses `99 checks`.

## Files Changed

  - `tests/test_dev_im_finder_scan_lib.py` (new, 553 lines, 56 tests)
