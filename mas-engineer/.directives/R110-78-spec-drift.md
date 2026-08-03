# IM-Pipeline Directiven-Paket fuer mas-engineer
# R110-78 Spec-Drift Lesson (2026-08-03)
# Zweck: mas-engineer selbst beibringen, nach count/version/etc.-korrekturen
# die zugehoerigen tests mit zu updaten, damit keine spec-drift entsteht.

Ziel-Repo: mas-engineer (mczardybon/mas-engineer)
Branch: cleanup
Datum: 2026-08-03
Quelle: R110-78 (commit 9c73100) -- nach R110-71 (commit f6f2f46)
        der recipe-count von 96 auf 110 aenderte ohne die tests mitzuziehen,
        was 2 tests permanent brechen liess.

================================================================
DIREKTIVE 1: sub_mas-pre-push-validator um pytest-step erweitern
================================================================

Aktueller zustand: recipe/sub/sub_mas-pre-push-validator.yaml macht
15 checks (P1-findings, hardcoded-paths, yaml-validity, ...),
aber KEINEN pytest-run. Das ist die luecke die R110-71 spec-drift
entstehen liess: validator gruen, tests rot, push geht durch.

Gewuenschter zustand: ein neuer Check 16 "pytest-run" wird nach
Check 15 (oder am ende der check-liste) eingefuegt, der den
test-tree ausfuehrt und das ergebnis strukturiert festhält.

KONKRETE SPEZIFIKATION (PHASE 1, R110-82 spec):

  1. DATEI: mas-engineer/recipe/sub/sub_mas-pre-push-validator.yaml
     INSERT-POINT: nach dem letzten existierenden check (Check 15
     -- ermitteln via `grep -c "^Check\|check_nr\|id: check" <file>`),
     ALS NEUER CHECK MIT id: check_16_pytest_run

  2. BEFEHL (im neuen check auszufuehren):
       cd <mas-engineer-cwd> && \
       python3 -m pytest tests/ -q --tb=line \
         --color=no 2>&1 | tail -30
     --tb=line: nur 1-zeile traceback pro failure (schoenere logs)
     --color=no: keine ANSI codes in pre_push_validation.yaml
     tail -30: letzte 30 zeilen, reicht fuer fail-summary

  3. OUTPUT-PARSING:
     Expected pytest output format:
       ============================= 1295 passed in 8.32s ==============================
     Parser regex (Python re):
       PASSED_RE   = r"(\d+) passed"
       FAILED_RE   = r"(\d+) failed"
       ERROR_RE    = r"(\d+) error"           # collection errors
       SKIPPED_RE  = r"(\d+) skipped"
       TIME_RE     = r"in ([\d.]+)s"
     Edge cases:
       "no tests ran" -> failed=0, errors=0, passed=0
                         (NICHT als failure werten, sondern loggen
                          "no tests collected")
       pytest not installed -> errors=1, exit code 127
                              (BLOCKED weil es ein umgebungsfehler ist)

  4. STRUKTURIERTER OUTPUT (in pre_push_validation.yaml):
       pytest_summary:
         passed: <int>
         failed: <int>
         errors: <int>
         skipped: <int>
         duration_seconds: <float>
         exit_code: <int>           # 0 = ok, 1 = tests failed, 2 = errors, 5 = no tests
         last_lines: <list[str>]    # letzte 10 zeilen output
         timestamp: <iso8601>

  5. BLOCKED-LOGIK:
       check_16_pytest_run returns BLOCKED iff:
         failed > 0 OR errors > 0 OR exit_code != 0
       sonst return PASSED (auch wenn skipped > 0 oder passed=0).
     Begruendung: skipped tests sind explizit als skip markiert,
     das ist OK. Aber failed ODER errors bedeuten dass der
     spec-drift oder ein anderer test-bug existiert.

  6. INTEGRATION IN VALIDATOR-OUTPUT:
       Im top-level validator-summary:
         status: BLOCKED  (statt "passed" wenn check_16 BLOCKED)
         blocking_checks: ["check_16_pytest_run"]
     Die anderen 15 checks laufen weiter (nicht abgebrochen), damit
     man alle probleme auf einmal sieht.

  7. IDEMPOTENZ / RE-RUN-SAFETY:
       Wenn check_16 schon existiert (vorheriger run hat ihn
       angelegt), kein zweiter insert -- vorheriger beibehalten.
       Detection: `grep -q "check_16_pytest_run" <file>`

  8. WIE TESTEN:
       a) POSITIVE: in mas-engineer/, `python3 -m pytest tests/ -q`
          exit 0, 1295 passed. validator-status: passed.
       b) NEGATIVE: einen test absichtlich brechen (z.B. in
          tests/test_sub_mas_bootstrap.py ein `assert False` einbauen,
          in einem temp-branch, NICHT cleanup). validator-status:
          BLOCKED. Dann revert, status zurueck auf passed.
       c) NO-TESTS: ein package ohne tests/ erzeugt
          exit_code=5, no tests collected. Status: PASSED (das ist
          OK, kein test-coverage ist KEIN fehler fuer jetzt --
          spaeter SD-finding faengt das).

  9. NICHT TUN:
       - KEIN --skip-pytest flag. Wenn jemand den check
         umgehen will, ist das per design BLOCKED. Pytest ist
         PFLICHT im validator.
       - KEINE automatische --collect-only (zu schnell, kann
         collection-errors uebersehen).
       - KEIN pytest-xdist (kein -n auto) -- sequenzielle
         ausfuehrung ist 10s und ermoeglicht deterministische
         failure-tracebacks.

