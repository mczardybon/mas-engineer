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
- **Status**: ARCHIVED-READY (alle 5 PHASEN done, PHASE 4 hermes
  done, R110-78 lesson komplett geschlossen, R110-123 entries
  updated + this closure summary added)
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
| 3c | STALE-LITERAL Pattern B fix | DONE | 2026-08-04 | 2026-08-04 | R110-121 (sales→dev-team in 3 files + Pattern B bug-fix + 1 Test) | PHASE 3c closed: 0 STALE-LITERAL findings, im-finder L146 false positive fixed |
| 3d | scanner Pattern A+B | DONE | 2026-08-04 | 2026-08-04 | 5b82fab (R110-124) | PHASE 3d closed: dev_im_finder_scan.py:check_hardcode_stale() + check_stale_literal() wrap dev_self_audit Patterns A+B (lazy importlib import), 6 HARDCODE-STALE-* types emit (18 occurrences on recipe/instructions/), 2 new tests pass (1286→1288) |
| 4 | skill update (Hermes) | DONE | 2026-08-03 | 2026-08-03 | (Hermes session) | pre-push-gate skill, R110-77 |

**Overall**: 5/5 mas-engineer PHASEN done, 1/1 hermes PHASE done.
mas-engineer-side: PHASE 1 (R110-94+R110-100) + PHASE 2
(R110-106) + PHASE 3 (R110-118 sub_mas-self-audit + dev_self_audit
+ dev_spec_invariant + Check 18) + PHASE 3b (R110-120 STEP 0.6
self-audit in IM-pipeline) + PHASE 3c (R110-121 STALE-LITERAL
Pattern B fix) + PHASE 3d (R110-124 scanner Pattern A+B
detection in dev_im_finder_scan.py).
hermes-side: PHASE 4 (R110-77 pre-push-gate skill).
**Status: ARCHIVED-READY** — R110-78 spec-drift lesson komplett
geschlossen. Total: 8 R-Nummern (R110-77, R110-94, R110-100,
R110-106, R110-118, R110-120, R110-121, R110-124), 7 commits auf
origin/cleanup (R110-118 + R110-119 in PHASE 3a, R110-120 in
3b, R110-121 in 3c; plus R110-117 dispatch mechanism + R110-116
commit-hygiene + R110-115 RECURSION-GUARD v3). pytest 1284→1286
(+2 net tests: test_step_0_6 in R110-120 + test_pattern_b in
R110-121; R110-118 added +3 incl. Check 18 — 1281→1286 = +5
total, verified 2026-08-04 via pytest --collect-only). 4 BLOCKER
+ 6 STALE-LITERAL + 5 simple-stale HARDCODE = 15 findings gefixt.

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

### R110-121-stale-literal-fix (neu 2026-08-04)
- **Datei**: `R110-121-stale-literal-fix.md` (2026-08-04)
- **Ziel**: STALE-LITERAL Pattern B findings fixen — sales-Beispiele →
  dev-team in 3 files + Pattern B Bug-Fix (R110-78 PHASE 3c closure)
- **Applied**: 2026-08-04 via sub_mas-apply-directive (RECURSION_OVERRIDE=2,
  R110-117 per-directive dispatch, HEAD 4050394)
- **Ausfuehrung**: DIREKTIVE 1 sales→dev-team in sub_mas-team-packager.md
  (Package-Tree L16-25 + Invocation-Example L368-397 inkl. agent_count
  6→5) + HOWTO-TEAM-STANDALONE.md (6 refs) + HOWTO-PACKAGE-TEAM.md
  (8 refs); DIREKTIVE 2 Pattern B fix in dev_self_audit.py (MULTILINE
  path-like index + `./`-prefix + YAML bare-name index mit self-definition
  exclusion); DIREKTIVE 3 +1 Test (test_pattern_b_stale_literal_detected,
  Finding.code statt draft-f.type, R110-120 import-pattern).
