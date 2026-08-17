# EVENTS.md — body-claim → evidence-file mapping

Quick reference: which evidence file proves which commit-body claim.

## R110-126 (42cda98) — `chore: R110-126 apply`

| Body claim | Evidence file |
|---|---|
| "11/11 regression: phase3_phoenix_log + phase4_escalation" | `tests/results/r110-126-mq-pattern/01-phase3-phase4-regression-11-11.txt` |
| "10/10 key phrases grep-treffer (6 tester + 4 builder)" | `tests/results/r110-126-mq-pattern/02-key-phrases-grep-10-10.txt` (correction: case-insensitive only, see file) |
| "section ## MQ-CONSUMER TEST PATTERN in tester" | `tests/results/r110-126-mq-pattern/02-key-phrases-grep-10-10.txt` (grep -c result) |
| "section ## CROSS-TOPIC AUTO-ESCALATION in builder" | `tests/results/r110-126-mq-pattern/02-key-phrases-grep-10-10.txt` (grep -c result) |
| "1528 passed/16 skipped/0 failed" | `tests/results/r110-171-flake-fix/04-full-suite-pytest-n4.txt` (re-verified 2026-08-17, same hash, code unchanged) |
| "no secrets" | `tests/results/r110-171-flake-fix/06-official-secret-scan.txt` scan 2 + scan 3 |

## R110-171 (3ba2bfd) — `test: R110-171 fix pre-push Check 17 xdist flakes`

| Body claim | Evidence file |
|---|---|
| "2 files +54/-3" | `git show 3ba2bfd --stat` (not in tests/results/, in git itself) |
| "test im_finder_publish_enqueues_message ndjson race root cause" | `tests/results/r110-171-flake-fix/01-phantom-test-names-grep.txt` (also 03-* runs prove post-fix pass) |
| "test backpressure_..._no_extra_throttle GIL race root cause" | `tests/results/r110-171-flake-fix/03-flake-suite-run-{1,2,3}.txt` |
| "3x consecutive 14/14 passed" | `tests/results/r110-171-flake-fix/03-flake-suite-run-{1,2,3}.txt` |
| "1528/16/0 full suite" | `tests/results/r110-171-flake-fix/04-full-suite-pytest-n4.txt` |
| "1544 tests collected, no test count delta" | `tests/results/r110-171-flake-fix/02-pytest-collect-only.txt` + `07-pytest-collect-only-3x.txt` |
| "phantom test_bootstrap_distributes_96_subagents does not exist" | `tests/results/r110-171-flake-fix/01-phantom-test-names-grep.txt` (grep exit 1) |
| "phantom test_recipe_count_matches_subagents does not exist" | `tests/results/r110-171-flake-fix/01-phantom-test-names-grep.txt` (grep exit 1) |
| "no real secrets, no fixture-form" | `tests/results/r110-171-flake-fix/05-secret-scan.txt` + `06-official-secret-scan.txt` (official scanner, 4/4 clean) |

## R110-172 (this commit) — `docs: R110-172 — body-claim evidence standard`

| Body claim | Evidence file |
|---|---|
| "12 evidence files in tests/results/" | `find tests/results -type f` (run during commit, see git ls-files) |
| "pytest -n 4 unveraendert" | `tests/results/r110-171-flake-fix/04-full-suite-pytest-n4.txt` (was generated 2026-08-17, same hash, code unchanged) |
| "no secrets in new files" | `tests/results/r110-171-flake-fix/06-official-secret-scan.txt` scan 4 (target: `tests/results/r110-171-flake-fix/`) |
| "tests/results/ not gitignored" | `git ls-files tests/results/` (run during commit) |

## Maintenance

If a test changes, re-run the affected evidence commands and update
the corresponding `.txt` file. If the body claim becomes wrong,
amend the body (R110-78 spec-drift lesson) AND the file together.