Begruendung: pytest laeuft in ~10s fuer das mas-engineer-test-tree
(1295 tests as of 2026-08-03), das ist billig genug um in jeden
pre-push-validator-run eingebaut zu werden. Es faengt spec-drift
frueh, BEVOR der 90s+ validator-run verschwendet wird.

================================================================
DIREKTIVE 2: SPEC-DRIFT-CHECK in sub_mas-im-finder einbauen
================================================================

Aktueller zustand: im-finder scannt recipes + tools + docs auf
probleme, aber er hat keine spec-drift-detektion. Spec-drift
entsteht wenn ein test etwas altes asserted (z.B. "96 sub-agents")
und die recipe (oder ein anderes file das der test liest) wurde
auf den neuen wert geaendert (z.B. "110 sub-agents") -- dann
failt der test permanent bis jemand den test fixt.

Gewuenschter zustand: ein neuer finding-type mit code-prefix
"SD-" (spec-drift), der automatisch generiert wird wenn:

    (a) ein test in tests/ einen literal wert asserted
        (z.B. "96 sub-agents"), UND
    (b) kein recipe/tool/docs-file in repo diesen literal enthaelt.

Detection-algorithmus im im-finder:

    for test_file in $(find tests -name 'test_*.py'):
      for assertion in extract_asserted_literals(test_file):
        # extract: alle strings in `assert "..." in content` und
        #          alle integer-vergleiche `assert N == ...`
        if not grep -rqF "$assertion" recipe/ tools/ docs/:
          emit_finding(
            code=f"SD-{test_file}-{assertion}",
            severity=MEDIUM,
            description=f"Test {test_file} asserts '{assertion}' "
                        f"but no recipe/tool/doc contains it -- "
                        f"either test is stale or recipe drift.",
            suggested_fix=f"Run: grep -rn '{assertion}' tests/ "
                          f"recipe/ tools/ docs/  -- if only tests/ "
                          f"matches, the test is stale; either update "
                          f"it to current spec or delete if obsolete.",
          )

Output fliesst in findings.yaml mit dem SD-prefix. im-rank priorisiert
SD-* MEDIUM-severity findings gleich nach P1 (weil sie tests brechen,
nicht nur stylistik sind). im-designer erzeugt einen patch der den
test updated. im-validator verifiziert dass der patch die tests
wieder gruen macht (pytest -q muss 0 failed zeigen).

================================================================
DIREKTIVE 3: TEST-COUNT-INVARIANT in recipe-content-tracking
================================================================

Manche recipe-content-referenzen wie "X tools" oder "Y sub-agents"
sind snapshot-counte. Wenn mas-engineer die recipe aendert, MUSS
er den test mit-aendern. Aktuell hat er dafuer keinen mechanismus.

