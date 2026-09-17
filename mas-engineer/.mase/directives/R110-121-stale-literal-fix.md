# R110-121 — fix STALE-LITERAL findings: sales example → dev-team example (R110-78 PHASE 3c)

## CONTEXT (R110-78 PHASE 3c closure)

R110-120 (4050394) implementierte STEP 0.6 in im-finder. Re-run von
dev_self_audit zeigt 27 WARN, davon 21 HARDCODE (R110-119 documented)
+ 6 NEUE STALE-LITERAL findings (Pattern B R110-118):

  1. recipe/instructions/sub_mas-team-packager.md:375-385: 6x
     'recipe/sub/sub_mas-sales-{director,prospector,proposal,
     pipeline,analyst,crm}.yaml' (die recipes wurden in b9ceac4
     R110-87 "remove test-team artifacts" removed — stale example)
  2. recipe/instructions/sub_mas-im-finder.md:146: 1x
     'recipe/sub/sub_mas-goose-expert.yaml' (FALSE POSITIVE:
     recipe existiert in 9 files, but Pattern B extrahiert nur
     path-like quoted strings, nicht YAML bare references)

Die 2 HOWTO docs (docs/HOWTO-TEAM-STANDALONE.md + docs/HOWTO-
PACKAGE-TEAM.md) referenzieren auch sales-recipes (L9+18+95+96
+ L41+51+52+66-68+79+88). R110-87 hat nur YAML files removed,
nicht die doc references.

R110-78 PHASE 3c = OPEN bis R110-121: STALE-LITERAL Pattern B
findings fixen. Split:

  PHASE 3a (DONE R110-118+119): tool/agent + first-run fixes
  PHASE 3b (DONE R110-120): STEP 0.6 in im-finder pipeline
  PHASE 3c (DONE THIS commit): STALE-LITERAL Pattern B findings
    (6 stale sales-references + Pattern B bug fix for im-finder
    L146 false positive)

## DIREKTIVE 1: REPLACE sales-examples mit dev-team in 3 files

Replace alle 'sub_mas-sales-*' references in:

  A) recipe/instructions/sub_mas-team-packager.md (L375-385,
     6 stale references in root_recipe + sub_recipes):
     Replace 'sub_mas-sales-director.yaml' →
       'sub_mas-dev-director.yaml'
     Replace 'sub_mas-sales-{prospector,proposal,pipeline,analyst,
       crm}.yaml' → 'sub_mas-dev-{analyzer,builder,observer,tester}.
       yaml' (real sub_mas-dev-team files in recipe/sub/)

     BEFORE:
       root_recipe: 'recipe/sub/sub_mas-sales-director.yaml'
       sub_recipes:
         - 'recipe/sub/sub_mas-sales-prospector.yaml'
         - 'recipe/sub/sub_mas-sales-proposal.yaml'
         - 'recipe/sub/sub_mas-sales-pipeline.yaml'
         - 'recipe/sub/sub_mas-sales-analyst.yaml'
         - 'recipe/sub/sub_mas-sales-crm.yaml'

     AFTER:
       root_recipe: 'recipe/sub/sub_mas-dev-director.yaml'
       sub_recipes:
         - 'recipe/sub/sub_mas-dev-analyzer.yaml'
         - 'recipe/sub/sub_mas-dev-builder.yaml'
         - 'recipe/sub/sub_mas-dev-observer.yaml'
         - 'recipe/sub/sub_mas-dev-tester.yaml'

     NOTE: dev-team hat 4 sub_agents (director + 4) statt 6 wie
     sales-team hatte. Update agent_count accordingly
     (L391 `agent_count: 6` → `agent_count: 5` for accuracy).

  B) docs/HOWTO-TEAM-STANDALONE.md (L9+18+95+96+118+152, 6 stale
     references): Replace sales* examples mit dev-team analog.
     Use sub_mas-dev-team as the EXAMPLE team (since it's REAL
     production team in recipe/sub/).

  C) docs/HOWTO-PACKAGE-TEAM.md (L41+51+52+66-68+79+88, 8 stale
     references): Same replacement.

  HINWEIS: Die HOWTO docs sind NICHT in `recipe/`, also NICHT in
  Pattern B scope — sie sind NICHT in self-audit findings. Aber
  R02 lesson: konsistent fixen (nicht in recipe aber verlinkt).

