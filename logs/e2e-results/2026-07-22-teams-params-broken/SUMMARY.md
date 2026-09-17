# HONEST TEST RUN: 3 Business Demo Teams Params Dispatch

**Date:** 2026-07-22 01:38 UTC
**Tester:** Hermes
**Method:** Real goose CLI calls (one per team, no wrapper scripts)
**Test command pattern:**
```bash
goose run --recipe <path> --no-session --params <KEY=VALUE> < prompt.txt
```

## Results — all 3 teams fail the same way

| Team | Exit | Auth errors | Orchestrator response |
|------|------|-------------|------------------------|
| sales-team | 0 | 0 | "Just tell me your ICP..." (params ignored) |
| marketing-team | 0 | 0 | "How would you like to use the marketing team today?" (params ignored) |
| translator-team | 0 | 0 | "I'll ask for the text and language first, since you haven't provided them yet." (params ignored) |

**VERDICT: Params-dispatch problem is NOT fixed.**

The recipes load cleanly (no 401 errors, no crashes), but the
orchestrators do not use the --params they receive. Each orchestrator
prompts the user for information that was already provided via --params.

## Root cause

Each team recipe has the same structural defect:

1. No `parameters:` block in the recipe YAML.
2. No `{{ param_name }}` template interpolation in instructions/prompt.
3. Orchestrator prompt is hardcoded to "tell me what you need" instead
   of using the params that were passed.

## Logs

- /workspace/h-logs/h-test-sales-1784683915.log
- /workspace/h-logs/h-test-marketing-1784684270.log
- /workspace/h-logs/h-test-translator-1784684279.log

## What would fix it

For each of the 3 recipes:
1. Add `parameters:` block with each param's name, description, default.
2. Use `{{ param_name }}` in instructions and prompt.
3. Update orchestrator to use the interpolated values.

## What this means for IM-005..009 work

My recent pushed commits (f1a4a59, 41e3f70) did NOT touch the 3 demo
team recipes (they live in /tmp/, not in master). The params-dispatch
problem is a separate issue that predates my work and is still present.
