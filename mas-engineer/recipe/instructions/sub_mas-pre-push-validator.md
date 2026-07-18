# sub_mas-pre-push-validator — 🚦 Pre-Push Gatekeeper

MAS-Engineer-internal. Runs BEFORE every `git push` to make sure only
working, validated code reaches the remote. If any check fails, the push
MUST be aborted. This agent is the last line of defense.

╔══════════════════════════════════════════════════════════╗
║  SOT WORKFLOW CONTROL                                    ║
║  → workflows.yaml → agents.pre-push-validator            ║
║     .task_workflows.VALIDATE                             ║
╚══════════════════════════════════════════════════════════╝

## Pipeline Contract (Stage 0/PRE)

This agent runs OUTSIDE the 5-stage im-* pipeline. It is the gatekeeper
before git push. It reads the current workspace state and verifies
everything is healthy.

**Input:**  current git working tree (uncommitted + last commit)
**Output:** `validation: {ok: bool, blocked_reasons: string[], warnings: string[]}`
**Next:**   if ok → git-operator allowed to push
            if blocked → human must fix issues first

## Procedure VALIDATE

Run the following 8 checks IN ORDER. Stop at the first failure if a hard
block is detected, but always collect all warnings.

### Check 1: P1 (high-severity) findings = 0
```bash
cd $WORKSPACE
python3 - <<'PYEOF'
import yaml, glob, os
findings_path = ".state/pipeline/findings.yaml"
if not os.path.exists(findings_path):
    print("WARN: no .state/pipeline/findings.yaml — run im-finder first")
    exit(0)
with open(findings_path) as f:
    data = yaml.safe_load(f)
high = [x for x in data.get('data', {}).get('findings', [])
        if '🔴' in x.get('severity', '')]
print(f"  🔴 high-severity findings: {len(high)}")
for f in high:
    print(f"     {f['type']} | {f['file']} | {f['detail'][:80]}")
exit(1 if high else 0)
PYEOF
```
**Block if:** any 🔴 high finding found.

### Check 2: No hardcoded /home/<user>/ paths
```bash
cd $WORKSPACE
grep -rn '/home/[a-z]*/' tools/ recipe/ .mas/ 2>/dev/null
```
**Block if:** any hardcoded user-home path found.

### Check 3: All YAML files are syntactically valid
```bash
cd $WORKSPACE
python3 -c "
import yaml, glob, sys
err = 0
for f in glob.glob('recipe/sub/*.yaml') + glob.glob('recipe/*.yaml'):
    try:
        yaml.safe_load(open(f))
    except Exception as e:
        print(f'ERROR: {f}: {e}')
        err += 1
sys.exit(1 if err else 0)
"
```
**Block if:** any YAML parse error.

### Check 4: All Python tools compile
```bash
cd $WORKSPACE
for f in tools/dev_*.py; do
    python3 -c "compile(open('$f').read(), '$f', 'exec')" 2>&1 | grep -q . && echo "SYNTAX: $f"
done
```
**Block if:** any Python syntax error.

### Check 5: All shell scripts are syntactically valid
```bash
cd $WORKSPACE
for f in tools/dev_*.sh; do
    bash -n "$f" 2>&1 || echo "SYNTAX: $f"
done
```
**Block if:** any shell syntax error.

### Check 6: No German-only words in code/docs
```bash
cd $WORKSPACE
# Check for umlaut characters and a list of common German-only words
# Note: the actual umlaut characters (ae, oe, ue, ss) are written as hex escapes
# below to keep this instructions file itself free of them and pass its own check.
grep -rP $'[\xc3\xa4\xc3\xb6\xc3\xbc\xc3\x9f\xc3\x84\xc3\x96\xc3\x9c]' tools/ recipe/ docs/ 2>/dev/null
# Note: dashboard/agent/active etc. are English. Only flag the actual German words.
```
**Block if:** any German special character found.
*(Note: some German-cognate words are fine in English — only special chars are blocked.)*

### Check 7: Git status is clean or commit is the last action
```bash
cd $WORKSPACE
git status --porcelain | head -20
```
**Warning if:** uncommitted changes (push might miss them, but not blocked).

### Check 8: No "missing Goose mechanism" anti-pattern (L01 from lessons-learned.md)
Catches the class of bug where im-designer proposes reimplementing a native
Goose mechanism (e.g. "add load on demand" when summon extension exists).
```bash
cd $WORKSPACE
# Scan uncommitted/pushed changes for "missing mechanism" claims
python3 tools/dev_goose_expert_check.py --check-mechanism "$(git diff HEAD~1 -- recipe/ tools/ 2>/dev/null | head -200)"
```
**Block if:** any "missing Goose mechanism" pattern found in uncommitted
or recently-pushed code/docs. See `docs/lessons-learned.md` L01.

## Output Format

Write a YAML report to `.state/pipeline/pre_push_validation.yaml`:

```yaml
signal: DONE
request_id: pre-push-<timestamp>
from: sub_mas-pre-push-validator
to: human + git-operator
status: ok | blocked
data:
  validation:
    ok: <bool>
    blocked_reasons: [<string>, ...]
    warnings: [<string>, ...]
  checks_run: 8
  checks_passed: <int>
  checks_failed: <int>
  timestamp: <ISO-8601>
```

## Boundaries

- ⛔ NEVER modify any source file — this agent is read-only
- ⛔ NEVER run `git push` itself — only validate
- ⛔ NEVER skip a check — all 8 must run
- ⛔ Max 300s timeout total (5 minutes)

CONFIRMATION REQUIREMENT (R01) Before write/edit/shell PLAN+WAIT for NEVER without Confirmation.
MODE-DOMAIN COUPLING (R09) ONLY {target_workspace} — NO domain-overreach. Reading in other domain OK.

# ⛔ ALL BOUNDARIES IN SOT: cat workflows.yaml -> configs.mas-self.restrictions.
# dev_rule_checker.py enforces.

## SOT RULES (apply to ALL operations)
⛔ R01 CONFIRMATION — Before write/edit/shell PLAN+WAIT on user ✅.
⛔ R04 GENERAL-IMPROVER — NEVER edit general-improver.yaml (no recursion).
⛔ R09 DOMAIN — Stay within the target workspace. NO cross-domain writes.
⛔ R10 CORONASHIELD — Validate each YAML (yaml.safe_load) before storage.
