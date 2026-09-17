# R110-559 — fix pre-existing flake in tests/test_r110279_runtime_var_skip.py (synth + runtime-var subtests)

## Context

Full-sweep pytest (159 files, ~8m23s) for `tests/test_r110*.py` on cleanup-branch
HEAD 361bb5e (2026-09-14) shows 3916 PASSED + 6 SKIPPED + 1 XFAIL + **1 FAILED**:

```
FAILED tests/test_r110279_runtime_var_skip.py::test_detector_finds_drift_for_synth_test
FileNotFoundError: tests/test_zz_r110279_synth.py
```

Both tests in this file are flaky pre-existing (R110-369 §"THE 2 TIMEOUTS" classified
them as "pre-existing slow suite, out of scope"). R110-491 listed them again as
Category C (SD-test detector drift) — but R110-491 was never completed (status OPEN)
and R110-493 fixed only `test_r110470_*` and `test_sub_mas_im_finder::*`, not r110279.

## Root cause (verified empirically 2026-09-14)

The failing test `test_detector_finds_drift_for_synth_test` writes a synth file
`tests/test_zz_r110279_synth.py` containing a unique literal, spawns the detector as a
subprocess with `timeout=250`, and asserts the literal is in `result.stdout`.

**Empirical evidence:**
- With synth file present (manually written + detector run): detector output contains
  `"SD-test_zz_r110279_synth-1": 1` → 84 findings total → assertion would PASS.
- With synth file absent (full-sweep at the moment detector ran): 83 findings,
  no synth entry → assertion fails with `FileNotFoundError` (secondary; the `os.unlink
  (test_path)` in `finally` raises because a prior cleanup hook removed the file).

**The synth file is leaked across tests because:**

1. The 2 subtests share the path `tests/test_zz_r110279_synth.py` (subtest 1) and
   `tests/test_zz_r110279_runtime.py` (subtest 2) — neither is module-scoped.
2. Pytest schedules them in the same session.
3. `tests/conftest.py::pytest_sessionstart` deletes all `tests/test_zz_*.py` ONCE at
   session start (R110-318 zombie cleanup) — NOT between tests.
4. If subtest 2 (`test_detector_does_NOT_flag_runtime_var_assert`) ran first and
   crashed/timeout'd BEFORE its `finally: os.unlink`, the file leaks.
5. Subtest 1 starts: writes its own synth file → detector subprocess (250 s) →
   **during this 250 s window, some other cleanup hook (or pytest fixture teardown)
   removes the synth file** → detector output has no synth finding → `assert L1 in
   result.stdout` raises AssertionError → `finally: os.unlink` raises secondary
   `FileNotFoundError`.

**Hypothesis A (most likely):** pytest's tmp_path + monkeypatch interactions in
adjacent test files cause a race between file write and detector scan. The detector
itself works correctly (proven by manual repro).

**Hypothesis B:** Some other test in the 159-file sweep also writes to
`tests/test_zz_*.py` paths and races. Conftest only cleans at session start, not
between tests.

## Goal

Restore 3917 PASSED + 0 FAILED for the `test_r110*.py` sweep on cleanup-branch.
Eliminate the synth-file-race flake so the test reliably passes in CI.

## Fix plan (preferred → least invasive)

### Option 1 — Use `tmp_path` fixture + relative-to-cwd paths (preferred)

Rewrite both subtests to:

1. Write the synth file to `tmp_path / "test_zz_r110279_synth.py"` instead of
   `os.path.join(REPO_ROOT, "tests", "test_zz_r110279_synth.py")`.
2. Copy or symlink the synth file into `tests/` only AFTER the detector subprocess
   finishes (or skip `tests/` entirely and let detector scan tmp_path).
3. Use `subprocess.run(..., cwd=str(tmp_path))` so detector sees the synth file in
   its working directory.
4. Use `pytest.fixture` with `scope="function"` (default) and explicit cleanup in
   `finally`.

**Why preferred:** eliminates cross-test pollution and rm-races entirely. No need to
touch conftest or shared paths.

