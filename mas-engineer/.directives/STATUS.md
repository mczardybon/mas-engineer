# Directives Status Tracker

Wird von mas-engineer IM-pipeline automatisch aktualisiert wenn
PHASEN abgeschlossen werden. Auch vom User manuell editierbar
wenn externe commits (z.B. fix-commits aus anderen R-Runs)
eine PHASE effektiv abschliessen.

## Aktive Direktiven

### R110-94-historical-drift-check
- **Datei**: `R110-94-historical-drift-check.md` (211 lines, 2026-08-04)
- **Ziel**: dev_category_drift.py als pre-push-validator Check 16+ integrieren
- **Created**: 27d8cb7 (R110-94, 2026-08-04)
- **Refs**: R110-92 (standalone detector, ee0b242), R110-90 (rebase precedent),
  R110-89 (validator evidence), R110-78 (spec-drift lesson)

| PHASE | DIREKTIVE | Status | Started | Completed | Commit | Effekt |
|---|---|---|---|---|---|---|
| 1 | validator Check 16+ + dev_category_drift.py | DONE | 2026-08-04 | 2026-08-04 | 27d8cb7 | 5-cat-drift in last 30d blockt pre-push |

**Overall**: 1/1 PHASE done (R110-94 komplett). Status: ARCHIVED-READY
(alle 6 acceptance-kriterien 206-212 erfuellt; validator v2.2.0,
Check 16+ in instructions L714-777, drift detector exits 0 mit
drift_count=0 + 4 conform + 479 exempt + 490 total).

Test-fixture-template: `.directives/test-fixtures/test_check_16_drift_template.py`
(5 skip-tests, optional CI-integration, nicht pytest-discoverable solange
in test-fixtures/).

### R110-78-spec-drift
- **Datei**: `R110-78-spec-drift.md` (528 lines, 2026-08-03)
- **Ziel**: mas-engineer spec-drift-resistent machen
- **Created**: 04afe4a (R110-79)
- **Refactoring**: 5f9418e (R110-80), b8f8bc7 (R110-81),
  634f626 (R110-82), 417650d (R110-83/84), f5204f5 (R110-85)
- **Erstellt nach**: 9c73100 (R110-71 spec-drift incident
  admitted)

| PHASE | DIREKTIVE | Status | Started | Completed | Commit | Effekt |
|---|---|---|---|---|---|---|
| 1 | validator + pytest | DONE | 2026-08-03 | 2026-08-04 | 27d8cb7 (R110-94 Check 16+ drift) + c005db6 (R110-100 Check 17 pytest) | spec-drift vor push blocken (drift + pytest-count-mismatch) |
| 2 | SD-* finding | DONE | 2026-08-04 | 2026-08-04 | 3b80259 (R110-106) | spec-drift in IM-scans finden — dev_im_finder_scan.py:check_spec_drift() (4 test-cases), im-finder recipe Z.36 ruft standalone-script auf, 7 SD-* findings in R110-108 run verifiziert |
| 3 | dev_spec_invariant.py | IN-PROGRESS | 2026-08-04 | — | bbc76ca (R110-109 directive, spec-only) | spec fuer R110-110 naechster run; implementiert dann sub_mas-self-audit + dev_spec_invariant.py + Check 18 |
| 4 | skill update (Hermes) | DONE | 2026-08-03 | 2026-08-03 | (Hermes session) | pre-push-gate skill, R110-77 |

**Overall**: 2/3 mas-engineer PHASEN done, 3/4 PHASEN done
(hermes-side: skill-update done; mas-engineer-side: PHASE 1+2 done
via R110-94+R110-100+R110-106; PHASE 3 in-progress via R110-109).

### R110-106-sd-detector-pilot (neu 2026-08-04)
- **Datei**: `R110-106-designer-im-top-n-respect.md` (130 lines, 2026-08-04)
- **Ziel**: SD-detection logic (check_spec_drift) + IM_TOP_N=30 e2e-pilot
- **Created**: 3b80259 (R110-106, 2026-08-04)
- **Effekt**: 2 spec-drifts fixed (F-001 Q4 path, F-022 SD test-literal
  "14 critical checks" -> "17 critical checks"); 4 SD-detector fixture-
  tests; 130 lines follow-up spec fuer im-designer Z.164 hardcoded
  "TOP-5" (R110-107 directive, commit 9136778)

