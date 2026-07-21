# Are MAS-Engineer-created teams standalone-runnable?

Short answer: **Partially, but not without the MAS-Engineer framework.**
The created teams are **shells**, not independent runnable systems. This
document explains what works without MAS-Engineer, what does not, and why.

## What a MAS-Engineer team looks like

When you ask MAS-Engineer to "build a sales team" with the AUTO-SPLIT
workflow, you get a set of YAML files. Each agent file contains:

- A role description (who I am, what I do).
- Domain boundaries (what I will NOT do).
- A tool inventory (what I CAN do: load, delegate, shell, file-IO, ...).
- An input/output schema (HANDOVER signal in, DONE/BLOCKED/ERROR out).
- A delegation map (which keywords trigger which sub-agent).

The orchestrator (for example, `sub_mas-sales-director.yaml`) has a
`sub_recipes` list that points to each specialist.

## What a team has

A created team has:

- 1 root YAML (orchestrator or coordinator) with `sub_recipes`.
- N sub-agent YAMLs, each with role + tool inventory + I/O schema.
- N workflow entries (defined in the parent MAS-Engineer SOT).
- N SOT entries (`agents.<name>` in `.state/workflows.yaml`).

## What a team does NOT have

A created team does **NOT** have:

- Its own SOT file. The SOT lives in MAS-Engineer's
  `.state/workflows.yaml`. Take the team out of MAS-Engineer and the
  workflow routing has no place to live.
- Its own orchestrator process. The team has no `dev-<domain>` root
  recipe. The MAS-Engineer root (`dev-mas-engineer.yaml`) is what
  invokes the team via `sub_recipes`.
- Its own knowledge base. The teams I built reference MAS-Engineer
  knowledge files (for example, `.state/knowledge/05-rules.md`).
- Its own state tracking. There is no `.state/` in the team directory.

## What works without MAS-Engineer

If you copy the team's YAML files to a different project, you can:

- Read each agent's role and tool inventory.
- See the delegation map (which keywords trigger which sub-agent).
- Inspect the input/output schema for each agent.
- Adapt the YAML files into a standalone Goose recipe set.

What breaks immediately:

- SOT references like `SOT: workflows.yaml — agents.<name>.task_workflows`
  point to a SOT that no longer exists.
- Tool inventory entries like `✅ HAS: load (load knowledge)` reference
  MAS-Engineer's `.state/knowledge/` directory.
- The `summon` extension (delegate to sub-agent) requires the parent
  MAS-Engineer to be running.
- The `dev_rule_checker` invocation in the prompt has no
  `tools/dev_rule_checker.py` to call.

## Why MAS-Engineer keeps the SOT central

Centralized SOT is a design choice, not a limitation. It means:

- One place to add or remove agents. No per-team SOTs to keep in sync.
- One audit trail. Every team's actions are logged in
  `.state/audit.log.jsonl`.
- One rule source. R01 (confirmation), R09 (domain), R10
  (coronashield) are defined once, not per team.
- One health report. `health-reporter` sees all teams at once.
- One pre-push validator. No per-team pre-push hooks.

The trade-off is that teams are not standalone-runnable. If you need a
standalone team, you must bootstrap a new project with the
`sub_mas-generic-init` agent and `INIT` task. That process creates a
new SOT, knowledge base, and orchestrator for the new project. See
[HOWTO-CREATE-AGENT.md](HOWTO-CREATE-AGENT.md) for the team creation
flow.

## Two paths to a runnable system

### Path 1: Stay inside MAS-Engineer (default)

The team is created in MAS-Engineer's `recipe/sub/` directory. You invoke
it through the MAS-Engineer root:

```bash
cd /tmp/mas-engineer/mas-engineer
goose run --recipe recipe/dev-mas-engineer.yaml
```

Tell the root: "ask the sales team to qualify this list of prospects."
The root delegates to `sub_mas-sales-director.yaml`, which delegates to
the specialists. All SOT, audit, and knowledge lookups work because the
parent MAS-Engineer is running.

### Path 2: Bootstrap a new project (standalone)

