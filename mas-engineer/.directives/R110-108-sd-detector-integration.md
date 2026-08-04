# R110-108 — integrate SD-detector into sub_mas-im-finder (PHASE 2 of R110-78)
# 2026-08-04
# Quelle: R110-106 commit 3b80259 hat die SD-detection logic in
# tools/dev_im_finder_scan.py getan, aber R110-78 PHASE 2 spec sagt
# explizit "SD-* finding type in sub_mas-im-finder einbauen" (DIREKTIVE 2
# der R110-78 directive, Z.220-268). R110-108 ist die spec-compliance
# Korrektur: logic von tools/ in die recipe wandern lassen.

Ziel-Repo: mas-engineer (mczardybon/mas-engineer)
Branch: cleanup
Parent-Commit: 9136778 (R110-107 directive)
Ref: R110-78 (commit 9c73100 spec-drift incident), R110-106 (commit
     3b80259 SD-detector), R110-99 (Check 17 naming), R110-94
     (Check 16+ historical-drift)

================================================================
DIREKTIVE 1: SD-detection in sub_mas-im-finder.yaml integrieren
================================================================

Aktueller zustand:
  - tools/dev_im_finder_scan.py Z.659-749 hat check_spec_drift()
    funktion die 4 test-files (test_sd_fixture_r110105.py) durch
    ein 6-step pattern laufen laesst und SD-<file>-<idx> findings
    emittiert.
  - sub_mas-im-finder.yaml (recipe) ruft diese logic NICHT auf --
    sie ist standalone in tools/, nicht in der im-finder pipeline.
  - Resultat: die R110-106 e2e-pilot demonstration hat 16 implementable
    findings gefunden (F-001 Q4 + F-022 SD + 14x NN1), aber nur weil
    ich den detector manuell im R110-106 e2e-pilot gestartet habe.
    Normale im-pipeline runs (R110-78, R110-94, R110-100) haben KEINE
    spec-drift detection.

Gewuenschter zustand:
  - sub_mas-im-finder.yaml recipe hat einen neuen STEP (STEP 2.5 oder
    vergleichbar) der check_spec_drift() aufruft
  - tools/dev_im_finder_scan.py bleibt als standalone script erhalten
    (mancher test-fixture-run will es ohne recipe)
  - beide rufen die gleiche funktion auf (extract_asserted_literals +
    check_spec_drift) -- single source of truth

KONKRETE SPEZIFIKATION:

  1. DATEI: mas-engineer/recipe/sub/sub_mas-im-finder.yaml
     NEUER STEP nach dem existierenden code-defect-scan (STEP 2)
     und vor dem rank-output (STEP 3):
       STEP 2.5: spec-drift scan via check_spec_drift()
       Aufruf: python3 -m dev_im_finder_scan --check-spec-drift
                --repo-root . --output .state/pipeline/sd_findings.yaml
       Output: SD-<test-basename>-<idx> findings (medium severity)
               in sd_findings.yaml
       Merge: rank-agent liest jetzt ZWEI files (findings.yaml +
              sd_findings.yaml), dedupliziert per finding_id.

  2. DATEI: mas-engineer/recipe/sub/sub_mas-im-finder.yaml
     PROMPT-UPDATE: description block erweitern um
       "STEP 2.5 spec-drift: walk tests/*.py fuer assert-literals
        die in recipe/tools/docs fehlen (siehe R110-78 DIREKTIVE 2 +
        tools/dev_im_finder_scan.py:check_spec_drift)."

  3. IDEMPOTENZ: falls check_spec_drift() schon im recipe-body
     referenziert wird (von einem frueheren run applied), skip.
     Detection: `grep -q "check_spec_drift\\|spec-drift scan" recipe/
     sub/sub_mas-im-finder.yaml`.

  4. NICHT ZU TUN:
     - KEIN neues finding-type-prefix. SD-* bleibt.
     - KEIN refactor von tools/dev_im_finder_scan.py -- die ist
       korrekt, nur die integration fehlt.
     - KEIN neues test-file fuer diese integration (das wuerde den
       test-count invariant verletzen wenn mas-engineer selbst
       1282 tests erwartet). Wenn der integration gewuenscht ist,
       in R110-109+ vorschlagen.

================================================================
DIREKTIVE 2: R110-107-FOLLOW-UP self-audit agent
================================================================

Aktueller zustand: R110-107 versucht im-designer Z.164 "TOP-5
FINDING" hardcode zu fixen, aber mas-engineer kann seine eigene
recipe-instruction nicht selbst fixen weil:
  a) im-finder sucht code-defects, nicht recipe-self-bugs
  b) im-designer drafted patches fuer ranked_findings, nicht
     fuer sich selbst
  c) im-general-improver lehnt direct file-writes per R06 ab

Der R110-107 run (commit 9136778) hat das bestaetigt: 0 patches
gedraftet, alle 16 findings either already-applied oder R52-fail.

