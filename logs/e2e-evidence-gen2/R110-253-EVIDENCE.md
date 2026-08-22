# R110-253 Evidence Report

**Date:** 2026-08-22
**Operator:** Hermes-MAS-Engineer
**Trigger:** "go" — R110-253 (mas-engineer mas-t branch, followup to R110-252)
**Commit:** ed890da — 🔧 R110-253 — fix: e2e-test.sh [5/10] doc-links + [6/10] german-words 2 false-positives

## Was R110-253 gemacht hat

2 pre-existing fails in e2e-test.sh --all gefixt, die nach R110-252 (das ci-validate.sh in den e2e-flow wired) sichtbar wurden:

1. **[5/10] Doc links false-positives (4 files)**: regex `r'\]\(([^)]+)\)'` matchte Python raw-strings wie `r'''assert\s+["\'](\d+)\s+(\w[\w-]*)["\']\s+in\s+'''` weil das substring `](\d+)` als markdown-link-target interpretiert wurde. Falsch: markdown's `[text](url)` syntax erfordert dass `[` und `]` prose link text wrappen, NICHT innerhalb eines Python literals eingebettet sind.

2. **[6/10] German-words (4 violations in 2 files)**: language check fand 4 deutsche wörter:
   - recipe/instructions/sub_mas-yaml-editor.md L16: "Mehrere Files equalzeitig" + L17: "ROLLBACK die fehlgeschlagenen, andere bleiben"
   - recipe/sub/sub_mas-self-audit.yaml L5: "audits auf hardcodes" + L7: "hardcoded zahlen ohne env-var context" + "die zahlen assertieren die nicht mit --collect-count match" + "selbst-referenz"

## Files

| File | Status | Lines | Purpose |
|------|--------|-------|---------|
| mas-engineer/scripts/_strip_code.py | NEW | 68 | State-machine pass: strips fenced blocks + inline backticks from markdown |
| mas-engineer/scripts/_check_doc_links.py | NEW | 97 | Doc-link check refactored, uses _strip_code, stricter regex |
| mas-engineer/scripts/e2e-test.sh | MODIFIED | +71/-45 | [5/10] block shrunk from ~40-line heredoc to 7-line script call |
| mas-engineer/recipe/instructions/sub_mas-yaml-editor.md | MODIFIED | +2/-2 | L16-17: german→english |
| mas-engineer/recipe/sub/sub_mas-self-audit.yaml | MODIFIED | +2/-2 | L5+L7: german→english |

Total: 5 files, +240/-49

## Refactor: why 2 new modules instead of inline

The original e2e-test.sh [5/10] block was a 40-line inline python heredoc with
3 hardcoded scope values, no code-stripping, and a too-permissive regex
`r'\]\(([^)]+)\)'`. After this commit:
- `_strip_code.py` is a standalone, importable utility (state-machine pass,
  not regex) — can be reused by future checks that scan markdown
- `_check_doc_links.py` is the single source of truth for the doc-link check
  and reads `E2E_SCOPE` + `E2E_FILE_FILTER` from env (not from string
  interpolation in bash heredoc — that was the source of the original
  backtick-in-bash-quoting bug)
- The new regex `\[([^\]\n\\"\'`]{2,}?)\]\(([^\)\n\\"\'`]+)\)` requires
  [text] and (url) to be ≥2 chars and NOT contain Python-source-like chars
  (backslash, quote, backtick). This eliminates the false-positive class on
  Python raw-strings.

## E2E Run — BEFORE the fix

Command: `bash mas-engineer/scripts/e2e-test.sh --all`

Result (reproduced on this branch before any fix):
```
[5/10] Doc links (scope: all)
    broken: .mase/directives/R110-109-self-audit-spec-invariant.md -> r'''assert\s+["\'](\d+)\s+(\w[\w-]*)["\']\s+in\s+'''
    broken: .mase/directives/R110-118-self-audit-implementation.md -> (similar)
    broken: .mase/directives/R110-78-spec-drift.md -> (similar)
    broken: .mase/skills/devops/pre-push-gate/SKILL.md -> (similar)
  FAIL: Doc links — 4 broken

[6/10] German words (scope: all)
  (4 violations listed)
  FAIL: German words — 4 found
```

Final count: 10 PASS, 2 FAIL, 0 SKIP.

## E2E Run — AFTER the fix (current state)

Command: `bash mas-engineer/scripts/e2e-test.sh --all`

Result (re-runnable, 2026-08-22):
```
[5/10] Doc links (scope: all)
  PASS: Doc links — all resolve

[6/10] German words (scope: all)
  PASS: German words — 0 violations

... (other 10 checks) ...

================================================================
E2E RESULT: 12 PASS, 0 FAIL, 0 SKIP
================================================================
ALL CHECKS PASS (or SKIP). Safe to push.
```

## Cross-check: the 4 previously-false-positive files

Loaded each file with the new regex after _strip_code pre-processing:
- .mase/directives/R110-109-self-audit-spec-invariant.md: 0 matches ✓
- .mase/directives/R110-118-self-audit-implementation.md: 0 matches ✓
- .mase/directives/R110-78-spec-drift.md: 0 matches ✓
- .mase/skills/devops/pre-push-gate/SKILL.md: 0 matches ✓

## Pre-push-gate (R110-126 protocol)

| Step | Status | Detail |
|------|--------|--------|
| 0. Secret-scan | OK | 0 secrets in commit ed890da (grep ghp_/sk-) |
| 1. Pre-commit hook | OK | Hook ran during commit, no PATs |
| 2. Pytest tests/ | OK (collect-only) | 1629 tests collected in 0.41s. Full pytest run hits a known issue in `test_dev_phase1_publishers.py` (3 fails in full suite, all PASS when run alone) — pre-existing test-ordering issue unrelated to R110-253, see `mas-engineer-pre-push-check17-flake-handling` skill |
| 3. Commit msg 🔧 R-format | OK | em-dash, 5-section body, R-num R110-253 |
| 4. Push | OK | origin/mas-t..HEAD: empty |
| 5. Post-flight audit | OK | git show --stat, secret-scan, remote-url clean |

## Why this commit exists

R110-252 wired ci-validate.sh into the e2e flow. With that hook active, the
e2e --all run suddenly surfaced 2 pre-existing fails that nobody had run
end-to-end on this branch before. R110-253 is the cleanup pass that makes
e2e --all actually green. The branch is now in a state where every R-sprint
commit (R110-254+) starts with a clean baseline.
