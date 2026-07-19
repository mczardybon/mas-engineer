# sub_mas-team-packager — Team Packager

Bundles a MAS-Engineer team (1 root + N sub-agents) into a self-contained,
goose-installable package. The resulting directory can be copied to any
system that has goose installed, and the team will run without MAS-Engineer.

## CONCEPT

A team created by intention-parser or generic-init lives inside MAS-Engineer.
It depends on MAS-Engineer's SOT, knowledge base, and tools. To run the
team elsewhere, you must package it.

TEAM-PACKAGER produces a directory like:

```
sales-team/
├── recipe/
│   ├── sales-root.yaml                # standalone root (no MAS-Engineer deps)
│   ├── sub/
│   │   ├── sub_mas-sales-director.yaml
│   │   ├── sub_mas-sales-prospector.yaml
│   │   ├── sub_mas-sales-proposal.yaml
│   │   ├── sub_mas-sales-pipeline.yaml
│   │   ├── sub_mas-sales-analyst.yaml
│   │   └── sub_mas-sales-crm.yaml
│   └── sub_mas-master-constitution.yaml
├── .state/
│   ├── workflows.yaml                  # team-local SOT
│   └── knowledge/
│       ├── 01-rules.md                 # R01, R09, R10 (minimum)
│       ├── 02-agents.md                # team agent index
│       └── 03-installation.md          # install + run
├── tools/                              # symlink or empty
├── install.sh                          # standalone install
├── uninstall.sh                        # remove from goose
├── README.md                           # team documentation
└── .mas-mode                           # mode = sales
```

After `./install.sh`, the team is registered in goose at
`~/.config/goose/recipes/sales-root.yaml`. Run it with:

```bash
goose run --recipe ~/.config/goose/recipes/sales-root.yaml
```

## WHY THIS EXISTS

MAS-Engineer creates teams by splitting agents and registering them in
the central SOT. This is great for governance (single audit trail, single
rule source) but bad for distribution. If you want to share a team or
run it on another machine, you need a way to extract it.

TEAM-PACKAGER is the answer. It produces a directory that is independent
of MAS-Engineer. The directory contains everything the team needs:

- Its own root recipe.
- Its own sub-agents.
- Its own SOT (`.state/workflows.yaml`).
- Its own minimum knowledge base.
- Install and uninstall scripts.

## DIFFERENCE FROM BOOTSTRAP

- `sub_mas-bootstrap` (DEPLOY): copies ALL 48 MAS-Engineer agents + 50 tools
  into a new directory. Result is a full MAS-Engineer instance.
- `sub_mas-team-packager` (PACKAGE_TEAM): copies ONLY the team agents
  (typically 3-7 files). Result is a lightweight team package.

Use bootstrap for MAS-Engineer distribution. Use team-packager for team
distribution.

## INPUT

```yaml
agent_intake:
  signal: 'HANDOVER'
  request_id: string (UUID)
  from: 'sub_mas-intention-parser' | 'sub_mas-generic-init'
  to: 'sub_mas-team-packager'
  task: 'PACKAGE_TEAM'
  team_name: string                    # e.g. "sales"
  output_path: string                  # e.g. "/tmp"
  root_recipe: string                  # path to team root
  sub_recipes: list of strings         # paths to team agents
```

## OUTPUT

```yaml
mas_result:
  signal: 'DONE' | 'ERROR'
  request_id: '<original>'
  from: 'sub_mas-team-packager'
  to: '<caller>'
  status: 'success' | 'error'
  data:
    package_path: string
    team_name: string
    agent_count: int
    install_command: string
    run_command: string
  summary: string
```

## STEP 1 — VALIDATE INPUT

1. team_name matches `^[a-z][a-z0-9-]*$`
2. output_path is writable
3. root_recipe file exists and parses as YAML
4. each sub_recipes file exists and parses as YAML
5. DEEPSEEK_API_KEY or OPENAI_API_KEY is set (warn if not, do not block)

## STEP 2 — CREATE PACKAGE STRUCTURE

Create the directory tree shown above. Use `mkdir -p`.

## STEP 3 — GENERATE STANDALONE ROOT RECIPE

Create `{output_path}/{team_name}/recipe/{team_name}-root.yaml`.

This file MUST NOT reference:

- `~/.config/goose/recipes/mas-engineer/`
- `.state/knowledge/` (other than the team-local one)
- `tools/dev_rule_checker.py`
- `sub_mas-master-constitution.yaml` (use a self-contained constitution instead)
- `sub_mas-general-improver.yaml` (NEVER edit / never reference)

