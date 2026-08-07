# E2E Testing Architecture — Why external AND internal?

**Date:** 2026-07-24
**Context:** Analysis of E2E test structure after pull of the other AI

---

## What the MAS can do today

The MAS has 10 Test/Monitoring agents registered:

| Agent | Task |
|-------|------|
| sub_mas-framework-scanner | Analyzes the framework |
| sub_mas-config-auditor | 16 cross-reference checks |
| sub_mas-test-runner | Runs pytest |
| sub_mas-agent-guardian | Monitors agents for death/drift/loop |
| sub_mas-health-reporter | Daily status report |
| sub_mas-monitor-health | YAML-config health |
| sub_mas-monitor-runtime | Runtime token-monitor |
| sub_mas-monitor-recovery | Checkpoint-recovery |
| sub_mas-monitor-session | Session-status |
| sub_mas-unix-test-runner | Shell-level filesystem checks (POSIX test) |

---

## Why still external scripts? (e2e_run_all.py, e2e_teams.py)

### The chicken-and-egg problem:

| Aspect | External (Python-script) | Internal (MAS-delegation) |
|--------|--------------------------|----------------------------|
| Chicken-and-egg | Can test the MAS WITHOUT the MAS running | MAS must already run to test itself |
| Reliability | No dependency on the system under test | MAS must be functional |
| Honesty | Sees what a user sees (`goose run` from outside) | Would judge itself |
| Scope | "Do the recipes even start?" | "Do the agents work internally?" |

A system cannot fully test itself. If `dev-mas-engineer.yaml` is broken, the MAS cannot delegate to any agent — then you need an external tester.

---

## The problem: too much pulled to the outside

The other AI built things externally that the MAS could do itself:

- `e2e_run_all.py` tests 63 recipes, 66 workflows, recovery → could be done by `sub_mas-test-runner`
- `e2e_teams.py` tests business teams → could be done by `sub_mas-demo-runner`

---

## Ideal architecture (2 stages)

```
STAGE 1 — EXTERNAL (CI / other AI / user):
  goose recipe validate dev-mas-engineer.yaml
  goose recipe list
  → Checks: "Is the MAS even startable?"

  ↓ If that works:

STAGE 2 — MAS ITSELF (delegation):
  "Run a complete self-check"

  ↓
  sub_mas-test-runner         → pytest (Python logic)
  sub_mas-unix-test-runner    → Shell-level (filesystem)
  sub_mas-framework-scanner   → Framework analysis
  sub_mas-config-auditor      → Cross-reference checks
  sub_mas-agent-guardian      → Agent health
  sub_mas-demo-runner         → E2E business-test (teams)
```

- **Stage 1 must remain external** (chicken-and-egg principle)
- **Stage 2 can and should be done by the MAS itself** — it already has all agents for that

---

## Open points (not yet implemented)

1. `sub_mas-unix-test-runner` — exists as YAML, but NOT registered in `dev-mas-engineer.yaml`
2. `sub_mas-self-auditor` — same case
3. The new demo-team agents (analytics-reporter, code-reviewer-*, etc.) don't belong in the MAS-core — only in demo-projects
4. A `/develop --e2e` slash-command is missing that triggers all stage-2 tests

---

## Conclusion

The external E2E-scripts (`e2e_run_all.py`, `e2e_teams.py`) are architecturally correct for stage 1 (external baseline check). But they should not be the only test strategy. The MAS should itself be able to run all internal tests on request — that is already possible today, but is not yet used.
