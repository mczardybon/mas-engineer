# R47 + R48 Evidence Report

**Date:** 2026-07-24 21:21 - 21:35 UTC
**Operator:** Hermes
**Trigger:** User-feedback "sorge dafür das dies nicht mehr vorkommen kann"

## Problem

R45 (mas round-43) hat 4 directors APPROVED die auf 5 nicht-existente sub_recipes zeigen:
- sub_mas-framework-finder.yaml
- sub_mas-framework-hardener.yaml
- sub_mas-security-{secrets,deserialize,cmd-injection}-scanner.yaml

Coverage sank 50/101 = 49.5%. R46 hat die 5 fehlenden sub-agents erstellt, aber die **strukturelle lücke bleibt:**
1. Pre-push-validator hat keinen Check #12 für sub_recipe-ref-resolution
2. Design-stage in sub_mas-general-improver markiert "caveat" als informational statt blocking
3. NN1 director-patches sind nicht atomar (directors + sub-agents müssen im selben patch-set)

## R47: FIX_SPECIFIC (3 structural fixes)

**Goal:** Direkt anwenden der 3 fixes
**Result:** signal=DONE, 0 patches applied (NO_CHANGES_NEEDED)

**Mas's verdict:**
> "findings_R47_structural.yaml are design-stage concepts — would need to
> go through FULL_IMPROVEMENT or REVIEW pipeline"

**Log:** r47-fix_specific-noop-2026-07-24.log

## R48: FULL_IMPROVEMENT (9 patches)

**Goal:** Gehe durch volle pipeline (FIND→RANK→DESIGN→APPLY) für 3 structural fixes
**Result:** signal=DONE, 9 patches applied, 2 skipped

**Was mas R48 tatsaechlich gemacht hat:**
- 1× E1: sub_mas-intention-parser.yaml (added 5 patterns: pipeline, dashboard, signal, health, rank)
- 2× NN1: degradation-handler split (director + analyzer + reporter + ORIGINAL)
- 2× NN1: dashboard-refresh split (director + data-reader + generator + ORIGINAL)
- 2× NN1 skipped: test-director + security-scanner (already split in R45)
- **NICHT die 3 structural fixes** (Check 12, caveats-are-blocking, NN1-atomic-bundle)

**Analyse:** Mas R48 hat die R47_findings.yaml NICHT in RANK-stage aufgenommen. Stattdessen
verarbeitete R48 R43-draft_findings (1,973 raw findings) und zog die hochst-prioritaten
daraus. Die R47 findings sind design-stage-konzepte, nicht standard-findings — mas's
FIND stage hat sie nicht erkannt.

**Verdict:** R48 war erfolgreich (9 patches), aber hat die user-gewuenschten structural fixes
nicht implementiert. Mas's design-stage hat einen blinden fleck fuer "design-proposals".

**Log:** r48-full_improvement-9patches-2026-07-24.log

## Pre-push-validator (R48)

**Result:** 11/11 checks PASS, e2e 128/128 = 100% (upgraded from 8/8 to 128/128)
**0 blocked, 0 failed**

**Log:** prepush-r48-100pct-2026-07-24.log

## Commit + Push

- 9 files changed (mas's R48 patches) + 7 state files
- e2e upgraded 8/8 → 128/128 (full e2e-suite re-run)
- Pushed to origin/master

## Was Hermes manuell getan hat

- 3 structural fixes als findings_R47_structural.yaml definiert
- R47 gestartet (FIX_SPECIFIC) → mas hat abgelehnt mit "design-stage concepts"
- R48 gestartet (FULL_IMPROVEMENT) → 9 patches, aber NICHT die 3 fixes
- Pre-push-validator manuell ausgefuehrt: 128/128 PASS
- Commit + push

## Was bleibt fuer R49+

- **Check 12: sub_recipe-ref-resolution** in pre-push-validator (manuell verifiziert: 69 refs, 0 broken)
- **Caveats-are-blocking rule** in im-designer stage
- **NN1-atomic-bundle pattern** in im-designer stage

Diese muessen in mas's design-stage integriert werden, was nur mas kann.

## Cost-limit-resets heute (operator override)

- R44 reset (FIX_SPECIFIC no-op, R45 vorbereiten)
- R45 reset (FULL_IMPROVEMENT, draft_findings_R43 verarbeiten)
- R46 reset (5 missing sub_recipes regression-fix)
- R47 reset (3 structural fixes — design proposals)
- R48 reset (FULL_IMPROVEMENT, versuch die 3 fixes via pipeline)

Total: 5 manual resets, alle mit begruendung in metadata.reset_reason.

## Empfehlung

Die 3 structural fixes sind **nicht trivial** — sie erfordern design-stage-aenderungen
in sub_mas-general-improver.yaml die mas's pipeline-internes verhalten aendern. Mas's
FIND+RANK+DESIGN+APPLY pipeline hat einen blinden fleck fuer "design proposals" die
nicht aus dem code-scan kommen, sondern vom operator (Hermes) als konzeptuelle fixes
vorgeschlagen werden.

**Loesungs-ansaetze:**
1. **Hermes-side skill** (post-mas-push audit): sub_recipe_ref_check.py laeuft nach
   jedem mas-push automatisch, mas's fehler werden frueh erkannt
2. **R49: mas mit expliziten design-patches** (nicht als findings, sondern als
   recipe-edits die mas selbst vornehmen muss)
3. **Manual fix durch mas** in einem dedizierten R-Round (kein auto-improvement,
   sondern operator-gesteuerte design-aenderung)
