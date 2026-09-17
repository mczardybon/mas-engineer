# R110-120 — wire sub_mas-self-audit as PHASE 0.5 STEP 0.6 in im-finder (PHASE 3b R110-78)

## CONTEXT (R110-78 PHASE 3b closure)

R110-118 (f4277fc) + R110-119 (0d3317f) implementierten
sub_mas-self-audit (recipe + dev_self_audit.py + dev_spec_invariant.py
+ Check 18 test). R110-119 hat 4 BLOCKER + 24 HARDCODE findings gefixt.

R110-78 PHASE 3a = DONE (tool exists, standalone-invokable, can find
drift). **PHASE 3b = OPEN**: sub_mas-self-audit ist NICHT in der
improvement-pipeline auto-invoked. Detection-aktivierend fehlt.

R110-120 wired sub_mas-self-audit in im-finder als **STEP 0.6** (zwischen
STEP 0.5 goose-consult und STEP 0.7 write findings.yaml). So laeuft es
AENDLICH auto-matisch jedes mal wenn improvement-pipeline triggert.

## DIREKTIVE 1: ADD STEP 0.6 in sub_mas-im-finder.md

Insert NEW STEP 0.6 zwischen STEP 0.5b (L169 im-finder) und
STEP 0.7 (L82). Struktur:

```markdown
## ⛔ STEP 0.6 — SELF-AUDIT SPEC-DRIFT CHECK (NEW IN R110-120)

**🚨 THIS IS NOT OPTIONAL. sub_mas-self-audit runs BEFORE writing
findings.yaml. R110-78 PHASE 3b. 🚨**

After STEP 0.5 (goose-consult) and 0.5b (im-designer liaison), BEFORE
STEP 0.7 (write findings.yaml), I run sub_mas-self-audit to catch
spec-drift findings that the scanner does NOT detect.

**Why this is mandatory:**
- The scanner detects YAML structure issues (MM1-9) but NOT stale
  count literals in recipe-instructions (e.g. "96 sub-agents" when
  the actual count is 112 — R110-71/R110-78 lesson).
- Without STEP 0.6, the im-finder can MISS a whole class of drift
  that the pre-push validator (Check 18) would later block.
- This is a CIRCULAR-PROOF gate: every improvement-pipeline run
  ALSO scans the recipes for drift, not just runs the user-prompted
  improvement.

**EXECUTE:**

```python
# 1. Run self-audit
shell(cmd="cd {workspace} && python3 tools/dev_self_audit.py --scope recipe/instructions/ --repo-root {workspace} --output {workspace}/.mase/pipeline/self_audit.yaml")
shell(cmd="cd {workspace} && python3 tools/dev_spec_invariant.py --repo-root {workspace} --output {workspace}/.mase/pipeline/spec_invariant.yaml")

# 2. Read both outputs
import yaml
sa = yaml.safe_load(open('{workspace}/.mase/pipeline/self_audit.yaml'))
si = yaml.safe_load(open('{workspace}/.mase/pipeline/spec_invariant.yaml'))

# 3. Convert findings to MM9-EXTENSION entries
mm9_ext = []
for finding in sa.get('findings', []):
    if finding.get('severity') in ('BLOCKER',):
        # BLOCKER → fail-fast STOP, do NOT write findings.yaml
        print(f"FATAL: self-audit BLOCKER: {finding['file']}:{finding.get('line','?')} - {finding.get('description','')}")
        raise SystemExit(1)
    if finding.get('type','').startswith('HARDCODE') or finding.get('type','').startswith('INVARIANT'):
        mm9_ext.append({
            'id': f"MM9-EXT-{len(mm9_ext)+1:03d}",
            'type': 'MM9-EXT',
            'subtype': finding.get('type', 'UNKNOWN'),
            'severity': finding.get('severity', 'WARN'),
            'file': finding.get('file', ''),
            'line': finding.get('line', 0),
            'issue': finding.get('description', '')[:200],
            'fix': finding.get('suggested_fix', ''),
            'source': 'sub_mas-self-audit',
            'pipeline_stage': 0.6
        })