## DIREKTIVE 2: FIX Pattern B bug (R110-121 PART B)

Im-finder.md L146 hat `sub_recipe="recipe/sub/sub_mas-goose-
expert.yaml"` als path-like reference. Pattern B extrahiert das
korrekt als `recipe/sub/sub_mas-goose-expert.yaml`. ABER:
- `sub_mas-goose-expert.yaml` existiert in 9 files
- 8 files referenzieren es als YAML bare name (`name: sub_mas-
  goose-expert`) oder relative path (`./sub_mas-goose-expert.
  yaml`)
- Pattern B zaehlt nur path-like quoted strings, NICHT bare
  names oder relative paths

FIX: In tools/dev_self_audit.py, add new PATTERN_B_YAML_BARE_RE
= re.compile(r'\bname:\s*(sub_mas-[\w-]+)') das YAML `name:`
fields extrahiert. Add to _build_repo_literal_index iteration
loop ABER exclude the file that IS the definition (so sub_mas-
goose-expert.yaml's own `name: sub_mas-goose-expert` field does
not count as a self-reference).

ALSO: Improve _B_PATH_LIKE_RE to recognize relative paths like
`./sub_mas-goose-expert.yaml` (mit `./` prefix).

Pseudocode:
```python
_B_PATH_LIKE_RE = re.compile(
    r'^(?:\./)?[\w./\-]+/[\w./\-]+\.(?:yaml|py|md|json|sh|txt)$')
# Now matches both 'recipe/sub/x.yaml' AND './x.yaml' AND
# 'x.yaml' if combined with subdir.

_B_YAML_BARE_NAME_RE = re.compile(
    r'\bname:\s*(sub_mas-[\w-]+)\b')
# Extracts 'sub_mas-goose-expert' from 'name: sub_mas-goose-
# expert' lines.
```

HINWEIS: This PART B is RISKY — es koennte regressions in
existing tests verursachen. After implement, run ALL tests +
verify dev_self_audit now correctly resolves `sub_mas-goose-
expert.yaml` as "appears in N files" (not 1, not 0).

If regression → REVERT PART B in same commit, document as
"R110-121 PART B deferred to R110-122" (R02 lesson: never
break existing tests, even to fix findings).

## DIREKTIVE 3: UPDATE tests/test_sub_mas_self_auditor.py

Add 1 test for STALE-LITERAL Pattern B:

```python
def test_pattern_b_stale_literal_detected():
    """R110-121: Pattern B detects stale references."""
    from tools.dev_self_audit import run_self_audit
    from pathlib import Path
    result = run_self_audit(
        scope=Path('recipe/instructions/'),
        repo_root=Path('.')
    )
    stale_findings = [f for f in result.findings
                      if 'STALE-LITERAL' in f.type]
    # After R110-121 DIREKTIVE 1: should be 0 stale
    # (sales replaced, im-finder false positive fixed)
    assert len(stale_findings) == 0, \
        f"Stale findings remain: {[f.file+':'+str(f.line) for f in stale_findings]}"
```

## DIREKTIVE 4: RE-RUN + VERIFY (R110-116 transparency)

After DIREKTIVE 1+2+3:

  1. dev_self_audit: 21 HARDCODE WARN (unchanged from R110-119
     "27 minus 6 stale = 21") — IF PART B works, plus 0
     STALE-LITERAL. If PART B reverts, 1 STALE-LITERAL (im-
     finder L146 false positive, documented as known).
  2. dev_spec_invariant: 0 BLOCKER (unchanged)
  3. pytest 1285+1=1286 PASS (1 new test)
  4. test_recipe_registry_consistency: 9/9 PASS
  5. grep verify: 0 occurrences of 'sub_mas-sales-*' in
     recipe/instructions/ + docs/
  6. R36 cost: archive today's entries if > $20 budget

