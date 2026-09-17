📊 EVIDENCE — R110-284 — Coverage baseline 62% (Ziel: ≥85% in R110-285+)

Bug: Coverage-messung im mas-engineer repo fehlte. Letzte EVIDENCE
(R110-282) hatte nur pytest totals (1995 PASS in 365s), keine code-
coverage. R110-284 schließt diese lücke und definiert die baseline
vor der R110-285+ test-ausbau-run.

Messung (R110-284 baseline):
  - Tool: coverage.py 7.15.3
  - Source: mas-engineer/ (mit omit: tests/, .mase/, .state/, .mas/,
    e2e-results/, logs/)
  - Mode: --branch (line + branch coverage)
  - Test-run: pytest mas-engineer/tests/ -k 'not phoenix_recovery'
    --deselect mas-engineer/tests/test_dev_phoenix_recovery_publish.py
  - Resultat: 1995 passed, 1 skipped, 23 deselected, 4 warnings
    in 461.32s (7 min 41 sec)

Coverage-resultat (R110-284 baseline, sortiert nach cover %):

  ≥95% cover (5 files, framework-glue, optimal):
    dev_auto_project.py        95%  ( 26 stmts)
    dev_pytest_hook.py         96%  ( 35 stmts)
    dev_pattern_apply.py       98%  ( 39 stmts)
    dev_fast_scan.py           99%  ( 60 stmts)
    dev_editor_large.py       100%  ( 44 stmts)

  70-94% cover (6 files, akzeptabel, kann besser):
    dev_haerte_propagation.py  86%  ( 41 stmts)
    dev_spec_invariant.py      85%  (233 stmts)
    dev_im_finder_scan.py      80%  (703 stmts)
    dev_im_design_patches.py   79%  ( 64 stmts)
    dev_self_audit.py          76%  (173 stmts)
    dev_message_queue.py       74%  (622 stmts)

  50-69% cover (6 files, test-ausbau nötig):
    dev_phoenix_log_persister.py 69%  ( 61 stmts)
    dev_category_drift.py        68%  ( 80 stmts)
    dev_dashboard_data.py         67%  (299 stmts)
    dev_issue_db.py               64%  (219 stmts)
    dev_recovery_defib.py         61%  ( 88 stmts)
    dev_architecture_checker.py   61%  ( 44 stmts)
    dev_template_generator.py     57%  (503 stmts)
    dev_audit_deps.py             53%  ( 76 stmts)
    dev_dispatch_tracker.py       50%  (174 stmts)
    dev_intention_parser.py       49%  ( 62 stmts)

  <50% cover (3 files, kritisch, priorität 1):
    dev_workspace.py            34%  (877 stmts) ← größter blinde fleck
    dev_evidence_sot.py         29%  (162 stmts)
    dev_parallel.py             27%  (222 stmts)

  TOTAL: 62% (4907 stmts, 1786 miss, 2142 branches, 283 partial)

Ziel: ≥85% in R110-285+ (R110-285 = plan, R110-286+ = implementation).

Strategie für 62% → 85%:

  PRIORITÄT 1 (3 files, ≈+8-10%):
    dev_workspace.py 34→80%   =  +290 covered
    dev_evidence_sot.py 29→75% =  +75 covered
    dev_parallel.py 27→70%     =  +95 covered

  PRIORITÄT 2 (5 files im 50-69% bereich, ≈+5-7%):
    dev_intention_parser.py 49→80%
    dev_dispatch_tracker.py 50→80%
    dev_audit_deps.py 53→80%
    dev_template_generator.py 57→80%
    dev_architecture_checker.py 61→80%
    dev_recovery_defib.py 61→80%
    dev_issue_db.py 64→80%
    dev_dashboard_data.py 67→80%
    dev_category_drift.py 68→80%
    dev_phoenix_log_persister.py 69→80%

  PRIORITÄT 3 (5-6 files im 70-85% bereich, ≈+3-4%):
    dev_message_queue.py 74→85%
    dev_self_audit.py 76→85%
    dev_im_design_patches.py 79→85%
    dev_im_finder_scan.py 80→88%
    dev_spec_invariant.py 85→90%
    dev_haerte_propagation.py 86→90%

Erwartete total-coverage: 62% → ~85% (ziel erreicht).

Pre-push-gate (R110-284):
  Step 0 (secret scan, tracked + history):   OK 0 secrets
  Step 1 (pre-commit hook, staged content):  OK PASS
  Step 2 (pytest tests/):                    OK 1995/1995 in 461s
  Step 3 (commit msg, 📊 EVIDENCE format):   OK per protocol
  Step 4 (push):                              pending
  Step 5 (post-flight audit):                 pending

Files (1):
  A logs/e2e-evidence-gen2/R110-284-COVERAGE-BASELINE.md
    (NEW, voll-ständige coverage-messung + strategie für R110-285+)

Cumulative state after R110-284:
- 1995/1995 tests passing in mas-engineer/tests/ (phoenix_recovery
  deselected per pre-push-check17-flake-handling skill)
- 62% code coverage (baseline, R110-285+ zielt auf ≥85%)
- 0 DRIFT findings
- 0 secret leaks
- 1 disclosed + recovered mangel (R110-281 force-push, dokumentiert)
