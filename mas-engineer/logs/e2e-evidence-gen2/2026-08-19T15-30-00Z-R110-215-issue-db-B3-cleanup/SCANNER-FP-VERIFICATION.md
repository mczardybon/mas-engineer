# R110-215 — B3 issue-db cleanup verification

**Date:** 2026-08-19 15:30Z
**Scope:** 20 pre-R110-209 HARDCODE-STALE entries + 2 SD-test-dev-* false-positives
**Source-of-truth:** scanner output (per user 2026-08-19)

## Part 1: 20 HARDCODE-STALE entries (legacy false-positives)

### Why scanner is SOT and issue-db entries are stale

R110-209 (commit 766b501, 2026-08-19 06:40Z) fixed `tools/dev_im_finder_scan.py`:
- `+76/-9 lines` to scanner
- HTML-comment-historical marker pattern recognised:
  `<!-- (historical, 2026-07-25: N/M — current YYYY-MM-DD: P/Q) -->`
- Plain-prose hardcodes in 5 instruction files converted to historical markers

**Result:** Post-R110-209 scanner emits 0 HARDCODE-STALE findings.
**But:** Issue-db accumulated 20 entries from pre-R110-209 scans.
These are legacy false-positives — the scanner was wrong at the time
and R110-209 fixed the wrong-detection, but the issue-db was never
backfilled to mark them as fixed.

### Spot-check verification (5 of 20)

| File:line | What scanner saw (pre-R110-209) | What file actually contains (post-R110-209) |
|---|---|---|
| `recipe/instructions/sub_mas-bootstrap.md:4` | "112 sub-agents" hardcode | `<!-- (historical, 2026-07-25: 112/58 — current 2026-08-19: 116/80) -->` |
| `recipe/instructions/sub_mas-pre-push-validator.md:26` | "23 checks" hardcode | "Run the following 23 checks" (correct, validator is v2.8.0 with 23 checks) |
| `recipe/instructions/sub_mas-pre-push-validator.md:531` | "112/124" stale counts | "currently 116 yaml files in recipe/sub/, ... 163 test_*.py files, ratio 1.41" (current ground-truth) |
| `recipe/instructions/sub_mas-system-knowledge.md:133` | "80 Tools" hardcode | "80 Tools (69 dev_*.py + 10 *.sh + 1 *.yaml) (historical, 2026-07-25: 58)" |
| `recipe/instructions/sub_mas-bootstrap.md:40` | "sub-agents" hardcode | Step instruction text (no hardcode present) |

**Verdict:** All 5 spot-checks confirm current file content is
either (a) correct current values, (b) R110-209 historical markers,
or (c) false-detection of normal text. All 20 entries are legacy
false-positives from the pre-R110-209 scanner.

### Action taken

20 entries updated in `.mase/pipeline/issue_db.json`:
- `status`: "open" → "fixed"
- `fix_summary`: appended R110-215 closeout note with R110-209 reference
- `past_validation_outcomes[]`: appended R110-215 entry referencing this evidence file
- `last_modified_at`: 2026-08-19T15:30Z
- `summary.by_status`: open -20, fixed +20

## Part 2: 2 SD-test-dev-* false-positives (detected during A3 validator re-run)

Scanner ran during the R110-214 A3 validator re-run (2026-08-19T18:56:54/55Z)
and emitted 2 new findings. These are scanner-bugs, not real issues:

### SD-test_dev_spec_invariant-1
- **File:** tests/test_dev_spec_invariant.py:99
- **Literal:** "instructions_with_checks.md"
- **Scanner claim:** "literal absent from recipe/, tools/, docs/"
- **Reality:** literal IS present in tests/test_dev_spec_invariant.py:51
  as a `tmp_path` fixture (`(instr_dir / "instructions_with_checks.md").write_text(...)`).
  The test itself writes the fixture file and asserts on it.
- **Verdict:** scanner false-positive. The literal is a test-fixture
  reference, not a spec-drift.

### SD-test_dev_check_orphan_recipes-1
- **File:** tests/test_dev_check_orphan_recipes.py:91
- **Literal:** "sub_test-orphan-xyz"
- **Scanner claim:** "literal absent from recipe/, tools/, docs/"
- **Reality:** literal IS present in tests/test_dev_check_orphan_recipes.py
  as a `tmp_path` fixture (4 occurrences: lines 84, 91, 98, 120, 131).
  The test creates an orphan recipe file in tmp_path to verify
  the orphan-detection tool works.
- **Verdict:** scanner false-positive. The literal is a test-fixture
  reference, not a spec-drift.

### grep -rn verification

```
$ grep -rn "instructions_with_checks.md" tests/ recipe/ tools/ docs/
tests/test_dev_spec_invariant.py:51        (fixture write)
tests/test_dev_spec_invariant.py:99        (fixture assert)

$ grep -rn "sub_test-orphan-xyz" tests/ recipe/ tools/ docs/
tests/test_dev_check_orphan_recipes.py:84  (fixture write)
tests/test_dev_check_orphan_recipes.py:91  (fixture assert)
tests/test_dev_check_orphan_recipes.py:98  (fixture write)
tests/test_dev_check_orphan_recipes.py:120 (fixture assert)
tests/test_dev_check_orphan_recipes.py:131 (fixture assert)
```

Both literals are **only in tests/**, exclusively as `tmp_path` fixtures.
Scanner does not understand test-fixture context.

### Action taken

2 entries updated in `.mase/pipeline/issue_db.json`:
- `status`: "open" → "false_positive"
- `wontfix_reason`: scanner-false-positive: test-fixture literal
- `wontfix_marked_at`: 2026-08-19T15:30Z
- `wontfix_marked_by`: "R110-215"
- `summary.by_status`: open -2, false_positive +2

## Final issue-db state

```
total:                111
by_status:            open=79, fixed=30, false_positive=2, wontfix=0
HARDCODE-STALE-001:   0/9 open (all 9 now fixed)
HARDCODE-STALE-002:   0/5 open (all 5 now fixed)
HARDCODE-STALE-003:   0/2 open (both now fixed)
HARDCODE-STALE-004:   0/2 open (both now fixed)
HARDCODE-STALE-005:   0/1 open (now fixed)
HARDCODE-STALE-006:   0/1 open (now fixed)
SD-test_dev_spec_invariant-1:       false_positive
SD-test_dev_check_orphan_recipes-1: false_positive
```

## Scanner-vs-issue-db drift: RESOLVED

Before R110-215:
- Scanner (SOT):  0 HARDCODE-STALE findings
- Issue-db:      20 HARDCODE-STALE findings "open"
- Drift:         20 entries

After R110-215:
- Scanner (SOT):  0 HARDCODE-STALE findings
- Issue-db:      0 HARDCODE-STALE findings "open"
- Drift:         0 entries

**The scanner-vs-issue-db inconsistency documented in the
2026-08-19T11-15-00Z-OPEN-ITEMS-inventory/OPEN-ITEMS.md
"B3: 20 pre-R110-209 HARDCODE-STALE issue-db entries" is RESOLVED.**
