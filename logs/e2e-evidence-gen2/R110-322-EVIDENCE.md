# R110-322 EVIDENCE — fix top-level scalar yaml drop in dev_spec_invariant

**Commit:** 7247571 (origin/mas-t-tests, pushed 2026-09-03)
**Round:** 110 (sprint R110-322 = spec-invariant scalar-yaml fix)
**Author:** Hermes-MAS-Engineer <Hermes@mas-engineer.local>
**Skill:** mas-engineer-coverage-push-workflow (R110-320 pattern:
probe with edge-case tests → find latent bug → fix → 1+ regression
tests per bug class)

## Why this commit exists

R110-321 (d56ec64) documented the R110-320 candidate list of 5 CLI
tools with 0% coverage and ≥200 stmts. dev_spec_invariant.py (229
stmts) was item #5 on that list. R110-322 picks it up using the
exact R110-320 pattern: probe with edge-case tests, find a latent
bug, fix it, write 1+ regression tests per bug class.

The bug that surfaced during the probe: a top-level string scalar
in a yaml recipe (e.g. `5 ab here` or `"5 ab here"`) was being
silently dropped by an early-return in
`extract_count_from_recipes()`:

```python
if not isinstance(data, (dict, list)):
    continue
```

But the docstring for the function explicitly promises to scan
"single-line string scalar VALUES of the parsed YAML". A
top-level string IS a single-line string scalar. A recipe whose
entire body is a one-liner count-declaration (e.g. a literal
`5 ab here`) was being silently skipped — a real
spec-drift false negative, exactly the kind of bug the invariant
checker is supposed to prevent.

The fix is a 1-line change: `if not isinstance(data, (dict, list))`
→ `if data is None`. Now `walk(data)` runs on `dict`, `list`, AND
`str` top-level values, matching what the docstring promises.

## Files touched (4)

| File | + | - | Why |
|------|---|---|-----|
| `mas-engineer/tools/dev_spec_invariant.py` | +10 | -1 | `if data is None: continue` (was `if not isinstance(data, (dict, list))`) + 9-line comment block explaining R110-322 |
| `mas-engineer/tests/test_r110322_spec_invariant_scalar_yaml.py` | +188 | 0 | NEW, 8 tests in 3 classes (4 bug-surface + 2 regression + 2 no-regression) |
| `mas-engineer/.mase/directives/R110-322-spec-invariant-scalar-yaml-fix.md` | +247 | 0 | NEW, 9-section spec (Bug/Repro/Fix/Regression-test/Why-now/Cov-delta/Pre-push-gate/Files/Refs/Lessons) |
| `mas-engineer/STATUS.md` | +60 | 0 | R110-322 section appended |
| **Total** | **+505** | **-1** | **2 modified, 2 added** |

## Pre-push-gate status (per pre-push-gate + mas-engineer-commit-protocol skills)

| Step | What | Result |
|------|------|--------|
| 0 | secret scan, tracked + history | OK 0 secrets (dev_spec_invariant.py + test + directive + STATUS.md all clean) |
| 1 | pre-commit hook, staged content | OK PASS (STATUS.md trailing-blank already stripped at body-draft time) |
| 2 | pytest `tests/test_r110322_spec_invariant_scalar_yaml.py` (8 tests) | OK 8/8 in 1.32s |
| 2b | regression sweep — R110-320 (5) + Check-18 (3) + pre-existing dev_spec_invariant (4) | OK 20/20 in 2.46s |
| 2c | cov `tools/dev_spec_invariant.py` | pre=0% (file not in any test) → post=60% (137/229 stmts) |
| 3 | body-claim re-verify (R110-305, 4 rounds) | OK 4/4 rounds stable at +505/-1 (initial draft had +459 wrong; corrected) |
| 4 | `git diff --check` (trailing-whitespace) | OK clean (after `rstrip` on directive + STATUS.md) |
| 5 | commit + push via credential-helper | OK 7247571 pushed, d56ec64..7247571, mas-t-tests |
| 6 | post-flight sub_recipe_ref audit | OK 77/77 refs resolve, 0 broken, 100% coverage |

## Body-claim drift caught and corrected (R110-305 lesson)

Initial body draft claimed:
  test +218 (REAL: +188)
  STATUS +33 (REAL: +60)
  directive +198 (REAL: +247)
  total +459 (REAL: +505)

The 4-round `git diff --cached --numstat` re-verify at body-finalize
time (per R110-305) caught all 4 errors. Updated body to match real
numbers before commit. This is the EXACT failure class R110-305
documents (R110-305/308/309 had the same drift). The re-verify is
the prevention layer; the body-claim-drift detector in the validator
is the detection layer. R110-322 found the drift at the prevention
layer, so the validator never saw it.

