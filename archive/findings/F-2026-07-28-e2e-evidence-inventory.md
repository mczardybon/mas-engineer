Finding: e2e-evidence-gen2/ inventory + 1241db8 log-claim mismatch

DATE: 2026-07-28
SCOPE: e2e-evidence-gen2/ (91 files, 3.5MB)

INVENTORY RESULTS

30 R-evidence files: R44-R74 (continuous), R89
Gaps: R75-R88 (14 missing — was passierte da?)
2 e2e-test-reports: E2E-TEST-REPORT-gen2.md, E2E-TEST-REPORT-gen2-R41.md
14 post-flight-audit files: R48-R57, R74, R89 (91-505 bytes each)
43 .log files: e2e-runs, prepush-runs, full_improvement-runs, fix_specific-runs
1 yaml-validation: validation_author_fixes-R51.yaml
2 bug-reports: author-schema-mismatch, test-fix-failures-bug

1241db8 COMMIT-MESSAGE CLAIM vs REALITY

Claim (in 1241db8 commit message):
  "30 logs, 9-15 KB each, 347 KB total"

Reality (in e2e-evidence-gen2/*.log):
  43 .log files (not 30)
  Range: 174 bytes - 280,866 bytes
  Median: 66,340 bytes (not 9-15 KB)
  0 of 43 logs in the 9-15 KB range
  Total: 3,329,706 bytes = 3,175 KB (not 347 KB)

PATTERN

The 1241db8 message "30 logs × 11.5 KB ≈ 347 KB" was:
- Under-counted: real number is 43 (43% more)
- Wrong size range: median 6× the claimed 11.5 KB
- Coincidentally-close total: 347 KB target, real 3.2 MB
  → 347 KB might be a partial subset OR a fabricated figure

This matches the verification-theater pattern from R101 / 602648a
(2026-07-23). Commit-message overclaim hiding actual evidence quality.

IMPLICATIONS

- 1241db8's evidence is real (43 logs exist, R40-R89 documented)
  BUT commit message numbers were wrong
- The "30 logs 9-15 KB each" was probably a pre-fix eyeball
  estimate or aspirational target, not actual data
- Real e2e-runs are 50-300 KB (full_improvement), tiny utility runs
  are <1 KB. Two distinct log classes mixed together.
- Author-bug (R41, 19/96 broken) → fixed by R51 (validation_author_fixes.yaml)
- R75-R88 gap suggests IM-Pipeline had a multi-run period with
  batched evidence (not individual R-evidence files)

NEXT STEPS

1. Update F-2026-07-28-1241db8-verification-theater.md with concrete
   log-count data (43 ≠ 30)
2. Run actual e2e: tools/e2e_run_all.py --no-interactive (DONE 2026-07-28: 202/202 PASS in 24.2s)
3. If user wants TEST 5 (real goose+LLM run): need goose install + DEEPSEEK_API_KEY

See also:
- F-2026-07-28-1241db8-verification-theater.md (parent finding)
- e2e-results/2026-07-28-run-2/raw-results.json (this session's run)
- e2e-evidence-gen2/E2E-TEST-REPORT-gen2.md (R40-R41 baseline)
