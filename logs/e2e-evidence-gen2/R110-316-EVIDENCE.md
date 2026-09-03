# R110-316 EVIDENCE — 3-source lockstep for RECIPE_EXCLUDE (1 new test)

**Commit:** ab43dbc (origin/mas-t-tests, pushed 2026-09-01)
**Round:** 110 (sprint R110-313..316 = drift-detector + 0-byte-fixture handling)
**Author:** Hermes-MAS-Engineer <Hermes@mas-engineer.local>
**Skill:** mas-engineer-pre-existing-test-fix-3-source-lockstep (R110-316 added
"Failure Mode 3: Generalised 3-source lockstep for any allowlist" section)

## Why this commit exists

R110-315 fixed a single-source allowlist problem: `RECIPE_EXCLUDE` in
`tests/test_unix_test_word.py` was missing the new `sub_-.yaml` 0-byte
test-side-effect fixture. R110-315 added it to RECIPE_EXCLUDE and the
pytest test turned green. R110-316 noticed that the e2e-runner
(`tools/e2e_run_all.py::artifacts`) has a PARALLEL list that was NEVER
in lockstep with `RECIPE_EXCLUDE`. Before R110-316, the 2 lists could
silently disagree: pytest tolerated a 0-byte fixture that e2e silently
dropped (or vice versa). R110-316 added a smoke test that enforces
**A ∪ B ⊇ C** where:
- **A** = `RECIPE_EXCLUDE` in `tests/test_unix_test_word.py`
- **B** = `artifacts` list in `tools/e2e_run_all.py`
- **C** = filesystem reality (`recipe/sub/*.yaml` of size 0)

## Files touched (3)

| File | + | - | Why |
|------|---|---|-----|
| `mas-engineer/tests/test_pre_push_check_1_5_skill_alignment.py` | +125 | 0 | New test `test_check_1_5_recipe_exclude_3_source_lockstep` enforces A ∪ B ⊇ C with explicit diagnostic naming A/B/C sets |
| `mas-engineer/tools/e2e_run_all.py` | +9 | 0 | 1 line code (`recipe/sub/sub_-.yaml` in artifacts) + 8 lines comment explaining R110-316 lockstep role |
| `mas-engineer/.mase/directives/R110-316-recipe-exclude-3-source-lockstep-test.md` | +61 | 0 | Sprint planning doc, force-added per R110-0d57265 pattern (R110-316 was discovered as a side-effect of pre-push gate review, not planned) |
| **Total** | **+195** | **0** | **1 new test, 1 source-list entry, 1 directive** |

## Pre-push-gate status (per mas-engineer-commit-protocol skill)

| Step | What | Result |
|------|------|--------|
| 0 | secret scan, tracked + history | OK 0 secrets |
| 1 | pre-commit hook, staged content | OK PASS (no PAT leak) |
| 2 | pytest `tests/test_pre_push_check_1_5_skill_alignment.py` (12 tests) | OK 12/12 in 0.81s |
| 2b | pytest `tests/test_unix_test_word.py` (negative-case regression) | OK 1/1 PASS (still rejects REAL 0-byte recipe files) |
| 3 | commit msg, conventional `test:` + R-format | OK `test: R110-316 — ...` matches validator Check 1.5 conventional-form allowlist |
| 4 | push via credential-helper | OK (d4bd83c..ab43dbc) |
| 5 | post-flight audit | OK 12/12 still green, 0 secrets in `git show origin/mas-t-tests:...` |

## E2E test (R110-316 specific, synthetic-drift verification)

