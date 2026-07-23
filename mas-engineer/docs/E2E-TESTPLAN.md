# MAS-ENGINEER E2E-TESTPLAN v1.0

**Ziel:** Jederzeit wiederholbar. Alle Funktionen, Schalter, Modi abdecken. Echte runs (kein wrapper).
Jede KI kann diesen Plan ausfuehren.

**Stand:** 2026-07-23
**Workspace:** `/workspace/mas-engineer-src/mas-engineer`
**Repo:** `github.com/mczardybon/mas-engineer`

---

## 0. VORBEDINGUNGEN (one-time, idempotent)

### 0.1 Environment
```bash
export PATH=/root/.local/bin:/usr/bin:/bin
export DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY:?set DEEPSEEK_API_KEY env var}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-$DEEPSEEK_API_KEY}"
export OPENAI_HOST="https://api.deepseek.com"
export GOOSE_MODEL="deepseek-v4-flash"
export GOOSE_PROVIDER="openai"
export NO_COLOR=1
export MAS_WORKSPACE="/workspace/mas-engineer-src/mas-engineer"
```

### 0.2 Goose PATH-Bug vermeiden
Memory: `goose: command not found` wenn von Hermes-shell. Fix:
`PATH=$PATH:$(dirname $(which goose))` — vor jedem goose-call.

### 0.3 Workspace-Cleanliness-Gate
```bash
du -sh .state/                                            # muss <2M sein
find .state/ -type f | wc -l                              # muss <100 sein
test -d e2e-results/ && echo "FAIL: e2e-results existiert" || echo "OK"
test -d .state/workflow_runs/ && echo "FAIL: workflow_runs" || echo "OK"
test -d .state/pipeline/backups/ && echo "FAIL: pipeline/backups" || echo "OK"
```

### 0.4 Budget-Check
```bash
python3 -c "
import json, datetime
d = json.load(open('.state/changes.json'))
cutoff = datetime.datetime.now() - datetime.timedelta(hours=24)
recent = [e for e in d.get('entries',[]) if 'timestamp' in e and e['timestamp'] > cutoff.isoformat()]
full = [e for e in recent if e.get('type') == 'full_improvement_override']
print(f'recent 24h: {len(recent)}, full: {len(full)}, budget left: {5-len(full)}')
"
```
Bei `budget left = 0` → entweder `RECURSION_OVERRIDE=2` setzen oder warten.

---

## 1. TEST-KATEGORIEN (7 Stueck)

| # | Kategorie | Testet | Tools/Recipes | Modi/Schalter |
|---|-----------|--------|---------------|---------------|
| 1 | Sanity / Smoke | goose funktioniert, alle recipes laden | alle 88 | default |
| 2 | Sub-Recipe Direkt | jedes sub-recipe alleine laeuft | 52 sub_mas-* | --no-session, --with-builtin developer |
| 3 | Tool-Layer | jedes tool-skript python-importiert und --help | 50 tools | unit-argparse |
| 4 | Im-Pipeline Phasen | FIND/RANK/DESIGN/VALIDATE/APPLY isoliert | im-finder..general-improver | RECURSION_OVERRIDE=1,2 |
| 5 | Modi + Schalter | RECURSION_OVERRIDE, MAS_TASK, MAS_CONFIRM, MAS_APPROVE, override_mode, temperature, max_steps | general-improver | alle env-vars + params |
| 6 | Composition (dev-mas-engineer) | haupt-recipe + alle sub_recipes als composition | dev-mas-engineer | pty-interactive + sub_delegates |
| 7 | Rule-Checker / Pre-Push | alle regel-tools + R01-R20 enforcement | dev_rule_checker*, dev_goose_expert_check | alle actions |

---

## 2. PHASE 1: SANITY (5 tests, 60s)

### Test 1.1 — goose selbst erreichbar
```bash
PATH=$PATH:$(dirname $(which goose)) goose --version
```
**Pass:** exit 0, version string

### Test 1.2 — alle recipes YAML-valid (88 files)
```bash
for r in $(find recipe/ -name "*.yaml" -not -path "*/legacy/*" -not -path "*/template/*" -not -path "*/.backups/*"); do
  python3 -c "import yaml,sys; yaml.safe_load(open('$r'))" 2>&1 || echo "FAIL: $r"
done
```
**Pass:** 0 failures

### Test 1.3 — alle recipes ladbar via goose
```bash
for r in $(find recipe/ -name "*.yaml" -not -path "*/legacy/*" -not -path "*/template/*" -not -path "*/.backups/*" -not -name "root_recipe.yaml"); do
  PATH=$PATH:$(dirname $(which goose)) goose run --recipe $r --explain 2>&1 | grep -q "Loading recipe" || echo "FAIL: $r"
done
```
**Pass:** alle 87 recipes "Loading recipe" output

