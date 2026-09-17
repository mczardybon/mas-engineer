# R110-356 Evidence — workspace coverage-push round 3 (Prio-2)

## 1. Why

R110-323+ coverage-push queue, Prio-2 (workspace).
R110-355 continues the workspace push after R110-351/353
brought the testable surface from 0% to 31%.

## 2. R110-355 (5065fcb) — Round 3: cmd_project_* functions

### 2.1 Strategy
Target the 6 cmd_project_* functions (L1064-1242, ~178
lines).  These are pure functions reading/writing
`framework/.projects.yaml` and manipulating
`framework/<name>/` directories + `framework/current`
symlink.

### 2.2 6 function groups targeted, 22 tests, 6 test classes

**TestCmdProjectList (5 tests)** — covers `cmd_project_list`
(L1064-1074).  Branches:

  - empty projects dict → just header
  - 1 project → listed with name
  - 3 projects → all listed + total=3
  - active project marker ("<- active")
  - unknown status still listed (weiss fallback)

All 5 PASS.

**TestCmdProjectCreate (5 tests)** — covers
`cmd_project_create` (L1077-1124).  Branches:

  - name exists already → no-op (no overwrite)
  - create without copy_from → subdirs + config.yaml + symlink
  - create with copy_from → shutil.copytree from existing
  - copy_from not found → no-op + error
  - newly created project becomes active

All 5 PASS.

**TestCmdProjectSwitch (2 tests)** — covers
`cmd_project_switch` (L1126-1144).  Branches:

  - name not found → no-op + shows list
  - switch updates active + symlink

Both PASS.

**TestCmdProjectShow (2 tests)** — covers
`cmd_project_show` (L1146-1157).  Branches:

  - name not found → no-op
  - show prints all fields (label/type/agents/tests/status)

Both PASS.

**TestCmdProjectDelete (4 tests)** — covers
`cmd_project_delete` (L1159-1184).  Branches:

  - dev-team protected (cannot be deleted)
  - name not found → no-op
  - existing project moved to .trash/ + removed from yaml
  - deleting active project → active becomes dev-team
    + symlink updated

All 4 PASS.

**TestCmdProjectRename (4 tests)** — covers
`cmd_project_rename` (L1186-1209).  Branches:

  - old not found → no-op
  - new exists already → no-op
  - rename ok → dir renamed + config updated
  - renaming active → active becomes new + symlink updated

All 4 PASS.

### 2.3 Result

| Metric | R0 | R1 | R2 | R3 |
|---|---|---|---|---|
| Lines covered | 0 / 595 | 95 / 595 | 187 / 595 | 290 / 595 |
| Coverage % | 0% | 16% | 31% | 49% |
| Tests | 0 | 25 | 53 | 75 |
| Tests runtime | n/a | 0.19s | 0.97s | 0.74s |

## 3. Cross-batch regression

```
$ python3 -m pytest tests/test_r110351_workspace_coverage_push_r1.py \
                    tests/test_r110353_workspace_coverage_push_r2.py \
                    tests/test_r110355_workspace_coverage_push_r3.py \
                    --cov=dev_workspace --cov-report=term
75 passed in 0.74s
TOTAL                      595    305    49%
```

- 25 prior R110-351 tests: still PASS
- 28 prior R110-353 tests: still PASS
- 22 new R110-355 tests: all PASS
- Coverage report: 49% (was 31%)

## 4. Honest assessment

Round 3 is +18pp on 595 testable stmts.  This is the
largest single-round yield so far.  Remaining ~51% are
heavier functions (cmd_init YAML, cmd_doctor_init,
cmd_test, cmd_wf_test, cmd_create_skill, cmd_install_pkg,
cmd_search_*).

Round 4 plan: cmd_init YAML-generating branches (L79-126,
47 lines) + cmd_create_skill (L1245-1286, ~42 lines).
Expected yield: 49% → 60%.

## 5. Body-claim-drift audit (R110-305 protocol)

All claims verified:
  - "22 new tests" → 22 test_ methods: ✓
  - "6 test classes" → 6 Test* classes: ✓
  - "31% → 49% (+18pp)" → coverage report: ✓
  - "75/75 PASS in 0.74s" → pytest output: ✓
  - "290/595 stmts covered" → coverage report: ✓

## 6. R110-323+ queue status

Prio-1 (im_finder_scan, 1660 lines): DONE
  - 25% → 30% (+5pp, 34 lines newly covered)
Prio-2 (workspace, 1478 lines): IN PROGRESS
  - R1 (R110-351): 0% → 16% (+16pp) ✓
  - R2 (R110-353): 16% → 31% (+15pp) ✓
  - R3 (R110-355): 31% → 49% (+18pp) ✓
  - R4: 49% → 60% (cmd_init, cmd_create_skill, cmd_test)
Prio-3 (template_gen, 901 lines): queued
Prio-4 (dashboard, 566 lines): queued

## 7. References

- R110-322 (f4f8b3a) — coverage pattern documentation
- R110-323 — coverage-push queue
- R110-333 (f14be8c) — Prio-2/3/4 R-sprint plan
- R110-345/346/347/348/349/350 — Prio-1 im_finder_scan
- R110-351 (6ece410) — workspace round 1
- R110-352 (2160da2) — R1 EVIDENCE
- R110-353 (1295413) — workspace round 2
- R110-354 (dd7d1ca) — R2 EVIDENCE
- R110-309/324 — prior workspace tests
- R110-296/297 — 5-category commit protocol
- R110-78 — verification-theater guard
- R110-281 — force-push-VERSBOT
- R110-92 — drift detector
- R110-305 — 4-round numstat body-claim audit
- R110-258 — .mase/ + logs/ .gitignored + force-add pattern
- R110-318 — R-code → R-evidence pair pattern
