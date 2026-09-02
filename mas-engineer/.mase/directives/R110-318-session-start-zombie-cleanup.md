# Directive R110-318 — Auto-cleanup of test-side-effect zombie files via conftest pytest_sessionstart hook

## 1. Problem

Some mas-engineer tests create ephemeral test files as part of their test
logic, with cleanup in a `try/finally: os.unlink()` block:

  - `tests/test_r110279_runtime_var_skip.py` creates `tests/test_zz_*.py`
    + `recipe/sub/sub_-.yaml` (and similar 0-byte fixture patterns)
  - These are then collected by pytest as tests or detected as
    "0-byte fixture" by the R110-316 3-source lockstep test

If `pytest-timeout` kills the test mid-run (e.g. test hangs, OOM, or
developer aborts with Ctrl-C), the `finally` block is **skipped**, and
the file persists as a "zombie". R110-295 documented this exact issue
with a leftover `test_zz_r110279_*.py` file that had to be manually
`rm`-ed before pre-push.

The R110-316 3-source lockstep test catches zombies at pre-push time,
but that is a *detection* mechanism, not a *prevention* one. The
zombie still has to be manually cleaned by the developer.

## 2. Goal

Add an automatic "fresh state" guarantee at the start of every pytest
session: any zombie test-side-effect files are silently cleaned before
collection. This way:

  - the developer does not have to remember to `rm` zombies
  - the R110-316 lockstep test is no longer needed for THIS class of
    drift (it remains useful for the broader lockstep invariants)
  - pre-push runs are clean by default

## 3. Design

A `pytest_sessionstart` hook in `tests/conftest.py` runs BEFORE pytest
collects tests. The hook performs two operations:

### 3.1 Auto-cleanup: `tests/test_zz_*.py`

The known test-side-effect pattern. Originates from R110-279
(`test_r110279_runtime_var_skip.py`) and is the ONLY such pattern
currently in use. Any new test that creates ephemeral test files MUST
use this same `test_zz_*.py` prefix so the auto-cleanup covers it.

The hook:
  1. globs `tests/test_zz_*.py`
  2. deletes each match
  3. also deletes `tests/__pycache__/test_zz_*.pyc` (matching .pyc)
  4. prints `[R110-318] Cleaning N zombie test-side-effect file(s)` to
     stderr (so it is visible but not in stdout, and does NOT break
     stdout-based tests)

This is the only destructive operation in the hook. The pattern is
narrow (`test_zz_*.py`), so the risk of false-positive deletion is
effectively zero. Legitimate tests are NOT touched.

### 3.2 Read-only WARNING: `recipe/sub/*.yaml` 0-byte files

A separate class of zombies: 0-byte `recipe/sub/*.yaml` files that
are NOT in the `RECIPE_EXCLUDE` allowlist. These are RARE in practice
(test_zz_*.py tests use `tests/` as their workspace, not `recipe/sub/`)
but if one exists it is almost always a zombie. The hook:

  1. globs `recipe/sub/*.yaml` and filters to 0-byte files
  2. loads `RECIPE_EXCLUDE` from `tests/test_unix_test_word.py` via
     importlib (best-effort, does not fail if import errors)
  3. emits `[R110-318] WARNING: N 0-byte recipe/sub/*.yaml file(s)
     NOT in RECIPE_EXCLUDE allowlist` to stderr, listing the files
  4. does NOT delete them (destructive, may be legitimate)

The user sees the WARNING and can decide: `rm` the file or add it to
the allowlist.

### 3.3 Why read-mostly for recipe/sub

Auto-deleting `recipe/sub/*.yaml` would be too dangerous: a user
might have a legitimate 0-byte fixture (e.g. an empty default
config). The WARNING is the right level: visibility without
destruction. The R110-316 3-source lockstep test will FAIL on
pre-push if the WARNING is not addressed, giving two layers of
detection (one immediate, one at push time).

### 3.4 Pattern safety

- The hook uses `pathlib.Path.unlink()` which is atomic and raises
  `FileNotFoundError` if the file is already gone (rare race; not a
  problem because we glob at hook start, so the list is fixed)
- The hook does NOT recurse into subdirectories (no `**/*.yaml`)
- The hook does NOT touch files outside `tests/` and `recipe/sub/`
- The hook is called once per pytest session, not per test

