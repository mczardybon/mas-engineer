# R110-274 — NN1 scope-restriction (4 tests, 19 false-positives eliminated)

## Summary

R110-274 fixes the NN1 detector's false-positive problem. The detector
flagged 19 issues in R110-273, but 18 of those were sub-recipes in
`recipe/sub/` which are by-design sub-agents (not orchestrators that
need splitting). The detector was naively counting 5+ role-verbs in
ANY recipe, regardless of whether it was a top-level orchestrator or
a focused sub-agent.

The fix: NN1 now only flags `recipe/*.yaml` at the TOP level. Sub-
recipes in `recipe/sub/` and workflow recipes in `recipe/wf_*.yaml`
are skipped because they are by-design orchestrators/sub-agents.

## Files changed (2)

| File | +/− | Purpose |
|---|---|---|
| `tools/dev_im_finder_scan.py` | +9/−0 | NN1 scope-restriction: skip `recipe/sub/` and `recipe/wf_*.yaml` |
| `tests/test_dev_im_finder_scan_lib.py` | +86/−0 | NEW: 4 unit tests for the path filter |

## Impact

| Metric | Pre R110-274 | Post R110-274 | Delta |
|---|---|---|---|
| Total findings | 106 | 86 | -20 |
| NN1 findings | 19 | 1 | -18 |
| False-positive NN1 | 18 (sub-recipes) | 0 | -18 |
| True-positive NN1 | 1 (dev-mas-engineer-30agents) | 1 | 0 |

The remaining 1 NN1 finding (`recipe/dev-mas-engineer-30agents.yaml`)
is a real orchestrator with 30 agents — it should be split into
sub-orchestrators. This is a legitimate finding, not a false positive.

## Pitfalls discovered & fixed during R110-274

1. **Path filter bug**: First fix used `/recipe/sub/` (leading slash),
   but `ALL_YAMLS` contains RELATIVE paths like `recipe/sub/foo.yaml`,
   not absolute. The filter did not match. Fixed by removing the
   leading slash. Tests would have caught this if they had been
   written before the code change — but the bug was discovered via
   the real scanner output (19 → 19, not 19 → 1).

2. **Test-isolation gap**: 4 unit tests verify the path-filter
   string matching logic, but they don't run the actual `main()`
   scanner. The real verification came from running the scanner and
   inspecting the JSON output. For R110-275, consider an integration
   test that monkey-patches `ALL_YAMLS` and re-runs the NN1 loop.

## Tests (4, all passing in 14.89s full pre-flight)

1. `test_nn1_skips_recipe_sub_dir` — sub-recipe paths match the filter
2. `test_nn1_skips_recipe_wf_prefix` — wf_* paths match the filter
3. `test_nn1_still_flags_top_level_recipe` — top-level recipes don't match
4. `test_nn1_path_filter_uses_forward_slashes` — Windows backslash compat

## Verification (R110-174 body-claim)

- 2 source files: +95 (git diff --stat to verify on commit)
- 4 new tests pass (pre-flight 96/96 in 14.89s, 5 test files)
- Real scanner run: NN1 findings went 19 → 1 (verified via JSON output)
- 0 regressions (existing 92 tests still pass)

## Open follow-ups (R110-275+)

- `dev-mas-engineer-30agents.yaml` is now the only NN1. The 30-agent
  orchestrator is by design but could be split into 3-5 sub-orchestrators
  (e.g. dev/, test/, deploy/) for cleaner responsibility. This is a
  design question, not a code change.
- Add an integration test that monkey-patches `ALL_YAMLS` and re-runs
  the actual NN1 loop (not just the path-filter string check). The
  current unit tests are fast but only verify the substring match.
- Consider a similar scope-restriction for NN3 (4 open issues) — also
  a 5+-verb pattern, likely similar false-positive rate.

## Files

  M tools/dev_im_finder_scan.py                    |  9 +
  M tests/test_dev_im_finder_scan_lib.py           | 86 +++++++++
  2 files changed, 95 insertions(+), 0 deletions(-)

Refs: R110-174, R110-270, R110-271, R110-272, R110-273
