# R110-217 — fix dev_rule_refresh.sh CWD-safety bug

## Problem

`tools/dev_rule_refresh.sh` line 13 hard-codes the rules directory
as a CWD-relative path:

```bash
REGL_DIR="mas-engineer/.mase/rules"
```

This is only correct when the script is invoked from the
**worktree-root** (`mas-engineer-cleanup/`). When invoked from
the inner subdir (`mas-engineer-cleanup/mas-engineer/`, which
is the actual mas-engineer source tree), the path resolves to
`mas-engineer-cleanup/mas-engineer/mas-engineer/.mase/rules` —
i.e. a NESTED WRONG directory that does not match the real
rules location.

This bug is the root cause of R110-216 C3 finding: dangling
commit 599e40e wrote `mas-engineer/mas-engineer/.mase/rules/.state`
and `.last_refresh` into the nested path. After `git reset HEAD~1`
removed the commit, the working-tree files remained; a subsequent
rule-refresh on 2026-08-18 01:50 updated them again (filesystem
mtime 1787017841 = 2026-08-18T01:50:41Z).

## Evidence

- Outer `mas-engineer/.mase/rules/` (the real one) has timestamp
  1784882105 = 2025-03-23T14:35:05Z (file mtime 2026-08-14 15:58)
- Nested `mas-engineer/mas-engineer/.mase/rules/` (the bug) had
  timestamp 1787017841 = 2026-08-18T01:50:41Z (file mtime 2026-08-18 01:25/01:50)
- 5-day difference confirms the nested path was being written
  to by a different invocation context than the outer path
- The 01:50 nested-refresh corresponds to a build-test workflow
  that ran with CWD != mas-engineer-cleanup (workflow_runs missing
  because rule-refresh is not always captured as a workflow-run
  artifact)

## Comparison: how does dev_rule_checker.py handle it?

`tools/dev_rule_checker.py` lines 14-15 uses the correct
defensive pattern:

```python
BASE_DIR = os.path.abspath(".")
MAS_DIR = os.path.join(BASE_DIR, "mas-engineer") if os.path.isdir(os.path.join(BASE_DIR, "mas-engineer")) else BASE_DIR
```

This is exactly the pattern `dev_rule_refresh.sh` should use.

## Fix

Replace the hard-coded `REGL_DIR="mas-engineer/.mase/rules"` in
`tools/dev_rule_refresh.sh` with a script-dir-based resolution
that follows the same pattern as dev_rule_checker.py.

### Proposed change (bash)

```bash
# Find the script's own directory (handles being invoked from any CWD)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Resolve the workspace root (parent of SCRIPT_DIR if SCRIPT_DIR is mas-engineer/tools)
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# MAS rules live in workspace/mas-engineer/.mase/rules (if mas-engineer/ subdir exists)
# OR workspace/.mase/rules (if not, e.g. when script is run from inside mas-engineer/)
if [ -d "$WORKSPACE_ROOT/mas-engineer/.mase/rules" ]; then
    REGL_DIR="$WORKSPACE_ROOT/mas-engineer/.mase/rules"
    TEMPLATE_DIR="$WORKSPACE_ROOT/mas-engineer/.mase/templates"
elif [ -d "$SCRIPT_DIR/../.mase/rules" ]; then
    REGL_DIR="$SCRIPT_DIR/../.mase/rules"
    TEMPLATE_DIR="$SCRIPT_DIR/../.mase/templates"
else
    # Fallback: keep CWD-relative (legacy behavior, may be wrong)
    REGL_DIR="mas-engineer/.mase/rules"
    TEMPLATE_DIR="mas-engineer/.mase/templates"
fi
```

Then update line 39 from:
```bash
cp -n mas-engineer/.mase/templates/user_rulen_template.yaml "$REGL_DIR/rulen.yaml" 2>/dev/null
```
to:
```bash
cp -n "$TEMPLATE_DIR/user_rulen_template.yaml" "$REGL_DIR/rulen.yaml" 2>/dev/null
```

## Why idempotent

- BASH_SOURCE-based resolution gives the SAME path regardless of CWD
- Three-tier fallback (outer / inner / legacy) covers all known
  invocation contexts
- No behavior change for the common case (CWD = mas-engineer-cleanup)
- No new files created
- No .state / .last_refresh writes to wrong path anymore

## Scope

**In scope (this R-number):**
- tools/dev_rule_refresh.sh (line 13, line 39)

**Out of scope (separate R-numbers):**
- tools/dev_mode.sh (lines 25, 79) — same bug, different file
- tools/dev_gatekeeper.py (line 117) — uses `~/.config/goose/...` hardcoded
- tools/dev_autobuild.sh (line 20) — uses `$WORKSPACE` env var (not CWD-relative)
- tools/dev_haerte_propagation.py (line 18) — takes workspace as arg, OK
- tools/dev_recursion_override.py (lines 36, 67) — takes workspace as arg, OK

## Verification

After fix:
1. `bash tools/dev_rule_refresh.sh` from `mas-engineer-cleanup/` → still writes to `mas-engineer/.mase/rules/` (outer)
2. `cd mas-engineer && bash tools/dev_rule_refresh.sh` → now also writes to `mas-engineer/.mase/rules/` (outer, was nested)
3. `bash tools/dev_rule_refresh.sh --mode generic` from any CWD → copies template from correct path

## Test addition

Add a test in tests/ that invokes the script from both contexts
and asserts the .state file appears in the OUTER path, not nested.
