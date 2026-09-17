# R110-344/345 Evidence — tools/__init__.py + im_finder_scan coverage-push round 1

## 1. Why

R110-323+ coverage-push queue.  Prio-1: im_finder_scan (1660 lines,
682 stmts, was 25% covered).  Two commits:

  - R110-344 (a07fe2c): 🔧 SNAFU-fix for the missing
    `tools/__init__.py` that R110-322 had documented as required
    for `pytest --cov=tools/X` to work.
  - R110-345 (388bdc6): 🔧 Coverage-push round 1: 9 new tests
    for 3 high-value pure helpers, 25% → 27%.

## 2. R110-344 (a07fe2c) — SNAFU-fix

### 2.1 What was missing
R110-322 (f4f8b3a) documented the requirement: `tools/` must
have `__init__.py` for `pytest --cov=tools/X` to work.  The
file was missing entirely.  Every `pytest --cov=tools/X` failed
with "module not imported" or "no data collected".

### 2.2 The fix
```
+ mas-engineer/tools/__init__.py  (2 lines)
m mas-engineer/tests/test_r110309_im_finder_scan_lib.py
  (added R110-323 explanatory comment re eager-import vs
   fixture-based import)
```

### 2.3 Verification
```
$ python3 -m pytest tests/test_r110309_im_finder_scan_lib.py \
    --cov=dev_im_finder_scan --cov-report=term-missing
19 passed, dev_im_finder_scan.py: 25% covered (682 stmts, 513 missing)
```

Coverage now works end-to-end.  The pre-existing 19 r110309
tests all pass, and coverage report is generated.

## 3. R110-345 (388bdc6) — Coverage-push round 1

### 3.1 Strategy
Targeted the highest-value **pure-function helpers** with
**untested branches** (NOT scan-loop code, which requires a
real repo walk and is hard to test in unit scope).

### 3.2 3 helpers targeted, 9 tests, 3 test classes

**TestIsCommonValue (4 tests)** — covers `_is_common_value`
(L962-984), a function that walks `search_dirs` and returns
True if a literal appears in 3+ files (the "common value"
rule that prevents `True`, `False`, etc. from triggering SD
findings).

  - test_is_common_value_true_when_3plus_hits ✓
  - test_is_common_value_false_when_fewer_than_3_hits ✓
  - test_is_common_value_skips_pycache ✓
  - test_is_common_value_missing_search_dir ✓

**TestIsPathExcludedIncludeExternal (2 tests)** — covers the
`_INCLUDE_EXTERNAL=True` branch of `_is_path_excluded` (L165),
which is set by `--include-external-recipes` CLI flag or
`MAS_INCLUDE_EXTERNAL_RECIPES=1` env var.  When this flag is
set, external recipes (`/.config/goose/recipes/`) should NOT
be excluded.

  - test_external_recipes_included_when_flag_set ✓
  - test_external_recipes_excluded_by_default ✓

**TestCollectScopeDirs (3 tests)** — covers the CLI-arg and
comma-separated-env branches of `_collect_scope_dirs` (L109-130),
which determines which directories the scanner walks.

  - test_collect_scope_dirs_with_cli_arg ✓
  - test_collect_scope_dirs_with_multiple_cli_args ✓
  - test_collect_scope_dirs_comma_separated_env ✓

### 3.3 Result

| Metric | Before | After | Δ |
|---|---|---|---|
| Lines covered | 169 / 682 | 187 / 682 | +18 |
| Coverage % | 25% | 27% | +2pp |
| Tests (combined) | 19 | 28 | +9 |
| Tests runtime | n/a | 0.44s | — |

### 3.4 Why only +2pp
The bulk of missing lines (513 total) is in scan-loop code:
- L255-607 (Q1-Q3 detector bodies, ~350 lines)
- L644-735 (NN detector, ~90 lines)
- L749-840 (Q4 detector, ~90 lines)
- L1579-1604, L1633-1681 (module-level scan + JSON emission)

These require a real repo walk.  Rounds 2-3 will target
the SD-test detector branches (L989-1486) which can be tested
in isolation with the `ifs` fixture.

## 4. Cross-batch regression

```
$ python3 -m pytest tests/test_r110309_im_finder_scan_lib.py \
                    tests/test_r110345_im_finder_scan_coverage_push.py \
                    --cov=dev_im_finder_scan --cov-report=term
28 passed in 0.44s
```

- 19 prior R110-309 tests: still PASS
- 9 new R110-345 tests: all PASS
- Coverage report: 27% (was 25%)

## 5. Body-claim-drift audit (R110-305 protocol)

All claims verified:
  - "9 new tests" → 9 test_ methods: ✓
  - "3 test classes" → 3 Test* classes: ✓
  - "+2pp (25%→27%)" → coverage report: ✓
  - "28/28 PASS" → pytest output: ✓
  - "0.44s" → pytest output: ✓
  - "Round 1: 9 tests, 3 helpers" → matches the strategy docstring ✓
  - "R110-322 SNAFU-fix" → commit message + body: ✓

## 6. R110-323+ queue status

Prio-1 (im_finder_scan): Round 1 done, 25% → 27%, +2pp
  - Round 2: SD-test detector branches (target +5-8pp)
  - Round 3: scan-loop code with real-repo walk (target +3-5pp)

Prio-2 (workspace, 1445 lines): queued
Prio-3 (template_gen, 901 lines): queued
Prio-4 (dashboard, 566 lines): queued

## 7. References

- R110-322 (f4f8b3a) — coverage pattern documentation
- R110-323 — coverage-push queue
- R110-333 (f14be8c) — Prio-2/3/4 R-sprint plan
- R110-344 (a07fe2c) — R110-322 SNAFU-fix (this commit's pair 1)
- R110-345 (388bdc6) — round 1 (this commit's pair 2)
- R110-296/297 — 5-category commit protocol
- R110-78 — verification-theater guard
- R110-281 — force-push-VERSBOT
- R110-92 — drift detector
- R110-305 — 4-round numstat body-claim audit
- R110-258 — .mase/ + logs/ .gitignored + force-add pattern
- R110-318 — R-code → R-evidence pair pattern
