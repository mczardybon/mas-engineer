# R52 Evidence Report

**Date:** 2026-07-25 05:56 - 05:58 UTC
**Operator:** Hermes
**Trigger:** mas-side fix — NN1 threshold + skip-if-recently-split

## Was Hermes angefordert hat

R52 sollte mas's NN1 split-loop stoppen. R48-R51 haben alle 5 die
gleichen agents gesplittet (intention-parser, dashboard-refresh,
degradation-handler, team-packager, test-reporter).

Fix-recipe: 3 instruction-edits in im-designer + im-finder + skip-list.

## Was mas R52 tatsaechlich gemacht hat

**NICHTS.** Mas R52 hat die R52 findings ignoriert (6. mal mas-blind-spot)
und reportete "no patches to apply — all findings already processed".

## Mas-blind-spot dokumentiert (R47-R52 = 6 Rounds)

Pattern: mas's FIND+RANK stage liest keine "instruction-edits" als
findings. Mas verarbeitet was mas's im-finder als NN1/E1/MM2 etc.
emittiert, NICHT was der operator als design-fix vorschlägt.

**Mögliche Ursachen:**
- im-finder scant nur code (YAML/python), nicht instruction .md files
- RANK-stage priorisiert high-frequency patterns aus code-base
- instruction-edits erscheinen nicht im findings-format

## Hermes-side workaround (R52 mas-side fix operator-applied)

Hermes hat die 3 design-fixes manuell angewendet:

### Fix 1: im-designer PRECONDITIONS
- File: recipe/instructions/sub_mas-im-designer.md
- Added: 3 preconditions vor Split-Design Procedure
  1. Line threshold: >= 200 lines instruction section
  2. Recency guard: skip if in skip_recently_split.yaml (< 5 rounds)
  3. Im-finder flag: must have `flagged_by: intention-parser`
     OR `already_split: false`

### Fix 2: im-finder already_split tag
- File: recipe/instructions/sub_mas-im-finder.md
- Added: NN1 detection tags finding with `already_split: true`
  wenn sub_mas-{name}-director.yaml existiert UND name in skip list

### Fix 3: skip_recently_split.yaml
- File: .state/pipeline/skip_recently_split.yaml
- Listed 5 most-recently-split agents mit last_split_round + ts
- Expiry: 5 rounds (≈ 5 FULL_IMPROVEMENT runs)

## Pre-push-validator R52

**Result:** 11/11 checks PASS, 137/137 e2e (100%), 0 blocked
**Log:** prepush-r52-100pct-2026-07-25.log

## Was R52 erreicht hat (positiv)

- 3 design-fixes manuell angewendet (instruction-edits + skip-list)
- NN1 wird ab R53+ throttled (200 lines minimum, skip-list)
- 0 broken YAML, 0 broken refs, 100% coverage

## Erwartete Wirkung R53+

- intention-parser, dashboard-refresh, degradation-handler:
  - skip-list aktiv fuer 5 rounds (R52-R56)
  - line-threshold meist under 200, also skip
- team-packager, test-reporter:
  - line-threshold je nach instruction-laenge
  - skip-list fuer R52-R56
- R53-R56 sollten **deutlich weniger NN1 splits** produzieren
  (frequency-counter priorisiert was im code-base ist, skip-list
   + threshold reduziert eligible candidates)

## Cost-limit-resets heute

- R44, R45, R46, R47, R48, R49, R50, R51, R52 (9x operator override)

Total: 9 manual resets.

## Empfehlung

R53 monitoren: wenn NN1 patches von ~5/R auf ~1-2/R fallen, ist der fix wirksam.
Wenn nicht: weitere threshold-anpassung noetig (z.B. 300 lines minimum).

Alternative: NN1 komplett deaktivieren wenn split_history >= 2.
