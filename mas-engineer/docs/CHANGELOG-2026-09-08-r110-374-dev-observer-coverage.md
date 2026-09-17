# R110-374 — tools/dev_observer.py coverage push r1 (0% → 91%)

## TL;DR

R110-374 targets the 5th-largest 0%-Lücke in `tools/`: `dev_observer.py`
(432 lines, 8 public functions/classes, 0% covered). The test file
`tests/test_dev_observer_r110374.py` (490 lines, 41 tests, 7 classes)
brings coverage from 0% to **91.2%** (+258 stmts covered, 25 still-missed).

The 25 still-missed lines are in `main()` arg-parser error paths and
unreachable defensive code (chmod-0 / corrupt-yaml fallbacks). A r2
would require subprocess-bad-arg tests to push toward 100%.

## Test Plan (7 classes, 41 tests)

| Class | Tests | Target |
|---|---|---|
| TestResolveAgentDir | 3 | `resolve_agent_dir()` path resolution |
| TestLazyLoaders | 2 | `get_agent_dir()` / `get_state_dir()` |
| TestFileInfo | 8 | `FileInfo` class (file metadata) |
| TestYamlDetail | 10 | `YamlDetail` class (yaml field extraction) |
| TestScanner | 11 | `Scanner` class (full/quick/yaml scans) |
| TestSaveScan | 2 | `save_scan()` writes analysis.json |
| TestMainCli | 5 | `main()` argparse CLI entry |
| **Total** | **41** | **7 function ranges, 91.2% coverage** |

## Coverage Delta

```
Pre-fix:  dev_observer.py  0% (no test file targets this module)
Post-fix: dev_observer.py  91.2% (258/283 stmts)
Delta:    +91.2pp, +258 stmts
```

## Pre-Existing Test Status (no regression)

Full suite: 3745 passed, 13 failed, 7 skipped in 10:59. The 13 failures
are all in pre-existing test files (test_dev_im_finder_scan_lib,
test_dev_message_queue, test_guardian_scan, test_r110262_*,
test_r110279_runtime_var_skip). **None are in test_dev_observer_r110374.py.**

## ⚠️  8e72b14 Empty-Subject Disclosure

Commit `8e72b14` (which added the test file) was created with an
**empty subject `[]`** — this is a Check 1.5 BLOCKER per R110-78/304.
Per R110-281, force-push and rebase are FORBIDDEN, so the recovery
path is: keep 8e72b14 as historical fact, document the gap
transparently, and let the next R-sprint (R110-375) add a
`📝 R110-374 — subject recovery` follow-up commit.

The test content is correct (41/41 PASS in 0.14s, 91.2% coverage);
only the commit metadata needs a follow-up.

## Files Touched

| File | Status | Lines |
|---|---|---|
| `tests/test_dev_observer_r110374.py` | added in 8e72b14 | 490 |
| `docs/CHANGELOG-2026-09-08-r110-374-dev-observer-coverage.md` | NEW (this) | ~50 |
| `logs/e2e-evidence-gen2/R110-374-EVIDENCE.md` | NEW | ~165 |
| `STATUS.md` | MOD | +1 row |

## Refs

- R110-373 (508ce6e) — r2 dev_editor at 58.18%
- R110-372 (9b5c9bb) — r1 dev_editor at 49.87%
- R110-371 (3764ffa) — dev_workspace at 80.1%
- R110-367 — dev_dashboard_refresh (sibling pattern)
- R110-78 — verification-theater pattern
- R110-258 — force-add evidence via `git add -f`
- R110-281 — force-push-versehen, no-rebase rule
- R110-304 — 3-source lockstep for commit-subject format
- Skill: `mas-engineer-coverage-push-workflow` (Pitfall 10)
