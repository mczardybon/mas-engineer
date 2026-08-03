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

Gewuenschter zustand: als Check 16 (oder als sub-step von Check 6
'YAML parse') soll der validator laufen lassen:

    cd mas-engineer && python3 -m pytest -q 2>&1 | tail -20

und das ergebnis in pre_push_validation.yaml unter
`pytest_summary: {passed: N, failed: M, errors: E, skipped: S}`
festhalten. Wenn failed > 0 ODER errors > 0, ist der validator-
output "BLOCKED" (nicht "passed"), auch wenn alle 15 anderen
checks gruen sind.

Begründung: pytest laeuft in ~10s fuer das mas-engineer-test-tree
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
WORKFLOW FUER DIESE DIREKTIVEN
================================================================

1. User packt diese datei in mas-engineer/.directives/R110-78-spec-drift.md
   und committet sie auf cleanup.
2. Naechster im-pipeline run (FIND/RANK/DESIGN/VALIDATE/APPLY)
   bearbeitet die 3 mas-engineer-direktiven automatisch.
3. Ergebnis: validator + im-finder + spec-invariants modul sind
   spec-drift-resistent.
4. Verifikation: ein erneuter count-fix (z.B. recipe 110 -> 120)
   wuerde jetzt vom validator BLOCKED werden, der spec-invariants
   wuerde P1 emittieren, der im-finder wuerde SD-findung generieren.

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

- DIREKTIVE 1 (validator + pytest): ~30min, 1 file
- DIREKTIVE 2 (im-finder SD-findung): ~2h, 1 file
- DIREKTIVE 3 (dev_spec_invariant.py): ~3h, 1 neues file + 2 hooks
- Total: ~5.5h implementation + 30min im-pipeline run + 10min e2e
  = ~6.5h end-to-end

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
