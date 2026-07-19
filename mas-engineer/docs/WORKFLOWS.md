# Workflow Selection Guide

MAS-Engineer supports two workflows for building multi-agent teams. This guide
explains when to use which, how to trigger each one, and what to expect from
the result.

## At a glance

| Workflow | Trigger | Result | When to use |
|----------|---------|--------|-------------|
| **AUTO-SPLIT** | no keyword or `(auto)` | 1 monolith agent, then auto-split into 1 orchestrator + N specialized sub-agents | You know the team's purpose and want it ready to use |
| **INTERACTIVE** | `(interactive)`, `(manual)`, `(shell)`, `(no-split)`, `(let me define)` | 1 coordinator + N generic sub-agents that ask "What should I do?" | You want to define each agent's role through conversation |

The default is AUTO-SPLIT. If you say nothing about a workflow, MAS-Engineer
chooses AUTO-SPLIT for you.

## AUTO-SPLIT workflow

The AUTO-SPLIT workflow is the default. It is best when you already know what
the team should do and you want a ready-to-use structure immediately.

### What happens

1. You describe the team (for example, "a customer-support team that handles
   tickets, escalates hard issues, and writes KB articles").
2. `intention-parser` reads the description and detects 3 or more distinct
   roles.
3. The agent is first created as a single monolith YAML file.
4. The improvement pipeline splits the monolith into one orchestrator and N
   specialized sub-agents, each with a clear role and a delegation map.
5. All sub-agents and workflows are registered in the SOT
   (`.state/workflows.yaml`) and in the `sub_recipes` list of the root
   orchestrator.

### Example

```text
"Build a customer-support team"
  -> AUTO-SPLIT runs

Result:
  - sub_mas-support-director.yaml          (orchestrator)
  - sub_mas-support-tickets.yaml           (specialist)
  - sub_mas-support-escalations.yaml       (specialist)
  - sub_mas-support-kb-writer.yaml         (specialist)
```

### Keywords

- (no keyword) -> AUTO-SPLIT (default)
- (auto) -> AUTO-SPLIT (explicit)

## INTERACTIVE workflow

The INTERACTIVE workflow is for users who want to shape the team step by
step. Each generic member starts as a blank slate and asks
"What should I do?". You then tell each member its specific role, and from
that point on the member responds in that role.

### What happens

1. You describe the team and add an INTERACTIVE keyword to the description.
2. `intention-parser` reads the keyword, skips the split pattern, and
   delegates to `generic-init` with the `CREATE_TEAM_SHELL` task.
3. `generic-init` creates one coordinator plus N generic sub-agents. Each
   generic member is registered in the SOT and in `sub_recipes`.
4. When you talk to a generic member, it asks what it should do. You define
   its role in conversation, and the member keeps that role for the rest of
   the session.

### Example

```text
"Build a customer-support team (interactive)"
  -> INTERACTIVE runs

Result:
  - sub_mas-support-coordinator.yaml       (delegates to members)
  - sub_mas-support-member-1.yaml         (generic, asks "What should I do?")
  - sub_mas-support-member-2.yaml         (generic, asks "What should I do?")
  - sub_mas-support-member-3.yaml         (generic, asks "What should I do?")

Conversation:
  "Member 1, you handle incoming tickets."
  "Member 2, you write KB articles."
  "Member 3, you escalate hard issues."
```

### Keywords

All of the following trigger the INTERACTIVE workflow:

- (interactive)
- (manual)
- (shell)
- (no-split)
- (let me define)

## When to use which

Use AUTO-SPLIT when:

- You already know the team's responsibilities.
- You want a ready-to-use team without further conversation.
- You trust the LLM to pick good roles.
- You want the SOT, delegation map, and pipelines set up automatically.

Use INTERACTIVE when:

- You are not sure yet which roles you need.
- You want to explore what each agent can do before committing.
- You want full control over each agent's role.
- You are learning how MAS-Engineer teams work.
- You want to test a team concept before fully specifying it.

## Switching workflows

You cannot mix workflows in a single request. If you started with AUTO-SPLIT
and want to convert a specialist into a generic member, or vice versa, you
have two options:

1. **Start over**: change the keyword in your description and run the team
   creation again. The new team is created alongside the old one.
2. **Edit by hand**: open the agent's YAML file and rewrite the
   `task:` and `prompt:` fields. Update the SOT entry in
   `.state/workflows.yaml` to match.

## Auto-hint

If you describe a team without a keyword, MAS-Engineer shows this hint in
the R01 plan before asking for confirmation:

```text
Available workflows for team creation:
  - AUTO-SPLIT (default) - ready-to-use team, auto-split into orchestrator + N specialists
  - INTERACTIVE - team shell, N generic agents, you define roles through conversation

Add keyword to description to switch:
  "build a marketing team (interactive)"   -> interactive shell
  "build a marketing team (auto)"          -> explicit auto-split
  "build a marketing team"                 -> auto-split (default)
```

This hint appears only when the description mentions a team, multi-role, or
multi-agent language. For single-agent requests, the hint is skipped.

## Summary

- Default: AUTO-SPLIT (ready-to-use team).
- Add `(interactive)`, `(manual)`, `(shell)`, `(no-split)`, or
  `(let me define)` for the INTERACTIVE shell workflow.
- Both workflows register agents in the SOT and `sub_recipes` correctly.
- Choose by how much you already know about the team's roles.
