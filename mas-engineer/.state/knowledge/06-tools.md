# MAS-Tools (47) in mas-engineer/tools/

## Hardening-Tools (Methods 5+6+9)
| Tool | Method | lines | Purpose |
|:-----|:-------:|:------:|:------|
| dev_rule_checker.py | M9 Rule-Test | 296 | Blocked actions on rule violation (all 11 Rules) |
| dev_rule_refresh.sh | M5 Anchor | 55 | Reloads hard rules every 5 steps |
| dev_haerte_propagation.py | M6 Prop. | 62 | Passes rules to sub-agents |
| dev_rule_checker_generic.py | M9 Generic | 463 | Universal Checker for Generic-Projects |

## Build & Deployment
| Tool | lines | Purpose |
|:-----|:------:|:------|
| dev_build.sh | 263 | ZIP-Builder (Workspace→ZIP, ONLY Build) |
| dev_autobuild.sh | 47 | Auto-Build after git commit |
| dev_mode.sh | 128 | Mode switch (MAS/Generic/framework) |

## Analysis & Architecture
| Tool | lines | Purpose |
|:-----|:------:|:------|
| dev_observer.py | 413 | Scan framework (files, structure) |
| dev_architect.py | 433 | Detect patterns, relationships, gaps |
| dev_analyst.py | 312 | Quality check (YAML, Consistency) |
| dev_fast_scan.py | 65 | Quick scan |
| dev_goose_db.py | 318 | Analyze session DB via SQL |
| dev_agent_doctor.py | 494 | Optimize framework agents (--scan, --fix) |

## YAML-Editor & Changes
| Tool | lines | Purpose |
|:-----|:------:|:------|
| dev_editor.py | 541 | Safe YAML edit (Backup→Patch→Validate→rollback) |
| dev_changes.py | 290 | Document changes & rollback |
| dev_yaml_generator.py | 167 | Generate YAML from Template |
| dev_template_generator.py | 36163 | Agent-Template-Generator v2 (SOT+BP+Improvement) |

## Dashboard & Monitoring
| Tool | lines | Purpose |
|:-----|:------:|:------|
| dev_app_builder.py | 541 | Dashboard-Status-Generator (v2.2.0) |
| dev_dashboard_refresh.py | 353 | On-Demand Dashboard Generator |
| dev_dashboard_data.py | 272 | Dashboard Data Generator for MCP App |
| dev_workload_monitor.py | 238 | Workload analysis + relief deployment |
| dev_health_report.py | 133 | Health-Score + Trend |
| dev_dispatch_tracer.py | 239 | Dispatch tracing (NDJSON-Log) |

## Additional (30+)
| Tool | lines | Purpose |
|:-----|:------:|:------|
| dev_session_cleanup.sh | 91 | Session cleanup (autostart at every session) |
| dev_paralll.py | 213 | Dispatch batch tasks in parallel |
| dev_recipe_manager.py | 335 | Install/uninstall recipes |
| dev_goose_manager.py | 290 | Manage Goose-Skills/Sessions/Logs |
| dev_pytest_hook.py | 51 | pytest checker hook |
| dev_audit_deps.py | 99 | Dependency-Scanner |
| dev_registry_merge.py | 102 | Registry-Merge |
| dev_update_schedule.py | 90 | Maintain timing plan |
| dev_workspace.py | 1027 | Workspace-Manager (install/uninstall) |
| dev_pattern_apply.py | 55 | Pattern-Apply |
| dev_auto_project.py | 32 | Auto-Project |

### dev_editor_large.py
Line-based Edit for files >1000 lines.
Usage: python3 dev_editor_large.py edit <file> <start> <end> <text>
       python3 dev_editor_large.py find <file> <pattern>
       python3 dev_editor_large.py insert <file> <after_line> <text>
Primarily used by sub_mas-yaml-editor (large-file mode).
