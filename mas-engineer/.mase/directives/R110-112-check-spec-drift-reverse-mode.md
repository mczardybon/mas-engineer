# R110-112 — check_spec_drift() reverse-mode extension (recipe -> test)
# 2026-08-04
# Quelle: R110-111 directive hat den L26 "16 checks" vs test-assert
# "17 critical checks" drift gefunden. check_spec_drift() in
# tools/dev_im_finder_scan.py (R110-106 commit 3b80259, Z.659-740)
# deckt nur die test->recipe richtung ab ("literal-only-in-tests").
# R110-112 spec'd die umgekehrte richtung ("literal-only-in-recipe"):
# recipe sagt einen wert, der test akzeptiert einen anderen wert.

Ziel-Repo: mas-engineer (mczardybon/mas-engineer)
Branch: cleanup
Parent-Commit: 902c9a3 (R110-111 directive)
Ref: R110-111 (L26 drift), R110-106 (check_spec_drift original),
     R110-78 (spec-drift lesson), R110-71 (R110-78 spec-drift
     incident trigger)

================================================================
DIREKTIVE 1: check_spec_drift() reverse-mode parameter
================================================================

Aktueller zustand:
  tools/dev_im_finder_scan.py Z.659-740 hat check_spec_drift(
  findings, repo_root='.'). Logik:
    1. fuer jedes test_*.py in tests/
    2. extract literals via _SD_STRING_IN_RE / _SD_INT_EQ_RE /
       _SD_INT_CMP_RE
    3. fuer jedes literal L: check ob L in recipe/tools/docs ist
    4. wenn NEIN: emit_finding('SD-test_<base>-<idx>', 'medium',
       ..., 'literal-only-in-tests ...')

  Was fehlt: das reziproke. Wenn recipe Z.B. "16 checks" sagt,
  der test aber "17 critical checks" verlangt, ist das ein drift
  in der anderen richtung. Aktuell emittiert check_spec_drift()
  das NICHT weil es nur in test-files scannt.

