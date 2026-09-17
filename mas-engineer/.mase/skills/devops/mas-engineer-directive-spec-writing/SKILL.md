---
name: mas-engineer-directive-spec-writing
description: How to write a .mase/directives/R<NR>-<topic>.md file for mas-engineer's IM-pipeline. Use when the user asks to create, update, or extend a directive in mas-engineer/.mase/directives/. Covers 9-section structure, naming convention, idempotenz rules, single-commit-per-spec, and how to avoid the spec-drift-in-direktive-itself trap (R110-78 lesson).
---

## When to use

Load this skill when: How to write a .mase/directives/R<NR>-<topic>.md file for mas-engineer's IM-pipeline. Use when the user asks to create, update, or extend a directive in mas-engineer/.mase/directives/. Covers 9-section structure, naming convention, idempotenz rules, single-commit-per-spec, and how to avoid the spec-drift-in-direktive-itself trap (R110-78 lesson).

For mas-engineer framework development, this skill provides domain-specific guidance that supersedes generic workflows.



# Writing Directives for mas-engineer's IM-Pipeline

A directive is a spec-package consumed by mas-engineer's self-improvement
IM-pipeline (S1 FIND -> S3 RANK -> S4 DESIGN -> S5 VALIDATE -> S7 APPLY).
The user writes the intent + concrete implementation contract; mas-engineer's
im-designer produces the patch.

## When to write a directive

- When a mas-engineer bug is too complex to fix in one IM-pipeline run
  (multiple PHASEN, multiple files, requires new convention)
- When the same fix keeps recurring (spec-drift symptom)
- When a future IM-pipeline run needs a pre-digested spec to avoid
  guessing on the implementation

## When NOT to write a directive

- For one-line bug fixes (just commit, no directive needed)
- For mas-engineer code changes the user wants to do themselves
  (write code, commit, push -- no directive layer)
- For Hermes-side skill updates (those go in skills/, not .mase/directives/)

## Naming convention

```
R<NR>-<topic>.md
```

- `R` = "R-Run" (historically grown, do not change)
- `<NR>` = 3-digit running number (R001, R002, ...)
- `<topic>` = lowercase, hyphen-separated, short

## File location

Directives go in `mas-engineer/.mase/directives/` (NOT at repo root).
This subdir is created on first directive, moved if needed via a
dedicated "move into mas-engineer/" commit.

## 9-Section spec structure (PHASE-specific)

Each DIREKTIVE within the .md file should have these 9 sections:

  1. EXACT FILE + INSERT-POINT (which file to touch, where)
  2. EXTRACT-FUNCTIONS / REGEX / PATTERNS (concrete code shape)
  3. MATCHING / SEARCH LOGIC (deterministic, no guessing)
  4. OUTPUT-SCHEMA / FINDING-SCHEMA (concrete examples)
  5. INTEGRATION HOOK-POINTS (3 places: im-finder, pre-push-validator,
     pytest-hook, etc.)
  6. SEVERITY (P1=blocker, MEDIUM, P3=optional)
  7. IDEMPOTENZ (skip conditions to prevent double-implementation)
  8. TESTING (unit + integration + regression scenarios)
  9. NICHT TUN (anti-patterns, footguns, anti-scope-creep)

Sections 1, 2, 4, 8 must have CONCRETE examples (regex strings,
file paths, function signatures) -- not "the validator should
check that tests are consistent".

Section 7 (IDEMPOTENZ) is critical: it tells mas-engineer how to
detect "this is already implemented, skip the patch". Common pattern:
`test -f tools/dev_foo.py` or `grep -q "def foo" recipe/sub/x.yaml`.

## Commit + push protocol

For each DIREKTIVE extension or 9-section spec:

  1. ONE commit per spec-extension (not batched)
  2. Commit body MUST cite exact numstat, references
  3. Push to `origin/cleanup` only (per user profile rule)
  4. Pre-push secrets check: real + R110-77 truncated fixture form

  Real secrets check: grep -E "sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}"
  R110-77 fixture check: grep -E "sk-[A-Za-z0-9]{3,}\.\.\.[A-Za-z0-9]{3,}|ghp_[A-Za-z0-9]{3,}\.\.\.[A-Za-z0-9]{3,}"

## Spec-Drift-in-Direktive-Itself trap (CRITICAL)

**R110-87 lesson**: When writing a directive, ALL counts in the
directive text must be verified against the actual repo state.
Common drift:

  - "1295 tests as of 2026-08-03" -- was 1277 in reality (18-test delta)
  - "5 sub-agents" -- count via `ls recipe/sub/ | wc -l` to verify
  - "PHASE 2 will take 2 days" -- vague, mas-engineer cannot act

VERIFICATION BEFORE COMMIT:
  - For test counts: `cd mas-engineer && python3 -m pytest tests/ --collect-only -q`
  - For recipe counts: `ls recipe/sub/*.yaml | wc -l` or similar
  - For tool counts: `ls tools/*.py | wc -l`

If the count is wrong in the spec, fix it in a follow-up commit
BEFORE the directive is consumed by mas-engineer's IM-pipeline.

## Single-commit vs multi-commit

Default: ONE commit per scope-unit. Use multiple commits when:

  - Multiple DIREKTIVE sections are added at once (R110-83/84 was
    one commit because both sections are one spec-edition;
    R110-86 + R110-87 were separate because they're different
    scope: status-tracking vs test-fixture-template)
  - The commit body would exceed 4000 chars if combined
  - There's a `git revert -n` need for partial rollback

The user-profile rule (R110-78): "nach count/spec-korrektur-commits
MÜSSEN tests mit-aktualisiert werden" applies to count-FIXES, not
spec-extensions. So adding new 9-section spec to a DIREKTIVE is
one commit, even if it's +232 lines.

## Test-Fixture Template convention

For each directive with a PHASE 1+ testing strategy, create a
template in `mas-engineer/.mase/directives/test-fixtures/` (NOT in
`tests/`). The template is:

  - All tests marked @ pytest.mark.skip
  - File is NON-discoverable by pytest (lives in .mase/directives/,
    not in tests/) -- prevents collect-count inflation
  - mas-engineer copies it to tests/ and removes skip-decorators
    when PHASE is implemented
  - collect-count audit: verify current count with
    `cd mas-engineer && python3 -m pytest tests/ --collect-only -q`
    before writing the template (to document current baseline)

## Reference commit chain (R110-78 example)

8-commit example showing spec-iteration over a single directive:

  - R110-78 (9c73100): spec-drift fix in code
  - R110-79 (04afe4a): create .mase/directives/ at repo root
  - R110-80 (5f9418e): move .mase/directives/ into mas-engineer/
  - R110-81 (b8f8bc7): add WORKFLOW + PHASEN + stop-punkte
  - R110-82 (634f626): add 9-section spec to DIREKTIVE 1
  - R110-83/84 (417650d): add 9-section spec to DIREKTIVE 2+3
  - R110-85 (f5204f5): add .mase/directives/README.md index
  - R110-86 (74c6835): add .mase/directives/STATUS.md tracker
  - R110-87 (db5bdd0): add .mase/directives/test-fixtures/ template

Each commit has:
  - One-scope (one direktive-section or one meta-file)
  - Full commit-body transparency (numstat, secrets check, refs)
  - Push to origin/cleanup only

## Related skills

- `mas-engineer-commit-protocol` -- commit body format, pre-push gate
- `pre-push-gate` -- the complete pre-push gate
- `mas-engineer-workflow` -- mas-engineer dev branch overview
- `im-pipeline` -- what mas-engineer's IM-pipeline does with directives
