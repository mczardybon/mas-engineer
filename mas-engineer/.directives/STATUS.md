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
| 3 | dev_spec_invariant.py | DONE | 2026-08-04 | 2026-08-04 | R110-118 (sub_mas-self-audit agent + tools/dev_self_audit.py + tools/dev_spec_invariant.py + Check 18 in pre-push) | R110-78 PHASE 3 closed: self-audit agent auditiert recipe/instructions/ (Patterns A/B/C), spec-invariant Check 18 blockt test-vs-recipe count-drift vor push |
| 3b | self-audit in IM-pipeline | DONE | 2026-08-04 | 2026-08-04 | R110-120 (STEP 0.6 in sub_mas-im-finder.md + sub_mas-self-audit in im-finder sub_recipes + test_step_0_6) | PHASE 3b closed: sub_mas-self-audit auto-invoked in improvement-pipeline (im-finder STEP 0.6, MM9-EXT findings, BLOCKER fail-fast vor findings-write) |
| 4 | skill update (Hermes) | DONE | 2026-08-03 | 2026-08-03 | (Hermes session) | pre-push-gate skill, R110-77 |

**Overall**: 3/3 mas-engineer PHASEN done, 3/4 PHASEN done
(hermes-side: skill-update done; mas-engineer-side: PHASE 1+2 done
via R110-94+R110-100+R110-106; PHASE 3 DONE via R110-118
— sub_mas-self-audit agent + dev_self_audit.py + dev_spec_invariant.py
+ pre-push Check 18). R110-78 spec-drift lesson komplett geschlossen.

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
- **Status**: DONE (implemented by R110-118 directive-apply, 2026-08-04)
- **Ausfuehrung**: R110-118 applied via sub_mas-apply-directive (RECURSION_OVERRIDE=2):
  sub_mas-self-audit.yaml + recipe/instructions/sub_mas-self-audit.md +
  tools/dev_self_audit.py (Patterns A/B/C) + tools/dev_spec_invariant.py
  (DIREKTIVE 2) + pre-push-validator Check 18 (DIREKTIVE 3, v2.4.0).
  pytest 1284/1284 PASS, scanner 21 findings (no regression).
  R11 GOOSE-EXPERT trigger (type A NEW recipe) fulfilled.

### R110-120-im-finder-step-0-6 (neu 2026-08-04)
- **Datei**: `R110-120-im-finder-step-0-6.md` (2026-08-04)
- **Ziel**: sub_mas-self-audit in improvement-pipeline auto-invoken —
  im-finder STEP 0.6 (R110-78 PHASE 3b closure)
- **Applied**: 2026-08-04 via sub_mas-apply-directive (RECURSION_OVERRIDE=2,
  R110-117 per-directive dispatch, HEAD 0d3317f)
- **Ausfuehrung**: STEP 0.6 "SELF-AUDIT SPEC-DRIFT CHECK" (~78 lines)
  zwischen STEP 0.5b und STEP 0.7 in sub_mas-im-finder.md (R01 BYPASS,
  MM9-EXT mapping, BLOCKER fail-fast) + sub_mas-self-audit in im-finder
  sub_recipes (3 entries: goose-expert + im-designer + self-audit) +
  test_step_0_6_self_audit_attaches_mm9_ext.
- **Status**: R110-78 PHASE 3b = DONE. pytest 1285/1285 PASS,
  registry 9/9 PASS, dev_spec_invariant 0 BLOCKER,
  dev_self_audit 27 WARN (unchanged, 0 NEW findings).

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

## R110-115 follow-up: R110-116 (commit-hygiene corrections)

- **R110-115** (b00dade): sub_mas-apply-directive + RECURSION-GUARD v3
  + 2 directive tools. pytest 1281/1281 PASS. 6 files +455/-1.
- **R110-116** (this commit): non-breaking follow-up mit ehrlicher
  body-korrektur. b00dade bleibt unveraendert. 3 bugs im detail
  dokumentiert (yaml-parse-error von `<path>` in single-quote,
  log_change() kwarg collision, description-prefix fehlte).
  "EFFECTIVENESS TEST" → "MANUAL WORKAROUND" re-classifiziert.
  File: `docs/architecture/R110-115-b00dade-body-corrections.md`.

## R110-117+118 — self-improvement loop closed

- **R110-117** (690f39e): RECURSION-GUARD v3 wired end-to-end.
  sub_mas-apply-directive in sub_recipes + TASK-DETECTION
  RECURSION_OVERRIDE=1 → +2. e2e dispatch verified.
- **R110-118** (this commit): R110-109 DIREKTIVE 1+2+3 implemented
  via R110-117 dispatch mechanism. 5 new files (sub_mas-self-audit
  agent + dev_self_audit.py + dev_spec_invariant.py + Check 18 test).
  PHASE 3 R110-78 spec-drift = DONE. Standalone spec-invariant
  finds 4 BLOCKER + 5 HARDCODE on first run (sub_mas-bootstrap.md
  "96 sub-agents" stale, pre-push-validator.md "18 checks" hardcoded).
  pytest 1281+3=1284 PASS.