## SCOPE

  - recipe/instructions/sub_mas-team-packager.md (L375-385,
    replace 6 sales* with dev-team* + L391 agent_count 6→5)
  - docs/HOWTO-TEAM-STANDALONE.md (L9+18+95+96+118+152, replace
    6 sales* with dev-team*)
  - docs/HOWTO-PACKAGE-TEAM.md (L41+51+52+66-68+79+88, replace
    8 sales* with dev-team*)
  - tools/dev_self_audit.py (DIREKTIVE 2: Pattern B fix)
  - tests/test_sub_mas_self_auditor.py (+1 test)
  - .mase/directives/STATUS.md (R110-121 entry, R110-78 PHASE 3c DONE)

## PRE-CONDITIONS

  - 4050394 (R110-120) auf origin/cleanup ✓
  - pytest 1285/1285 PASS ✓
  - dev_spec_invariant: 0 BLOCKER ✓
  - dev_self_audit: 27 WARN (21 HARDCODE + 6 STALE-LITERAL)
  - cost 24h: < $20 budget (R36 unlock ggf.)

## ACCEPTANCE

  - 0 occurrences of 'sub_mas-sales-*' in recipe/instructions/
    + docs/ (grep verify)
  - sub_mas-dev-* referenced as example in 3 files (consistency)
  - 0 STALE-LITERAL findings IF PART B works; 1 known
    STALE-LITERAL (im-finder L146 false positive) IF PART B
    reverts
  - pytest 1285+1=1286 PASS
  - dev_spec_invariant: 0 BLOCKER (unchanged)
  - 0 secrets
  - R04-block honest (PART B may need revert, document)
  - R110-78 PHASE 3c = DONE in STATUS.md
  - 0 amend (R110-24 non-breaking)
  - dispatched via R110-117 mechanism

## 3 HOOK POINTS

1. PRE-APPLY: pre-apply hook (R36 unlock if needed)
2. POST-APPLY: post-apply hook (pytest + scan + registry check)
3. ERROR: rollback via git checkout (R36 if changes archive
   failed)

## IDEMPOTENZ

pre-apply 2nd returns `ok=false, reason=already applied`.

## TESTING (end-to-end via R110-117 dispatch)

```bash
# 0. R36 unlock (if cost-gate)
[archive today's entries if cost > $20]

# 1. pre-apply (fresh)
rm -f .mase/directive_already_applied.json
python3 tools/dev_directive_applier.py --hook pre-apply \
  .mase/directives/R110-121-stale-literal-fix.md

# 2. apply via R110-117 dispatch
set -a; . ./.env; set +a
export RECURSION_OVERRIDE=2
export MAS_TASK=DIRECTIVE_APPLY
export MAS_CONFIRM=yes
export MAS_APPROVE=y
echo "per directive .mase/directives/R110-121-stale-literal-fix.md apply DIREKTIVE 1+2+3+4: replace sales examples with sub_mas-dev-team in 3 files (team-packager + 2 HOWTO docs), improve dev_self_audit Pattern B for im-finder L146 false positive, add test_pattern_b_stale_literal_detected, verify clean. ack" | \
  timeout 600 goose run --with-builtin developer \
  --recipe recipe/sub/sub_mas-general-improver.yaml --no-session \
  > /tmp/r110121-improver.log 2>&1

# 3. verify
cd tools && python3 -m dev_self_audit --scope ../recipe/instructions --repo-root ..
# Expected: 21 HARDCODE WARN (no STALE-LITERAL IF PART B works)
cd .. && python3 -m pytest tests/ -q
# Expected: 1285+1=1286 PASS
python3 -m pytest tests/test_recipe_registry_consistency.py -q
# Expected: 9/9 PASS

# 4. grep verify
grep -rn "sub_mas-sales" recipe/ docs/
# Expected: 0 results

# 5. post-apply
python3 tools/dev_directive_applier.py --hook post-apply \
  .mase/directives/R110-121-stale-literal-fix.md
```

## ANTI-PATTERNS

- NICHT Pattern B regress other Pattern A or C findings
  (verify after PART B with full pytest + dev_self_audit re-run)
- NICHT skip PART B if it fails first try (R02: investigate
  first, revert if still broken, document as R110-122 follow-up)
- NICHT modify dev_self_audit CLI args (R110-118 API stable)
- NICHT amend 4050394 (R110-120)
- NICHT skip HOWTO docs (R02: konsistent fixen)
- NICHT keep sales example as comment with TODO (R02: replace
  with real example, not leave stale)
