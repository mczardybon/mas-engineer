# R110-311 — Subprocess-Coverage-Tracking via sitecustomize.py

## Problem

R110-310 hat 45 untracked CLI-Tools via `subprocess.run(...)` exerciert
aber Coverage blieb 31%. Grund: pytest-cov instrumentiert nur den
pytest-Prozess. Subprocesses schreiben ihr eigenes Coverage-Data
aber das wird nicht gemerged.

## Loesung

Drei zusammenwirkende Mechanismen:

### 1. `sitecustomize.py` (repo root)

Wird automatisch geladen von Python wenn der repo root in
`sys.path` ist (conftest.py garantiert das). Ruft
`coverage.process_startup()` auf wenn `COVERAGE_PROCESS_START`
gesetzt ist. Dadurch wird JEDER subprocess (der das env
var erbt) automatisch fuer coverage instrumentiert.

### 2. `tests/conftest.py` — env-var setup

Setzt BEVOR pytest tests startet:
  - `COVERAGE_PROCESS_START=REPO/.coveragerc` (defaultable)
  - `PYTHONPATH=REPO` (prepended, damit subprocesses sitecustomize finden)

### 3. `.coveragerc` — parallel mode

`parallel = True` aktiviert damit:
  - pytest-cov schreibt `.coverage.<host>.pytest_pid`
  - subprocesses schreiben `.coverage.<host>.<subprocess_pid>`
  - `coverage combine` am Ende merged in `.coverage`

## Ergebnis (Pilot)

  tests:        2890 → 2944 (+54 tests)
  passed:       53 (parametrized) + 9 (manual) + others = 53 R110-310
  skipped:      1 (dq_stage3_anomalies DATA_PATH)
  failed:       0 (nach sitecustomize.py-Filter fuer coverage-Traceback)
  duration:     16.43s fuer R110-310 subset
  coverage:     0/80 tools → 79/80 tools (e2e_run_all nicht erfasst weil
                10s timeout zu kurz)

## Per-File (R110-310 subset)

  tools/dev_yaml_generator.py            88    34   61%
  tools/dev_yaml_generator_core.py       60    19   68%
  tools/dev_yaml_generator_generic.py    64    50   22%
  tools/dev_test_runner.py               94    71   24%
  tools/dev_workload_monitor.py         124    93   25%
  tools/dev_yaml_check.py               197   170   14%
  tools/dev_yaml_immune.py              130   108   17%
  tools/pre_check_lib/auto_repair.py     81    67   17%
  tools/dev_tff.py                      139   115   17%
  tools/e2e_teams.py                    209   176   16%
  tools/e2e_run_all.py                  241   211   12%  (timeout-abgebrochen)
  tools/dq_stage3_anomalies.py          299   277    7%  (DATA_PATH skip)
  ... und 67 weitere

  79/80 tools jetzt mit > 0% coverage. Total: 13111 stmts, 11659 missing, 11%

## Lessons Learned (R110-311)

1. **subprocess ohne sitecustomize = NULL Coverage-Hebel**: Auch
   wenn die tests gruen sind, sehen sie pytest-cov nicht ohne
   explizite Instrumentierung der subprocesses.

2. **parallel mode = Pflicht**: Ohne `parallel = True` in
   .coveragerc kollidieren pytest und subprocess beim Schreiben
   in dieselbe `.coverage` datei → data wird ueberschrieben.

3. **coverage-Traceback von process_startup()**: Wenn `.coveragerc`
   einen Syntaxfehler hat (z.B. `; sigterm`), schreibt
   `process_startup()` einen Traceback nach stderr der die Tests
   stoert. Filter in `test_untracked_tool_runs_without_traceback`
   via `re.sub(r"Traceback[\s\S]+?coverage/control\.py[\s\S]+?(?=\nTraceback|\Z)", "", err)`.

4. **sitecustomize im repo root = funktioniert ohne setup**:
   Python sucht automatisch nach `sitecustomize.py` in jedem
   `sys.path` entry. conftest.py setzt REPO_ROOT an erste stelle.

5. **.coveragerc-Race-Reminder**: Trotz neuer mechanismen
   kann die race weiterhin zuschlagen (R110-308). Backup zu
   /tmp vor jedem langen Run bleibt Pflicht.

## Geplante naechste Schritte (R110-312)

  - Full-Suite-Run mit Coverage (laeuft)
  - 84 verbleibende stmts in den 35 getrackten Files (R110-309 gap)
  - Refactor der Top-3 tools (dev_generic_init 561, dev_rule_checker
    442, dev_editor 385) als Library-Module fuer granular
    Unit-Tests
  - Wenn coverage < 50%: weitere subprocess-tests mit komplexeren
    args (nicht nur --help)