## Coverage delta

```
=== tools/dev_spec_invariant.py ===

  Pre-R110-322:    0%     (file not in any test, never imported)
  Post-R110-322:   60%    (137/229 stmts covered, 92 missing)

  Delta:           +60pp  1 file from 0% → 60%
```

The 8 subprocess tests cover:
- the 3 top-level yaml cases (dict, list, str)
- the `None` and `int` top-level cases (regression guard)
- the COUNT_DECLARE_RE matching for `ab`, `cd`, `tests` (blacklisted)
- the full CLI entrypoint through `__main__` (RC=0 vs RC=1 paths)

Missing 92 stmts (out-of-scope for R110-322, candidates for R110-327):
- the `__main__` argparse + JSON dump (lines 197-236, 249-261)
- the `_find_canonical` / git-blame helper (lines 280-298) which
  requires a real git repo
- the instruction-file walk (lines 184-187, 300-304) which is a
  separate code path
- the `to_findings()` docstring-claim-emitting branches (lines
  310-317, 398-410)

R110-322 is the "spec-drift false negative fix" sprint, not the
"100% cov" sprint. The cov-push to 100% is a different goal
(direct-import tests for `to_findings()`, not subprocess CLI
invocations).

## Test pattern (R110-310/R110-320 inheritance)

The 8 regression tests use the subprocess pattern:

```python
proc = subprocess.run(
    [sys.executable, str(TOOL), *args, "--repo-root", str(tmp_repo)],
    cwd=str(REPO_ROOT),
    capture_output=True,
    text=True,
    timeout=20,
)
```

This is the R110-310 pattern: invoke the CLI as a real user
would. Two benefits:
1. **Behavior test** — actually tests the CLI end-to-end (argparse,
   file I/O, exit codes, stdout/stderr) rather than just the
   internal API.
2. **Coverage** — when invoked from a `cwd` that has
   `sitecustomize.py` (R110-311) and `COVERAGE_PROCESS_START` set
   (R110-129 conftest), the subprocess is auto-instrumented and
   its executed lines feed back to the cov report.

This is the pattern R110-320 (e7ef060) used for the 5 R110-320
regression tests on dev_registry_merge.py, and the same pattern
that brought dev_spec_invariant.py from 0% to 60% in this commit.

## R-sprint pattern summary (R110-320 → R110-321 → R110-322)

R110-320: fix UnboundLocalError in dev_registry_merge.empty-findings
          path. 5 regression tests. cov: dev_registry_merge.py from
          0% to ~35%.
R110-321: documentation commit listing the 5 remaining
          0%-cov ≥200-stmt candidates for future R-sprints.
R110-322: pick up candidate #5 (dev_spec_invariant.py). Find a
          latent bug while writing tests. Fix it. 8 regression
          tests in 3 classes. cov: 0% → 60%.

Pattern: each R-sprint takes ONE file, probes it with tests, finds
a latent bug, fixes it, writes 1+ regression tests per bug class,
measures cov delta. Future R110-323+ picks up candidates #1-4 from
the R110-321 list:
  - dev_im_finder_scan.py (1660 stmts, 0% cov)
  - dev_workspace.py (1445 stmts, 0% cov)
  - dev_template_generator.py (901 stmts, 0% cov)
  - dev_dashboard_data.py (566 stmts, 0% cov)

## Refs

- R110-320 (e7ef060) — the R-sprint pattern R110-322 follows
- R110-321 (d56ec64) — the candidate list R110-322 picks up
- R110-310 (3523302) — sitecustomize.py + COVERAGE_PROCESS_START
- R110-311 (subprocess cov pattern) — auto-instruments subprocesses
- R110-129 (conftest chdir + COVERAGE_PROCESS_START) — enables
  the cov pattern to work from any cwd
- R110-303 (CWD-anchored subprocess helper) — the helper pattern
- R110-305 (4-round git diff --numstat re-verify) — caught
  body-claim drift in R110-322
- R110-78 / R110-174 (pre-push body-claim verification) — the
  workflow this commit followed
- R110-281 (force-push-versehen) — committed via credential-helper,
  NO force-push
- Skill: pre-push-gate — full e2e + secret scan + validator rules
- Skill: pre-push-body-claim-verification — 4 rounds of
  `git diff --numstat` + `wc -l` re-verify
- Skill: mas-engineer-coverage-push-workflow — same-scope
  comparison pattern + subprocess-cov limitation note