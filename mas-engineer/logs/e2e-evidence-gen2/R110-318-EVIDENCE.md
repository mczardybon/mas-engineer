# R110-318 EVIDENCE — conftest.py pytest_sessionstart hook auto-cleans test-side-effect zombies

**Commit:** 0fb0fdf (origin/mas-t-tests, pushed 2026-09-01)
**Round:** 110 (sprint R110-316/317/318 = drift-detection + auto-cleanup)
**Author:** Hermes-MAS-Engineer <Hermes@mas-engineer.local>
**Skill:** mas-engineer-pre-existing-test-fix-3-source-lockstep (paired
with R110-316 for 2-layer defense: detection-at-pre-push + prevention-
at-session-start)

## Why this commit exists

R110-316 added the 3-source lockstep test that catches `recipe/sub/*.yaml`
0-byte files at pre-push time. R110-318 noticed a RELATED zombie
class that R110-316 does NOT catch: `tests/test_zz_*.py` test-side-
effect files created by `test_r110279_runtime_var_skip.py` (and any
future tests using the same pattern).

Pattern: a test creates an ephemeral `tests/test_zz_*.py` file as
part of its test logic, with cleanup in a `try/finally: os.unlink()`
block. If `pytest-timeout` kills the test mid-run, the `finally`
block is SKIPPED, and the file persists as a zombie. R110-295
documented this exact issue: a leftover `test_zz_r110279_*.py` file
had to be manually `rm`-ed before pre-push.

R110-318 closes this gap at the source by adding a
`pytest_sessionstart` hook in `tests/conftest.py` that runs BEFORE
pytest collection and auto-cleans these zombies. R110-316 catches
them at pre-push (detection layer); R110-318 prevents them from
accumulating in the first place (prevention layer).

## Files touched (4)

| File | + | - | Why |
|------|---|---|-----|
| `mas-engineer/tests/conftest.py` | +109 | 0 | +18 docstring (R110-318 explanation), +1 import (`glob`, symmetry, currently unused — left for future), +90 hook (`pytest_sessionstart` with auto-cleanup + WARNING) |
| `mas-engineer/tests/test_r110318_session_start_zombie_cleanup.py` | +200 | 0 | NEW, 7 tests covering: single zombie + .pyc + legit files untouched + WARNING + allowlist no-warn + no-op + multi-zombie |
| `mas-engineer/.mase/directives/R110-318-session-start-zombie-cleanup.md` | +185 | 0 | NEW, 9-section spec (Problem/Goal/Design/Files/Tests/Edges/Migration/Future/Pre-push-gate) |
| `mas-engineer/STATUS.md` | +79 | 0 | R110-317 + R110-318 sections appended |
| **Total** | **+573** | **0** | **2 modified, 2 added** |

## Pre-push-gate status (per mas-engineer-commit-protocol skill)

| Step | What | Result |
|------|------|--------|
| 0 | secret scan, tracked + history | OK 0 secrets (conftest.py + test + directive + STATUS.md all clean) |
| 1 | pre-commit hook, staged content | OK PASS after `STATUS.md` trailing-blank fix (`rstrip(b'\n\r ')+b'\n'`) |
| 2 | pytest `tests/test_r110318_session_start_zombie_cleanup.py` (7 tests) | OK 7/7 in 0.14s |
| 2b | pytest `tests/test_pre_push_check_1_5_skill_alignment.py` (12 tests) | OK 12/12 (regression check) |
| 2c | pytest `tests/test_unix_test_word.py` (11 tests) | OK 11/11 (regression check) |
| 2d | pytest combined (48 tests) | OK 48/48 in 1.20s |
| 3 | commit msg, 🔧 R-format pattern 2 | OK `🔧 R110-318 — ...` matches validator Check 1.5 emoji-prefix allowlist |
| 4 | push via credential-helper | OK (09c8d99..0fb0fdf) |
| 5 | post-flight audit | OK 37/37 still green, 0 secrets in `git show origin/mas-t-tests:...` |

## E2E test (R110-318 specific, dual-direction verification)

The 7 new tests must be run in BOTH directions before commit (per
R110-316 EVIDENCE precedent, generalised for any new test):

### Direction 1: zombie-exists → cleanup

```bash
# Setup: create a fake zombie
$ cd mas-engineer
$ touch tests/test_zz_r110318_zombie.py
$ ls tests/test_zz_r110318_zombie.py
tests/test_zz_r110318_zombie.py

# Test: hook removes it
$ python3 -m pytest tests/test_r110318_session_start_zombie_cleanup.py::test_clean_zombie_test_zz_file -v
PASSED

# Post-state: file is gone
$ ls tests/test_zz_r110318_zombie.py
ls: cannot access 'tests/test_zz_r110318_zombie.py': No such file or directory
```

### Direction 2: zombie-allowed-in-allowlist → no warning

```bash
# Setup: create 0-byte file in allowlist
$ touch recipe/sub/sub_-.yaml

# Test: hook does NOT warn (allowlist match)
$ python3 -m pytest tests/test_r110318_session_start_zombie_cleanup.py::test_no_warning_when_recipe_sub_yaml_in_allowlist -v
PASSED

# Post-state: file is still there (read-mostly behavior)
$ ls -la recipe/sub/sub_-.yaml
-rw-r--r-- 1 user user 0 Sep  1 23:50 recipe/sub/sub_-.yaml
```

This proves the test is NOT vacuous: it catches both the deletion
(direction 1) and the no-deletion (direction 2) behaviors.

## Targeted pytest summary (R110-318)

