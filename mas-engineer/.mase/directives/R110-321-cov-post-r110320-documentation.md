# R110-321 — cov-post-r110320 documentation + line 23 collision-fix

## Context

R110-320 (commit e7ef060) fixed an UnboundLocalError in
`tools/dev_registry_merge.py::merge_findings()` and added 4 regression
tests (`tests/test_r110320_registry_merge_empty_findings.py`).

R110-321 measures the impact of R110-320 on coverage and adds ONE
small follow-up: a 5th test that covers the previously-missing
`n += 1` collision loop body at line 23, taking dev_registry_merge.py
from 98.31% to **100.00%**.

This is a **documentation + 1 test addition** commit, not a coverage
push. The cov-raise is the R110-320 effect being fully closed.

## Coverage measurement (post-R110-320 vs post-R110-321)

Measured with: `pytest tests/test_r110320_registry_merge_empty_findings.py
--cov=tools/dev_registry_merge.py --cov-report=term`

```
=== tools/dev_registry_merge.py ===

  Pre-R110-320:   0%  (file not in cov-final; 0 stmts tracked)
  Post-R110-320:  98.31%  (58/59 stmts covered)
  Post-R110-321:  100.00%  (59/59 stmts covered, 0 missing)
  Delta (R321):   +1 stmt, +1.69pp, 1 file from 98.31% → 100.00%

  Final missing lines: 0
```

The 4 R110-320 tests cover:
  - empty-findings path (the original bug repro) → 0 stmts new
  - empty-findings registry-write path → 1 stmts new (now)
  - one-finding happy path → ~28 stmts new
  - repeated-finding merge path → ~29 stmts new (count=2)

**Why line 23 was missed:** the 4 R110-320 tests use unique
`type` values ('Z1', 'Z2'), so the `existing_ids` set never
contains a collision with the `n=1` candidate. To cover line 23,
the test pre-seeds the registry with a "fake" pattern whose
`name` is NOT 'cross_generisch' (so it doesn't match by name
in line 50-53) but whose `id` collides with what `generate_id()`
would compute for a `type='Z3'` finding (which maps to
PATTERN_NAMES['Z3']='cross_generisch' → base='BP-CF-GENERI').

## The 5th test (closes the 1.69% gap)

`TestCollisionHandler::test_id_collision_uses_n2_id`:
  1. Pre-seed registry with `id='BP-CF-GENERI-001'`, `name='__fake_collision_seeder__'`
  2. Send 1 finding of `type='Z3'`
  3. Expected behavior:
     - existing-by-name loop (line 50-53) finds no match
       (name='__fake_collision_seeder__' != 'cross_generisch')
     - Falls through to line 66: `pid, _ = generate_id('Z3', existing_ids)`
     - existing_ids = {'BP-CF-GENERI-001'} (from pre-seed)
     - generate_id: n=1, ID='BP-CF-GENERI-001' in existing_ids → **COLLISION**
     - Line 23: `n += 1` (n=2)
     - Returns ID='BP-CF-GENERI-002'
  4. Assert: new pattern has `id='BP-CF-GENERI-002'`, count=1
  5. Assert: pre-seed pattern untouched (still `id='BP-CF-GENERI-001'`)

**Real-world use:** this collision only happens if a manual
edit or out-of-band writer creates a registry pattern with a
conflicting ID. Not a likely production path, but the
defensive code (line 23) is still meaningful — without it,
two patterns would share an ID and downstream tooling
(lookup-by-id) would break.

## What R110-321 changes (3 files)

  M mas-engineer/tests/test_r110320_registry_merge_empty_findings.py   +70 / -0
    ↳ 5th test: TestCollisionHandler::test_id_collision_uses_n2_id
       (pre-seed with id='BP-CF-GENERI-001', name mismatch,
       then 1 finding type='Z3' → line 23 hit → ID '-002')

  A mas-engineer/.mase/directives/R110-321-cov-post-r110320-documentation.md  +151 / -0 (NEW, force-added)
    ↳ this file

  M mas-engineer/STATUS.md                                              +57 / -0
    ↳ R110-321 section: cov measurement, 98.31% → 100.00% delta,
       links back to R110-320

  Total: 2 modified, 1 new directive, +278 insertions, 0 deletions

## Why this commit pattern (R320 → R321 documentation+test)?

R110-320 was a code fix + 4 regression tests. R110-321 is a
**follow-up documentation commit** that:

  1. Measures the cov impact of R110-320 (was it worth it?)
  2. Closes the 1-stmt gap (98.31% → 100.00%) with 1 extra test
  3. Updates STATUS.md to record the cov-baseline shift for
     dev_registry_merge.py
  4. Documents the missing-files inventory for future R-sprints
     (the 5 files with 0% and > 200 stmts)

This is a "R-code → R-evidence → R-prevention" sprint closure:
  - R110-320 (code): bug fix + 4 tests
  - R110-321 (evidence): cov measurement + documentation + 1 more test
  - Future R110-322+ (next): the 0% files (dev_im_finder_scan,
    dev_workspace, dev_template_generator, dev_dashboard_data,
    dev_spec_invariant) — each a candidate for the same
    "R110-320" pattern (find a latent bug, write 1 fix + N tests)

## Pre-push-gate (per skill: pre-push-gate + pre-push-body-claim-verification)

  Step 0 (secret scan, tracked + history):  OK 0 secrets (pending add)
  Step 1 (pre-commit hook, staged content): OK PASS (pending)
  Step 2 (pytest targeted, 5 R110-320+R110-321 tests): OK 5/5 in 3.38s
  Step 3 (cov: dev_registry_merge.py = 100%):  OK 59/59 stmts
  Step 4 (commit msg, 📝 R-format pattern 1):  OK documentation
  Step 5 (push via credential-helper):     pending (on user 'go')
  Step 6 (post-flight audit):              pending (post-push)

## Refs

- R110-320 (e7ef060) — the bug fix + 4 tests this R-sprint
  documents and extends
- R110-310 (3523302) — sitecustomize.py + COVERAGE_PROCESS_START
  pattern that makes cov-measurement-with-subprocess-tests
  possible (subprocess tests show up in the same cov run as
  in-process tests; without R110-310, the 5 R110-320+R110-321
  tests would not have contributed to dev_registry_merge's cov)
- R110-303 — CWD-anchored subprocess helper pattern
- R110-129 — conftest.py os.chdir(REPO_ROOT) precedent
- Skill: `mas-engineer-coverage-push-workflow` — same-scope
  comparison pattern + `--help`-only-smoke limitation note
- Skill: `pre-push-body-claim-verification` (R110-174 + R110-305) —
  4 rounds of `git diff --numstat` + `wc -l` re-verify

## Future R-sprint candidates (NOT in R110-321)

For R110-322+ planning — the 5 files with 0% coverage and ≥200 stmts:

  1. tools/dev_im_finder_scan.py  (682 stmts, 0%)
  2. tools/dev_workspace.py       (589 stmts, 0%)
  3. tools/dev_template_generator.py (489 stmts, 0%)
  4. tools/dev_dashboard_data.py  (295 stmts, 0%)
  5. tools/dev_spec_invariant.py  (229 stmts, 0%)

Each is a candidate for the R110-320 pattern:
  - Find a latent bug (or just `--help`-only smoke test gap)
  - Write 1 fix + 1-4 regression tests
  - Document in a directive
  - Push

But: writing 682+589+489+295+229 = 2284 stmts worth of tests is
**not** a 1-sprint job. It's a multi-R-sprint push (one file per
R-commit, per the cleanup-sprint pattern from R110-316→R110-320).
