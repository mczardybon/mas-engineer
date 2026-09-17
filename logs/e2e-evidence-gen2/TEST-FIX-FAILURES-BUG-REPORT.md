# test-fix-failures pipeline — BUG REPORT (2026-07-24)

## Symptom
`goose run --recipe test-fix-failures.yaml --no-session` läuft endlos (27+ min) ohne Fortschritt.

## Verhalten
Der director (`sub_mas-test-fix-failures-director.yaml`) macht:
1. `tree` auf `/workspace/mas-engineer-src/recipe/instructions`
2. `cat health-report-2026-07-23.md` (gibts nicht)
3. `cat BUG-BRIEF-2026-07-23.md`
4. `cat E2E-TESTPLAN.md | head -100`
5. `find recipe/ -name "*.yaml" | sort`
6. Python-check für title/extensions keys auf 5 recipes
7. `ls sub_mas-analytics-reporter.yaml` (gibts nicht)
8. `cat .backups/20260723_222402/sub_mas-analytics-reporter.yaml`

**Ergebnis nach 27 min:** KEIN einziger fix, KEIN delegation-call zum finder/ranker/designer/applier, KEIN output.

## Root cause
Der director nutzt seine reconnaissance-phase um ALLES zu laden, statt die sub-agents zu delegieren. Das ist ein framework-bug in der NN1-director-rolle: die reconnaissance-phase hat keine maximale iteration-anzahl und kein "stop-and-delegate" trigger.

## Vergleichbare Symptome
- e2e-verify-phoenix-fixes director: gleiches verhalten (9+ min reconnaissance, dann gekillt)
- framework-scanner director: kürzere reconnaissance, sagt korrekt "I delegate only" → ist die ausnahme
- test-fix-failures director: endlos reconnaissance ohne delegation

## Workaround (für jetzt)
Test-fix-failures manuell nutzen:
1. `python3 -c "import yaml; ..."` um bugs zu finden
2. manuell fixen via `edit`
3. mit `goose run --recipe X --explain` validieren

## Log evidence
- `e2e-evidence-gen2/test-fix-failures-run.log` (3667 bytes, 100 lines, 27 min, killed)

## Empfohlener Fix (für nächsten mas-run)
- NN1-director pattern braucht eine `max_recon_steps: 5` config option
- Nach 5 reconnaissance-calls MUSS der director delegieren
- Sonst wird reconnaissance-phase zur endlos-schleife
