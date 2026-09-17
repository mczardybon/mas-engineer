# Agents-Overview

## MAS-Sub-Agents (39) — recipe/sub/sub_mas-*.yaml

### Category Analysis (9)
| Agent | description |
|:------|:-------------|
| framework-knowledge | understand framework concepts & blueprints |
| framework-scanner | analyze framework (SCAN/AUDIT/HARDEN) |
| session-analyst | Session-Correlation & Anomalies |
| config-auditor | Config-Consistency (16 Checks) |
| prompt-engineer | Prompt-Quality (10 Criteria) |
| goose-expert | Goose-Rule-conformity (14 Scopes) |
| im-finder | 🔍 Optimization potential (37 Feature-types) |
| im-designer | 🛠️ Design patches from findings |
| im-validator | ✅ Validate changes & rollback |

### Category Recovery (6)
| Agent | description |
|:------|:-------------|
| recovery-checkpoint | Git-similar Snapshots |
| recovery-defib | Emergency-Resuscitation |
| recovery-immune | Coronashield YAML-Prevention |
| recovery-safezone | Parallel Fork-Workspace |
| recovery-timeline | Automatic Best-Point-Search |
| migration-helper | Plan framework Migrations |

### Category Monitoring (6)
| Agent | description |
|:------|:-------------|
| agent-guardian | Death/Drift/Loop-Monitoring |
| monitor-health | YAML-Config-Health |
| monitor-recovery | Checkpoint-Recovery-Monitor |
| monitor-runtime | Runtime-token-Monitor |
| monitor-session | Session-Status-Monitor |
| mas-controller | Scheduler (all 15min) |

### Category Management (7)
| Agent | description |
|:------|:-------------|
| goose-admin | Goose-Components (Skills/Sessions/Logs) |
| recipe-manager | Install/uninstall recipes |
| yaml-editor | Safe YAML-Edit |
| worktree-manager | Git-Worktree-Manager |
| verification-runner | Result-Check |
| summarizer | Summarization |
| interpreter | Interpretation |

### Category Self-Improve & Constitution (12)
| Agent | description |
|:------|:-------------|
| general-improver | 🔬 Improvement-Pipeline Orchestrator (6 Levels) |
| im-session-reader | 📊 Read Session-Database & Raw-Data |
| im-finder | 🔍 Detect optimization potential (37 types) |
| im-rank | 📊 Prioritize & filter findings |
| im-designer | 🛠️ Design patches from findings |
| im-validator | ✅ Validate changes & rollback |
| general-improver | 🔬 Improvement-Pipeline (v2, backwards-compat) |
| dashboard-live | 📊 Live-Dashboard-Update |
| generic-init | 🌍 Generic-Improver Initialization (v3: Symlink + Guidelines, no copy) |
| master-constitution | ⚖️ MAS-Constitution |
| test-runner | 🧪 Execute tests & detect regressions |

### Category Generation (3)
| Agent | description |
|:------|:-------------|
| doc-generator | Check docs for currency |
| signal-generator | Signals (CP_DONE/ERROR/SESSION_END) |
| degradation-handler | Degradation-Recovery |

## framework Specialists (47) — specialist_*.yaml
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

## framework-Sub-Agents (44) — sub_*.yaml
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
Git-Administration: init, commit, status, log, diff. NO push without ✅.

### 🧬 sub_mas-python-repair
Python-Code-Repair: compile (Syntax), analyze (AST), fix (Code-Change), validate (Health-Check).

### 📝 sub_mas-doc-writer
Markdown-Documentation: create, update, consistency (check links).

### 🔧 sub_mas-json-utility
JSON-Operations: validate (Syntax), format (indent+sort), append (add entry).
### 🏗️ sub_mas-recipe-designer
Design new Sub-Agents, design them, enter in SOT, update knowledge. Tasks: CONCEIVE, DESIGN, WORKFLOWS, SOT, KNOWLEDGE, FULL.

### 📋 sub_mas-health-reporter
Create daily Health-Report about MAS-State. Tasks: REPORT (collect status), COMPARE (trends), MARKDOWN (format report), FULL (all).
