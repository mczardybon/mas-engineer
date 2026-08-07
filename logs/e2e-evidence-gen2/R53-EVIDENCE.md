# R53 Evidence Report

**Date:** 2026-07-25 06:01 - 06:15 UTC
**Operator:** Hermes
**Trigger:** NN1 threshold + skip-list effectiveness test

## Test-Design

R53 sollte zeigen ob R52-fix (NN1 threshold + skip-if-recently-split)
wirkt. Vergleich:
- R48-R51: 5+ NN1 splits per FULL_IMPROVEMENT run
- R53: Anzahl NN1 splits nach fix

## Mas R53 (erster versuch, APPLY_ONLY)

Mas hat RECURSION_OVERRIDE=1 als default erkannt → APPLY_ONLY pfad
(3 idempotent patches). R53a ist KEIN valides test des full pipeline.

## Mas R53b (retry, full pipeline)

Mit RECURSION_OVERRIDE=2 (--params): full pipeline durchlaufen.

### Patches: 1 applied

| ID | Type | File | Status |
|----|------|------|--------|
| F-2187 | E1 | sub_mas-intention-parser.yaml | APPLIED (43→46 patterns) |

### Skipped: 4 (NN1 splits, R52-fix wirkt!)

| ID | File | Why |
|----|------|-----|
| F-2188 | sub_mas-degradation-handler | PRECONDITION FAILED: 60 lines < 200; last split R49; already orchestrator |
| F-2189 | security-scanner | PRECONDITION FAILED: 60 lines < 200; already split |
| F-2190 | sub_mas-degradation-planner | PRECONDITION FAILED: 39 lines < 200; already single-role |
| F-2191 | sub_mas-degradation-handler | PRECONDITION FAILED: 60 lines < 200; last split R49; already orchestrator |

### NN1 splits per round: VERGLEICH

| Round | NN1 splits | Total patches |
|-------|-----------|---------------|
| R48 | 3 | 9 |
| R49 | 2 | 3 |
| R50 | 3 | 5 |
| R51 | 0 (andere) | 4 |
| R52 | 0 (mas-blind) | 0 |
| **R53b** | **0** | **1** |

**NN1 drastisch reduziert** (R48-R51: 8 total → R53: 0).

## Pre-push-validator R53b

**Result:** 8/8 checks PASS (100%), 0 blocked
**Log:** prepush-r53b-100pct-2026-07-25.log

## Was R53 erreicht hat

- **1 patch applied:** intention-parser E1 update (43→46 patterns)
- **4 NN1 splits verhindert** durch PRECONDITION check
- **0 broken YAML**, **0 broken refs**
- **0 NN1 splits** = 100% reduction vs R48-R51 avg

## Cost-limit-resets heute

R44-R53: 10x operator override.

Total: 10 manual resets.

## Fazit: R52-fix erfolgreich

Der mas-side fix wirkt:
- Line threshold (≥200) blockt micro-splits
- Recency guard (5 rounds) blockt re-splits
- Im-finder already_split flag blockt stale NN1 findings

**Empfehlung:** Pattern beibehalten. Bei naechster frequency-spike
(z.B. 10+ findings/R) koennte threshold auf 300 erhoeht werden.
