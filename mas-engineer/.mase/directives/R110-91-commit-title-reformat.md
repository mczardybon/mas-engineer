# R110-91 — Re-format R110-78..R110-88 commit titles to 5-category

**Status:** DRAFT-ARCHIVED (2026-08-04, decision log below)
**Author:** Hermes (R110-89 Finding A follow-up)
**Target:** 11 commits in range R110-78..R110-88 (commit-title convention drift)
**Decision:** A. Nichts tun (cutoff-Mechanik R110-92 löst enforcement).

## Goal

Bring commit TITLES in the range R110-78..R110-88 into the 5-category
convention (`feat:` / `fix:` / `chore:` / `docs:` / `refactor:`), as
defined by the commit-msg-editor.sh case-on-subject-keywords mechanism
(R110-90) and verified by `tools/dev_category_drift.py` (R110-92).

## Why

- R110-90 (2026-08-03) rebased R110-89..R110-95 commit TITLES to the
  5-category set via `git rebase -i` with `reword` + commit-msg-editor.
  This worked for R110-90..R110-95 but **left R110-78..R110-88 titles
  untouched** (they predate the 5-cat convention).
- R110-94 Check 16+ (validator v2.2.0) reports historical drift in
  `--since 30` mode. To get clean exit 0 across the 30-day window,
  R110-78..R110-88 titles must be re-formatted.
- Without this fix, `dev_category_drift.py --since 30` exits 1
  (drift > 0) and Check 16+ BLOCKS every push. This blocks T5's
  pytest-run check (Check 17) from ever being green.

## Scope

1. 11 commit titles in range R110-78..R110-88 rewritten via
   `git rebase -i R110-77^` with `reword` + commit-msg-editor.sh
   case-mapping. **Force-push allowed** (validator permits it for
   R-NR-prefixed rebase commits, see R110-90 precedent).
2. Update `R110-89...R110-88` evidence-doc references if any
   mention the original titles (none expected, they only cite R-NR).

## 9-Section Spec

### 1. EXACT FILE + INSERT-POINT

No file change. This directive is **action-only** (git rebase).

Affected commits (R110-78..R110-88):
  R110-78, R110-79, R110-80, R110-82, R110-83, R110-84, R110-85,
  R110-86, R110-87, R110-88, R110-89 (11 total)

### 2. EXTRACT-PATTERN

For each commit in range, run:
  `git log -1 --format=%s R110-NN` to read current title.
  If title starts with `chore R110-NN` or `wrench R110-NN` or other
  non-conventional prefix, reword to `chore: R110-NN -- ...` or
  appropriate category.

### 3. MATCHING (rebase strategy)

`git rebase -i R110-77^` opens editor with pick/reword/squash/...
Use `reword` (r) for each of the 11 commits. The commit-msg-editor.sh
case-on-subject-keywords (R110-90) auto-applies the right category
based on subject content.

### 4. OUTPUT-SCHEMA

For each reworded commit, expected title format:
  `<category>: R110-NN -- <description>`

Categories (5 allowed):
  feat:     new feature
  fix:      bug fix
  chore:    maintenance / tooling
  docs:     documentation only
  refactor: code change without behavior change

### 5. 3-HOOK-POINTS

Pre-rebase:
  - `git fetch origin/cleanup` (ensure up-to-date)
  - `git log --oneline R110-77^..R110-88` (verify 11 commits)
  - `git config user.email` (must be configured)

Mid-rebase:
  - For each `reword` action, commit-msg-editor.sh runs
    automatically. Verify category applied (look for "category: "
    prefix in the resulting title).

Post-rebase:
  - `git log --oneline R110-77^..R110-88 | wc -l` (expect 11)
  - `python3 tools/dev_category_drift.py --since 30` (expect exit 0)
  - `git push --force-with-lease origin cleanup`

### 6. SEVERITY

HIGH. Without this fix, Check 16+ BLOCKS every push (drift > 0).
Blocks entire R110 sprint archival + Check 17 pytest-run adoption.

### 7. IDEMPOTENZ

Rebase is naturally idempotent: re-running it on already-rebased
commits is a no-op (titles already match 5-cat). Detection:
  `git log --format=%s R110-78..R110-88 | grep -vE "^(feat|fix|chore|docs|refactor): "`
should return 0 lines after rebase.

### 8. TESTING

1. `python3 tools/dev_category_drift.py --since 30` exits 0
2. `python3 tools/dev_category_drift.py --convention-since 2026-07-27`
   exits 0 (no historical drift in pre-cutoff window)
3. Pre-push-validator: all 17 checks (0, 1, 1.5, 2-15, 16+, 17) PASSED
4. `git log --oneline -20` shows clean 5-cat titles

### 9. DO-NOT (anti-patterns)

- **DO NOT** reformat the 11 commits in any way OTHER than
  prefix-change. Bodies stay as-is (R110-92 covers bodies if needed).
- **DO NOT** use `git rebase --interactive` with `edit` instead of
  `reword` — this would drop the bodies.
- **DO NOT** push without `--force-with-lease` — regular `--force`
  risks losing remote commits.
- **DO NOT** include R110-89..R110-95 in the rebase — they are
  already 5-cat (R110-90 already reformatted them).
- **DO NOT** archive R110-91 evidence to `docs/` until the rebase is
  verified and pushed.

## Provenance

- R110-89 evidence-doc Finding A (R110-91 — re-format commit titles).
- R110-90 rebase precedent (commit-msg-editor.sh + force-push pattern).
- R110-92 standalone drift detector (validation).
- R110-94 Check 16+ (push-gate enforcement).

## Acceptance criteria

- [ ] 11 commit titles in R110-78..R110-88 match 5-cat regex
- [ ] `dev_category_drift.py --since 30` exits 0
- [ ] `--force-with-lease` push to origin/cleanup succeeds
- [ ] No body content changed (only title prefix)
- [ ] Post-rebase: 11 commits still present, hashes changed (expected)
- [ ] Commit body of the R110-91 commit itself cites: 11 commits
      rewritten, numstat per category, dev_category_drift.py exit

## Decision log (2026-08-04, R110-103)

R110-91 was DRAFT (rebase-11-commits plan) when R110-92 introduced the
`pre-protocol cutoff` mechanism in `dev_category_drift.py`. With the
cutoff default at 2026-08-04, all 11 R110-78..R110-88 commits are
pre-cutoff = exempt from enforcement. `dev_category_drift.py --since 30`
is RC=0 (0 DRIFT, 0 REGRESSIONS) as of 2026-08-04. The Check 16+
pre-push-validator passes. So the **enforcement-pressure** that
motivated R110-91 no longer exists.

**Decision: A. Nichts tun** (default-decision per mas-engineer-discipline,
since user was not available to confirm). Reasons:
- R110-92 cutoff-Mechanik löst enforcement → rebase ist nicht mehr
  block-relevant, nur history-cleanup
- Force-push-Rebase riskiert externe refs (R110-sprint-archive,
  evidence-docs die commit-hashes zitieren)
- `dev_category_drift.py --convention-since 2026-07-27` zeigt weiterhin
  145 historical-drift-commits, aber das ist **inventory-mode**,
  nicht enforcement-mode → keine aktion erforderlich
- A ist reversibel: wenn der user später doch B (rebase) will, kann
  er es jederzeit auslösen

**Status:** DRAFT-ARCHIVED. Re-activate (= DRAFT) by:
- (a) user explicitly requests R110-91 rebase, OR
- (b) the cutoff default is moved earlier than 2026-07-27, bringing
      the 11 R110-78..R110-88 commits back into the enforcement
      window (Check 16+ would then start failing again).
