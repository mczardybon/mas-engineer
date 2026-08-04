# R110-111 — recipe L26 "16 checks" → "17 checks" drift fix
# 2026-08-04
# Quelle: R110-110 im-finder run 11:04 UTC hat 21 findings emittiert,
# davon 7 SD-* (alle false_positive/by_design/line_wrap_artifact).
# Beim manuellen grep fuer "16" vs "17" hardcodes in recipe/
# instructions/ vs test-asserts: drift bestaetigt.

Ziel-Repo: mas-engineer (mczardybon/mas-engineer)
Branch: cleanup
Parent-Commit: e0dbca3 (R110-110 status update)
Ref: R110-110 (R110-109 run 11:04), R110-100 (Check 17 added),
     R110-94 (Check 16+ added), R110-78 (spec-drift lesson)

================================================================
DIREKTIVE 1: SD-literal drift fix in sub_mas-pre-push-validator.md Z.26
================================================================

Aktueller zustand:
  recipe/instructions/sub_mas-pre-push-validator.md Z.26 sagt:
    "Run the following 16 checks IN ORDER. Stop at the first
     failure if a hard block is detected, but always collect
     all warnings."
  Tatsaechlich sind es 17 checks (Check 1-15 + Check 16+ (R110-94)
  + Check 17 (R110-100)). Der text wurde seit R110-94 nicht
  aktualisiert.

  Test-assert (tests/test_sub_mas_pre_push_validator.py Z.52):
    assert "17 critical checks" in content or "17 checks" in content
  Test akzeptiert "17" (mit oder ohne "critical") -- beide
  patterns matchen "17 critical checks" (in den example-blocks
  Z.427, 442) aber NICHT "16 checks" (Z.26 alt-text).

  Resultat: SD-test waere failed in test_run_file_against_lints()
  wenn der "16" hardcode nicht gefixt wird. Aber: SD-detector
  hat den literal NICHT emittiert weil check_spec_drift() in
  tools/dev_im_finder_scan.py (R110-106 commit 3b80259) sucht
  nur in tests/ nach "literal-only-in-tests" pattern. Die
  rezept-seite ist die quelle des drifts, nicht der test.

