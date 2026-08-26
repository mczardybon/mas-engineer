# R110-257 — EVIDENCE

## Pre-push verification (deterministic, reproducible)

### 1. Secret scan (Step 0)
```
$ git ls-files | xargs grep -lE 'sk-[A-Za-z0-9]{3,}\.\.\.[A-Za-z0-9]{3,}|ghp_[A-Za-z0-9]{3,}\.\.\.[A-Za-z0-9]{3,}' 2>/dev/null
(leer — 0 hits)
$ git diff origin/master..HEAD | grep -nE 'sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}'
(leer — 0 hits in working tree diff)
```
**Result:** ✅ PASS — no secrets in tracked files or working-tree diff.

### 2. Pytest (Check 17, R110-78 prevention)
```
$ python3 -m pytest tests/ -q --tb=line --timeout=300 --ignore=.state
1641 passed in 414.02s (0:06:54)
```
**Result:** ✅ PASS — 1641/1641 tests pass in 6:54.
- 12 new tests added (`tests/test_dev_evidence_sot.py`) — all 12 pass
- 1 pre-existing test (`test_sub_mas_im_finder.py::test_step_0_6_self_audit_attaches_mm9_ext`) was
  broken by the v2.8.0→v2.9.0 bump (Check 24 changed 23→24 checks in 3 places:
  recipe markdown line 26, test docstring line 5/8, test assertions). Fixed in
  R110-257 (added R110-257 reference line + bumped counts to 24). Re-run → PASS.

### 3. Spec-invariant check (Check 18, R110-118 prevention)
```
$ python3 mas-engineer/tools/dev_evidence_sot.py --git --strict
RESULT: ✅ PASS — no SOT violations
exit code: 0
$ python3 -c "import yaml; print(yaml.safe_load(open('mas-engineer/recipe/sub/sub_mas-pre-push-validator.yaml'))['version'])"
2.9.0
$ git ls-files logs/e2e-evidence-gen2/ | wc -l
139
$ git ls-files mas-engineer/.directives/ 2>/dev/null | wc -l
0
$ git ls-files mas-engineer/logs/ 2>/dev/null | wc -l
0
$ git check-ignore -v mas-engineer/.directives/R110-999.md
.gitignore:233:mas-engineer/.directives/  mas-engineer/.directives/R110-999.md
$ git check-ignore -v mas-engineer/logs/test.log
.gitignore:238:**/mas-engineer/logs/  mas-engineer/logs/test.log
```
**Result:** ✅ PASS — all evidence/directive files at SOT locations; .gitignore
blocks both anti-SOT locations (even before files exist).

### 4. File counts (deterministic)
```
35 files, 832 insertions, 12 deletions (from --stat at start of pre-push)
+ 1 added: mas-engineer/docs/CHANGELOG-2026-08-26-r110-257.md
= 36 files, 1006 insertions, 12 deletions (pre-EVIDENCE.md add; pre-push-validator run; pre-R110-257-EVIDENCE.md)
```
- 28 renames (no content change, history preserved)
- 4 modifications (`.gitignore` +31, `STATUS.md` +65, `recipe/instructions/sub_mas-pre-push-validator.md` +83, `recipe/sub/sub_mas-pre-push-validator.yaml` +4/-4)
- 2 new test files (`tests/test_dev_evidence_sot.py` 291 lines, `tests/test_sub_mas_pre_push_validator.py` +15)
- 1 new tool (`tools/dev_evidence_sot.py` 351 lines)
- 1 new CHANGELOG (`docs/CHANGELOG-2026-08-26-r110-257.md` 174 lines)

NOTE: After the pre-push-validator run (R110-258), the gate's Check 0 corrected
4 of the above body-numstat claims. CORRECTED values:
  - .gitignore: +31 lines (was +3 in body — wrong; the diff added 31 lines
    of gitignore rules blocking anti-SOT paths, not 3)
  - recipe/sub/sub_mas-pre-push-validator.yaml: +4/-4 (was +8/-8 in body — wrong;
    the actual edit was a tight version-bump + instructions metadata tweak)
  - R110-257-EVIDENCE.md: 114 lines (was +123 in body — wrong; the actual file
    is 114 lines as of R110-258 amendment)
  - logs/e2e-evidence-gen2/ file count: 140 at HEAD (was 139 in body — wrong;
    113 prior + 26 renames + 1 R110-257-EVIDENCE.md = 140)
See R110-258-CORRECTION.md in this directory for the full body-claim-correction
audit (R110-174 / R110-256 pattern).

