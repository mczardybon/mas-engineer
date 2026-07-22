# HONEST E2E TEST: 3 Business Demo Teams (Sales/Marketing/Translator)

**Date:** 2026-07-22 01:38 UTC
**Tester:** Hermes (per user instruction: "teste es wie ein Mensch es tun wurd")
**Test method:** Real goose CLI calls (no wrapper scripts), one foreground
goose run per team, with --params as the human user would invoke them.

## WHAT WAS TESTED

Each of the 3 demo teams was invoked with a short prompt and explicit
--params, exactly as a human user would do in a non-interactive scenario:

```bash
# Sales
goose run --recipe /tmp/sales-team/recipe/sales-team.yaml \
  --no-session \
  --params icp_industry="fintech" --params icp_size="50-200" \
  < /tmp/e2e_human_sales.txt

# Marketing
goose run --recipe /tmp/marketing-team/recipe/marketing-team.yaml \
  --no-session \
  --params product_name="TestProduct" --params target_audience="CTOs..." \
  < /tmp/e2e_human_marketing.txt

# Translator
goose run --recipe /tmp/translator-team/recipe/translator-team.yaml \
  --no-session \
  --params source_text="..." --params target_lang="German" \
  < /tmp/e2e_human_translator.txt
```

## RESULTS — ALL 3 TEAMS FAIL THE SAME WAY

### 1. SALES TEAM — FAIL (orchestrator ignores params)
**Log:** /workspace/h-logs/h-test-sales-1784683915.log
**Exit:** 0
**Auth errors:** 0
**Outcome:** Recipe loads, params printed as recognized, but orchestrator
responds: "Just tell me your ICP (Ideal Customer Profile) and I'll run
the full pipeline!" — params are NOT used by orchestrator.

### 2. MARKETING TEAM — FAIL (orchestrator ignores params)
**Log:** /workspace/h-logs/h-test-marketing-1784684270.log
**Exit:** 0
**Auth errors:** 0
**Outcome:** Recipe loads, params printed as recognized, but orchestrator
responds: "How would you like to use the marketing team today?" — params
are NOT used by orchestrator.

### 3. TRANSLATOR TEAM — FAIL (orchestrator ignores params)
**Log:** /workspace/h-logs/h-test-translator-1784684279.log
**Exit:** 0
**Auth errors:** 0
**Outcome:** Recipe loads, params printed as recognized, but orchestrator
responds: "I'll ask for the text and language first, since you haven't
provided them yet." — params are NOT used by orchestrator.

## ROOT CAUSE (from inspecting the recipes)

Each team recipe (sales-team.yaml, marketing-team.yaml, translator-team.yaml)
has the same structural defect:

1. **No `parameters:` section in the recipe YAML** — the recipe accepts
   --params on the CLI (goose prints them) but does NOT declare them in
   a `parameters:` block.
2. **No `{{ param_name }}` template interpolation** — the instructions
   and prompt strings are hardcoded; they do not interpolate the params.
3. **Orchestrator prompt says "tell me what you need"** — the orchestrator
   is instructed to ask the user for parameters instead of using the
   ones that were passed.

**VERDICT: The params-problem in the 3 demo teams is NOT fixed.**

## CONTEXT: This was already known

A previous test (2026-07-21, see
e2e-results/2026-07-21-demo-3teams/E2E-FIX-VERIFICATION/) reported the
same problem:

> "After the welcome message, every single one of the 3 orchestrators
> asks the user for the SAME information that was already provided via
> --params"

The health-report from 2026-07-21 also showed:
> "Fixed sub_recipes architecture bug: added summon extension to
> orchestrators, updated prompts"

That fix was about sub_recipes LOADING, not about PARAMS DISPATCH. The
param-dispatch problem is a separate bug that is still present.

## WHAT MY RECENT IM-005..009 WORK ACTUALLY CHANGED

My recent pushed commits (IM-007 f1a4a59, IM-009 41e3f70) affected:

- `recipe/instructions/sub_mas-im-finder.md` — IM-finder agent prompt
- `tools/dev_im_finder_scan.py` — internal scanner for improvements
- `recipe/dashboard-data-refresh.yaml` — dashboard agent prompt
- `recipe/sub/sub_mas-team-packager.yaml` — team-packager agent prompt

These are all INTERNAL mas-engineer components. They do NOT change the
3 demo teams' recipes (which are in /tmp/, not in master). Even if they
had, the params-dispatch problem is in the recipe structure itself, not
in the agent prompts.

## HONEST CONCLUSION

| What | Status |
|------|--------|
| 3 demo team recipes can be loaded | ✅ YES (no auth errors, clean load) |
| 3 demo team orchestrators dispatch work | ❌ NO (all 3 ask for params again) |
| 3 demo teams are usable in non-interactive mode | ❌ NO |
| Health-report claims about "param fix" | ❌ INACCURATE (the 2026-07-21 fix was about sub_recipes loading, not params dispatch) |
| My recent IM-005..009 pushed work | ✅ Does what it claims (940→929 findings, 5 delegates, 5 subagents, 202 verdicts) — but does NOT touch the 3 demo teams |
| 7-stage IM-pipeline end-to-end | ❌ NOT TESTED |
| 3 demo teams end-to-end | ❌ NOT WORKING |

## WHAT WOULD FIX THE PARAMS-DISPATCH PROBLEM

For each of the 3 team recipes (sales-team.yaml, marketing-team.yaml,
translator-team.yaml):

1. Add a `parameters:` section declaring each parameter with a
   description and default value.
2. Use `{{ param_name }}` template syntax in the `instructions:` and
   `prompt:` fields to interpolate the values.
3. Update the orchestrator's behavior to USE the interpolated values
   instead of asking the user.

## FILES

- Test logs: /workspace/h-logs/h-test-{sales,marketing,translator}-*.log
- Team recipes: /tmp/{sales,marketing,translator}-team/recipe/*.yaml
- Previous test: e2e-results/2026-07-21-demo-3teams/