### Test 1.4 — alle python-tools importierbar (50)
```bash
for t in tools/*.py; do
  python3 -c "import importlib.util; s=importlib.util.spec_from_file_location('m','$t'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)" 2>&1 | grep -v "DeprecationWarning" | head -3 || echo "FAIL: $t"
done
```
**Pass:** 0 fails

### Test 1.5 — alle tools haben --help
```bash
for t in tools/*.py; do
  python3 $t --help >/dev/null 2>&1 || echo "FAIL: $t"
done
```
**Pass:** 0 fails

---

## 3. PHASE 2: SUB-RECIPE DIREKT (52 tests, ~15 min)

Fuer jedes sub-recipe in `recipe/sub/sub_mas-*.yaml`:

```bash
RECIPE=recipe/sub/sub_mas-<name>.yaml
OUT=/tmp/e2e-results/sub_$(basename $RECIPE .yaml)_$(date +%s)
mkdir -p $OUT

cd $MAS_WORKSPACE
PATH=$PATH:$(dirname $(which goose)) \
DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY \
OPENAI_API_KEY=$OPENAI_API_KEY \
OPENAI_HOST=$OPENAI_HOST \
GOOSE_MODEL=deepseek-v4-flash \
GOOSE_PROVIDER=openai \
NO_COLOR=1 \
MAS_WORKSPACE=$MAS_WORKSPACE \
goose run --with-builtin developer \
  --recipe $RECIPE \
  --params "workspace=$MAS_WORKSPACE" \
  --no-session \
  > $OUT/log.txt 2>&1
EXIT=$?

if [ $EXIT -ne 0 ]; then echo "FAIL $RECIPE exit=$EXIT"; fi
grep -qE "Loading recipe|SUCCESS|DONE|completed" $OUT/log.txt || echo "FAIL $RECIPE no success marker"
grep -qE "delegate\(|summon" $OUT/log.txt || echo "WARN $RECIPE no delegation"
```

**Pass-Kriterium pro sub-recipe:**
- exit code 0
- log enthaelt "Loading recipe" ODER spezifischen success-marker
- log enthaelt delegation/sub-recipe-call (nicht nur echo der prompt)

**Liste (52 sub_mas-* + 4 weitere):**
```
sub_mas-agent-guardian        sub_mas-im-finder
sub_mas-bootstrap             sub_mas-im-rank
sub_mas-code-reviewer-director  sub_mas-im-session-reader
sub_mas-code-reviewer-reporter sub_mas-im-validator
sub_mas-code-reviewer-synthesizer  sub_mas-intention-parser
sub_mas-code-reviewer-validator sub_mas-interpreter
sub_mas-config-auditor        sub_mas-json-utility
sub_mas-content-writer        sub_mas-mas-controller
sub_mas-dashboard-refresh     sub_mas-master-constitution
sub_mas-degradation-handler   sub_mas-migration-helper
sub_mas-demo-runner           sub_mas-monitor-health
sub_mas-doc-generator         sub_mas-monitor-recovery
sub_mas-doc-writer            sub_mas-monitor-runtime
sub_mas-email-campaign-manager sub_mas-monitor-session
sub_mas-framework-knowledge   sub_mas-pre-push-validator
sub_mas-framework-scanner     sub_mas-prompt-engineer
sub_mas-general-improver      sub_mas-python-repair
sub_mas-generic-init          sub_mas-recipe-designer
sub_mas-git-operator          sub_mas-recipe-manager
sub_mas-goose-admin           sub_mas-recovery-checkpoint
sub_mas-goose-expert          sub_mas-recovery-defib
sub_mas-health-reporter       sub_mas-recovery-immune
sub_mas-im-designer           sub_mas-recovery-safezone
                              sub_mas-recovery-timeline
                              sub_mas-self-auditor
                              sub_mas-session-analyst
                              sub_mas-signal-generator
                              sub_mas-social-media-manager
                              sub_mas-summarizer
                              sub_mas-team-packager
                              sub_mas-test-runner
                              sub_mas-unix-test-runner
                              sub_mas-verification-runner
                              sub_mas-web-researcher
                              sub_mas-workflow-engine
                              sub_mas-worktree-manager
                              sub_mas-yaml-editor
```

---

## 4. PHASE 3: TOOL-LAYER UNIT (50 tests, 120s)

