# R110-216 — C3 nested `mas-engineer/mas-engineer/` cleanup

**Date:** 2026-08-19 15:45Z
**Branch:** mas-mq
**HEAD before:** fcbf2d2 (R110-215)
**HEAD after:** (this commit, R110-216)

## What was done

User approved C3 cleanup (2026-08-19 15:40Z). Resolves the
"nested `mas-engineer/mas-engineer/`" open item from R110-213
inventory.

### Inventory findings

`/workspace/dev-branch/mas-engineer-cleanup/mas-engineer/mas-engineer/`
contained exactly 2 files, 21 bytes total:
- `.mase/rules/.state` = `REFRESHED\n` (10 bytes)
- `.mase/rules/.last_refresh` = `1787017841\n` (11 bytes, 2026-08-18T01:50:41Z)

### Origin of these files

Tracked first by dangling commit **`599e40e9308df1fa22a66a216370f2a0df9e1cfd`**
with message `[MAS-ENGINEER] test commit` (author mczardybon,
2026-08-14T18:14:43Z, parent 45e52c21).

This commit was a **test commit** (per R110-152 git-commit-hygiene
skill pattern) and was undone via `git reset HEAD~1` (per reflog:
`52d5b3f HEAD@{11}: reset: moving to HEAD~1`).

After the reset:
- Files were no longer in any commit
- 599e40e became a dangling commit (not in any ref, would be GCed)
- Working-tree files remained because git reset only moves HEAD,
  it does not delete files that were written to disk

### Why files were updated 2026-08-18 even though untracked

The filesystem .last_refresh (1787017841 = 2026-08-18T01:50:41Z)
is ~5 days newer than the dangling-commit version (1786731282
= 2026-08-14T18:14:42Z).

A rule-refresh workflow ran on 2026-08-18 and wrote to
BOTH outer `mas-engineer/.mase/rules/` AND nested
`mas-engineer/mas-engineer/.mase/rules/`. The nested path was
likely reached because the worktree structure
(mas-engineer-cleanup is a worktree of mas-engineer) caused
some path-resolution code to recurse into the wrong directory.

This is a separate workflow-bug candidate (R110-217?) — out of
scope for R110-216 which is just cleanup.

### Cleanup action

**Step 1:** Preserved dangling-commit blobs in evidence file:
- `logs/e2e-evidence-gen2/2026-08-19T15-45-00Z-R110-216-c3-nested-cleanup/dangling-commit-snapshot.json`
- Contains both 599e40e (original) and filesystem (2026-08-18) versions
- Audit trail for: "what was in the nested path, and why"

**Step 2:** `rm -rf mas-engineer/mas-engineer/`
- Removed the entire 21-byte subtree
- Outer `mas-engineer/.mase/rules/` (the real one) untouched
- Verified outer files still present and unchanged

**Step 3:** Verified clean state
- `git status -sb`: only evidence dir shows as untracked (intended)
- `git ls-files mas-engineer/mas-engineer/`: empty (path no longer in any commit)
- `git fsck --unreachable`: 599e40e not in output (already GCed or pending)

## Files (1)

```
A  logs/e2e-evidence-gen2/2026-08-19T15-45-00Z-R110-216-c3-nested-cleanup/
   dangling-commit-snapshot.json    (1.9KB)
```

Plus untracked deletion: `mas-engineer/mas-engineer/` (21 bytes removed from
working tree, was never tracked after 599e40e reset).

## numstat

1 file, 29 insertions.

## Body-claim verification (Check 0)

| Claim | Evidence |
|---|---|
| "2 files, 21 bytes" | pre-delete `find ... -type f -exec ls -la` showed `.state` (10 bytes) + `.last_refresh` (11 bytes) |
| "origin: dangling 599e40e" | `git show 599e40e --name-status` shows A for both files; `git reflog 599e40e` shows reset HEAD~1 |
| "dangling, not in any ref" | `git for-each-ref --contains 599e40e` = empty; `git fsck --unreachable` = no 599e40e in output |
| "outer untouched" | `cat mas-engineer/.mase/rules/.state` + `.last_refresh` after delete shows same content as before |
| "evidence file written" | `ls -la logs/e2e-evidence-gen2/2026-08-19T15-45-00Z-R110-216-c3-nested-cleanup/` shows 1969-byte JSON |
| "audit trail complete" | snapshot.json contains both 599e40e version AND filesystem version with timestamps decoded |