# 4. Attach to findings list BEFORE STEP 0.7
findings.extend(mm9_ext)
print(f"STEP 0.6 ATTACHED: {len(mm9_ext)} MM9-EXT findings (total findings now: {len(findings)})")
```

**R01 BYPASS FOR self-audit output:**
- self_audit.yaml + spec_invariant.yaml are the agent's own output,
  same as findings.yaml (R01 lesson L82-95).

**After this step:**
- Proceed to STEP 0.7 (write findings.yaml) with the augmented
  findings list.
- If a BLOCKER was found, the agent STOPS — do NOT write findings.yaml.
- If 0 findings → proceed silently (no MM9-EXT attachments).

**Why MM9-EXT (not MM9):**
- MM9 is the existing type for "YAML field missing". We use MM9-EXT
  to signal an extension type (spec-drift in instruction text, not
  YAML structure).
- This preserves backward compat with the 53 Feature-Type matrix.
- The scanner does not detect MM9-EXT; only sub_mas-self-audit does.
- See also: `recipe/instructions/sub_mas-self-audit.md` Pattern A/B/C.
```

## DIREKTIVE 2: UPDATE sub_mas-im-finder.yaml sub_recipes

Add sub_mas-self-audit to sub_recipes list:

```yaml
sub_recipes:
  - name: sub_mas-goose-expert
    path: ./sub_mas-goose-expert.yaml
    description: "R11 mandatory consultation for goose-related finding types"
  - name: sub_mas-im-designer
    path: ./sub_mas-im-designer.yaml
    description: "R110-78 PHASE 3b: design validation for spec-drift fixes"
  - name: sub_mas-self-audit
    path: ./sub_mas-self-audit.yaml
    description: "R110-78 PHASE 3b: spec-drift detector (Pattern A/B/C: hardcodes, stale literals, count-assertion mismatch)"
```

NOTE: im-designer is referenced in STEP 0.5b but NOT in sub_recipes
list — that's a pre-existing issue (R110-120 PARTIAL fix, just
self-audit). Follow-up R110-121.

## DIREKTIVE 3: UPDATE test_sub_mas_im_finder.py with STEP 0.6 test

Add 1 test (or extend existing pipeline-test):

```python
def test_step_0_6_self_audit_attaches_mm9_ext():
    """R110-120: STEP 0.6 wires sub_mas-self-audit as MM9-EXT findings."""
    # 1. Run self-audit
    import yaml
    from tools.dev_self_audit import run_self_audit
    from pathlib import Path
    result = run_self_audit(
        scope=Path('recipe/instructions/'),
        repo_root=Path('.')
    )
    # 2. Verify findings list is non-empty
    assert len(result.findings) > 0, "self-audit should find drift"
    # 3. Verify all are WARN (not BLOCKER, since R110-119 fixed them)
    severities = {f.severity for f in result.findings}
    assert 'BLOCKER' not in severities, \
        f"BLOCKER found after R110-119: {severities}"
    # 4. Verify types are HARDCODE-*/INVARIANT-*
    types = {f.type for f in result.findings}
    assert any(t.startswith('HARDCODE') for t in types)
    assert any(t.startswith('INVARIANT') for t in types)
```

## DIREKTIVE 4: RE-RUN + VERIFY (R110-116 transparency)

After DIREKTIVE 1+2+3:

  1. dev_spec_invariant: 0 BLOCKER, 0 simple-stale HARDCODE
     (must be unchanged from R110-119)
  2. dev_self_audit: 17 WARN (canonical/context-dependent, both
     documented)
  3. pytest 1284+1=1285 PASS (1 new STEP 0.6 test)
  4. test_recipe_registry_consistency: 9/9 PASS (sub_mas-self-audit
     in im-finder sub_recipes list)
  5. self-audit RECURSIVELY: after R110-120 applied, run
     sub_mas-self-audit again — should find 0 NEW findings
     (drift is now caught by im-finder pipeline too)
  6. R36 cost: archive today's entries if > $20 budget

## SCOPE

  - recipe/instructions/sub_mas-im-finder.md (insert STEP 0.6,
    ~80 lines between STEP 0.5b and STEP 0.7)
  - recipe/sub/sub_mas-im-finder.yaml (add sub_mas-self-audit
    to sub_recipes list)
  - tests/test_sub_mas_im_finder.py (add test_step_0_6)
  - .mase/directives/STATUS.md (PHASE 3b R110-78 = DONE entry)
  - .mase/directive_already_applied.json (auto-updated by
    dispatch)

