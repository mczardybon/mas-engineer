# R110-323 Evidence — dev_im_finder_scan latent-bug fixes

## 1. Why

R110-321 (d56ec64) picked tools/dev_im_finder_scan.py (1660 stmts,
0% cov) as the next cov-push candidate from the R-sprint queue.
R110-323 took that and probed the scanner for latent bugs. Two
real, narrow bugs were found and fixed. This EVIDENCE.md closes
the evidence gap per the R110-316/318/319 pattern (R-code(🔧) →
R-evidence(📝) → R-prevention(🔧) → R-evidence(📝)).

The R-sprint pattern is now: every code-fix R-commit (🔧) gets
paired with an evidence-closure R-commit (📝) that documents
the bug(s), the fix, the regression tests, and the pre-push
gate results. This is a 2-layer defense: (1) the code-fix
itself + the regression tests lock the bug in; (2) this
EVIDENCE.md creates a discoverable artifact for future readers
who hit a related issue.

## 2. Refs (the loop R110-323 closes)

- R110-321 (d56ec64) — R-sprint candidate list picking R110-323.
  The list was: im_finder_scan(1660), workspace(1445),
  template_generator(901), dashboard_data(566). R110-323 took
  item #1.
- R110-322 (7247571) — the previous R-sprint (spec-invariant
  scalar-yaml fix). R110-323 follows the same pattern:
  probe → find bug → fix + tests → evidence.
- R110-320 (e7ef060) — the R-sprint pattern origin (registry
  merge empty findings fix).
- R110-318 (0fb0fdf) — conftest auto-cleanup of zombie files.
  R110-323 reuses the conftest's R110-129 chdir-to-REPO_ROOT
  and R110-311 subprocess-cov env var setup.
- R110-311 — sitecustomize.py: auto-instrument subprocesses for
  coverage when COVERAGE_PROCESS_START is set.
- R110-310 — subprocess-cov pattern (subprocess.run + cwd +
  inherit env). R110-323 inherits this for the test harness.
- R110-305 — 4-round `git diff --numstat` re-verify protocol.
  R110-323 used this in section 3 below.
- R110-78 — spec-drift detector family. BUG-1 is in
  check_spec_drift_reverse, which is part of the R110-78 lineage.
- R110-114 — the 1,961-findings descriptive-prose lesson.
  BUG-1's conservative-skip pattern follows from here: a
  detector that over-fires on descriptive prose gets its
  signal buried in noise. R110-114 taught us to skip more,
  not less, when the line is clearly a historical reference.

## 3. Pre-push gate (R110-323 commit 53a6144)

- Secrets: 0 in staged diff (grep -cE `sk-[a-f0-9]{30,}|ghp_...` = 0)
- 4 rounds `git diff --numstat` re-verify (R110-305):
    ROUND 1: 2 files / +301 / -4
    ROUND 2: 2 files / +301 / -4  (stable)
    ROUND 3: 2 files / +301 / -4  (stable)
    ROUND 4: 2 files / +301 / -4  (stable)
  Per-file:
    M tools/dev_im_finder_scan.py                       +25 / -4
    A tests/test_r110323_im_finder_scan_bug_fixes.py   +276 (NEW)
- `git diff --check` clean (no trailing whitespace, no merge markers)
- Branch: mas-t-tests (R110-269 branch-lock)
- Push: via credential-helper, NO `https://${GH_PAT}@...` (R110-281)
- Pushed commit: 53a6144 (parent: 2a8842f R110-322-EVIDENCE)

## 4. Body-claim-drift audit (R110-305 protocol)

The R110-322 commit had a body-claim-drift bug: initial draft
said +188/+60/+247/+505 but real was identical after re-measure.
R110-305 protocol was applied: 4 rounds of `git diff --cached
--numstat` re-verify before commit. This R110-323 commit's
numbers were stable from draft through final, no correction
needed.

Specifically checked claims:
  - "2 files changed, 301 insertions(+), 4 deletions(-)" →
    real 2/301/4 ✓ (4/4 rounds)
  - "+25/-4 on tools/dev_im_finder_scan.py" → real +25/-4 ✓
  - "+276 (NEW) on test_r110323_im_finder_scan_bug_fixes.py" →
    real +276 ✓
  - "0 secrets" → `git diff --cached | grep -cE` returned 0 ✓
  - "6/6 R110-323 tests PASS" → pytest tests/test_r110323
    -q returns 6/6 ✓
  - "19/19 cross-sprint sanity" → pytest tests/test_r110323
    + test_r110322 + test_r110320 = 19 passed ✓
  - "Pushed commit: 53a6144" → git log --oneline -1 ✓
  - "parent: 2a8842f" → git log --oneline -2 ✓

