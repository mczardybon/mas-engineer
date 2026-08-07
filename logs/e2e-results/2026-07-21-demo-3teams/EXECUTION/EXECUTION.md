# MAS-Engineer 3-Team Demo — REAL E2E EXECUTION (2026-07-21)

**Goal:** Actually RUN each of the 3 teams (not just load them) with a real user query, observe behavior, document what works and what does not.

**Method:** For each team, the root recipe was invoked with `goose run --recipe <root> --no-session` and a real query piped via stdin. NO `--explain`. This is the live multi-agent flow.

---

## TL;DR — Honest results

| Team | Architecture | Recipe loads? | Orchestrator dispatches? | Specialists executed? | Result |
|------|--------------|:-------------:|:------------------------:|:---------------------:|--------|
| sales-team | Pipeline | ✅ | ❌ (asks 5 clarifying questions) | ❌ | **FAIL** (2/2 attempts) |
| marketing-team | Hub-and-Spoke | ✅ | ❌ (asks "what marketing challenge?") | ❌ | **FAIL** (1/1 attempt) |
| translator-team | Parallel + Voting | ✅ (after fix) | ❌ (asks for source_text + target_lang) | ❌ | **FAIL** (2/2 attempts) |

**All 3 teams fail at the same step:** the orchestrator LLM receives the user query, prints a polite "I'll handle this" message, and asks clarifying questions — but never actually invokes any specialist agent. The full multi-agent flow was **never executed** in any of the 5 attempts.

---

## Detailed execution traces

### 1. sales-team — 2 attempts, both failed

**Attempt 1** (vague query):
- Query: "Find 5 B2B SaaS leads in the DACH region..."
- Behavior: orchestrator lists its 5 agents, then asks 5 clarifying questions (industry, location, company size, product, number of leads)
- Last line: *"I'll orchestrate the full pipeline: scrape → verify → draft outreach → closing strategy"*
- ❌ No `delegate` call, no specialist invocation

**Attempt 2** (query with all answers pre-filled):
- Query: included industry=AI/dev-tools, location=DACH, company size=10-200, product=mas-engineer, count=3
- Behavior: orchestrator again lists 5 agents and asks 4 of the 5 questions I already answered
- Last line: *"I'll run the full pipeline — always ensuring leads pass through verification before any outreach is drafted."*
- ❌ No `delegate` call, no specialist invocation

### 2. marketing-team — 1 attempt, failed

**Attempt 1** (explicit "dispatch to all 4 specialists in parallel"):
- Query: asked for SEO + content + social + analytics with "Do NOT ask clarifying questions"
- Behavior: orchestrator lists its 5 specialists, then asks "Go ahead — what marketing challenge can I help you tackle today?"
- ❌ Ignored the explicit "do not ask" instruction

### 3. translator-team — 2 attempts, both failed

**Attempt 1** (missing `prompt:` field — build bug):
- Error: `Error: no text provided for prompt in headless mode`
- Root cause: `translator-team.yaml` had no top-level `prompt:` field. When invoked in headless mode with stdin, goose could not find a prompt to pass to the orchestrator sub-recipe.
- Fix: added `prompt:` field with instructions to dispatch to all 3 translators + judge.

**Attempt 2** (after fix):
- Query: provided source_text and target_lang explicitly
- Behavior: orchestrator lists 5 subagents, then asks again for `source_text` and `target_lang` (which the user already provided via stdin)
- ❌ No `delegate` call to any of the 3 translators, no judge invocation

---

## Root cause analysis (post-mortem)

The orchestrator's prompt instructions say:

> "Use `delegate` to dispatch sub-tasks to specialists in the correct order."
> "DYNAMICALLY dispatches... Use `delegate`... Invoke ONLY the relevant spokes."

But `delegate` is **not actually a tool available in the goose session**. Goose's `sub_recipes` field loads the sub-recipes as **separate runnable recipes**, not as **in-session callable tools**. The LLM is being told to call a tool that does not exist.

This is a **fundamental design issue** in how mas-engineer / Goose recipes represent multi-agent systems:

| Recipe concept | What it actually does in goose | What the orchestrator instructions assume |
|----------------|--------------------------------|------------------------------------------|
| `sub_recipes: [...]` | Loads sub-recipes; they can be invoked as **separate** `goose run --recipe <sub>` shell commands | Believes sub-recipes are in-session callable tools via `delegate()` |

Two possible fixes (out of scope for this E2E run):
1. **Orchestrator calls sub-recipes as shell commands** — the orchestrator prompt must include explicit `goose run --recipe ./sub/<name>.yaml --text "<query>"` invocations. This would work but is brittle.
2. **Replace `sub_recipes` with `extensions` or `tools`** — define each specialist as a real in-session tool that the orchestrator can call. This is the right design but requires rewriting the recipe schema.

---

## What this E2E run actually proves

✅ **Proves (positive findings):**
- All 3 teams **load as valid recipes** (`Loading recipe: ... 🏢 Sales Team... 🎯 MARKETING-TEAM... 🌐 Translator Team...`)
- All 3 teams have **0 authentication errors** in any of the 5 attempts
- The build-time YAML validation was correct (all files parse, all `sub_recipes` paths resolve)
- The architecture-specific keywords are present in the orchestrator prompts (DYNAMICALLY, NO fixed order, PARALLEL + VOTING, MANDATORY quality gate)

❌ **Does NOT prove (negative findings):**
- That any of the 3 teams can actually execute a real multi-agent flow
- That the specialists ever get invoked
- That the final output would be a synthesized result from multiple agents
- That the architecture (pipeline / hub-and-spoke / parallel+voting) is observable in runtime behavior

---

## Honest summary

The `2026-07-21-demo-3teams` build was a **successful recipe-construction demo**, not a **runtime multi-agent execution demo**. The orchestrator prompts are written correctly on paper, but Goose's `sub_recipes` mechanism does not provide the in-session `delegate` tool that the orchestrators try to use. The fix is non-trivial (recipe schema redesign), so it is documented here as a known limitation rather than silently glossed over.

This is exactly the kind of finding that E2E execution is meant to surface, and it is now permanently archived in this folder as evidence.

---

## Files in this folder

| File | Size | Content |
|------|-----:|---------|
| `01-sales-query.txt` | 429 B | Attempt 1 query (vague) |
| `02-sales-exec-attempt1.log` | 18 lines | Result: 5 clarifying questions, no dispatch |
| `03-sales-query-attempt2.txt` | 614 B | Attempt 2 query (with all answers) |
| `04-sales-exec-attempt2.log` | 20 lines | Result: 4 clarifying questions, no dispatch |
| `05-marketing-query.txt` | 545 B | Marketing query (explicit "don't ask") |
| `06-marketing-exec.log` | 20 lines | Result: "what marketing challenge?", no dispatch |
| `07-translator-query.txt` | 621 B | Translator query with source + target lang |
| `08-translator-exec-attempt1.log` | 8 lines | Error: no text provided for prompt in headless mode |
| `09-translator-exec-attempt2.log` | 29 lines | After prompt-field fix: still asks for source_text again |
