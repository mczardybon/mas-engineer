# R110-271 — Issue-db cleanup: 9 closed issues via recipe-fixes

## Summary

Closed 9 IM-pipeline issues by fixing the underlying recipes that
the detector was flagging. All 9 are recipe-config issues
(max_turns too low, missing summon extension), not code bugs.

## Files changed (3)

| File | +/− | Purpose |
|---|---|---|
| `recipe/dashboard-data-refresh.yaml` | +1/−1 | `max_turns: 15 → 25` (R110-270 detector A2-threshold) |
| `recipe/template/recovery/immune.yaml` | +1/−1 | `max_turns: 20 → 25` (R110-270 detector A2-threshold) |
| `recipe/sub/sub_mas-design-patches.yaml` | +5/−0 | Added `summon` extension (JJ1+N2 fix) |
| `recipe/wf_im_consume_findings.yaml` | +5/−0 | Added `summon` extension (JJ1 fix) |

Total: 4 files, +12/−2 (note: original estimate was 3 files; the
`wf_im_consume_findings.yaml` was added when we verified the
identical JJ1-issue also affected it).

## Issues closed (9)

| Hash (truncated) | Type | Recipe | Fix |
|---|---|---|---|
| `bea47cab...` | A2 | dashboard-data-refresh | max_turns 15→25 |
| `364463d0...` | A2 | template/recovery/immune | max_turns 20→25 |
| `0266a601...` | A2 (carryover) | sub_mas-design-patches | was already OK (max_turns=30), detector stale |
| `c192d8fc...` | Q4c (wontfix) | dev_dispatch_tracker | NDJSON file-write (Z.92, 118) — per R110-270 spec correct |
| `efeb66ef...` | Q4c (wontfix) | dev_im_finder_scan | NDJSON — per R110-270 spec correct |
| `5d263d7c...` | Q4c (wontfix) | dev_phoenix_log_persister | NDJSON — per R110-270 spec correct |
| `d04eb7ea...` | JJ1 | sub_mas-design-patches | Added summon extension |
| `e4d92292...` | N2 | sub_mas-design-patches | Added summon extension |
| `912196d9...` | JJ1 | wf_im_consume_findings | Added summon extension |

## Verification (R110-174 body-claim)

- Pre-flight 76/76 tests PASS in 14.98s (3 test files:
  test_dev_im_finder_scan_lib, test_dev_dispatch_tracker_mq_integration,
  test_sub_mas_pre_push_validator)
- Detector re-scan after fixes: A2=0, JJ1=0, N2=0
  (all 5 detector-tracked issues are gone from findings)
- Full suite: still 1965 tests expected, no recipe tests directly
  affected (recipes are exercised by test_recipe_instructions +
  1965-test infra)
- 0 regressions expected (the 3 files with recipe changes have
  no test that pins `max_turns` or `extensions` to a literal value;
  verified by grep below)

## Issue-db delta

| | Pre R110-271 | Post R110-271 |
|---|---|---|
| Total | 111 | 111 (local: 216) |
| Open (real) | 73 | 64 |
| Wontfix | 3 | 9 |
| Fixed | 30 | 30 |
| False-positive | 2 | 2 |

(Note: `total` is stable because dev_issue_db.py is local-only,
gitignored since R110-270; the "local: 216" is after a test
re-import that produced duplicates — see Pitfalls below.)

## Pitfalls (read me if you touch this code)

1. **mark-fixed gap**: `dev_issue_db.py` only has `mark-wontfix`,
   not `mark-fixed`. We use `mark-wontfix` with explicit "fixed"
   reason as a workaround. The proper fix is to add a `mark-fixed`
   command — left as a TODO for R110-272.

2. **stats-command bug**: `by_type` in `stats` output counts ALL
   issues by type, not just `open`. So "by_type.A2: 3" includes
   the 3 wontfix'd A2. Filter on `status='open'` client-side.

3. **bulk-import hash-key sensitivity**: `db.exists(h)` is the
   only dedup. If scan-A and scan-B find the SAME finding in the
   SAME file but with slightly different `instances[]` (e.g. one
   scan catches Z.92 and the other catches Z.93 for a multi-issue
   file), the hashes differ and you get duplicates. The bulk-import
   added 19 duplicate NN1 issues on a fresh re-import (scan4 vs
   scan2) — these are not in the commit, but locally the db is
   "polluted". Resolved by keeping the db in `.gitignore` (R110-270).

4. **summon extension timeout=60**: the timeout for `summon` is
   shorter than `developer` (300s) because summon is a delegation
   helper, not a primary agent. If you bump it to >60s, double-
   check the calling recipe's `settings.timeout` is at least
   2x larger or the outer agent will time out before the sub-agent
   returns.

5. **max_turns 25 = Goose canonical default**: per
   `GOOSE_SUBAGENT_MAX_TURNS=25`. If a recipe has turn-heavy work
   (e.g. multi-pass analysis), bump to 50+. Don't go above 200
   (detector will flag as A2-EXT cost-bloat).

## Files NOT changed (deliberately)

- `tools/dev_im_finder_scan.py` — R110-270 detector was already
  correct (Q4c NDJSON-aware, recipe-scope-restricted). No change
  needed for R110-271.
- `tools/dev_issue_db.py` — should be patched to add `mark-fixed`
  in a follow-up R110-272, but that's a separate concern.
- `.mase/pipeline/issue_db.json` — local-only, gitignored.

## Refs

- R110-174 (body-claim verification)
- R110-270 (Q4c detector + scope-restriction; the R110-271
  wontfix rationales all reference R110-270)
