# R110-206 — Extend dev_spec_invariant.py (Check 18) to also scan recipe/instructions/*.md and test-docstrings (R110-118 scope-gap closure)

## Context (the bug R110-205 just exposed)

R110-118 DIREKTIVE 2 implemented Check 18 (`tools/dev_spec_invariant.py`)
to detect spec-drift between:

- test-files (`tests/*.py`): `assert "N type" in ...` literals
- recipe-files (`recipe/sub/*.yaml`): `(\d+)\s+(\w[\w-]*)` on
  single-line YAML scalar values

This is the machine-checkable core of R110-78 spec-drift resistance
and it works — except it has a SCOPE GAP that R110-205 just hit:

The pre-push-validator v2.7.0 description + prompt say "22 critical
checks" in 3 places:
  - recipe/sub/sub_mas-pre-push-validator.yaml (yaml, 22)
  - recipe/instructions/sub_mas-pre-push-validator.md (markdown, 21) ❌
  - tests/test_sub_mas_pre_push_validator.py (test docstring, 18) ❌❌

Two stale literals survived for weeks because:
  - The .md instruction file is NEITHER scanned by Check 18
    (no .py/.yaml file).
  - The test file's "18 critical checks" is in a DOCSTRING at the top
    of the file, NOT in an `assert "N type" in ...` literal. Check 18
    Extract a) only matches the `assert "N type" in` form, so the
    docstring "18 critical checks" is invisible to it.

R110-205 fixed the literals manually. R110-206 is the PREVENTION:
extend Check 18 to catch this class of drift structurally so the
next divergence is a machine-blocker, not a manual fix.

## Goal (DETECTION → CORRECTION → PREVENTION)

1. **DETECTION (today)**: Check 18 ran, exit 0. F-082 (the
   "21 vs 22 vs 18" drift) was caught by R110-204 phase-1 SCAN
   (`dev_im_finder_scan.py`), NOT by Check 18. Check 18 was
   structurally blind to it.

2. **CORRECTION (R110-205)**: manual 3-line edits across 3 files
   to reconcile the count to 22. Should have been a Check 18 BLOCKER.

3. **PREVENTION (this directive)**: extend `dev_spec_invariant.py`
   with two new extract-functions, add a new invariant-check loop,
   and add 4 pytest cases. Future drifts in either scope will be
   caught at pre-push time, with a clear BLOCKER message naming
   the diverged files.

## Required changes (4 files)

### 1. `tools/dev_spec_invariant.py` (MODIFIED, +2 extract-functions)

Add 2 new extract-functions and extend the invariant-check loop:

**a) `extract_count_from_instructions(instructions_dir)`** — scan
`recipe/instructions/*.md` for the `(\d+)\s+(\w[\w-]*)` pattern,
filtered to single-line prose (not inside ``` code blocks, not
inside markdown tables, not inside HTML comments). Returns the
same `dict[type, set[count]]` shape as the existing `b)`.

**b) `extract_count_from_docstrings(tests_dir)`** — scan
`tests/*.py` for `(\d+)\s+(\w[\w-]*)` literals INSIDE module-level
docstrings (the first `"""..."""` at line 1 of a test file). Use
the same `_is_docstring_or_comment` heuristic that's already
imported. Returns the same dict shape.

**c) `run_spec_invariant_check()`** — add both new extractions to
the result. Extend the invariant loop so that the test/docstring
set and the instructions set are ALSO cross-checked against the
recipe counts. The invariant is: for any (file_kind, type, count)
triple, all file_kinds must agree on the count for that type.

### 2. `recipe/instructions/sub_mas-pre-push-validator.md` (MODIFIED, Check 18 block)

Update the "Check 18: spec-invariant" block to mention the new
scope: "test count-assertions AND test-docstrings AND recipe/
instructions/*.md MUST match recipe count-declarations". Keep
the existing `grep -q "check_18_spec_invariant"` idempotency
check (R110-118 self-insert).

### 3. `recipe/sub/sub_mas-pre-push-validator.yaml` (MODIFIED, +scope mention)

Update the description/prompt to mention the broadened scope if
it currently says "test count-assertions vs recipe count-
declarations" — change to "test count-assertions + recipe/
instructions/*.md literals vs recipe count-declarations".

### 4. `tests/test_dev_spec_invariant.py` (NEW, ~100 lines)

Pytest test for the new functions. 4 cases:
  - (a) `extract_count_from_instructions` on a synthetic
    `tests/fixtures/instructions_with_3_checks.md` returns
    `{"checks": {3}}` (3 single-line mentions of "N checks")
  - (b) `extract_count_from_docstrings` on a synthetic test
    file with a module-level docstring containing "22 critical
    checks" returns `{"checks": {22}}`
  - (c) `run_spec_invariant_check` on a repo where instructions
    say "21 checks" but recipes say "22 checks" emits an
    INVARIANT-checks BLOCKER (the F-082 reproduction)
  - (d) Idempotency: a second run on the same repo returns the
    same result set (no duplicate findings)

## Acceptance

- [ ] `python3 tools/dev_spec_invariant.py --repo-root .` still
      exits 0 on current HEAD (F-082 is already manually fixed,
      so 0 findings expected)
- [ ] When a synthetic instruction file with "21 checks" is added
      to a test repo, Check 18 emits INVARIANT-checks BLOCKER
      with the file name in the finding
- [ ] When a synthetic test docstring with "18 critical checks"
      is added, Check 18 emits INVARIANT-checks BLOCKER for the
      docstring scope too
- [ ] `python3 -m pytest tests/test_dev_spec_invariant.py -v`
      shows 4 passed
- [ ] Full pytest: 1614+4 = 1618+ passed, 0 failed
- [ ] pre-push-validator: 22/22 checks still passed
- [ ] No regression in the original 3 test cases in
      `tests/test_pre_push_check_18_spec_invariant.py`

## Why this is a real cycle, not a doc-only fix

R110-78 (DETECTION spec) defined the invariant conceptually.
R110-118 (PREVENTION 1) implemented Check 18 in `dev_spec_
invariant.py` but only for the .py-assert + .yaml-scalar scope.
R110-205 (CORRECTION) manually fixed the 3-source drift.
R110-206 (PREVENTION 2) closes the scope gap so that ANY
literal in test-docstrings OR in `recipe/instructions/*.md` is
now machine-checked against recipes. The next time someone
changes a count in one of these 3 places, the pre-push will
block instead of letting a stale test survive.

## Out of scope (follow-up directives)

- Auto-fixing the drift (writing back the canonical count to
  the diverged file) — too magical, general-improver should
  decide the canonical source via git blame
- Scanning ALL prose, including multi-line descriptions in
  recipe/instructions/*.md — too noisy, single-line only for now
- Scanning test-file non-docstring code comments — also too
  noisy; the docstring extraction is the focused case
- Scanning `recipe/instructions/*.md` tables (markdown tables
  with `| N | type |` rows) — separate directive, R110-207+
- Extending to multi-line YAML scalar values (block strings) —
  R110-208+

## Cross-refs

- R110-78 (spec-drift spec, the original invariant)
- R110-118 (DIREKTIVE 2 = the original Check 18 implementation,
  this directive's scope-gap parent)
- R110-204 (DETECTION→CORRECTION→PREVENTION pattern, sibling
  directive; R110-206 is the same cycle for Check 18 scope)
- R110-205 (CORRECTION for F-082, this directive's WHY)
- F-082 (the BLOCKER finding that proved the scope gap, fixed
  in R110-205)
- MM9-EXT-002 (sibling finding: "21 checks" hardcode in .md,
  same root cause as F-082, resolved by R110-205)