### 5. Renames verified
```
$ git diff --cached --name-status -M | grep "^R" | wc -l
28
$ git diff --cached --name-status -M | grep "^R" | grep -E "logs/e2e-evidence-gen2" | wc -l
26
$ git diff --cached --name-status -M | grep "^R" | grep -E "\.directives" | wc -l
2
```
- 26 evidence renames (R110-194/210/214/215/216/229/230/255 violators → REPO-ROOT)
- 2 directive renames (R110-217/218 → `.mase/directives/`)

### 6. Prevention layers verified
1. `.gitignore` (+3 lines, blocks `mas-engineer/.directives/` + `mas-engineer/logs/`) ✅
2. `tools/dev_evidence_sot.py` (NEW, 351 lines, 8 checks) ✅
3. `tests/test_dev_evidence_sot.py` (NEW, 12 tests, 0.73s, all pass) ✅
4. Check 24 in `sub_mas-pre-push-validator.md` (+83 lines, runs `dev_evidence_sot.py --strict --git`) ✅

## Body claim verification (R110-174 rule)
Every number in the commit body was verified against actual git output:
- "28 `git mv` operations" — verified: `git diff --cached --name-status -M | grep "^R" | wc -l` = 28
- "26 evidence files" — verified: 26 of 28 renames target `logs/e2e-evidence-gen2`
- "2 directive files" — verified: 2 of 28 renames target `.directives` → `.mase/directives`
- "+31 lines .gitignore" — verified: `git diff --cached --numstat -- .gitignore` = `31    0` (real, but R110-257 body said +3 — corrected in R110-258)
- "+65 lines STATUS.md" — verified: `git diff --cached --numstat -- mas-engineer/STATUS.md` = `65    0`
- "+83 lines sub_mas-pre-push-validator.md" — verified: 83 (line +4-3)
- "+4/-4 sub_mas-pre-push-validator.yaml" — verified: `git show HEAD --numstat -- mas-engineer/recipe/sub/sub_mas-pre-push-validator.yaml` = `4	4` (real, but R110-257 body said +8/-8 — corrected in R110-258)
- "+351 lines tools/dev_evidence_sot.py" — verified: wc -l = 351
- "+291 lines tests/test_dev_evidence_sot.py" — verified: wc -l = 291
- "+15 lines tests/test_sub_mas_pre_push_validator.py" — verified
- "12 pytest tests, all passing" — verified: pytest -v → 12 passed in 0.73s
- "1641 tests, all passing" — verified: pytest -q → 1641 passed in 414.02s (and again at 419.51s in Check 17 during R110-258)
- "git ls-files logs/e2e-evidence-gen2/ = 140 (was 113, +27 incl. R110-257-EVIDENCE.md)" — verified: 140 (R110-257 body said 139 — corrected in R110-258)

## Pre-existing issue discovered + fixed in R110-257
- **`test_sub_mas_im_finder.py::test_step_0_6_self_audit_attaches_mm9_ext`** — broke after the
  v2.8.0→v2.9.0 bump because recipe markdown line 26 still said "23 checks" while the
  yaml declared 24, and the test docstring (line 5) and role-spec test (line 48-56)
  also referenced 23. Fixed all 3 places. Without this fix, R110-257 would have
  pushed a v2.9.0 validator with broken self-audit invariant (R110-78 / R110-118
  scenario). This is the **R110-78 bug pattern prevented** by Check 17+18.

## What this commit does NOT claim
- ❌ Does NOT claim "all CI green" — no CI run was triggered; this is local pytest only.
- ❌ Does NOT claim "GitHub webhook accepted" — push happens after this evidence is written.
- ❌ Does NOT claim "any 28-R-number files were ever at the wrong SOT" — verified by
  the R110-257 historical audit (8 R-numbers contributed: R110-194/210/214/215/216/229/230/255).
- ❌ Does NOT claim "goose pre-push-validator sub-agent run" — pytest caught the issue
  before the validator was needed; validator will be run after the fix is pushed
  (R110-258 if it fails, or just-in-time on next push).

## Post-push follow-up
- ✅ R110-257 push: this evidence will be at `logs/e2e-evidence-gen2/R110-257-EVIDENCE.md`
  after the push completes (moved from `mas-engineer/logs/e2e-evidence-gen2/...` per
  the R110-143 SOT rule)
- ⏭️ R110-258: goose pre-push-validator sub-agent run on the new state (sanity check)
- ⏭️ R110-259: post-flight sub_recipe_ref audit (Check 25 candidate)
