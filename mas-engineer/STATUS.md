# MAS-Engineer STATUS.md — Sprint 2026-08-21

**Branch:** `mas-t` (only)
**HEAD:** `2cf5c30` (R110-235)
**Origin:** `https://github.com/mczardybon/mas-engineer.git`
**Sprint window:** 2026-08-21 (single-day sprint)
**Last update:** 2026-08-21 (R110-235 + R110-235a finalisiert)

---

## R-codes 2026-08-21 (consolidated)

This single-day sprint produced 10 R-codes (R110-225..234 + 235
post-push doc-sync + 235a gap-closure). Each is a single commit.
All are on `origin/mas-t` (235 + 235a pending).

### Pushed (9 R-codes, 9 commits)

| SHA     | R-num   | type | subject                                                            | stat           | CHANGELOG                |
|---------|---------|------|--------------------------------------------------------------------|----------------|--------------------------|
| ce1eaac | R110-225 | docs | 17 .mase/skills "When to use" header                               | 17 f, +136    | CHANGELOG-2026-08-21-r110-225-229.md |
| 74c29e4 | R110-226 | test | 5 tests theater-fix refactor (DETECT not BLOCK)                    | 6 f, +229/-229 | CHANGELOG-2026-08-21-r110-225-229.md |
| 36b7cdc | R110-227 | docs | sub_mas-master-constitution-team Boundaries + .mase/todo.md        | 2 f, +18       | CHANGELOG-2026-08-21-r110-225-229.md |
| c1182aa | R110-228 | fix  | sub_mas-clone placement + drift-detector exempt                    | 3 f, +16/-1    | CHANGELOG-2026-08-21-r110-225-229.md |
| 412df84 | R110-229 | docs | transparency follow-up                                             | 1 f, +80       | CHANGELOG-2026-08-21-r110-225-229.md |
| f1d6906 (R110-230) | fix  | .mase/workflows.yaml SOT consistency (clone agent task_workflows)  | 1 f, +1/-1     | ✅ r110-230-232.md (R110-235a)     |
| 2b4ae7d (R110-231) | fix  | body-claim correction (R110-78 pattern)                             | 1 f, +26/-0    | ✅ r110-230-232.md (R110-235a)     |
| ecfdbf9 (R110-232) | fix  | sub_mas-clone permanent removal (from dev-mas-engineer + mas-self) | 5 f, +18/-168  | ✅ r110-230-232.md (R110-235a)     |
| c39d2e7 | R110-233 | fix  | gitignore stub-cleanup + dev_changes.py list→dict migration        | 5 f, +85/-44  | CHANGELOG-2026-08-21-r110-233-234.md |
| 1332c96 | R110-234 | docs | CI pipeline: pytest matrix + e2e-smoke on mas-t                    | 2 f, +158/-0  | CHANGELOG-2026-08-21-r110-233-234.md |
| 2cf5c30 | R110-235 | docs | post-push doc-sync (CHANGELOG-2026-08-21-r110-233-234 + STATUS.md) | 2 f, +355/-0  | CHANGELOG-2026-08-21-r110-233-234.md |

### CHANGELOG-coverage gaps (disclosed)

- **R110-230:** ✅ documented in `docs/CHANGELOG-2026-08-21-r110-230-232.md`
  (R110-235a, 2026-08-21 14:36). Original commit a8f453e.
- **R110-231:** ✅ documented in `docs/CHANGELOG-2026-08-21-r110-230-232.md`
  (R110-235a). Original commit 2b4ae7d. R110-78 pattern
  body-claim correction.
- **R110-232:** ✅ documented in `docs/CHANGELOG-2026-08-21-r110-230-232.md`
  (R110-235a). Original commit ecfdbf9. sub_mas-clone permanent
  removal.
- **R110-233 + R110-234:** fully documented in
  CHANGELOG-2026-08-21-r110-233-234.md (this sprint).

### Action: CHANGELOG consolidation for R110-230..232 → DONE (R110-235a)

Closed 2026-08-21 14:36: `docs/CHANGELOG-2026-08-21-r110-230-232.md`
shipped (176 lines, 5-section per R, +18/-168 e2e-result, R110-185
defib-PTY section). All 3 R-codes now have explicit documentation
matching the R110-225..229 + R110-233..234 convention. The pre-push-
gate 100%-gap-closure verified by hand: every R-code in the
R-sprint-table now has ✅ in the CHANGELOG column.

---