- **Status**: R110-78 PHASE 3c = DONE. pytest 1286/1286 PASS,
  registry 9/9 PASS, dev_spec_invariant 0 BLOCKER, dev_self_audit
  20 HARDCODE + 0 STALE-LITERAL, grep 'sub_mas-sales' recipe/+docs/ = 0.

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
- User-discussion (die gehoeren in logs/e2e-results/<session>/
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

## R110-78 lesson — spec-drift = ARCHIVED

R110-78 spec-drift lesson (created 04afe4a R110-79, 528 lines
spec, 2026-08-03) is now FULLY CLOSED with all 6 PHASEN done:

- **PHASE 1** (validator + pytest gate, R110-94 + R110-100):
  27d8cb7 (Check 16+ drift) + c005db6 (Check 17 pytest-count-
  mismatch). spec-drift in commits blockt pre-push.
- **PHASE 2** (SD-* finding type, R110-106): 3b80259.
  dev_im_finder_scan.py:check_spec_drift() findet 7 SD-*
  findings in R110-108 run. im-finder recipe Z.36 ruft
  standalone-script auf.
- **PHASE 3** (sub_mas-self-audit + dev_self_audit +
  dev_spec_invariant + Check 18, R110-118): f4277fc.
  Pattern A (HARDCODE stale literals) + Pattern B (STALE-
  LITERAL no-twin references) + Pattern C (count-assertion
  drift). 4 BLOCKER + 5 simple-stale HARDCODE on first run.
- **PHASE 3b** (self-audit in IM-pipeline, R110-120): 4050394.
  STEP 0.6 in sub_mas-im-finder.md (between 0.5 goose-consult
  and 0.7 write findings), MM9-EXT findings, BLOCKER fail-fast
  vor findings-write. +1 test.
- **PHASE 3c** (STALE-LITERAL Pattern B fix, R110-121): 83e4ce7.
  sales→dev-team examples in 3 files, dev_self_audit.py Pattern
  B bug-fix (YAML bare-name detection), 0 STALE-LITERAL
  findings. +1 test.
- **PHASE 4** (hermes-side skill, R110-77): pre-push-gate skill
  with R110-78 lesson documented.

**Total impact (R110-78 lesson):**
- 7 R-Nummern, 7 commits auf origin/cleanup (R110-118+119 in
  PHASE 3a, R110-120 in 3b, R110-121 in 3c; plus R110-117
  dispatch mechanism + R110-116 commit-hygiene + R110-115
  RECURSION-GUARD v3)
- pytest 1281→1286 (+5 tests across R110-118+120+121: +3 in
  R110-118 incl. Check 18, +1 test_step_0_6 in R110-120,
  +1 test_pattern_b in R110-121; verified 2026-08-04 via
  `pytest --collect-only`: 1286 tests collected)
- 15 findings gefixt: 4 BLOCKER + 6 STALE-LITERAL + 5 simple-
  stale HARDCODE
- 0 STALE-LITERAL findings, 0 BLOCKER in dev_spec_invariant
  (clean), 20 HARDCODE-WARN (canonical/context-dependent, both
  documented per R110-119 context-comment + R110-121 Pattern B
  improvement)

**R110-78 spec-drift lesson = KOMPLETT GESCHLOSSEN + ARCHIVED.**
Future drift will be caught by:
- pre-push Check 16+ (5-cat-drift), Check 17 (pytest-count),
  Check 18 (count-assertion drift)
- im-finder STEP 0.6 (auto-invoke sub_mas-self-audit vor
  findings-write, MM9-EXT findings attached)
- dev_self_audit.py (standalone-invokable for ad-hoc checks)
- dev_im_finder_scan.py:check_spec_drift() (called from im-
  finder recipe Z.36 for SD-* finding type)

## R110-124 — scanner Pattern A+B (MM9-EXT scanner support)

- **Datei**: `R110-124-scanner-pattern-ab.md` (357 lines, 2026-08-04)
- **Ziel**: dev_im_finder_scan.py erkennt HARDCODE-STALE-* (Pattern A)
  + STALE-LITERAL-* (Pattern B) — scanner als single source of truth
  fuer recipe-drift, nicht nur sub_mas-self-audit-agent
- **Applied**: 2026-08-04 via sub_mas-apply-directive (RECURSION_OVERRIDE=2,
  R110-117 per-directive dispatch)
- **Ausfuehrung**: DIREKTIVE 1+2 = check_hardcode_stale() + check_stale_literal()
  in tools/dev_im_finder_scan.py (lazy-import dev_self_audit, reuse
  PATTERN_A_RE/PATTERN_A_ACCEPT_CTX/_is_in_fence/_strip_inline_code/
  _scan_pattern_b/_build_repo_literal_index — kein Reimplementieren,
  R02 consumer/producer); DIREKTIVE 3 = 2 try/except call-sites im
  main flow (nach check_spec_drift_reverse); DIREKTIVE 4 = +2 tests.
- **Abweichungen (R110-116 ehrlich dokumentiert, commit body)**:
  1. STALE-LITERAL severity 'warn' → 'medium' (R28 SEVERITY_FILTER
     default medium,high,blocker wuerde 'warn' still droppen)
  2. STALE-LITERAL e2e-test auf synthetisches Fixture umgestellt
     (Repo hat post-R110-121 0 STALE-LITERAL — Acceptance ">=1" war
     stale, kopiert vom Pre-Fix-Stand "6 STALE-LITERAL")
  3. Helper-Name `_strip_inline_code_inline` (directive-Draft) →
     `_strip_inline_code` (tatsaechlicher Name in dev_self_audit)
- **Status**: DONE. pytest 1288/1288 PASS, registry 9/9 PASS,
  scanner --scope=recipe/instructions/ emittiert HARDCODE-STALE-*
  (>=1; Repo hat 18 Kandidaten) + 0 STALE-LITERAL (korrekt, da
  R110-121 alle gefixt hat; Wrapper verifiziert per synthetischem
  Fixture), dev_self_audit 20 WARN (unveraendert), dev_spec_invariant
  0 BLOCKER.
