# MAS-Kommunikationsfluss

## MAS → Sub-Agenten (intern)
DEV-MAS-ENGINEER 
  ├── delegate() → sub_mas-goose-expert
  ├── delegate() → sub_mas-framework-scanner
  ├── delegate() → sub_mas-yaml-editor
  ├── delegate() → ... (36 Sub-Agenten verfuegbar)
  │
  ├── shell → tools/dev_*.py (43 Tools direkt)
  ├── shell → git (Commits + Checkpoints)
  ├── shell → .state/changes.json (Dokumentation)
  └── apps → Dashboard-App (Live-Daten)

REGEL: Sub-Agent = NUR Analyse. Shell selbst ausfuehren.

## Framework (intern)
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
JEDES Signal hat Pflichtfelder: request_id, from, to, signal

| Signal | Von → An | Zweck |
|:-------|:---------|:------|
| starter_handover | starter → planner | User-Input + Kontext |
| planner_plan_ready | planner → executor | Fertiger EXECUTION_PLAN |
| specialist_intake | executor → specialist | Task-Dispatch |
| specialist_result | specialist → executor | Erfolg |
| specialist_error | specialist → executor | Fehler |
| specialist_handover | specialist → executor | Uebergabe |
| executor_status | executor → planner | Fortschritt (10 Signale) |
| executor_error | executor → planner | Fehler |
| executor_escalation | executor → planner | P0-Finding |
| executor_summary | executor → planner | Abschlussbericht |

## Request-ID-Pflicht
Jede strukturierte Antwort hat eine request_id (UUID).
Spezialisten geben nur zurueck: specialist_result, specialist_error, specialist_handover.

## Kommunikationsprinzip
- YAML-strukturiert (maschinenlesbar, kein Freitext)
- Keine gemischten Outputs (YAML-Block = eine Nachricht)
- Groesse: max 50KB pro YAML (groessere splitten)
- Encoding: UTF-8
