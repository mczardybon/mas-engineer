# R110-109 — sub_mas-self-audit + tools/dev_spec_invariant.py (R110-78 PHASE 3)
# 2026-08-04
# Quelle: R110-78 spec-drift lesson + R110-108 DIREKTIVE 2+3.
# R110-107 e2e-pilot hat den "mas-engineer kann sich nicht selbst fixen"
# blind spot entdeckt: im-finder sucht code-defects, im-designer drafted
# fuer ranked_findings (nicht fuer sich selbst), im-general-improver
# lehnt per R06 direkte file-writes ab. R110-109 schliesst diese luecke
# mit zwei neuen mechanismen.

Ziel-Repo: mas-engineer (mczardybon/mas-engineer)
Branch: cleanup
Parent-Commit: 391be5b (R110-108 directive)
Ref: R110-78 (commit 9c73100 spec-drift), R110-106 (commit 3b80259
     SD-detector), R110-107 (commit 9136778 directive), R110-108
     (commit 391be5b directive, R110-108 run bestaetigte SD-integration
     ist bereits via R110-106 commit 3b80259 erfuellt)

================================================================
DIREKTIVE 1: NEUER SUB-AGENT sub_mas-self-audit
================================================================

Aktueller zustand: mas-engineer hat keinen mechanismus um seine
eigenen recipe-instructions auf hardcoded-zahlen, stale literals
oder spec-drift zu auditten. Im-finder scanned code, nicht
recipes (ausser fuer SD-detection in tests).

Gewuenschter zustand: ein neuer sub-agent der als PHASE 0.5
(vor im-finder) laeuft und recipe-instructions walked.

KONKRETE SPEZIFIKATION:

  1. NEUE DATEI: mas-engineer/recipe/sub/sub_mas-self-audit.yaml
     Schema: gleiche YAML-struktur wie andere sub_mas-recipes
     (recipe: <name>, blocks: role, prompt, ...).
     Source inspiration: sub_mas-im-finder.yaml (einfachster
     finder, nur ein STEP).

  2. NEUE DATEI: mas-engineer/recipe/instructions/sub_mas-self-audit.md
     Body: 3-4 absaetze die den agent erklaeren (audit recipe-
     instructions auf hardcodes, stale literals, spec-drift).
     KEINE sub_recipes (selbst-detect mu recursive sein).

  3. EXECUTE-BLOCK in sub_mas-self-audit.yaml (STEP 1):
       shell(cmd="cd {workspace} && python3 -m dev_self_audit \
                --scope=recipe/instructions/ \
                --output {workspace}/.mase/pipeline/self_audit.yaml")

  4. NEUE DATEI: mas-engineer/tools/dev_self_audit.py
     Standalone-script (R110-106 pattern: importierbar als modul,
     CLI-callable). API:
       def run_self_audit(scope: Path, repo_root: Path) -> SelfAuditResult
       class SelfAuditResult:
           def to_findings(self) -> list[Finding]
     CLI: `python3 -m dev_self_audit --scope <dir> --repo-root <path>`
          exit 0 wenn clean, 1 sonst.

  5. DETECTION-ALGORITHMUS (high-level):
       for instruction_file in scope:
         for line_num, line in enumerate(instruction_file):
           # Pattern A: hardcoded zahlen die nicht env-var sind
           # Regex: r'\b(\d{2,})\s+(sub-agents|tools|phases|checks|tests)\b'
           # Skip wenn in gleicher zeile: $IM_TOP_N, ${...}, _N suffix
           # ODER wenn zahl in {(IM_TOP_N, IM_TOP_N_MULTIPLIER)} table
           if re.search(r'\b\d{2,}\s+(\w+)\b', line) and \
              not re.search(r'IM_TOP_N|env var|default\s+\d', line):
             emit_finding(SA-INSTRUCTION, HIGH, line_num, ...)

           # Pattern B: stale literal vs tools/files
           # (gleiche logic wie check_spec_drift, aber NUR fuer
           # recipe/instructions/)
           ...

  6. IDEMPOTENZ: sub_mas-self-audit muss sich selbst ausschliessen
     aus der detection. Detection via `instruction_file.name !=
     "sub_mas-self-audit.md"`.

