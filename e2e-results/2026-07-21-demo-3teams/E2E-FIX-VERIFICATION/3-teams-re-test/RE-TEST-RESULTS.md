# 3-Team Re-Test After Issue 7355/7570 Fix — HONEST RESULTS

**Date**: 2026-07-21
**Tester**: Hermes
**Context**: After the type:platform fix (commits d03efd2, 5431a40), the
user correctly pointed out that the 3 teams from the 21.07 demo (sales,
marketing, translator) were never re-tested for actual delegation behavior.
This document records the honest results.

## What was tested

I re-ran the 3 demo-team root recipes with the fix in place, passing
--params on the command line (which is how the human user would invoke
them in a non-interactive scenario).

## Result — RECIPE LOAD: PASS (all 3)

All 3 recipes (`sales-team.yaml`, `marketing-team.yaml`, `translator-team.yaml`)
load cleanly with `goose run --recipe <path> --no-session`. Goose prints
"Parameters used to load this recipe: ..." showing the params were parsed.
Goose opens a deepseek-chat session, prints the welcome banner, NO crash.

This proves the Issue 7355/7570 LOADING fix works for these 3 recipes too.

## Result — ORCHESTRATOR DISPATCH: FAIL (all 3)

After the welcome message, every single one of the 3 orchestrators asks
the user for the SAME information that was already provided via --params:

### translator-team
- --params source_text="Hello world" --params target_lang="German"
- Orchestrator response: "I need two pieces of information from you:
  1. source_text — What text would you like translated?
  2. target_lang — Which language should it be translated into?"

### sales-team
- --params icp_industry="fintech" --params icp_size="50-200"
- Orchestrator response: "Willkommen! What can I help you with today?
  Here are some example pipelines I can run: ... Just describe your
  Ideal Customer Profile (ICP) and I'll handle the rest!"

### marketing-team
- --params topic="DevOps tools"
- Orchestrator response: "Hello! 👋 I'm your Marketing Orchestrator ...
  Just tell me what you are working on, and I'll dynamically dispatch
  the right agents ..."

## Root cause of the dispatch failure

This is a SEPARATE issue from Issue 7355/7570. The cause is the recipe
design: the root recipes have a static `prompt:` template that does not
reference `--params`. The orchestrator's `prompt:` is hard-coded
explanatory text, not a template that interpolates the params.

## The TWO failures, clearly distinguished

| # | Failure | Issue | Status |
|---|---------|-------|--------|
| 1 | Recipe fails to load (crash / silent summon-loss) | #7355 / #7570 | **FIXED and VERIFIED** |
| 2 | Recipe loads but orchestrator ignores --params, asks again | Recipe-design | **NOT FIXED, separate issue** |

The current certificate claims "Issue 7355 fixed and verified". This is
TRUE for the loading part only. The dispatcher actually delegating to
specialists with the user-provided context is a SEPARATE, unfixed problem.

## What would actually fix #2

For each root recipe (sales-team.yaml, marketing-team.yaml, translator-team.yaml),
the `prompt:` field needs to be a template that interpolates --params.
Example for translator-team.yaml:

```yaml
prompt: |
  You are the TRANSLATOR ORCHESTRATOR.
  User-provided parameters:
    source_text: {{source_text}}
    source_lang: {{source_lang | default "auto"}}
    target_lang: {{target_lang | default "English"}}

  PARALLEL dispatch the source text to all 3 translators (literal,
  literary, technical) simultaneously, then have the judge score and
  vote for the best translation.
```

This template work is OUT OF SCOPE for the Issue 7355/7570 fix. It is
a recipe-engineering task that needs to be done per-recipe.

## Implication for the certificate

The current `E2E-FIX-VERIFICATION/CERTIFICATE.md` and `FINAL-E2E-EVIDENCE.md`
overclaim by saying things like:
- "mas-engineer IS E2E-functional" — true for the mas-engineer
  framework / orchestrator config, NOT true for the 3 demo teams
- "ALL HYPOTHESES VERIFIED" — the delegation hypothesis (the
  orchestrator actually dispatches) was NOT verified
- "VERIFIED FUNCTIONAL" — applies to the meta-system (dev-mas-engineer),
  not the demo teams

These need to be rewritten to be honest.

## What's true and what isn't

### TRUE (verified in this session and previous sessions)
- The mas-engineer ROOT recipe (`dev-mas-engineer.yaml`) loads with
  type:platform fix
- summon extension is available in the mas-engineer session
- 52 sub-recipes are auto-injected as system prompts
- The model can answer substantive MAS-related questions with the
  52 sub-recipes loaded (verified via goose run --text workaround)
- The 3 demo-team ROOT recipes load cleanly (no crash, no error)
- pre-push-validator passes 8/8

### NOT VERIFIED
- The 3 demo-team orchestrators actually delegating to specialists
  with user-provided context (--params is ignored, orchestrator
  re-asks for the same info)
- The interactive TUI dispatch (typing a query, seeing `▸ delegate`
  in real-time from a non-TTY environment) — node.js TUI does not
  work with stdin-submit from non-TTY
- The 52-sub-recipe "delegation" (what was tested was the model
  having all 52 as flat system prompts, NOT the orchestrator logic
  routing to them)
- The end-to-end success of sales/marketing/translator demos
  from this hermes-sandbox environment

## Recommendation

1. Rewrite CERTIFICATE.md, FINAL-E2E-EVIDENCE.md, SUMMARY.txt to
   clearly distinguish "loading fix verified" from "delegation
   behavior verified"
2. The 3 demo-team orchestrators need a separate recipe-engineering
   pass to fix the --params issue (not in scope of this commit)
3. A human user with a real Goose TUI is needed to verify the full
   delegation chain for the 3 demo teams
