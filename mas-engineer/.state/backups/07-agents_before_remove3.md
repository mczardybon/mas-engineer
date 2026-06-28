# Agenten-Uebersicht

## MAS-Sub-Agenten (36) — recipe/sub/sub_mas-*.yaml

### Kategorie Analyse (9)
| Agent | Beschreibung |
|:------|:-------------|
| framework-knowledge | Framework-Konzepte verstehen & Bauplaene |
| framework-scanner | Framework analysieren (SCAN/AUDIT/HARDEN) |
| session-analyst | Session-Korrelation & Anomalien |
| config-auditor | Config-Konsistenz (16 Checks) |
| prompt-engineer | Prompt-Qualitaet (10 Kriterien) |
| goose-expert | Goose-Regelkonformitaet (14 Scopes) |
| si-analyzer | System-Analyse (36 Typen, 11 TAs, 19 MAs) |
| si-designer | Feature-Design + Goose-Check + Priorisierung |
| si-validator | Nachher-Validierung + Rollback-Empfehlung |

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

### Kategorie Verwaltung (8)
| Agent | Beschreibung |
|:------|:-------------|
| goose-admin | Goose-Komponenten (Skills/Sessions/Logs) |
| recipe-manager | Recipes installieren/deinstallieren |
| yaml-editor | Sicheres YAML-Edit |
| worktree-manager | Git-Worktree-Manager |
| verification-runner | Ergebnis-Pruefung |
| summarizer | Zusammenfassung |
| interpreter | Interpretation |
| dashboard-live | Live-Dashboard-Update |

### Kategorie Self-Improve & Konstitution (7)
| Agent | Beschreibung |
|:------|:-------------|
| self-improver | 10-Schritt-Pipeline (komplexester Agent) |
| generic-init | Generic-Improver Initialisierung |
| master-constitution | MAS-Konstitution |
| performance | Performance-Analyse |
| security | Security-Analyse |
| test-runner | Tests ausfuehren & Bruch erkennen |
| test-specialist | Test-Engineering |

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
