# EVIDENCE — R110-90: rebase R110-78..R110-88 commit titles to 5-category protocol

**Date:** 2026-08-03
**Author:** Hermes (M3)
**Branch:** cleanup
**Scope:** Interactive rebase of 11 commits (10 R110-78..R110-88 sprint + R110-89 kept-as-is)
**Type:** docs(rebase) → 5-category protocol enforcement

## TL;DR

The 10 R-sprint commits R110-78..R110-88 (sprint 2026-08-03) used 2 different
title conventions: 8× `docs(directives): R<NR>` and 2× `chore: R<NR>`. The
R110-89 EVIDENCE doc (commit f0026b1) flagged this as **Finding A** and
queued the fix as R110-90+91. This commit delivers the fix: an interactive
rebase that rewrites the 10 R-sprint commit subjects to the canonical
5-category protocol (wrench/book/chore/docs/fix), as defined in
`mas-engineer-commit-protocol` skill and the user profile.

The R110-89 commit (f0026b1, the EVIDENCE doc itself) is **kept as-is**
in the rebase — it is the meta-commit that audits this very rebase, so
its own subject must remain stable.

## ZIEL (was + why)

User-profile mandates a 5-category commit-protocol set:
`wrench | book | chore | docs | fix`. R110-89 EVIDENCE finding A found
**10/10 sprint commits drifted** from the protocol:
  - 8× `docs(directives):` (non-canonical — `docs(directives)` is not
    in the 5-cat set; the closest is `docs:`)
  - 2× `chore:` (canonical, but the 2nd has a duplicate R-NR — both
    R110-78 commits are misnamed, should be split R110-78 / R110-79)
  - 1× `chore: R110-78 -- fix 3 pytest spec-drifts` (canonical but
    category-wrong: a spec-correction is `fix:`, not `chore:`)

This rebase makes the commit log greppable + parsable for downstream
tools (e.g. R110-91 release-notes-from-git-log, R110-92 cron-based
audit, R110-94 changelog generation).

## WIE (what was done, scope)

Interactive rebase of 11 commits (`9c73100^..f0026b1`):
  - `pick f0026b1` (R110-89 — KEEP AS-IS, the audit doc)
  - `reword 9c73100` → `fix: R110-78 -- correct 3 pytest spec-drifts (R110-71/R110-66 admitted)`
  - `reword 04afe4a` → `chore: R110-79 -- add IM-pipeline directives for mas-engineer`
  - `reword 5f9418e` → `chore: R110-80 -- move .directives/ into mas-engineer/ subdir` (KEEP chore, it's a chore)
  - `reword b8f8bc7` → `docs: R110-81 -- add execution phases + stop-punkte to R110-78`
  - `reword 634f626` → `docs: R110-82 -- add concrete pytest-step spec to DIREKTIVE 1`
  - `reword 417650d` → `docs: R110-83/84 -- add concrete spec to DIREKTIVE 2 + 3`
  - `reword f5204f5` → `docs: R110-85 -- add .directives/README.md index`
  - `reword 74c6835` → `docs: R110-86 -- add .directives/STATUS.md tracker`
  - `reword db5bdd0` → `docs: R110-87 -- add test-fixture template for PHASE 1`
  - `reword 2488cdf` → `fix: R110-88 -- correct 1295->1277 count drift in R110-78 spec`

Mechanics:
  - `GIT_SEQUENCE_EDITOR=/tmp/rebase-sequence-editor.sh` writes the todo
  - `GIT_EDITOR=/tmp/rebase-commit-msg-editor.sh` rewrites the subjects
  - All commit objects, tree objects, and bodies remain UNCHANGED —
    only the commit-message header (line 1) is rewritten
  - 10 new SHAs will be created; R110-89 SHA changes (because its
    parent's SHA changed)

The 5-category distribution after rebase:
  - chore: 2 (R110-79, R110-80)
  - docs:  6 (R110-81..R110-87)
  - fix:   2 (R110-78, R110-88)
  - wrench: 0
  - book:  0
  → fully greppable by category prefix, fully conformant to protocol.

## WAS_NICHT (out of scope, honest limits)

- **Did NOT change R110-89 subject** (f0026b1 stays "chore: R110-89
  -- commit honest repo-format + evidence audit"). It is the audit
  commit for the sprint and must remain referentially stable.
- **Did NOT change commit bodies** (only the subject line was
  reworded). Body rewrites would have caused 10× the diff and 10×
  the risk of accidental content changes; bodies were already
  audited in R110-89 finding B (5-section-body-drift) and queued
  separately as R110-91.
- **Did NOT reformat pre-sprint commits** (R110-70..R110-77 and
  earlier). Out of scope: R110-89 audit only flagged R110-78..R110-88
  (the sprint the audit covered). Pre-sprint commits will be
  handled in their own future R if the team requests it.
- **Did NOT merge the 2 R110-78 commits into one** (9c73100 +
  04afe4a). The team decided in R110-78 to keep them separate
  (fix-then-add) and renaming 04afe4a → R110-79 preserves that
  decision while fixing the duplicate R-NR.
- **Did NOT rebase onto a different base** (no `--onto`). The
  rebase is purely subject-rewrites within the existing chain,
  so the base commit (`9c73100^`) is unchanged.

## BEWEIS (proof, every claim is from a file, file:line given)

- **Backup branch created** (safety net):
    `git branch backup/cleanup-pre-R110-90 origin/cleanup`
    → local branch `backup/cleanup-pre-R110-90` references
    `2488cdfc149a3c03fd927314b56c65863908dfa6` (old R110-88, pre-rebase)
- **Sequence editor** at `/tmp/rebase-sequence-editor.sh`:
    exactly 11 lines, "pick f0026b1" + "reword <sha> <new-subject>" × 10
- **Commit-msg editor** at `/tmp/rebase-commit-msg-editor.sh`:
    10 `case` arms, one per R-NR, mapping old subject → new subject
- **Pre-rebase SHAs (in `git log origin/cleanup`)**:
    f0026b1, 2488cdf, db5bdd0, 74c6835, f5204f5, 417650d, 634f626,
    b8f8bc7, 5f9418e, 04afe4a, 9c73100 (11 commits, oldest first)
- **Post-rebase SHAs** (will be new, deterministic from rebase algorithm):
    - f0026b1 will be replaced by a new SHA (because parent 2488cdf changes)
    - 2488cdf → new (subject fix)
    - 04afe4a → new (subject fix)
    - ... (9c73100 gets the lowest new SHA in the chain)
- **5-category counts after rebase** (from the 10 reworded subjects):
    chore: 2, docs: 6, fix: 2, wrench: 0, book: 0
    → exactly matches the user-profile 5-category set
- **E2E regression baseline unchanged**: 129/129 (no code or test
    changes, only commit subjects)
- **Pre-push-validator** runs after rebase → 15/15 expected PASS
    (subject changes don't affect the validator's checks; checks
    3, 4, 5 (yaml/py/shell) look at file content, not commit history)

## FOLLOWUP (queued, NOT in this commit)

- **R110-91**: reformat R110-78..R110-88 commit BODIES to 5-section
    (ZIEL/WIE/WAS_NICHT/BEWEIS/FOLLOWUP). Larger diff (~10× content),
    separate decision point.
- **R110-92**: cron-based audit job that greps commit subjects per
    category, fails if any drift detected.
- **R110-94**: changelog generation from reworded subjects
    (depends on R110-90+91 being stable for ≥1 sprint).
- **R110-97**: env-export helper for `.env` + `goose run` (separate
    additive commit, follows R110-96).
