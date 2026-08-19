# R110-217 — fix dev_rule_refresh.sh CWD-safety bug

**Date:** 2026-08-19 19:49Z
**Branch:** mas-mq
**Status:** FIX VERIFIED ✓

## Root cause (C3 followup)

`tools/dev_rule_refresh.sh` hard-coded the rules directory as a
CWD-relative path:

```bash
REGL_DIR="mas-engineer/.mase/rules"
```

This is only correct when invoked from `mas-engineer-cleanup/`
(the worktree root). When invoked from `mas-engineer-cleanup/mas-engineer/`
(the inner subdir, the actual source tree), the path resolves
to a NESTED WRONG directory: `mas-engineer-cleanup/mas-engineer/mas-engineer/.mase/rules`.

This bug caused R110-216 C3: dangling commit 599e40e wrote to
the nested path; after `git reset HEAD~1` the files remained;
a 2026-08-18 01:50 rule-refresh updated them again (filesystem
mtime 1787017841).

## Reference pattern (the correct one)

`tools/dev_rule_checker.py` lines 14-15 uses a defensive pattern
that handles both invocation contexts:

```python
BASE_DIR = os.path.abspath(".")
MAS_DIR = os.path.join(BASE_DIR, "mas-engineer") if os.path.isdir(os.path.join(BASE_DIR, "mas-engineer")) else BASE_DIR
```

## Fix applied

In `tools/dev_rule_refresh.sh`:

1. Replaced hard-coded `REGL_DIR="mas-engineer/.mase/rules"`
   with BASH_SOURCE-based script-dir resolution (lines 13-31):
   - `SCRIPT_DIR = cd $(dirname ${BASH_SOURCE[0]}) && pwd`
   - `WORKSPACE_ROOT = cd $SCRIPT_DIR/../.. && pwd`
   - Three-tier fallback: outer / inner / legacy CWD-relative
2. Added `TEMPLATE_DIR` variable (same resolution pattern)
3. Updated line 39 generic-mode template copy to use `$TEMPLATE_DIR`

## Verification

Two-CWD test (script now writes to outer .mase/rules/ from both
contexts, no nested mas-engineer/mas-engineer/ created):

### TEST 1: CWD = mas-engineer-cleanup/ (outer)
- Bash syntax check: ✓ OK
- Script runs, writes to `mas-engineer/.mase/rules/.state` + `.last_refresh`
- File content: `REFRESHED` + unix timestamp ✓

### TEST 2: CWD = mas-engineer-cleanup/mas-engineer/ (inner — was broken)
- Script runs, writes to `mas-engineer/.mase/rules/.state` + `.last_refresh`
- File content: `REFRESHED` + unix timestamp ✓
- **No nested `mas-engineer/mas-engineer/` created** ✓

## Out of scope (separate R-numbers)

- `tools/dev_mode.sh` lines 25, 79 — same CWD-relative pattern bug
- `tools/dev_gatekeeper.py` line 117 — uses `~/.config/goose/...` hardcoded
- `tools/dev_rule_refresh.sh` line 46 — searches for `harte_rulen.yaml`
  but real file is `hard_rules.yaml` (orthogonal bug, R110-218?)

## Directive file

`mas-engineer/.directives/R110-217-rule-refresh-cwd-safety.md`
(4692 bytes) — full bug analysis, evidence, fix proposal.

## Files (this commit)

- M  tools/dev_rule_refresh.sh
  - lines 13-31: REGL_DIR resolution fix (+19 lines, -1 line)
  - line 57: TEMPLATE_DIR usage in template copy
- A  .directives/R110-217-rule-refresh-cwd-safety.md (new)
- A  logs/e2e-evidence-gen2/2026-08-19T15-45-00Z-R110-216-c3-nested-cleanup/R110-217-FIX-REPORT.md