================================================================
DIREKTIVE 2: tools/dev_spec_invariant.py (R110-78 PHASE 3)
================================================================

Aktueller zustand: R110-78 PHASE 3 spec (Z.286-309) ist nur
spec, keine implementierung. Es gibt keinen mechanismus der
test-count-assertions (z.B. "110 sub-agents") mit recipe-counts
vergleicht und bei mismatch blocked.

Gewuenschter zustand: standalone-script das IMMER laeuft (auch
ohne im-pipeline) und counts synchronisiert.

KONKRETE SPEZIFIKATION (R110-78 PHASE 3 wiederholung mit
R110-109-anpassungen):

  1. NEUE DATEI: mas-engineer/tools/dev_spec_invariant.py
     Standalone-script, importierbar als modul. API:
       def run_spec_invariant_check(repo_root: Path) -> SpecInvariantResult
       class SpecInvariantResult:
           def to_findings(self) -> list[Finding]
     CLI: `python3 -m dev_spec_invariant --repo-root <path>`
          exit 0 wenn alle invariants match, 1 sonst.

  2. EXTRACT-FUNKTIONEN:
     a) extract_count_assertions_from_tests(tests_dir):
        Regex: COUNT_ASSERT_RE = re.compile(
                 r'''assert\s+["'](\d+)\s+(\w[\w-]*)["']\s+in\s+''')
        TYPE_MIN_LEN = 2
        TYPE_BLACKLIST = {"tests", "files", "lines", "args",
                          "items", "keys", "values", "chars"}
        # Returns: dict[type, set[count]] z.B. {"sub-agents": {110}}
     b) extract_count_from_recipes(recipe_dir):
        Regex: r'(\d+)\s+(\w[\w-]*)' auf recipe/sub/*.yaml
        Skip in: comments, multiline-strings, valid_yaml
        Returns: dict[type, set[count]]

  3. INVARIANT-CHECK:
     for type, test_counts in test_assertions.items():
       recipe_counts = recipe_counts.get(type, set())
       if test_counts != recipe_counts:
         emit_finding(
           code=f"INVARIANT-{type}",
           severity=BLOCKER,
           description=f"Test asserts {test_counts} '{type}' "
                       f"but recipe declares {recipe_counts}",
           suggested_fix="Update test OR recipe to match (find "
                         "which is canonical via git blame)."
         )

  4. INTEGRATION: dev_spec_invariant.py laeuft als pre-push
     Check 18 (nach Check 17 pytest-run, in der implementierungs-
     reihenfolge). Naming-update analog R110-99 wenn zwischen-
     zeitlich Check 17+ hinzukommt.

  5. IDEMPOTENZ: skip wenn recipe/sub/sub_mas-pre-push-validator
     schon check_18_spec_invariant enthaelt (grep-detect).

================================================================
DIREKTIVE 3: TEST-COUNT-INVARIANT FIX FUER R110-78 PHASE 3
================================================================

Mit dev_spec_invariant.py aktiv MUSS der test-count invariant
gelten: pytest --collect-count == 1281 (oder neuer wert). Wenn
mas-engineer einen neuen test hinzufuegt ohne den invariant zu
pflegen, faengt Check 18 das. Wenn mas-engineer einen test
umbenennt ohne update, faengt Check 18 auch das.

ERWARTETER EFFEKT NACH R110-109:
  - Normal im-finder-run findet jetzt SD-* findings automatisch
    (via R110-106 commit 3b80259)
  - Normal pre-push-validator laeuft Check 17 (pytest) +
    Check 18 (spec-invariant) + NEU: sub_mas-self-audit als
    phase 0.5
  - SD-literal "16 checks" in sub_mas-pre-push-validator.md
    wird durch Check 17/18 NICHT gefunden (es ist text-literal,
    nicht count-instruction), ABER durch sub_mas-self-audit
    via Pattern A (hardcoded "16" ohne IM_TOP_N context)
  - im-designer Z.164 hardcoded "TOP-5" wird durch Pattern A
    gefunden, dann als SA-finding emittiert, dann von
    general-improver als mas-task an im-designer gegeben
    (das ist der R110-107-FOLLOW-UP architectural fix)

================================================================
Ausfuehrung via im-pipeline (R110-109 run)
================================================================

  cd /tmp/mas-engineer-test/mas-engineer
  set -a; . ./.env; set +a
  export PATH=$PATH:/root/.local/bin
  export GOOSE_SESSION_TAG="[r110-109-self-audit+invariant]"
  export MAS_WEB_RESEARCH=no
  export IM_TOP_N=30
  export IM_TOP_N_MULTIPLIER=3
  export RECURSION_OVERRIDE=2
  export MAS_TASK="apply"
  export MAS_CONFIRM=yes
  export MAS_APPROVE=y

  # Phase 0.5 (SELF-AUDIT) -- NEU
  echo "ack" | goose run --with-builtin developer \
    --recipe recipe/sub/sub_mas-self-audit.yaml --no-session

  # Phase 1 (FIND) -- findet jetzt auch SA-findings via sub_mas-self-audit
  echo "ack" | goose run --with-builtin developer \
    --recipe recipe/sub/sub_mas-im-finder.yaml --no-session

  # Phase 2 (RANK)
  echo "ack" | goose run --with-builtin developer \
    --recipe recipe/sub/sub_mas-im-rank.yaml --no-session

  # Phase 3 (DESIGN)
  echo "ack" | goose run --with-builtin developer \
    --recipe recipe/sub/sub_mas-im-designer.yaml --no-session

  # Phase 4 (VALIDATE)
  echo "ack" | goose run --with-builtin developer \
    --recipe recipe/sub/sub_mas-im-validator.yaml --no-session

  # Phase 5 (APPLY) -- DIREKTIVE 1+2 werden gefixt
  echo "FULL_IMPROVEMENT - apply sub_mas-self-audit agent +
  dev_spec_invariant.py per R110-109 DIREKTIVE 1+2. ack" | \
    goose run --with-builtin developer \
    --recipe recipe/sub/sub_mas-general-improver.yaml --no-session

ERWARTETES ERGEBNIS (5 files modified):
  - recipe/sub/sub_mas-self-audit.yaml (NEU, ~80 lines)
  - recipe/instructions/sub_mas-self-audit.md (NEU, ~50 lines)
  - tools/dev_self_audit.py (NEU, ~200 lines)
  - tools/dev_spec_invariant.py (NEU, ~200 lines)
  - recipe/sub/sub_mas-pre-push-validator.yaml (Check 18 ergaenzt)
  Total: ~530 insertions, 0 deletions, 5 files (4 new + 1 modified)

VERIFIKATION:
  - python3 -m dev_self_audit --scope recipe/instructions/ --repo-root .
    # exit 0 oder 1 (mit SA-findings)
  - python3 -m dev_spec_invariant --repo-root .
    # exit 0 wenn alle counts match
  - grep "check_18_spec_invariant" recipe/sub/sub_mas-pre-push-validator.yaml
    # MUSS >= 1 sein
  - ls recipe/sub/sub_mas-self-audit.yaml   # MUSS existieren
  - python3 -m pytest tests/ -q   # 1281/1281 PASS

ROLLBACK-STRATEGY:
  - Bei false-positives (SA-detector flagged legitime hardcodes):
    TYPE_BLACKLIST erweitern, oder severity HIGH -> MEDIUM
  - Bei recursion (self-audit audited sich selbst):
    Detection-skip in dev_self_audit.py hinzufuegen
  - Bei performance-problemen (self-audit dauert >60s):
    cache letztes result in .mase/pipeline/self_audit_cache.yaml

GOOSE-EXPERT CONSULT (R11):
  R11 prefix list matcht fuer R110-109: die neuen recipe-yaml
  files haben type A (NEW recipe). R11 GOOSE-EXPERT MUSS konsultiert
  werden vor dem apply. Im-validator step 4 macht das automatisch
  weil R11 ist in dessen step-3 eingebaut.

NICHT-ZIELE (R110-109 vs R110-110+):
  R110-109: self-audit + spec-invariant (DIREKTIVE 1+2)
  R110-110 (folgerun): R110-78 PHASE 2+3 acceptance kriterien
    verifizieren (acceptance-test fixtures, CI-integration)
  R110-111+ (optional): recipe-instruction L26 "16 checks" drift
    fix, weitere spec-drifts die im self-audit gefunden werden
