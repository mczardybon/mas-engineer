# MAS-Engineer

A Multi-Agent System for **developing, improving, monitoring, and operating
Multi-Agent Systems (MAS)** for the User.

MAS-Engineer itself is a MAS: 50+ agents and 50+ tools that work together
to build other MAS frameworks.

## What you get

- 50+ specialized sub-agents (designer, finder, rank, validator, health-reporter, ...)
- 50+ tools (generic-init, framework-scanner, dashboard-data, ...)
- A complete dashboard (MCP server + 2 HTML webapps)
- Full audit trail in `.state/`
- Single-source-of-truth workflows in `.state/workflows.yaml`
- 7-stage IM-pipeline (FIND -> RANK -> DESIGN -> IMPLEMENT -> VALIDATE)

## Quick start: run the demo

The fastest way to see MAS-Engineer in action is to run the research-team
demo. It builds a complete 5-agent research framework at `/tmp/research-team`
with a working dashboard.

```bash
cd /tmp/mas-engineer/mas-engineer
goose run --recipe recipe/sub/sub_mas-demo-runner.yaml --no-session
```

Or just say "Run the demo." in any goose session.

## Try the prompt yourself

**Want to write your own MAS-Engineer prompts? See real examples:**

```
prompts/
├── README.md              ← how to write prompts
└── research-team.txt      ← full working prompt, ready to copy-paste
```

The [prompts/research-team.txt](prompts/research-team.txt) file is the
exact prompt that built the 5-agent research team at `/tmp/research-team`.
Copy it, modify the agents, change the output path, and run it. It
follows the 6-step pattern: initialize → create agents → wire them →
dashboard → live test → report.

More prompts: [prompts/README.md](prompts/README.md)

## Documentation

- [docs/DEMO-RESEARCH-TEAM.md](docs/DEMO-RESEARCH-TEAM.md) — Run the research-team demo
- [prompts/](prompts/) — Copy-paste prompts to use as templates
- [prompts/research-team.txt](prompts/research-team.txt) — The full demo prompt

## Use MAS-Engineer for your own work

```bash
cd /tmp/mas-engineer/mas-engineer
goose session
```

Try:
- "Build me a customer-support MAS at /tmp/support with 3 agents"
- "Audit the current project for security issues"
- "Improve the documentation of my Python package"
- "Run the IM-pipeline on my idea: <your idea>"

## Team Creation Workflows

MAS-Engineer supports **two workflows** for building multi-agent teams. Choose with a keyword:

| Workflow | Keyword | Result | Best for |
|----------|---------|--------|----------|
| **AUTO-SPLIT** (default) | none or `(auto)` | 1 monolith → 1 orchestrator + N specialized sub-agents | Clear requirements, want ready-to-use team |
| **INTERACTIVE** | `(interactive)`, `(manual)`, `(shell)`, `(no-split)`, `(let me define)` | 1 coordinator + N generic sub-agents | Exploration, learning, want full control |

### Examples

```text
"Build a customer-support team"
  → AUTO-SPLIT: 1 director + 3-5 specialists (ready to use)

"Build a customer-support team (interactive)"
  → INTERACTIVE: 1 coordinator + 3 generic members (you define roles)

"Build a data-analysis team (manual)"
  → INTERACTIVE: 1 coordinator + N generics
```

If no keyword is found and the description mentions a team, MAS-Engineer
shows a hint in the plan offering both options before R01 confirmation.

See: [docs/WORKFLOWS.md](docs/WORKFLOWS.md) for the full workflow selection guide.

## Architecture

```
User
  |
  v
dev-mas-engineer  (root orchestrator)
  |
  +-- delegate(finder)         find issues / opportunities
  +-- delegate(rank)           prioritize them
  +-- delegate(im-designer)    design the fix
  +-- delegate(im-validator)   validate the design
  +-- delegate(generic-init)   create new framework skeleton
  +-- delegate(demo-runner)    run the research-team demo
  +-- delegate(pre-push-validator)  block bad pushes
  +-- ... 50+ sub-agents
```

## Documentation

- [docs/WORKFLOWS.md](docs/WORKFLOWS.md) - Team creation workflows (AUTO-SPLIT vs INTERACTIVE)
- [docs/HOWTO-CREATE-AGENT.md](docs/HOWTO-CREATE-AGENT.md) - Create a single agent with intention-parser
- [docs/HOWTO-IM-PIPELINE.md](docs/HOWTO-IM-PIPELINE.md) - Run the 7-stage improvement pipeline
- [docs/HOWTO-TEAM-STANDALONE.md](docs/HOWTO-TEAM-STANDALONE.md) - Are created teams standalone-runnable?
- [docs/HOWTO-PACKAGE-TEAM.md](docs/HOWTO-PACKAGE-TEAM.md) - Package a team for standalone distribution
- [docs/DEMO-RESEARCH-TEAM.md](docs/DEMO-RESEARCH-TEAM.md) - Run the research-team demo
- [docs/governance.md](docs/governance.md) - R-rules and decision-making
- [docs/manifest.md](docs/manifest.md) - What MAS-Engineer is
- [docs/procedures.md](docs/procedures.md) - Standard operating procedures
- [docs/lessons-learned.md](docs/lessons-learned.md) - Hard-won knowledge
- [prompts/](prompts/) - Copy-paste prompts to use as templates
- [recipe/instructions/](recipe/instructions/) - All sub-agent instructions

## Project structure

```
mas-engineer/
  recipe/
    dev-mas-engineer.yaml       # root orchestrator
    sub/                        # 50+ sub-agent recipes
    instructions/               # detailed instructions per agent
    setup-dashboard.yaml        # dashboard setup
    dashboard-data-refresh.yaml # data.json refresher
  tools/                        # Python tools (50+)
  .mas/mcp/                     # MCP dashboard server
  .state/                       # SOT, audit trail, findings
  docs/                         # documentation
  tests/                        # test suite
  sub/                          # legacy sub-agents
```

## Rules (always active)

- **R01**: No changes without User confirmation
- **R18**: Delegate to specialized sub-agents
- **R20**: No direct write access — via Gatekeeper
- **R21**: Every action is logged
- **R09**: Strict domain separation (MAS != Framework)

All rules: `.state/workflows.yaml` -> `configs.mas-self`

## Versioning

- v1.0.0 — Current stable
- See git tags for history
