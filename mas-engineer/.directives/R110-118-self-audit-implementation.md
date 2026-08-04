# R110-118 — sub_mas-self-audit + dev_spec_invariant.py (R110-109 DIREKTIVE 1+2+3 implementation)

## CONTEXT (R110-78 PHASE 3 closure)

R110-109 (commit bbc76ca, 2026-08-04) was SPEC-ONLY: 238-line spec
defining 3 DIREKTIVE blocks for PHASE 3 of R110-78 spec-drift lesson.
R110-109 DIREKTIVE 1+2+3 wurden noch nicht implementiert.

R110-115 (b00dade) baute **sub_mas-apply-directive** (anderer agent,
operator-directive-driven). R110-116 (dac9e1f) fixte body-bugs. R110-117
(690f39e) wired RECURSION-GUARD v3 (C) end-to-end dispatch.

R110-118 implementiert R110-109 DIREKTIVE 1+2+3:
  1. NEUER SUB-AGENT sub_mas-self-audit (DIREKTIVE 1)
  2. tools/dev_spec_invariant.py (DIREKTIVE 2)
  3. TEST-COUNT-INVARIANT FIX (DIREKTIVE 3, Check 18 in pre-push)

Nach R110-118 ist R110-78 PHASE 3 = DONE. PHASE 1 (R110-94/R110-100)
+ PHASE 2 (R110-106) + PHASE 3 (R110-118) = all closed.

## DIREKTIVE 1: SUB_MAS-SELF-AUDIT AGENT

