# MAS Communication Flow

## MAS → Sub-Agents (internal)
DEV-MAS-ENGINEER
  ├── delegate() → sub_mas-goose-expert
  ├── delegate() → sub_mas-framework-scanner
  ├── delegate() → sub_mas-yaml-editor
  ├── delegate() → ... (36 Sub-Agents available)
  │
  ├── shell → tools/dev_*.py (43 tools directly)
  ├── shell → git (commits + Checkpoints)
  ├── shell → .state/changes.json (Documentation)
  └── apps → Dashboard App (live data)

RULE: Sub-Agent = ONLY analysis. Execute shell yourself.

## framework (internal)
FRAMEWORK-STARTER (User-Interface)
  └── delegates TO → PLANNER (Master Orchestrator)
       └── delegates TO → EXECUTOR (Dispatch-Orchestrator)
            ├── dispatches TO → 47 Specialists (via specialist_intake)
            ├── delegates TO → sub_dispatcher
            └── delegates TO → sub_orchestrator, sub_worktree-manager, ...

PLANNER delegates to:
  sub_session-init, sub_interpreter, sub_mode-selector,
  sub_agent-selector, sub_plan-validator, sub_analyst-* (21),
  sub_summarizer, sub_status-tracker

FRAMEWORK-CONTROLLER (continuous operation, all-knowing)
  delegates to: sub_fw-monitor-health, -comms, -memory,
  -runtime, -session, -recovery

## Signals (YAML Envelope, machine-readable)
EVERY signal has required fields: request_id, from, to, signal

| Signal | From → To | Purpose |
|:-------|:---------|:------|
| starter_handover | starter → planner | User-Input + Context |
| planner_plan_ready | planner → executor | Finished EXECUTION_PLAN |
| specialist_intake | executor → specialist | Task-Dispatch |
| specialist_result | specialist → executor | Success |
| specialist_error | specialist → executor | Error |
| specialist_handover | specialist → executor | Handover |
| executor_status | executor → planner | Progress (10 signals) |
| executor_error | executor → planner | Error |
| executor_escalation | executor → planner | P0-Finding |
| executor_summary | executor → planner | Final report |

## Request-ID Requirement
Every structured answer has a request_id (UUID).
Specialists give only back: specialist_result, specialist_error, specialist_handover.

## Communication Principle
- YAML-structured (machine-readable, no free text)
- No mixed outputs (YAML block = one message)
- Size: max 50KB per YAML (split if larger)
- Encoding: UTF-8