## 5. Cov delta

The subprocess-cov pattern (R110-310/R110-322) works end-to-end:
  - sitecustomize.py auto-loaded when subprocess inherited
    COVERAGE_PROCESS_START + PYTHONPATH=REPO_ROOT
  - subprocess wrote 53KB of .coverage data
  - `coverage combine` merged the data

But measuring the actual cov delta is finicky because:
  - The scanner is designed to walk the FULL mas-engineer repo
    (6123+ files in workflow_runs/, 30+ second timeouts when
    run from REPO_ROOT).
  - Running from a tmp_repo with the .coveragerc `source = tools`
    filter excludes the tmp_repo paths from the report.
  - Workaround (run from REPO_ROOT with `--subdir` arg) is
    in-progress but the scanner doesn't have a `--subdir` arg
    today; would need a new R-sprint to add it.

Resolution: cov delta measurement deferred to R110-324
(dev_workspace.py is a smaller, more cov-friendly target).
The R110-323 goal was "lock in the 2 latent-bug fixes", not
"100% cov". The 6 regression tests in
tests/test_r110323_im_finder_scan_bug_fixes.py exercise the
two fix sites (check_spec_drift line 1114, check_spec_drift_reverse
line 1290-1295) and serve as the regression lock.

## 6. Test pattern (subprocess-cov inheritance)

Each test in test_r110323_im_finder_scan_bug_fixes.py:
  1. Builds a minimal recipe/instructions + tests/ + recipe/sub
     layout in a tmp_path (no .mase/ side effects, no real
     repo pollution).
  2. Writes a 1-paragraph recipe + a 1-line test file.
  3. Invokes `python3 tools/dev_im_finder_scan.py --scope=recipe`
     as a real subprocess via subprocess.run (no in-process
     import — R110-310 lesson: tools/ has no `__init__.py` so
     direct import would fail).
  4. Parses the JSON block after the `---JSON_START---` marker
     in stdout.
  5. Filters findings by type prefix (e.g. `SD-recipe_*`) and
     asserts on the count + content.

This pattern is identical to R110-310's dev_spec_invariant
subprocess tests and R110-322's spec_invariant regression
tests. The R110-323 test file's docstring explicitly calls
out this inheritance so future maintainers know to follow
the same shape for R110-324+ (workspace, template_gen, dashboard).

## 7. R-sprint summary (R110-320 → R110-321 → R110-322 → R110-323)

- R110-320 (e7ef060): 🔧 code-fix (registry merge empty
  findings) + 5 tests. First R-sprint of the new pattern.
- R110-321 (d56ec64): 📝 R-sprint candidate list documentation.
  No code changes. Lists 4 candidates for cov-push:
  im_finder_scan(1660), workspace(1445), template_generator(901),
  dashboard_data(566).
- R110-322 (7247571): 🔧 code-fix (spec invariant scalar yaml
  top-level drop) + 8 tests. Same pattern as R110-320.
