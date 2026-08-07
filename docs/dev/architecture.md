# System Architecture

This document describes the internal architecture of MAS-Engineer at the level a
developer needs to extend or debug it. It covers the layered model, the delegation
flow, the mode system, and the data model.

## Layered model

```mermaid
flowchart TB
    subgraph RUNTIME["Goose MCP Runtime"]
        G1["Session management"]
        G2["Scheduling"]
        G3["Extensions (summon, developer)"]
    end
    subgraph CORE["mas-engineer/ (the system)"]
        ME["dev-mas-engineer.yaml\nroot orchestrator (thin delegator)"]
        DIR["sub_mas-dev-director.yaml\norchestrator"]
        AGENTS["112 sub-agents\n(recipe/sub/sub_mas-*.yaml)"]
        TOOLS["65 tools\n(mas-engineer/tools/)"]
        SOT[".mase/workflows.yaml\nSingle Source of Truth"]
        CHECKER["dev_rule_checker.py\nruntime enforcement"]
    end
    subgraph EVIDENCE["Evidence"]
        LOGS["logs/ — committed e2e logs"]
        DOCS["docs/ + docs/dev/"]
    end

    RUNTIME --> CORE
    ME --> DIR
    DIR --> AGENTS
    AGENTS --> TOOLS
    AGENTS --> SOT
    TOOLS --> SOT
    SOT --> CHECKER
    CHECKER -->|"block / allow"| AGENTS
    AGENTS --> LOGS
```

The system is deliberately **thin at the top**: `dev-mas-engineer.yaml` only
delegates to `sub_mas-dev-director.yaml`, which routes tasks to specialized
sub-agents based on the task domain. Almost all behavior lives in the sub-agents
and tools.

## Root orchestrator flow

```mermaid
sequenceDiagram
    participant U as User
    participant E as dev-mas-engineer
    participant D as dev-director
    participant A as specialized sub-agent
    participant T as tool

    U->>E: natural-language task
    E->>D: delegate(task)
    D->>A: delegate(domain-matched sub-agent)
    A->>T: shell tool call
    T-->>A: result
    A-->>D: 🟢 DONE (result)
    D-->>E: result
    E-->>U: summary
```

`dev-director` uses a **delegation map** to route domains:

| Domain | Sub-agent |
|--------|-----------|
| analyze / audit / scan | `sub_mas-dev-analyzer` |
| design / create / generate | `sub_mas-dev-builder` |
| test / validate / verify | `sub_mas-dev-tester` |
| research / monitor | `sub_mas-dev-observer` |
| commit / git / push | `sub_mas-git-operator` |
| degradation | `sub_mas-degradation-director` |
| team packaging | `sub_mas-team-packager-director` |
| test reporting | `sub_mas-test-reporter-director` |

## Mode system (R14, R110-31)

The operating mode is read from `.mas-mode` and determines which **domain** a
sub-agent belongs to:

```mermaid
stateDiagram-v2
    direction LR
    [*] --> MAS: .mas-mode = "mas"
    [*] --> FRAMEWORK: .mas-mode = "framework"
    [*] --> GENERIC: .mas-mode = "<project>"

    state MAS {
        M1: improves itself (DOMAIN 1)
    }
    state FRAMEWORK {
        F1: improves user system (DOMAIN 2)
    }
    state GENERIC {
        G1: operates a project (DOMAIN 3)
    }
```

Detection priority (R110-31): `.mas-mode` value > action-string heuristic.

- **mas** (DOMAIN 1): all `sub_mas-*.yaml` must be registered in
  `configs.mas-self.sub_agents`.
- **framework** (DOMAIN 2): a mas-generated team; the orchestrator's
  instructions are the registry.
- **generic** (DOMAIN 3): a standalone project; mas-engineer's `workflows.yaml`
  is not involved.

## Data model

MAS-Engineer's state is concentrated in `.mase/`:

```
.mase/
├── workflows.yaml          # SOT — agents, rules, workflows, signals, paths
├── knowledge/              # 9 knowledge files (architecture, rules, tools, ...)
├── rules/                  # rule definitions + hardness levels
├── templates/              # agent schemas, guidelines, BP checklist
├── skills/                 # 20 SKILL.md files (agent runtime skills)
├── mcp/                    # MCP dashboard server (Node.js)
├── config/                 # cost.yaml (budget gates)
├── directives/             # R-sprint directive specs
├── pipeline/               # IM-pipeline outputs (findings, patches, validation)
└── checkpoints/            # recovery checkpoints
```

Evidence (test logs, e2e results, reports) lives outside `.mase/` in `logs/` at
the repository root and is committed to GitHub.

## Repository layout

```
repo root/
├── mas-engineer/           # the system (recipes, tools, tests, .mase)
├── logs/                   # committed e2e evidence
├── docs/                   # documentation (guides)
│   └── dev/                # developer documentation (this)
├── archive/                # historic reports, samples, legacy scripts
├── demos/                  # demo teams
├── install.sh              # installer
└── README.md
```

## See also

- [sot.md](sot.md) — the SOT schema and path resolution
- [communication.md](communication.md) — agent protocol
- [rules.md](rules.md) — runtime rule enforcement
