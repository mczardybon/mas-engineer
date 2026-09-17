# R110-172 — body-claim evidence files standard (reproducible test+scan evidence)

## CONTEXT

R110-126 + R110-171 commit-bodies contained number-claims (e.g.
"11/11 regression tests passed", "1528/16/0 full suite", "10/10 key
phrases grep-hits", "3x consecutive flake-suite clean"). These
numbers were verified at the moment of the push (hermes had the
pytest-output live in the terminal), but AFTER the push only the
body-text existed in git — no reproducible artifact in the
repo. Whoever got the clone could either believe the numbers
or rerun pytest themselves.

Additionally the R110-126 body contains a claim which surfaced
as inaccurate during R110-172 reproduction: "10/10 key phrases"
was wrong for strict-case-grep, only 5/10 exact; 10/10 only
case-insensitive or as section-themes. Body-claim-drift,
not spec-drift, but uncomfortable.

The `mas-engineer-verification-theater-guard` skill (created by
hermes itself) says: "every test-number in a commit-body
must exist as a reproducible artifact, otherwise it is
theater".

This directive establishes the standard: EVERY commit that
asserts test-numbers, scan-results, or grep-hits in the body
MUST commit the corresponding logs to
`tests/results/<R-NR>-<topic>/`.

## TARGET REPO

mas-engineer (mczardybon/mas-engineer)
Branch: mas-mq
Parent-Commit: 3ba2bfd (R110-171)
Ref: R110-126 (42cda98), R110-171 (3ba2bfd), R110-78 (spec-drift
     lesson), R110-100 (check 17 test-count-mismatch)

================================================================
DIRECTIVE 1: tests/results/ LAYOUT-STANDARD
================================================================

Current state: no `tests/results/` dir in the repo. Tests
write their artifacts to tmp dirs (pytest convention) which
are gone after the run. Commit-bodies reference numbers that
are not reproducibly in the repo.

Standard for all future commits with body-claims:

  tests/results/<R-NR>-<short-topic>/
    01-<claim-1>.txt
    02-<claim-2>.txt
    ...
    NN-<claim-N>.txt

Every .txt file has:
  - Date + commit-sha it proves (header)
  - The exact command (verbatim, copy-paste-able)
  - The output (stdout+stderr, complete or relevant tail)
  - A "Conclusion:" line stating which body-claim is
    proven here

Example layout for R110-172 itself (reference):

  tests/results/r110-171-flake-fix/
    01-phantom-test-names-grep.txt
    02-pytest-collect-only.txt
    03-flake-suite-run-1.txt
    03-flake-suite-run-2.txt
    03-flake-suite-run-3.txt
    04-full-suite-pytest-n4.txt
    05-secret-scan.txt
    06-official-secret-scan.txt
  tests/results/r110-126-mq-pattern/
    01-phase3-phase4-regression-11-11.txt
    02-key-phrases-grep-10-10.txt
  tests/results/README.md

================================================================
DIRECTIVE 2: TESTS/RESULTS/ IS NOT GITIGNORED
================================================================

`tests/results/` MUST be tracked (not in .gitignore). It is
the counterpart to `.mase/runtime/` (which is gitignored):
  - `.mase/runtime/` = living state, regenerable, NOT
    reproducible (every run is different)
  - `tests/results/` = proof-fossils, frozen per commit,
    REPRODUCIBLE via the command in the file-header

If a CI-run later updates these files, the git-diff surfaces
it as a warning-signal ("something changed here, is the body
still current?").

================================================================
DIRECTIVE 3: BODY-CLAIM-EVIDENCE LINK
================================================================

Every commit-body making a number-claim MUST have an "EVIDENCE"
block at the end that references the evidence-files:

  EVIDENCE (reproducible via tests/results/<dir>/):
    - 01-...: 11/11 passed in 2.44s
    - 04-...: 1528 passed, 16 skipped, 0 failed in 256.76s
    - 05-...: 4x clean (no real, no fixture-form)

The EVIDENCE-block is OPTIONAL for commits without number-claims
(e.g. pure docs/refactor commits), but MANDATORY for
test/perf/ci commits.

================================================================
DIRECTIVE 4: BACKWARD-COMPATIBLE WITH R110-126 + R110-171
================================================================

R110-126 + R110-171 bodies have NOT yet used the EVIDENCE-block
format. R110-172 fixes this retroactively: the evidence
files are created AFTER-THE-FACT in
tests/results/r110-126-mq-pattern/ and
tests/results/r110-171-flake-fix/. The existing bodies are
NOT amended (git history stays linear + honest — "was at that
time as the body says, evidence was supplied later under
R110-172").

The R110-172 commit contains:
  - tests/results/r110-171-flake-fix/ (7 evidence files)
  - tests/results/r110-126-mq-pattern/ (2 evidence files)
  - tests/results/README.md (standard-documentation)
  - NO code-changes, NO recipe-changes (pure evidence-
    supplement)

================================================================
VERIFICATION (what R110-172 must prove)
================================================================

1. `git show R110-172-sha --stat` shows 9-10 new files under
   tests/results/ and 0 code-changes
2. `python3 -m pytest tests/ -q -n 4` = 1528/16/0 (unchanged)
3. `python3 tools/dev_security_scan.py SCAN secrets tests/results/`
   = issues_found: false
4. `git ls-files tests/results/` lists all files (not
   gitignored)
5. `cat tests/results/r110-171-flake-fix/04-full-suite-pytest-n4.txt
   | grep "1528 passed"` = match
6. `cat tests/results/r110-171-flake-fix/01-phantom-test-names-grep.txt
   | grep "exit code: 1"` = match (proof that phantom-tests
   do not exist)
7. `cat tests/results/r110-126-mq-pattern/01-phase3-phase4-regression-11-11.txt
   | grep "11 passed"` = match

REFERENCES:
  R110-100 (check 17): pytest-count-mismatch was real, now
    with test-count evidence-file also reproducible
  R110-78 (spec-drift): R110-126 body's "10/10 key phrases" was
    inaccurate (case-sensitive). R110-172 documents this honestly
    in tests/results/r110-126-mq-pattern/02-key-phrases-grep-10-10.txt
  mas-engineer-verification-theater-guard skill: defines that
    proofs must be reproducible
