# How to package a team for standalone distribution

MAS-Engineer creates teams that depend on the parent MAS-Engineer
framework (SOT, knowledge base, tools). This guide shows how to
extract a team and make it run in any goose installation without
MAS-Engineer.

## Why this exists

By default, teams created by MAS-Engineer live inside the framework.
They share the central SOT, the knowledge base, and the tools. This
is good for governance, but it means the team cannot run elsewhere
without the framework.

The `sub_mas-team-packager` agent solves this. It bundles a team
(1 root + N sub-agents) into a directory that is self-contained.
The directory has everything the team needs: its own root recipe,
its own SOT, its own minimum knowledge base, and install/uninstall
scripts.

## When to use

Use this when you want to:

- Share a team with someone who has goose but not MAS-Engineer.
- Run a team on a server that does not have MAS-Engineer installed.
- Test a team in isolation.
- Distribute a team as a product.

Do NOT use this when:

- The team is part of MAS-Engineer and will stay in MAS-Engineer.
- You want to deploy MAS-Engineer itself. Use
  `sub_mas-bootstrap` (DEPLOY) instead.

## How to invoke

Inside a goose session with MAS-Engineer running:

```text
"Package the sales team for distribution. Output to /tmp."
```

The intention-parser detects the team name, then delegates to
`sub_mas-team-packager` with task `PACKAGE_TEAM`.

You can also call the agent directly:

```text
"Delegate to sub_mas-team-packager with task PACKAGE_TEAM,
team_name=sales, output_path=/tmp,
root_recipe=recipe/sub/sub_mas-sales-director.yaml,
sub_recipes=[list of paths]."
```

## What you get

After PACKAGE_TEAM runs, you have a directory like:

```
/tmp/sales-team/
├── recipe/
│   ├── sales-root.yaml                 # standalone root
│   ├── sub_mas-master-constitution-team.yaml
│   └── sub/
│       ├── sub_mas-sales-director.yaml
│       ├── sub_mas-sales-prospector.yaml
│       ├── sub_mas-sales-proposal.yaml
│       └── ... (one per agent)
├── .state/
│   ├── workflows.yaml                  # team-local SOT
│   └── knowledge/
│       ├── 01-rules.md                 # R01, R09, R10
│       ├── 02-agents.md                # team index
│       └── 03-installation.md          # install + run
├── install.sh                          # standalone install
├── uninstall.sh                        # remove from goose
├── README.md                           # team documentation
└── .mas-mode                           # mode = sales
```

## How to install

On the target system (the one without MAS-Engineer):

```bash
# 1. Copy the package to the target
scp -r /tmp/sales-team user@server:/opt/

# 2. SSH in and install
ssh user@server
cd /opt/sales-team
./install.sh
```

The install script copies:

- Root recipe to `~/.config/goose/recipes/sales-root.yaml`
- Sub-agents to `~/.config/goose/recipes/sub/`
- Team SOT to `~/.config/goose/recipes/.state/workflows.yaml`
- Knowledge base to `~/.config/goose/recipes/.state/knowledge/`
- Mode file to `~/.config/goose/recipes/.mas-mode`

## How to run

On the target system:

```bash
# Set provider key (DeepSeek recommended)
export DEEPSEEK_API_KEY=sk-...

# Run the team
goose run --recipe ~/.config/goose/recipes/sales-root.yaml
```

Then talk to the team as you would inside MAS-Engineer. The team
behaves identically because it has its own root recipe, SOT, and
knowledge base.

## How to uninstall

```bash
cd /opt/sales-team
./uninstall.sh
```

The uninstall script removes:

- Root recipe
- Sub-agents (only ones with the team prefix)
- Optionally: SOT entries for the team

## What is preserved

The packaged team has everything it needs to run. Specifically:

- The root recipe is a standalone goose recipe. It does NOT depend
  on MAS-Engineer.
- The SOT is team-local. The team does NOT need MAS-Engineer's SOT.
- The knowledge base has R01, R09, R10 (the minimum rules). The
  team does NOT need MAS-Engineer's 11 hard rules.
- The constitution is team-local. The team does NOT need the full
  MAS-Engineer constitution.

## What is NOT preserved

The packaged team does NOT have:

- All 23 MAS-Engineer rules. Only R01, R09, R10 are included.
- The full 9-file knowledge base. Only 3 files are included.
- The MAS-Engineer tools (health-reporter, pre-push-validator, etc.).
- The MCP dashboard server.
- The audit log infrastructure.

If the team needs MAS-Engineer-specific capabilities, those must be
added to the team before packaging.

## Differences from sub_mas-bootstrap

`sub_mas-bootstrap` (DEPLOY) is for distributing MAS-Engineer itself.
It copies all 52 sub-agents + 52 tools + dashboard + recovery. The result
is a full MAS-Engineer instance on the target system.

`sub_mas-team-packager` (PACKAGE_TEAM) is for distributing a single
team. It copies only the team's agents (typically 3-7 files). The
result is a lightweight team package.

| Aspect | bootstrap (DEPLOY) | team-packager (PACKAGE_TEAM) |
|--------|--------------------|------------------------------|
| Agents copied | 52 | N (team only) |
| Tools copied | 52 | 0 (or symlink) |
| Knowledge files | 9 | 3 (minimum) |
| Rules | R01-R18 | R01, R09, R10 |
| Dashboard | yes | no |
| Use case | deploy MAS-Engineer | distribute team |
| Install | full | single team |

## Workflow integration

The team-packager is automatically called by:

- `sub_mas-intention-parser` when a team is created via AUTO-SPLIT
- `sub_mas-generic-init` when task is CREATE_TEAM_SHELL with
  `package_after_create: true`

To skip packaging (e.g. for testing), pass `package_after_create: false`.

## Pre-push validation

Before any commit, the `pre-push-validator` checks that:

- `sub_mas-team-packager.yaml` is a valid YAML
- The team-packager instruction file exists
- No secrets are in the team-packager files
- The constitution file exists

If any of these fail, the push is blocked.

## See also

- [HOWTO-CREATE-AGENT.md](HOWTO-CREATE-AGENT.md) - Create a single agent
- [HOWTO-IM-PIPELINE.md](HOWTO-IM-PIPELINE.md) - Run the improvement pipeline
- [HOWTO-TEAM-STANDALONE.md](HOWTO-TEAM-STANDALONE.md) - Are created teams standalone?
- [recipe/sub/sub_mas-team-packager.yaml](../recipe/sub/sub_mas-team-packager.yaml) - The agent
- [recipe/instructions/sub_mas-team-packager.md](../recipe/instructions/sub_mas-team-packager.md) - Full instructions
- [recipe/instructions/sub_mas-master-constitution-team.md](../recipe/instructions/sub_mas-master-constitution-team.md) - Team constitution
