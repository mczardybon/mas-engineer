# MAS-Engineer — Erstanalyse (first_scan)

**Datum:** 2026-06-22  
**Gesamt:** 1037 Dateien  
**Größe:** ~9.5 MB

---

## Architektur-Kern

**DEV-MAS-ENGINEER** (Haupt-Agent) steuert **46 Sub-Agenten** über eine Dispatch-Hierarchie:

| Kategorie | Anzahl | Agenten |
|-----------|--------|---------|
| Analyse | 6 | `framework-knowledge`, `framework-scanner`, `session-analyst`, `config-auditor`, `goose-expert`, `prompt-engineer` |
| Recovery | 5+1 | `recovery-immune`, `recovery-checkpoint`, `recovery-safezone`, `recovery-timeline`, `recovery-defib`, `migration-helper` |
| Monitoring | 6 | `agent-guardian`, `monitor-health`, `monitor-runtime`, `monitor-recovery`, `monitor-session`, `mas-controller` |
| Verwaltung | 8 | `goose-admin`, `recipe-manager`, `yaml-editor`, `worktree-manager`, `verification-runner`, `summarizer`, `interpreter` |
| Self-Improve | 11 | `general-improver`, `im-session-reader`, `im-finder`, `im-rank`, `im-designer`, `im-validator`, `workflow-engine`, `intention-parser`, `doc-generator`, `signal-generator`, `degradation-handler` |
| Generic | 2 | `generic-init`, `master-constitution` |
| Spezial | 7 | `test-runner`, `git-operator`, `python-repair`, `doc-writer`, `json-utility`, `health-reporter`, `recipe-designer` |

---

## Regel-System (Hardening)

**21 Regeln (R01-R21)** mit 5 Härtestufen:

### Extrem (⛔⛔⛔⛔⛔ — blockierend)
- **R01** Confirmation requirement vor write/edit/shell
- **R02** Bestand vor Neubau
- **R04** Niemals general-improver.yaml editieren
- **R05** Auto-Commit nach Change (git+checkpoint+changes.json)
- **R09** Domain-Trennung (MAS ≠ Framework)
- **R10** Coronashield — YAML-Validierung vor Speicherung
- **R11** SI-Rate-Limit — max 1 General-Improver alle 6h
- **R12** MAS unabhängig von work/
- **R13** Neues Projekt ignoriert MAS-Konfiguration
- **R14** work_on-Modus (mas | projekt)
- **R15** Architektur-Changes brauchen User-Genehmigung
- **R18** Delegationspflicht — niemals selbst wenn Sub-Agent existiert
- **R19** Pfad-Hierarchie — nur installierte Tools execute
- **R20** Write/Edit/Shell-Entzug — nur via Gatekeeper
- **R21** Audit-Pflicht — jede Aktion in audit.log.jsonl

### Stark (⛔⛔⛔ — Warnung)
- **R06** Sub-Agent = nur Analyse
- **R17** Improvement-Push an User-Projekt

### Normal (⛔)
- **R07** CP_DONE-Signal nach Checkpoint
- **R08** General-Improver max 50K Tokens

### Enforcement-Methoden
| Methode | Tool | Trigger |
|---------|------|---------|
| 5 | `dev_rule_refresh.sh` | Alle 5 Schritte |
| 6 | `dev_haerte_propagation.py` | Bei jedem delegate() |
| 9 | `dev_rule_checker.py --all` | Vor write/edit/shell |
| 10 | Multiprompt (prompt_1/2/3) | Jede Session |
| 15 | `dev_architecture_checker.py` | Bei Architektur-Dateien |
| 18 | `dev_rule_checker.py --check R18` | Vor shell/write/edit |
| Gate | `dev_gatekeeper.py` | Jede write/edit/shell |

---

## Tools (44 Python + 7 Shell)

