# MAS-Architecture v1.0.0

## System Architecture
```
┌──────────────────────────────────────────────────┐
│  DEV-MAS-ENGINEER (dev-mas-engineer.yaml)        │
│  - Entwickelt/aboutwacht/testet/patcht framework │
│  - 36 Sub-Agents (sub_mas-*.yaml)              │
│  - 43 Tools (mas-engineer-tools/)                │
│  - Runs ALWAYS (auch without framework)            │
└──────────┬───────────────────────────────────────┘
           │ delegate()
           ▼
┌──────────────────────────────────────────────────┐
│  FRAMEWORK v1.0.0                               │
│  - 4 Core-Recipes (executor, planner, ...)       │
│  - 47 Specialists (sicherheit, backend, ...)     │
│  - 44 Sub-Agents (sub_dispatcher, ...)          │
│  - Runs ALWAYS (auch without MAS)                  │
└──────────────────────────────────────────────────┘
```

## rolesverteilung
- **MAS = Developer des frameworks** (analyzed, patcht, testet, deployt)
- **framework = productivsystem** (weiss nothing from MAS)
- **User = Entscheider** (MAS schlaegt before, User decides)

## Domain separation (R09)
- MAS writes ONLY in mas-engineer/
- framework writes ONLY in framework/
- Read in andere domain ist OK
- Durchgesetzt via: registry.yaml + dev_rule_checker.py R09

## directorystruktur (Workspace)
```
work/
├── mas-engineer/         ← MAS (autonomouser Developer)
│   ├── recipe/           → dev-mas-engineer.yaml + sub/sub_mas-*.yaml
│   ├── tools/            → 43 Dev-Tools
│   ├── docs/             → Manifest, Governance, Procedures
│   ├── plans/            → Dashboard-blueprints
│   └── .state/           → Rules, Domains, Agents, Wissen
├── framework/            ← FRAMEWORK (productivsystem)
│   └── dev-team/
│       ├── recipes/      → 47 Specialists + 44 Subs + 4 Cores
│       ├── docs/         → Governance, Protocols, Boundaries
│       ├── config.yaml
│       ├── tests/        → pytest
│       └── python/       → Admin-Skripte
├── installr.sh, update.sh, .mas-mode
├── repo/                 → HomeAssistant-Core (anderes Projekt)
└── dist/                 → Gebaute ZIPs
```

## Installation targets (after ./installr.sh)
```
~/.config/goose/recipes/  (RECIPE_PATH):
├── dev-mas-engineer.yaml     ← Core-Recipe
├── executor.yaml             ← FW Core 1/4
├── planner.yaml              ← FW Core 2/4
├── framework-controller.yaml ← FW Core 3/4
├── framework-starter.yaml    ← FW Core 4/4
├── specialist_*.yaml (47)    ← Direkt auffindbar for delegate()
├── sub_*.yaml (44)           ← Direkt auffindbar for delegate()
├── sub/sub_mas-*.yaml (36)   ← MAS-Sub-Agents
├── core/specialist-constitution.yaml
└── mas-engineer-tools/ (43)  ← Tools

~/.local/share/goose/framework/dev-team/:
├── config.yaml, docs/, tests/, python/
```

## Hardening System (Methods 1+5+6+9+10)
```
prompt_1 (800 tokens)  → ⛔⛔⛔⛔⛔ NIE deleted
prompt_2 (500 tokens)  → ⛔⛔⛔ bleibt bis Turn-End
prompt_3 (300 tokens)  → ⛔ can verschwinden
```

| Method | Mechanismus | Tool |
|:-------:|:------------|:-----|
| 5 | Reaktivierungs-Anker (all 5 steps) | dev_rule_refresh.sh |
| 6 | Hardening Propagation (at delegate) | dev_haerte_propagation.py |
| 9 | Rule-Test (before jeder action) | dev_rule_checker.py |
| 10 | Multi-Prompt (3 Leveln) | prompt_1+prompt_2+prompt_3 |