## PRE-CONDITIONS

  - 0d3317f (R110-119) auf origin/cleanup ✓
  - pytest 1284/1284 PASS ✓
  - dev_spec_invariant: 0 BLOCKER ✓
  - dev_self_audit: 17 WARN (documented) ✓
  - cost 24h: < $20 budget (R36 unlock ggf.)

## ACCEPTANCE

  - sub_mas-im-finder.md hat STEP 0.6 block (~80 lines, MANDATORY
    mark, EXECUTE-block with 4 sub-steps)
  - sub_mas-im-finder.yaml hat sub_mas-self-audit in sub_recipes
    list (3 entries total: goose-expert + im-designer + self-audit)
  - 1 new test test_step_0_6_self_audit_attaches_mm9_ext PASS
  - pytest 1284+1=1285 PASS
  - dev_spec_invariant: 0 BLOCKER (unchanged)
  - 0 secrets
  - R04-block honest (e.g. wenn STEP 0.6 text 90 lines nicht 80)
  - R110-78 PHASE 3b = DONE in STATUS.md
  - 0 amend (R110-24 non-breaking)
  - dispatched via R110-117 mechanism (per-directive trigger)

## 3 HOOK POINTS

1. PRE-APPLY: pre-apply hook (R36 unlock if needed)
2. POST-APPLY: post-apply hook (pytest + scan + registry check)
3. ERROR: rollback via git checkout (R36 if changes archive failed)

## IDEMPOTENZ

pre-apply 2nd returns `ok=false, reason=already applied`.

## TESTING (end-to-end via R110-117 dispatch)

```bash
# 0. R36 unlock (if cost-gate)
[archive today's entries if cost > $20]

# 1. pre-apply (fresh)
rm -f .mase/directive_already_applied.json
python3 tools/dev_directive_applier.py --hook pre-apply \
  .mase/directives/R110-120-im-finder-step-0-6.md

# 2. apply via R110-117 dispatch
set -a; . ./.env; set +a
export RECURSION_OVERRIDE=2
export MAS_TASK=DIRECTIVE_APPLY
export MAS_CONFIRM=yes
export MAS_APPROVE=y
echo "per directive .mase/directives/R110-120-im-finder-step-0-6.md apply DIREKTIVE 1+2+3+4: insert STEP 0.6 in im-finder.md (sub_mas-self-audit pre-write), add sub_mas-self-audit to im-finder.yaml sub_recipes, add STEP 0.6 test, verify clean. ack" | \
  timeout 600 goose run --with-builtin developer \
  --recipe recipe/sub/sub_mas-general-improver.yaml --no-session \
  > /tmp/r110120-improver.log 2>&1

# 3. verify
cd tools && python3 -m dev_spec_invariant --repo-root ..
# Expected: 0 BLOCKER (unchanged)
python3 -m dev_self_audit --scope ../recipe/instructions --repo-root ..
# Expected: 17 WARN (unchanged, all documented)
cd .. && python3 -m pytest tests/ -q
# Expected: 1284+1=1285 PASS
python3 -m pytest tests/test_recipe_registry_consistency.py -q
# Expected: 9/9 PASS

# 4. post-apply
python3 tools/dev_directive_applier.py --hook post-apply \
  .mase/directives/R110-120-im-finder-step-0-6.md
```

## ANTI-PATTERNS

- NICHT STEP 0.6 nach STEP 0.7 einfuegen (R02: order matters —
  spec-drift muss VOR findings-write gefangen werden)
- NICHT MM9-EXT als MM9 missbrauchen (R02: type-system hat
  historische bedeutung, neue subtype via -EXT suffix)
- NICHT R01 gate for self_audit.yaml/spec_invariant.yaml output
  files (same R01 BYPASS as findings.yaml)
- NICHT skip BLOCKER fail-fast (R02: BLOCKER findings sind die
  raison d'etre von sub_mas-self-audit; silent skip = same drift
  as pre-R110-78)
- NICHT amend 0d3317f (R110-119)
- NICHT update sub_mas-im-designer in same commit (R110-121
  follow-up, separate directive)
- NICHT modify dev_self_audit.py / dev_spec_invariant.py CLI
  (siehe R110-119, sie sind stable)