- R110-322-EVIDENCE (2a8842f, this commit's parent): 📝 evidence
  closure for R110-322.
- R110-323 (53a6144, this commit): 🔧 code-fix (im_finder_scan
  BUG-1 + BUG-2) + 6 tests. Same pattern as R110-320/322.
- R110-323-EVIDENCE (this file): 📝 evidence closure for R110-323.
- R110-324 (next): 🔧 code-fix (dev_workspace.py, 1445 stmts)
  per the R110-321 candidate list.

## 8. R110-323 bug details

### BUG-1: boolean-precedence false-positive (line 1290-1295)

LOCATION: tools/dev_im_finder_scan.py, check_spec_drift_reverse

BEFORE (buggy):
    if re.search(r'R\d+-\d+', line):
        if (re.search(rf'\\bhad\\s+{re.escape(num)}', line)
                or re.search(rf'\\+\\s*{re.escape(num)}\\b', line)
                or re.search(rf'{re.escape(num)}\\s+tests?\\b', line)
                    and 'AFTER' in line):
            continue

The boolean `A or B or C and D` evaluates as `A or B or (C and D)`
because `and` binds tighter than `or`. The (C and D) branch only
fires when the line contains "AFTER". A line like
"R110-271 mentions 1690 tests" (no AFTER, no `+1690`, no `had 1690`):
  A=False, B=False, C=True (matches `1690 tests`), D=False (no AFTER)
  → (C and D) = False → whole OR = False → NOT skipped → FALSE POSITIVE.

AFTER (fixed):
    if re.search(r'R\d+-\d+', line):
        if (re.search(rf'\\bhad\\s+{re.escape(num)}', line)
                or re.search(rf'\\+\\s*{re.escape(num)}\\b', line)
                or (re.search(rf'{re.escape(num)}\\s+tests?\\b', line)
                    and 'AFTER' in line)
                # 4th sub-condition: any count-anchor word on a
                # commit-reference line is a historical reference.
                or re.search(rf'\\b{re.escape(num)}\\s+{re.escape(word)}\\b', line)):
            continue

Added explicit parens for clarity and a 4th sub-condition
`r'\bN \w+\b'` that matches any count-anchor word on a
commit-reference line. Now "R\d+-\d+ AND N <word>" is always
treated as a historical reference.

Regression test: test_historical_ref_with_N_tests_no_AFTER_is_now_skipped
  - Creates a recipe with "Historical note: R110-271 mentions
    1690 tests in this codebase."
  - Runs the scanner.
  - Asserts no SD-recipe finding with "1690" AND "tests" in issue.
  - This test FAILS without the fix (proves the bug is real).
  - This test PASSES with the fix (proves the fix works).

Sanity tests (3):
  - test_historical_ref_with_AFTER_is_skipped (no regression)
  - test_historical_ref_with_had_N_is_skipped (no regression)
  - test_load_bearing_anchor_still_fires (the fix must not
    skip LOAD-BEARING count-anchors that have no R\d+-\d+)

### BUG-2: dead-code branch in .mase/ source-anchor (line 1114)

LOCATION: tools/dev_im_finder_scan.py, check_spec_drift

BEFORE (dead code):
    if d.endswith(os.sep + '.mase') or d == '.mase':

The second arm `d == '.mase'` is unreachable because search_dirs
is built via `os.path.join(repo_root, '.mase')` which always
produces a path with a directory separator. So `d == '.mase'`
is False for every d in search_dirs.

AFTER (dead code removed):
    if d.endswith(os.sep + '.mase'):

Added a R110-323-BUG-2 comment explaining the removal so future
readers know this is intentional and not a regression.

Regression test: test_recipe_subdir_in_mase_still_works
  - Creates a tmp_repo with .mase/pipeline/ + .mase/workflows.yaml.
  - Adds a recipe referencing `canonical_literal_test_marker_xyz`
    (which exists only in .mase/).
  - Runs the scanner.
  - Asserts the scanner doesn't error out on the .mase/
    source-anchor dir.
  - This test passes both BEFORE and AFTER the fix (because the
    dead branch was indeed dead). It serves as a regression
    guard in case someone later tries to "restore" the dead
    branch and breaks the .mase/ source-anchor detection.

## 9. Refs

Skills used:
  - pre-push-gate (full pre-push checklist)
  - pre-push-body-claim-verification (R110-305 4-round numstat)
  - mas-engineer-coverage-push-workflow (R110-321 candidate list)
  - mas-engineer-r110-78-verification-theater-fix (BUG-1
    conservative-skip pattern)
  - mas-engineer-r110-224-pytest-100pct-green-pass (subprocess
    cov pattern inheritance)

Commits referenced:
  - 53a6144 (this commit's code-fix)
  - 2a8842f (R110-322-EVIDENCE, parent)
  - 7247571 (R110-322, code-fix)
  - d56ec64 (R110-321, candidate list)
  - e7ef060 (R110-320, R-sprint pattern origin)
  - 0fb0fdf (R110-318, conftest cleanup + EVIDENCE format)

Lessons applied:
  - R110-78 verification-theater guard (real bug, real test)
  - R110-114 1,961-findings descriptive-prose lesson
    (conservative-skip is the right call)
  - R110-281 force-push-verbot (push via credential-helper)
  - R110-269 branch-lock (mas-t-tests only)
  - R110-305 4-round numstat (no body-claim drift)
  - R110-310 subprocess-cov pattern
  - R110-311 sitecustomize.py (subprocess cov infrastructure)
  - R110-316/318/319 evidence-closure pattern
  - R110-321 cov-push candidate list
  - R110-322 subprocess-cov worked-example (60% on
    dev_spec_invariant.py)