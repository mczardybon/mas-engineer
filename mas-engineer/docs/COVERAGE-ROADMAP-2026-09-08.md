# Coverage Roadmap (post-R110-378)

Generated 2026-09-08 from `/tmp/cov-r110378.json`.

Total tools/ coverage after R110-378: **64%** (8396/13171 stmts, +38.24pp vs R110-377 baseline 26%).

## R110-37x progress so far (8 commits, +456pp combined, 359 tests)

| R-Nr | Target file | Pre | Post | Delta | Tests |
|------|-------------|-----|------|-------|-------|
| R110-371 r2 | dev_workspace.py | 71% | 80.1% | +9.1pp | — |
| R110-372 r1 | dev_editor.py | 0% | 49.87% | +49.87pp | — |
| R110-373 r2 | dev_editor.py | 49.87% | 58.18% | +8.31pp | — |
| R110-374 r1 | dev_observer.py | 0% | 91.2% | +91.2pp | — |
| R110-375 r3 | dev_yaml_check.py | 13.7% | 94.4% | +80.7pp | 58 |
| R110-376 r1 | dev_generic_init.py | 11.7% | 91% | +79.3pp | 99 |
| R110-377 r1 | dev_agent_doctor.py | 0% | 99% | +99pp | 80 |
| R110-378 r1 | dev_architect.py | 0% | 100% | +100pp | 52 |

## Next-up files (lowest coverage, biggest impact)

Sortable by `missing_statements * 1.5` (rough effort estimate).

| File | Coverage | Missing stmts | Effort hint |
|------|---------:|--------------:|-------------|
| tools/dq_stage3_anomalies.py | 7.4% | 277 | large (anomaly detector) |
| tools/dev_rule_checker.py | 10.2% | 405 | large (regex rules) |
| tools/dev_rule_checker_generic.py | 9.9% | 291 | medium (rule dispatcher) |
| tools/dev_goose_db.py | 10.5% | 171 | medium (DB wrapper) |
| tools/dev_guardian_scan.py | 11.4% | 147 | medium (scan loop) |
| tools/dev_dispatch_tracer.py | 7.6% | 121 | small-medium (pure) |
| tools/dev_recursion_override.py | 12.1% | 123 | small-medium |
| tools/dev_analyst.py | 12.8% | 171 | medium |
| tools/dev_gatekeeper.py | 12.9% | 148 | medium |
| tools/dev_goose_manager.py | 14.4% | 154 | medium |
| tools/bulk_findings_fixer.py | 15.2% | 95 | small |
| tools/e2e_teams.py | 15.8% | 176 | medium |
| tools/e2e_run_all.py | 16.2% | 202 | medium |
| tools/dev_changes.py | 16.2% | 150 | medium |
| tools/dev_yaml_immune.py | 16.9% | 108 | small |
| tools/dev_tff.py | 17.3% | 115 | small |
| tools/pre_check_lib/auto_repair.py | 17.3% | 67 | small |
| tools/dev_goose_expert_check.py | 17.3% | 86 | small |
| tools/dev_template_engine.py | 17.5% | 94 | small |
| tools/dev_directive_applier.py | 20.6% | 77 | small |

## Next-up files (medium coverage, fast wins)

| File | Coverage | Missing stmts | Effort hint |
|------|---------:|--------------:|-------------|
| tools/dev_dispatch_live.py | 21.5% | 95 | small |
| tools/dev_yaml_generator_generic.py | 21.9% | 50 | very small |
| tools/dev_recipe_manager.py | 22.9% | 118 | small |
| tools/dev_security_scan.py | 24.0% | 73 | small |
| tools/dev_test_runner.py | 24.5% | 71 | small |
| tools/dev_audit.py | 24.7% | 61 | very small |
| tools/dev_workload_monitor.py | 25.0% | 93 | small |

## Refs
- R110-378 (predecessor, +52 tests, dev_architect 0%→100%)
- R110-377 (predecessor, +80 tests, dev_agent_doctor 0%→99%)
- R110-376 (predecessor, +99 tests, dev_generic_init 11.7%→91%)
- R110-78 verification-theater guard
- Skill: mas-engineer-coverage-push-workflow
