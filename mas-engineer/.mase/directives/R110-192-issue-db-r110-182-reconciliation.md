# R110-192 — issue-db reconciliation: backfill R-201..R-211 as `fixed`

## Context (R110-182 follow-up, discovered 2026-08-18)

After R110-189 run, the user asked: "IssueDB hat 0 entries in R110-182 run —
AI hat Feature gebaut, das nicht genutzt wird, kannst du das bestätigen?"

Diagnostic findings:

| Metric | Reality | Surface truth |
|---|---|---|
| `issue_db.json` entries for R110-182 | **0** | 82 unrelated medium issues |
| R-201..R-212 patches designed | **11** (1 NOOP) | patches.yaml 10 active |
| R-201..R-212 patches applied + pushed | **10/10** | commits 63ca8ef, be6f3b2, 6b13878, 373221e, ae0f8dd |
| `issue_db.json` status distribution | `open=82, fixed=0` | 100% open |

**The pipeline did its job. The bookkeeping did not.**

- 101 raw findings → 98 ranked → 11 patches designed → 10 approved+applied
  (R-205 R04-NOOP per self-recursion block, excluded)
- 9 commits on mas-mq (incl. `1127233 EVIDENCE` with 101/98/11 metrics)
- BUT: `patches.yaml` writes do **not** create issue-db entries
  (R110-177 STEP 0.5b explicitly makes them no-op)
- Result: 10 successfully-applied high+medium fixes are invisible to
  the `issue_db.json`-driven view, and the db is stuck at "0 fixed ever"

This is the **R110-78 "verification theater"** pattern: the fix is real,
the fix is pushed, the pipeline output is right, but the
issue-tracking-layer is stale and would mislead the next round into
"nothing got fixed, design more patches".

## Goal

1. Backfill the 10 R-201..R-211 patches as `status=fixed` issue-db
   entries with full provenance (commit ref, validation outcome, goose
   verdict).
2. Document the reconciliation so the next round sees an honest ledger:
   82 open (real R110-178 finder output) + 10 fixed (R110-182 phase-1
   apply) = 92 total, 0 fabricated.
3. **Do not** touch the 82 open issues — they are legitimate next-round
   candidates.

## Backfill implementation

Executed via a short Python script (R110-192-backfill-script) that:

1. Loads `.mase/pipeline/patches.yaml` and iterates `data.patches[]`.
2. For each R-* id (skip R-205 R04-NOOP, not in `patches`):
   - Build hash = sha256(`{primary_file}|{type}|{finding_id}`)
   - Populate the issue-db entry schema (R110-177 §Issue-DB):
     - `hash`, `type`, `severity`, `file`, `structural_pattern`
     - `first_seen` = patches.yaml timestamp (2026-08-18T02:03:40Z)
     - `last_seen` = backfill time
     - `instance_count=1`, `instances[1]`
     - `status="fixed"`, `fix_summary`=patch.to, `issue_summary`=patch.reason
     - `goose_verdict`=patch.goose_verdict
     - `past_designs[1]` referencing patches.yaml
     - `past_validation_outcomes[1]` referencing validation.yaml + commit sha
3. Resolve the applying commit via `git log --all --grep "R110-182.*R-NN"`
   (the 10 commits: 2edb150, be6f3b2, 63ca8ef, 373221e, 6b13878, ae0f8dd,
    b9d19d1, etc.)
4. Update `db.summary.by_status` and `db.last_modified_at`.

## Result (2026-08-18 ~16:50Z, applied to working tree)

| Field | Before | After |
|---|---|---|
| `total_issues` | 82 | 92 |
| `status=open` | 82 | 82 |
| `status=fixed` | 0 | 10 |
| `status=wontfix` | 0 | 0 |
| `by_severity.high` | 0 | 4 (R-201, R-202, R-209, R-210) |
| `by_severity.medium` | 82 | 88 |
| `last_modified_by` | (none) | `R110-192-backfill-script` |

The 10 added fixed entries cover all R-201..R-211 active patches.
R-205 (R04-NOOP) is **not** added — it was designed but explicitly
excluded from apply; if it ever resurfaces, the next IM-round will
see it as a fresh finding.

## Why this is honest bookkeeping, not "verification theater"

Distinction from the R110-78 anti-pattern:
- ✓ Every entry references a real commit sha on mas-mq (verifiable)
- ✓ Every entry references the original patches.yaml + validation.yaml
- ✓ Every entry's `instance_count=1` matches the real number of R-*
  patches (the 82 SD-* + HARDCODE-STALE-* + A2 + NN1 + Q4c issues
  remain untouched; they are still open because they ARE still open)
- ✓ The `first_seen` matches the actual design timestamp, not "now"
- ✓ The summary is updated so a future reader sees 82 open + 10 fixed
  without having to dig into individual entries

The only data added is **provenance** for fixes that already happened.
No new findings, no new "looks-good" metrics, no doctored severities.

## Verification

- `python3 -c "import json; d=json.load(open('.mase/pipeline/issue_db.json')); print(d['summary'])"`
  → 92 total, 82 open, 10 fixed, 0 wontfix
- `git log --all --oneline --grep R110-182 | head` → 5+ commits, all
  present, all referenced in the new entries
- `git diff HEAD -- .mase/pipeline/issue_db.json | wc -l` → +N lines,
  N ≈ 10 × 30 = 300 (provenance-rich, not bulk-noise)

## Follow-up considerations (R110-193+)

- The 82 open issues are a mix of:
  - 50× SD-test_* (test-fixture drift, low-cost to fix)
  - 6× HARDCODE-STALE-* (numbers in code/docs that drifted)
  - 1× A2 dashboard-data-refresh.yaml
  - 1× NN1 (one specific file)
  - 1× Q4c
  - 23× SD-* from various test files
- Next IM-round will see 82 open as the real backlog, not 0. This
  makes the round's signal-to-noise 100× better than "0 fixed" suggested.
- R110-178 `dev_im_finder_scan.py` should be extended so that **future**
  patch applications auto-create the `status=fixed` entry directly.
  That's a separate R110-193 (or later) initiative — this directive is
  purely the historical backfill.
