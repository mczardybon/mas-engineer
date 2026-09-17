# R110-107 — fix im-designer Z.164 hardcoded "TOP-5" (R110-106-FOLLOW-UP)
# 2026-08-04
# Quelle: R110-106 e2e-pilot (commit 3b80259) — designer hat 1 patch
# gedraftet (F-022), 15 weitere implementable findings wurden mit
# skip-reason "beyond IM_TOP_N=5 scope (default 5); not drafted this
# session" abgelehnt, obwohl IM_TOP_N=30 exportiert war und der
# rank-agent 16 items in top_N aufgenommen hatte.

Ziel-Repo: mas-engineer (mczardybon/mas-engineer)
Branch: cleanup
Parent-Commit: 3b80259 (R110-106)
Quelle: R110-106 e2e + directive R110-106-designer-im-top-n-respect

================================================================
DIREKTIVE 1: recipe/instructions/sub_mas-im-designer.md Z.164 fix
================================================================

Aktueller zustand (3 stellen):
  Z.160: "- data: {ranked_findings: [], top_N: [] (length=IM_TOP_N
          env var, default 5), scores: {}}"
  Z.164: "## STEP 1 — DRAFT ONE PATCH FOR EACH TOP-5 FINDING"
  Im skip-reason block (spätere zeile, suesse "beyond IM_TOP_N=5
  scope"): "Ranked but beyond IM_TOP_N=5 scope (default 5); not
  drafted this session."

Gewuenschter zustand: alle 3 stellen dynamisch zum IM_TOP_N env var
(der IM_TOP_N_MULTIPLIER bleibt unangetastet — der ist ein
separater factor fuer den rank-agent, nicht fuer den designer).
Die "5" in der ueberschrift MUSS raus. Die laenge kommt aus
top_N (vom rank-agent), nicht aus einer constant.

KONKRETE SPEZIFIKATION:

  1. DATEI: mas-engineer/recipe/instructions/sub_mas-im-designer.md
     AENDERUNG Z.164:
     VORHER:  "## STEP 1 — DRAFT ONE PATCH FOR EACH TOP-5 FINDING"
     NACHHER: "## STEP 1 — DRAFT ONE PATCH FOR EACH ENTRY IN top_N
              (length = IM_TOP_N env var, default 5)"
     Body der section: erklaere dass der designer fuer JEDEN eintrag
     in data.top_N einen patch draftet (nicht fuer die ersten 5).

  2. DATEI: mas-engineer/recipe/instructions/sub_mas-im-designer.md
     AENDERUNG skip-reason block:
     VORHER:  "Ranked but beyond IM_TOP_N=5 scope (default 5); not
              drafted this session."
     NACHHER: "Ranked but beyond top_N scope (IM_TOP_N env var, default
              5); not drafted this session."
     Der wert ist nicht mehr hardcoded 5 sondern kommt aus dem env var.

  3. DATEI: mas-engineer/recipe/instructions/sub_mas-im-designer.md
     Z.160 (data: zeile) bleibt wie sie ist — die ist bereits korrekt
     ("top_N: [] (length=IM_TOP_N env var, default 5)") und dient als
     specification der datenquelle. KEINE aenderung hier noetig.

  4. IDEMPOTENZ: falls die section schon "TOP-N" heisst (von einem
     frueheren run applied), idempotent ueberspringen. Detection via
     `grep -q "TOP-N FINDING\\|ENTRY IN top_N" recipe/instructions/
     sub_mas-im-designer.md`.

================================================================
DIREKTIVE 2: e2e-verifikation des fixes
================================================================

Nach dem apply MUSS ein IM_TOP_N=30 run zeigen:
  - finder: schreibt 16+ implementable findings in .mase/pipeline/
    findings.yaml (mind. 3 davon type Q1-Q3 settings-adjust oder
    C1-C4 instructions-update, weil die mit dem "5" hardcode zu
    tun haben)
  - rank: 16+ items in top_N (length = 30 weil IM_TOP_N=30, aber
    die meisten sind R52-fail und werden nicht zu patches)
  - designer: drafts ANZAHL_PATCHES > 1 (vorher war 1, jetzt mind. 2-3)
  - skip-reason: KEIN "beyond IM_TOP_N=5 scope" mehr auftauchen
  - improver: applied ANZAHL_PATCHES > 0 Patches, alle mit
    GOOSE-COMPLIANT verdict

