# R110-360 — DIREKTIVE: Evidence SOT-Location Cleanup

## CONTEXT

R110-257 (2026-08-27) introduced Check 24 (evidence/directive SOT-location audit) in `sub_mas-pre-push-validator.yaml` (v2.9.0). The check mandates that evidence files live at `logs/e2e-evidence-gen2/` (REPO-ROOT) — NOT `mas-engineer/logs/e2e-evidence-gen2/`.

Between R110-257 and R110-359, twelve (12) evidence files were force-added to the git index at the WRONG SOT location (likely the subdir-relative `mas-engineer/logs/...` path) by sessions R110-336, R110-338, R110-340, R110-342, R110-346, R110-348, R110-350, R110-352, R110-354, R110-356, R110-358. These are at:

```
mas-engineer/logs/e2e-evidence-gen2/R110-{334,336,338,340,342,346,348,350,352,354,356,358}-EVIDENCE.md
```

Wait — actually `git ls-files` from the OUTER worktree (`mas-engineer-cleanup/`) shows them at `logs/e2e-evidence-gen2/...` (REPO-ROOT, the CORRECT SOT). The Check 24 failure is reporting the same files with the `mas-engineer/` prefix prepended because of the validator's CWD or path-interpretation.

**Root cause hypothesis:** When the validator runs from inside the `mas-engineer/` subdir (R110-128+ pattern: the recipe is at `mas-engineer/recipe/sub/sub_mas-pre-push-validator.yaml`), its CWD is the subdir. The `git ls-files` then returns repo-root-relative paths like `mas-engineer/logs/...` because the git root is the parent, but the relative-path-from-subdir has the `mas-engineer/` prefix.

Or: the validator's check is misnaming the files. Either way, the result is that **every push since R110-336 has been failing Check 24** — but the pushes still happened (R110-336..R110-358 are all on origin/mas-t-tests). The "BLOCK" message was either: (a) ignored, (b) the validator had a different version, or (c) the file paths shifted.

## DIREKTIVE

Investigate + fix the Check 24 / `test_dev_evidence_sot.py::test_clean_state_exits_zero` mismatch so future pushes don't carry the pre-existing BLOCK.

### Step 1: Re-confirm the current state
```bash
cd /workspace/dev-branch/mas-engineer-cleanup
git ls-files logs/e2e-evidence-gen2/*-EVIDENCE.md | wc -l    # should be 12+
# Verify validator output:
cd mas-engineer && export PATH="/root/.local/bin:$PATH" && set -a && . .env && set +a
goose run --recipe recipe/sub/sub_mas-pre-push-validator.yaml --no-session 2>&1 | grep -A2 "Check 24"
```

### Step 2: Determine actual root cause
Hypothesis A: validator CWD-relative path display (cosmetic, fix in validator)
Hypothesis B: real path mismatch (test must be updated to match reality)
Hypothesis C: test fixture drift (the test_clean_state_exits_zero was added when only 1-2 evidence files existed; now 12+)

Check `recipe/instructions/sub_mas-pre-push-validator.md` lines 1410-1450 for the exact `git ls-files` + path-stripping logic. The fix is either:
- Strip the leading `mas-engineer/` prefix in the validator display, OR
- Update the pytest test to assert against the actual paths in HEAD (not the un-prepended SOT)

### Step 3: Apply fix
If Hypothesis A (cosmetic): patch the validator's report function to strip `mas-engineer/` from anti-SOT file paths.

If Hypothesis B/C: either
- Move all 12 files to the correct SOT (probably already there at `logs/...` REPO-ROOT, just delete the stale `mas-engineer/logs/...` references)
- Update the test's assertion to match reality (12 files at `logs/e2e-evidence-gen2/` = PASS, not the historical 0)

### Step 4: Re-run + verify
```bash
# After fix:
goose run --recipe recipe/sub/sub_mas-pre-push-validator.yaml --no-session 2>&1 | grep "Check 24"
# Should be: ✅ Check 24 passed
pytest tests/test_dev_evidence_sot.py -v --color=no
# Should be: 100% PASS
```

## VERIFICATION

After applying the fix:
1. `goose run --recipe recipe/sub/sub_mas-pre-push-validator.yaml --no-session` returns `Check 24: ✅ passed`
2. `pytest tests/test_dev_evidence_sot.py` is 100% green
3. `git log --oneline -5` shows the R110-360 commit with the fix
4. Origin/mas-t-tests push succeeds (no more pre-existing BLOCK)

## FILES TOUCHED

- `recipe/instructions/sub_mas-pre-push-validator.md` (if Hypothesis A) — strip `mas-engineer/` prefix in Check 24 display
- `tests/test_dev_evidence_sot.py` (if Hypothesis B/C) — update assertion
- OR `tools/dev_evidence_sot_audit.py` (the underlying tool the test calls) — fix the audit logic

## PRIORITY

Prio-1 (BLOCKER): every push since R110-336 carries this BLOCK. R110-359 hit it again. Urgent fix needed so future R-sprints (R110-361+) don't have to document the pre-existing BLOCK in every commit body.