Gewuenschter zustand: ein neues modul tools/dev_spec_invariant.py
das beim im-finder-run mitlaeuft und:

  1. sammelt alle `assert "<N> <TYPE>" in content` aus tests/
  2. sammelt alle literal counts in recipe/sub/*.yaml die diese
     TYPE matchen (z.B. "110 sub-agents", "77 tools")
  3. emittiert SD-findung wenn test-count != recipe-count

Output-format:
  {
    "test_bootstrap_distributes_110_subagents": {
      "test_asserts": "110 sub-agents",
      "recipe_says": "110 sub-agents",
      "match": true
    },
    "test_tools_count_77": {
      "test_asserts": "77 tools",
      "recipe_says": null,    # NOT FOUND in any recipe
      "match": false,         # <-- spec-drift
      "fix": "delete test or add to recipe"
    }
  }

Integration: im-validator ruft dev_spec_invariant.py am ende auf
und emittiert eine P1-finding wenn test.asserts != recipe_says
fuer einen COUNT-TYPE-paar.

================================================================
DIREKTIVE 4: PRE-PUSH-GATE SKILL UPDATE (human-seitig)
================================================================

Der skill devops/pre-push-gate/SKILL.md (Hermes-seitig, NICHT
mas-engineer) wurde heute (2026-08-03) bereits manuell erweitert
um den pytest-spec-drift rule (R110-78). Section "Pytest
spec-drift rule (R110-78, 2026-08-03)" wurde nach Step 2
eingefuegt. Diese human-seitige rule ist das fallback fuer
faelle in denen der mas-engineer-pre-push-validator die
pytest-ergaenzung noch nicht hat.

Mas-engineer muss DIREKTIVE 1 umsetzen damit der validator selbst
auch pytest laufen laesst, nicht nur der human-operator.

================================================================
WORKFLOW FUER DIESE DIREKTIVEN -- REIHENFOLGE DER UMSETZUNG
================================================================

Strategie: low-risk + immediate-impact zuerst, dann medium-risk
structural improvements. Jede direktive ist ein eigenstaendiger
patch -- bei abbruch nach PHASE N ist PHASE 1..N-1 bereits
produktiv.

PHASE 1 (sofort, ~30min, low risk):
  DIREKTIVE 1 -- pytest-step in sub_mas-pre-push-validator
    Risiko: minimal (ein zusatzlicher check, keine aenderung an
            bestehender logik)
    Effekt: SOFORT -- jeder zukuenftige pre-push-run faengt
            spec-drift BEVOR er den 90s+ validator verschwendet.
            Verhindert exact R110-71 wiederholung.
    Verifikation: ein test-commit der einen count-fix macht ohne
                  den test mitzuaendern, wird vom validator
                  BLOCKED.

PHASE 2 (nach phase 1, ~2h, medium risk):
  DIREKTIVE 2 -- SD-* finding type in sub_mas-im-finder
    Risiko: medium (neuer finding-type, koennte false-positive
            SD-findung generieren bei legitimen patterns)
    Effekt: mittelfristig -- im-finder findet spec-drift in
            laufenden scans, nicht erst beim pre-push-validator.
            Reduziert time-to-detect von Tagen (R110-71->R110-78
            war ~24h) auf stunden.
    Verifikation: ein absichtlicher stale-test erzeugt SD-finding,
                  mas-engineer behebt ihn automatisch.

PHASE 3 (nach phase 2, ~3h, medium risk):
  DIREKTIVE 3 -- tools/dev_spec_invariant.py + 2 hooks
    Risiko: medium (strukturelle aenderung, neue modulschnittstelle)
    Effekt: langfristig -- dediziertes modul garantiert dass
            test.asserts == recipe_says invariant IMMER gilt, nicht
            nur in finding-runs. Wird in im-validator am ende
            aufgerufen und emittiert P1 bei mismatch.
    Verifikation: 100% der count-diskrepanzen werden gefangen,
                  auch solche die im-finder/validator nicht direkt
                  sehen.

PHASE 4 (informational, bereits done):
  DIREKTIVE 4 -- Hermes-side pre-push-gate skill
    Status: bereits umgesetzt in dieser session (2026-08-03)
            mas-engineer muss hier nichts mehr tun.

STOP-PUNKTE:
  - Nach PHASE 1: commit + push + verifikation OK
                  -> PHASE 2 freigeben
  - Nach PHASE 2: 1 tag warten, schauen ob SD-findings nuetzlich
                  sind, dann PHASE 3
  - Nach PHASE 3: alle 3 aktiv, mas-engineer spec-drift-resistent

NICHT PARALLELISIEREN -- PHASE 1 muss erfolgreich sein bevor
PHASE 2 startet, weil PHASE 2 die SD-findung gegen den
erweiterten validator testet. PHASE 3 haengt von PHASE 1+2 ab.

================================================================
REFERENZ-COMMITS
================================================================

- R110-78 (9c73100, 2026-08-03): fixe 3 pytest-failures
  (96->110, composition-breakdown, dev_pytest_hook "failed" output)
- R110-71 (f6f2f46, 2026-08-03): aenderte recipe-count 96/57 -> 110/77
  OHNE die tests mitzuaendern (das war der bug den diese direktive
  verhindern soll)
- R110-77 (uncommittet, 2026-08-03): secret-leak-defense skill
  erweitert um GH-spezifisches pattern
- Skill-update pre-push-gate: Pytest spec-drift rule hinzugefuegt

================================================================
EXPECTED EFFORT
================================================================

Phasen-reihenfolge (WICHTIG, siehe WORKFLOW section oben):

  PHASE 1: DIREKTIVE 1 (validator + pytest)      ~30min,  1 file
  PHASE 2: DIREKTIVE 2 (im-finder SD-findung)    ~2h,     1 file
  PHASE 3: DIREKTIVE 3 (dev_spec_invariant.py)   ~3h,     1 neu + 2 hooks
  PHASE 4: DIREKTIVE 4 (skill update)            done,    0 files

  Total implementation:                          ~5.5h
  + im-pipeline run (3 PHASEN):                  ~30min
  + e2e verification:                            ~10min
  ---------------------------------------------------
  End-to-end:                                    ~6.5h

================================================================
NICHT ZU TUN
================================================================

- mas-engineer-files (recipe/sub/*, tools/*) NICHT direkt von
  Hermes editieren -- immer durch im-pipeline (rule 2026-07-21)
- Keine breaking changes an bestehenden tests (nur ergaenzen, nicht
  umschreiben -- sonst werden andere findings generiert die nicht
  mit dem urspruenglichen commit zusammenhaengen)
- pytest darf NIE optional gemacht werden (--skip-pytest flag ist
  verboten -- sonst kann man es einfach weglassen wenn es failed
  und der fix wird nie gemacht)
