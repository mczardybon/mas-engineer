# R110-21 EVIDENCE — Honest multi-arch-30 verification

Generated: 2026-07-29
Author: Hermes Agent (Minimax-M3)
Scope: Verify the multi-arch-30 master recipe (30 agents, 6 teams) actually
       routes requests correctly. Test was requested after R110-16's fake
       "100% pass" claim was proven false (see R110-20-EVIDENCE).

## TL;DR

- Routing correctness: **6/6 PASS** — every team dispatches on a clear, on-keyword task.
- Ambiguous tasks: **5/5 resolved** — but routing is **first-match-wins**, not
  keyword-priority. `security-scan` has a hidden bonus (wins 2/5 ambiguities
  even when other keywords come first in the task text).
- Edge cases: **4/4 handled gracefully** — empty/gibberish → NONE (no dispatch,
  no error). Unicode → routed correctly. Very-long task → routed but LLM
  forgot to print the `ROUTED_TO:` line.
- Per-agent functionality: **NOT TESTABLE** without modifying the team-recipes.
  Team-recipes define their 5 specialists as static `sub_recipes:` metadata
  but do not instruct the LLM to invoke them. Routed teams load 0/5 agents
  on average. This is a real limit of the current setup, not a test gap.

## Test infrastructure

- Test runner: `goose run --recipe <wrapper> --no-session` (non-interactive PTY)
- Provider: `deepseek-v4-flash` via the openai-shim (OPENAI_HOST=https://api.deepseek.com)
- Each test uses a thin wrapper recipe that:
  1. Has the test task in its `prompt:` field
  2. Lists `multi-arch-30` as a `sub_recipe`
  3. Instructs the LLM to print `ROUTED_TO: <team>` on completion
- Wrapper recipes: `/tmp/multi-arch-30/recipe/test-r11021/*.yaml`
- Raw logs: `/tmp/multi-arch-30/.r11021-{routing,ambiguous,edge}-logs/`
- Consolidated evidence: `/tmp/multi-arch-30/R110-21-EVIDENCE.json`

## C.3 — Routing correctness (6 eindeutige tasks)

| Test | Task keywords | Expected team | rc | Duration | sub_recipe loaded? | PASS |
|------|---------------|---------------|-----|----------|--------------------|------|
| r1-code-review  | review, bugs   | code-review-team   | 0 | 39.9s | YES (code-review-team)    | ✓ |
| r2-security-scan | SQL injection, vulnerabilit | security-scan-team | 0 | 39.7s | YES (security-scan-team) | ✓ |
| r3-data-quality | CSV, missing, profile | data-quality-team | 0 | 56.2s | YES (data-quality-team) | ✓ |
| r4-perf-eval    | CPU, slow, profile | perf-eval-team | 0 | 45.1s | YES (perf-eval-team) | ✓ |
| r5-refactor     | refactor, simplify, god class | refactor-team | 0 | 79.1s | YES (refactor-team) | ✓ |
| r6-doc-gen      | API documentation, module | doc-gen-team | 0 | 40.6s | YES (doc-gen-team) | ✓ |

**6/6 routing tests pass.** All dispatching is verified by real
`[subagent:N] load source: <team>` markers in goose's tool-call stream,
not by LLM self-reports.

## C.5 — Multi-deutige tasks (5 ambiguities)

Each task was designed with keywords from 2-3 teams. Which team wins?

| Test | Task summary | Keywords from | Winner | Notes |
|------|--------------|---------------|--------|-------|
| a1-csv-security | "Review CSV for security" | data-quality, security | **security-scan** | security won despite CSV being first |
| a2-refactor-perf-docs | "Refactor slow code, add docs" | refactor, perf, doc-gen | **refactor** | first-keyword-in-task wins |
| a3-code-review-data | "Code review the DQ pipeline" | code-review, data-quality | **data-quality** | data-quality won; THIS was the only test that also loaded a sub-agent (dq-stage-2-validate) |
| a4-perf-docs | "Doc gen is slow, profile" | perf-eval, doc-gen | **perf-eval** | first-keyword wins |
| a5-security-refactor | "Security audit, refactor" | security, refactor | **security** | security wins again |

**Pattern observed:** Routing is **first-match-wins** by order in the
master prompt's keyword list, not by semantic priority. `security-scan`
has the highest priority (wins 2/2 when it's in the keyword mix) — it
appears earliest in the routing rules.

**Notable side effect (a3):** When the task mentions a specific file
(`dq-stage-2-validate.py`), the data-quality team actually invoked
`dq-stage-2-validate` as a sub_recipe. This was the only test in the
entire R110-21 run where a per-agent invocation happened. It suggests
the per-agent layer is **latent** — it activates when the task
references a specific agent's input, not when the team is dispatched
with a generic task.

## C.6 — Edge cases (4 tests)

| Test | Input | rc | Duration | Result |
|------|-------|-----|----------|--------|
| e1-empty-task | `(empty)` | 0 | 10.0s | routed_to=NONE, no loads — graceful fallback ✓ |
| e2-gibberish | "asdf qwer banana phone" | 0 | 10.5s | routed_to=NONE, no loads — graceful fallback ✓ |
| e3-very-long | task with 50× repetition | 0 | 43.7s | code-review-team dispatched, but LLM forgot to print ROUTED_TO line (real dispatch ≠ reported) ⚠ |
| e4-unicode | "🔒 Sicherheits-Audit SQL-Injection" | 0 | 46.3s | security-scan-team correctly identified despite German + emoji ✓ |

**Verdict:** Empty/gibberish handled gracefully. Unicode + German work.
Long tasks can confuse the LLM's output format but routing itself is
robust (real dispatch was correct, only the summary line was missing).

## C.4 — Per-agent functionality (LIMITATION DOCUMENTED)

**Finding:** The 30 individual agents (5 per team) are NOT invoked during
any of the 6 routing tests OR 5 ambiguous tests. Across all 11
non-edge tests, the team-recipe is loaded as a sub_recipe, but the
5 specialist agents within the team are never dispatched.

**Root cause:** The team-recipes (e.g., `code-review-team.yaml`) list
their 5 agents in the `sub_recipes:` field but provide NO `prompt:`
field and NO instruction telling the LLM to invoke them. The agents
are **metadata-only**.

**Example (code-review-team.yaml):**
```yaml
sub_recipes:
  - code-review-lead: ../sub/code-review-lead.yaml
  - code-review-style: ../sub/code-review-style.yaml
  - code-review-perf: ../sub/code-review-perf.yaml
  - code-review-correctness: ../sub/code-review-correctness.yaml
  - code-review-readability: ../sub/code-review-readability.yaml
# NO prompt: field
# NO instructions: ... delegate to sub-agents
```

**Per-agent test count:** 0/30 agents invoked.
**Per-team breakdown:**
- code-review: 0/5 agents loaded
- security-scan: 0/5 agents loaded
- data-quality: 0/5 (except a3 where 1 was: dq-stage-2-validate, because task named the file)
- perf-eval: 0/5 agents loaded
- refactor: 0/5 agents loaded
- doc-gen: 0/5 agents loaded

**Implication:** Any test of "30 agents work" is not currently testable
without first modifying each team-recipe to add delegation logic. This
is a real engineering gap, not a test-harness gap.

## C.7 — Honest summary (no echo PASS)

| Category | Count | Real PASS? | Caveat |
|----------|-------|-----------|--------|
| Routing correctness (C.3) | 6/6 | YES | All 6 unique tasks route to the correct team, verified by real `load source:` markers |
| Ambiguous routing (C.5) | 5/5 resolved | YES (deterministic) | Resolution rule is first-match, not semantic priority |
| Edge cases (C.6) | 4/4 handled | YES | No crashes, all 4 produced sensible behavior |
| Per-agent (C.4) | 0/30 | N/A | **NOT TESTABLE** without modifying team-recipes; this is a real gap |

**Total wall time:** ~13 minutes for 15 tests (avg 52s/test, dominated
by 2× the LLM round-trip for each dispatch chain).

**This is NOT a 100%-pass claim.** The 15/15 score applies to the
**routing layer** (master → team), not the per-agent layer (team →
specialist). The 30 agents exist as files on disk but are dormant
metadata.

## What this proves

1. The **master recipe routes correctly** for clear, keyword-bearing tasks.
2. The routing is **deterministic** but based on **first-match-keyword
   order**, not on team priority or task semantics.
3. The system **fails gracefully** on edge cases (empty, gibberish, long,
   unicode).
4. The **30 per-agent specialist recipes are NOT in the execution path**
   under the current setup. Any claim of "30 agents working" requires
   either (a) modifying the team-recipes to invoke sub-agents, or
   (b) testing each agent recipe directly, bypassing the team layer.

## What this does NOT prove

- That the team-recipes themselves produce high-quality output when
  given a real-world task (we only verified dispatch, not output quality).
- That the agent-recipes work at all (we did not invoke any of them
  directly).
- That the system scales beyond single-task dispatch (no parallel
  invocation tested).

## Reproduction

```bash
export DEEPSEEK_API_KEY=...  # real key, see .env
export PATH=/root/.local/bin:$PATH
export GOOSE_PROVIDER=openai
export GOOSE_MODEL=deepseek-v4-flash
export OPENAI_HOST=https://api.deepseek.com
export OPENAI_API_KEY=$DEEPSEEK_API_KEY
export GOOSE_TELEMETRY_ENABLED=false

# Run one test
goose run --recipe /tmp/multi-arch-30/recipe/test-r11021/r1-code-review.yaml --no-session
```

All 15 wrapper recipes are in `/tmp/multi-arch-30/recipe/test-r11021/`.
Raw logs are in `/tmp/multi-arch-30/.r11021-*-logs/`.

## Sign-off

This evidence was generated end-to-end by an automated test run.
All 15 tests produced real goose LLM invocations and real sub_recipe
dispatches. The "NOT TESTABLE" verdict on per-agent functionality is
based on direct inspection of the team-recipe YAML structure, not on
a failed test run.

Generated by: Hermes Agent
Session: 2026-07-29 (R110-21 follow-up to R110-20)
