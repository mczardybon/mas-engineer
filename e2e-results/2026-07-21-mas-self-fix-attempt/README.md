# E2E test — mas-engineer self-improvement attempt

**Date:** 2026-07-21
**Goal:** Have mas-engineer fix the 2 real bugs it found in the e2e test
(`e2e-results/2026-07-21-mas-e2e-full/README.md`)

**Result:** mas-engineer **could not fix itself autonomously**. This is a
legitimate, transparent finding — not a failure to try. The evidence below
shows exactly what happened, why, and what a human operator would need to do.

## What was attempted

Three separate `goose run` invocations of the `sub_mas-general-improver`
recipe, each with progressively more explicit instructions. All three ran
to completion. None made any filesystem changes.

| Attempt | Input | Outcome |
|---------|-------|---------|
| v1 | "Improve the 2 bugs" | Asked "How would you like to proceed?" — 5 menu options |
| v2 | Detailed YAML intake with explicit paths | Acknowledged bugs, asked for prioritization |
| v3 | "Just write a self-analysis report, no fixes" | Confirmed it has only `delegate` + `load` tools |

## Why mas-engineer could not fix itself

Verbatim from the v3 log (lines 30-50):

> "I have `delegate` and `load` — that's it. No shell, no file read/write."
>
> "I see the challenge — none of the subagents in this session have
> filesystem access tools."
>
> "The external instructions file `recipe/instructions/sub_mas-general-improver.md`
> is not available in this session. It's referenced in the recipe configuration
> but hasn't been loaded into the source system."

This is the very Bug B from the e2e test — the sub-agents have no
filesystem tools. The general-improver needs to delegate to agents that
can write files, but those agents also have no write tools. The
im-* agents referenced in the 7-stage pipeline either don't exist as
loadable sources, or also lack filesystem tools.

**In other words:** Bug B is the load-bearing constraint that prevents
the 7-stage pipeline from running. To fix Bug B, the pipeline would
need to run, but the pipeline needs Bug B fixed first. Classic chicken-
and-egg.

## What a human operator (or Hermes) must do instead

### Manual fix for Bug A: missing instruction file

Create `mas-engineer/recipe/instructions/sub_mas-self-auditor.md` with
the actual instructions, modeled on the pattern in
`mas-engineer/recipe/instructions/sub_mas-*.md` for other sub-agents.

### Manual fix for Bug B: sub-agents cannot write

Either:
- (a) Update the sub-agent recipes to be honest: "this agent emits
      its report as the LLM's final assistant message — it does not
      write to `.state/pipeline/` directly. A wrapper or human must
      capture and persist the report."
- (b) Add a "delegate to dev-mas-engineer" pattern in the sub-agents
      so they hand off the report to a tool-equipped orchestrator.

Option (a) is faster and more honest.

### The deeper architectural issue

The 7-stage improvement pipeline (`im-scanner`, `im-analyzer`,
`im-designer`, `im-reviewer`, `im-implementer`, `im-tester`,
`im-verifier`) assumes each im-* agent has shell/write tools. They don't.
The pipeline cannot run end-to-end without this fix.

## Evidence

```
e2e-results/2026-07-21-mas-self-fix-attempt/
├── README.md
└── evidence/
    ├── 01-first-attempt-asks-for-input.log         12.5kB
    ├── 02-retry-with-paths-stuck.log                7.4kB
    └── 03-selfanalysis-no-shell-tools.log           5.1kB
```

Total: 25KB of real goose CLI output showing the exact prompts,
agent reasoning, and dead-ends.

## What I (Hermes) am doing next

Following the user instruction "ja" (yes, do it), I will:

1. **NOT pretend mas-engineer fixed itself.** It didn't.
2. **NOT silently fix the bugs on mas-engineer's behalf** — that would
   violate R04 (the rule that says only mas-engineer itself can improve
   mas-engineer) and would hide what actually happened.
3. **Pause here and inform the user** — they need to decide:
   - (A) Apply the manual fix anyway, accepting that the improvement
         came from Hermes, not mas-engineer.
   - (B) Modify the mas-engineer recipes to give im-* agents shell/write
         tools, then re-attempt the self-improvement.
   - (C) Acknowledge that mas-engineer is a documentation/orchestration
         layer, not a self-modifying system, and rename it accordingly.
   - (D) Treat the e2e test as the deliverable (which is already pushed
         in commit c96881f) and stop here.

## Why I am pausing

The user's last instruction was "ja" — yes to running mas-engineer's
self-improvement. I ran it three times. It could not complete the task
without human intervention. Silently completing it anyway would be
dishonest. The user gets to decide the next move.
