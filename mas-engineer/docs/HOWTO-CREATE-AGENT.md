# How to create a single agent

This guide shows how to create a single sub-agent using MAS-Engineer's
`intention-parser`. The agent is registered automatically in the SOT
(`.state/workflows.yaml`) and the root orchestrator's `sub_recipes`.

## When to use

Use this for:

- One-off agents (no team).
- Agents with a single, clear role.
- Tools, scanners, validators, reporters.

Do not use this for:

- Multi-role teams. Use the team creation workflows instead
  (see [WORKFLOWS.md](WORKFLOWS.md)).

## How to invoke

Open a Goose session in the MAS-Engineer project and describe the agent in
plain language.

```bash
cd /tmp/mas-engineer/mas-engineer
goose session
```

Then describe your agent:

```text
"I need a JSON validator agent. It should read a JSON file from disk,
validate its schema against a configurable schema, and return a structured
report with all errors and warnings."
```

## What happens

1. `intention-parser` parses your description.
2. It detects agent type (sub, full, internal) and finds any workflow
   keywords.
3. It generates a plan with the agent name, file path, SOT entry, and
   `sub_recipes` entry.
4. It shows the plan (R01 confirmation).
5. After you confirm, the plan is applied: YAML file created, SOT updated,
   `sub_recipes` updated.
6. The agent is ready to use.

## Keywords you can use in the description

`intention-parser` recognizes several patterns:

| Pattern | Effect |
|---------|--------|
| "I need an agent that..." | sub type (default) |
| "Create an autonomous agent" | full type |
| "Build a function into existing agent" | internal type |
| "update/refresh agent {name}" | --refresh --agent {name} |
| "update all agents" | --refresh-all |
| "show what is missing" | --dry-run |
| "what has changed" | --diff |
| "may NOT..." | restrictions.forbidden_paths |
| "should ONLY..." | restrictions.allowed_paths |
| "first X, then Y" | workflow.steps |
| "on error cancel" | on_error: abort |

## Restrictions

You can constrain an agent by listing what it may and may not do. The
restrictions are written into the agent's YAML as `restrictions:` fields.

Example:

```text
"I need a log-reader agent. It should ONLY read files in /var/log/.
It may NOT modify any file. It should NOT execute any commands."
```

This produces a YAML like:

```yaml
restrictions:
  allowed_paths:
    - /var/log/
  forbidden_paths:
    - **
  forbidden_actions:
    - modify
    - execute
```

## Workflow steps

If your agent needs a fixed order of operations, describe them as steps:

```text
"I need a deployment agent. First, validate the manifest. Then, check
the cluster health. Then, apply the deployment. Then, verify the rollout.
On error cancel the deployment."
```

This produces a `workflow.steps:` list in the YAML, and an `on_error: abort`
policy.

## Agent types

There are three agent types. `intention-parser` picks the type from your
description, or you can specify it explicitly.

| Type | When to use | Example |
|------|-------------|---------|
| sub | Default. A regular sub-agent under the root orchestrator. | "I need a JSON validator" |
| full | A standalone, autonomous agent (no parent orchestrator). | "Create an autonomous agent" |
| internal | A function or feature to add to an existing agent. | "Add a schema-validate function to the JSON utility agent" |

## Refreshing an existing agent

If you want to update an existing agent's description, settings, or
restrictions, mention its name in the description:

```text
"Update the json-utility agent. It should now also support YAML files."
```

Or use the explicit form:

```text
"--refresh --agent json-utility"
```

The current state of the agent is shown in a diff so you can see what
changes.

## Dry run

To see what `intention-parser` would do without applying changes, use:

```text
"--dry-run"
```

This prints the plan but does not write any file.

## Where the agent ends up

A new agent is created as a YAML file in `recipe/sub/`:

```text
recipe/sub/sub_mas-<agent-name>.yaml
```

It is also registered in two places:

- `.state/workflows.yaml` -> `agents.<agent-name>`
- `recipe/dev-mas-engineer.yaml` -> `sub_recipes`

## See also

- [WORKFLOWS.md](WORKFLOWS.md) - For multi-agent teams.
- [HOWTO-IM-PIPELINE.md](HOWTO-IM-PIPELINE.md) - For improving existing code.
- [recipe/instructions/sub_mas-intention-parser.md](../recipe/instructions/sub_mas-intention-parser.md) - Full intention-parser specification.
