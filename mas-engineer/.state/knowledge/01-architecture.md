# MAS-Architecture v1.0.0

## System Architecture
```
┌──────────────────────────────────────────────────┐
│  DEV-MAS-ENGINEER (dev-mas-engineer.yaml)        │
│  - Develops/monitors/tests/patches the framework │
│  - 36 Sub-Agents (sub_mas-*.yaml)              │
│  - 43 Tools (mas-engineer-tools/)                │
│  - Runs ALWAYS (also without framework)            │
└──────────┬───────────────────────────────────────┘
           │ delegate()
           ▼
┌──────────────────────────────────────────────────┐
│  FRAMEWORK v1.0.0                               │
│  - 4 Core-Recipes (executor, planner, ...)       │
│  - 47 Specialists (security, backend, ...)     │
│  - 44 Sub-Agents (sub_dispatcher, ...)          │
│  - Runs ALWAYS (also without MAS)                  │
└──────────────────────────────────────────────────┘
```

## Role Distribution
- **MAS = Developer of the framework** (analyzes, patches, tests, deploys)
- **framework = production system** (knows nothing about MAS)
- **User = Decision-Maker** (MAS proposes beforehand, User decides)

## Domain separation (R09)
- MAS writes ONLY in mas-engineer/
- framework writes ONLY in framework/
- Read in other domain is OK
- Enforced via: registry.yaml + dev_rule_checker.py R09

## Directory Structure (Workspace)
```
work/
├── mas-engineer/         ← MAS (autonomous Developer)
│   ├── recipe/           → dev-mas-engineer.yaml + sub/sub_mas-*.yaml
│   ├── tools/            → 43 Dev-Tools
│   ├── docs/             → Manifest, Governance, Procedures
│   ├── plans/            → Dashboard-blueprints
│   └── .state/           → Rules, Domains, Agents, Knowledge
├── framework/            ← FRAMEWORK (production system)
│   └── dev-team/
│       ├── recipes/      → 47 Specialists + 44 Subs + 4 Cores
│       ├── docs/         → Governance, Protocols, Boundaries
│       ├── config.yaml
│       ├── tests/        → pytest
│       └── python/       → Admin Scripts
├── installr.sh, update.sh, .mas-mode
├── repo/                 → HomeAssistant-Core (other project)
└── dist/                 → Built ZIPs
```

## Installation targets (after ./installr.sh)
```
~/.config/goose/recipes/  (RECIPE_PATH):
├── dev-mas-engineer.yaml     ← Core-Recipe
├── executor.yaml             ← FW Core 1/4
├── planner.yaml              ← FW Core 2/4
├── framework-controller.yaml ← FW Core 3/4
├── framework-starter.yaml    ← FW Core 4/4
├── specialist_*.yaml (47)    ← Directly findable for delegate()
├── sub_*.yaml (44)           ← Directly findable for delegate()
├── sub/sub_mas-*.yaml (36)   ← MAS-Sub-Agents
├── core/specialist-constitution.yaml
└── mas-engineer-tools/ (43)  ← Tools

~/.local/share/goose/framework/dev-team/:
├── config.yaml, docs/, tests/, python/
```

## Hardening System (Methods 1+5+6+9+10)
```
prompt_1 (800 tokens)  → ⛔⛔⛔⛔⛔ NEVER deleted
prompt_2 (500 tokens)  → ⛔⛔⛔ remains until turn end
prompt_3 (300 tokens)  → ⛔ can disappear
```

| Method | Mechanism | Tool |
|:-------:|:------------|:-----|
| 5 | Reactivation anchor (all 5 steps) | dev_rule_refresh.sh |
| 6 | Hardening Propagation (at delegate) | dev_haerte_propagation.py |
| 9 | Rule-Test (before every action) | dev_rule_checker.py |
| 10 | Multi-Prompt (3 levels) | prompt_1+prompt_2+prompt_3 |
