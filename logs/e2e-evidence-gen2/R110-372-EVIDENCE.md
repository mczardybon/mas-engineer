# R110-372 — EVIDENCE: dev_editor.py 0% → 50% coverage push r1

**Commit:** `📝 R110-372 — dev_editor.py 0% to 50% coverage push r1 + commit-msg-recovery (CHANGELOG + EVIDENCE + EXEMPT_HASHES)` (this commit)
**Branch:** mas-t-tests
**Date:** 2026-09-08
**Author:** Hermes-MAS-Engineer <Hermes@mas-engineer.local>
**Sprint:** R110 (continuous)
**Parent:** `aa4a975` (R110-372 work commit, exempt from title-check due to `[]` empty-message bug, see CHANGELOG-2026-09-08)

## Files Touched (3 in this commit + 1 in parent)

| File | Status | Lines | Description |
|------|--------|-------|-------------|
| `docs/CHANGELOG-2026-09-08-r110-372-commit-msg-recovery.md` | NEW | 153 | Full lessons-learned: commit-msg bug, verification-theater catch, R110-373 r2 plan |
| `logs/e2e-evidence-gen2/R110-372-EVIDENCE.md` | NEW | (this file) | EVIDENCE with honest coverage numbers |
| `tools/dev_category_drift.py` | MOD | +1 | `aa4a975` added to `EXEMPT_HASHES` (R110-281 pattern) |
| `tests/test_r110372_dev_editor_coverage_push_r1.py` | NEW (in `aa4a975` parent) | 628 | 54 tests, 12 classes, 100% pass |

## Pre-Fix State (0% coverage on dev_editor.py)

```
$ pytest tests/test_r110372_dev_editor_coverage_push_r1.py \
    --cov=tools/dev_editor --cov-report=term
  (file existed? no)
  tools/dev_editor.py  — not in any test, 0% coverage
```

No test file existed for `tools/dev_editor.py` at `3764ffa` (R110-371 r2 parent). The 385 stmts were entirely uncovered.

## Post-Fix State (49.87% coverage on dev_editor.py)

```
$ pytest tests/test_r110372_dev_editor_coverage_push_r1.py \
    --cov=tools/dev_editor --cov-report=term
  tools/dev_editor.py                     385    192    50%   40-44, 51, 55, 63, 73-78, ...
  54 passed in 5.66s
```

(Detail: `193 missing` per `--cov-report=json`, `192 covered` → 49.87% rounded to 50% display.)

**Honest delta: +49.87pp (0% → 49.87%)**, **+192 stmts covered**.

## Pre-Existing Test Status (R110-372 does not regress)

```
$ pytest tests/test_pre_push_check_1_5_skill_alignment.py \
         tests/test_r110370_dev_self_audit_bug_hunt.py \
         tests/test_sub_mas_im_finder.py \
         tests/test_r110322_dev_im_finder_helpers.py \
         tests/test_r110259_dev_yaml_editor_coverage_push_r1.py
  — 105 tests, 0 failures
```

## Pytest Result (this commit's tests)

```
$ pytest tests/test_r110372_dev_editor_coverage_push_r1.py -v
============================= 54 passed in 5.66s ==============================
```

## Test Class Breakdown

| Class | Tests | Function Range Covered |
|---|---|---|
| TestEnsureDir | 2 | L66-70 `ensure_dir` |
| TestValidateYaml | 2 | L71-80 `validate_yaml` (subprocess + yaml.safe_load) |
| TestCreateBackup | 2 | L81-102 `create_backup` (file-not-found, success) |
| TestRemainderoreBackup | 2 | L103-121 `remainderore_backup` (backup-not-found, restore) |
| TestDoPatch | 5 | L122-338 `do_patch` (5 paths: file-not-found, yaml-invalid, no-match, success, multi-match) |
| TestLoadBestPractices | 4 | L339-352 `load_best_practices` (no-file, valid, invalid, empty) |
| TestValidateAgainstBestPractices | 16 | L353-444 `validate_against_best_practices` (all 7 check_types + auto_apply) |
| TestCmdValidate | 5 | L445-508 `cmd_validate` (5 paths) |
| TestDoValidate | 3 | L509-532 `do_validate` (3 paths) |
| TestDoBackup | 2 | L533-540 `do_backup` |
| TestDoRollback | 3 | L541-551 `do_rollback` |
| TestMainViaSubprocess | 7 | L552-603 `main` (7 argparse paths) |
| **Total** | **54** | **12 function ranges, 50% coverage** |