Gewuenschter zustand:
  tools/dev_im_finder_scan.py hat eine NEUE funktion
  check_spec_drift_reverse(findings, repo_root='.') die:
    1. fuer jedes recipe/instructions/*.md und tools/dev_*.py
       (spec-quellen)
    2. extract numeric literals via regex (\b\d{2,}\s+\w+\b) +
       string literals via _SD_STRING_IN_RE (nur "X checks"-style
       patterns, nicht alle strings)
    3. fuer jedes literal L: check ob L in tests/ (test-asserts)
       vorkommt
    4. wenn NEIN: emit_finding('SD-recipe_<file-basename>-<idx>',
       'medium', ..., 'literal-only-in-recipe ...')

KONKRETE SPEZIFIKATION:

  1. NEUE FUNKTION: check_spec_drift_reverse(findings, repo_root='.')
     in tools/dev_im_finder_scan.py Z.659+ (nach check_spec_drift
     definition, vor dem "try: check_spec_drift(...)" aufruf Z.746).

  2. SCOPE-DEFINITION:
     recipe_sources = [
       os.path.join(repo_root, 'recipe/instructions'),
       os.path.join(repo_root, 'tools'),  # dev_*.py only
     ]
     test_files = glob.glob(tests/test_*.py, recursive=True)

  3. EXTRACT-LOGIC (analog check_spec_drift Z.687-693):
     # In recipe/instructions/*.md:
     _RECIPE_NUMERIC_RE = re.compile(r'\b(\d{2,})\s+(\w[\w-]+)')
     for line in instruction_file:
       if line.lstrip().startswith('#'): continue
       for m in _RECIPE_NUMERIC_RE.finditer(line):
         # filter: skip if in-code, in-table, in-example-block
         # (heuristic: line has "passed:" or "❌" or "```")
         if _is_in_code_block(lines, ln - 1): continue
         if _is_in_table_or_example(lines, ln - 1): continue
         yield (literal, line_num, file)

  4. TEST-ASSERT-CHECK (analog check_spec_drift Z.707-727):
     for L, ln, src in literals:
       hit = False
       for tf in test_files:
         try:
           with open(tf) as fh:
             if L in fh.read():
               hit = True
               break
         except: continue
       if not hit:
         emit_finding('SD-recipe_<file-base>-<idx>', 'medium',
                      f'{src}:{ln}',
                      f"spec_drift_reverse: recipe asserts literal "
                      f"'{L}' but it is absent from tests/ (recipe-side "
                      f"drift = recipe was updated without test fix, "
                      f"or test expects a different value)",
                      f"Test will pass but recipe contradicts itself. "
                      f"Run: grep -rn '{L}' tests/ recipe/ ; if only "
                      f"recipe/ matches: test is stale; if tests/ matches "
                      f"different value: recipe is stale",
                      f"Update recipe OR test to match (find which is "
                      f"canonical via git blame).")

  5. SEVERITY-LOGIC:
     - MEDIUM default (wie check_spec_drift)
     - BLOCKER wenn literal im format "N checks" (count-assertion
       gegen test-anchor) UND test-anchor eine andere zahl nennt
       (dann ist es exakt das R110-111 L26 pattern)
     - INFO sonst (recipe-only literatur, kein test-anchor)

  6. IDEMPOTENZ: skip wenn check_spec_drift_reverse schon definiert
     in tools/dev_im_finder_scan.py (grep-detect).

  7. NICHT ZU TUN:
     - Kein refactor der bestehenden check_spec_drift() funktion
     - Kein neuer finding-type-prefix (SD-* bleibt, plus
       SD-recipe_* variant)
     - Kein neuer aufruf-call (block unten erweitern statt Z.747
       patchen)
     - Kein neues test-file (test-count invariant 1281)

================================================================
DIREKTIVE 2: SEVERITY-LOGIC erweiterung
================================================================

check_spec_drift_reverse() emittiert MEDIUM per default, aber
"R-count checks" + "test-anchor different" = BLOCKER. Begruendung:
  - test-anchor ist canonical (per R110-78 DIREKTIVE 1: pytest
    ist ground truth)
  - recipe-count assertion die nicht mit test-anchor ueberein-
    stimmt = spec-drift, was pytest-count-mismatch erzeugen kann
  - BLOCKER severity weil das direkt R110-78 PHASE 1 (validator
    + pytest) verletzt

KONKRETE SPEZIFIKATION:
  In check_spec_drift_reverse() nach dem hit-test:
    if re.search(r'\d+\s+checks?\b', L):  # "16 checks" pattern
      # check ob test-anchor eine andere zahl hat
      test_anchor = re.search(r'["\'](\d+)\s+checks?["\']',
                              test_file_content)
      if test_anchor and test_anchor.group(1) != L.split()[0]:
        emit_finding(severity='blocker', ...)
      else:
        emit_finding(severity='medium', ...)
    else:
      emit_finding(severity='medium', ...)

================================================================
DIREKTIVE 3: BLOCKER severity integration
================================================================

Aktueller zustand: im-finder emittiert findings mit severity
"high" / "medium" / "low" / "info" / "🟢 low". BLOCKER als severity
gibt es noch nicht (R110-78 lesson: pre-push-validator hat "BLOCK"
als prefix in der echo-output, nicht als finding-severity).

Gewuenschter zustand: finding-severity "blocker" wird als
gueltiger wert akzeptiert in add_finding() (tool-validation
update) und in pre-push-validator (Check 16+ severity_filter)
respektiert.

KONKRETE SPEZIFIKATION (R110-112 macht NUR die severity-validierung,
den pre-push-validator update ist R110-113 territory):
  1. DATEI: tools/dev_im_finder_scan.py
     add_finding() hat ein severity-validation dict
     (z.B. {'high': 90, 'medium': 65, 'low': 35, 'info': 10,
     'blocker': 100}). Update den dict um 'blocker': 100 (over
     'high').
  2. Pre-push-validator Check 16+ (R110-94) liest severity aus
     findings, filtert nach active_ceiling. Default-ceiling ist
     'high' (rank score >= 80). BLOCKER findings (score 100)
     passen den filter IMMER (severity > high).
  3. NICHT ZU TUN: kein update der validator-instruction hier
     (R110-113 spec'd das separat); nur add_finding() validation.

================================================================
Ausfuehrung via im-pipeline (R110-112 run)
================================================================

  cd /tmp/mas-engineer-test/mas-engineer
  set -a; . ./.env; set +a
  export PATH=$PATH:/root/.local/bin
  export GOOSE_SESSION_TAG="[r110-112-reverse-mode]"
  export MAS_WEB_RESEARCH=no
  export IM_TOP_N=30
  export IM_TOP_N_MULTIPLIER=3
  export RECURSION_OVERRIDE=2
  export MAS_TASK="apply"
  export MAS_CONFIRM=yes
  export MAS_APPROVE=y

  # Phase 1 (FIND)
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

  # Phase 5 (APPLY) -- DIREKTIVE 1+2+3 werden gefixt
  echo "FULL_IMPROVEMENT - apply R110-112: extend
  tools/dev_im_finder_scan.py with check_spec_drift_reverse()
  function. Pattern: same as check_spec_drift but scan
  recipe/instructions/*.md + tools/dev_*.py, emit
  SD-recipe_<base>-<idx> findings (medium default, BLOCKER for
  'N checks' literal with mismatched test-anchor). Update
  add_finding() severity dict to include 'blocker': 100. ack" | \
    goose run --with-builtin developer \
    --recipe recipe/sub/sub_mas-general-improver.yaml --no-session

ERWARTETES ERGEBNIS (1 file modified, ~80 insertions):
  - tools/dev_im_finder_scan.py +check_spec_drift_reverse()
    (~70 lines) +severity-dict update (~3 lines)
  - Total: 1 file, ~80 insertions, 0 deletions
  - pytest 1281/1281 PASS
  - 1 commit

VERIFIKATION:
  - grep "def check_spec_drift_reverse" tools/dev_im_finder_scan.py
    # MUSS >= 1 sein
  - python3 -c "from dev_im_finder_scan import check_spec_drift_reverse;
                print('import OK')"   # MUSS OK sein
  - python3 -m dev_im_finder_scan --check-spec-drift --repo-root .
    # MUSS SD-recipe_* findings emittieren fuer recipe L26
    "16 checks" (test-anchor: "17 critical checks" oder
    "17 checks" -> BLOCKER)
  - python3 -m pytest tests/ -q   # 1281/1281 PASS
  - git show --stat HEAD | head -3   # 1 file modified

ROLLBACK-STRATEGY:
  - Bei false-positive BLOCKER: severity-logic tuning
    (DIREKTIVE 2 spec section 2) anpassen
  - Bei performance-issue: scanner-cache in .mase/pipeline/
    sd_reverse_cache.yaml (R110-113+)
  - Bei recursion (reverse detect detected sich selbst):
    SCOPE-DEFINITION erweitern um `if 'dev_im_finder_scan' in
    file: skip`

GOOSE-EXPERT CONSULT (R11):
  R11 prefix list matcht fuer R110-112: 1 file modified
  (tools/), type B (BACKEND/standalone script). R11 GOOSE-EXPERT
  MUSS konsultiert werden vor dem apply. Im-validator step 4
  macht das automatisch.

NICHT-ZIELE (R110-112 vs R110-113+):
  R110-112: check_spec_drift_reverse() + BLOCKER severity
  R110-113: sub_mas-new-agent recipe (R110-109 self-creation fix)
  R110-114: pre-push-validator Check 18 (R110-109 spec'd)
  R110-115+ (optional): weitere reverse-mode-detections (z.B.
    tools/ sagt X aber recipe/ sagt Y)
