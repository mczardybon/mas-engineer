# R110-278 — SD-test detector search-path fix (.mase/ as 4th source-anchor)

**Date:** 2026-08-28
**Author:** Hermes-MAS-Engineer <Hermes@mas-engineer.local>
**Branch:** mas-t-tests
**Related:** R110-269 (workspace part 2), R110-270 (Q4c initial), R110-276/277 (detector tuning + recursion guard)

## What this commit does

After R110-277, the scanner reported 35 findings — all SD-test
(spec-drift: test asserts literal X but X is absent from recipe/,
tools/, docs/). Manual analysis showed 9 of those were false
positives: the literals (e.g. "Consumer", "inputSchema",
"__WORKSPACE_PLACEHOLDER__") are canonical descriptions in
`.mase/workflows.yaml` and `.mase/mcp/server.js`, but the
`check_spec_drift()` function only searched `recipe/`, `tools/`,
`docs/`. So legitimate, in-source literals were flagged as drift.

**R110-278 adds `.mase/` as a 4th source-anchor directory** with
a skip-list of data-only subdirs (pipeline/, workflow_runs/, etc.)
that contain runtime/data artifacts where literals appear
incidentally (e.g. `issue_db.json` tracks previously-found
issues, `workflow_runs/*.json` records past test outputs).

## The bug

`check_spec_drift()` (and the reverse variant) iterated over
`search_dirs = [recipe/, tools/, docs/]`. Any literal that
exists in `.mase/` (which is the framework's canonical source
for workflows, MCP server code, dashboard HTML, best-practices
YAML, etc.) but NOT in recipe/tools/docs was flagged as drift.

```python
# BEFORE R110-278:
search_dirs = [
    os.path.join(repo_root, 'recipe'),
    os.path.join(repo_root, 'tools'),
    os.path.join(repo_root, 'docs'),
]
# Problem: 9 of 35 SD-test findings had literals in .mase/ but
# not in recipe/tools/docs. The detector couldn't find them.
```

## The fix (1 source change, +36/-3)

```python
# AFTER R110-278:
search_dirs = [
    os.path.join(repo_root, 'recipe'),
    os.path.join(repo_root, 'tools'),
    os.path.join(repo_root, 'docs'),
    # R110-278: add .mase/ as a 4th source-anchor dir. The mas-engineer
    # framework canonical sources (workflows.yaml, mcp/server.js,
    # best-practices.yaml, validation.yaml, etc.) live here. Without
    # this, test literals like "Consumer" (workflows.yaml desc),
    # "inputSchema" (mcp/server.js JSON-RPC spec), or
    # "__WORKSPACE_PLACEHOLDER__" (mcp/dashboard.html) are flagged
    # as drift even though they ARE in the canonical source.
    os.path.join(repo_root, '.mase'),
]
# Skip data-only subdirs of .mase/ — those are runtime artifacts,
# not source-of-truth. workflow_runs/ alone has 6123 files, would
# blow scan time to 5+ min AND mask real drift with incidental
# literal matches in data files.
_SD_DATA_DIRS = {
    'pipeline', 'workflow_runs', 'phoenix_logs', 'checkpoints',
    'mq', 'backups', 'coverage', 'dashboards', 'im', 'recovery',
}
# os.walk uses `dirs[:] = []` to actually prune (not just `continue`).
```

## E2E result: PASS

```
1. python3 tools/dev_im_finder_scan.py → 26 findings (was 35, -9 = -26%)
   - SD-test: 35 → 26 (-9 false-positives eliminated)
2. pytest tests/test_dev_im_finder_scan_lib.py
   → 75 passed in 224.07s (was 71, +4 new R110-278 tests)
3. SD-test findings (before R110-278): 35
4. SD-test findings (after R110-278):  26
5. Scanner runtime: ~75s (with dirs[:]=[] prune of workflow_runs/)
```

## 4 unit tests added (`tests/test_dev_im_finder_scan_lib.py`, +147/-0, section 18)

1. **`test_sd_test_mase_added_to_search_dirs`** — source-inspection test: the `search_dirs` list in `dev_im_finder_scan.py` must include `.mase/` as a 4th entry. Catches regressions where someone reverts the change.

2. **`test_sd_test_data_dirs_skip_list_present`** — source-inspection test: `_SD_DATA_DIRS` set exists and includes the critical data-dirs (pipeline, workflow_runs, backups, coverage, phoenix_logs, mq, dashboards). Without the skip-list, workflow_runs/ (6123 files) would slow the scanner to 5+ minutes AND mask real drift with incidentally-matched literals.

