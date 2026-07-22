# E2E Real Test — 2026-07-22

## What This Is

**Honest, raw, re-runnable end-to-end tests of 3 demo multi-agent teams.**

Unlike the previous report (which was a "narrative" without raw artifacts), this folder
contains the actual recipe files AND the raw goose session output (PTY logs) from real
e2e runs.

## Setup

- **3 demo teams** built 2026-07-21, originally in `/tmp/{sales,marketing,translator}-team/`
- **Today 2026-07-22**: copied into `/root/.config/goose/recipes/{sales,marketing,translator}/`
  with absolute `path:` references in sub_recipes (because `./sub/` resolves relative to
  cwd, not to the recipe file location).
- **DEEPSEEK_API_KEY** must be set in env for goose auth (the bash fallback
  `${DEEPSEEK_API_KEY:-sk-XXXX}` was removed in the security fix this morning)

## Test Results

### Sales Team ✅ PASS (real e2e)

- **Recipe**: `sales/sub/sales-orchestrator.yaml`
- **Test query**: "Find 3 fintech startups in Munich"
- **Log**: `sales-direct.log` (2739 bytes)
- **Tool calls (▸)**: 10
- **Sub-agents invoked**: 7 (subagent:141, 142, 143)
- **Sub-agents actually used**: `lead-scraper`, `lead-verifier`, `outreach-drafter` — all 3
  ECHT dispatched with real subagent IDs visible in the log
- **Results**:
  - 3 leads found (Finleap, N26, Vauban)
  - 1 verified Munich-based (Finleap) — N26 was actually Berlin, Vauban was actually London
  - 1 outreach draft created for Finleap
- **401 errors**: 0

### Marketing Team ⚠️ PARTIAL

- **Recipe**: `marketing/sub/marketing-orchestrator.yaml`
- **Test query**: "Create Q3 content strategy for our SaaS" (campaign_type=full)
- **Log**: `marketing-direct.log` (8999 bytes)
- **Tool calls (▸)**: 5
- **Sub-agents invoked (subagent:NNN)**: **0** ← problem
- **What happened**: orchestrator TRIED to dispatch to `seo-researcher`, `content-writer`,
  `social-media-manager`, `analytics-reporter`, `email-campaign-manager` — but they
  weren't registered as available sources. The orchestrator self-reported: "The specialist
  spokes don't exist as registered subagents yet" and synthesized the Q3 strategy
  directly itself.
- **Result**: Got a nice Q3 SaaS content plan (SEO keywords, content pillars, social
  plan, email sequences), BUT the sub-agents were NOT actually invoked — the orchestrator
  did the work alone. This is a structural gap in the marketing recipe.
- **401 errors**: 0

### Translator Team ✅ PASS (real e2e)

- **Recipe**: `translator/sub/translator-orchestrator.yaml`
- **Test**: "Hello world, this is a test translation" → German
- **Log**: `translator-full.log` (5544 bytes) — full run with `timeout 60`
- **Tool calls (▸)**: 7
- **Sub-agents invoked**: orchestrator dispatched to 3 translators + 1 judge
- **What happened**:
  - 3 translators dispatched in PARALLEL (literal, literary, technical)
  - Real translations produced:
    - Literal: "Hallo Welt, dies ist eine Testübersetzung"
    - Literary: "Sei gegrüßt, Welt — dies ist eine Probe aufs Exempel, übersetzt mit bedächtiger Hand."
    - Technical: "Hallo Welt, dies ist eine Testübersetzung"
  - Translation-judge scored and voted
  - Winner: Literal (29/30 points)
- **Note**: The orchestrator's `delegate` calls used `source: translator-orchestrator`
  (itself) as the source, not the named sub-agents. But goose still correctly created
  parallel sub-sessions (subagent:147, 148, etc.) that loaded the sub-agent recipes
  via the orchestrator's instructions. The end-to-end pipeline works.
- **401 errors**: 0

## Summary Table

| Team | Recipe | Tool calls | Sub-agents | 401s | Verdict |
|------|--------|------------|------------|------|---------|
| Sales | sales-orchestrator | 10 | 7 (real) | 0 | ✅ PASS |
| Marketing | marketing-orchestrator | 5 | 0 (self-fallback) | 0 | ⚠️ PARTIAL |
| Translator | translator-orchestrator | 7 | 3 parallel + 1 judge | 0 | ✅ PASS |

## How To Reproduce

```bash
# Setup
export DEEPSEEK_API_KEY="sk-YOUR-KEY"
export OPENAI_API_KEY="$DEEPSEEK_API_KEY"
# Recipes must be in /root/.config/goose/recipes/{team}/sub/
# with sub_recipes paths pointing to absolute paths
# (the install in this folder assumes the sub_recipes are already absolute)

# Run
cd /root/.config/goose/recipes
goose run --recipe sales/sub/sales-orchestrator.yaml --params query="Find 3 fintech startups in Munich"
goose run --recipe marketing/sub/marketing-orchestrator.yaml --params query="Create Q3 content strategy for our SaaS"
goose run --recipe translator/sub/translator-orchestrator.yaml --params source_text="Hello world" --params target_lang="German" --params source_lang="English"
```

## What Was Wrong With The Previous Report

The 2026-07-21 "22/22 PASS" e2e-final-report claimed 3 demo teams ran successfully and
had 0 errors. The actual git commit `271a0f3` (which replaced the secret-leaking
`c96881f`) only contained:
- `dev-mas-engineer.yaml` (the agent)
- `E2E_FINAL_REPORT.md` (the narrative)
- `replay-mas-e2e-full.sh` (the script with hardcoded key)

**The 3 demo orchestrators, 16 sub-agents, and live test logs were NOT in the commit.**
They were in `/tmp/{team}-team/recipe/` and `/workspace/h-logs/`, with no provenance
in the public repo. This was called out by the user on 2026-07-22 as a transparency
gap: only the report existed, no raw data to verify.

This commit fixes that by including:
1. The actual 3 demo team recipe packages
2. The raw PTY session logs from real re-runs today
3. An honest summary of which parts actually worked vs which fell back to orchestrator-
   self-execution
