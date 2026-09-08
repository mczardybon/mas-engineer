# R110-377 EVIDENCE: tests/test_dev_agent_doctor_r110377.py

**Date:** 2026-09-08
**Branch:** mas-t-tests
**Tool under test:** `tools/dev_agent_doctor.py` (359 LOC)

## Goal

Achieve high coverage of `tools/dev_agent_doctor.py` with a self-catching pytest
suite that documents behaviour for every public function and CLI mode, and
exercises the realistic interactions between scanner, fix and apply-lessons
phases.

## Test suite

* **File:** `mas-engineer/tests/test_dev_agent_doctor_r110377.py`
* **Lines:** 1178
* **Test functions (def):** 77
* **Parametrized expansions:** 3 (print helpers) → 80 total tests
* **Classes:** 17

| #  | Class                       | Coverage target                                 |
| -- | --------------------------- | ----------------------------------------------- |
|  1 | TestGetFrameworkPath        | `get_framework_path` (3 cases)                  |
|  2 | TestSetFrameworkPath        | `set_framework_path` (2 cases)                  |
|  3 | TestPrintHelpers            | ok/warn/info/err → ok/ng (3 parametrized)       |
|  4 | TestLoadBestPractices       | load YAML, missing file, malformed YAML         |
|  5 | TestFindFrameworkAgents     | recipe discovery + extension filtering          |
|  6 | TestScanAgent               | 7 check types (F-OK, P-OK, R-RANGE, R-EXISTS,    |
|    |                             | R-CONTAINS, P-LEN, P-EXISTS)                     |
|  7 | TestFullScan                | scan across all agents, filter by --agent       |
|  8 | TestShowReport              | JSON output, text output, empty results         |
|  9 | TestAutoFix                 | 3 fix types: missing-section, missing-file,     |
|    |                             | missing-key                                     |
| 10 | TestWatchMode               | iteration behaviour                             |
| 11 | TestExportReport            | --export writes JSON                             |
| 12 | TestFindMasAgents           | MAS sub-recipe discovery                        |
| 13 | TestCheckMasAgent           | 7 MAS checks C1-C7                              |
| 14 | TestApplyLessons            | missing BP, no MAS agents, agent filter skip     |
| 15 | TestShowApplyReport         | plain + JSON output                             |
| 16 | TestMain                    | 12 CLI scenarios                                 |
| 17 | TestIntegrationSmoke        | scan + auto-fix + report dry-run                |

## Results (REAL, from re-derivation run on 2026-09-08)

```
$ python3 -m pytest tests/test_dev_agent_doctor_r110377.py --tb=no -q
........................................................................ [ 90%]
........                                                                 [100%]
80 passed in 0.36s
```

```
$ python3 -m pytest tests/test_dev_agent_doctor_r110377.py --tb=no -q \
    --cov=tools --cov-report=term
tools/dev_agent_doctor.py               359      3    99%   25-26, 248
80 passed in 3.21s
```

## Coverage analysis

* **359** statement total
* **3** missed lines
* **99%** coverage

Missed lines (all marginal / defensive paths):

* `25-26` — `ImportError` fallback when `yaml` package is missing. Cannot
  be tested without breaking the import. Hard-fault import is exercised
  by importing the module at collection time (it succeeds).
* `248` — `err("recipe file disappeared during scan")` in `main()`. Race
  condition between `find_recipes()` and `read_text()`. Not reproducible
  in a unit test without monkey-patching `Path.read_text` to raise on
  demand (which would also obscure intent).

## Self-catching evidence

The suite is self-catching: every check and every fix path in
`dev_agent_doctor.py` is exercised by at least one test. Removing the
`auto_fix` block makes `test_auto_fix_*` fail. Removing the `apply_lessons`
block makes `test_apply_lessons_*` fail. Removing a check from
`scan_agent` makes the corresponding `TestScanAgent.test_*_check` test
fail. The suite therefore guards against regression at the function
level, not just line level.

## Pre-existing fixes in scope of R110-377

The pre-existing SOT-tool failure was also fixed in this worktree:

1. `mas-engineer/.mase/directives/` was missing (R110-257 leftover).
   Created. Standalone `tools/dev_evidence_sot.py --git --strict` now
   reports `RESULT: ✅ PASS`.
2. The `cleanup/mas-engineer/.mase/` and `cleanup/.mase/` path trap was
   identified and documented in MEMORY (Monorepo-Path-Trap update).

## What was NOT done

* `test_dev_evidence_sot.py::test_clean_state_exits_zero` still reports
  violations when invoked from pytest (vs. standalone PASS). The diff is
  in the `cwd` resolution of `REPO_ROOT` inside the test runner. The
  standalone tool is correct and passes. This is a separate test-fixture
  problem, not in R110-377 scope.

## Files changed

* `mas-engineer/tests/test_dev_agent_doctor_r110377.py` — **NEW** (1178
  lines, 80 tests)
* `mas-engineer/.mase/directives/.gitkeep` — **NEW** (empty-dir marker,
  SOT-requirement)
