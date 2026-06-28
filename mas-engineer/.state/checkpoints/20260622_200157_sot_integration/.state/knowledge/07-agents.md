# Agenten-Uebersicht

## MAS-Sub-Agenten (39) — recipe/sub/sub_mas-*.yaml

### Kategorie Analyse (9)
| Agent | Beschreibung |
|:------|:-------------|
| framework-knowledge | Framework-Konzepte verstehen & Bauplaene |
| framework-scanner | Framework analysieren (SCAN/AUDIT/HARDEN) |
| session-analyst | Session-Korrelation & Anomalien |
| config-auditor | Config-Konsistenz (16 Checks) |
| prompt-engineer | Prompt-Qualitaet (10 Kriterien) |
| goose-expert | Goose-Regelkonformitaet (14 Scopes) |
| im-finder | 🔍 Optimierungspotential (37 Feature-Typen) |
| im-designer | 🛠️ Patches aus Findings entwerfen |
| im-validator | ✅ Changes validieren & Rollback |

### Kategorie Recovery (6)
| Agent | Beschreibung |
|:------|:-------------|
| recovery-checkpoint | Git-aehnliche Snapshots |
| recovery-defib | Notfall-Wiederbelebung |
| recovery-immune | Coronashield YAML-Praevention |
| recovery-safezone | Paralleler Fork-Workspace |
| recovery-timeline | Automatische Bestpunkt-Suche |
| migration-helper | Framework-Migrationen planen |

### Kategorie Ueberwachung (6)
| Agent | Beschreibung |
|:------|:-------------|
| agent-guardian | Death/Drift/Loop-Ueberwachung |
| monitor-health | YAML-Config-Health |
| monitor-recovery | Checkpoint-Recovery-Monitor |
| monitor-runtime | Laufzeit-Token-Monitor |
| monitor-session | Session-Status-Monitor |
| mas-controller | Scheduler (alle 15min) |

### Kategorie Verwaltung (7)
| Agent | Beschreibung |
|:------|:-------------|
| goose-admin | Goose-Komponenten (Skills/Sessions/Logs) |
| recipe-manager | Recipes installieren/deinstallieren |
| yaml-editor | Sicheres YAML-Edit |
| worktree-manager | Git-Worktree-Manager |
| verification-runner | Ergebnis-Pruefung |
| summarizer | Zusammenfassung |
| interpreter | Interpretation |

### Kategorie Self-Improve & Konstitution (12)
| Agent | Beschreibung |
|:------|:-------------|
| general-improver | 🔬 Improvement-Pipeline Orchestrator (6 Stufen) |
| im-session-reader | 📊 Session-Datenbank lesen & Rohdaten |
| im-finder | 🔍 Optimierungspotential erkennen (37 Typen) |
| im-rank | 📊 Findings priorisieren & filtern |
| im-designer | 🛠️ Patches aus Findings entwerfen |
| im-validator | ✅ Changes validieren & Rollback |
| general-improver | 🔬 Verbesserungs-Pipeline (v2, backwards-compat) |
| dashboard-live | 📊 Live-Dashboard-Update |
| generic-init | 🌍 Generic-Improver Initialisierung (v3: Symlink + Guidelines, keine Kopie) |
| master-constitution | ⚖️ MAS-Konstitution |
| test-runner | 🧪 Tests ausfuehren & Bruch erkennen |

### Kategorie Generierung (3)
| Agent | Beschreibung |
|:------|:-------------|
| doc-generator | Docs auf Aktualitaet pruefen |
| signal-generator | Signale (CP_DONE/ERROR/SESSION_END) |
| degradation-handler | Degradation-Recovery |

## Framework Specialists (47) — specialist_*.yaml
accessibility, ai_engineer, api_designer, api_gateway, auth,
backend, chaos_engineer, cloud_architect, cost_optimizer,
database, data_engineer, data_governance, data_scientist,
ddd_architect, dependency_manager, devops, devsecops,
event_driven, frontend, i18n, incident_response,
legal_compliance, migration, ml_engineer, mobile, mobile_ci,
multi_tenant, observability, onboarding, performance,
platform_engineer, quality_manager, realtime_engineer,
refactoring, release_manager, requirements_engineer, reviewer,
search_engineer, security, software_architekt,
software_engineer, sre, system_architekt, technical_writer,
test_engineer, ux_designer, workflow_engineer

## Framework-Sub-Agenten (44) — sub_*.yaml
sub_dispatcher, sub_orchestrator,
sub_analyst, sub_analyst-accessibility, sub_analyst-auth,
sub_analyst-backend, sub_analyst-code, sub_analyst-deps,
sub_analyst-devops, sub_analyst-docs, sub_analyst-generic,
sub_analyst-i18n, sub_analyst-infra, sub_analyst-migration,
sub_analyst-observability, sub_analyst-performance,
sub_analyst-quality, sub_analyst-refactoring,
sub_analyst-requirements, sub_analyst-security, sub_analyst-sre,
sub_analyst-tests, sub_analyst-ux,
sub_session-init, sub_interpreter, sub_mode-selector,
sub_agent-selector, sub_plan-validator, sub_summarizer,
sub_status-tracker, sub_worktree-manager, sub_memory-writer,
sub_signal-generator, sub_context-preparer,
sub_degradation-handler, sub_verification-runner,
sub_starter-launch,
sub_fw-monitor-comms, sub_fw-monitor-debug,
sub_fw-monitor-health, sub_fw-monitor-memory,
sub_fw-monitor-recovery, sub_fw-monitor-runtime,
sub_fw-monitor-session

### 🔧 sub_mas-git-operator
Git-Administration: init, commit, status, log, diff. KEIN push ohne ✅.

### 🧬 sub_mas-python-repair
Python-Code-Reparatur: compile (Syntax), analyze (AST), fix (Code-Change), validate (Health-Check).

### 📝 sub_mas-doc-writer
Markdown-Dokumentation: create, update, consistency (Links check).

### 🔧 sub_mas-json-utility
JSON-Operationen: validate (Syntax), format (indent+sort), append (Eintrag hinzufügen).
### 🏗️ sub_mas-recipe-designer
Neue Sub-Agenten konzipieren, designen, in SOT eintragen, Wissen aktualisieren. Tasks: CONCEIVE, DESIGN, WORKFLOWS, SOT, KNOWLEDGE, FULL.

### 📋 sub_mas-health-reporter
Taeglichen Gesundheitsbericht ueber MAS-Zustand erstellen. Tasks: REPORT (Status sammeln), COMPARE (Trends), MARKDOWN (Bericht formatieren), FULL (alles).