## Pre-push-gate status (all greens for R110-233 + R110-234)

| Step | What | Result for R110-233 + R110-234 |
|------|------|-------------------------------|
| 0    | secret scan (tracked + untracked + history) | OK 0 echte secrets |
| 1    | e2e-test.sh (11 checks)                      | ✅ 11/11 PASS (twice) |
| 1b   | goose sub_mas-pre-push-validator             | ✅ 23/23, 133/133 e2e, 1622/1622 pytest (outer 480s timeout, R110-69 pattern) |
| 2    | pytest tests/ (independent)                  | ✅ 1629/1629 in 434s |
| 3    | commit-msg 🔧/📚 R-format + body-claims     | ✅ both green, 5-section body |
| 4    | push (credential-helper, 0 leak)             | ✅ 2cf5c30 (R110-235) mas-t → mas-t |
| 5    | post-flight audit                            | ✅ 3 checks green, no secrets in pushed content |

---

## CI-Pipeline status (R110-234, first-activation pending)

- **ci-tests.yml:** defined, not yet activated (next push to mas-t)
  Expected: pytest matrix 3.11+3.12, ubuntu, 8min timeout, 0 cost
- **ci-e2e-smoke.yml:** defined, not yet activated (next push to mas-t)
  Expected: scripts/e2e-test.sh, ubuntu, 5min timeout, 0 cost,
  DEEPSEEK_API_KEY="" → goose-step skipped
- **Compat:** both workflows have `if: github.actor != 'github-actions[bot]'`
  → respects block-copilot.yml + ai-pipeline-kill-switch.yml
- **Cost:** $0 external API (deepseek NUR lokal pre-push)

---

## E2E FULL RUN status (post-push verification)

