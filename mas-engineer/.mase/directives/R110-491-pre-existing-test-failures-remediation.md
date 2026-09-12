# R110-491 — pre-existing test failures remediation (11 fails post-R110-481 refactor)

## Context

R110-481 refactor (large restructure of tools/ + tests/) re-emerged
11 pre-existing test failures in the cleanup-branch HEAD (f0691b4,
2026-09-12). These failures are pre-existing (not introduced by the
R110-480 coverage-push commit which is the commit ahead of origin).

Full-sweep evidence: `logs/e2e-evidence-gen2/R110-490-EVIDENCE.md`.
Pytest output: `/tmp/full_sweep.log` (last 100 lines show all 11 FAILED lines).

## The 11 failures (categorized)

### Category A — Test pollution (PASS individually, FAIL in full-sweep)
Root cause: tests modify shared state (`.mase/mq/*.ndjson`, `.state/pipeline/`)
that affects subsequent tests when run in same pytest process.

- `tests/test_dev_phase1_publishers.py::test_im_finder_publish_enqueues_message`
- `tests/test_dev_phase1_publishers.py::test_im_finder_without_publish_does_not_enqueue`
- `tests/test_dev_phase1_publishers.py::test_im_finder_uses_default_request_id_when_omitted`
- `tests/test_sub_mas_im_finder.py::test_step_0_6_self_audit_attaches_mm9_ext`

### Category B — Coverage-push test pollution (recent R-sprints)
Root cause: R110-470/R110-477 added tests that share module-reload state
with other tests in the same pytest session.

- `tests/test_r110470_dev_im_finder_scan_coverage.py::TestImportGuards::test_findings_proxy_returns_list_after_reload`
- `tests/test_r110477_dev_fast_scan_coverage.py::TestMain::test_main_default_cwd`

### Category C — SD-test detector drift (real failures, not pollution)
Root cause: R110-481 refactor moved/changed files; detector tests still
reference old paths/counts.

- `tests/test_dev_im_finder_scan_lib.py::test_sd_test_mase_integration_findings_reduced`
- `tests/test_pre_push_check_1_5_skill_alignment.py::test_check_1_5_origin_cleanup_recent_commits_match`
- `tests/test_r110259_category_drift_scope.py::test_r110257_subject_accepted_by_detector_in_real_git_history`
- `tests/test_r110279_runtime_var_skip.py::test_detector_finds_drift_for_synth_test`
- `tests/test_r110279_runtime_var_skip.py::test_detector_does_NOT_flag_runtime_var_assert`

## Goal

Restore the R110-401 baseline: 4331/4331 PASSED + 7 SKIPPED in ~1422s
(without --timeout=600 inflation). All 11 failures fixed, no new flakes
introduced, coverage on the affected tools remains ≥95%.

## Per-batch fix plan (R110-418 strategy)

| Batch | Tests | Strategy | Est time |
|-------|-------|----------|----------|
| 1 | 4 Category A tests | add fixture-level `.mase/mq/*.ndjson` cleanup + tmp_path isolation | 30 min |
| 2 | 2 Category B tests | refactor to use module-level fixtures instead of `importlib.reload` | 20 min |
| 3 | 5 Category C tests | update detector tests to match R110-481 file paths/counts | 45 min |
| 4 | 1 Category D test (q4c_recursion_guard_scanner_output_reduced) | investigate why inner subprocess exceeds 240s timeout on cleanup-worktree but passes on primary; likely .mase/mcp/node_modules scan bloat | 20 min |
| 5 | full-sweep verification | `pytest tests/ -q --tb=line --timeout=300 --ignore=.state` | 25 min |

Total estimated: ~2.5 hours.

## Verification (per batch)

- Per-batch: `pytest tests/test_<file>.py -v --tb=short --timeout=60`
- Full sweep: `python3 -m pytest tests/ -q --tb=line --color=no --timeout=300 --ignore=.state`
  - Expected: 6148 passed, 7 skipped, 0 failed in <1500s

## Pre-push gate

After R110-491 fix + verification, re-run pre-push-gate manually:
- Check 17 (pytest-run) → must show 0 failed
- Check 18 (spec-invariant) → must show 0 BLOCKER
- All other checks → unchanged from R110-480

## Status

OPEN — not started. Will be picked up as next sprint after R110-480 push lands.
