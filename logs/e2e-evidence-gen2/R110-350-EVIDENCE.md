# R110-349 Evidence — im_finder_scan coverage-push round 3 (FINAL PURE-HELPER ROUND)

## 1. Why

R110-323+ coverage-push queue, round 3.  Rounds 1+2 brought
coverage from 25% to 28% via 38 tests across 8 classes for
high-leverage pure helpers.  Round 3 targets the LAST
remaining pure-helper branches.

## 2. R110-349 (25c3ca4) — Round 3: last pure helpers

### 2.1 Strategy
Identify the very few remaining pure-helper branches that
r110309/345/347 left untested.  This is the last pure-helper
round; remaining missing code is scan-loop body that
requires integration tests with a real repo walk.

### 2.2 3 helpers targeted, 15 tests, 3 test classes

**TestCollectScopeDirsEnvBranch (6 tests)** — covers the
env-var + comma-split + de-dup branches in
`_collect_scope_dirs` (L109-130).  Branches:

  - env-only single dir
  - de-dup of same value in CLI and env (L126)
  - comma-split creates multiple entries (L124)
  - whitespace stripped from comma-separated entries (L125)
  - empty entries from leading/trailing commas skipped (L127)
  - fallback to ['recipe'] when no CLI and no env (L120)

All 6 PASS.

**TestAddFindingSeverityFilter (3 tests)** — covers the
severity-filter early-return branch in `add_finding` (L207-208).
This is a 2-line branch but it's a high-traffic path (every
finding with a filtered severity hits it).  Branches:

  - severity NOT in SEVERITY_FILTER → no finding appended
  - severity IN filter → finding appended (counter increments)
  - sequential calls get sequential finding_ids (F-NNN)

All 3 PASS.

**TestIsPycacheOrBackup (6 tests)** — covers all 3 branches
in `_is_pycache_or_backup` (L941-944).  Branches:

  - `__pycache__` in path → True
  - path ends with `.pyc` → True
  - `/llm-backup/` in path → True
  - `/llm-backup/` nested in path → True
  - regular path → False
  - `__pycache__` in middle of path → True

All 6 PASS.

### 2.3 Result

| Metric | R0 | R1 | R2 | R3 |
|---|---|---|---|---|
| Lines covered | 169 / 682 | 187 / 682 | 193 / 682 | 203 / 682 |
| Coverage % | 25% | 27% | 28% | 30% |
| Tests (combined) | 19 | 28 | 57 | 72 |
| Tests runtime | n/a | 0.44s | 0.69s | 0.39s |

### 2.4 Honest assessment

Round 3 is +2pp combined.  The 479 missing lines remaining
are overwhelmingly scan-loop body.  To meaningfully close
the gap on those would require either:
  (a) integration tests with a real testproject repo, OR
  (b) refactoring the scan loop to be more testable
      (extract walk → collect, scan → process).

Strategy decision: rather than continue to push for marginal
+1-2pp per round on pure helpers, PIVOT the next rounds to
Prio-2 (workspace, 1445 lines) which has more testable
surface per line.  Expected yield on workspace: 0% → 30%+
in 2 rounds.

## 3. Cross-batch regression

```
$ python3 -m pytest tests/test_r110309_im_finder_scan_lib.py \
                    tests/test_r110345_im_finder_scan_coverage_push.py \
                    tests/test_r110347_im_finder_scan_coverage_push_r2.py \
                    tests/test_r110349_im_finder_scan_coverage_push_r3.py \
                    --cov=dev_im_finder_scan --cov-report=term
72 passed in 0.39s
```

- 19 prior R110-309 tests: still PASS
- 9 R110-345 tests: still PASS
- 29 R110-347 tests: still PASS
- 15 R110-349 tests: all PASS
- Coverage report: 30% (was 25%)

## 4. Body-claim-drift audit (R110-305 protocol)

All claims verified:
  - "15 new tests" → 15 test_ methods: ✓
  - "3 test classes" → 3 Test* classes: ✓
  - "+2pp (28%→30%)" → coverage report: ✓
  - "72/72 PASS" → pytest output: ✓
  - "0.39s combined" → pytest output: ✓
  - "LAST pure-helper round" → remaining missing = scan-loop: ✓
  - "PIVOT to Prio-2 workspace" → strategy documented: ✓

## 5. R110-323+ queue status

Prio-1 (im_finder_scan, 1660 lines): Rounds 1+2+3 done
  - 25% → 30% (+5pp, 34 lines newly covered)
  - Pure-helper coverage is now near 100% (the remaining
    missing lines are scan-loop body)
  - PIVOT to Prio-2 (workspace) for next rounds

Prio-2 (workspace, 1445 lines): NEXT
  - Round 1 expected: 0% → 20%+ (10+ pure helpers)
  - Round 2 expected: 20% → 35%+ (file-handling + emit)
Prio-3 (template_gen, 901 lines): queued
Prio-4 (dashboard, 566 lines): queued

## 6. References

- R110-322 (f4f8b3a) — coverage pattern documentation
- R110-323 — coverage-push queue
- R110-333 (f14be8c) — Prio-2/3/4 R-sprint plan
- R110-344 (a07fe2c) — R110-322 SNAFU-fix
- R110-345 (388bdc6) — coverage-push round 1
- R110-346 (35386ad) — round 1 EVIDENCE
- R110-347 (2e5dc05) — coverage-push round 2
- R110-348 (776fac9) — round 2 EVIDENCE
- R110-349 (25c3ca4) — coverage-push round 3 (this commit's pair)
- R110-296/297 — 5-category commit protocol
- R110-78 — verification-theater guard
- R110-281 — force-push-VERSBOT
- R110-92 — drift detector
- R110-305 — 4-round numstat body-claim audit
- R110-258 — .mase/ + logs/ .gitignored + force-add pattern
- R110-318 — R-code → R-evidence pair pattern