### R110-107-im-designer-top-n-fix (neu 2026-08-04)
- **Datei**: `R110-107-im-designer-top-n-fix.md` (167 lines, 2026-08-04)
- **Ziel**: im-designer Z.164 hardcoded "TOP-5" -> "TOP-N" fix
- **Created**: 9136778 (R110-107, 2026-08-04)
- **Status**: SPEC-DRAFT (no code change yet)
- **Ergebnis R110-107 run**: 0 patches drafted — mas-engineer kann
  recipe-self-bugs nicht selbst fixen (finder sucht code-defects,
  improver lehnt per R06 direct file-writes ab). Architectural fix
  in R110-109 (sub_mas-self-audit).

### R110-108-sd-detector-integration (neu 2026-08-04)
- **Datei**: `R110-108-sd-detector-integration.md` (202 lines, 2026-08-04)
- **Ziel**: SD-detector in sub_mas-im-finder integrieren (R110-78 PHASE 2 spec-compliance)
- **Created**: 391be5b (R110-108, 2026-08-04)
- **Status**: SPEC-DRAFT (DONE confirmed in R110-108 run 2026-08-04 10:53Z:
  recipe/instructions/sub_mas-im-finder.md Z.36 ruft dev_im_finder_scan.py
  auf, 7 SD-* findings in run emittiert). DIREKTIVE 1 (integration) ist
  bereits durch R110-106 commit 3b80259 erfuellt.

### R110-109-self-audit-spec-invariant (neu 2026-08-04)
- **Datei**: `R110-109-self-audit-spec-invariant.md` (238 lines, 2026-08-04)
- **Ziel**: sub_mas-self-audit agent + dev_spec_invariant.py (R110-78 PHASE 3)
- **Created**: bbc76ca (R110-109, 2026-08-04)
- **Status**: SPEC-DRAFT (no code change yet)
- **Ausfuehrung**: R110-110 naechster im-pipeline run drafted + applied
  5 files (4 NEU + 1 modified): sub_mas-self-audit.yaml, instructions,
  dev_self_audit.py, dev_spec_invariant.py, pre-push-validator Check 18.
  R11 GOOSE-EXPERT trigger (type A NEW recipe).

## PHASE-Status-Legende

- `OPEN` -- spec existiert, implementation ausstehend
- `IN-PROGRESS` -- mas-engineer-design-phase laeuft
- `DONE` -- implementation committet + validiert
- `BLOCKED` -- findet statt, aber durch external issue gestoppt
  (z.B. findet eine abhaengigkeit die nicht erfuellt ist)
- `CANCELLED` -- spec wurde verworfen, dokumentiert in commit
  message warum
- `SPEC-DRAFT` -- directive committet, implementation wartet auf
  naechsten im-pipeline run

## Wann wird aktualisiert

- mas-engineer IM-pipeline: am ende jedes runs (S7 SUMMARIZE
  stage) -- wenn ein PHASE commit committet+gepusht+validiert
  ist, wird `Completed` + `Commit` ausgefuellt
- User: manuell, wenn ein PHASE durch fix-commit aus
  anderem R-Run abgeschlossen wurde (z.B. wenn R110-90
  nebenbei PHASE 1 von R110-78 erfuellt)
- IM-pipeline FIND phase: liest diese datei BEVOR sie
  findings emittiert. Wenn alle PHASEN DONE, wird die
  direktive als `STATUS: ARCHIVED` markiert und nicht mehr
  als offener finding emittiert

## Format-Konvention

Pro direktive ein eintrag mit:
- Datei + lines + creation date
- 1-zeilen ziel
- Created commit + alle folgenden refactorings
- Tabelle mit 1 row pro PHASE: PHASE nr, DIREKTIVE name,
  Status, Started, Completed, Commit (hash), Effekt
- "Overall" summary (X/Y PHASEN done)

## Was NICHT hierher

- Implementation details (die gehoeren in commits/diffs)
- Performance metrics (die gehoeren in mas-engineer
  monitoring + dashboard)
- User-discussion (die gehoeren in e2e-results/<session>/
  oder in user-side notes, nicht hier)
- "Was hat NICHT funktioniert" retros (die gehoeren in
  commit messages der jeweiligen fix-commits)
