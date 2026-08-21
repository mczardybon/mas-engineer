---
name: mas-engineer-e2e-user-perspective
description: How to interpret E2E tests, "fix this" prompts, and demo-team feedback in mas-engineer — the user is the test driver (not the developer), demo teams are on-demand generated (not static), variance is a feature not a regression, and "fix the team recipe" is usually the wrong abstraction level. Use whenever an E2E prompt, a "fix das" prompt, or a demo-team result comes in. Complements mas-engineer-demo-team-improvement and mas-engineer-e2e-100-percent-recipe.
category: devops
---

## When to use

Load this skill when: How to interpret E2E tests, "fix this" prompts, and demo-team feedback in mas-engineer — the user is the test driver (not the developer), demo teams are on-demand generated (not static), variance is a feature not a regression, and "fix the team recipe" is usually the wrong abstraction level. Use whenever an E2E prompt, a "fix das" prompt, or a demo-team result comes in. Complements mas-engineer-demo-team-improvement and mas-engineer-e2e-100-percent-recipe.

For mas-engineer framework development, this skill provides domain-specific guidance that supersedes generic workflows.



# MAS-Engineer E2E from the User's Perspective

## The 5 trigger-points (checklist — read all 5 before responding)

### 1. E2E tests are run by the USER, not the developer

The user does not open `tools/*.py`. The user types a prompt into the
goose CLI and watches what comes out. The MAS does the rest.

- **Wrong:** "Let me read the test runner to understand the failure"
- **Right:** "Let me run the recipe the user would run and see what
  they would see"

When the user reports an E2E failure, reproduce it as a USER would —
through the CLI entry point, with the same model, same timeout,
same cwd. The hermes-side `tools/dev_self_auditor.py` is for
suspicion-checking candidate fixes, not for replacing the real e2e.

### 2. Demo teams (sales / marketing / translator / ...) are on-demand generated

They are NOT static recipes that should be "fixed" when one fails.
Each generation is a fresh LLM run. The artifact is the generation
prompt + the validator, not the team's per-instance output.

- A "failed" demo-team is a *generation* failure, not a *recipe* failure
- The fix lives in the prompt-template or validator, not in the team yaml
- For static (intentionally stable) infra, the rule is different —
  there, fix the recipe

### 3. Variance is a feature, not a regression signal

"100% pass on 1 run" does NOT mean "fixed". A later failure does NOT
mean "fix is broken". It means the system has variance.

The correct metric is **success rate over N generations**:
- "12 of 15 generated teams pass" → fix is solid
- "3 of 15 generated teams pass" → fix is missing or wrong
- "15 of 15 pass on run A, 4 of 15 on run B" → variance, not regression

Apply the same rule the mas-engineer health-report uses for
infrastructure (14 runs) to business-demo-teams — but currently does
NOT. That gap is the real bug, not any single team failure.

### 4. "Fix the findings in the team recipe" is usually the wrong abstraction

There are two layers of bugs:
- **Framework bugs** (tools/*.py, instructions/, validator-yamls,
  the dev-self-auditor, the summon/dispatch glue) — worth fixing
  permanently, because they affect every run
- **Demo-team-instance issues** (one sales team, one marketing team,
  one translator team) — NOT worth fixing as recipes. Fix the
  generator, measure success-rate over N

When the user says "fix this team" or "fix the recipe", ask first:
"Framework bug or generation variance?" before patching.

### 5. When the user says "fix das" — ASK, don't patch

The user has corrected this frame twice (2026-07-19 and 2026-07-24).
The pattern is:
- User reports a failure
- I assume "fix the recipe" 
- User: "no, you misunderstood — see trigger 1/2/3/4"

Before patching ANY recipe yaml after a "fix das" prompt, run through
this checklist internally and confirm with the user which layer
they mean.

## How this skill connects to others

- `mas-engineer-demo-team-improvement` — handles the actual demo-team
  improvement workflow (this skill explains WHEN not to use it)
- `mas-engineer-e2e-100-percent-recipe` — handles static-recipe E2E
  (this skill explains the on-demand-generation case)
- `im-pipeline` — the 5-phase pipeline runs framework-bug fixes; for
  generation-variance issues, the pipeline is the wrong tool

## The single sentence to remember

> Run E2E as the user would. Demo teams are generated not stored.
> Variance is a feature. Fix the framework, not the team. Ask when
> the user says "fix this".