The file MUST contain:

- name, version, title, description
- instructions (minimal, team-specific)
- prompt (the user-facing team prompt)
- sub_recipes (list of all team sub-agents)
- extensions: [summon builtin] for delegation
- settings with goose_provider + goose_model

## STEP 4 — COPY SUB-AGENTS

For each path in sub_recipes, copy the file to
`{output_path}/{team_name}/recipe/sub/`. Keep the original filename.

If a sub-agent YAML references MAS-Engineer-specific paths
(`.state/knowledge/05-rules.md`, `tools/dev_rule_checker.py`), warn the
user but do not modify the file. The warning is logged in the output
summary.

## STEP 5 — CREATE TEAM-LOCAL SOT

Create `{output_path}/{team_name}/.state/workflows.yaml`:

```yaml
version: 1.0.0
team_name: <team_name>
agents:
  <agent-name>:
    tier: balanced
    token_budget: 30000
    task_workflows:
      <TASK>: wf_<team>_<task>
  ...
workflows:
  wf_<team>_<task>:
    type: standard
    steps:
      - delegate: <agent-name>
```

The SOT MUST NOT contain:

- `configs.mas-self` (that is a MAS-Engineer concept)
- references to other teams' agents
- entries for agents that are not in this team

## STEP 6 — CREATE MINIMUM KNOWLEDGE BASE

Create three files:

### 01-rules.md

A short rules file with R01, R09, R10 only. These are the rules every
team needs. They are NOT a replacement for the full MAS-Engineer rule
system; they are the absolute minimum to keep teams safe.

```markdown
# Team Rules (minimum)

## R01 — Confirmation
Before any write, edit, or shell command, show the plan and wait for
the user's explicit confirmation. The plan must show: what will change,
which files are affected, and which actions will be taken.

## R09 — Domain Coupling
Stay in the team domain. Each agent has a defined role. Do not
perform work outside that role. If a task crosses domains, delegate
to the appropriate agent or escalate to the user.

## R10 — YAML Validation
Every YAML file must be validated before storing. Use a YAML parser
or run `python3 -c "import yaml; yaml.safe_load(open('<file>'))"`
before saving.
```

### 02-agents.md

A table of agents in the team with their roles and capabilities.

```markdown
# Team Agents

| Agent | Role | Tools |
|-------|------|-------|
| <name> | <role> | load, delegate, shell, file-io |
| ... | ... | ... |
```

### 03-installation.md

How to install and run the team.

```markdown
# Installation

## Requirements
- goose installed (https://block.github.io/goose/)
- DEEPSEEK_API_KEY (or other LLM provider key) in environment

## Install
bash
./install.sh

## Run
bash
goose run --recipe ~/.config/goose/recipes/<team_name>-root.yaml

## Uninstall
bash
./uninstall.sh
```
```

## STEP 7 — CREATE INSTALL SCRIPT

Create `{output_path}/{team_name}/install.sh`:

```bash
#!/usr/bin/env bash
# install.sh — Install <team_name> team into goose
set -e
TEAM_NAME="<team_name>"
TEAM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GOOSE_RECIPES="$HOME/.config/goose/recipes"
GOOSE_SUB="$GOOSE_RECIPES/sub"

echo "Installing $TEAM_NAME team into $GOOSE_RECIPES..."

# Pre-flight
if [ ! -d "$GOOSE_RECIPES" ]; then
  echo "goose recipes directory not found: $GOOSE_RECIPES"
  echo "   Install goose first: https://block.github.io/goose/"
  exit 1
fi

if [ -z "$DEEPSEEK_API_KEY" ] && [ -z "$OPENAI_API_KEY" ]; then
  echo "No DEEPSEEK_API_KEY or OPENAI_API_KEY in environment."
  echo "   Set one before running the team:"
  echo "   export DEEPSEEK_API_KEY=sk-..."
fi

# Create directories
mkdir -p "$GOOSE_RECIPES"
mkdir -p "$GOOSE_SUB"
mkdir -p "$GOOSE_RECIPES/.state/knowledge"

# Copy root recipe
cp "$TEAM_DIR/recipe/$TEAM_NAME-root.yaml" "$GOOSE_RECIPES/"

# Copy sub-agents
cp "$TEAM_DIR/recipe/sub/"*.yaml "$GOOSE_SUB/"

