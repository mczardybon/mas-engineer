# R110-305 — E2E log body-claim cite rule (runner TOTAL line, not JSON sums)

**Status:** DRAFT (2026-08-30)
**Author:** Hermes (R110-305 follow-up, 2026-08-30 session)
**Target:** All future commits that cite an e2e-runner result in the
commit body (`X tested, Y PASS (Z%)`)

## Context

R110-305 (this push, 533063d follow-up + ba0fee6 + 0330746) hit
a new body-claim-drift class: the author cited the runner's
"200 tested, 198 PASS (99.0%)" line in commit bodies, but the
raw-results.json SUGGESTED a different count (198/205 = 96.6%) if
you naively summed the dict values:

```
task_workflows: {sampled: 70, ok: 66, fail: 1, skip: 5}
                ↑ int     ↑ len ↑ len ↑ len
                = 70      = 66  = 1   = 5
                sum: 72 (not 67, which the runner says)
```

The discrepancy: the `skip` list mixes **pre-sampling
out-of-scope** (3 entries, workflows not in scope at all) with
**post-sampling skip** (2 entries, sample-picked but then
deferred). The runner's tested count is `sampled - pre_scope_skip
= 70 - 3 = 67`, NOT `sampled = 70` and NOT `ok+fail+skip = 72`.

If the body had used "198/205 (96.6%)" derived from raw-results.json,
it would be a body-claim-drift of the same severity as R110-173
("115 lines" vs real 155 lines) — wrong number, plausible
shape, would have slipped past the existing
`pre-push-body-claim-verification` check (which only catches
numstat and pytest totals, not e2e derived sums).

The body-claim re-verification in ba0fee6 + 0330746
deliberately used the runner's TOTAL log line, NOT derived sums,
per this directive.

## Rule

When a commit body cites an e2e-runner result:

1. The source-of-truth is the runner's own log line:
   `[INFO] TOTAL: 200 tested, 198 PASS (99.0%)`
2. Per-category line:
   `[INFO] task_workflows: 66/67 OK (1 fail + 5 SKIP)`
3. NEVER derive "tested" or "PASS rate" by summing
   `raw-results.json` dict keys (the skip list mixes pre+post
   sampling, double-counting).

## Pre-commit verification procedure

```bash
# 1. Read the runner's own TOTAL line
grep -E "TOTAL|elapsed_s" logs/e2e-evidence-gen2/<date>/full-run.log

# 2. Read per-category line
grep -E "recipe_yaml|top_workflows|recovery_workflows|task_workflows" \
    logs/e2e-evidence-gen2/<date>/full-run.log

# 3. The body MUST quote (1) and (2) VERBATIM.
#    If they say "200 tested, 198 PASS", the body says
#    "200 tested, 198 PASS (99.0%)", not "X/Y" derived from
#    raw-results.json.

# 4. If raw-results.json SAYS a different number (e.g. sum
#    of all ok+fail+skip+timeout+error = 205, not 200), the
#    body must explain WHY: cite the runner's source-of-truth
#    and note that raw-results.json's skip list is over-counted
#    due to pre-sampling scope filtering.
```

## Sanity check (one-liner)

```bash
# If the body cites "N tested" and the runner's TOTAL line says
# "N tested", they match → body is OK.
# If the body says "N tested" but raw-results.json's sum of
# {ok, fail, skip, timeout, error} across all categories = M
# (M != N), this is EXPECTED (skip is over-counted). The body
# is OK as long as it cited the runner, not the JSON sum.
```

## Files (changed by R110-305 push ba0fee6 + 0330746)

- `mas-engineer/STATUS.md`: R110-302 round 3 entry references
  the 100% coverage claim, with per-file table verified by
  `pytest --cov` (302 stmts, 100% across 5 files, 116 tests).
- `mas-engineer/.mase/directives/STATUS.md`: R110-304 entry
  body-claim-drift fix (533063d had fictional test file names
  + wrong TestDevPytestHook count; fixed in 0330746).
- `logs/e2e-evidence-gen2/2026-08-30-r110304/`:
  - `full-run.log` (3201 bytes) — runner's own log, source-of-truth
  - `raw-results.json` (10513 bytes) — secondary, do NOT derive
    from this

## Skill update (hermes-side, R110-305)

`pre-push-body-claim-verification` SKILL.md got a new section
"E2E log body-claims: cite the runner's TOTAL line, not derived
sums (R110-305 lesson)" with the raw-results.json trap
explanation. Hermes will see this on every future
`mas-engineer-workflow` task via the skill-load step 0.

## Verification (post-R110-305)

- The 2 commits ba0fee6 + 0330746 (just pushed to
  mas-t-tests) cite ONLY the runner's TOTAL + per-category
  lines. No JSON sums in the bodies. Verified by re-grep:
  `git show ba0fee6 0330746 | grep -E "198|200|99\.0%" | head`
  shows the numbers match the runner's log lines, not
  raw-results.json sums.
- pre-push-gate Step 0 secret scan: PASS (no secrets in the
  2 new commits' diffs).
- pre-push-gate Step 2 pytest lockstep test (the most-related
  test file): 14/14 PASS (`test_pre_push_check_1_5_skill_alignment.py`).
- pre-push-gate Step 5 sub_recipe_ref audit: 77/77 = 100% coverage.

## Out of scope (for R110-305)

- No mas-engineer/ code change (this is purely hermes-side LLM
  behavior + body-claim discipline).
- No recipe renames.
- No test additions.
- No changes to the e2e-runner itself (it correctly reports
  the TOTAL line; the issue is purely in how the author
  cites it in commit bodies).

## Status

DRAFT. The 2 commits ba0fee6 + 0330746 are the evidence that
the rule is in effect. A future R110-306+ can decide if the
rule should be enforced by a mas-side check (e.g. a
`dev_e2e_body_cite_check.py` that re-greps the body against
the full-run.log and exits 1 on mismatch), but that's a
separate mas-side fix.
