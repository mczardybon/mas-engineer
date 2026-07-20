# How to run the IM-Pipeline

The IM-Pipeline (Improvement Pipeline) is MAS-Engineer's 7-stage workflow for
finding, ranking, designing, validating, and applying improvements to a
codebase. This guide shows when to use it, how to trigger it, and what to
expect at each stage.

> **Note:** The pipeline has 7 core stages (FIND→RANK→DESIGN→IMPLEMENT→VALIDATE→SUMMARIZE→PUSH), plus STEP 0 (Prerequisites) and STEP 8 (Push).

## When to use

Use the IM-Pipeline when you want to:

- Find improvement opportunities in a codebase.
- Prioritize them by impact.
- Design patches automatically.
- Validate that patches do not break anything.
- Apply the patches to your code.

Do not use the IM-Pipeline when:

- You already know what to change. Just make the change by hand.
- You want a single new agent. Use `intention-parser` instead.
- You want a multi-agent team. Use the team creation workflows.

## How to invoke

Open a Goose session and describe the improvement you want. The
improvement-pipeline coordinator picks up the request.

```bash
cd ~/mas-engineer/mas-engineer
goose session
```

Then describe the target:

```text
"Run the IM-pipeline on this project. Focus on the dev-mas-engineer
orchestrator. Find any duplication or missing documentation."
```

## The 7 stages

The IM-Pipeline runs the following stages in order:

1. **FIND**: `im-finder` scans the target area and writes findings to
   `.state/pipeline/findings.yaml`. Each finding has an id, type, location,
   and severity.

2. **RANK**: `im-rank` reads the findings and produces
   `.state/pipeline/ranked_findings.yaml`. Findings are sorted by severity
   and impact.

3. **DESIGN**: `im-designer` reads the ranked findings and produces
   `.state/pipeline/patches.yaml`. Each patch has a target file, old string,
   and new string.

4. **IMPLEMENT**: The patches are applied to the codebase.

5. **VALIDATE**: `im-validator` checks that the patches are correct, that
   the YAML files parse, and that the SOT is consistent. Results go to
   `.state/pipeline/validation.yaml`.

6. **SUMMARIZE**: The user sees a summary of changes and a diff. R01
   confirmation is requested.

7. **PUSH**: After confirmation, the changes are committed and pushed to
   the repository.

## Common invocation patterns

### Full improvement run

```text
"Run the IM-pipeline on the dev-mas-engineer orchestrator."
```

This runs the full 7-stage pipeline. Use it when you want a broad
improvement pass.

### Targeted improvement

```text
"Run the IM-pipeline on recipe/instructions/sub_mas-im-finder.md.
Focus on missing edge-case handling."
```

This scopes the FIND stage to a specific file. Useful when you already
know where the issue is.

### Cost analysis

```text
"Run the IM-pipeline with task=COST_ANALYSIS on this project."
```

This skips the DESIGN and IMPLEMENT stages. It only analyzes the cost
(token usage, runtime) of each agent and produces a report.

### Error pattern analysis

```text
"Run the IM-pipeline with task=ERROR_PATTERN on .state/audit.log.jsonl."
```

This finds recurring error patterns in the audit log and produces a
findings report. No patches are designed.

## NN types

Findings produced by `im-finder` have a type. The common types are:

| Type | Description |
|------|-------------|
| **NN1** | Multi-role agent: a single agent does too many different things. |
| **NN2** | Tool overload: an agent uses too many tools. |
| **NN3** | Scope bloat: an agent handles too many domains. |
| **NN4** | Flagged for split: the agent has been marked by `intention-parser` for splitting into a team. |

NN1 to NN4 are typical for agents that should be split into a team. Other
types include DUPLICATION, MISSING_DOC, INCONSISTENT_STYLE, and
STALE_CODE.

## The split pattern

When `im-finder` produces an NN1, NN2, NN3, or NN4 finding, `im-designer`
applies the `split_into_orchestrator_and_subs` pattern:

1. The original agent is archived to `recipe/sub/legacy/`.
2. One orchestrator is created: `sub_mas-<domain>-director.yaml`.
3. N specialized sub-agents are created: `sub_mas-<domain>-<role>.yaml`.
4. The SOT and `sub_recipes` are updated.
5. The original agent is removed from the active list.

This is the same pattern that the team creation AUTO-SPLIT workflow uses.
The IM-Pipeline does it for existing agents; the team creation workflow
does it for new ones.

## SOT and sub_recipes

After the IM-Pipeline runs:

- `.state/workflows.yaml` has the new agent entries and workflow definitions.
- `recipe/dev-mas-engineer.yaml` has the new `sub_recipes` entries.
- The original agent is archived (not deleted) under
  `recipe/sub/legacy/`.

You can always revert by restoring the archived file and removing the
SOT / `sub_recipes` entries.

## Confirming the changes

The IM-Pipeline never pushes changes to your repository without your
confirmation. After the VALIDATE stage, the SUMMARIZE stage shows you
the diff and asks for R01 confirmation. Only after you say yes are the
changes committed and pushed.

To skip the confirmation step (for fully autonomous runs), set
`auto_commit: true` in the invocation. This is only recommended in trusted
environments.

## Pre-push validation

Before any commit, the `pre-push-validator` agent runs all critical checks:

- No secrets in tracked files.
- All YAML files parse.
- The SOT is consistent with `sub_recipes`.
- The constitution rules are satisfied.

If the pre-push-validator reports any blocking findings, the push is
aborted and the findings are shown to you.

## See also

- [WORKFLOWS.md](WORKFLOWS.md) - Team creation workflows.
- [HOWTO-CREATE-AGENT.md](HOWTO-CREATE-AGENT.md) - Single agent creation.
- [recipe/instructions/sub_mas-general-improver.md](../recipe/instructions/sub_mas-general-improver.md) - Full improver specification.
- [docs/procedures.md](procedures.md) - Standard operating procedures.
