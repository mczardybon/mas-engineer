# How to run the IM-Pipeline

The IM-Pipeline (Improvement Pipeline) is MAS-Engineer's 5-stage workflow for
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

## The 8 pipeline stages (S1-S8) + S0 prerequisites

The IM-Pipeline runs as an 8-stage orchestrator flow (`general-improver` dispatcher) with an optional S0 prerequisites check before it. Of those 8 stages, 5 are executed by dedicated `im-*` sub-agents (S1, S2, S3, S4, S6) and 3 by the general-improver dispatcher (S5 apply, S7 summary, S8 push):

1. **READ SESSION DATA** (im-session-reader, S1): Reads past Goose session history from the SQLite DB into `.mase/pipeline/session_data.yaml`. Feeds FIND in the next step.

2. **FIND** (im-finder, S2): Scans the target area and writes findings to
   `.mase/pipeline/findings.yaml`. Each finding has an id, type, location,
   and severity. Detects 53 documented optimization patterns (A-MM).

3. **RANK** (im-rank, S3): Reads the findings and produces
   `.mase/pipeline/ranked_findings.yaml`. Findings are sorted by severity
   and impact, with Article 1-6 constitution check.

4. **DESIGN** (im-designer, S4): Reads the ranked findings and produces
   `.mase/pipeline/patches.yaml`. Each patch has a target file, old string,
   and new string.

5. **IMPLEMENT** (dispatcher, S5): The user reviews patches; on approval
   `sub_mas-yaml-editor` (or `sub_mas-generic-init` for non-YAML targets)
   applies each patch with backup → edit → validate → rollback-on-fail.

6. **VALIDATE** (im-validator, S6): Checks that the patches are correct, that
   the YAML files parse, and that the SOT is consistent. Results go to
   `.mase/pipeline/validation.yaml`. May also call `sub_mas-prompt-engineer`
   (prompt score) and `sub_mas-agent-guardian` (drift check) for before/after
   comparison.

7. **SUMMARIZE** (dispatcher, S7): The user sees a summary of changes and a diff. R01
   confirmation is requested.

8. **PUSH** (dispatcher, S8): After confirmation, `PUSH_IMPROVEMENTS` task copies improvements to user projects
   (knowledge files, agent templates, SOT updates) and the changes are
   committed to git.

**S0 Prerequisites** (pre-pipeline, optional): mode detection, rule-hardness check, web-research prompt, recursion-guard. Only at FULL_IMPROVEMENT or REVIEW.

For the canonical stage-by-stage documentation (with all 53 pattern categories, rate limiting, and rollback semantics), see [`../../docs/improvement-pipeline.md`](../../docs/improvement-pipeline.md).

## Common invocation patterns

### Full improvement run

```text
"Run the IM-pipeline on the dev-mas-engineer orchestrator."
```

This runs the full 8-stage pipeline (S1-S8) with the `general-improver` dispatcher handling IMPLEMENT (S5) / SUMMARIZE (S7) / PUSH (S8) and the 5 dedicated `im-*` sub-agents running S1, S2, S3, S4, S6. Use it when you want a broad improvement pass.

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
"Run the IM-pipeline with task=ERROR_PATTERN on .mase/audit.log.jsonl."
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

- `.mase/workflows.yaml` has the new agent entries and workflow definitions.
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
