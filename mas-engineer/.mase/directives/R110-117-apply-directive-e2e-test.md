# R110-117 — end-to-end test: sub_mas-apply-directive autonomous dispatch

## CONTEXT

R110-115 implementierte sub_mas-apply-directive + RECURSION-GUARD v3.
R110-116 dokumentierte die 3 bugs + re-label.
R110-117 verifiziert dass das ganze system **autonomous end-to-end**
funktioniert: operator sagt "per directive X" → general-improver
dispatched zu sub_mas-apply-directive → directive wird angewendet.

## DIREKTIVE 1: ADD sub_mas-apply-directive to general-improver sub_recipes

**Bug (R110-117 entdeckt):** RECURSION-GUARD v3 sagt "DELEGATE to
sub_mas-apply-directive" aber sub_mas-apply-directive war NICHT in
der `sub_recipes:` list von general-improver. Goose kann nur zu
declared sub_recipes delegieren.

**Fix (manuell, R110-117):**

`recipe/sub/sub_mas-general-improver.yaml`:

    sub_recipes:
      ...
      - name: sub_mas-self-auditor
        path: ./sub_mas-self-auditor.yaml
        description: "Self-audit before commit"
    + - name: sub_mas-apply-directive
    +   path: ./sub_mas-apply-directive.yaml
    +   description: "R110-113: applies operator-written .mase/directives/ specs"
      - name: sub_mas-generic-init

## DIREKTIVE 2: CREATE test-dispatch log file via sub_mas-apply-directive

End-to-end test: sub_mas-apply-directive soll autonomous eine
datei erstellen die beweist dass der dispatch-mechanismus
funktioniert.

**Action:** Erstelle `.mase/test_apply_directive_dispatch.log` mit
inhalt:

    [YYYY-MM-DD HH:MM:SS UTC] sub_mas-apply-directive dispatched.
    Source: R110-117 directive
    Action: created test-dispatch log file
    Recipe: recipe/sub/sub_mas-apply-directive.yaml
    Trigger: RECURSION-GUARD v3 (C) + RECURSION_OVERRIDE=2

**Verification:** File existiert, content enthaelt timestamp + source.

## SCOPE

`recipe/sub/sub_mas-general-improver.yaml` (1 line added)
`tools/dev_directive_applier.py` (--apply command re-test)
`.mase/test_apply_directive_dispatch.log` (created by apply)

## PRE-CONDITIONS

- b00dade (R110-115) und dac9e1f (R110-116) auf origin/cleanup
- pytest 1281/1281 PASS
- cost 24h: < $20 budget (R36 archive ggf. noetig)
- sub_mas-apply-directive recipe existiert
- general-improver RECURSION-GUARD v3 active

## ACCEPTANCE

- File `.mase/test_apply_directive_dispatch.log` existiert
- Content enthaelt timestamp + source + action
- pytest 1281/1281 PASS nach dispatch
- general-improver log zeigt "DELEGATE to sub_mas-apply-directive"
- .mase/changes.json entry: stage=apply_only, via=apply_directive
- kein "RECURSION-GUARD v2 → v3" was-overwritten (immutable)

## 3 HOOK POINTS

1. PRE-APPLY: `python3 tools/dev_directive_applier.py --hook pre-apply \
   .mase/directives/R110-117-apply-directive-e2e-test.md`
2. POST-APPLY: pytest + scan, write .mase/directive_already_applied.json
3. ERROR: rollback sub_recipes add (if dispatch failed)

## IDEMPOTENZ

`pre-apply` 2nd-run returns `ok=false` (getestet in R110-115/116).

## TESTING (end-to-end)

```bash
# 0. Archive today entries (R36 unlock, falls counter >= 5)
python3 -c "import json; from datetime import datetime, timezone; \
  p='.mase/changes.json'; d=json.load(open(p)) if __import__('os').path.exists(p) else []; \
  today=datetime.now(timezone.utc).strftime('%Y-%m-%d'); \
  td=[e for e in d if e.get('timestamp','').startswith(today)]; \
  ar={'metadata':{'archived_at':datetime.now(timezone.utc).isoformat(),\
    'reason':'R36 unlock for R110-117 e2e test','entry_count':len(td)},\
    'changes':td}; \
  open(f'.mase/changes.archive-{today}.json','w').write(json.dumps(ar,indent=2)+chr(10)); \
  d=[e for e in d if not e.get('timestamp','').startswith(today)]; \
  open(p,'w').write(json.dumps(d,indent=2)+chr(10)); print(f'archived {len(td)} entries')"

# 1. pre-apply
python3 tools/dev_directive_applier.py --hook pre-apply \
  .mase/directives/R110-117-apply-directive-e2e-test.md
# Expected: ok=true

# 2. apply via sub_mas-apply-directive
set -a; . ./.env; set +a
export PATH=$PATH:/root/.local/bin
export GOOSE_SESSION_TAG="[r110-117-e2e-apply-directive]"
export RECURSION_OVERRIDE=2
export MAS_TASK=apply
export MAS_CONFIRM=yes
export MAS_APPROVE=y
echo "per directive .mase/directives/R110-117-apply-directive-e2e-test.md apply" | \
  timeout 300 goose run --with-builtin developer \
  --recipe recipe/sub/sub_mas-general-improver.yaml --no-session \
  > /tmp/r110117-improver.log 2>&1

# 3. verify dispatch log created
test -f .mase/test_apply_directive_dispatch.log && \
  echo "DISPATCH SUCCESS" || echo "DISPATCH FAILED"
cat .mase/test_apply_directive_dispatch.log

# 4. post-apply
python3 tools/dev_directive_applier.py --hook post-apply \
  .mase/directives/R110-117-apply-directive-e2e-test.md

# 5. pytest still 1281 PASS
python3 -m pytest tests/ -q 2>&1 | tail -2
```

## ANTI-PATTERNS

- NICHT amend b00dade/dac9e1f (R110-24 non-breaking)
- NICHT skip sub_recipes add (Bug-fix DIREKTIVE 1 mandatory)
- NICHT use RECURSION_OVERRIDE=1 (operator-mode = 2)
- NICHT skip mas_cost check (cost-limit blocks if exceeded)