VERIFIKATION:
  - cd /tmp/mas-engineer-test/mas-engineer
  - grep -c "TOP-N FINDING\\|ENTRY IN top_N" recipe/instructions/
    sub_mas-im-designer.md   # MUSS >= 1 sein
  - grep -c "beyond IM_TOP_N=5 scope" recipe/instructions/
    sub_mas-im-designer.md   # MUSS 0 sein
  - python3 -m pytest tests/ -q   # 1281/1281 PASS
  - git show --stat HEAD | head -5   # 1-2 modified files

================================================================
DIREKTIVE 3: nicht-ziele (was R110-107 NICHT tut)
================================================================

A) KEIN neues env var. IM_TOP_N bleibt single source of truth. Wer
   ein neues IM_DESIGNER_TOP_N will, kann das in R110-108+
   vorschlagen — R110-107 fixt nur den hardcode.

B) KEIN refactor der skip-reason logic. Der skip-reason selbst ist
   eine korrekte fehlermeldung (manche findings werden wirklich
   geskippt weil sie R52-fail sind); R110-107 aendert NUR die
   "beyond IM_TOP_N=5 scope" → "beyond top_N scope" formulierung.

C) KEIN neuer test. Die existierenden 1281 tests + die 4 SD-detector
   tests decken den fix implizit ab (der im-designer wird via
   recipe geladen, nicht via test). Wenn ein dedizierter
   im-designer-test gewuenscht ist, ist das R110-108 territory.

D) KEIN anderer recipe. sub_mas-im-finder, -rank, -validator,
   -general-improver sind korrekt — der bug ist NUR im
   im-designer.

================================================================
Ausfuehrung via im-pipeline (R110-107 run)
================================================================

  cd /tmp/mas-engineer-test/mas-engineer
  set -a; . ./.env; set +a
  export PATH=$PATH:/root/.local/bin
  export GOOSE_SESSION_TAG="[r110-107-im-top-n-fix]"
  export MAS_WEB_RESEARCH=no
  export IM_TOP_N=30
  export IM_TOP_N_MULTIPLIER=3
  export RECURSION_OVERRIDE=2
  export MAS_TASK="apply"
  export MAS_CONFIRM=yes
  export MAS_APPROVE=y

  # Phase 1-3 (FIND+RANK+DESIGN)
  # Designer MUSS jetzt patches fuer ALLE items in top_N draften
  # (nicht nur top-5). Verifier via patches.yaml.patches.length > 1.
  echo "ack" | goose run --with-builtin developer \
    --recipe recipe/sub/sub_mas-im-finder.yaml --no-session
  echo "ack" | goose run --with-builtin developer \
    --recipe recipe/sub/sub_mas-im-rank.yaml --no-session
  echo "ack" | goose run --with-builtin developer \
    --recipe recipe/sub/sub_mas-im-designer.yaml --no-session

  # Phase 4: VALIDATE
  echo "ack" | goose run --with-builtin developer \
    --recipe recipe/sub/sub_mas-im-validator.yaml --no-session

  # Phase 5: APPLY
  echo "FULL_IMPROVEMENT - apply all CONFORM patches from
  R110-107 (im-designer Z.164 TOP-5 -> TOP-N). ack" | \
    goose run --with-builtin developer \
    --recipe recipe/sub/sub_mas-general-improver.yaml --no-session

ERWARTETES ERGEBNIS:
  - recipe/instructions/sub_mas-im-designer.md Z.164 hat
    "TOP-N FINDING" / "ENTRY IN top_N"
  - skip-reason block hat "beyond top_N scope (IM_TOP_N env var,...)"
    NICHT "beyond IM_TOP_N=5 scope"
  - git status -s zeigt 1 modified file
  - git diff --stat zeigt 2-4 insertions in der richtigen file
  - KEIN "beyond IM_TOP_N=5" mehr in recipe/instructions/
    sub_mas-im-designer.md
  - patches.yaml.patches.length > 1 (vorher = 1)

ROLLBACK-STRATEGY:
  - Falls designer-fix fehlschlaegt: skip-reason hat noch "=5
    hardcode" — neu als R110-108 directive
  - Falls patches.yaml leer bleibt (alle R52-fail):
    trotzdem committen mit "fix(im-designer): respect IM_TOP_N
    env var" + note im body dass 0 weitere patches drafted
  - Falls der find-step zu viele findings produziert (>50): mit
    IM_TOP_N=10 re-runnen (default-nahe)

GOOSE-EXPERT CONSULT (R11):
  R11 prefix list matcht NICHT fuer R110-107 — der fix ist pure
  text-substitution (kein Goose-architecture touch). R11 ist nicht
  noetig. Im-validator step 4 wird trotzdem goose-compliance
  automatisch pruefen.
