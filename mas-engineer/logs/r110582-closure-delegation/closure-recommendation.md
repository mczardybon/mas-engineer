# R110-582 — Directive-closure-sprint delegation report

**Date:** 2026-09-16
**Author:** Hermes (cleanup-session, post-R110-579)
**Target:** `.mase/directives/R*.md` (61 directives ohne `## Status`-section)
**Action recommended:** Delegate closure to IM-pipeline per mas-engineer
framework architecture (Hermes does not modify framework files directly).

## Background

68 total directives. 7 already have formal `## Status: CLOSED` block
(R110-93, R110-175, R110-185, R110-210, R110-305, R110-491, R110-559).
61 have no Status block.

The 61-without-Status are a maintenance debt: knowing what-is-open vs.
what-is-done requires reading every directive body. A formal Status
block at the top would make the IM-pipeline's triage easier.

## Selection criteria

For closure, a directive needs:
1. Commit evidence (directive body references commit SHAs and they
   resolve to `git log` output)
2. Subsequent follow-up commits mentioning the directive number
   (showing the work was adopted / extended / wrapped-up)
3. No active blocker language ("TODO", "TBD", "blocked", "open
   question") in the directive body

Scanned all 61 directives via two static-analysis scripts:
- `logs/r110582-closure-delegation/scan-directives.py`
- Manual spot-checks of the top-15 by score

## Top-10 closure candidates (strongly recommended)

| # | Directive | SHA-evidence | Follow-up commits | Verdict |
|---|-----------|--------------|-------------------|---------|
| 1 | R110-194-mq-full-adoption.md | 9 SHAs | 8 git-commits | DONE — wires shipped in ea2cbf6 / 1c3e66e / b478afe / 256517b |
| 2 | R110-192-issue-db-r110-182-reconciliation.md | 13 SHAs, body says "100%" | 3 git-commits | DONE — issue-db reconciled per mas-engineer post-mortem |
| 3 | R110-118-self-audit-implementation.md | 10 SHAs | 24 git-commits | DONE — self-audit lives on, latest R110-561 fixed regex |
| 4 | R110-116-commit-hygiene-b00dade-corrections.md | 15 SHAs | 11 git-commits | DONE — co-built with R110-126 MQ-consumer test |
| 5 | R110-109-self-audit-spec-invariant.md | 7 SHAs | 11 git-commits | DONE — feeds into R110-253, R110-78 PHASE 3 |
| 6 | R110-108-sd-detector-integration.md | 6 SHAs | 3 git-commits | DONE — closed via R110-110 ("R110-78 PHASE 2 done") |
| 7 | R110-369-pre-existing-test-debt-cleanup.md | 6 SHAs | 23 git-commits | DONE — adopted continuously, latest R110-559 |
| 8 | R110-306-ci-red-pre-existing-fixes.md | 11 SHAs | 5 git-commits | DONE — included in 5-directive-closure batch |
| 9 | R110-223-wf-yaml-clone-sideeffect.md | 5 SHAs | 4 git-commits | DONE — closed via R110-232 "cycle fix" |
| 10 | R110-191-im-finder-findings-top-key-mismatch.md | 3 SHAs, "shipped" | (inherited) | DONE — IM-finder stable since R110-189 |

## Recommended action for IM-pipeline

For each of the 10 above, prepend a `## Status\n\nCLOSED 2026-09-16` block
following the format already established by R110-93/175/185/210/305/491/559:

```markdown
## Status

CLOSED 2026-09-16 (this delegation batch). [Evidence: R110-NNN was
implemented in commit(s) AAA, extended in commit(s) BBB, latest touch
in commit(s) CCC. Subsequent sprints (R110-MMM) have consumed the work
and verified no regression.]
```

**Why delegate, not Hermes-write:**
1. BRANCH-LOCK R110-269 prevents Hermes from touching `.mase/directives/`
   on `cleanup` branch (those are framework files on master).
2. IM-pipeline already has pattern-recognition for this kind of structured
   form-attachment (R110-118 self-audit, R110-126 codification).
3. Closure-evidence pattern (commit-shas + grep-history) is mechanically
   auditable by `tools/dev_spec_invariant.py` per R110-78 PHASE 3.

## Remaining 51 directives

Most of the remaining 51 are covered by:
- Older implementation work (R110-94..107) — closeable via the same
  delegation-pattern, but lower-priority.
- Recurring-templates (R110-260 / R110-262 / R110-330 / R110-333) — these
  are META-directives, not implementation-directives; they should NOT
  be "CLOSED" because they are standing rules.
- Active-system-directives (R110-578 / R110-579 — open in this session).

A second delegation pass (R110-588 if needed) can batch-close the older
ones after these 10 land cleanly.

## Verification of evidence

For each of the 10 above, the follow-up-commits listed are real
`git log` results on `origin/mas-t-tests` (where these refs exist):

```
$ git log --all --oneline --grep=R110-194
ea2cbf6 🔧 R110-194 — dev_recovery_defib: wire live replay_dlq()
1c3e66e feat: R110-195 — wire im.finding.created consumer loop
8d12781 test: R110-196 — consumer-side contract tests
b478afe feat: R110-197 — dashboard mq_block observability surface
256517b feat: R110-198 — pre-push Check 21 (MQ topic caller-chain audit)
b7b8495 chore: R110-214 — A1+A2+A3 cleanup
bb36cd0 📝 R110-193 — archive e2e evidence logs
```

(Similar listings for each row in the table above are in
`scan-directives.py` output.)

## Out of scope (intentionally NOT closed)

- R110-578 / R110-579 — ACTIVE in this session, leave for session-end wrap.
- R110-260 / R110-262 / R110-330 / R110-333 — meta-directives (recurring
  rules), should NEVER carry CLOSED status.
- R110-490..560 — most are mid-flight per dispatch tracker (verify each
  before any closure pass).

## Refs

- R110-78 PHASE 3 — `tools/dev_spec_invariant.py` (verification-theater)
- R110-118 — `tools/dev_self_auditor.py` (self-audit tool)
- R110-579 — current CI-threshold sprint (parallel work)
- MEMORY `BRANCH-LOCK R110-269`
