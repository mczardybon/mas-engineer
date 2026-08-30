# R110-306 — CI red pre-existing fixes (pytest hardcoded paths + e2e smoke missing pytest)

**Status:** DRAFT (2026-08-30)
**Author:** Hermes (R110-306 follow-up, 2026-08-30 session)
**Target:** mas-engineer CI on `origin/mas-t-tests` — 2 pre-existing bugs that
have been red on every commit since 7397957 (2026-08-30 R110-304 / R110-305 era)

## Context

`origin/mas-t-tests` is currently RED for `ci-tests` and `ci-e2e-smoke` on
all 4 recent commits (7397957, 533063d, 0330746, a4a90e0). `ci-quality`
succeeds. The red is NOT caused by the 3 docs-only commits we just pushed
(R110-303 directive + R110-304 + R110-305 — all `.mase/directives/STATUS.md`
text or `logs/e2e-evidence-gen2/` data files, 0 code-changes).

Verified via:
```
$ git log --oneline 7397957..HEAD
7397957 (R110-303 base)  533063d (R110-304 directive)  0330746 (R110-305 fix)
a4a90e0 (R110-305 push)
$ git diff --stat 7397957..HEAD
 .mase/directives/STATUS.md                 | only text additions
 logs/e2e-evidence-gen2/2026-08-30-r110304/ | only data files
```

All 4 commits share the same 2 pre-existing bugs. This directive fixes both.

## Bug 1 — ci-tests: 3 tests fail with FileNotFoundError on absolute path

**Failure (Python 3.11 + 3.12 pytest, jobs 99234991006 + 99234991122):**

```
FileNotFoundError: [Errno 2] No such file or directory:
'/workspace/dev-branch/mas-engineer-cleanup/mas-engineer/tools/dev_im_finder_scan.py'
```

**Root cause:** 4 tests in `tests/test_dev_im_finder_scan_lib.py` open
`dev_im_finder_scan.py` via a hardcoded absolute path that exists on the
user's local machine but NOT in the GitHub Actions runner's checkout
(`/home/runner/work/mas-engineer/mas-engineer/...`).

Affected tests (all open the file via the same hardcoded path):
- `test_nn1_threshold_is_8_not_5` (line 645-646)
- `test_nn3_threshold_is_400_not_200` (line 664-665)
- `test_nn3_skips_sub_recipes` (line 688-689)
- `test_q4c_print_only_requires_ensure_ascii` (line 703-704)

(`test_r110_286_nn3_*` on line 841 already uses a relative `tools/...`
path which works because R110-129's conftest does `os.chdir(REPO_ROOT)`.)

**Fix:** Replace the hardcoded absolute path with `mod.__file__` —
the same pattern the file already uses on line 644 (the first occurrence
already does `mod.__file__ and open(mod.__file__).read() or open(<hardcoded>)`,
proving the author knew the right pattern but copy-pasted the fallback in
the 4 follow-up tests). Using `mod.__file__` directly is CWD-independent
and CWD-safe regardless of where the test is invoked from.

## Bug 2 — ci-e2e-smoke: check #12 fails with "No module named pytest"

**Failure:** `ci-e2e-smoke.yml` installs only `pyyaml` in the
"Install minimal deps" step. But `e2e-test.sh` check #12 (R110-262
redteam-2, scripts/e2e-test.sh:496) invokes
`python3 -m pytest tests/test_r110_262_*.py` for 3 spec-gap test
files, which fails with `No module named pytest` and exits non-zero.

**Fix:** Add `pytest` to the `pip install` line. The shell harness
calls pytest, so pytest must be installed. pyyaml stays for the
earlier checks (#1..#11) that use `yaml.safe_load`.

## Verification

- `pytest tests/test_dev_im_finder_scan_lib.py -k "nn1_threshold or nn3_threshold or nn3_skips_sub or q4c_print_only"`:
  4/4 PASS locally (Python 3.11).
- `bash scripts/e2e-test.sh`: 13/13 PASS, 0 FAIL, 0 SKIP locally.
  Check #12 specifically: `R110-262 redteam-2 — 3 spec-gap tests PASS (48 passed)`.
- `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci-e2e-smoke.yml'))"`: YAML valid.
- The same 2 fixes will be picked up by CI on next push to `mas-t-tests`.

## Refs

- R110-276 (NN3 threshold + scanner logic — the test-content being checked)
- R110-262 (redteam-2 spec-gap tests — the 3 tests e2e #12 invokes)
- R110-129 (conftest chdir R-FIX — the reason line 841 already works)
- R110-305 (previous docs-only commit on `mas-t-tests`, this commit is
  its code-fix follow-up)
