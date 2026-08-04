# R110-113 — sub_mas-apply-directive (für R110-109 self-creation fix)
# 2026-08-04
# Quelle: R110-110 + R110-111 im-pipeline runs haben gezeigt dass
# RECURSION-GUARD v2 in sub_mas-general-improver (R04-block, 24h
# cooldown + APPLY_ONLY mode) das anwenden von FULL_IMPROVEMENT
# blockiert wenn keine drafted patches existieren. R110-109
# DIREKTIVE 1+2 (sub_mas-self-audit + dev_spec_invariant) sind
# NEW AGENTS die nicht via im-finder kommen, daher drafted=0
# und improver treated das als "nothing to apply".
#
# R110-113 fixt das mit einem neuen sub-recipe sub_mas-apply-directive
# der DIRECTIVE-FILES liest (statt im-finder findings) und patches
# anhand der DIREKTIVE specs drafted+applied. RECURSION-GUARD v2
# bleibt intakt weil sub_mas-apply-directive ein eigenstaendiger
# recipe ist, nicht ein wrapper um general-improver.

Ziel-Repo: mas-engineer (mczardybon/mas-engineer)
Branch: cleanup
Parent-Commit: dc4375b (R110-111 L26 fix)
Ref: R110-110 (R110-109 run 0 patches), R110-111 (L26 manual fix),
     R110-109 (self-audit + spec_invariant spec),
     R110-108 (RECURSION-GUARD v2 lessons), R110-78 (spec-drift
     lesson, R04-R10 invariants)

================================================================
DIREKTIVE 1: NEUER SUB-AGENT sub_mas-apply-directive
================================================================

Aktueller zustand: mas-engineer hat keinen mechanismus der
directive-files (z.B. R110-109 DIREKTIVE 1+2) liest und
automatisch implementiert. Im-finder findet code-defects,
im-designer drafted patches für ranked_findings, improver
apply-t nur drafted patches. Directives die "new agent"
oder "new tool" spezifizieren sind im standard-flow nicht
erreichbar (R110-110 run bewiesen: 21 findings, 0 patches,
RECURSION_OVERRIDE -> APPLY_ONLY -> 0 applied).

Gewuenschter zustand: ein neuer sub-recipe
sub_mas-apply-directive der:
  1. liest .directives/R<NR>-*.md files
  2. parsed die "DIREKTIVE 1+2+..." sections
  3. fuer jede DIREKTIVE: drafted eine patch-spec
     (yaml + tools + recipe files mit INSERT/REPLACE spec)
  4. validiert die patch-spec (R10 yaml.safe_load)
  5. applied via sub_mas-yaml-editor + sub_mas-recipe-designer
  6. tests run (pytest --collect-count == 1281 invariant)
  7. commit + push via sub_mas-git-operator