```python
import importlib.util, subprocess, sys, os
tools = [f for f in os.listdir('tools') if f.endswith('.py')]
results = []
for t in tools:
    name = t[:-3]
    try:
        spec = importlib.util.spec_from_file_location(name, f'tools/{t}')
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        import_ok = True
    except Exception as e:
        import_ok = False
    r = subprocess.run([sys.executable, f'tools/{t}', '--help'],
                      capture_output=True, text=True, timeout=10)
    help_ok = r.returncode in (0, 2)
    results.append((name, import_ok, help_ok))
    print(f"{name}: import={import_ok} help={help_ok}")
fail = [n for n,i,h in results if not (i and h)]
print(f"FAIL: {fail if fail else 'none'}")
```

---

## 5. PHASE 4: IM-PIPELINE PHASEN (5 tests, ~12 min)

### 5.1 FIND isoliert
```bash
echo "ack" | PATH=$PATH:$(dirname $(which goose)) \
DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY OPENAI_API_KEY=$OPENAI_API_KEY OPENAI_HOST=$OPENAI_HOST \
GOOSE_MODEL=deepseek-v4-flash GOOSE_PROVIDER=openai NO_COLOR=1 MAS_WORKSPACE=$MAS_WORKSPACE \
goose run --with-builtin developer \
  --recipe recipe/sub/sub_mas-im-finder.yaml \
  --params "workspace=$MAS_WORKSPACE,scan_scope=recipe/" \
  --no-session
```
**Pass:** exit 0, `.state/pipeline/findings.yaml` updated, size > 50KB

### 5.2 RANK isoliert
```bash
echo "ack" | goose run --with-builtin developer \
  --recipe recipe/sub/sub_mas-im-rank.yaml --no-session
```
**Pass:** `.state/pipeline/ranked_findings.yaml` updated, valid yaml, enthaelt ≥1 finding mit priority

### 5.3 DESIGN isoliert
```bash
echo "ack" | goose run --with-builtin developer \
  --recipe recipe/sub/sub_mas-im-designer.yaml --no-session
```
**Pass:** `.state/pipeline/patches.yaml` mit ≥1 patch (file, field, from, to, reason)

### 5.4 VALIDATE isoliert
```bash
echo "ack" | goose run --with-builtin developer \
  --recipe recipe/sub/sub_mas-im-validator.yaml --no-session
```
**Pass:** `.state/pipeline/validation.yaml` mit CONFORM/VIOLATION verdict

### 5.5 APPLY (general-improver) isoliert
```bash
RECURSION_OVERRIDE=1 \
MAS_TASK=APPLY_ONLY MAS_CONFIRM=yes MAS_APPROVE=y \
goose run --with-builtin developer \
  --recipe recipe/sub/sub_mas-general-improver.yaml \
  --params "task=APPLY_ONLY,confirm=yes,approve=y" \
  --no-session
```
**Pass:** exit 0, `.state/pipeline/apply.yaml` updated, applied_patches zeigt echte file-modifications

---

## 6. PHASE 5: MODI + SCHALTER (8 tests, ~20 min)

**Critical env-vars/params (alle aus IM-007 spec):**

| Schalter | Wert | Test |
|----------|------|------|
| `RECURSION_OVERRIDE=1` | APPLY_ONLY bypass | general-improver 5.5 |
| `RECURSION_OVERRIDE=2` | FULL pipeline bypass 24h-cooldown | full run mit skip-cooldown |
| `MAS_TASK=FULL_IMPROVEMENT` | trigger full pipeline | general-improver mit task= |
| `MAS_TASK=REVIEW` | review ohne apply | general-improver |
| `MAS_TASK=COST_ANALYSIS` | cost report | general-improver |
| `MAS_CONFIRM=yes` | R01 bypass | R01 sollte nicht triggern |
| `MAS_APPROVE=y` | R4.5 bypass | approval sollte nicht triggern |
| `override_mode=full` | alle 5 phasen erzwingen | wie RECURSION_OVERRIDE=2 |
| `temperature=0.3` | deterministisch | sub-recipe mit temperature-setting |
| `max_steps=300` | step-limit | dev-mas-engineer mit custom |
| `--no-session` | 1-frage modus | IM-005 fix |
| `--with-builtin developer` | file-write capability | alle file-edit recipes |
| `--params workspace=...` | workspace injection | IM-005 fix |
| `SCAN_SCOPE=...` | scan-scope fuer im-finder | sub_mas-im-finder mit scope |

### Test 5.1 — R01 confirmation-bypass
```bash
echo "no-confirm" | goose run --recipe recipe/sub/sub_mas-general-improver.yaml \
  --params "task=APPLY_ONLY,confirm=no" --no-session 2>&1 | grep -q "Are you sure" && echo "FAIL: R01 not bypassed" || echo "PASS"
```

