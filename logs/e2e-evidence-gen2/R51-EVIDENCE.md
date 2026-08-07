# R51 Evidence Report

**Date:** 2026-07-25 05:43 - 05:48 UTC
**Operator:** Hermes
**Trigger:** "go" — R51 FIX_SPECIFIC (consumer-recipes)

## Was Hermes angefordert hat

R51 sollte consumer-recipes auf neue directors zeigen (test-director,
generic-init, intention-parser). Mas R50 hatte explizit als next-step gemeldet:
> "Fix cross-references in wf_team_package workflow steps and update consumer
> recipes (test-director, generic-init, intention-parser) to point to the new
> director agents."

## Was mas R51 tatsaechlich gemacht hat

**4 author-fixes in install-dir** (/root/.config/goose/recipes/sub/):
- sub_mas-e2e-auto-repair-director.yaml — author: removed
- sub_mas-e2e-german-fixes-director.yaml — author: removed
- sub_mas-e2e-phoenix-fixes-director.yaml — author: removed
- sub_mas-test-fix-failures-director.yaml — author: removed

**1 E1 update intention-parser** (in source) — small update

**Mas R51 hat die R51-consumer-fixes IGNORIERT** (5. mal mas-blind-spot).
Stattdessen verarbeitete R51 die round41 author-fixes (19 findings) und
reportete 4 als "needs install-path application".

## R51 Resultat

- Author: lines aus 4 install-dir files entfernt (L01-compliance)
- intention-parser: E1 update
- Consumer-recipes: NICHT geändert (mas-blind-spot bestätigt)

## Pre-push-validator R51

**Result:** 11/11 checks PASS, validation ok:true, 0 blocked
**Log:** prepush-r51-100pct-2026-07-24.log

## Was R51 erreicht hat (positiv)

- 19/19 round41 author-fixes vollständig in install-dir applied (4 jetzt neu, 15 schon vorher)
- L01-compliance: alle recipe-agents ohne author: line
- Goose-runtime-error prevention

## Mas-blind-spot: consumer-fixes werden ignoriert (5. mal)

R47 (FIX_SPECIFIC), R48 (FULL_IMPROVEMENT), R49 (FULL_IMPROVEMENT),
R50 (FULL_IMPROVEMENT), R51 (FIX_SPECIFIC) — alle 5 haben meine design-finds
ignoriert. Mas verarbeitet stattdessen:
- R47: design-proposals → "design-stage concepts, not in scope"
- R48/R49/R50: R43 raw-findings high-frequency patterns
- R51: round41 author-fixes (nicht R51 consumer-fixes)

**Muster:** Mas's FIND+RANK stage priorisiert was im code-base sichtbar ist
(R43 raw, round41 author-fixes) und ignoriert operator-supplied design-fixes.

**Operator mitigation:** Mas-push-post-flight-audit skill laeuft nach jedem push
und verifiziert sub_recipe_refs (catches R45 regression class).

## Cost-limit-resets heute

- R44, R45, R46, R47, R48, R49, R50, R51 (8x operator override)

Total: 8 manual resets.

## Empfehlung

Consumer-recipes (test-director, generic-init, intention-parser) muessen manuell
gefixt werden, oder in einer dedizierten R-Round mit FIX_SPECIFIC und direkter
files-list (kein design-proposal-format). Mas's im-validator akzeptiert nur was
mas's im-finder/RANK stage produziert.

Alternativ: consumer-recipe-fixes als mas-internal e2e-validity-check in
pre-push-validator implementieren (mas-side fix).
