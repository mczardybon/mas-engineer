# R60 Evidence Report

**Date:** 2026-07-25 08:49 - 08:55 UTC
**Operator:** Hermes
**Trigger:** "R60 — R58 false-positive investigation"

## Problem (R58 entdeckt)

F-2187 E1 intention-parser wurde in R48 als APPLIED markiert, aber in
R58 wieder als OPEN gefunden. Entweder: (a) im-finder re-detected, oder
(b) R48 war nicht applied.

## Mas R60 Result

**0 new patches, 1 idempotent.**

Investigation: F-2187 E1 war bereits in R48 angewendet, aber im-finder
re-detected als false-positive. Fix in R61 (im-finder bug).

| Commit | Files |
|--------|-------|
| f90df0d | recipe/sub/static-analyzer.yaml |
| | recipe/sub/sub_mas-mas-controller.yaml |
| | recipe/sub/sub_mas-recipe-designer.yaml |

## Pattern: idempotent patches

R60 zeigt: mas kann patches erkennen die bereits angewendet wurden
(anti-regression), aber logged es als "0 new patches" — operator muss
manuell verifizieren dass nicht echter regression.
