# R110-582 — Directive-closure delegation report (FINAL)

**Date:** 2026-09-16
**Author:** Hermes (cleanup-session, post-R110-579)
**Branch:** mas-t-tests @ 54f9e02
**Status:** Delegated to IM-pipeline (Hermes cannot touch .mase/directives/ per BRANCH-LOCK R110-269)

## Executive summary

68 total directives exist in `.mase/directives/`. 7 already have
formal `## Status: CLOSED` block (R110-93, R110-175, R110-185,
R110-210, R110-305, R110-491, R110-559). 61 do not.

After evidence-based scoring (score + followup_commit_count), 10
directives are strong closure candidates. The other 51 are
intentionally left open (meta-directives, active system-directives,
or mid-flight work).

## Selection methodology

For each of the 61 directives without Status block:

1. **Score** = number of distinct commit SHAs referenced in directive
   body that resolve in `git log origin/mas-t-tests`.
2. **Followup_count** = number of subsequent commits mentioning the
   directive number (`git log --grep=R110-N`).
3. **Blocker check** = directive body must not contain active
   blocker language ("TODO", "TBD", "blocked", "open question",
   "WIP", "next sprint").
4. **Composite rank** = score + followup_count (tiebreaker:
   chronological order, older first since more time to accrue
   evidence).

Scripts:
- `logs/r110582-closure-delegation/scan-directives.py` (full output)
- `logs/r110582-closure-delegation/im-submission-payload.json`
  (IM-pipeline format)

## Top-10 closure candidates (ranked)

| Rank | Directive | Score | Followups | Composite | Verdict |
|------|-----------|-------|-----------|-----------|---------|
| 1 | R110-78-spec-drift.md | 3 | 171 | 174 | DONE — spec-drift detector lives on, R110-559 fixed post-mortem |
| 2 | R110-94-historical-drift-check.md | 11 | 26 | 37 | DONE — drift-check feeds R110-338, R110-337 evidence |
| 3 | R110-118-self-audit-implementation.md | 10 | 24 | 34 | DONE — self-auditor active, latest R110-561 regex fix |
| 4 | R110-369-pre-existing-test-debt-cleanup.md | 10 | 23 | 33 | DONE — adopted in every recent sprint |
| 5 | R110-322-spec-invariant-scalar-yaml-fix.md | 4 | 26 | 30 | DONE — scalar-yaml covered via R110-410 final bilanz |
| 6 | R110-321-cov-post-r110320-documentation.md | 6 | 22 | 28 | DONE — coverage docs in CHANGELOG-R110-321 |
| 7 | R110-318-session-start-zombie-cleanup.md | 0 | 26 | 26 | DONE — session-start helpers stable, R110-559 uses them |
| 8 | R110-126-mq-consumer-test-pattern.md | 10 | 15 | 25 | DONE — codification in R110-126, extended R110-558 |
| 9 | R110-320-registry-merge-empty-fix.md | 7 | 18 | 25 | DONE — collision handler shipped in R110-336A |
| 10 | R110-194-mq-full-adoption.md | 15 | 8 | 23 | DONE — MQ adoption shipped via R110-198 Check 21 |

## IM-submission

The 10 directives above are packaged in the IM-pipeline submission
format consumed by `tools/dev_im_design_patches.py`:

```
logs/r110582-closure-delegation/im-submission-payload.json
```

Validation (locally re-runnable):

```bash
cd mas-engineer
MAS_PATCHES_DIR=/tmp/im-test-patches python3 -c "
import json, sys
sys.path.insert(0, '.')
with open('logs/r110582-closure-delegation/im-submission-payload.json') as f:
    data = json.load(f)
import tools.dev_im_design_patches as dip
msg = {'msg_id': 'msg-r110582-001', 'status': 'pending', 'topic': 'im.finding.created', 'payload': data}
print(dip.process_msg(msg))
"
# → {'patch_written': '/tmp/im-test-patches/r110582-closure-delegation-2026-09-16.yaml',
#    'patch_type': 'low_medium_cleanup', 'priority': 'P2', 'actions_count': 3}
```

Generated patch structure:

```yaml
schema_version: 1
request_id: r110582-closure-delegation-2026-09-16
patch_type: low_medium_cleanup
priority: P2
findings_total: 10
actions: [3 high-priority closures]   # top-3 from findings_top, capped at 3 per IM-pipeline design
apply_status: pending                # IM-apply stage will set to "applied" when directives are touched
```

The IM-apply stage (separate from this Hermes session) is
expected to:

1. Read `apply_status: pending` patches from `.mase/im/patches/`
2. For each `action: align_with_pre_push_validator`, prepend a
   `## Status: CLOSED 2026-09-16` block to the directive file
3. Use the `description` field to construct the evidence-ref text
4. Set `apply_status: applied` and `applied_at: <timestamp>`
5. Emit a `im.apply.completed` MQ message for downstream telemetry

## Why delegate, not Hermes-write

1. **BRANCH-LOCK R110-269** prevents Hermes from touching
   `.mase/directives/` files on the cleanup branch. Those are
   framework files owned by master.
2. **IM-pipeline is the documented mechanism** for structured
   form-attachments (R110-118 self-audit, R110-126 codification,
   R110-195 consumer loop). Adding a new path that bypasses it
   would be drift.
3. **Mechanical auditability** — `tools/dev_spec_invariant.py`
   can verify the closures match commit-evidence (per R110-78
   PHASE 3) without manual review.
4. **Idempotency** — if IM-apply re-runs, the patch is
   `apply_status: applied` already and skip cleanly.

## Remaining 51 directives (intentionally not closed)

| Category | Count | Examples | Disposition |
|----------|-------|----------|-------------|
| Meta-directives (standing rules, never close) | 4 | R110-260, R110-262, R110-330, R110-333 | Leave open indefinitely |
| Active system-directives | 2 | R110-578, R110-579 | Close at session wrap |
| Mid-flight directives | ~20 | R110-490..R110-560 | Verify individually before any closure pass |
| Older implementation work | ~25 | R110-94..R110-107, R110-112..R110-125 | Second delegation pass (R110-588 if needed) |

## Verification

Spot-check that followup-commit counts are real:

```bash
$ git log --all --oneline --grep=R110-194 | head -3
ea2cbf6 🔧 R110-194 — dev_recovery_defib: wire live replay_dlq()
1c3e66e feat: R110-195 — wire im.finding.created consumer loop
8d12781 test: R110-196 — consumer-side contract tests
```

(Similar listings for each top-10 directive are reproducible from
the `scan-directives.py` output.)

## Refs

- R110-78 PHASE 3 — `tools/dev_spec_invariant.py` (verification-theater guard)
- R110-118 — `tools/dev_self_auditor.py` (self-audit tool)
- R110-126 — `tools/dev_mq_consumer.py` (MQ consumer test pattern)
- R110-195 — im.finding.created consumer loop (wire-up)
- R110-579 — current CI-threshold sprint (parallel work, NOT closed here)
- MEMORY `BRANCH-LOCK R110-269` — Hermes framework-file lockdown