Gewuenschter zustand:
  recipe/instructions/sub_mas-pre-push-validator.md Z.26:
    ALT: "Run the following 16 checks IN ORDER. Stop at the first"
    NEU: "Run the following 17 checks IN ORDER. Stop at the first"
  Keine weiteren aenderungen -- der rest des recipe-instructions
  ist konsistent (Z.427-442 example-blocks sagen "17 critical
  checks", das stimmt mit dem fix ueberein).

KONKRETE SPEZIFIKATION:
  1. DATEI: mas-engineer/recipe/instructions/sub_mas-pre-push-validator.md
  2. Z.26: "16 checks" -> "17 checks" (single word replace)
  3. IDEMPOTENZ: skip wenn schon "17 checks" (grep-detect)
  4. NICHT ZU TUN: keine weiteren aenderungen, kein refactor der
     check-numerierung, keine re-categorization

================================================================
DIREKTIVE 2: SD-detector extension -- reverse direction (recipe -> test)
================================================================

Aktueller zustand: tools/dev_im_finder_scan.py:check_spec_drift()
sucht nach "literal-only-in-tests" pattern (R110-106 spec) --
das ist die halbe richtung (test claimed etwas das in recipe
fehlt). Die andere richtung (recipe sagt etwas das im test
nicht geprueft wird) ist der R110-111 drift.

KONKRETE SPEZIFIKATION (follow-up, nicht in R110-111 apply):
  1. ERWEITERUNG: check_spec_drift() um parameter
     `reverse: bool = False`. Wenn True, suche nach
     "literal-only-in-recipe" pattern -- d.h. recipe sagt
     einen wert (z.B. "16 checks"), aber test akzeptiert
     einen anderen (z.B. "17").
  2. SEVERITY: medium (BLOCKER nur wenn test akzeptiert N+1
     aber recipe noch N sagt, weil das blockierende test-run-
     failures erzeugt; INFO sonst).
  3. IDEMPOTENZ: skip wenn tool schon reverse-mode hat
     (grep-detect).
  4. AUSFUEHRUNG: in R110-112 spec'd, in R110-113 implementiert.
     R110-111 macht NUR die single-word replacement fix.

================================================================
DIREKTIVE 3: Test-assert maintenance hygiene
================================================================

Beobachtung: tests/test_sub_mas_pre_push_validator.py Z.52
akzeptiert "17 critical checks" ODER "17 checks" (OR-pattern).
Das ist absichtlich tolerant fuer die "critical"-suffix variation.
Aber: wenn recipe Z.26 zu "17 checks" gefixt wird, matcht der
test "17 checks" sofort. Wenn spaeter zu "18 checks" erweitert
wird, faellt der test sofort (assertion mismatch).

KONKRETE SPEZIFIKATION (follow-up):
  1. TEST-ASSERT HARTEN: in R110-112+ sollte der test
     "18 critical checks" verlangen sobald Check 18 spec'd ist.
     So bleibt der test der canonical anchor.
  2. IDEMPOTENZ: skip wenn test schon "18 critical checks"
     sagt (grep-detect).

================================================================
Ausfuehrung via im-pipeline (R110-111 run)
================================================================

  cd /tmp/mas-engineer-test/mas-engineer
  set -a; . ./.env; set +a
  export PATH=$PATH:/root/.local/bin
  export GOOSE_SESSION_TAG="[r110-111-recipe-drift-fix]"
  export MAS_WEB_RESEARCH=no
  export IM_TOP_N=30
  export IM_TOP_N_MULTIPLIER=3
  export RECURSION_OVERRIDE=2
  export MAS_TASK="apply"
  export MAS_CONFIRM=yes
  export MAS_APPROVE=y

  # Phase 1 (FIND) -- findet jetzt schon SD-test_recipe_instructions
  #   F-015 = spec_drift F-015 in R110-110 run, war verified=
  #   false_positive weil "security-scanner.md" content-only-stale.
  #   R110-111 run emittiert das gleiche finding weil test-glob
  #   INSTRUCTION_FILE_GLOB + INST_DIR pattern nicht updated wurde.
  echo "ack" | goose run --with-builtin developer \
    --recipe recipe/sub/sub_mas-im-finder.yaml --no-session

  # Phase 2 (RANK) -- SD-findings sind nicht-implementable (R52-fail
  #   weil verified=false_positive), aber NN1 (architecture) sind
  #   drin und werden R52-fail
  echo "ack" | goose run --with-builtin developer \
    --recipe recipe/sub/sub_mas-im-rank.yaml --no-session

  # Phase 3 (DESIGN) -- 0 patches weil alle NN1 R52-fail und SD
  #   verified=false_positive. R110-111 DIREKTIVE 1 muss als
  #   FULL_IMPROVEMENT task gepushed werden.
  echo "ack" | goose run --with-builtin developer \
    --recipe recipe/sub/sub_mas-im-designer.yaml --no-session

  # Phase 4 (VALIDATE)
  echo "ack" | goose run --with-builtin developer \
    --recipe recipe/sub/sub_mas-im-validator.yaml --no-session

  # Phase 5 (APPLY) -- DIREKTIVE 1 wird gefixt
  echo "FULL_IMPROVEMENT - apply R110-111 DIREKTIVE 1: change
  recipe/instructions/sub_mas-pre-push-validator.md Z.26 from
  'Run the following 16 checks' to 'Run the following 17 checks'.
  Single-word replace. Idempotent via grep-detect. ack" | \
    goose run --with-builtin developer \
    --recipe recipe/sub/sub_mas-general-improver.yaml --no-session

ERWARTETES ERGEBNIS (1 file modified, 1 line changed):
  - recipe/instructions/sub_mas-pre-push-validator.md Z.26
  - "16 checks" -> "17 checks"
  - pytest 1281/1281 PASS in 8.05s
  - 1 commit, +1/-1 (single line)

VERIFIKATION:
  - grep "17 checks" recipe/instructions/sub_mas-pre-push-validator.md
    | head -1   # MUSS Z.26 sein
  - grep "16 checks" recipe/instructions/sub_mas-pre-push-validator.md
    # MUSS 0 sein (nur in code als "Check 16+" referenzen, nicht
    # als "16 checks")
  - python3 -m pytest tests/test_sub_mas_pre_push_validator.py -q
    # PASS (der test wollte "17" oder "17 critical checks", jetzt
    # matcht "17 checks")
  - python3 -m pytest tests/ -q   # 1281/1281 PASS

ROLLBACK-STRATEGY:
  - Bei false-positive (das "16" ist kein drift, sondern
    absichtlich): spec ist im commit-message dokumentiert, revert
    via `git revert <commit-hash>`
  - Bei test-failure nach fix: test-assert update erforderlich
    (anderer change, R110-112 territory)

GOOSE-EXPERT CONSULT (R11):
  R11 prefix list matcht fuer R110-111: 1 file modified
  (recipe/instructions), single line. R11 GOOSE-EXPERT MUSS
  konsultiert werden vor dem apply weil type A (instruction
  recipe). Im-validator step 4 macht das automatisch.

NICHT-ZIELE (R110-111 vs R110-112+):
  R110-111: single-word replacement Z.26 "16" -> "17"
  R110-112: check_spec_drift() reverse-mode extension
  R110-113: R110-109 DIREKTIVE 1+2 nochmal (sub_mas-self-audit
    + dev_spec_invariant, mas-engineer-self-creation braucht
    neuen sub-recipe "sub_mas-new-agent" der nicht durch
    RECURSION_OVERRIDE blocked wird)
  R110-114+ (optional): weitere recipe L-line drifts die im
    self-audit (R110-109+113) gefunden werden
