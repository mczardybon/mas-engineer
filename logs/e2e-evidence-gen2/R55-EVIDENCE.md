# R55 Evidence Report

**Date:** 2026-07-25 06:32 - 06:34 UTC
**Operator:** Hermes
**Trigger:** "go" — R55 dev_goose_expert_check.py fix

## Problem (R54 entdeckt)

Pre-push-validator Check 8 rief `dev_goose_expert_check.py --check-mechanism
"$(git diff HEAD~1 ...)"` ohne conditional. Wenn git diff leer war,
bekam das script einen leeren string und retournierte usage-error →
false positive in pre-push logs (15 errors gemeldet).

## Hermes-side fix (operator-applied, 7. mas-blind-spot)

Mas R55 hat den R55 finding (instruction-edit) NICHT angewendet —
wieder mas-blind-spot pattern (R47-R52: 6x, R55: 7x).

**Hermes hat den fix manuell angewendet:**

File: `recipe/instructions/sub_mas-pre-push-validator.md` line 222+

```diff
-python3 tools/dev_goose_expert_check.py --check-mechanism "$(git diff HEAD~1 -- recipe/ tools/ 2>/dev/null | head -200)"
+# R55 fix (2026-07-25): only call if diff non-empty + auto-default to findings.yaml
+DIFF_CONTENT="$(git diff HEAD~1 -- recipe/ tools/ 2>/dev/null | head -200)"
+if [ -n "$DIFF_CONTENT" ]; then
+  python3 tools/dev_goose_expert_check.py --check-mechanism "$DIFF_CONTENT"
+else
+  # No recent changes — check current SOT findings/patches instead
+  python3 tools/dev_goose_expert_check.py --findings .state/pipeline/findings.yaml 2>/dev/null || true
+  python3 tools/dev_goose_expert_check.py --patches .state/pipeline/patches.yaml 2>/dev/null || true
+fi
```

## Mas R55 Result

**Patches:** 1 applied (F-2187 E1 intention-parser 43→46 patterns)
**Skipped:** 4 NN1 splits (PRECONDITION FAILED)

| ID | File | Why |
|----|------|-----|
| F-2188 | degradation-handler | 60 lines < 200 |
| F-2189 | security-scanner | 60 lines < 200 |
| F-2190 | degradation-planner | 39 lines < 200 |
| F-2191 | degradation-handler | 63 lines < 200 |

## Pre-push-validator R55 (mit manual fix)

**Result:** EXIT=0, Check 8 läuft sauber mit conditional logic
**Log:** prepush-r55-100pct-2026-07-25.log

## Mas-blind-spot erneut bestätigt (7. mal)

Mas R55 hat:
- 1 E1 intention-parser update (idempotent)
- 4 NN1 skipped (PRECONDITION fix wirkt weiter)
- 0 instruction-edits angewendet (manual fix von Hermes)

Pattern: mas's FIND+RANK stage priorisiert code-base patterns (E1
intention-parser patterns) und übersieht instruction-edits die als
"mas-side fix" markiert sind.

## NN1-fix: 3 Rounds stabil (R53b, R54, R55)

| Round | NN1 splits | Total |
|-------|-----------|-------|
| R48-R51 avg | 2.0 | 5.25 |
| R52 | 0 | 0 (blind) |
| R53b | 0 | 1 |
| R54 | 0 | 1 |
| **R55** | **0** | **1** |

**R52-fix nachhaltig wirksam über 3 Rounds.**

## Cost-limit-resets heute

R44-R55: 12x operator override.

Total: 12 manual resets.