### Härtungs-Tools
- `dev_rule_checker.py` (514 Zeilen) — Deterministischer Regel-Checker
- `dev_gatekeeper.py` (248Z) — Pre-Execute-Gate für write/edit/shell
- `dev_haerte_propagation.py` — Härte-Regeln in Sub-Agenten injizieren
- `dev_architecture_checker.py` — Architektur-Changes erkennen
- `dev_write_filter.py` — Schreib-Filter mit YAML-Validierung
- `dev_audit.py` — Audit-Log-System (JSONL)
- `dev_rule_refresh.sh` — Regel-Reaktivierung (Methode 5)

### Analyse
- `dev_observer.py` (432Z) — Framework-Scanner
- `dev_analyst.py` (312Z) — Qualitys-Checker
- `dev_architect.py` (433Z) — Architektur-Analyse
- `dev_fast_scan.py` — Schnell-Scan (Prompt/Settings/Structure)
- `dev_goose_db.py` (318Z) — SQLite-Session-Analyse
- `dev_audit_deps.py` — Dependency-Analyse
- `dev_auto_project.py` — Automatische Projekterkennung

### Build & Deployment
- `dev_build.sh` (231Z) — Distribution-Builder v3
- `dev_autobuild.sh` (127Z) — Automatischer ZIP-Builder
- `dev_workspace.py` (1442Z) — Workspace-Manager
- `dev_recipe_manager.py` (335Z) — Recipe-Installer
- `dev_goose_manager.py` (290Z) — Goose-Komponenten-Manager
- `dev_mode.sh` — MAS/Framework-Modus-Wechsler

### YAML & Edit
- `dev_editor.py` (541Z) — Sicherer YAML-Editor mit Backup/Rollback
- `dev_editor_large.py` — Zeilenbasierter Editor für >1000 Zeilen
- `dev_template_engine.py` — BP-konformer Sub-Agent-Creator
- `dev_template_generator.py` (901Z) — Agent-YAML-Generator aus SOT
- `dev_yaml_generator.py` — YAML-Generator (MAS/Generic)
- `dev_yaml_generator_core.py` — Shared YAML-Generation-Core
- `dev_yaml_generator_generic.py` — Generic YAML-Generator

### Dashboard
- `dev_dashboard_refresh.py` (403Z) — On-Demand Dashboard v3
- `dev_app_builder.py` (428Z) — Dashboard-Status-JSON-Generator
- `dashboard_prd_template.py` — PRD-Template-Generator
- `dev_dashboard_live.py` — DEPRECATED (v2)
- `dev_dashboard_poller.py` — DEPRECATED
- `dev_dashboard_pending.py` — DEPRECATED

### Self-Improve
- `dev_changes.py` (290Z) — Changes-Management
- `dev_update_schedule.py` — Self-Improve-Timing
- `dev_pattern_apply.py` — Pattern-Applier
- `dev_registry_merge.py` — Pattern-Registry-Merger
- `dev_agent_doctor.py` (494Z) — Agent-Optimizer
- `dev_generic_init.py` (715Z) — Generic-Projekt-Initialisierer
- `dev_rule_checker_generic.py` (463Z) — Generic Rule Checker

### Parallel & Workflow
- `dev_parallel.py` (425Z) — Parallel-Pool-Manager
- `dev_workflow_runner.py` — Workflow-CLI-Runner
- `dev_workload_monitor.py` (238Z) — Workload-Analyse
- `dev_intention_parser.py` — Intentions-Erkennung
- `dev_dispatch_tracer.py` — Dispatch-Tracer (NDJSON)
- `dev_dispatch_tracker.py` — Dispatch-Tree-Tracker

### Sonstige
- `dev_pytest_hook.py` — Pytest-Checker-Hook
- `dev_health_report.py` — Health-Report-Generator
- `dev_session_cleanup.sh` (219Z) — Session-Cleanup
- `run_dashboard_monitor.sh` — DEPRECATED
- `start_dashboard.sh` — DEPRECATED

---

## State-Management (SOT)