## 4. Files

### 4.1 Modified

  - `mas-engineer/tests/conftest.py`
    - +18 lines docstring describing R110-318
    - +1 import: `import glob` (for `glob.glob` symmetry, currently unused)
    - +91 lines: `pytest_sessionstart` hook
    - net: +111 lines (docstring + hook)

### 4.2 Added

  - `mas-engineer/tests/test_r110318_session_start_zombie_cleanup.py`
    - 7 tests, ~250 lines, + 0 imports beyond stdlib
    - Tests use `tmp_path` fixture + `monkeypatch` to fake the REPO_ROOT
    - Each test creates its own zombies in isolation; no test pollution

### 4.3 Not modified

  - `mas-engineer/tests/test_r110316_*` (3-source lockstep test): kept
    in place as belt-and-suspenders for the broader lockstep invariants
    (A ∪ B ⊇ C). R110-318 only addresses the *runtime* zombie class.

## 5. Test plan

The 7 tests in `test_r110318_session_start_zombie_cleanup.py` cover:

  1. test_clean_zombie_test_zz_file — single `test_zz_*.py` removed
  2. test_clean_zombie_pycache — matching `.pyc` also cleaned
  3. test_legitimate_test_files_untouched — `tests/test_unix_test_word.py`
     + `tests/__init__.py` (0-byte by convention) NOT touched
  4. test_warn_on_unhandled_recipe_sub_yaml — WARNING emitted, file kept
  5. test_no_warning_when_recipe_sub_yaml_in_allowlist — no WARNING
     when in allowlist
  6. test_no_op_when_no_zombies — clean state produces no output
  7. test_multiple_zombies_all_cleaned — 5 zombies all cleaned in one pass

Pre-push-gate Step 2 runs all 7 + 12 alignment + 11 unix + 4 lockstep
+ 1 zombie-recovery = 35 tests; verified PASS in 1.20s.

## 6. Edge cases

### 6.1 tests/__init__.py is 0-byte by convention

The conftest hook's pattern is `test_zz_*.py`, which does NOT match
`__init__.py`. Verified by `test_legitimate_test_files_untouched`
(0-byte `tests/__init__.py` fixture; assert still exists after hook).

### 6.2 RECIPE_EXCLUDE import fails

The hook uses `importlib.util.spec_from_file_location` to load
`test_unix_test_word.py`. If this import fails (syntax error, missing
file, permission denied), the hook falls back to an empty allowlist
and warns about ALL 0-byte recipe/sub/*.yaml files. This is the
correct behavior: "if I cannot determine the allowlist, assume the
worst and warn."

### 6.3 pytest_sessionstart called multiple times in one process

This can happen if pytest is invoked from another pytest (rare). The
hook is idempotent: if no zombies exist, the second call is a no-op
(`if zombies:` short-circuits).

## 7. Migration path

No migration needed. The hook is automatically active for any pytest
run that loads `tests/conftest.py` (which is all current tests, since
`conftest.py` is at the test root).

Existing tests are unaffected because:
  - The hook only deletes files matching `test_zz_*.py`
  - The hook only WARNS about recipe/sub/*.yaml (no delete)
  - The hook runs before pytest collection, so no test sees a different
    file system than the developer

## 8. Future improvements (NOT in scope for R110-318)

  - Apply the same pattern to other "ephemeral fixture" prefixes
    (e.g. `tests/test_tmp_*.py` if such a pattern emerges)
  - Add a `--no-zombie-cleanup` CLI flag for users who want to
    inspect zombies before deletion (debugging aid)
  - Replace the 0-byte recipe/sub warning with an opt-in `--strict`
    mode that fails the session on unhandled 0-byte files (today the
    R110-316 lockstep test does this at pre-push time)

## 9. Pre-push-gate

  - Step 0 (secret scan): 0 secrets
  - Step 1 (pre-commit hook): PASS
  - Step 2 (pytest targeted): 7/7 + 12/12 + 11/11 + 4/4 + 1/1 = 35/35
  - Step 3 (commit msg, 📝 R-format): pattern 5 matched
  - Step 4 (push): pending (this commit)
  - Step 5 (post-flight audit): pending