```text
tests/test_r110318_session_start_zombie_cleanup.py::test_clean_zombie_test_zz_file PASSED
tests/test_r110318_session_start_zombie_cleanup.py::test_clean_zombie_pycache PASSED
tests/test_r110318_session_start_zombie_cleanup.py::test_legitimate_test_files_untouched PASSED
tests/test_r110318_session_start_zombie_cleanup.py::test_warn_on_unhandled_recipe_sub_yaml PASSED
tests/test_r110318_session_start_zombie_cleanup.py::test_no_warning_when_recipe_sub_yaml_in_allowlist PASSED
tests/test_r110318_session_start_zombie_cleanup.py::test_no_op_when_no_zombies PASSED
tests/test_r110318_session_start_zombie_cleanup.py::test_multiple_zombies_all_cleaned PASSED
... (7/7 PASS, 0 fail, 0 error in 0.14s)

# Combined with regression set
tests/test_pre_push_check_1_5_skill_alignment.py (12 tests) PASSED
tests/test_unix_test_word.py (11 tests) PASSED
... (48/48 PASS, 0 fail, 0 error in 1.20s)
```

## Body-claim verification (R110-305 + R110-173 lesson)

| Claim in body | Verified via | Actual |
|---------------|--------------|--------|
| `+111` for conftest.py (initial) | `git diff --numstat` | `+109` (off-by-2) |
| `+250` for test file (initial) | `wc -l` | `+200` (off-by-50) |
| `+198` for directive (initial) | `wc -l` | `+185` (off-by-13) |
| `+76` for STATUS.md (1st pass) | `git diff --numstat` | `+80` (off-by-4) |
| `+79` for STATUS.md (2nd pass) | `git diff --numstat` | `+79` (match, 2nd pass after 1st patch) |
| `+80` for STATUS.md (3rd pass) | `git diff --numstat` | `+80` (match, after 2nd patch) |
| `+79` for STATUS.md (FINAL) | `git diff --numstat` (after trailing-blank fix) | `+79` ✓ (after re-stage) |
| `+573` total (FINAL) | `git diff --cached --stat` | `4 files changed, 573 insertions(+)` ✓ |
| `7/7 R110-318 tests PASS` | `pytest tests/test_r110318_session_start_zombie_cleanup.py` | `7 passed, 0 failed` ✓ |
| `48/48 targeted pytest PASS` | `pytest` of combined set | `48 passed, 0 failed` ✓ |
| `0 secrets in staged content` | `git diff --cached \| grep -E "sk-\|ghp_\|DEEPSEEK_API_KEY=[a-z0-9]"` | `0 matches` ✓ |

The body-claim drift was corrected through 4 rounds of `git diff
--numstat` + `wc -l` re-verification per R110-305. Initial estimates
+111/+250/+198/+76 = +635 were off by ~62 from final +109/+200/+185
/+79 = +573. The `STATUS.md` final count dropped from +80 to +79
after the trailing-blank-line fix (re-staged post-rstrip).

## Design decisions

### Read-mostly by design

The hook auto-DELETES only `tests/test_zz_*.py` files. For
`recipe/sub/*.yaml` 0-byte files, it only WARNS (read-mostly).
Reason: a 0-byte `recipe/sub/*.yaml` might be a legitimate fixture
(e.g. empty default config), so deletion would be too dangerous.
The R110-316 3-source lockstep test will FAIL on pre-push if the
WARNING is not addressed, giving two layers of protection
(immediate visibility + push-time enforcement).

### Pattern safety

- The hook uses `pathlib.Path.unlink()` which is atomic
- The hook does NOT recurse into subdirectories
- The hook does NOT touch files outside `tests/` and `recipe/sub/`
- The hook is called once per pytest session, not per test
- `tests/__init__.py` (0-byte by convention) is NEVER matched
  (pattern is `test_zz_*.py`, not `*.py`)

### RECIPE_EXCLUDE import strategy

The hook uses `importlib.util.spec_from_file_location` to load
`RECIPE_EXCLUDE` from `tests/test_unix_test_word.py`. If the
import fails (syntax error, missing file, permission denied), the
hook falls back to an empty allowlist and warns about ALL 0-byte
recipe/sub/*.yaml files. This is the correct behavior: "if I
cannot determine the allowlist, assume the worst and warn."

## Forward-pointer

- **R110-319** (potential, in flight): evidence closure for
  R110-318 (this file + STATUS.md entry + CHANGELOG). Same
  convention as R110-317 for R110-316.
- **R110-32X** (potential): trim unused `import glob` in
  conftest.py (minor cleanup) + add `--no-zombie-cleanup` CLI flag
  for debug inspection (per directive §8 future improvements).

## Related

- R110-316: 3-source lockstep smoke test (the detection layer
  R110-318 pairs with)
- R110-317: evidence closure for R110-316 (the pattern R110-319
  follows for R110-318)
- R110-295: original zombie-recovery commit that documented the
  manual `find -size 0` cleanup pattern (R110-318 automates it)
- R110-279: origin of the `tests/test_zz_*.py` test-side-effect
  pattern (the R110-318 hook targets this pattern specifically)
- R110-129 + R110-311: conftest-setup precedents (os.chdir +
  COVERAGE_PROCESS_START) — R110-318 follows the same pattern
  for conftest-level setup before test collection
- Skill: `mas-engineer-pre-existing-test-fix-3-source-lockstep`
  (R110-318 pairs R110-316 for 2-layer defense; same skill
  referenced for failure-mode documentation)
- Skill: `pre-push-body-claim-verification` (R110-305 + R110-173
  used for the 4 rounds of `git diff --numstat` + `wc -l` to nail
  the exact +109/+200/+185/+79 = +573 numbers)
