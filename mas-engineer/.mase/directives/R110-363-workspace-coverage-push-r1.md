---
sprint: R110-363
topic: workspace.py coverage r1 — small wins on remaining 109 stmts (82% → 88-92%)
status: planned
---

# R110-363 — workspace.py coverage r1: small wins on remaining 109 stmts

## Goal

Push `tools/dev_workspace.py` coverage from **82% to 88-92%** with
15-20 NEW tests targeting the remaining 109 uncovered stmts.

## Reality check (vs R110-323 inventory)

- R110-323 inventory claim: "0% / 1445 stmts" — **WRONG**
- Actual: 82% / 599 executable stmts (1482 raw lines, 60% are comments/blank)
- Source of error: inventory was measured when `dev_workspace` was
  not yet importable as canonical name (R110-129/311 fix landed
  later). The "0%" was the "module was never imported" warning,
  not real coverage.
- Prior coverage-push history: R110-266, R110-269, R110-300, R110-309,
  R110-324, R110-351, R110-353, R110-355, R110-357 — 9 R-sprints
  already pushed workspace to 82% before R110-363.

## What's left (109 uncovered stmts in 14 ranges)

| Range | What | Testable? |
|-------|------|-----------|
| L504-528 | `_install_mas_from_workspace` (file copy helper) | ✅ yes — tmp_path + assert file copied |
| L847-848 | `print(f"❌ Template not found")` (early-return branch) | ✅ yes — patch `MAS_TEMPLATE.exists` to False |
| L862-864 | `fw_specialist` branch of `_generate_agent` | ✅ yes — call with `agent_type="fw_specialist"` |
| L940-941 | `sub_<name>.yaml` default branch | ✅ yes — call with unknown agent_type |
| L950, 954-960 | `input("Overwrite?")` interactive flow | ✅ yes — monkeypatch `input` to return `"j"` |
| L1113 | `cmd_install_check` early-return (ws_dir missing) | ✅ yes — call with `ws_dir=""` |
| L1310-1342 | `cmd_scaffold` interactive flow (asks 5 questions) | ✅ yes — monkeypatch `_ask_*` helpers + `input` |
| L1369 | `cmd_install_check` returns 1 when no manifest | ✅ yes — patch `manifest_path.exists` to False |
| L1386 | `cmd_install_check` happy-path | ✅ yes — full tmp_path setup |
| L1397 | `cmd_install_check` other-CLI-mode dispatch | ✅ yes — patch `MAS_ENGINEER_BIN` env var |
| L1419-1477 | `if __name__ == "__main__"` CLI dispatcher | ❌ NO — would need to fork+exec the file |

## Target

- 15-20 NEW tests
- Coverage: 82% → 88-92% (+6-10pp)
- Wall-clock: <5s (subprocess tests excluded — use direct calls)
- The L1419-1477 `__main__` block is NOT testable here — its 58 stmts
  will remain uncovered. That's documented as a known gap.

## Why not aim for 100%

- `cmd_install_mas` (L529-545) is marked `# pragma: no cover`
  (R110-266: deferred, touches real GOOSE paths — see comment in source)
- `if __name__ == "__main__"` (L1419-1477) needs fork+exec
- Interactive `input()` calls in `cmd_scaffold` (L950) need full
  monkeypatching — but the R110-324-BUG-A fix made the flow
  complex enough that a 1-test monkeypatch chain is the wrong
  granularity for a r1 push.

90% is a realistic cap. The remaining 10% requires a separate
"interactive-CLI-testing" R-sprint.

## Files (planned)

- `mas-engineer/tests/test_r110363_workspace_coverage_push_r1.py`
  (NEW, ~350 lines, 15-20 tests, 4 TestXxx classes)

## Constraints

- DO NOT touch the existing 196 workspace tests
- DO NOT add `# pragma: no cover` markers to the `__main__` block
  (R110-266 pattern — keep it honest, leave it uncovered)
- DO NOT change `dev_workspace.py` source (this is a test-only push)

## Verification

```bash
# Should PASS in <5s
python3 -m pytest tests/test_r110363_workspace_coverage_push_r1.py \
  -p no:cacheprovider --no-header -q --timeout=30

# Coverage delta
python3 -m pytest tests/test_r110363_workspace_coverage_push_r1.py \
  tests/test_r110266_workspace.py tests/test_r110269_workspace_part2.py \
  tests/test_r110300_workspace_library.py tests/test_r110309_workspace_lib.py \
  tests/test_r110324_workspace_bug_fixes.py tests/test_r110351_workspace_coverage_push_r1.py \
  tests/test_r110353_workspace_coverage_push_r2.py tests/test_r110355_workspace_coverage_push_r3.py \
  tests/test_r110357_workspace_coverage_push_r4.py \
  -p no:cacheprovider --no-header -q --timeout=30 \
  --cov=tools --cov-report=term 2>&1 | grep dev_workspace.py
# Expected: 88-92% (vs current 82%)
```

## Refs

- R110-351/353/355/357 — last 4 R-sprints that pushed workspace
  (R110-363 follows the same TestXxx-class structure)
- R110-323 (inventory — but the 0% claim was wrong, see reality check)
- R110-361/362 — coverage-push r1 + pre-existing-test-fix for
  im_finder_scan (the +56pp overshoot is the model for being
  conservative on the target)
- Skill: mas-engineer-coverage-push-workflow
