# E2E Test — sub_mas-demo-runner (2026-07-19)

## What was tested
- sub_mas-demo-runner (recipe: ~/.config/goose/recipes/sub/sub_mas-demo-runner.yaml)
- Demo-runner built a complete research-team at /tmp/research-team with 5 agents + dashboard
- 15/15 verification checks PASS (5x goose --explain, 5x yaml.safe_load, 5x json validate, MCP server test)
- 2 real research tasks (Nobel Physics 2024, C programming language)
- 1 improvement cycle (7 fixes applied)
- 1 retry after improvement (quantum entanglement)

## Results
- **Build:** 15/15 PASS, 5 agents + dashboard
- **Task 1 (Nobel 2024):** Hopfield + Hinton, citations [1][4][5]
- **Task 2 (C language):** Dennis Ritchie, Bell Labs, 1972-1973, 5 sources, 0.95-0.98 confidence
- **Improvement:** 7 fixes (source-verifier filtering, fact-extractor schema, synthesizer attribution)
- **Retry (entanglement):** 0.96-0.98 confidence, Wikipedia + Stanford Encyclopedia

## What was NOT pushed (per user)
- /tmp/research-team/recipe/* (created by demo-runner)
- /tmp/research-team/.mas/* (created by demo-runner)
- /tmp/research-team/tests/* (created by demo-runner)

## Files in this folder
- evidence/ — all 5 goose run logs
- run.log — main timing log
- e2e-demo-runner.sh — replay script

## Total runtime
~25 minutes (build 7m + task1 5m + task2 5m + improve 3m + retry 4m)
