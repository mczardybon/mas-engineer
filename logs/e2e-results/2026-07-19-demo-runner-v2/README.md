# E2E Test — sub_mas-demo-runner — 2026-07-19 (v2, human-style)

This folder is the second attempt at an E2E test of the
sub_mas-demo-runner. The first attempt (commit b40096c) used a
wrapper script which silently produced 5 x 401 errors (it passed
the REDACTED key placeholder to goose instead of the real key) and
was then deleted in commit ef78b84; that deleted folder has now
been restored at `../2026-07-19-demo-runner-ARCHIVED-script-failure/`
as a permanent transparency artifact, with its original
`TRUTHFUL_REPORT.md` documenting the failure. This v2 attempt is
the real success story.

## Method (human-style)

For each step, a single `goose run --no-session --text "..."` command
was issued in the terminal, with the real DEEPSEEK_API_KEY exported
into the shell environment beforehand. Each call was put in the
background with nohup, then polled until the goose process exited.
The output of each call was saved to its own log file.

No wrapper script, no chained commands, no "automation framework" —
just the goose CLI invoked as a user would invoke it.

## Test steps and results

### Step 1 — Build the research-team (evidence/h-build1.log)
- **Bytes:** 163,964
- **Real 401 errors:** 0
- **Test results in log:** 14/14 PASS, 0 FAIL
- **Files created at /tmp/research-team:** 36
- The build ran the full demo-runner recipe which created:
  - 5 YAML recipes: research-team.yaml + sub/{web-searcher, source-verifier, fact-extractor, synthesizer}.yaml
  - Dashboard: data.json, server.js, dashboard.html, mas-dispatch-monitor.html
  - State files: guardian.yaml, rules.yaml, health-report.json
  - Tests: test_agent_syntax.py
  - Top-level: project.yaml, workflows.yaml, 00-GUIDELINES.md, BP-CHECKLIST.md
- Notes from log:
  - "npm is not installed — the MCP dashboard server needs npm install to resolve dependencies. The server files are in place and ready for when npm becomes available."
  - "The source-verifier is the mandatory quality gate — all research results pass through it before reaching the fact-extractor. No bypass is possible."

### Step 2 — Use the team on Nobel Physics 2024 (evidence/h-task1.log)
- **Bytes:** 69,888
- **Real 401 errors:** 0
- **Output:** Full report on the 2024 Nobel Prize in Physics
- **Laureates named correctly:** John J. Hopfield, Geoffrey Hinton
- **Citation quote correct:** "for foundational discoveries and inventions that enable machine learning with artificial neural networks"
- **3 sources cited:** nobelprize.org press release, popular science PDF, scientific background PDF
- **Pipeline summary in log:** "Orchestrator → Web Search → Source Verification (all claims confidence ≥ 0.95) → Fact Extraction (18 atomic facts) → Synthesis (full report with inline citations)"

### Step 3 — Use the team on C language origin (evidence/h-task2.log)
- **Bytes:** 26,487
- **Real 401 errors:** 0
- **Output:** Full report on the invention of C
- **Inventor named correctly:** Dennis Ritchie, Bell Labs, 1972
- **Key dates correct:** 1967 (joined Bell Labs), 1972 (C renamed from NB), November 1973 (Unix kernel rewritten in C)
- **Key collaborators named correctly:** Ken Thompson (B and Unix), Brian Kernighan (K&R book)
- **3 sources cited:** Wikipedia C language, Wikipedia Dennis Ritchie, Wikipedia C language § History

### Step 4 — Improvement cycle (evidence/h-improve.log)
- **Bytes:** 42,105
- **Real 401 errors:** 0
- **Output:** 5 recipes upgraded v1.0.0 → v1.0.1
- **Validation:** All 5 YAMLs parse, all 1 test passes, all versions bumped consistently
- **Improvements applied:**
  - web-searcher: search_query_id tracking, no_results status, anti-fabrication rule
  - source-verifier: all_rejected status, structured output schema
  - fact-extractor: 4 explicit categories (background, key finding, statistic, quote), no_facts handling, anti-fabrication rule
  - synthesizer: clarified 1-indexed citation numbering, graceful degradation for missing facts
  - All recipes: standardized `prompt:` → `instructions:`

### Step 5 — Retry after improvement (evidence/h-retry.log)
- **Bytes:** 45,804
- **Real 401 errors:** 0
- **Output:** Full report on quantum entanglement
- **Key facts named correctly:** EPR paper 1935, Wu & Shaknov 1949 (first lab demo), Bell 1964, Freedman & Clauser 1972, Aspect 1982, Ekert E91 protocol
- **2 sources cited:** Wikipedia Quantum entanglement, Stanford Encyclopedia of Philosophy
- **Applications covered:** Quantum key distribution, quantum teleportation (1992 proposed, 1997 demonstrated)

## Summary

- **5 goose runs, all completed successfully, 0 real 401 errors**
- **36 files created in /tmp/research-team/ by the demo-runner** (none of these pushed to git, per user instruction)
- **5 evidence log files in this folder** (all under evidence/)
- **Total runtime:** ~28 minutes (build 6m + task1 6m + task2 5m + improve 5m + retry 6m)

## What was committed to git

- This folder: 1 README + 5 log files in evidence/
- Nothing else

## What was NOT committed (per user instruction)

- The 36 files that the demo-runner created at /tmp/research-team/
- Those files exist on the local filesystem but are not versioned
