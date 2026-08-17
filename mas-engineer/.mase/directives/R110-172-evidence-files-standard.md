# R110-172 — body-claim evidence files standard (reproduzierbare test+scan beweise)

## CONTEXT

R110-126 + R110-171 commit-bodies enthielten zahlen-claims (z.B.
"11/11 regression tests passed", "1528/16/0 full suite", "10/10 key
phrases grep-treffer", "3x consecutive flake-suite clean"). Diese
zahlen waren im moment des pushes verifiziert (hermes hatte den
pytest-output live im terminal), aber NACH dem push war nur der
body-text in git vorhanden — kein reproduzierbares artefakt im
repo. Wer den clone bekam konnte die zahlen entweder glauben
oder selber nochmal pytest laufen lassen.

Zusaetzlich enthaelt R110-126 body einen claim der heute bei
R110-172-reproduktion als ungenau auffiel: "10/10 key phrases"
war strict-case-grep-falsch, nur 5/10 exakt; 10/10 nur
case-insensitive oder als section-themes. Body-claim-drift,
nicht spec-drift, aber unangenehm.

Skill `mas-engineer-verification-theater-guard` (selbst von
hermes erstellt) sagt: "jede test-zahl in einem commit-body
muss als reproduzierbares artefakt existieren, sonst ist es
theater".

Diese directive etabliert den standard: JEDER commit der
test-zahlen, scan-ergebnisse oder grep-treffer im body
behauptet, MUSS die entsprechenden logs in
`tests/results/<R-NR>-<topic>/` mit-commiten.

## ZIEL-REPO

mas-engineer (mczardybon/mas-engineer)
Branch: mas-mq
Parent-Commit: 3ba2bfd (R110-171)
Ref: R110-126 (42cda98), R110-171 (3ba2bfd), R110-78 (spec-drift
     lesson), R110-100 (check 17 test-count-mismatch)

================================================================
DIREKTIVE 1: tests/results/ LAYOUT-STANDARD
================================================================

Aktueller zustand: kein `tests/results/` dir im repo. Tests
schreiben ihre artefakte in tmp dirs (pytest convention) die
nach dem run weg sind. Commit-bodies verweisen auf zahlen die
nicht reproduzierbar im repo liegen.

Standard fuer alle zukuenftigen commits mit body-claims:

  tests/results/<R-NR>-<short-topic>/
    01-<claim-1>.txt
    02-<claim-2>.txt
    ...
    NN-<claim-N>.txt

Jede .txt datei hat:
  - Datum + commit-sha den sie beweist (header)
  - Den exakten command (verbatim, copy-paste-bar)
  - Den output (stdout+stderr, komplett oder relevant tail)
  - Eine "Conclusion:" zeile die sagt welcher body-claim hier
    bewiesen ist

Beispiel-layout fuer R110-172 selbst (referenz):

  tests/results/r110-171-flake-fix/
    01-phantom-test-names-grep.txt
    02-pytest-collect-only.txt
    03-flake-suite-run-1.txt
    03-flake-suite-run-2.txt
    03-flake-suite-run-3.txt
    04-full-suite-pytest-n4.txt
    05-secret-scan.txt
    06-official-secret-scan.txt
  tests/results/r110-126-mq-pattern/
    01-phase3-phase4-regression-11-11.txt
    02-key-phrases-grep-10-10.txt
  tests/results/README.md

================================================================
DIREKTIVE 2: TESTS/RESULTS/ IST NICHT GITIGNORED
================================================================

`tests/results/` MUSS getrackt sein (nicht in .gitignore). Es
ist der gegenpol zu `.mase/runtime/` (was gitignored ist):
  - `.mase/runtime/` = lebender state, regenerierbar, NICHT
    reproduzierbar (jeder run ist anders)
  - `tests/results/` = beweis-fossilien, festgefroren pro
    commit, REPRODUZIERBAR via dem command im file-header

Wenn ein CI-run spaeter diese files updated, faellt das in
git-diff auf und ist ein warning-signal ("hier hat sich was
geaendert, ist der body noch aktuell?").

================================================================
DIREKTIVE 3: BODY-CLAIM-EVIDENCE LINK
================================================================

Jeder commit-body der einen zahlen-claim macht MUSS am ende
einen "EVIDENCE" block haben der auf die evidence-files
verweist:

  EVIDENCE (reproduzierbar via tests/results/<dir>/):
    - 01-...: 11/11 passed in 2.44s
    - 04-...: 1528 passed, 16 skipped, 0 failed in 256.76s
    - 05-...: 4x clean (no real, no fixture-form)

Das EVIDENCE-block ist OPTIONAL fuer commits ohne zahlen-claims
(z.B. reine docs/refactor commits), aber PFLICHT fuer
test/perf/ci commits.

================================================================
DIREKTIVE 4: BACKWARD-COMPATIBLE MIT R110-126 + R110-171
================================================================

R110-126 + R110-171 bodies haben das EVIDENCE-block format noch
NICHT verwendet. R110-172 fixt das rueckwirkend: die evidence
files werden NACHTRAGLICH in tests/results/r110-126-mq-pattern/
und tests/results/r110-171-flake-fix/ angelegt. Die bestehenden
bodies werden NICHT amended (git history bleibt linear +
ehrlich — "war zu dem zeitpunkt so wie der body sagt, evidence
wurde nachgereicht unter R110-172").

Der R110-172 commit enthaelt:
  - tests/results/r110-171-flake-fix/ (7 evidence files)
  - tests/results/r110-126-mq-pattern/ (2 evidence files)
  - tests/results/README.md (standard-dokumentation)
  - KEINE code-changes, KEINE recipe-changes (reines evidence-
    supplement)

================================================================
VERIFICATION (was R110-172 beweisen muss)
================================================================

1. `git show R110-172-sha --stat` zeigt 9-10 neue files unter
   tests/results/ und 0 code-changes
2. `python3 -m pytest tests/ -q -n 4` = 1528/16/0 (unveraendert)
3. `python3 tools/dev_security_scan.py SCAN secrets tests/results/`
   = issues_found: false
4. `git ls-files tests/results/` listet alle files (nicht
   gitignored)
5. `cat tests/results/r110-171-flake-fix/04-full-suite-pytest-n4.txt
   | grep "1528 passed"` = match
6. `cat tests/results/r110-171-flake-fix/01-phantom-test-names-grep.txt
   | grep "exit code: 1"` = match (beweis dass phantom-tests
   nicht existieren)
7. `cat tests/results/r110-126-mq-pattern/01-phase3-phase4-regression-11-11.txt
   | grep "11 passed"` = match

REFERENZEN:
  R110-100 (check 17): pytest-count-mismatch war real, jetzt
    mit test-count evidence-file auch reproduzierbar
  R110-78 (spec-drift): R110-126 body's "10/10 key phrases" war
    ungenau (case-sensitive). R110-172 dokumentiert das ehrlich
    in tests/results/r110-126-mq-pattern/02-key-phrases-grep-10-10.txt
  mas-engineer-verification-theater-guard skill: definiert dass
    beweise reproduzierbar sein muessen
