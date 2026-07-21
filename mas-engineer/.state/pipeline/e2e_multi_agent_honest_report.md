# E2E Multi-Agent Honest Report — 2026-07-21

## Test Setup

Three real Goose 1.43.0 runs with the patched mas-engineer (commit 94a4fbc, after IM-002 P-F010).

| Run | Recipe | Goal | Result |
|-----|--------|------|--------|
| v2 | sub_mas-im-finder | Fresh scan, expect 93 findings, R11 consultation | 93 findings, 1 delegate-call attempted |
| v3 | sub_mas-goose-expert | Independent goose-expert run with concrete intake | Recursion-guard triggered, asked for intent |
| v4 | sub_mas-general-improver | Full 5-stage improvement cycle | Recursion-guard + asked for intent |
| v5 | sub_mas-im-finder | Direct summoning of goose-expert for JJ1 verification | 304 findings, 1 delegate-call attempted, run timed out |

## What Worked (Positive Evidence)

### 1. `summon` extension is now functional in all 53 sub-agent recipes
- All 53 recipes render with `extensions: - type: platform, name: summon`
- Pre-IM-002: 28/53 had summon (only IM-001 round 1 fixes)
- Post-IM-002: 53/53 have summon (verified via `goose run --recipe ... --render-recipe`)

### 2. `delegate` tool is now available and called
- v2 line 2521: `▸ delegate source: sub_mas-goose-expert, max_turns: 5`
- v5 line 4298: `▸ delegate source: sub_mas-goose-expert, extensions: developer`
- Pre-IM-002: delegate tool was not in the agent's tool list (silent fail per skill `goose-recipe-summon-platform-extension`)

### 3. im-finder detects and reports R11 compliance
- v5 detected 304 findings across 28 types
- 119 findings have `goose_verdict` field (carried over from IM-002 verdicts)
- For new finding types, agent attempted delegate-call to goose-expert

## What Did NOT Work (Honest Findings)

### 1. delegate tool does not return usable sub-agent responses
- v2: `▸ delegate` -> Goose response: "The goose-expert subagent isn't available as a named source"
- v5: `▸ delegate` -> No visible response in log, agent falls back to `cat recipe/sub/sub_mas-goose-expert.yaml`

### 2. Only 1/53 recipes has a working `sub_recipes` block
- sub_mas-team-packager.yaml has `sub_recipes: []` (empty array)
- All other 52 recipes have NO `sub_recipes` block
- Goose `delegate` tool requires `sub_recipes` or known agent registry to resolve names

### 3. The 118+ CONFORM verdicts from IM-002 are carried over via findings.yaml
- This is technically a caching/lookup, NOT a real goose-expert consultation
- v2 explicitly said: "all previous verdicts were CONFORM... can reuse existing verdicts"
- This means R11 was satisfied by file lookup, not by real multi-agent invocation

## Root Cause

`delegate` in Goose 1.43.0 requires the target sub-agent to be discoverable via:
- (a) `sub_recipes:` block in the parent recipe, OR
- (b) a registered agent in the goose session (e.g. `~/.config/goose/agents/`)

The mas-engineer recipes define `summon` extension but do NOT register the sub-agents
in any of these locations. Therefore `delegate` fails silently, and agents fall back
to reading the recipe file as text.

## Evidence Files

- /workspace/h-logs/e2e-multi-agent-full.log  (v2: 2897 lines)
- /workspace/h-logs/e2e-goose-expert.log     (v3: independent goose-expert run)
- /workspace/h-logs/e2e-full-cycle.log        (v4: general-improver full cycle)
- /workspace/h-logs/e2e-v4.log                (v5: 304 findings, timed out at 240s)

## Recommended Next Steps (not in scope for this round)

1. Add `sub_recipes:` blocks to the 8 pipeline-coordinator recipes
   (im-finder, im-rank, im-designer, im-validator, general-improver, etc.)
   declaring their known sub-agents explicitly.
2. OR register the 53 sub-agents in `~/.config/goose/agents/` so
   `delegate` can resolve them by name.
3. After (1) or (2), re-run the e2e test and verify delegate-call returns
   a real `mas_result` block instead of silent failure.

## Bottom Line

**The IM-002 P-F010 fix (adding `summon` extension to all 53 agents) is a
necessary precondition for multi-agent operation, but it is NOT sufficient.**

The `delegate` tool now appears in the agent's tool list, and the agent
attempts the call. But the call silently fails because no recipe declares
the sub-agents in a way Goose 1.43.0 can resolve them.

This is a real architectural gap that needs the `sub_recipes` fix in a
follow-up round (proposed: IM-003 P-F011).