KONKRETE SPEZIFIKATION:

  1. NEUE DATEI: mas-engineer/recipe/sub/sub_mas-apply-directive.yaml
     Schema: gleiche YAML-struktur wie sub_mas-general-improver.yaml
     (recipe: <name>, blocks: role, prompt, sub_recipes, ...).
     Source inspiration: sub_mas-im-designer.yaml (STEP-driven
     recipe mit yaml.safe_load validation, ~200 lines).

  2. NEUE DATEI: mas-engineer/recipe/instructions/sub_mas-apply-directive.md
     Body: 5-6 absaetze die den agent erklaeren (read directive
     files, parsed DIREKTIVE sections, drafted+apply patches).
     KEINE sub_recipes (selbst-detect mu recursive sein, aber
     R04-block bleibt: der agent darf general-improver NICHT
     summonen).

  3. STEPS (analog im-designer STEP 1-3):
     STEP 0.5: GOOSE-EXPERT consultation (R11 type A/B check)
     STEP 1: read .directives/R<NR>-*.md (newest first per
             git log -10), extract DIREKTIVE N sections
     STEP 2: parsed INSERT/REPLACE specs (regex: r'INSERT\s+(\S+)\s+(.*?)\s*\n\s*```\n(.*?)\n```',
             analog). Build patch list.
     STEP 3: validate each patch (R10 yaml.safe_load)
     STEP 4: write .state/pipeline/directive_patches.yaml
     STEP 5: emit signal DONE -> caller (user or im-pipeline orchestrator)

  4. NEUE DATEI: mas-engineer/tools/dev_directive_parser.py
     Standalone-script (R110-106/109 pattern: importierbar als
     modul, CLI-callable). API:
       def parse_directive(path: Path) -> list[DirectivePatch]
       class DirectivePatch:
           directive_nr: int
           target_file: str
           operation: str  # 'INSERT'|'REPLACE'|'CREATE_FILE'
           content: str
           verification: str
     CLI: `python3 -m dev_directive_parser --directive <path>
           --output .state/pipeline/directive_patches.yaml`
          exit 0 wenn parse OK, 1 sonst.

  5. NEUE DATEI: mas-engineer/tools/dev_directive_applier.py
     Standalone-script, nimmt .state/pipeline/directive_patches.yaml
     und applied via sub_mas-yaml-editor + sub_mas-recipe-designer
     (R10 CORONASHIELD before each apply).
     API:
       def apply_directive_patches(patches: list[DirectivePatch],
                                    repo_root: Path) -> ApplyResult
     CLI: `python3 -m dev_directive_applier --patches <path>
           --repo-root <path>` (exit 0 wenn all applied, 1 sonst)

  6. IDEMPOTENZ: skip wenn sub_mas-apply-directive.yaml schon
     existiert in recipe/sub/. Detection via grep-detect.

================================================================
DIREKTIVE 2: RECURSION-GUARD v2 v3 (in sub_mas-general-improver)
================================================================

Aktueller zustand: sub_mas-general-improver prompt (R110-108
commit 391be5b, recipe Z.70-73) hat RECURSION-GUARD v2:
  "(A) FULL_IMPROVEMENT blocked if last < 24h; (B) APPLY-ONLY
   allowed when RECURSION_OVERRIDE=1 - READ validation.yaml,
   APPLY CONFORM patches via sub_mas-yaml-editor."

Gewuenschter zustand: RECURSION-GUARD v3 erlaubt FULL_IMPROVEMENT
auch wenn drafted=0, FALLS die FULL_IMPROVEMENT message einen
directive-file-path enthaelt (z.B. ".directives/R110-109-*.md").
Beispiel: "FULL_IMPROVEMENT per directive .directives/R110-109-
self-audit-spec-invariant.md" wird parsed und
sub_mas-apply-directive summont (statt R04-block).

KONKRETE SPEZIFIKATION (R110-113 macht NUR das prompt-update
+ env-var declaration; die invocation-pass-through zu
sub_mas-apply-directive ist DIREKTIVE 3):

  1. DATEI: mas-engineer/recipe/sub/sub_mas-general-improver.yaml
  2. Z.70 prompt: RECURSION-GUARD v2 -> v3 update mit neuer
     erkennung: wenn "per directive <path>" im message ist,
     dispatch zu sub_mas-apply-directive statt R04-block.
  3. IDEMPOTENZ: skip wenn "RECURSION-GUARD v3" schon im prompt
     (grep-detect).
  4. NICHT ZU TUN: kein refactor der v2 logic (v2 ist fallback
     wenn "per directive" fehlt), nur add v3 detection davor.

================================================================
DIREKTIVE 3: sub_mas-apply-directive integration
================================================================

