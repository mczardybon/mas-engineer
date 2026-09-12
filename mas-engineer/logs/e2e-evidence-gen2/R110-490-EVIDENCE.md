# R110-490-EVIDENCE.md — E2E re-onboarding run after R110-481 refactor (gen2)

## Was wurde gemacht

- Pull der aktuellen cleanup-branch version (R110-483..R110-489, master HEAD 5d04c9d)
- Working tree clean (working in PRIMARY mas-engineer-cleanup/mas-engineer/)
- E2E pre-flight + goose MCP runtime verifiziert
- pytest full sweep tests/ -q --tb=line --color=no --timeout=600 (31:46, 4331 passed + 7 skipped)

## pytest full sweep Ergebnis (4345 collected)

- 4331 PASSED
- 7 SKIPPED
- 11 FAILED (alle pre-existing, nicht durch das onboarding verursacht — siehe R110-491)
- Exit code 1

## Was NICHT behoben wurde in diesem run

- Die 11 pre-existing failures wurden NICHT behoben
- pre-push-gate Check 17 würde BLOCKEN weil 11 fails > 0 fails threshold
- Push wurde deshalb NICHT ausgeführt (per R110-281 / pre-push-gate skill: blocked_reasons first fixen)
- 100% grüner baseline (R110-401: 4331/4331 PASS + 7 SKIP in 1422.79s) ist NICHT mehr erreichbar ohne vorherigen fix-sprint R110-491+

## Empfehlung

- R110-491 sprint starten mit kategorisierten test-fix-batches (siehe memory + R110-490 categorization)
- Per-batch pytest laufen lassen mit --timeout=60 (skill: mas-engineer-pytest-batch-strategy)
- Erst nach 100% grün + pre-push-gate green → push erlauben

## Honest reporting

- Coverage-% aus full sweep 31:46 wurde NICHT neu berechnet (vorheriger run lag mehrere stunden zurück und würde misleading sein)
- Die 11 failures sind in memory dokumentiert (R110-490 categorization)
- Validator state file ist stale (von gestern, pre-onboarding run); muss vor nächstem push aktualisiert werden
