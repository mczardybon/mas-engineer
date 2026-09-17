# R110-347 Evidence — im_finder_scan coverage-push round 2

## 1. Why

R110-323+ coverage-push queue, round 2.  Round 1 (R110-345)
delivered +2pp (25%→27%) by targeting the highest-value
pure helpers.  Round 2 targets the SD-test detector
helpers that have multiple untested branches.

## 2. R110-347 (2e5dc05) — Round 2: SD-test detector branches

### 2.1 Strategy
The SD-test detector (added in R110-78) is the heart of
the drift-detection feature.  It has multiple helpers with
4-5 branches each, many of which r110309 covered only one
branch for.  Round 2 systematically tests every branch.

### 2.2 5 helpers targeted, 29 tests, 5 test classes

**TestIsRuntimeVarAssert (12 tests)** — covers all 4 paths
in `_is_runtime_var_assert` (L921-938).  This function
decides whether `assert "LITERAL" in <rhs>` is testing
runtime output (capsys, file content, function return)
versus static source.  Branches:

  - method-call RHS: `capsys.readouterr().out`, `result.stdout`
  - subscript RHS: `rules["key"]`, `data["key"]`
  - plain-var RHS: `out`, `captured`, `intake`
  - method-call chain: `result.stdout.split()`
  - non-runtime var (negative case)
  - no assert pattern (negative case)
  - assert against static var (negative case)

All 12 PASS.

**TestIsInCodeBlock (4 tests)** — covers all branches in
`_is_in_code_block` (L1170-1177), which detects whether
a line is inside a fenced markdown code block (3-backtick
markers).  Branches:

  - inside (odd ``` count)
  - outside (no markers)
  - after 2 markers (even count)
  - after 3 markers (odd count)

All 4 PASS.

**TestIsInTableOrExample (4 tests)** — covers all 4 branches
in `_is_in_table_or_example` (L1180-1187), which detects
markdown tables and example blocks (heuristic for ignoring
test literals in documentation examples).  Branches:

  - next line starts with '|'
  - prev line starts with '|'
  - next line contains 'Example'
  - all false (regular prose)

All 4 PASS.

**TestIsSelfReference (6 tests)** — covers all branches
in `_is_self_reference` (L945-961), which detects whether
an assert is checking a literal against itself (e.g.
`assert "test_foo" in "test_foo"`).  Branches:

  - literal == rhs single-quoted
  - literal == rhs double-quoted
  - literal != rhs (negative case)
  - no `in` clause (negative case)
  - rhs with trailing comma (stripped before compare)
  - literal == rhs unquoted — returns False (function only
    recognizes quoted rhs; this documents actual behavior,
    not a bug)

All 6 PASS.

**TestIsInDocstring (3 tests)** — covers both branches in
`_is_in_docstring` (L984-988), which detects whether a
line is inside a docstring (triple-double-quote markers).

  - inside (odd """ count)
  - outside (no markers)
  - after 2 markers (even count)

All 3 PASS.

### 2.3 Result

| Metric | Before R1 | After R1 | After R2 |
|---|---|---|---|
| Lines covered | 169 / 682 | 187 / 682 | 193 / 682 |
| Coverage % | 25% | 27% | 28% |
| Tests (combined) | 19 | 28 | 57 |
| Tests runtime | n/a | 0.44s | 0.69s |

### 2.4 Honest assessment

Round 2 is +1pp combined (r110347 alone is +5pp, but it
overlaps with r110309 coverage of the same function
headers — we exercised the *branches* but most new lines
were already in the partially-covered function body).

The big missing blocks (L255-607, L644-735, L749-840,
L1211-1368, L1405-1486, L1633-1681) remain at 0% covered.
These are scan-loop code that requires actual repo walks.

Round 3 strategy: target the file-handling + scan-loop
helpers (open() with errors='ignore', dict-keyed finding
construction, severity filter, etc.) which are smaller
functions with more testable branches.

## 3. Cross-batch regression

```
$ python3 -m pytest tests/test_r110309_im_finder_scan_lib.py \
                    tests/test_r110345_im_finder_scan_coverage_push.py \
                    tests/test_r110347_im_finder_scan_coverage_push_r2.py \
                    --cov=dev_im_finder_scan --cov-report=term
57 passed in 0.69s
```

- 19 prior R110-309 tests: still PASS
- 9 R110-345 tests: still PASS
- 29 R110-347 tests: all PASS
- Coverage report: 28% (was 25%)

## 4. Body-claim-drift audit (R110-305 protocol)

All claims verified:
  - "29 new tests" → 29 test_ methods: ✓
  - "5 test classes" → 5 Test* classes: ✓
  - "+1pp (27%→28%)" → coverage report: ✓
  - "57/57 PASS" → pytest output: ✓
  - "0.69s combined" → pytest output: ✓
  - "Round 1: 9 tests, 3 helpers" → matches strategy: ✓
  - "R110-322 SNAFU-fix" → commit message + body: ✓
  - "round 2 honest assessment +1pp" → matches: ✓

## 5. R110-323+ queue status

Prio-1 (im_finder_scan, 1660 lines): Rounds 1+2 done
  - 25% → 28% (+3pp, 24 lines newly covered)
  - Round 3: file-handling + scan-loop helpers (target +3-5pp)
  - Round 4: check_spec_drift branches (target +2-4pp)
  - Total expected: 28% → ~38% (+10pp cumulative)

Prio-2 (workspace, 1445 lines): queued
Prio-3 (template_gen, 901 lines): queued
Prio-4 (dashboard, 566 lines): queued

## 6. References

- R110-322 (f4f8b3a) — coverage pattern documentation
- R110-323 — coverage-push queue
- R110-333 (f14be8c) — Prio-2/3/4 R-sprint plan
- R110-344 (a07fe2c) — R110-322 SNAFU-fix
- R110-345 (388bdc6) — coverage-push round 1
- R110-346 (35386ad) — round 1 EVIDENCE
- R110-347 (2e5dc05) — coverage-push round 2 (this commit's pair)
- R110-296/297 — 5-category commit protocol
- R110-78 — verification-theater guard
- R110-281 — force-push-VERSBOT
- R110-92 — drift detector
- R110-305 — 4-round numstat body-claim audit
- R110-258 — .mase/ + logs/ .gitignored + force-add pattern
- R110-318 — R-code → R-evidence pair pattern
