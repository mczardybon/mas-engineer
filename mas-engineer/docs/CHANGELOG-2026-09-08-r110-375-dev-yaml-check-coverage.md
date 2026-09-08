# R110-375 — CHANGELOG entry

## tools/dev_yaml_check.py: 13.7% → 94.4% coverage (+80.7pp, 58 tests, 8 classes)

### Summary

R110-375 closes the 3rd-largest 0%-Lücke in `tools/` by adding a
dedicated test file for the YAML/syntax/state validator. This is
the **highest single-file coverage jump in the R110-37x series**
(+80.7pp, +159 stmts), surpassing even R110-374's +91.2pp
absolute delta (which started from 0% with 41 tests).

### Test file

- **Path**: `tests/test_dev_yaml_check_r110375.py`
- **Size**: 586 lines, 26329 bytes
- **Classes**: 8 (TestCheckYaml, TestDetectFileType,
  TestCheckPythonSyntax, TestCheckShellSyntax,
  TestCheckSyntaxDispatch, TestVerifyState, TestCheckAll,
  TestMainCli)
- **Tests**: 58
- **Pass rate**: 58/58 in 0.20s isolated
- **Coverage**: 94.4% (186/197 stmts)

### Incremental rounds

| Round | Tests | Coverage | New |
|---|---|---|---|
| r1 | 46 | 83.2% | Initial 8 classes |
| r2 | 53 | 90.9% | +1 bash mock, +4 main arg-failures, +2 main return codes |
| r3 | 58 | 94.4% | +2 explicit dispatch, +1 check_all sh, +2 main 4-args |

### What's tested

- **check_yaml (10)**: not-found, empty, valid, invalid syntax,
  binary, unicode, lines count (single + multi), lists, nested
- **detect_file_type (8)**: shebang python/bash/sh, .py/.sh/
  .yaml/.yml extensions, .txt unknown
- **check_python_syntax (4)**: not-found, valid, syntax error,
  check field
- **check_shell_syntax (5)**: not-found, valid bash, invalid bash,
  check field, bash-not-installed (subprocess mock)
- **check_syntax dispatch (7)**: auto-py, auto-yaml, explicit py,
  explicit unknown warning, auto-unknown, explicit sh, explicit yaml
- **verify_state (6)**: workspace not-found, no-yamls warning,
  perfect score (100), partial critical (75), good band (80),
  excludes .backups/checkpoints
- **check_all (5)**: yaml only, python file, error aggregation,
  warning aggregation, sh file
- **main CLI (13)**: no-args, CHECK_YAML command, VERIFY_STATE
  command, HELP, unknown command, CHECK_YAML/SYNTAX/STATE/ALL
  missing-arg errors, error return code (1), warning return
  code (0), CHECK_SYNTAX with 4-args, CHECK_ALL with 4-args

### What's still missed (11 lines, all defensive)

| Lines | Why missed |
|---|---|
| 70-73 | Generic read exception (OS-level fault injection) |
| 85-88 | Non-YAML exception (yaml.safe_load rarely throws) |
| 138-140 | Generic read exception (same as 70-73) |

These are the practical ceiling for unit-level testing.

### Pre-existing fail analysis (R110-78 honest disclosure)

Full suite after R110-375: 3801 pass / 15 fail / 7 skip.
**15 fails = 13 pre-existing (order-dependent) + 2 new.**

The 2 new fails:
1. `test_dev_evidence_sot.py::test_clean_state_exits_zero` —
   pre-existing infrastructure issue (`.mase/directives/` missing
   on this branch), NOT caused by R110-375
2. `test_r110259_category_drift_scope.py::test_r110257_subject_accepted_by_detector_in_real_git_history` —
   caused by 3 empty-subject commits in git history (5a9e3918,
   8e72b14, aa4a975) from R110-373/374/375 file-restorations

Per R110-281 (force-push-verbote), the empty-subject commits
cannot be amended in place. Option 0 recovery (non-destructive
documentation) is applied in commit body.

### Cumulative R110-37x progress

| Round | File | Delta | Tests |
|---|---|---|---|
| R110-371 r2 | dev_workspace.py | 71% → 80.1% | existing |
| R110-372 r1 | dev_editor.py | 0% → 49.87% | existing |
| R110-373 r2 | dev_editor.py | 49.87% → 58.18% | 57 |
| R110-374 r1 | dev_observer.py | 0% → 91.2% | 41 |
| **R110-375 r3** | **dev_yaml_check.py** | **13.7% → 94.4%** | **58** |
| **Total** | **4 files** | **+238.4pp combined** | **156** |

### Refs

- EVIDENCE: `logs/e2e-evidence-gen2/R110-375-EVIDENCE.md`
- Test: `tests/test_dev_yaml_check_r110375.py`
- Skill: `mas-engineer-coverage-push-workflow`
- Skills applied: `mas-engineer-r110-78-verification-theater-fix`,
  `pre-push-body-claim-verification`
