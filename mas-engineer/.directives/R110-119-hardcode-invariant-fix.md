# R110-119 — fix HARDCODE warnings + INVARIANT BLOCKER findings

## CONTEXT (R110-78 PHASE 3 + R110-109 closure)

R110-118 (f4277fc) implementierte sub_mas-self-audit + Check 18
spec-invariant. Erster standalone-run fand 4 BLOCKER + 19 HARDCODE
warnings in recipe/instructions/. **Beweis dass Check 18 / Pattern A
echte drift captured** — genau wofuer R110-78 spec-drift lesson
gebaut wurde.

R110-119 fixed diese findings:

  HARDCORE-STALE (canonical = 2026-08-04, simple sed-replace):
  - 96 sub-agents → 112 sub-agents (5x in bootstrap, generic-init)
  - 57 tools → 58 tools (5x in bootstrap, generic-init,
    system-knowledge)
  - 12/13 checks (in config-auditor, mas-controller) — research
    was canonical ist, dann update

  CONTEXT-DEPENDENT (NICHT blind fixen, R110-78 lesson R02: verify
  before changing):
  - 43 sub-agents (config-auditor L92+97, "MAS sub-agents + 43
    sub-agents" — unklar was 43 sind, vermutlich user-team-agenten)
  - 47 sub-agents (im-finder L471, "timeout=120s for 47 sub-agents
    to validate" — historisch wert, evtl raised to 112)
  - 120 sub-agents (pre-push-validator L531, "120 sub-agents and
    only ~2 dedicated test files" — historisch)
  - 44 sub-agents (system-knowledge L13, "52 specialists + 44
    sub-agents" — andere gruppierung)
  - 20 sub-agents (team-packager L364, "more than 20 sub-agents:
    warn" — team-size threshold, parameter)

  INVARIANT BLOCKER (4 findings, R110-78 PHASE 3 spec-compliance):
  - INVARIANT-min [5] → recipe declares ∅
  - INVARIANT-new [4] → recipe declares [3]
  - INVARIANT-scopes [14] → recipe declares ∅
  - INVARIANT-sub-agents [6, 110] → recipe declares [3, 4, 6, 110]

## DIREKTIVE 1: FIX SIMPLE-STALE HARDCODE

Update `recipe/instructions/sub_mas-bootstrap.md` (4x stale):
  L4: "All 96 sub-agents, 57 tools" → "All 112 sub-agents, 58 tools"
  L16: "all 96 sub-agents" → "all 112 sub-agents"
  L17: "57 tools" → "58 tools"
  L40: "ALL 96 sub-agents, 57 tools" → "ALL 112 sub-agents, 58 tools"

Update `recipe/instructions/sub_mas-generic-init.md` (1x):
  L39: "all 96 sub-agents + 57 tools" → "all 112 sub-agents + 58
       tools"

Update `recipe/instructions/sub_mas-system-knowledge.md` (2x):
  L12: "57 tools" → "58 tools"
  L13: "44 sub-agents" → RESEARCH: was 44 bedeutet (R02 lesson)
  L133: "57 tools" → "58 tools"
  L149: "57 tools" → "58 tools"

Update `recipe/instructions/sub_mas-team-packager.md` (1x):
  L65: "57 tools" → "58 tools"

Update `recipe/instructions/sub_mas-config-auditor.md` (2x):
  L92+97: "43 sub-agents" → RESEARCH oder comment
  L136: "12 checks" → RESEARCH canonical checks count

Update `recipe/instructions/sub_mas-mas-controller.md` (1x):
  L31: "13 checks" → RESEARCH canonical checks count

## DIREKTIVE 2: RESEARCH CONTEXT-DEPENDENT COUNTERS

Diese counters sind context-dependent, brauchen RESEARCH
bevor sie geupdated werden:

  1. "43 sub-agents" in config-auditor L92+97 (contexte:
     "MAS sub-agents + 43 sub-agents" — sind 43 die
     user-team agents die NICHT zu mas-self registry
     gehoeren? Dann canonical und NICHT fixen).
  2. "47 sub-agents" in im-finder L471 (contexte: "timeout=120s
     for 47 sub-agents to validate" — war der timeout
     historisch gesetzt? Wenn ja, raised to 112 wegen
     aktuelle sub-agent count).
  3. "120 sub-agents" in pre-push-validator L531 (contexte:
     "120 sub-agents and only ~2 dedicated test files" — war
     historisch der stand vor R110-31 expansion. Wenn L531
     eine RECHTFERTIGUNG fuer Check 12 (test coverage gate)
     ist, dann update to 112).
  4. "44 sub-agents" in system-knowledge L13 (contexte: "52
     specialists + 44 sub-agents + 4 core recipes" — sind 44
     ein anderer subset? Wenn ja, nicht 112.).
  5. "20 sub-agents" in team-packager L364 (contexte: "more
     than 20 sub-agents: warn" — TEAM-SIZE THRESHOLD,
     parameter, NICHT 112).

ACTION: Research-Modus (NICHT blind aendern):
  - grep `git log -p` history for "43", "47", "44", "120" um
    zu sehen wann die counts gesetzt wurden und warum
  - Wenn count ist HISTORICAL: comment mit `(historical, 2026-07-XX:
    count was 43)` hinzufuegen
  - Wenn count ist THRESHOLD: comment mit `(threshold, update to
    112 if mas-team-typical-size increases)` hinzufuegen
  - Wenn count ist ACTIVE STALE: update to 112

## DIREKTIVE 3: FIX INVARIANT BLOCKERS

Die 4 INVARIANT BLOCKER sind R110-78 PHASE 3 spec-compliance. Sie
blocken den push. Fix:

  a) INVARIANT-min [5] 'min' in tests, ∅ in recipe
     → check tests/test_*.py fuer `"5 min"` oder `5\s+min`
     → check recipe/sub/*.yaml fuer `5\s+min`
     → git blame um canonical zu finden
  b) INVARIANT-new [4] 'new' in tests, [3] in recipe
     → similar: 4 in tests, 3 in recipe
  c) INVARIANT-scopes [14] 'scopes' in tests, ∅ in recipe
     → 14 scopes-assertion in test, kein recipe declares
  d) INVARIANT-sub-agents [6, 110] in tests, [3, 4, 6, 110] in recipe
     → tests asserts 6 OR 110, recipe declares 3, 4, 6, OR 110

ACTION: git blame + manual inspection:
  - "5 min" / "4 new" / "14 scopes" / sub-agent count context
  - Recipe-author must decide which is canonical (test OR recipe)
  - Update the wrong one to match

## DIREKTIVE 4: RE-RUN + VERIFY CLEAN

After DIREKTIVE 1+2+3, re-run standalone:

  cd tools && python3 -m dev_spec_invariant --repo-root ..

Expected: 0 BLOCKER + 0 HARDCODE-STALE findings. Context-dependent
counters sind als comments dokumentiert (DUE_TO, NOT_STALE).

## SCOPE

recipe/instructions/sub_mas-bootstrap.md (4x)
recipe/instructions/sub_mas-generic-init.md (1x)
recipe/instructions/sub_mas-system-knowledge.md (4x, +1 research)
recipe/instructions/sub_mas-team-packager.md (1x)
recipe/instructions/sub_mas-config-auditor.md (3x, +1 research)
recipe/instructions/sub_mas-mas-controller.md (1x, +1 research)
recipe/instructions/sub_mas-im-finder.md (1x, research)
recipe/instructions/sub_mas-pre-push-validator.md (1x, research)
tests/test_*.py (DIREKTIVE 3: fix INVARIANT BLOCKER)
recipe/sub/*.yaml (DIREKTIVE 3: fix INVARIANT BLOCKER)
.directives/STATUS.md (PHASE 3a = DONE, R110-118+119)

## PRE-CONDITIONS

- f4277fc (R110-118) auf origin/cleanup
- pytest 1284/1284 PASS
- cost 24h: < $20 budget (R36 archive ggf. noetig)
- dev_spec_invariant standalone: 4 BLOCKER + 19 HARDCODE

## ACCEPTANCE

- 0 BLOCKER + 0 simple-stale HARDCODE (dev_spec_invariant clean)
- context-dependent counters: dokumentiert mit comments
  (DUE_TO, NOT_STALE)
- pytest 1284+0=1284 PASS (keine tests broken)
- alle 9 sub_mas-recipes die im-finder recipe registered sind
  noch in registry (test_recipe_registry_consistency 9/9 PASS)
- .directives/STATUS.md PHASE 3a = DONE
- 0 secrets, R04-block ehrlich dokumentiert
- 0 commits amend (R110-24 non-breaking)

## 3 HOOK POINTS

1. PRE-APPLY: pre-apply hook
2. POST-APPLY: post-apply hook (pytest + scan)
3. ERROR: rollback via git checkout (R36 if changes archive
   failed)

## IDEMPOTENZ

pre-apply 2nd returns `ok=false, reason=already applied`.

## TESTING (end-to-end via R110-117 dispatch)

```bash
# 0. R36 unlock
[archive today's entries]

# 1. pre-apply (fresh)
rm -f .state/directive_already_applied.json
python3 tools/dev_directive_applier.py --hook pre-apply \
  .directives/R110-119-hardcode-invariant-fix.md

# 2. apply via R110-117 dispatch
set -a; . ./.env; set +a
export RECURSION_OVERRIDE=2
export MAS_TASK=DIRECTIVE_APPLY
export MAS_CONFIRM=yes
export MAS_APPROVE=y
echo "per directive .directives/R110-119-hardcode-invariant-fix.md apply DIREKTIVE 1+2+3+4: fix simple-stale hardcode + research context-dependent + fix INVARIANT blockers + re-run. ack" | \
  timeout 600 goose run --with-builtin developer \
  --recipe recipe/sub/sub_mas-general-improver.yaml --no-session \
  > /tmp/r110119-improver.log 2>&1

# 3. verify
cd tools && python3 -m dev_spec_invariant --repo-root ..
# Expected: 0 BLOCKER + 0 simple-stale HARDCODE
# Context-dependent als comments dokumentiert (skip-findings)

# 4. pytest still PASS
cd .. && python3 -m pytest tests/ -q
# Expected: 1284/1284 PASS

# 5. post-apply
python3 tools/dev_directive_applier.py --hook post-apply \
  .directives/R110-119-hardcode-invariant-fix.md
```

## ANTI-PATTERNS

- NICHT blind context-dependent counters aendern (R02 lesson)
- NICHT amend f4277fc (R110-118)
- NICHT skip dev_spec_invariant re-run (DIREKTIVE 4 mandatory)
- NICHT skip git blame research (R02 lesson)
- NICHT update recipe-author's intent ohne research
