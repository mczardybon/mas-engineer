# R110-295 — EVIDENCE — Cleanup untracked zombie test_zz_r110279_runtime.py

**Generated:** 2026-08-29
**File:** `mas-engineer/tests/test_zz_r110279_runtime.py` (deleted)

## Before-deletion status (real-flow)

```
$ ls -la mas-engineer/tests/test_zz_r110279_runtime.py
-rw-r--r-- 1 root root 147 Aug 29 07:54 mas-engineer/tests/test_zz_r110279_runtime.py

$ git status --short
?? mas-engineer/tests/test_zz_r110279_runtime.py    # UNTRACKED, never committed

$ pytest mas-engineer/tests/test_zz_r110279_runtime.py
FAILED mas-engineer/tests/test_zz_r110279_runtime.py::test_r110279_runtime
E   NameError: name 'capsys' is not defined
1 failed in 0.04s
```

## After-deletion status (real-flow)

```
$ rm mas-engineer/tests/test_zz_r110279_runtime.py
$ ls -la mas-engineer/tests/test_zz_r110279_runtime.py
ls: cannot access '...': No such file or directory

$ git status --short
(no untracked files)

$ pytest mas-engineer/tests/test_r110279_runtime_var_skip.py -q --no-header
6 passed, 1 failed in 70.29s    # canonical R110-279 tests, 6/7 PASS.
  # 1 PRE-EXISTING FAILURE (NOT caused by R110-295 cleanup):
  # test_detector_finds_drift_for_synth_test — synth literal
  # 'ZOMBIEXYZ_FORTY_TWO_LITERAL_NOT_IN_ANY_SOURCE_R110279' is
  # already in 2 other files (test_r110279_runtime_var_skip.py
  # docstring Z.114 + others), so _is_common_value() triggers
  # and detector returns 0 findings instead of 1. Pre-existing
  # R110-279 bug, NOT caused by R110-295. Tracked as R110-296
  # follow-up (isolate synth literal in dedicated test-fixture
  # file, not inlined in any other file).
```

## Origin / root cause

- File created 2026-08-29 07:49:13 (this morning, before R110-293).
- Likely a scratch/aborted test left over from R110-279 work.
- Real R110-279 canonical tests live in
  `mas-engineer/tests/test_r110279_runtime_var_skip.py`
  (204 lines, 18 collect-tests, 7 test-functions via
  parametrize, committed 289780e).
- The orphan had:
  - 3 lines, 147 bytes
  - `def test_r110279_runtime():` (no `capsys` fixture param)
  - Asserts a literal that never appears in any source
  - Untracked, never committed
  - Broke every full pytest run with 1 collect-time NameError
