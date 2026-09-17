# R110-333 — R-Sprint-Folgeplan (R110-321 queue exhausted)

## TL;DR

The R110-321 candidate list (4 files) is EXHAUSTED. This
document is the FOLLOW-UP plan: a new candidate list of
6 files (5 tool files + 1 re-audit set) for R110-334+. The
R-sprint pattern continues: each candidate is a single
🔧 R-sprint code-fix commit + a 📝 R-sprint evidence-closure
commit, mirroring R110-320..R110-330.

## Background (what R110-321 was)

R110-321 (d56ec64, 2026-08-21) was a 4-file candidate list
created from a `find tools/ -name "*.py" -size +5k | xargs
wc -l` + cov-report cross-reference. The 4 files were:
  - dev_im_finder_scan.py (1660 stmts) — DONE in R110-323
  - dev_workspace.py (1445 stmts) — DONE in R110-326
  - dev_template_generator.py (901 stmts) — DONE in R110-328
  - dev_dashboard_data.py (566 stmts) — DONE in R110-330

R110-323..R110-331 found 12 latent bugs + 1 code smell
across those 4 files. The R-sprint proved the pattern
works: small, focused latent-bug audits on large tool files
find real bugs (regex char-class, yaml injection, default-dict
hot-reload, etc.). The pattern is worth repeating.

## New candidate list (R110-334+)

Identical audit method: `find mas-engineer/tools -name "*.py"
-type f -exec wc -l {} \;` sorted by line count, then
cross-referenced with coverage reports.

| Prio | File | Stmts | Status | Why |
|---|---|---|---|---|
| 1 | dev_generic_init.py | 1101 | NEW | Generic init for mas-engineer; 18+ top-level `create_*` functions, highest-leverage un-audited file |
| 2 | dev_message_queue.py | 1039 | NEW | MQ implementation, central to the mas-engineer ecosystem, has env-var-driven config (MAS_MQ_*) — high latent-bug surface |
| 3 | dev_rule_checker.py | 858 | NEW | Rule engine, 700+ lines of rule definitions, candidate for regex/string-handling bugs (R110-328-style) |
| 4 | e2e_teams.py | 597 | NEW | E2E test runner for teams, very high leverage (every CI run hits it), zero in-depth audit |
| 5 | dev_session_query.py | 512 | NEW | Session query, recent (R110-310 era), low coverage, candidate for cursor/iteration bugs |
| 6 | dev_self_auditor.py | 509 | NEW | Self-auditor (heals the mas-engineer), candidate for "auditing-itself" bugs (a self-referential class of bug) |
| 7 | e2e_run_all.py | 481 | NEW | Top-level E2E runner, similar leverage to e2e_teams.py |
| 8 | dev_rule_checker_generic.py | 468 | NEW | Generic rule checker, sibling of dev_rule_checker.py |
| 9 | dev_goose_expert_check.py | recent | NEW | Recently added (R110-310 era), low coverage, candidate for env-var validation bugs |
| 10 | (re-audit) the 4 done files | — | RE-AUDIT | The R-sprint caught 12 bugs in 1 pass, a 2nd pass with fresh eyes could find more (especially regex/string-handling) |

Total: 9 new files + 1 re-audit set. The re-audit is OPTIONAL
(lowest priority) — only run it if the 9 new files are done
and there are no other candidates.

## Recommended order (highest-leverage first)

The order above is RECOMMENDED. Prio-1 (dev_generic_init)
is largest un-audited file with 18+ `create_*` functions —
each one is a candidate for "what if input is empty/malformed"
bugs. Prio-2 (dev_message_queue) is the highest-leverage
un-audited file: it's the central MQ that the mas-engineer
ecosystem uses, so any bug there affects every team
interaction.

Prio-3..9 are progressively lower-leverage but still
high-value. The re-audit is a "if we have time" — not
required.

## R-sprint cadence (mirroring R110-320..R110-330)

For each candidate, the pattern is:

  1. 🔧 R<round>-<num>: latent-bug audit + fix (1-3 bugs)
  2. tests/test_r<round>_<num>_<topic>_bug_fixes.py (NEW,
     direct-import or in-process pattern, R110-318/326)
  3. 📝 R<round>-<num>-EVIDENCE: standalone evidence-closure
     commit (R110-316/318/319/327/329/331 pattern)
  4. Update STATUS.md (R110-332 pattern)
  5. Update CHANGELOG (R110-225-229 pattern)
  6. Force-add logs/e2e-evidence-gen2/ (R110-258 pattern)

Cycle time: 1-2 R-codes per day (matching R110-320..R110-330).

## What this is NOT

This is a PLAN, not a commitment. The user picks which
candidates to actually run. R110-334 could pick any of the
9 files (or a different one not on this list). R110-333
just lays out the OPTIONS.

## Refs

- R110-332 (0cfe867) — STATUS.md backfill (this section is
  being added to STATUS.md too, mirror of R110-332's pattern)
- R110-331 (a9d284a) — R-sprint FINALE
- R110-330 (09c4d92) — last R-sprint code-fix (dev_dashboard_data)
- R110-321 (d56ec64) — original candidate list (now exhausted)
- R110-320 (e7ef060) — R-sprint pattern origin
- R110-318 (0fb0fdf) — conftest cleanup + EVIDENCE format
- R110-316/317/319 — R-sprint evidence-closure pattern
- R110-310 (subprocess cov pattern) — first explored, abandoned
  for in-process
- R110-305 (4-round numstat re-verify)
- R110-281 (force-push-verbot) — never force-push
- Skills: pre-push-gate, pre-push-body-claim-verification,
  mas-engineer-commit-protocol, mas-engineer-coverage-push-workflow
