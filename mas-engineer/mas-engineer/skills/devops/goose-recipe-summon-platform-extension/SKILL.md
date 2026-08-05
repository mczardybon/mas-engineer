---
name: goose-recipe-summon-platform-extension
description: Diagnose and fix silent sub_recipes dispatch failure in Goose 1.24.0+ recipes. Use when a recipe's orchestrator prints welcome but never invokes sub-agents via load/delegate.
category: devops
---

# Diagnose: goose recipe sub_recipes silent dispatch failure (Issue 7355/7570)

## Symptoms
- Recipe loads cleanly (`goose run --recipe X --no-session` does not crash)
- Orchestrator prints welcome message, lists available sub-agents
- BUT no sub-agent is ever invoked when user sends a query
- No error message, no warning, no log
- Delegation tool (`load` / `delegate`) silently unavailable

## Root cause
PR #6964 (goose 1.24.0) moved the `summon` extension from `type: builtin`
to `type: platform`. Recipes with their own `extensions:` block must now
list `summon` explicitly:

```yaml
extensions:
  - name: summon
    type: platform
```

If the `extensions:` block is missing entirely OR uses the old
`type: builtin` value, the `load`/`delegate` tool is unavailable and
delegation silently fails.

## Diagnosis procedure
1. `goose run --recipe <path> --no-session --render-recipe` — does it
   parse? Rendered output shows `type: platform, name: summon`?
2. `grep -A2 '^extensions:' <path>` — is the block present? Is type
   `platform` or `builtin`?
3. Check SUB-recipes too: orchestrator recipes need the same fix
4. Check LIBRARY recipes: same fix applies

## Fix template
```yaml
# Add to root recipe if missing:
extensions:
  - name: summon
    type: platform

# Change in library recipes that have wrong type:
# extensions:
#   - name: summon
#     type: builtin    # WRONG pre-1.24, silent dispatch failure
extensions:
  - name: summon
    type: platform     # CORRECT for goose 1.24.0+
```

## Verification
After fix:
- `goose run --recipe <path> --no-session --render-recipe` should
  show `type: platform` in the rendered output
- `goose run --recipe <path> --no-session` (with valid
  DEEPSEEK_API_KEY in env) should print welcome and OPEN a session
- Full sub-recipe → sub-sub-recipe delegation must be tested in a
  real goose TUI (hermes-sandbox cannot pipe user input into the REPL)

## Files commonly affected
- Demo teams created by mas-engineer: `/tmp/<team>/recipe/*.yaml`
- Library: `/root/.config/goose/recipes/sub/sub_mas-*.yaml`
- Any user-authored recipe with orchestrator + sub_recipes

## Related but separate issue (NOT this fix)
Some orchestrators have a static `prompt:` block that does not read
`--params` passed via `goose run --params KEY=VALUE`. They re-ask
the user for input even when params were provided. Fix is
recipe-by-recipe prompt engineering. Out of scope for the
Issue 7355/7570 fix.
