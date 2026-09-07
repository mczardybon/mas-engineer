# R110-369 — Pre-existing test-debt cleanup (post R110-367 + R110-368)

## CONTEXT

After R110-367 (dev_dashboard_refresh.py 0% → 94%) and R110-368 (recipe-yaml-corruption
cascade fix, 25→3 pre-existing fails), 3 pre-existing test fails remain in the 14-file
pre-push Check 17 subset. All 3 are pre-existing, NOT caused by R110-367/368.

## STATUS (as of 2026-09-07, post-R110-368)

- Total pre-existing-fails: 3 (down from 25, 88% reduction)
- 2 additional files time out (not characterized yet):
  - tests/test_dev_im_finder_scan_lib.py  (TIMEOUT, pre-existing slow suite)
  - tests/test_r110279_runtime_var_skip.py (TIMEOUT, pre-existing slow suite)

## THE 3 REMAINING PRE-EXISTING FAILS

### Fail 1: test_r110259_category_drift_scope::test_r110257_subject_accepted_by_detector_in_real_git_history

**Root cause:** 5 commits in last 60 days have empty titles `[]` (R110-31 protocol
violation). The detector `tools/dev_category_drift.py` rejects these and exits 1,
which fails the test assertion `drift_count == 0`.

**Affected commits:**
```
9e7e990d []  (pre-existing, pre-R110-367)
d56ec64f []  (pre-existing, pre-R110-367)
6c911cbb []  (pre-existing, pre-R110-367)
46469dcd []  (pre-existing, pre-R110-367)
e382acd  []  (R110-315 fixture commit, kept as empty for sub_-.yaml test)
```

**Fix:** Interactive rebase to assign proper category emoji + subject to all 5
commits. R110-31 protocol: `[emoji] R<NR>-<topic> — <subject>`.
**Risk:** Force-push required after rebase. Per R110-281 (force-push-versehen), must
document transparently. Use `git tag pre-r110-369-backup` BEFORE rebase.
**Priority:** Medium (visible in pre-push output, blocks Check 17).

### Fail 2: test_pre_push_check_1_5_skill_alignment::test_check_1_5_origin_cleanup_recent_commits_match

**Root cause:** Test fetches `origin/<current-branch>` (mas-t-tests) and checks if
last 30 commit messages match the validator Check 1.5 regex (emoji + subject).
We haven't pushed yet, so `origin/mas-t-tests` is empty / stale.

**Fix:** Push the branch (this R-round is doing that). After push, the test will
have data to check against.
**Priority:** Resolved by R110-367+368 push itself.

### Fail 3: test_sub_mas_im_finder::test_step_0_6_self_audit_attaches_mm9_ext

**Root cause:** 3 BLOCKERs in `dev_self_audit.run_self_audit()` when scoped to
`recipe/instructions/`. The BLOCKERs are:
- INVARIANT-ab (1 file: `recipe/instructions/<file>.md` violates cross-recipe invariant)
- INVARIANT-cd (1 file: same)
- INVARIANT-yaml (1 file: same)

**Diagnosis needed:** Which files violate these? Run
`python3 -c "from tools.dev_self_audit import run_self_audit; from pathlib import Path; r = run_self_audit(scope=Path('recipe/instructions'), repo_root=Path('.')); [print(f.code, f.severity, f.description) for f in r.findings if f.severity == 'BLOCKER']"`
to get the file list.

**Fix:** Update the 3 violating files to satisfy the invariants. Likely
cross-recipe-instruction docs that drifted from the actual recipe.
**Priority:** Medium (BLOCKER severity, blocks Check 17, but pre-existing).

## THE 2 TIMEOUTS (not yet diagnosed)

### Timeout 1: tests/test_dev_im_finder_scan_lib.py
- Pre-existing slow suite (large IM dataset)
- 300s+ on single-process pytest
- Per R110-246 ci-tests.yml, parallel xdist can be used: `pytest -n 4 tests/test_dev_im_finder_scan_lib.py`
- Out of scope for R110-369

### Timeout 2: tests/test_r110279_runtime_var_skip.py
- Pre-existing slow suite
- 300s+ on single-process pytest
- Out of scope for R110-369

## DIREKTIVE

R110-369 will:
1. Diagnose the 3 INVARIANT BLOCKERs in Fail 3 (find the 3 violating files)
2. Fix those 3 files (1-line doc fixes, not recipe changes)
3. Update the 4 pre-existing empty-title commits to have proper R110-31 titles
   (5th commit `e382acd` stays empty — it's a deliberate fixture for sub_-.yaml)
4. Verify Check 17 with `pytest --timeout=300` shows 0/0 pre-existing-fails
5. Force-push with transparent post-mortem (per R110-281 template)

Estimated scope: 1 commit, 5-7 files changed, <10 lines net diff.
Estimated duration: 30 minutes (most time is `git rebase -i` for the 4 commits).

## VERIFICATION

```bash
# 1. Re-run Check 17 after fix
python3 -m pytest tests/test_r110259_category_drift_scope.py tests/test_pre_push_check_1_5_skill_alignment.py tests/test_sub_mas_im_finder.py -p no:cacheprovider --no-header --tb=line --timeout=300 -q
# Expected: all 0 fails (after pushing makes Fail 2 pass)

# 2. Pre-push validator
timeout 600 goose run --recipe recipe/sub/sub_mas-pre-push-validator.yaml --no-session
# Expected: all checks PASS, .state/pipeline/pre_push_validation.yaml status: passed

# 3. Push
git push origin mas-t-tests
# Expected: rc=0, no force-push needed
```