If you want the team to run outside MAS-Engineer, run
`sub_mas-generic-init` with task `INIT` and project name `<your-project>`.
This creates a new project directory with:

- Its own SOT (`.state/workflows.yaml`).
- Its own knowledge base (`.state/knowledge/`).
- Its own orchestrator (`recipe/dev-<project>.yaml`).
- Its own pre-push validator and health reporter.
- A copy of the team's agents under `recipe/sub/`.

The new project is fully standalone. MAS-Engineer is not needed at
runtime.

## What the cleanup commit changed

The cleanup commit (`b9ceac4`) removed test-team artifacts: the
`sub_mas-sales-*` and `sub_mas-marketing-*` YAML files, plus their SOT
entries and `sub_recipes` entries. These files were test outputs from
the E2E test runs. They were not framework components.

The MAS-Engineer framework (root orchestrator, all 52 framework
sub-agents, intention-parser, generic-init, improver) was kept. The
team-creation workflow itself (intention-parser detects
`(interactive)` vs `(auto)`, generic-init handles
`CREATE_TEAM_SHELL`) is framework code and is still in the repo.

## ⚠️ Critical: sub_recipes loads sub-recipes as separate sessions, NOT in-session tools

A common misconception is that `sub_recipes` entries are available as
in-session callable tools (like MCP tools). **This is incorrect.**

### How sub_recipes actually works

Goose's `sub_recipes` field loads each entry as a **separate runnable
recipe** accessible via the `load`/`delegate` mechanism (via the `summon`
extension). When an orchestrator calls `load(source: "specialist")`, Goose
spawns a **new sub-agent session** for that specialist. The specialist
runs in its own session context, with its own prompt, instructions, and
settings.

This means:
- Sub-recipes are **NOT** available as in-session tool calls (like MCP tools).
- Each sub-agent invocation creates a **separate goose session**.
- The orchestrator communicates with specialists via the `load`/`delegate`
  interface, not via direct function calls.
- Sub-recipes listed in `sub_recipes` appear in the `load`/`delegate`
  source list automatically.

### What this means for orchestrator recipes

Orchestrator recipes (e.g., `sales-orchestrator.yaml`) MUST:

1. **Have the `summon` extension listed** in their `extensions:` field:
   ```yaml
   extensions:
     - name: summon
       type: platform
   ```
   Without this, the `load`/`delegate` tool is unavailable. Goose
   documentation states: *"If Recipe extensions: defined, must summon
   explicitly be listed, else no delegate/load tool available."*

2. **Use `load` (not `delegate`)** in their prompts and instructions
   to invoke specialist agents. The `load` function spawns a sub-agent
   session for the named sub-recipe.

3. **Understand that each specialist runs in its own session** — there
   is no shared state between the orchestrator and specialists beyond
   what is passed via the `load` call parameters.

### Why this design

This design is intentional in Goose:
- Each sub-agent gets its own isolated execution context.
- Sub-agents can have different models, providers, and settings.
- Parallel execution is supported via `async: true` in load calls.
- The orchestrator remains lightweight — it coordinates, not executes.

### Common pitfalls

| Pitfall | Consequence | Fix |
|---------|-------------|-----|
| Missing `summon` extension | `load`/`delegate` tool unavailable | Add `extensions: [{name: summon, type: platform}]` |
| Using `delegate` instead of `load` | Confusion about mechanism | Use `load` for sub_recipes entries |
| Expecting in-session tool calls | Orchestrator cannot call specialists directly | Use `load` to spawn sub-agent sessions |
| No `async: true` for parallel | Specialists run sequentially | Add `async: true` to parallel load calls |

## Summary

- MAS-Engineer-created teams are **not standalone** by design. They
  depend on the parent MAS-Engineer's SOT, knowledge, and orchestrator.
- This is intentional. It gives central governance, single audit
  trail, and one rule source.
- To make a team standalone, bootstrap a new project with
  `sub_mas-generic-init` and task `INIT`. That creates everything the
  team needs.
- The cleanup commit removed test-team artifacts only. The team-creation
  framework code is still present and fully functional.