Gewuenschter zustand: ein neuer sub-agent "self-audit" der:
  1. recipe/instructions/*.md walked (alle 11+ instruction files)
  2. hardcoded zahlen sucht (regex \b\d{2,}\b) die nicht als
     `IM_TOP_N` oder `IM_TOP_N_MULTIPLIER` referenziert sind
  3. SA-* finding (self-audit) emittiert mit severity HIGH weil
     recipe-instructions sind user-facing contract

KONKRETE SPEZIFIKATION (skizze, vollstaendige spec in R110-109):

  1. NEUER AGENT: sub_mas-self-audit (recipe/sub/sub_mas-self-audit.yaml)
  2. TOOL: tools/dev_self_audit.py (standalone, callable als modul)
  3. INTEGRATION: im-pipeline phase 0.5 (vor im-finder) laeuft
     self-audit + schreibt .state/pipeline/self_audit_findings.yaml
  4. AUSGABE: SA-<instruction-file>-<line>-<idx> findings HIGH
  5. IDEMPOTENZ: SA-detector darf NICHT sich selbst detecten
     (regex muss IM_TOP_N etc. ausschliessen)

Diese direkive ANWEIST nur dass R110-109 spec erstellt wird; die
vollstaendige implementierung ist follow-up weil R110-108 selbst
schon 2-3h aufwand ist (DIREKTIVE 1 ist die kritische spec-fix
die R110-78 PHASE 2+3 blockiert).

================================================================
DIREKTIVE 3: R110-78 PHASE 3 trigger
================================================================

PHASE 3 von R110-78 ist "tools/dev_spec_invariant.py + 2 hooks",
estimated ~3h, medium risk. Aktuell ist das nur spec (R110-78
Z.286-309), keine implementierung.

DIESE DIREKTIVE MACHT PHASE 3 NICHT. Sie TRIGGERED es: nach
DIREKTIVE 1 fertig ist, ist R110-109 fokussiert auf PHASE 3
(dev_spec_invariant.py standalone script + integration in
im-finder + pre-push-validator Check 18).

Nicht-ziele (R110-108 vs R110-109):
  R110-108 (dieser run): SD-detection integration in im-finder
  R110-109 (folgerun): spec-invariant + self-audit agent
  R110-110+ (optional): R110-78 PHASE 4 (hermes-side bereits
    done per R110-77 pre-push-gate skill)

================================================================
Ausfuehrung via im-pipeline (R110-108 run)
================================================================

  cd /tmp/mas-engineer-test/mas-engineer
  set -a; . ./.env; set +a
  export PATH=$PATH:/root/.local/bin
  export GOOSE_SESSION_TAG="[r110-108-sd-integration]"
  export MAS_WEB_RESEARCH=no
  export IM_TOP_N=30
  export IM_TOP_N_MULTIPLIER=3
  export RECURSION_OVERRIDE=2
  export MAS_TASK="apply"
  export MAS_CONFIRM=yes
  export MAS_APPROVE=y

  # Phase 1 (FIND) -- wird R110-106 SD-detector jetzt MIT ausfuehren
  #   weil DIREKTIVE 1 integriert
  echo "ack" | goose run --with-builtin developer \
    --recipe recipe/sub/sub_mas-im-finder.yaml --no-session

  # Phase 2 (RANK) liest jetzt 2 files
  echo "ack" | goose run --with-builtin developer \
    --recipe recipe/sub/sub_mas-im-rank.yaml --no-session

  # Phase 3 (DESIGN)
  echo "ack" | goose run --with-builtin developer \
    --recipe recipe/sub/sub_mas-im-designer.yaml --no-session

  # Phase 4 (VALIDATE)
  echo "ack" | goose run --with-builtin developer \
    --recipe recipe/sub/sub_mas-im-validator.yaml --no-session

  # Phase 5 (APPLY) -- DIREKTIVE 1 wird gefixt
  echo "FULL_IMPROVEMENT - apply SD-detector integration in
  sub_mas-im-finder.yaml per R110-108 DIREKTIVE 1. ack" | \
    goose run --with-builtin developer \
    --recipe recipe/sub/sub_mas-general-improver.yaml --no-session

ERWARTETES ERGEBNIS:
  - recipe/sub/sub_mas-im-finder.yaml hat neuen STEP 2.5 der
    dev_im_finder_scan --check-spec-drift aufruft
  - sub_mas-im-finder.yaml description erwaehnt spec-drift scan
  - tools/dev_im_finder_scan.py unveraendert (standalone-script
    bleibt)
  - 2 files modified: recipe/sub/sub_mas-im-finder.yaml +
    evt. .state/pipeline/sd_findings.yaml
  - pytest 1281/1281 PASS
  - normaler im-pipeline run findet jetzt SD-findings AUTOMATISCH
    (vorher: nur manuelle R110-106 e2e-pilot demonstration)

VERIFIKATION:
  - grep "check_spec_drift\|spec-drift scan" recipe/sub/
    sub_mas-im-finder.yaml   # MUSS >= 1 sein
  - python3 -m dev_im_finder_scan --check-spec-drift --repo-root .
    # exit 0, .state/pipeline/sd_findings.yaml geschrieben
  - python3 -m pytest tests/ -q   # 1281/1281 PASS
  - git show --stat HEAD | head -5   # 1-2 modified files

ROLLBACK-STRATEGY:
  - Falls recipe-update fehlschlaegt: rollback via git revert HEAD
    (vorher commit-hash ist 9136778)
  - Falls SD-detection false-positives in normal run erzeugt:
    severity-tuning in tools/dev_im_finder_scan.py (medium -> low)
    als R110-109 folge-task
  - Falls R52 split preconditions die SD-detection blockieren:
    im-designer skip-reason um "SD-* findings" erweitern

GOOSE-EXPERT CONSULT (R11):
  R11 prefix list matcht NICHT fuer R110-108 -- die aenderung ist
  recipe-yaml-only, keine types A/B/D/MM/JJ/S/HH/LL. R11 nicht
  noetig. Im-validator step 4 wird goose-compliance automatisch
  pruefen.