### Kern-Dateien
- **`workflows.yaml`** (2030 Zeilen) — Single Source of Truth: Regeln, Enforcements, Recovery, Tier-System, Token-Budgets, Agent-Workflow-Mappings, 80+ Workflows
- **`agent_schema.yaml`** (3410 Zeilen) — Alle 46 Agenten mit vollständigen Instructions/Prompts/Settings
- **`best-practices.yaml`** (350 Zeilen) — 35+ Best Practices
- **`guardian.yaml`** (433 Zeilen) — Health-Scores aller 41 Agenten (alle gesund)
- **`sot_schema.yaml`** — Schema-Definition für Agent-Einträge
- **`schedule.yaml`** — Self-Improve-Timing mit 12 Runden History
- **`changes.json`** (668 Zeilen) — 88 Changes-Einträge
- **`audit.log.jsonl`** — Audit-Trail (JSON-Lines)
- **`changes.log`** — Changes-Log

### Regeln
- `rules/harte_regeln.yaml` — Härte-Stufen-Definitionen
- `rules/regeln_5_extrem.yaml` — Extrem-Regeln (R01-R10)
- `rules/regeln_4_stark.yaml` — Starke Regeln (R05-R06)
- `rules/regeln_2_normal.yaml` — Normale Regeln (R07-R08)
- `rules/responsibility_matrix.yaml` — Aktions/Datei→Agent-Mapping

### Wissen
- `knowledge/01-architecture.md` — MAS-Architektur v1.0.0
- `knowledge/02-communication.md` — Kommunikationsfluss
- `knowledge/03-installation.md` — Installation
- `knowledge/04-recovery.md` — 5-Stufen-Recovery
- `knowledge/05-rules.md` — Alle R01-R18 erklärt
- `knowledge/06-tools.md` — 43 Tools
- `knowledge/07-agents.md` — Agenten-Overview
- `knowledge/08-build.md` — Build-System v3
- `knowledge/09-im-features.md` — 36+ Feature-Typen

### Checkpoints
- `checkpoints/20260618_095227/` — Komplett-Snapshot (165 Dateien)
- `checkpoints/20260618_103409/` — Komplett-Snapshot (cleanup)

### Templates
- `templates/agent_schema.yaml` — Projekt-Templates (Python/Web/Generic)
- `templates/bp_checklist.md` — 37 Feature-Typen Checkliste
- `templates/goosehints_generic_template` — .goosehints-Template
- `templates/user_regeln_template.yaml` — User-Regeln-Template

---

## Recovery-System (5 Stufen)

```
immune → checkpoint → safezone → timeline → defib
```

| Stufe | Agent | Funktion |
|-------|-------|----------|
| 1. Immune | `recovery-immune` | YAML-Prävention VOR Edit (Coronashield) |
| 2. Checkpoint | `recovery-checkpoint` | Git-similar Snapshots |
| 3. Safezone | `recovery-safezone` | Fork-Workspace für paralleles Arbeiten |
| 4. Timeline | `recovery-timeline` | Automatische Bestpunkt-Suche |
| 5. Defib | `recovery-defib` | Notfall-Wiederbelebung |

---

## Verbesserungs-Pipeline

```
general-improver (Orchestrator)
  └── im-pipeline (6 Stufen)
       ├── im-session-reader → liest Session-DB
       ├── im-finder         → erkennt 53 Feature-Typen
       ├── im-rank           → priorisiert
       ├── im-designer       → entwirft Patches
       ├── im-validator      → validiert
       └── yaml-editor       → Backup→Edit→Validate→Rollback
```

---

## Kritische Beobachtungen

1. **Instructions zu lang** — 31 von 41 Agenten haben Instructions >2000 Zeichen (Guardian Issue)
2. **9 Agenten ohne SOT-Anbindung** — `im-designer/finder/rank/session-reader/validator`, `si-analyzer/designer/validator`
3. **Hohe Selbstreferenzialität** — MAS analysiert, verbessert und überwacht sich selbst
4. **2030-zeilige workflows.yaml** — extrem umfangreiche zentrale Schaltstelle
5. **Komplettes Distribution-System** — `install.sh` → `~/.config/goose/` mit Build/Autobuild
6. **Kosten ~$15.30/Tag** (86 Sessions) laut Session-Analyse vom 14.06.
7. **Dashboard V3** — Migration von Polling-Daemon zu On-Demand-Refresh
8. **120+ Backup-Dateien** in `.backups/` und `.state/checkpoints/`