Erstelle 3 files:

  1. `recipe/sub/sub_mas-self-audit.yaml`
     Schema: gleiche YAML-struktur wie sub_mas-im-finder.yaml.
     Description: "v1.0.0 | MAS-internal: Self-Audit audits recipe-
     instructions auf hardcodes, stale literals, spec-drift (R110-78
     PHASE 3, R110-109 DIREKTIVE 1)".
     sub_recipes: NONE (self-detect muss recursive sein).
     prompt: "I am self-audit (v1.0.0) | ROLE: PHASE 0.5 audit
     agent | SCOPE: recipe/instructions/ | DETECT: Pattern A
     (hardcoded zahlen ohne env-var context), Pattern B (stale
     literal vs tools/files), Pattern C (recipe-instructions die
     zahlen assertieren die nicht mit --collect-count match).
     EXCLUDE: sub_mas-self-audit.md (selbst-referenz). OUTPUT:
     .state/pipeline/self_audit.yaml"
     EXECUTE-block: shell(cmd="cd {workspace} && python3 -m
       dev_self_audit --scope=recipe/instructions/
       --output {workspace}/.state/pipeline/self_audit.yaml")
     blocks: 1 STEP (audit + emit findings).

  2. `recipe/instructions/sub_mas-self-audit.md`
     3-4 absaetze: scope, detection-patterns, output-format.
     3 hook points: PRE-AUDIT (skip if .state/pipeline/self_audit.
     yaml exists + fresh < 1h), POST-AUDIT (return count), ERROR
     (log to .state/self_audit_failures.json).

  3. `tools/dev_self_audit.py`
     Standalone-script, importierbar als modul. API:
       def run_self_audit(scope: Path, repo_root: Path) -> SelfAuditResult
       class SelfAuditResult:
           def to_findings(self) -> list[Finding]
     CLI: `python3 -m dev_self_audit --scope <dir> --repo-root <path>`
          exit 0 wenn clean, 1 sonst.
     Pattern A: hardcoded `\d{2,}\s+(sub-agents|tools|phases|checks)`
       ohne IM_TOP_N/${...}/default\s+\d context.
     Pattern B: stale literal (gleiche logic wie check_spec_drift,
       NUR fuer recipe/instructions/).
     Pattern C: count-assertion die nicht mit --collect-count match
       (delegation an dev_spec_invariant).

## DIREKTIVE 2: TOOLS/DEV_SPEC_INVARIANT.PY

Erstelle `tools/dev_spec_invariant.py` (~200 lines).

  API:
    def run_spec_invariant_check(repo_root: Path) -> SpecInvariantResult
    class SpecInvariantResult:
        def to_findings(self) -> list[Finding]
  CLI: `python3 -m dev_spec_invariant --repo-root <path>`
       exit 0 wenn alle invariants match, 1 sonst.

  Extract-functions:
    a) extract_count_assertions_from_tests(tests_dir):
       Regex: COUNT_ASSERT_RE = re.compile(
                r'''assert\s+["'](\d+)\s+(\w[\w-]*)["']\s+in\s+''')
       TYPE_MIN_LEN = 2
       TYPE_BLACKLIST = {"tests", "files", "lines", "args",
                         "items", "keys", "values", "chars"}
       Returns: dict[type, set[count]] z.B. {"sub-agents": {110}}
    b) extract_count_from_recipes(recipe_dir):
       Regex: r'(\d+)\s+(\w[\w-]*)' auf recipe/sub/*.yaml
       Skip in: comments, multiline-strings, valid_yaml
       Returns: dict[type, set[count]]

  Invariant-check:
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

## DIREKTIVE 3: CHECK 18 (PRE-PUSH-VALIDATOR)

Update `tools/dev_pre_push_validator.py` (oder das recipe equivalent):
  + Check 18: spec-invariant (nach Check 17 pytest-run).
  Naming-update analog R110-99 wenn zwischen-zeitlich Check 17+
  hinzukommt.

  Idempotenz: skip wenn recipe/sub/sub_mas-pre-push-validator
  schon check_18_spec_invariant enthaelt (grep-detect).

  Test: `tests/test_pre_push_check_18_spec_invariant.py`
        3 test-cases: (a) match passes, (b) mismatch emits BLOCKER
        finding, (c) recipe/sub/*.yaml excluded wenn leer.

## SCOPE

recipe/sub/sub_mas-self-audit.yaml (NEW)
recipe/instructions/sub_mas-self-audit.md (NEW)
tools/dev_self_audit.py (NEW)
tools/dev_spec_invariant.py (NEW)
tools/dev_pre_push_validator.py (MODIFIED, Check 18 add)
recipe/sub/sub_mas-pre-push-validator.yaml (MODIFIED, Check 18
  reference) — falls noetig
tests/test_pre_push_check_18_spec_invariant.py (NEW)
.state/workflows.yaml (MODIFIED, +sub_mas-self-audit in registry)
.directives/STATUS.md (MODIFIED, PHASE 3 → DONE)

## PRE-CONDITIONS

- b00dade (R110-115), dac9e1f (R110-116), 690f39e (R110-117) auf
  origin/cleanup
- pytest 1281/1281 PASS (verifiziert in R110-117)
- cost 24h: < $20 budget (R36 archive ggf. noetig)
- RECURSION_OVERRIDE=2 + per-directive dispatch verified in R110-117

## ACCEPTANCE

- 6 neue files + 1 modified recipe + 1 modified state file
- sub_mas-self-audit in DOMAIN 1 mas-self.sub_agents.improvement
  registry (test_mas_self_recipes_registered PASS)
- Check 18 spec-invariant test PASS (3 test-cases)
- pytest 1281+3 = 1284/1284 PASS
- scanner 21 findings (no regression, no new SD)
- 0 secrets im diff
- R110-78 PHASE 3 = DONE in STATUS.md

## 3 HOOK POINTS

1. PRE-APPLY: `python3 tools/dev_directive_applier.py --hook pre-apply \
   .directives/R110-118-self-audit-implementation.md`
2. POST-APPLY: pytest + scan + Check 18 spec-invariant
3. ERROR: rollback files via git checkout

## IDEMPOTENZ

pre-apply 2nd returns `ok=false, reason=already applied`.

## TESTING (end-to-end)

```bash
# 0. R36 unlock (falls counter >= 5)
[archive today's entries to .state/changes.archive-DATE.json]

# 1. pre-apply (fresh, R110-118 not yet applied)
rm -f .state/directive_already_applied.json
python3 tools/dev_directive_applier.py --hook pre-apply \
  .directives/R110-118-self-audit-implementation.md
# Expected: ok=true

# 2. apply via R110-117 dispatch mechanism
set -a; . ./.env; set +a
export RECURSION_OVERRIDE=2
export MAS_TASK=DIRECTIVE_APPLY
export MAS_CONFIRM=yes
export MAS_APPROVE=y
echo "per directive .directives/R110-118-self-audit-implementation.md apply DIREKTIVE 1+2+3: create sub_mas-self-audit agent + dev_spec_invariant.py + dev_self_audit.py + Check 18 + status update. ack" | \
  timeout 600 goose run --with-builtin developer \
  --recipe recipe/sub/sub_mas-general-improver.yaml --no-session \
  > /tmp/r110118-improver.log 2>&1

# 3. verify dispatch + apply
test -f .state/test_apply_directive_dispatch.log && echo "DISPATCH OK"
test -f recipe/sub/sub_mas-self-audit.yaml && echo "DIREKTIVE 1 OK"
test -f tools/dev_spec_invariant.py && echo "DIREKTIVE 2 OK"
test -f tools/dev_self_audit.py && echo "DIREKTIVE 1.4 OK"

# 4. post-apply
python3 tools/dev_directive_applier.py --hook post-apply \
  .directives/R110-118-self-audit-implementation.md
# Expected: ok=true, pytest_ok=true, scan_ok=true

# 5. verify Check 18 test
python3 -m pytest tests/test_pre_push_check_18_spec_invariant.py -v
# Expected: 3 passed

# 6. final pytest
python3 -m pytest tests/ -q
# Expected: 1284/1284 PASS
```

## ANTI-PATTERNS

- NICHT amend b00dade/dac9e1f/690f39e (R110-24 non-breaking)
- NICHT R36 skip (counter ist invariant)
- NICHT skip dev_spec_invariant.py (DIREKTIVE 2 mandatory)
- NICHT skip test file (DIREKTIVE 3 mandatory)
- NICHT skip registry update (test_mas_self_recipes_registered
  enforced)