The new test must be run in BOTH directions before commit (per
skill pitfall #6):

```bash
# State 1: clean (A ∪ B == C)
$ python3 -m pytest tests/test_pre_push_check_1_5_skill_alignment.py::test_check_1_5_recipe_exclude_3_source_lockstep -v
PASSED

# State 2: inject synthetic 0-byte file (C gains a member not in A ∪ B)
$ touch mas-engineer/recipe/sub/sub_NEW_DRIFT.yaml
$ python3 -m pytest tests/test_pre_push_check_1_5_skill_alignment.py::test_check_1_5_recipe_exclude_3_source_lockstep -v
FAILED with diagnostic:
  AssertionError: R110-316 3-source lockstep BROKEN: 0-byte
  recipe/sub/*.yaml files exist that are in NEITHER RECIPE_EXCLUDE (A)
  nor e2e artifacts (B):
      ['sub_NEW_DRIFT.yaml']
    A (RECIPE_EXCLUDE): ['sub_test-agent.yaml', 'sub_-.yaml']
    B (e2e artifacts):  ['recipe/sub/sub_test-agent.yaml', ...]
    C (fs reality):     ['sub_-.yaml', 'sub_NEW_DRIFT.yaml']

# Cleanup + verify back to green
$ rm mas-engineer/recipe/sub/sub_NEW_DRIFT.yaml
$ python3 -m pytest tests/test_pre_push_check_1_5_skill_alignment.py::test_check_1_5_recipe_exclude_3_source_lockstep -v
PASSED
```

This proves the test is NOT vacuous: it catches real drift.

## Targeted pytest summary (R110-316)

```text
tests/test_pre_push_check_1_5_skill_alignment.py::test_check_1_5_recipe_exclude_3_source_lockstep PASSED
tests/test_pre_push_check_1_5_skill_alignment.py::test_check_1_5_emoji_set_aligned_across_3_sources PASSED
tests/test_pre_push_check_1_5_skill_alignment.py::test_check_1_5_detector_conventional_types_match_validator PASSED
... (12/12 PASS)
tests/test_unix_test_word.py::test_all_recipe_files_non_empty PASSED
tests/test_r110_78_verification_theater.py (4 tests) PASSED
tests/test_dev_intention_parser_r110285.py (12 tests) PASSED
... (30/30 PASS, 0 fail, 0 error)
```

## Body-claim verification (R110-305 + R110-173 lesson)

| Claim in body | Verified via | Actual |
|---------------|--------------|--------|
| `+59` for the directive | `git show HEAD --stat \| grep directive` | `+61` (off-by-2) |
| `+125` for the test | `git show HEAD --stat \| grep test_pre_push` | `+125` ✓ |
| `+9` for e2e_run_all.py | `git show HEAD --stat \| grep e2e_run_all` | `+9` ✓ |
| `+195` total | `git show HEAD --stat \| grep "1 file changed"` (sum) | `+195` ✓ |
| `12/12 alignment tests PASS` | `pytest tests/test_pre_push_check_1_5_skill_alignment.py` | `12 passed, 0 failed` ✓ |
| `30/30 targeted pytest PASS` | `pytest tests/test_pre_push_check_1_5_skill_alignment.py tests/test_unix_test_word.py tests/test_r110_78_verification_theater.py` | `30 passed, 0 failed` ✓ |

The `+59 → +61` off-by-2 was caught at body-write time and corrected in
`/tmp/r110-316-msg.txt` before `git commit` (per R110-173 pitfall).
Final commit body claims `+61` for the directive line, consistent
with `git show HEAD --stat`.

## Forward-pointer

- **R110-317** (next, in flight): evidence closure for R110-316
  (this file + STATUS.md entry + CHANGELOG). Skill rule from
  R110-252/253: "After every R-sprint commit, write EVIDENCE.md".
- **R110-318** (potential): proactive SUB-AGENT HOOK so the mas-engineer
  sub-agents that produce 0-byte fixtures document their allowlist
  entries themselves (closes the R110-315/316 drift class at the
  source instead of via a smoke test). NOT in this commit.

## Related

- R110-313: pre-existing red surfaced (drift between validator +
  detector + smoke test on 1.5 emoji set)
- R110-314: validator Check 1.5 4-emoji regex fix
- R110-315: RECIPE_EXCLUDE 0-byte fixture allowlist (single-source fix)
- R110-316: 3-source lockstep smoke test (this commit, multi-source
  enforcement)
- Skill: `mas-engineer-pre-existing-test-fix-3-source-lockstep`
  (Failure Mode 3 added in this round)
- Skill: `pre-push-body-claim-verification` (R110-305 + R110-173
  body-claim drift, used to verify R110-316's `+59 → +61` correction)