## Pre-Push Gate

- Step 0 secret scan: ✅ no secrets
- Check 17 (pytest-run): ✅ 54/54 pass on new test file
- Check 18 (spec-invariant): ✅ exit 0
- Check 24 (SOT-location): ✅ new file in `tests/` (standard location)
- Check 1.5 (commit title): ⚠️ `aa4a975` parent has `[]` subject — **EXEMPT** in `dev_category_drift.EXEMPT_HASHES` (this commit adds the exemption)
- Check 0 (body disclosure): ⚠️ `aa4a975` body is empty — same exemption rationale
- Category-drift detector: ✅ 0 DRIFT, 313 conform, 479 exempt (last 60 days, post-this-commit)

## Recovery Incident (R110-372 commit-msg bug)

The original `aa4a975` commit was created with literal subject `[]` and empty body, due to an unconfirmed interaction between `git commit -F <file>` and a 2,733-byte UTF-8 commit message containing 13 em-dashes. The commit **content is intact** (628-line test file fully committed), only the message is wrong.

**Recovery per R110-281 pattern (no force-push):**
1. `aa4a975` added to `EXEMPT_HASHES` in `tools/dev_category_drift.py` (R110-369 pattern).
2. This follow-up commit (`📝 R110-372 — ...`) provides the correct documentation and accurate coverage claim.
3. `docs/CHANGELOG-2026-09-08-r110-372-commit-msg-recovery.md` contains full lessons-learned.
4. R110-373 r2 plans root-cause analysis of the empty-message bug.

**What is NOT done (intentionally):**
- No `git commit --amend` + `git push --force-with-lease` to repair `aa4a975`. **FORCE-PUSH-VERBOT (R110-281) respected.**

## Verification-Theater Self-Catch

The original `aa4a975` commit body claimed "0% → 85% (+85.0pp)". I caught this before push was irreversible and re-ran `pytest --cov --cov-report=json` to get honest numbers. The **real coverage is 49.87% (50% display)**, which is still a respectable +50pp improvement but not the +85pp I had hallucinated.

**Lesson:** Never write a coverage delta claim in a commit body without first running `--cov-report=json` and reading the numbers. This is a R110-78 verification-theater pattern.

## R110-373 r2 Plan (next sprint)

Add ~30 more tests targeting the 193 missing lines:
- `TestDoPatchExtended` (15 tests): R55 session-counter, git pre-edit commit, mehrfachfund, restore-on-fail
- `TestDoValidateExtended` (8 tests): whole happy-path, file-not-found, invalid yaml
- `TestCmdValidateExtended` (4 tests): empty bp, no bp_key, auto_apply=True
- `TestLoadBestPracticesExtended` (3 tests): YAMLError, empty yaml, no best_practices key
- `TestMainArgparseError` (1 test): `--patch` missing args → exit 1

Target: 50% → 80% (+30pp) in R110-373 r2.

## Refs

- R110-281 (CHANGELOG-2026-08-28) — original force-push incident + recovery pattern
- R110-369 (2026-09-08) — `EXEMPT_HASHES` mechanism in `dev_category_drift.py`
- R110-370 (2026-09-08) — smoke-test mirror of `EXEMPT_HASHES`
- R110-371 (2026-09-08) — dev_workspace.py 80.1% (r2)
- R110-31 — commit-message protocol (em-dash warning)
- R110-78 — verification-theater pattern
- Skill: `mas-engineer-coverage-push-workflow`