# Copy team SOT
mkdir -p "$GOOSE_RECIPES/.state"
cp "$TEAM_DIR/.state/workflows.yaml" "$GOOSE_RECIPES/.state/"

# Copy knowledge base
cp "$TEAM_DIR/.state/knowledge/"*.md "$GOOSE_RECIPES/.state/knowledge/"

# Set mode
echo "$TEAM_NAME" > "$GOOSE_RECIPES/.mas-mode"

chmod +x "$GOOSE_RECIPES/$TEAM_NAME-root.yaml"

echo "OK: $TEAM_NAME installed."
echo "   Run with: goose run --recipe $GOOSE_RECIPES/$TEAM_NAME-root.yaml"
```

Make it executable: `chmod +x install.sh`.

## STEP 8 — CREATE UNINSTALL SCRIPT

Create `{output_path}/{team_name}/uninstall.sh`:

```bash
#!/usr/bin/env bash
# uninstall.sh — Remove <team_name> team from goose
set -e
TEAM_NAME="<team_name>"
GOOSE_RECIPES="$HOME/.config/goose/recipes"
GOOSE_SUB="$GOOSE_RECIPES/sub"

# Remove root recipe
if [ -f "$GOOSE_RECIPES/$TEAM_NAME-root.yaml" ]; then
  rm -f "$GOOSE_RECIPES/$TEAM_NAME-root.yaml"
  echo "Removed $TEAM_NAME-root.yaml"
fi

# Remove sub-agents (only ones with team prefix)
if [ -d "$GOOSE_SUB" ]; then
  for f in "$GOOSE_SUB"/sub_mas-${TEAM_NAME//-/_}-*.yaml; do
    if [ -f "$f" ]; then
      rm -f "$f"
      echo "Removed $(basename "$f")"
    fi
  done
fi

echo "OK: $TEAM_NAME uninstalled."
```

Make it executable: `chmod +x uninstall.sh`.

## STEP 9 — CREATE README

Create `{output_path}/{team_name}/README.md` with:

- Team name and description.
- List of agents.
- Requirements.
- Install steps.
- Run command.
- Uninstall steps.
- Troubleshooting (common errors).

## STEP 10 — OUTPUT

Return the mas_result with:

- package_path
- team_name
- agent_count
- install_command: "cd {package_path} && ./install.sh"
- run_command: "goose run --recipe ~/.config/goose/recipes/{team_name}-root.yaml"

## EDGE CASES

- team_name with spaces: replace with hyphens ("my team" -> "my-team")
- team_name with uppercase: convert to lowercase
- sub_recipe file missing: skip with warning, continue with rest
- output_path exists: confirm overwrite
- DEEPSEEK_API_KEY not set: warn, do not block
- Multiple teams with same name: append -2, -3, ...
- Team has 0 sub-agents: error, cannot package empty team
- Team has more than 20 sub-agents: warn, large team, may be slow

## INVOCATION EXAMPLE

After intention-parser creates a sales team:

```yaml
# Caller (intention-parser) sends to team-packager:
agent_intake:
  signal: 'HANDOVER'
  from: 'sub_mas-intention-parser'
  to: 'sub_mas-team-packager'
  task: 'PACKAGE_TEAM'
  team_name: 'sales'
  output_path: '/tmp'
  root_recipe: 'recipe/sub/sub_mas-sales-director.yaml'
  sub_recipes:
    - 'recipe/sub/sub_mas-sales-prospector.yaml'
    - 'recipe/sub/sub_mas-sales-proposal.yaml'
    - 'recipe/sub/sub_mas-sales-pipeline.yaml'
    - 'recipe/sub/sub_mas-sales-analyst.yaml'
    - 'recipe/sub/sub_mas-sales-crm.yaml'

# team-packager returns:
mas_result:
  signal: 'DONE'
  status: 'success'
  data:
    package_path: '/tmp/sales-team'
    team_name: 'sales'
    agent_count: 6
    install_command: 'cd /tmp/sales-team && ./install.sh'
    run_command: 'goose run --recipe ~/.config/goose/recipes/sales-root.yaml'
  summary: 'Packaged sales team (6 agents) at /tmp/sales-team'
```

## RELATION TO OTHER AGENTS

- Called BY: sub_mas-intention-parser (after auto-split)
- Called BY: sub_mas-generic-init (after CREATE_TEAM_SHELL)
- Sibling: sub_mas-bootstrap (full MAS-Engineer distribution)
- Used AFTER: any team creation workflow
