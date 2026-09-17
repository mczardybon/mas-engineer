# R110-216 — C3 evidence-archive

**Date:** 2026-08-19 15:45Z
**Scope:** cleanup of nested `mas-engineer/mas-engineer/` (21 bytes)

## What this evidence proves

1. The nested path was created by commit **`599e40e9308df1fa22a66a216370f2a0df9e1cfd`**
   `[MAS-ENGINEER] test commit` (2026-08-14T18:14:43Z, mczardybon).
2. The commit was reset out via `git reset HEAD~1` (per git reflog
   `52d5b3f HEAD@{11}: reset: moving to HEAD~1`).
3. Working-tree files remained because `git reset` does not delete
   files that were written to disk by a previous commit.
4. Files were never re-committed after the reset.
5. Files were updated again on 2026-08-18 by a rule-refresh workflow
   that recursed into the nested path (separate bug, out of scope).

## Files in this archive

- `dangling-commit-snapshot.json` — both 599e40e and filesystem
  versions of the 2 nested files, with timestamps decoded
- `SESSION-REPORT.md` — full cleanup report

## Verification commands

```bash
# verify 599e40e is dangling
git for-each-ref --contains 599e40e   # empty output
git fsck --unreachable --no-reflogs   # 599e40e not listed

# verify cleanup
git status -sb
# shows: ## mas-mq...origin/mas-mq
#        ?? mas-engineer/logs/e2e-evidence-gen2/2026-08-19T15-45-00Z-R110-216-c3-nested-cleanup/

# verify outer .mase/rules/ untouched
cat mas-engineer/.mase/rules/.state
# REFRESHED
cat mas-engineer/.mase/rules/.last_refresh
# 1784882105
```