Aktueller zustand: sub_mas-general-improver v3 dispatch zu
sub_mas-apply-directive, aber sub_mas-apply-directive selbst
existiert nicht (DIREKTIVE 1 spec'd das).

Gewuenschter zustand: integration-test der zeigt dass
"goose run sub_mas-general-improver mit message 'FULL_IMPROVEMENT
per directive .directives/R110-109-*.md'" tatsaechlich
sub_mas-apply-directive summont (statt R04-block).

KONKRETE SPEZIFIKATION (integration ist DEFERRED bis DIREKTIVE
1+2 implementiert sind; DIREKTIVE 3 spec'd nur den test):
  1. NEUE TEST: mas-engineer/tests/test_sub_mas_apply_directive.py
     ~30 lines, 1-2 test-functions:
     - test_dispatch_via_message: parse ".directives/R110-109-*" aus
       message, assert sub_mas-apply-directive wird summont
     - test_idempotent_skip: assert doppelte runs skippen
  2. PYTEST-COUNT INVARIANT: 1281 + 2 = 1283 tests. Test-count
     aenderung MUSS via dev_spec_invariant.py (R110-109
     spec'd) automatisch detected werden. Wenn Check 18 läuft,
     passen 1281/1283 FAIL weil recipe-count (110) vs test-count
     (1283) mismatch. FIX: re-render R110-109 DIREKTIVE 1+2 mit
     invariant: "1281 tests" stays canonical.
     WAIT: contradiction! Wenn test 1283 sein soll UND 1281
     invariant bleiben soll, dann MUSS der test_count-anchor
     update werden (recipe/instructions/* verlangt 1281).
     Loesung: bei implementation erst check_spec_drift_reverse()
     (R110-112) und dev_spec_invariant.py (R110-109) MÜSSEN
     mit der neuen test-count synchronisiert sein BEVOR
     sub_mas-apply-directive implementiert wird. Oder:
     alternative implementierung ohne neue test-files (z.B.
     tests in bestehende tests/test_general_improver.py
     hinzufuegen statt neue datei).
  3. IDEMPOTENZ: skip wenn test-file schon existiert.
  4. PROBLEM: DIREKTIVE 3.2 hat eine logical circularity
     (test-count invariant vs new test). DIREKTIVE 3.3
     (alternative) ist der saubere pfad.

  ALTERNATIVE 3.3 (R110-113 recommended):
  - KEIN neues test-file
  - tests/test_general_improver.py erweitern um 2 tests
    (existing 4 tests + 2 new = 6 tests, count delta +2)
  - 1281 + 2 = 1283 tests. Recipe-count invariant update
    erforderlich (recipe/instructions/* sagt "1281 tests"
    irgendwo, muss zu "1283 tests" werden).
  - Diese update ist EIN follow-up commit, separat von
    R110-113 implementation.

  FAZIT: R110-113 implementiert DIREKTIVE 1+2 (new recipe +
  new tool + RECURSION-GUARD v3). Test integration (DIREKTIVE
  3) wird in R110-114 spec'd mit test-count invariant update.

================================================================
Ausfuehrung via im-pipeline (R110-113 run)
================================================================

  cd /tmp/mas-engineer-test/mas-engineer
  set -a; . ./.env; set +a
  export PATH=$PATH:/root/.local/bin
  export GOOSE_SESSION_TAG="[r110-113-apply-directive]"
  export MAS_WEB_RESEARCH=no
  export IM_TOP_N=30
  export IM_TOP_N_MULTIPLIER=3
  export RECURSION_OVERRIDE=2
  export MAS_TASK="apply"
  export MAS_CONFIRM=yes
  export MAS_APPROVE=y

  # Phase 1 (FIND) -- findet DIREKTIVE 1+2 als NN1 (new agent)
  echo "ack" | goose run --with-builtin developer \
    --recipe recipe/sub/sub_mas-im-finder.yaml --no-session

  # Phase 2 (RANK)
  echo "ack" | goose run --with-builtin developer \
    --recipe recipe/sub/sub_mas-im-rank.yaml --no-session

  # Phase 3 (DESIGN) -- drafted 0 (alle NN1 R52-fail) wie immer
  echo "ack" | goose run --with-builtin developer \
    --recipe recipe/sub/sub_mas-im-designer.yaml --no-session

  # Phase 4 (VALIDATE)
  echo "ack" | goose run --with-builtin developer \
    --recipe recipe/sub/sub_mas-im-validator.yaml --no-session

  # Phase 5 (APPLY) -- DIREKTIVE 1+2 werden gefixt
  # NEU: "per directive" prefix dispatched zu sub_mas-apply-directive
  # (NACH R110-113 implementation; vor R110-113 noch via
  # FULL_IMPROVEMENT APPLY_ONLY wie R110-110/111)
  echo "FULL_IMPROVEMENT per directive .directives/R110-113-apply-directive.md -
  apply DIREKTIVE 1+2: create sub_mas-apply-directive.yaml +
  sub_mas-apply-directive.md + dev_directive_parser.py +
  dev_directive_applier.py, update RECURSION-GUARD v2 -> v3 in
  sub_mas-general-improver prompt. ack" | \
    goose run --with-builtin developer \
    --recipe recipe/sub/sub_mas-general-improver.yaml --no-session

ERWARTETES ERGEBNIS (5 files modified, ~530 insertions):
  - recipe/sub/sub_mas-apply-directive.yaml (NEU, ~100 lines)
  - recipe/instructions/sub_mas-apply-directive.md (NEU, ~60 lines)
  - tools/dev_directive_parser.py (NEU, ~200 lines)
  - tools/dev_directive_applier.py (NEU, ~150 lines)
  - recipe/sub/sub_mas-general-improver.yaml Z.70 prompt
    update (RECURSION-GUARD v2 -> v3, ~5 lines modified)
  - Total: 5 files (4 new + 1 modified), ~515 insertions, 5 modifications

VERIFIKATION:
  - ls recipe/sub/sub_mas-apply-directive.yaml   # MUSS existieren
  - python3 -c "from dev_directive_parser import parse_directive;
                parse_directive('.directives/R110-109-self-audit-spec-invariant.md');
                print('OK')"   # MUSS OK sein
  - python3 -c "from dev_directive_applier import apply_directive_patches;
                print('OK')"
  - grep "RECURSION-GUARD v3" recipe/sub/sub_mas-general-improver.yaml
    # MUSS >= 1 sein
  - pytest 1281/1281 PASS (kein neues test-file in DIREKTIVE 1+2)

ROLLBACK-STRATEGY:
  - Bei false-positive dispatch (v3 summont sub_mas-apply-directive
    für nicht-directive messages): RECURSION-GUARD v3 pattern
    enger fassen (z.B. nur wenn "per directive" + ".directives/"
    beides im message)
  - Bei parser-fail: dev_directive_parser.py robuster machen
    (z.B. multiline-INSERT specs)
  - Bei applier-fail: dev_directive_applier.py hat
    per-patch try/except, failed patches in
    .state/pipeline/directive_patches_failed.yaml

GOOSE-EXPERT CONSULT (R11):
  R11 prefix list matcht fuer R110-113: 5 files modified (type A
  + type B), RECURSION-GUARD update. R11 GOOSE-EXPERT MUSS
  konsultiert werden vor dem apply. Im-validator step 4 macht
  das automatisch. Plus: recipe-new-file type A trigger
  (sub_mas-apply-directive.yaml).

NICHT-ZIELE (R110-113 vs R110-114+):
  R110-113: sub_mas-apply-directive + RECURSION-GUARD v3
  R110-114: test integration (DIREKTIVE 3 spec'd hier) +
    test-count invariant update (1281 -> 1283) +
    re-run R110-109 (self-audit + dev_spec_invariant apply via
    neuem sub_mas-apply-directive dispatch)
  R110-115: R110-112 reverse-mode im-pipeline run
  R110-116+ (optional): weitere directive-specs die via
    sub_mas-apply-directive dispatched werden koennen