### Test 5.2 — RECURSION_OVERRIDE=2 bypass 24h-cooldown
```bash
RECURSION_OVERRIDE=2 goose run --recipe recipe/sub/sub_mas-general-improver.yaml \
  --params "task=FULL_IMPROVEMENT" --no-session 2>&1 | grep -q "RECURSION_GUARD" && echo "FAIL" || echo "PASS"
```

### Tests 5.3-5.8 — alle weiteren env-vars analog

---

## 7. PHASE 6: COMPOSITION (1 langer test, ~30 min)

### Test 6.1 — dev-mas-engineer.yaml als interaktive PTY-session
```bash
cd $MAS_WORKSPACE
timeout 1800 goose run --recipe recipe/dev-mas-engineer.yaml --name e2e-dev-mas-composition 2>&1 | tee /tmp/e2e-results/dev-mas-composition.log
```

**Operator-Script (in PTY, antwortet wie ein Mensch):**
1. Erstes prompt: "Was kannst du?" → erwartet: capabilities-listing
2. "Liste alle 52 sub-agents" → erwartet: vollstaendige sub_recipes-liste
3. "delegate framework-scanner" → erwartet: framework-scanner delegation
4. "delegate general-improver mit task=FULL_IMPROVEMENT" → erwartet: im-pipeline triggert
5. Bei R01-prompt: submit "yes" oder "no"
6. Bei R4.5-prompt: submit "y" oder "n"

**Pass:** alle 5 antworten sinnvoll, sub-delegations sichtbar im log, exit 0

### Test 6.2 — full interactive mas-session mit allen rules
```bash
RECURSION_OVERRIDE=2 MAS_TASK=FULL_IMPROVEMENT MAS_CONFIRM=yes MAS_APPROVE=y \
MAS_WEB_RESEARCH=no \
goose run --recipe recipe/dev-mas-engineer.yaml --interactive
# operator beantwortet menu: "FULL_IMPROVEMENT" → "yes" → "y"
```

**Pass:** mas laeuft alle 5 im-phasen, commited, pushed, log in /tmp/e2e-results/

---

## 8. PHASE 7: RULE-CHECKER + PRE-PUSH (5 tests, 30s)

### 7.1 Alle actions durch rule_checker
```bash
ACTIONS=("SI-RUN start" "PATCH-DESIGN" "PATCH-VALIDATE" "PATCH-APPLY" "GIT-COMMIT" "GIT-PUSH" "RECURSION-RESET" "AUDIT-LOG" "TELEGRAM-SEND" "DELEGATE")
for a in "${ACTIONS[@]}"; do
  python3 tools/dev_rule_checker.py --all --action "$a" 2>&1 | grep -qE "approved|denied" || echo "FAIL: action=$a"
done
```

### 7.2 R13 enforcement (kein edit von /root/.config/goose/recipes/)
```bash
python3 tools/dev_recursion_override.py --action edit --file /root/.config/goose/recipes/translator/translator-team.yaml 2>&1 | grep -q "R13" && echo "PASS: R13 enforced" || echo "FAIL"
```

### 7.3 R01 enforcement
```bash
echo "" | goose run --recipe recipe/sub/sub_mas-general-improver.yaml --no-session 2>&1 | grep -q "R01" && echo "PASS" || echo "FAIL"
```

### 7.4 Pre-push validator
```bash
python3 tools/dev_goose_expert_check.py --commit HEAD 2>&1 | tee /tmp/e2e-results/pre-push.log
grep -qE "PASS|FAIL" /tmp/e2e-results/pre-push.log && echo "PASS" || echo "FAIL"
```

### 7.5 Self-auditor
```bash
goose run --with-builtin developer --recipe recipe/sub/sub_mas-self-auditor.yaml --params "workspace=$MAS_WORKSPACE" --no-session 2>&1 | tee /tmp/e2e-results/self-audit.log
```

---

## 9. AGGREGATION + REPORT (1 test, 30s)