3. **`test_sd_test_mase_data_dirs_excluded_via_dirs_prune`** — source-inspection test: the `os.walk` loop uses `dirs[:] = []` to actually PRUNE the walk (not just `continue`). This is a subtle bug — `continue` doesn't prevent os.walk from descending into a directory, only `dirs[:] = []` does. Caught during initial development: first attempt used `continue` and timed out at 5+ min.

4. **`test_sd_test_mase_integration_findings_reduced`** — **end-to-end integration test**: spawns the actual scanner as a subprocess, parses the JSON output, and asserts the total finding count is ≤30. This is the strongest test — it proves the whole pipeline (search_dirs + skip-list + dirs[:] prune) works in the FULL scanner run, not just in isolation. Threshold ≤30 gives regression margin (was 35 before, 26 after).

## Findings breakdown (after R110-278)

| Type      | R110-277 | R110-278 | Delta |
|-----------|----------|----------|-------|
| NN1       | 1        | 1        | 0     |
| NN3       | 0        | 0        | 0     |
| Q4c       | 0        | 0        | 0     |
| SD-recipe | 0        | 0        | 0     |
| SD-test   | 35       | 26       | **-9** |
| **Total** | **36**   | **27**   | **-9** |

## Why this commit exists (R110-261 lesson applied)

The 9 eliminated findings are real false-positives in a high-traffic
detector (R110-269/270/276/277 all touched the same `check_spec_drift()`
function). 9/35 = 26% of the findings were noise. Each one costs the
user a manual review cycle ("is this real drift or not?"). At 9 per
commit-cycle, that's hours of wasted attention.

The fix is structural (1 source-code block, 36 lines including
extensive R110-278 comments and the `_SD_DATA_DIRS` skip-list) and
prevents the same false-positive class from re-appearing as the
`.mase/` framework grows.

## Files (2)

- `mas-engineer/tools/dev_im_finder_scan.py` (1523 to 1556 lines, +36/-3: 3 patches in check_spec_drift() — search_dirs append, _SD_DATA_DIRS definition, dirs[:]=[] prune in os.walk)
- `mas-engineer/tests/test_dev_im_finder_scan_lib.py` (918 to 1065 lines, +147/-0: 4 new unit tests in section 18, with 2 test-bug fixes during dev — test 2 regex matched too-greedy on `\{[^}]+\}`, test 3 anchored on `_SD_DATA_DIRS` which has 2 occurrences)

## Pre-push-gate status

| Step | Status |
|------|--------|
| Step 0 (secret scan) | OK 0 secrets |
| Step 1 (goose pre-push-validator) | OK 133/133 PASS (100%, 84.8s) |
| Step 2 (pytest tests/test_dev_im_finder_scan_lib.py, 75 in directly-touched file) | OK 75/75 (224.07s) |
| Step 3 (commit msg, 🔧 R-format + 5-section body) | OK per protocol |
| Step 4 (push) | pending |
| Step 5 (post-flight audit) | pending |

## Body-claim verification (R110-174 applied)

All numbers in this commit body verified BEFORE writing:

| Claim | Source | Verified |
|-------|--------|----------|
| +36/-3 in scanner | `git diff --numstat mas-engineer/tools/dev_im_finder_scan.py` | ✓ |
| +147/-0 in tests | `git diff --numstat mas-engineer/tests/test_dev_im_finder_scan_lib.py` | ✓ |
| 75/75 tests pass | `pytest tests/test_dev_im_finder_scan_lib.py -q` | ✓ |
| 35→26 findings | `python3 tools/dev_im_finder_scan.py` JSON output | ✓ |
| 9 false-positives | 35 - 26 = 9 | ✓ |
| -26% | 9/35 = 0.257 | ✓ |
| 224.07s pytest | actual pytest elapsed | ✓ |
| 84.8s validator | actual goose run elapsed | ✓ |
| 4 new tests | test names in section 18 | ✓ |
| workflow_runs/ has 6123 files | `find .mase/workflow_runs/ -type f \| wc -l` | ✓ |

## Reference

- Skill `detector-threshold-tuning`: 4-bucket categorization
  (real defect / design intent / test-fixture / dogfooding).
  R110-278 falls into "real defect" (the false-positive class is a
  real detector bug, not design intent).
- R110-78 / R110-174: body-claim verification. All numbers
  in this commit body verified via `git diff --numstat` and
  actual pytest output.
- R110-261: EVIDENCE.md in the same/follow-up commit.
- Skill `mas-engineer-cleanup-sprint`: how to identify and clean
  up redundant or false-positive findings.
