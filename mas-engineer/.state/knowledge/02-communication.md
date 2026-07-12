# MAS-Kommunikationsfluss

## MAS → Sub-Agenten (intern)
DEV-MAS-ENGINEER 
  ├── delegate() → sub_mas-goose-expert
  ├── delegate() → sub_mas-framework-scanner
  ├── delegate() → sub_mas-yaml-editor
  ├── delegate() → ... (36 Sub-Agenten available)
  │
  ├── shell → tools/dev_*.py (43 Tools direkt)
  ├── shell → git (commits + Checkpoints)
  ├── shell → .state/changes.json (Documentation)
  └── apps → Dashboard-App (Live-Data)

REGEL: Sub-Agent = NUR Analyse. Shell selbst ausexecuten.

## framework (intern)
FRAMEWORK-STARTER (User-Interface)
  └── delegiert AN → PLANNER (Master Orchestrator)
       └── delegiert AN → EXECUTOR (Dispatch-Orchestrator)
            ├── dispatcht AN → 47 Specialists (via specialist_intake)
            ├── delegiert AN → sub_dispatcher
            └── delegiert AN → sub_orchestrator, sub_worktree-manager, ...

PLANNER delegiert an:
  sub_session-init, sub_interpreter, sub_mode-selector,
  sub_agent-selector, sub_plan-validator, sub_analyst-* (21),
  sub_summarizer, sub_status-tracker

FRAMEWORK-CONTROLLER (Dauerbetrieb, allwissend)
  delegiert an: sub_fw-monitor-health, -comms, -memory,
  -runtime, -session, -recovery

## Signale (YAML-Envelope, maschinenlesbar)
JEDES Signal has required fields: request_id, from, to, signal

| Signal | Von → An | Zweck |
|:-------|:---------|:------|
| starter_handover | starter → planner | User-Input + Context |
| planner_plan_ready | planner → executor | Fertiger EXECUTION_PLAN |
| specialist_intake | executor → specialist | Task-Dispatch |
| specialist_result | specialist → executor | Success |
| specialist_error | specialist → executor | Error |
| specialist_handover | specialist → executor | Aboutgabe |
| executor_status | executor → planner | Fortstep (10 Signale) |
| executor_error | executor → planner | Error |
| executor_escalation | executor → planner | P0-Finding |
| executor_summary | executor → planner | Abschlussbericht |

## Request-ID-Pflicht
Jede strukturierte Antwort has eine request_id (UUID).
Spezialistn geben only back: specialist_result, specialist_error, specialist_handover.

## Kommunikationsprinzip
- YAML-strukturiert (maschinenlesbar, no Freitext)
- No gemischten Outputs (YAML-Block = eine Message)
- Size: max 50KB pro YAML (sizere splitten)
- Encoding: UTF-8
