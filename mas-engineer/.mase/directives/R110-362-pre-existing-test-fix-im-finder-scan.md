---
sprint: R110-362
topic: pre-existing-test-fix — test_dev_im_finder_scan_lib.py 75 errors
status: planned
---

# R110-362 — Fix pre-existing 75 errors in test_dev_im_finder_scan_lib.py

## Goal

Make `mas-engineer/tests/test_dev_im_finder_scan_lib.py` PASS (75 errors → 0).
This is a **pre-existing test fix**, not a coverage-push. The expected
side-effect is a +20-30pp coverage boost on `tools/dev_im_finder_scan.py`
because the library tests already import the canonical `tools.dev_im_finder_scan`
name (per `.coveragerc [paths] source=tools/`), which is the import path
that coverage actually tracks.

## Root cause

`tests/test_dev_im_finder_scan_lib.py::mod` fixture (L42-49) uses
`importlib.util.spec_from_file_location` + `exec_module` to load
`tools/dev_im_finder_scan.py`. This triggers the **module-level**
`check_spec_drift(findings, '.')` call at L1578.

`check_spec_drift` then walks `recipe/`, `tools/`, `docs/`, `.mase/`,
`tests/`, etc. (via `os.walk`), and for EVERY literal extracted from
test files, reads every Python file in those dirs to check if the literal
appears. With the full mas-engineer dir (1500+ files, many KB each)
and 50+ test literals, this takes 30+ seconds → pytest-timeout
triggers at 30s.

## Fix (per R110-347 pattern)

In `_load_scanner()`, BEFORE `spec.loader.exec_module(mod)`:

1. Save current CWD + env vars (`os.environ['SCAN_SCOPE']`,
   `os.environ['SEVERITY_FILTER']`, `os.environ['MAS_INCLUDE_EXTERNAL_RECIPES']`)
2. `os.chdir(tmp_path)` — a sandboxed empty dir
3. `os.environ['SCAN_SCOPE'] = str(tmp_path / "no-such-dir")` — points to
   non-existent dir so even if check_spec_drift tries to use it, no-op
4. `os.environ['SEVERITY_FILTER']` = all severities (so the
   module-level add_finding calls don't get filtered out)
5. After exec_module: restore CWD + env

The `os.chdir` makes `os.path.isdir('tests')` return False inside
`check_spec_drift(findings, '.')` (since `'.'` is now `tmp_path`),
so the function returns immediately at L985 (the `if not os.path.isdir(
tests_dir): return` early-exit).

This is the same pattern that `test_r110347_im_finder_scan_coverage_push_r2.py`
+ `test_r110361_im_finder_scan_coverage_push_r1.py` use in their
`ifs` fixture (monkeypatch.chdir + SCAN_SCOPE + SEVERITY_FILTER BEFORE
import).

## Targets (after fix)

- `python3 -m pytest tests/test_dev_im_finder_scan_lib.py` → 75 errors → 0 errors
- All 75 tests PASS in < 5s (not 30s+)
- Coverage on `tools/dev_im_finder_scan.py` (combined with r110361):
  27% → 45-55% (because these tests exercise different code paths
  than the 4 pure-helper regions r110361 covers)
- Side-effect: the FIX is also reusable for any future test that
  imports `tools.dev_im_finder_scan` via importlib — no need to
  rediscover the 30s module-level scan

## Files

- `mas-engineer/tests/test_dev_im_finder_scan_lib.py` (MODIFY, +15 lines
  for save/restore logic in `_load_scanner()`, +5 lines for the
  `tmp_path` parameter in the `mod` fixture)

## Constraints

- DO NOT change test assertions — they're correct
- DO NOT add `--timeout=120` to dodge the issue — root cause is
  the module-level side-effect, fix that
- DO NOT add teardown that auto-cleans `sub_-.yaml` — per
  mas-engineer-pre-existing-test-fix-3-source-lockstep skill,
  the file is a legitimate negative-case fixture
- Keep `_load_scanner()` API stable so other tests can keep using it
  (or refactor to a shared helper if needed)

## Verification

```bash
# Should PASS in <5s
python3 -m pytest tests/test_dev_im_finder_scan_lib.py -q --timeout=30

# Coverage
python3 -m pytest tests/test_dev_im_finder_scan_lib.py \
  tests/test_r110361_im_finder_scan_coverage_push_r1.py \
  tests/test_r110347_im_finder_scan_coverage_push_r2.py \
  tests/test_r110323_im_finder_scan_bug_fixes.py \
  -p no:cacheprovider --no-header -q \
  --cov=tools --cov-report=term 2>&1 | grep dev_im_finder_scan.py
# Expected: ~45-55% (vs current 27%)
```

## Refs

- R110-347 (monkeypatch-env-import pattern, the model)
- R110-361 (r1 coverage-push, immediate predecessor)
- R110-309 (test_r110309_im_finder_scan_lib.py — already uses
  importlib.util + 19 tests pass, but did the env-isolation right)
- R110-323 (im_finder_scan Prio-3 inventory)
- Skills: mas-engineer-coverage-push-workflow,
  mas-engineer-pre-existing-test-fix-3-source-lockstep
