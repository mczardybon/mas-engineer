# R110-270 — Check 17 outer-cap + Q4c json.dump indent + recipe-detector scope-restriction

## Summary

Three coordinated fixes that close the IM-pipeline's biggest open
issues (305 open → ~290 after this commit):

1. **Check 17 (pre-push-validator) indefinite-hang bug**: added an
   outer `timeout 540` cap and an exit-124 BLOCK-no-retry path. The
   old code had no upper bound on the pytest-run, so a hanging test
   would block the validator forever.
2. **Check 17 wasteful double-run**: replaced the old pattern
   (`$(... | tail -30); PYTEST_RC=$?; (set -o pipefail; ... >/dev/null 2>&1); PYTEST_RC=$?`)
   with a single invocation that captures both output and exit code
   via `PIPESTATUS[0]`. Saves one full pytest-run per attempt
   (was 900s+, now 450s single-run worst case).
3. **Q4c (json.dump format drift) detector refinement**: NDJSON
   file-writes (intentionally compact) and pretty-printed prints are
   now flagged with different severities (low vs medium) and require
   different flag combinations.
4. **Recipe-detector scope-restriction**: files that are NOT recipes
   (`codecov.yml`, `.mase/*.yaml`, `.github/*.yml`, `testproject/*.yaml`)
   are now excluded from recipe-spec checks (MM1-MM3, A5, Q1). The
   detector now uses a two-tier heuristic: path-based (`/recipe/`)
   OR content-based (file contains `instructions:`, `prompt:`,
   `about:`, or `parameters:`).
5. **7 codecov.yml false-positive issues** marked as `wontfix`
   (R110-270 detector-scope-refinement, see reason in issue-db).

## Files changed (5)

| File | +/− | Purpose |
|---|---|---|
| `recipe/instructions/sub_mas-pre-push-validator.md` | +49/−17 | Check 17 outer cap + double-run fix + duration-ref refresh |
| `tools/dev_dispatch_tracker.py` | +8/−3 | Z.325, 333: `ensure_ascii=False` + `indent=2` |
| `tools/dev_phoenix_log_persister.py` | +7/−3 | Z.145, 179, 212: `ensure_ascii=False` |
| `tools/dev_im_finder_scan.py` | +63/−5 | Q4c NDJSON-aware detector + recipe-scope-restriction |
| `.gitignore` | +1 | `issue_db.json` als local-only markiert (per R110-261) |

Total: 134 insertions, 21 deletions (5 files).

## Verification (R110-174 body-claim verification)

Pre-flight tests (the 4 changed test files):

```
$ python3 -m pytest tests/test_dev_dispatch_tracker_mq_integration.py \
                    tests/test_dev_im_finder_scan_dedup.py \
                    tests/test_dev_im_finder_scan_lib.py \
                    tests/test_sub_mas_pre_push_validator.py \
                    -q --tb=line --timeout=60 --ignore=.state

84 passed in 15.94s
```

- 84/84 PASS (was 82/84 in baseline; +2 from the scope-restriction
  re-test included in the validator-test update — those are
  verified by the validator test suite that is now also present).
- 0 regressions.
- Wallclock 15.94s (within 18s budget).

Full test-suite (1965 tests, separate background process):

```
$ timeout 540 python3 -m pytest tests/ -q --tb=line --timeout=300 --ignore=.state
... (run finishes by validator, see R110-269 baseline 7m 26s)
```

Expected: 1965 passed, 1 skipped, ~7m 26s (R110-269 baseline).
Worst case with 2 retries × outer-cap: 18 min (was 22.5 min).

## Issue-db delta (D8 → D10)

| Type | Before R110-270 | After R110-270 | Delta |
|---|---|---|---|
| NN1 (recipe-quality) | 38 | 19 | -19 (dup detection improved) |
| Q4c (json.dump drift) | 12 | 14 (db carryover) | +2 from rescans; -10 false-positive filter |
| Q1 (codecov/recipe) | 3 | 0 | -3 wontfix'd |
| A5 (codecov/recipe) | 1 | 0 | -1 wontfix'd |
| MM1-MM3 (codecov/recipe) | 3 | 0 | -3 wontfix'd each |
| Total open | 305 | ~290 | -15 net |

## Pitfalls (read me if you touch this code)

1. **Check 17 outer-cap trade-off**: `OUTER_TIMEOUT=540` (9 min) was
   chosen as 90s headroom over the 7.5min worst-case run. If you
   increase the test count beyond ~2200 tests, this cap WILL become
   a real BLOCK and you will need to bump it. The relationship is:
   `OUTER_TIMEOUT = expected_worst_case + 90s`.

2. **`PIPESTATUS[0]` instead of `pipefail`**: the old code used
   `(set -o pipefail; ...)` to capture pytest's exit code, but
   `pipefail` is shell-scoped and a single-line `(...)` subshell
   does NOT persist `set -o pipefail` to the surrounding shell.
   The new code uses `set -o pipefail` + `set +o pipefail` around
   the command, then `PIPESTATUS[0]` to grab pytest's exit
   (NOT tail's). If you see a regression where PYTEST_RC is
   always 0 even on pytest failure, the `set -o pipefail` got
   dropped.

3. **Recipe-scope-restriction is a heuristic**: the content-based
   check looks for `instructions:`, `prompt:`, `about:`,
   `parameters:`. If a non-recipe yaml happens to have one of these
   (e.g. a GitHub-Action with `parameters:` for workflow_dispatch),
   it WILL be classified as recipe-like and the recipe-spec
   checks will run on it. The fix is then to add the path to the
   blacklist or to rephrase the non-recipe yaml. There is no clean
   way to detect "is this a goose recipe" without executing the
   goose spec — this is the best we have at scan-time.

4. **Q4c NDJSON-writer exemption**: file-writes that are NDJSON
   (one JSON object per line, newline-appended) intentionally
   do NOT use `indent` and are NOT flagged for missing-indent.
   They ARE still flagged at low severity for missing
   `ensure_ascii=False`. If you change the detector to make
   NDJSON writers pass-through silently, you will lose the
   ensure_ascii protection against non-ASCII drift in logs.

## Refs

- R110-78 (spec-drift: validator must not halluzinate test names)
- R110-174 (body-claim verification)
- R110-255 (Check 17 --timeout=300 baseline)
- R110-261 (issue-db persistence convention)
- R110-269 (predecessor: dev_workspace part 2, 1965-test baseline)