**Background process:** `proc_23f08e42022a` (last attempt; retried
proc_148587117a48 cwd-crash + proc_6f2242cd2210 --no-interactive, both
also blocked on same defib test)
**Started:** 2026-08-21 14:17:19 (immediately after R110-234 push)
**Command:** `MAS_AUTO_CONFIRM=1 python3 tools/e2e_run_all.py --auto-confirm`
**Workdir:** `mas-engineer/` (correct on retry 1+; proc_148587117a48 crashed
from wrong cwd in retry 0)
**Result:** PARTIAL — **132/132 reachable tests PASS (100%); 1 blocked
(wf_recovery_defib needs PTY which non-PTY background terminal can't
provide); 67 not reached (TEST 4 + 5)**. Confirmed deterministic by
3 attempts (proc_148587117a48 cwd-crash, proc_23f08e42022a default,
proc_6f2242cd2210 --no-interactive) all reach the same defib-block
at the same test number. `--no-interactive` only skips the
`goose run --explain` interactive prompt at TEST 5, NOT the
auto-repair codepath used by recovery workflows.
**Output dir:** `logs/e2e-results/2026-08-21-run-3/` (dir was empty —
runner writes raw-results.json only on full completion; defib hang
prevented that)
**Root cause for defib:** `bash: [325135: 1 (255)] tcsetattr:
Inappropriate ioctl for device` = goose auto-recipe needs PTY,
background terminal session is non-PTY. NOT a regression.
Deterministic: 3 attempts (proc_148587117a48, proc_23f08e42022a,
proc_6f2242cd2210 --no-interactive) all blocked at the same defib
test with the same tcsetattr error. `--no-interactive` flag does NOT
help here (it only skips `goose run --explain` at TEST 5, not the
recovery-workflows' auto-repair).
**Verdict:** NOT a regression. Pre-push-gate (e2e-test.sh 11/11 +
pytest 1629/1629 + validator 23/23 with 133/133 e2e-recipes) is the
definitive verification — all green. e2e_run_all.py 71-test deep run
is supplementary; defib-pty-block is environmental, not code.

**E2E FULL RUN details:** see CHANGELOG-2026-08-21-r110-233-234.md
"## E2E FULL RUN" section for the full TEST-by-TEST breakdown
(TEST 1: 125 yaml OK; TEST 2: 3 top workflows OK; TEST 3: 4/5
recovery OK + defib blocked).

---

## Working tree status

```
$ git status -s
(empty — clean)
$ git log --oneline -3
2cf5c30 (HEAD -> mas-t, origin/mas-t) R110-235 docs: post-push doc-sync (CHANGELOG-2026-08-21-r110-233-234 + STATUS.md)
1332c96 R110-234 docs: CI pipeline
c39d2e7 R110-233 fix: gitignore stub-cleanup
```

---

## Memory + skills (R110-233/234 patterns persisted)

- `~/.hermes/memories/MEMORY.md` updated with R110-233 + R110-234 facts
- `~/.hermes/skills/devops/mas-engineer-cleanup-sprint/SKILL.md` —
  5-category noise diagnosis, `git rm --cached`, ACMRT-filter,
  dev_changes.py list→dict migration, 2-repo path-trap, pre-push-gate
  3-step pattern. Reusable for next cleanup-sprint.
- `~/.hermes/skills/devops/mas-engineer-ci-pipeline-template/SKILL.md` —
  2-workflow pattern (pytest matrix + e2e-shell harness), Copilot-guard,
  DEEPSEEK_API_KEY=*** goose-skip, permissions zero-trust. Reusable for
  next CI addition.

---

## R110-252 + R110-253 (2026-08-22, mas-t) — CI-local-validation + e2e-false-positive cleanup

**Commits:**
- `c9ede3f` 🔧 R110-252 — feat: scripts/ci-validate.sh mirrors GHA CI locally (CI gap R110-241 audit)
- `ed890da` 🔧 R110-253 — fix: e2e-test.sh [5/10] doc-links + [6/10] german-words 2 false-positives

**Why these commits exist:** R110-241 surfaced 4 GHA-CI local-bypass gaps
(trivy-action v0.30.0 transitive dep R110-246, codeql-action network dep,
upload-sarif GHA-only, cache GHA-only). R110-252 builds `scripts/ci-validate.sh`
(518 lines, NEW) that runs those same checks locally without GHA dependencies,
and wires it into e2e-test.sh as the new [11/11] step.

**After R110-252 the e2e --all run surfaced 2 pre-existing fails** that
nobody had run end-to-end on this branch before:
1. [5/10] doc-links false-positives: regex `r'\]\(([^)]+)\)'` matched Python
   raw-strings (4 files in .mase/directives/ + .mase/skills/)
2. [6/10] german-words: 4 violations in 2 files
   (sub_mas-yaml-editor.md L16-17, sub_mas-self-audit.yaml L5+L7)

R110-253 fixed both by extracting `scripts/_strip_code.py` (68L) +
`scripts/_check_doc_links.py` (97L) as standalone modules, using a stricter
regex `\[([^\]\n\\"\'`]{2,}?)\]\(([^\)\n\\"\'`]+)\)` that requires [text]
and (url) to be ≥2 chars and not contain Python-source-like chars.

**Net file change:** R110-252 = 1 file +518/-0. R110-253 = 5 files
+240/-49 (2 new modules + 3 modified: e2e-test.sh, sub_mas-yaml-editor.md,
sub_mas-self-audit.yaml).

**E2E --all result (reproducible, DEEPSEEK_API_KEY set):**
```
[5/10] Doc links (scope: all)
  PASS: Doc links — all resolve
[6/10] German words (scope: all)
  PASS: German words — 0 violations
...
[11/11] CI workflow validation (R110-252)
  PASS: CI workflow validation — see /tmp/ci-validate.out
  CI VALIDATE RESULT: 3 PASS, 0 FAIL, 1 SKIP
================================================================
E2E RESULT: 12 PASS, 0 FAIL, 0 SKIP
================================================================
ALL CHECKS PASS (or SKIP). Safe to push.
```

The 1 SKIP is the pip-dry-run transitive-dep check (R110-246 pattern) —
mas-engineer deliberately declares Python deps inline in GHA workflows,
not in a requirements.txt; documented as known SKIP, not fail.

**Evidence files:**
- `logs/e2e-evidence-gen2/R110-252-EVIDENCE.md`
- `logs/e2e-evidence-gen2/R110-253-EVIDENCE.md`
- `mas-engineer/docs/CHANGELOG-2026-08-22-r110-252-253.md`

**Working tree status (post-push):**
```
$ git log origin/mas-t --oneline -3
ed890da (HEAD -> mas-t, origin/mas-t) 🔧 R110-253
c9ede3f 🔧 R110-252
9caaf59 🔧 R110-251
$ git status -s
(empty — clean)
```

**Memory + skills (R110-252+253 patterns to be persisted):**
- TODO: `~/.hermes/skills/devops/mas-engineer-commit-protocol/SKILL.md` —
  add "After every 🔧 R-sprint: write evidence file in logs/e2e-evidence-gen2/,
  append STATUS.md section, write CHANGELOG-<date>.md" as mandatory step
  before push (R110-126 protocol was missing this — R110-252+253 are the
  first commits that did it right, prior commits left it as a post-hoc
  documentation gap)
- TODO: `~/.hermes/skills/devops/mas-engineer-workflow/SKILL.md` — add
  e2e-test.sh [5/10] refactor as a reusable pattern (inline heredoc →
  2 standalone modules when check grows beyond ~30 lines)

---

## R110-255 (2026-08-22) — Check 17 timeout + duration spec retire

**Type:** fix
**Files changed:** `recipe/instructions/sub_mas-pre-push-validator.md` (+24/-3)

**What:** Pre-push-validator Check 17 now uses `pytest --timeout=300 --ignore=.state`
to match `ci-tests.yml` (R110-246). The R110-95 duration spec (9.65s) is RETIRED
because R110-239 added 4 phoenix tests @ 75s each; new R110-255 baseline is
7-7.5 min local, 14-15 min GHA.

**Verification:**
- `python3 -m pytest tests/ -q --tb=line --color=no --timeout=300 --ignore=.state` → 1629 passed in 7m 6s
- `python3 -m pytest tests/test_dev_phoenix_recovery_publish.py -v --timeout=300` → 9 passed in 4m 58s
- ci-tests.yml R110-254 (pre-fix measurement): 14m 32s, SUCCESS

**Evidence:** `logs/e2e-evidence-gen2/R110-255-EVIDENCE.md` (8065 bytes)
**Changelog:** `docs/CHANGELOG-2026-08-22-r110-255.md` (4812 bytes)

**Root cause:** User correctly pointed out that the timeout had to be set higher
(verbatim German user quote translated to English per LANGUAGE-RULE R110-172+173;
original in commit message body and R110-255-EVIDENCE.md). I had used
`--timeout=60` for local validation, producing 4 false-positive failures.
Investigation revealed the R110-95 spec was pre-phoenix (1277 tests) and is
now ~40× wrong.

## R110-257 (2026-08-26, mas-t) — Evidence/Directive SOT-location cleanup + Check 24

**Type:** fix (SOT consolidation) + feat (Check 24 prevention)
**Files changed:** 28 `git mv` (renames, history-preserved) + `.gitignore` (+3/-0) + `tools/dev_evidence_sot.py` (NEW, 411 lines) + `tests/test_dev_evidence_sot.py` (NEW, 12 tests, all passing) + `recipe/instructions/sub_mas-pre-push-validator.md` (+82/-0, +Check 24) + `recipe/sub/sub_mas-pre-push-validator.yaml` (v2.8.0 → v2.9.0, +Check 24 in description+prompt)

**What:** DETECTION→CORRECTION→PREVENTION cycle for the persistent
evidence/directive SOT-drift bug class. Three PREVENTION layers added.

**CORRECTION (28 `git mv` operations, history preserved):**
- 2 directives: `mas-engineer/.directives/R110-{217,218}.md` → `mas-engineer/.mase/directives/` (R110-115 DIREKTIVE 1 SOT)
- 26 evidence files: `mas-engineer/logs/e2e-evidence-gen2/` → `logs/e2e-evidence-gen2/` (R110-143 REPO-ROOT SOT) — covers R110-194/210/214/215/216/229/230/255
- Both `mas-engineer/.directives/` and `mas-engineer/logs/` now empty/removed (would-be recreated as dir entries, no commit history impact)

**PREVENTION layer 1 — .gitignore:** `mas-engineer/.directives/` and
`mas-engineer/logs/` (with `**` recursive) blocked. Verified:
`git check-ignore mas-engineer/.directives/R110-X.md` → matched (line 233),
`git check-ignore mas-engineer/logs/foo.log` → matched (line 238).

**PREVENTION layer 2 — `tools/dev_evidence_sot.py` (NEW, 411 lines):**
Standalone checker with 8 checks (4 working-tree + 2 git-index + 2
dir-health + history-scan). Flags `.gitignore`-excluded files too
(key design choice — they're invisible to git status but the tool
still catches them). Modes: `--strict` (CI exit codes), `--git`,
`--history`, `--json`. Tested standalone:
- clean state → exit 0
- intentional violation in `mas-engineer/.directives/` → exit 1
- intentional violation in `mas-engineer/logs/` → exit 1
- missing SOT dir → exit 1

**PREVENTION layer 3 — `tests/test_dev_evidence_sot.py` (NEW, 12 tests, all passing):**
Regression test suite covers (a) clean state, (b-c) violations at both
anti-SOT locations, (d) cleanup → restored clean, (e) JSON schema,
(f) --git mode, (g) --history scan, plus 2 dir-health tests.
`python3 -m pytest tests/test_dev_evidence_sot.py -v` → 12 passed in 0.73s.

**PREVENTION layer 4 — Check 24 in pre-push-validator (R110-257, NEW v2.9.0):**
The 24th check in the pre-push gate. Runs `tools/dev_evidence_sot.py --strict --git`,
BLOCKS the push if any file is at anti-SOT location. Wired into both
the recipe yaml (description + prompt + version bump 2.8.0 → 2.9.0) and
the external instructions file (full 82-line block following the Check 23
template: Goal + DETECTION→CORRECTION→PREVENTION history + idempotency
note + bash block + output blocks on PASS/BLOCK + Reference section).

**Verification:**
- `python3 mas-engineer/tools/dev_evidence_sot.py --git --strict` → exit 0, RESULT: ✅ PASS — no SOT violations
- `python3 -m pytest tests/test_dev_evidence_sot.py -v` → 12 passed in 0.73s
- `python3 -c "import yaml; print(yaml.safe_load(open('mas-engineer/recipe/sub/sub_mas-pre-push-validator.yaml'))['version'])"` → 2.9.0
- `git ls-files logs/e2e-evidence-gen2/ | wc -l` → 139 (was 113, +26 from R110-257 renames)
- `git ls-files mas-engineer/.directives/ 2>/dev/null | wc -l` → 0 (was 2)
- `git ls-files mas-engineer/logs/ 2>/dev/null | wc -l` → 0 (was 26)
- `git check-ignore mas-engineer/.directives/R110-999.md mas-engineer/logs/test.log` → both matched (exit 1, "ignored")

**Evidence:** `logs/e2e-evidence-gen2/R110-257-EVIDENCE.md` (created at push)
**Changelog:** `docs/CHANGELOG-2026-08-26-r110-257.md` (created at push)

**Root cause (accumulated over 8 R-numbers):** Every SOT-violating file
landed via "natural" session workflows — directives were created in
the wrong dir because the old `dev_directive_applier.py` default was
`mas-engineer/.directives/` (later changed to `.mase/directives/` per
R110-115, but the old default left orphan files), evidence files were
created in `mas-engineer/logs/e2e-evidence-gen2/` because that was the
ORIGINAL SOT before R110-143 (2026-08-15) moved the SOT to REPO-ROOT.
R110-257 is the first commit that does BOTH the bulk cleanup AND
installs a permanent prevention (3 layers + Check 24 in the gate).

---

## R110-261 (2026-08-27) — Coverage Sprint for 10 simple tools

**Branch:** `mas-t-tests`
**HEAD:** R110-261 (pending push)
**Type:** test
**Type-emoji:** 📊
**Changelog:** `docs/CHANGELOG-2026-08-27-r110-261.md`
**Evidence:** `logs/e2e-evidence-gen2/R110-261-EVIDENCE.md`

### Summary

The coverage improvement sprint R110-260's commit body predicted as
"follow-up: R110-261". Adds 88 direct library-function tests for 10
importable `tools/dev_*.py` modules across 3 new test files.

### Numbers (all verified pre-commit)

| Metric | R110-260 baseline | R110-261 result |
|--------|-------------------|-----------------|
| Test count | 1667 | 1755 (+88) |
| Test files | (existing) | +3 new |
| New tests green | n/a | 88/88 |
| Full suite green | 1667/1667 | 1755/1755 |
| Full suite wallclock | ~7m 30s | 7m 03s |
| e2e-test.sh | 12/12 | 12/12 |
| pre-push-validator | Check 1-16+ pass | Check 1-16+ pass (Check 17 = 1755/1755) |
| .mase/pre-push-test-coverage tests | 126 | 169 |
| .mase/pre-push-test-coverage ratio | 1.10 | 1.47 |
| .mase/pre-push-e2e-baseline baseline_pass | 83 | 133 |

### Tools covered (10/10 simple library-importable tools)

1. dev_evidence_sot (Round 1, +17 tests)
2. dev_dashboard_data (Round 1)
3. dev_architecture_checker (Round 2, +32 tests)
4. dev_audit_deps (Round 2)
5. dev_auto_project (Round 2)
6. dev_editor_large (Round 2)
7. dev_fast_scan (Round 3, +39 tests)
8. dev_haerte_propagation (Round 3)
9. dev_intention_parser (Round 3)
10. dev_category_drift (Round 3)

### Library-bugs found (NOT fixed here, tracked as R110-261a)

- dev_fast_scan: score=20 (not 10) for 2-pass/1-file
- dev_intention_parser: requires_confirmation only at restrictions[...]
- dev_category_drift: commit-shape is {hash,date,subject} not {message,files}

### Diff stat (R110-261)

```
 tests/test_r110261_tools_coverage.py        | 222 ++++++
 tests/test_r110261_tools_coverage_round2.py | 331 ++++++++
 tests/test_r110261_tools_coverage_round3.py | 430 +++++++++++
 .mase/pre-push-e2e-baseline.json            |  17 +++--
 .mase/pre-push-test-coverage.json           |  12 +++--
```

### Why not push the 80% gate up to ~30%?

The remaining un-tested tools (dev_workspace, dev_im_finder_scan,
dev_template_generator, dev_directive_applier, etc.) are CLI-arg
driven and need real-subcommand subprocess tests with tmp_path +
mocked I/O, not library tests. R110-261 is scope-limited to the
library-importable 10. A future sprint (R110-262) will do the
subprocess-test expansion.

### R110-261a (2026-08-27) — Library-Bug-Fixes revealed by R110-261

**Branch:** `mas-t-tests`
**HEAD:** R110-261a (pending push)
**Type:** fix
**Type-emoji:** 🔧
**Depends on:** R110-261 (cdaf2a1)
**Changelog:** `docs/CHANGELOG-2026-08-27-r110-261a.md`
**Evidence:** `logs/e2e-evidence-gen2/R110-261a-EVIDENCE.md`

#### Summary

R110-261's coverage-sprint revealed 2 real library-bugs and 1
docstring/test-shape issue. R110-261 declared them "tracked as
R110-261a" and out-of-scope. R110-261a is the fix-up commit.

#### Bugs fixed

1. **dev_fast_scan.scan_settings** (tools/dev_fast_scan.py):
   per-condition `ok` counter → per-file pass/fail, cap at 10.
   - 1 perfect file: 20.0 → 10.0 ✅
   - 1 half-good file: 10.0 (misleading) → 0.0 ✅
   - 20 perfect files: uncapped → capped at 10.0 ✅
   - Findings B1/B2/B3/B4 still emitted per-condition (unchanged)

2. **dev_intention_parser.analyse_intention**
   (tools/dev_intention_parser.py): `requires_confirmation` now
   also exposed at top-level as alias for
   `restrictions["requires_confirmation"]`. Backward-compat;
   restrictions[...] remains authoritative.

#### Test updates (R110-261a required)

- 2 existing tests in tests/test_tools_framework.py
  (`test_scan_settings_high_timeout_low_severity` and
  `test_scan_settings_optimal_scores_full`) were updated to
  assert the post-fix per-file pass/fail math. They previously
  documented the bug as a "known quirk"; they now document
  the fix.

#### Numbers (verified pre-commit)

| Metric | R110-261 baseline | R110-261a result |
|--------|-------------------|------------------|
| Test count | 1755 | 1764 (+9 new regression tests in test_r110261a) |
| All tests green | 1755/1755 | 1764/1764 (incl. updated test_tools_framework) |
| e2e-test.sh | 12/12 | 12/12 |
| dev_fast_scan 1 good file score | 20.0 (bug) | 10.0 ✅ |
| dev_intention_parser top-level requires_confirmation | KeyError | True ✅ |

#### Diff stat (R110-261a)

```
 tests/test_r110261a_library_bug_fixes.py | 131 ++++++++++++
 tests/test_tools_framework.py            |  22 ++--
 tools/dev_fast_scan.py                   |  21 ++-
 tools/dev_intention_parser.py            |   8 +-
 4 files changed, 211 insertions(+), 18 deletions(-)
```

#### Why R110-261a is a separate commit (not folded into R110-261)

1. **Commit hygiene** — R110-261 = test-only, R110-261a = test+source.
2. **Bisect-ability** — clean isolation if the fix breaks something.
3. **Pre-push-gate body-claim pattern (R110-78 / R110-258)** — split
   "tests reveal bug" from "tests pass after fix".
