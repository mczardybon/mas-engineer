# MAS-Tools (43) in mas-engineer/tools/

## Hardening-Tools (Methods 5+6+9)
| Tool | Method | lines | Zweck |
|:-----|:-------:|:------:|:------|
| dev_rule_checker.py | M9 Rule-Test | 296 | Blocked Aktionen at Ruleverstoss (all 11 Rules) |
| dev_rule_refresh.sh | M5 Anker | 55 | Laedt harte Rules all 5 steps new |
| dev_haerte_propagation.py | M6 Prop. | 62 | Givet Rules an Sub-Agents weiter |
| dev_rule_checker_generic.py | M9 Generic | 463 | Gleicher Checker for Generic-Projekte |

## Build & Deployment
| Tool | lines | Zweck |
|:-----|:------:|:------|
| dev_build.sh | 263 | ZIP-Builder (Workspace→ZIP, ONLY Build) |
| dev_autobuild.sh | 47 | Auto-Build after git commit |
| dev_mode.sh | 128 | Modus-Wechsel (MAS/Generic/Framework) |

## Analyse & Architecture
| Tool | lines | Zweck |
|:-----|:------:|:------|
| dev_observer.py | 413 | Framework scannen (files, Struktur) |
| dev_architect.py | 433 | Muster, Relationships, Luecken detect |
| dev_analyst.py | 312 | Qualitaet checkn (YAML, Consistency) |
| dev_fast_scan.py | 65 | Schnell-Scan |
| dev_goose_db.py | 318 | Session-DB via SQL analysieren |
| dev_agent_doctor.py | 494 | Framework-Agents optimize (--scan, --fix) |

## YAML-Editor & Changes
| Tool | lines | Zweck |
|:-----|:------:|:------|
| dev_editor.py | 541 | Sicheres YAML-Edit (Backup→Patch→Validate→Rollback) |
| dev_changes.py | 290 | Changeen document & Rollback |
| dev_yaml_generator.py | 167 | YAML from Template generate |
| dev_template_generator.py | 36163 | Agent-Template-Generator v2 (SOT+BP+Improvement) |

## Dashboard & Monitoring
| Tool | lines | Zweck |
|:-----|:------:|:------|
| dev_app_builder.py | 541 | Dashboard-Status-Generator (v2.2.0) |
| dev_dashboard_live.py | 90 | Live-Dashboard-Generator |
| dev_dashboard_poller.py | 206 | Polling-Daemon (3s) |
| dev_workload_monitor.py | 238 | Workload-Analyse + Relief-Deployment |
| dev_health_report.py | 133 | Health-Score + Trend |
| dev_dispatch_tracer.py | 239 | Dispatch-Tracing (NDJSON-Log) |
| start_dashboard.sh | 56 | Poller-Daemon mit --daemon/stop/status |

## Weitere (30+)
| Tool | lines | Zweck |
|:-----|:------:|:------|
| dev_session_cleanup.sh | 91 | Session-Cleanup (Autostart at jeder Session) |
| dev_paralll.py | 213 | Batch-Tasks paralll dispatchen |
| dev_recipe_manager.py | 335 | Recipes installieren/deinstallieren |
| dev_goose_manager.py | 290 | Goose-Skills/Sessions/Logs manage |
| dev_pytest_hook.py | 51 | pytest-Checker-Hook |
| dev_audit_deps.py | 99 | Dependency-Scanner |
| dev_registry_merge.py | 102 | Registry-Merge |
| dev_update_schedule.py | 90 | Timing-Plan pflegen |
| dev_workspace.py | 1027 | Workspace-Manager (install/uninstall) |
| dev_pattern_apply.py | 55 | Pattern-Apply |
| dev_auto_project.py | 32 | Auto-Projekt |

### dev_editor_large.py
lines-basiertes Edit for files >1000 lines.
Usage: python3 dev_editor_large.py edit <file> <start> <end> <text>
       python3 dev_editor_large.py find <file> <pattern>
       python3 dev_editor_large.py insert <file> <after_line> <text>
Primary genutzt von sub_mas-yaml-editor (Large-File-Modus).