**Effort:** ~15 min.
**Risk:** Low — purely test-local. Detector behavior unchanged.

### Option 2 — Pin synth content via hash + assert on hash not literal

Change the assertion from `assert L1 in result.stdout` to:

1. After writing synth file, compute its sha256.
2. After detector run, search for the hash (or a hash-prefix) in result.stdout.
3. The structural_pattern already includes sha256 hash, so this is robust.

**Why useful:** even if some race deletes the file mid-scan, the detector output
that we captured BEFORE the delete still contains the pattern. But: if detector
output is captured only AFTER scan finishes, this doesn't help.

**Effort:** ~10 min.
**Risk:** Low.

### Option 3 — Move synth-file cleanup into a fixture with autouse=True + try/except

Add to `tests/test_r110279_runtime_var_skip.py`:

```python
@pytest.fixture(autouse=True)
def _cleanup_synth_leftovers():
    for p in [
        os.path.join(REPO_ROOT, "tests", "test_zz_r110279_synth.py"),
        os.path.join(REPO_ROOT, "tests", "test_zz_r110279_runtime.py"),
    ]:
        try:
            os.unlink(p)
        except FileNotFoundError:
            pass
    yield
    for p in [...]:
        try:
            os.unlink(p)
        except FileNotFoundError:
            pass
```

**Why useful:** belt-and-suspenders against leftover synth files from sibling tests
or aborted runs.

**Effort:** ~5 min.
**Risk:** Very low.

### Recommended combo: Option 1 + Option 3

Apply BOTH Option 1 (move to tmp_path) and Option 3 (autouse fixture) for defense
in depth. Total effort ~20 min.

## Per-batch fix plan

| Batch | Action | Est time |
|-------|--------|----------|
| 1 | Move both subtests to `tmp_path` fixture + use `cwd=tmp_path` for detector subprocess | 15 min |
| 2 | Add autouse fixture for stale-synth-file cleanup | 5 min |
| 3 | Per-test verification | 5 min |
| 4 | Full-sweep re-run of `tests/test_r110*.py` to confirm 0 failed | 10 min |

Total estimated: ~35 min.

## Verification

Per-test:
```
$ pytest tests/test_r110279_runtime_var_skip.py -v --tb=short --timeout=300
# expected: 2 passed in ~500s (both subtests)
```

Full-sweep target:
```
$ pytest tests/test_r110*.py -q --tb=line --no-header
# expected: 3917 passed, 6 skipped, 1 xfailed, 0 failed in ~510s
```

Combined sanity:
```
$ pytest tests/ -q --tb=line --timeout=300 --ignore=.state
# expected: 6164+ passed, 7 skipped, 0 failed in <1500s
```

## Pre-push gate

After R110-559 fix + verification:
- Check 17 (pytest-run) → must show 0 failed in the `test_r110*.py` subset
- Check 18 (spec-invariant) → unchanged
- All other checks → unchanged

## Status

CLOSED 2026-09-15 (commit b895205). Verification:
- isolation 5x: 18/18 PASS × 5 in 103-108s (deterministic)
- suite `tests/test_r110*.py`: 3927 PASSED + 6 skipped + 1 xfailed + 0 FAILED in 265.62s
- phantom-commit c5dbf3e (IDE auto-commit junk empty sub_-.yaml, R110-546/558 pattern): REVERTED
- R-evidence: logs/e2e-evidence-gen2/post-flight-audit-R110-559.json

## Refs

- R110-279 — original `is_runtime_var_assert` skip-rule (concat-avoidance attempt)
- R110-296 — concat-avoidance is incomplete; literal still appears as single string
            in source
- R110-318 — conftest.py R110-318 zombie-test cleanup (session start only)
- R110-369 — pre-existing test debt cleanup (r110279 listed as "out of scope")
- R110-397 — cwd=REPO_ROOT mirror in r110279 subtests
- R110-413 — bump 180→300 timeout on r110279 subtests
- R110-491 — pre-existing test fails remediation (r110279 = Category C, OPEN)
- R110-493 — fixed 2/5 Category C tests; r110279 left untouched
- **R110-559 — this directive**