```bash
python3 -c "
import json, os, glob, datetime
phases = {
    '1_sanity': glob.glob('/tmp/e2e-results/sanity_*.log'),
    '2_sub_recipes': glob.glob('/tmp/e2e-results/sub_*.log'),
    '3_tools': glob.glob('/tmp/e2e-results/tool_*.log'),
    '4_pipeline': glob.glob('/tmp/e2e-results/pipeline_*.log'),
    '5_switches': glob.glob('/tmp/e2e-results/switch_*.log'),
    '6_composition': glob.glob('/tmp/e2e-results/dev-mas-*.log'),
    '7_rules': glob.glob('/tmp/e2e-results/rule_*.log'),
}
report = {'timestamp': datetime.datetime.now().isoformat(), 'phases': {}}
total_pass = total_fail = 0
for p, files in phases.items():
    pf = sum(1 for f in files if 'PASS' in open(f).read())
    ff = sum(1 for f in files if 'FAIL' in open(f).read())
    report['phases'][p] = {'pass': pf, 'fail': ff, 'files': len(files)}
    total_pass += pf
    total_fail += ff
report['total_pass'] = total_pass
report['total_fail'] = total_fail
report['pass_rate'] = f'{100*total_pass/(total_pass+total_fail):.1f}%' if (total_pass+total_fail) else 'N/A'
json.dump(report, open('/tmp/e2e-results/REPORT.json', 'w'), indent=2)
print(json.dumps(report, indent=2))
"
```

**Pass-Kriterium gesamt:** ≥90% pass-rate, 0 critical fails (rule-enforcement, pre-push, im-pipeline)

---

## 10. ROLLBACK + IDEMPOTENZ (2 tests)

### 10.1 Test ist idempotent
```bash
bash test-e2e-full.sh > /tmp/e2e-results/run1.log 2>&1
bash test-e2e-full.sh > /tmp/e2e-results/run2.log 2>&1
diff <(grep -E "PASS|FAIL" /tmp/e2e-results/run1.log) <(grep -E "PASS|FAIL" /tmp/e2e-results/run2.log) > /dev/null && echo "IDEMPOTENT" || echo "DIFFERENT — investigate"
```

### 10.2 Cleanup nach test
```bash
rm -rf /tmp/e2e-results/test-*
rm -f .state/pipeline/test_*
test "$(du -sm .state | cut -f1)" -lt 3 && echo "OK workspace zurueck"
```

---

## 11. ZEITPLAN

| Phase | Tests | Dauer | Parallelisierbar |
|-------|-------|-------|------------------|
| 0 Vorbereitung | 4 | 30s | nein |
| 1 Sanity | 5 | 60s | nein |
| 2 Sub-Recipes | 52 | 15 min | ja (4 parallel) |
| 3 Tools | 50 | 120s | ja (10 parallel) |
| 4 Pipeline | 5 | 12 min | nein (sequenziell) |
| 5 Modi | 8 | 20 min | ja (4 parallel) |
| 6 Composition | 2 | 30 min | nein |
| 7 Rules | 5 | 30s | nein |
| 9 Aggregation | 1 | 30s | nein |
| 10 Rollback | 2 | 30s | nein |
| **TOTAL** | **134** | **~80 min** | |

---

## 12. FAILED-TEST HANDLING

Bei fail:
1. **Sofort stop** — keine weiteren phasen starten
2. **Log sichern** — `cp /tmp/e2e-results/<test>.log /tmp/e2e-results/FAILED_<test>_<timestamp>.log`
3. **Diagnose** — operator liest log, identifiziert: bug in mas, falscher test, env-problem
4. **Re-run** — single test isoliert, dann ggf. ganze phase
5. **Skip** — nur bei EXTERNEN bugs (R13: /root/.config/goose/recipes/*), mit dokumentation
6. **Report** — am ende: PASS_RATE, LISTE_ALLER_FAILS, EMPFEHLUNG

---

## 13. PARAMETRIERBARKEIT

Test-skript akzeptiert:
```bash
bash test-e2e-full.sh --skip 6 --budget 2 --only pipeline
```
- `--skip <phase>` — phasen ueberspringen
- `--budget <n>` — mas-runs-budget fuer phase 4+6
- `--only <phase>` — nur diese phase
- `--parallel <n>` — parallelitaet fuer phase 2/3/5
- `--strict` — bei 1 fail sofort abbruch
- `--no-push` — phase 6 ohne git push
- `--workspace <path>` — anderes workspace testen

---

## 14. INTEGRATION IN MAS-SELBST

Phase 4+5+6 testen mas's self-improvement. Nach erfolgreichem e2e:
- mas-engineer committed die test-infrastruktur
- test-e2e-full.sh wird zu recipe/sub/sub_mas-e2e-runner.yaml
- weekly cron prueft health

---

**Plan fertig. 134 tests, ~80 min, idempotent, alle schalter modi funktionen.**

**Jede KI kann diesen Plan ausfuehren:**
1. Environment setzen (Phase 0)
2. Phasen 1-7 sequenziell laufen lassen
3. Aggregation (Phase 9) lesen
4. Failed-tests behandeln (Phase 12)
5. Optional: rollback / cleanup (Phase 10)
