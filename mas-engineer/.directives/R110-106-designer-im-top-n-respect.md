# IM-Pipeline Designer: respect IM_TOP_N env var
# R110-106 (2026-08-04)
# Zweck: mas-engineer's im-designer drafts patches only for TOP-5 findings
# regardless of IM_TOP_N env var. R110-105 SD-detector found F-022 (test
# says "14 critical checks" but validator has 19) at rank 16, but the
# designer hardcoded "TOP-5" in STEP 1 instruction and skipped it as
# "beyond IM_TOP_N=5 scope". This blocks legitimate spec-drift fixes.

Ziel-Repo: mas-engineer (mczardybon/mas-engineer)
Branch: cleanup
Datum: 2026-08-04
Quelle: R110-105 (SD-detector e2e) + R110-89 (R57 IM_TOP_N default 5)

================================================================
DIREKTIVE 1: im-designer STEP 1 instruction: TOP-5 -> TOP-N
================================================================

Aktueller zustand: recipe/instructions/sub_mas-im-designer.md Z.163
  "STEP 1 — DRAFT ONE PATCH FOR EACH TOP-5 FINDING"
  Der designer behandelt alle findings jenseits der ersten 5 als
  "beyond IM_TOP_N=5 scope" und drafted KEINEN patch, obwohl der
  im-rank agent sie in ranked_findings.top_N aufgenommen hat (weil
  IM_TOP_N=30 oder 50 gesetzt war).

Gewuenschter zustand: der designer drafted EINEN patch fuer JEDEN
eintrag in ranked_findings.top_N (laengenbestimmt, nicht fest auf 5).
Der IM_TOP_N env var (default 5) bestimmt die anzahl, nicht die
instruction.

KONKRETE SPEZIFIKATION:

  1. DATEI: mas-engineer/recipe/instructions/sub_mas-im-designer.md
     AENDERUNG: Z.163
     VORHER:  "## STEP 1 — DRAFT ONE PATCH FOR EACH TOP-5 FINDING"
     NACHHER: "## STEP 1 — DRAFT ONE PATCH FOR EACH ENTRY IN top_N
              (length = IM_TOP_N env var, default 5)"

  2. DATEI: mas-engineer/recipe/instructions/sub_mas-im-designer.md
     UPDATE: skip-reason text von "Ranked but beyond IM_TOP_N=5 scope
             (default 5); not drafted this session." ersetzen durch
             dynamische formulierung die den aktuellen IM_TOP_N
             wert nennt (nicht hardcoded 5).

  3. VERIFIKATION: nach dem fix muss ein im-pipeline run mit
     IM_TOP_N=30 exportiert
     - 16 implementable findings in top_N haben
     - 16 patch-entwuerfe (oder 0 wenn alle R52-fail) produzieren
     - KEIN "beyond IM_TOP_N=5 scope" skip-reason mehr auftauchen

================================================================
DIREKTIVE 2: F-022 (R110-105 spec-drift) end-to-end fixen
================================================================

Aktueller zustand: tests/test_sub_mas_pre_push_validator.py Z.5+46+52
sagt "14 critical checks" (literal in test-docstring + assertion),
aber recipe/instructions/sub_mas-pre-push-validator.md hat 19 checks
(Check 0, 1.5, 1-14, 16+, 17 — R110-94 hat Check 16+ hinzugefuegt,
R110-78 PHASE 1 hat Check 17 implementiert).

Gewuenschter zustand: test-literal enthaelt "19 critical checks"
(die korrekte aktuelle anzahl), so dass die spec-drift aufgeloest
ist und der test strenger wird (literal-match statt loose
substring fallback).

KONKRETE SPEZIFIKATION:

  1. DATEI: mas-engineer/tests/test_sub_mas_pre_push_validator.py
     Z.5: "runs all 14 critical checks before git push is allowed."
          -> "runs all 19 critical checks before git push is allowed."
     Z.46: docstring "runs 14 critical checks."
           -> "runs 19 critical checks."
     Z.52-53: assertion "14 critical checks" / "14 checks"
              -> "19 critical checks" / "19 checks"
     Die letzte fall-back assertion "or \"14\" in content" muss
     ENTFERNEN werden, damit der test streng wird.

  2. IDEMPOTENZ: wenn der fix bereits angewendet wurde, idempotent
     ueberspringen (nicht doppelt patchen).

  3. GOOSE-EXPERT CONSULT (R11): keinen — F-022 ist test-literal
     hygiene, nicht Goose-version/coupling frage. R11 prefix list
     matcht NICHT (SD-* != A/B/D/MM/JJ/S/HH/LL prefix).

================================================================
Ausfuehrung via im-pipeline
================================================================

  cd /tmp/mas-engineer-test/mas-engineer
  set -a; . ./.env; set +a
  export PATH=$PATH:/root/.local/bin
  export GOOSE_SESSION_TAG="[r110-106-im-top-n-fix]"
  export MAS_WEB_RESEARCH=no
  export IM_TOP_N=30
  export RECURSION_OVERRIDE=2
  export MAS_TASK="apply"
  export MAS_CONFIRM=yes
  export MAS_APPROVE=y

  # Phase 1-3 (FIND+RANK+DESIGN) — discovery, ranking, patch design
  # Designer MUSS jetzt patches fuer ALLE items in top_N draften
  # (nicht nur top-5). Verifier via patches.yaml.patches.length.
  echo "ack" | goose run --with-builtin developer \
    --recipe recipe/sub/sub_mas-im-finder.yaml --no-session
  echo "ack" | goose run --with-builtin developer \
    --recipe recipe/sub/sub_mas-im-rank.yaml --no-session
  echo "ack" | goose run --with-builtin developer \
    --recipe recipe/sub/sub_mas-im-designer.yaml --no-session

  # Phase 4: VALIDATE — goose-compliance check
  echo "ack" | goose run --with-builtin developer \
    --recipe recipe/sub/sub_mas-im-validator.yaml --no-session

  # Phase 5: APPLY — explicit "apply all CONFORM patches"
  echo "FULL_IMPROVEMENT - apply all CONFORM patches from
  R110-106 (designer TOP-N fix + F-022 spec-drift). ack" | \
    goose run --with-builtin developer \
    --recipe recipe/sub/sub_mas-general-improver.yaml --no-session

ERWARTETES ERGEBNIS:
  - recipe/instructions/sub_mas-im-designer.md Z.163 hat "TOP-N"
  - tests/test_sub_mas_pre_push_validator.py hat "19 critical checks"
  - git status -s zeigt 2-3 modified files
  - git diff --stat zeigt 2-4 insertions in den richtigen files
  - KEIN "beyond IM_TOP_N=5" mehr in .state/pipeline/patches.yaml

ROLLBACK-STRATEGY:
  - Falls der designer-fix fehlschlaegt: ranked_findings.yaml.patches
    bleibt leer, F-022 als follow-up R110-107 directive
  - Falls F-022 fix fehlschlaegt: nur designer-fix behalten, F-022
    in naechster run
