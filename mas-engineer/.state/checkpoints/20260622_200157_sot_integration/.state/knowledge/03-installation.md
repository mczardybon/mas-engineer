# Installation — ZIP-Struktur und Zielorte

## ZIP-Struktur (1:1 Workspace)
mas-framework-v2.42.0_TIMESTAMP.zip
├── framework/
│   └── dev-team/
│       ├── config.yaml
│       ├── recipes/         47 Specialists + 44 Subs + 4 Cores
│       ├── docs/            Governance, Protokolle, Boundaries
│       ├── tests/           pytest
│       └── python/          Admin-Skripte
├── mas-engineer/
│   ├── recipe/
│   │   ├── dev-mas-engineer.yaml
│   │   ├── sub/sub_mas-*.yaml   (36)
│   │   └── template/
│   ├── tools/               43 Dev-Tools
│   ├── docs/                Manifest, Governance, Procedures
│   ├── plans/               Dashboard-Bauplaene
│   └── .state/              Regeln, Domaenen, Agents, Wissen
├── installer.sh
├── update.sh
└── .mas-mode

## Installationsbefehle (User)
./installer.sh                  → MAS + Framework (Default)
./installer.sh --mas            → Nur MAS
./installer.sh --framework      → Nur Framework
./installer.sh --dry-run        → Trockentest
./installer.sh --status         → Status anzeigen

## Updates (Entwickler)
./update.sh --mas               → MAS aus Workspace syncen
./update.sh --framework         → Framework aus Workspace syncen
./update.sh --mas --dry-run     → MAS-Trockentest

## Build (Entwickler)
bash mas-engineer/tools/dev_build.sh              → ZIP bauen
bash mas-engineer/tools/dev_build.sh --full        → MAS + ALLE Projekte
bash mas-engineer/tools/dev_build.sh --dry-run     → Nur pruefen
bash mas-engineer/tools/dev_build.sh --version x.y.z

## Installationslogik (installer.sh)
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
