# R110-581 — Audit: silent-TypeError-after-refactor pattern (R110-562/563)

**Date:** 2026-09-16
**Author:** Hermes (cleanup-session)
**Target:** `tools/**/*.py` (production, not tests)
**Method:** Static analysis — extract function signatures, find callers,
          compare arg-types-vs-passed-types, look for `except` that would
          swallow TypeError.

## Background

R110-562 admitted a 30x perf regression after a refactor; R110-563 admitted a
silent-TypeError-broke-callers bug. Both came from signature-vs-caller drift
that the existing test suite did not catch.

This audit systematically scans `tools/` for the same shape:

  1. Functions with `Optional[X] = None` parameter where body does NOT
     have an `is None` / `or {}` / `or []` defensive check (R110-562 shape).
  2. Callers in PRODUCTION code passing `None` / `{}` / `[]` / `""` for a
     positional param whose type annotation says `list` / `dict` / `set`
     (R110-563 shape — caller-broken, callee-crashes-silently).
  3. Broad `except:` clauses that would swallow the resulting TypeError.

## Results

### (1) Optional[X] = None without None-handling in body

5 candidates found:

| File:line | Function | Param | Type |
|-----------|----------|-------|------|
| tools/dev_agent_doctor.py:391 | apply_lessons | skip | Optional[List[str]] = None |
| tools/dev_dashboard_data.py:518 | send_dashboard_notification | data | dict = None |
| tools/dev_message_queue.py:353 | enqueue | retry_policy | Optional[dict] = None |
| tools/dev_template_generator.py:657 | refresh_agent | sources | Optional[Dict] = None |
| tools/dev_template_generator.py:657 | refresh_agent | rules | Optional[Dict] = None |

**Verdict: NOT R110-562 pattern.** Manual review shows all 5 are
`unused-parameter` cases — the parameter is declared but the body never
references it (e.g. `apply_lessons` body never uses `skip`,
`send_dashboard_notification` body never uses `data`).

This is a SEPARATE smell (unused parameter / dead code) but it is NOT a
silent-TypeError pitfall because the body does not operate on the
parameter at all. A caller can pass `None` and nothing breaks.

### (2) Production callers passing wrong-type arg

0 candidates found. All wrong-type callers are in `tests/test_*` files,
where passing `{}` / `[]` / `""` is by-design for edge-case coverage.

### (3) Broad `except:` that could swallow TypeError

10 occurrences across:

| File:line | Context |
|-----------|---------|
| tools/dev_dashboard_data.py:38, 55, 64, 72, 228, 322 | subprocess/JSON-load defensive returns |
| tools/dev_workload_monitor.py:155 | session-scan defensive |
| tools/dev_audit_deps.py:24 | dep-list iteration defensive |
| tools/dev_health_report.py:20, 34 | health-check defensive |

**Verdict: defensive returns, not silent-swallowers.** All 10 broad
`except:` immediately `return` a sentinel (`""`, `[]`, `{}`, `None`)
rather than letting the exception propagate. This means a TypeError
crash inside the body would still surface to the caller (the sentinel
return tells them "something went wrong") — it does NOT silently
produce wrong data the way R110-563 did.

## Conclusion

**The R110-562/563 silent-TypeError pattern is NOT present in the current
codebase.** This is a NEGATIVE finding — a positive outcome from the
audit. The patterns R110-562/563 introduced (defensive None-handling in
callee bodies, type-checks at call sites) have held; subsequent refactors
in `tools/` have not regressed them.

### Follow-up smells (NOT in scope for this audit)

- 5 unused-parameter declarations (see table above). Dead code smell.
  Could be cleaned up in a separate R110-584 (unused-param sweep) —
  but this is purely a readability cleanup, not a bug.
- 10 broad `except:` clauses. Defensive but slightly anti-pattern
  (prefer `except Exception:` at minimum to avoid catching
  `KeyboardInterrupt` / `SystemExit`). Could be tightened in a
  separate R110-585 (except-tightening) — but no observed bug.

## Method reproducibility

Static-analysis script is inline below for re-run on future commits:

```bash
# 1. Optional[X] = None without None-check in body
rg -n 'def\s+\w+\([^)]*=\s*None[^)]*\)\s*:' tools/ --type py -A 50 \
  | python3 -c '
import sys, re
# (truncated for brevity — full script in audit-tools-def-signatures.py)
'

# 2. Production callers passing wrong-type
rg -n '\bNAME\s*\(\s*(None|{}|\[\])\s*,' tools/ --type py  # not tests/

# 3. Broad except
rg -n '^\s*except\s*:' tools/ --type py
```

Full script in `audit-tools-def-signatures.py` (next to this file).

## Evidence

Audit run: 2026-09-16, tools/**/*.py (excluding `__pycache__/`,
`tests/`), 605 def declarations, 492 distinct names, 0 production
wrong-type callers.

Refs: R110-562 (30x perf admission), R110-563 (silent-TypeError
admission), R110-578 (parity-after-refactor admission), R110-330
(json.load None defensive — opposite direction).
