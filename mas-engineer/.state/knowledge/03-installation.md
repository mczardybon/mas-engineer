# Installation — ZIP Structure and Target Locations

## ZIP Structure (1:1 Workspace)
mas-framework-v1.0.0_TIMESTAMP.zip
├── framework/
│   └── dev-team/
│       ├── config.yaml
│       ├── recipes/         47 Specialists + 44 Subs + 4 Cores
│       ├── docs/            Governance, Protocols, Boundaries
│       ├── tests/           pytest
│       └── python/          Admin Scripts
├── mas-engineer/
│   ├── recipe/
│   │   ├── dev-mas-engineer.yaml
│   │   ├── sub/sub_mas-*.yaml   (36)
│   │   └── template/
│   ├── tools/               43 Dev-Tools
│   ├── docs/                Manifest, Governance, Procedures
│   ├── plans/               Dashboard-blueprints
│   └── .state/              Rules, Domains, Agents, Knowledge
├── installr.sh
├── update.sh
└── .mas-mode

## Installation commands (User)
./installr.sh                  → MAS + framework (Default)
./installr.sh --mas            → Only MAS
./installr.sh --framework      → Only framework
./installr.sh --dry-run        → Dry run
./installr.sh --status         → Status display

## Updates (Developer)
./update.sh --mas               → MAS sync from workspace
./update.sh --framework         → framework sync from workspace
./update.sh --mas --dry-run     → MAS dry run

## Build (Developer)
bash mas-engineer/tools/dev_build.sh              → Build ZIP
bash mas-engineer/tools/dev_build.sh --full        → MAS + ALL projects
bash mas-engineer/tools/dev_build.sh --dry-run     → Only check
bash mas-engineer/tools/dev_build.sh --version x.y.z

## Installation Logic (installr.sh)
install_mas():
  M1: cp dev-mas-engineer.yaml → recipes/
  M2: cp sub_mas-*.yaml (36)   → recipes/sub/
  M3: cp tools/* (43)          → recipes/mas-engineer-tools/
  M4: cp docs/*                → docs/mas-engineer/
  M5: cp .state/*              → ~/.config/goose/.state/

install_framework():
  F1: cp -r framework/dev-team/ → ~/.local/share/goose/framework/
  F2: cp 4 Cores               → recipes/
  F3: cp core/                 → recipes/core/
  F4: cp specialist_*.yaml (47) → recipes/
  F5: cp sub_*.yaml (44)       → recipes/
  F6: cp docs/                 → ~/.config/goose/docs/
  F7: Config mergen            → ~/.config/goose/config.yaml
