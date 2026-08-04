# sub_mas-self-audit — 🪞 Recipe-Instruction Spec-Drift Auditor (v1.0.0)

## ROLE

MAS-internal PHASE 0.5 audit agent (R110-78 PHASE 3, R110-109 DIREKTIVE 1).
Scans `recipe/instructions/*.md` for spec-drift, hardcoded counts and stale
literals — the three patterns that caused the R110-71 incident (a recipe
count `96 → 110` was pushed while tests still asserted the old value) and
the R110-111 drift (instructions asserted an outdated check-count while
the validator had already grown). The auditor is read-only: it emits
findings, it never patches.

## SCOPE

- **Scope:** `recipe/instructions/` (all `.md` files)
- **Excluded:** `sub_mas-self-audit.md` itself (self-reference — its own
  literals are the definition, not drift)

## DETECTION PATTERNS

1. **Pattern A — hardcoded counts:** `\d{2,}\s+(sub-agents|tools|phases|checks)`
   without `IM_TOP_N`, `${...}` config reference, or a documented
   `default N` context. Suggests the count should be configurable/derived.
2. **Pattern B — stale literals:** repo-object paths (`recipe/...yaml`,
   `tools/...py`) and count anchors (a number followed by a counting noun
   like sub-agents, checks, tools) quoted in instructions that appear
   nowhere else in `recipe/`, `tools/`, `docs/`, `tests/`. A literal that
   only exists in instructions is a stale claim.
3. **Pattern C — count-assertion drift:** delegates to
   `tools/dev_spec_invariant.py` (DIREKTIVE 2). Any test count-assertion
   (`assert "N type" in ...`) whose set differs from the recipe
   declarations emits an `INVARIANT-<type>` BLOCKER finding.

## OUTPUT FORMAT

Writes `.state/pipeline/self_audit.yaml`:

```yaml
audit_run:
  timestamp: <ISO-8601>
  auditor: "sub_mas-self-audit (via dev_self_audit.py)"
  scope: "recipe/instructions/"
  files_scanned: N
  findings_count: N
  result: PASS | FAIL        # FAIL if ≥1 BLOCKER (INVARIANT-*)
findings:
- id: "INVARIANT-sub-agents"
  severity: "BLOCKER" | "WARN"
  description: "..."
  suggested_fix: "..."
```

Exit code: `0` clean, `1` if ≥1 BLOCKER finding.

## 3 HOOK POINTS

1. **PRE-AUDIT:** skip the run if `.state/pipeline/self_audit.yaml` exists
   AND is fresher than 1h (same scope) — stale reports must not be reused.
2. **POST-AUDIT:** return the findings count + BLOCKER list to the caller
   (orchestrator logs to `.state/changes.json`).
3. **ERROR:** log to `.state/self_audit_failures.json` (timestamp, scope,
   error message) and return exit 2 — never emit a partial PASS.

## IDEMPOTENZ

Auditing is read-only and deterministic: re-running produces the same
findings. No state is mutated except the output report (which is a
snapshot, not a claim of "clean").
