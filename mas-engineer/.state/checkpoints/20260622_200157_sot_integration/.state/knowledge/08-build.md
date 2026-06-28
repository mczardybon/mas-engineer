# Build-System v3.0

## ZIP-Bau (dev_build.sh)
cd ~/agent_test/work && bash mas-engineer/tools/dev_build.sh
→ dist/mas-framework-v2.42.0_TIMESTAMP.zip (287 Dateien, ~700 KB)

### Was passiert:
1. __pycache__ + .backups + .state/checkpoints werden vor Build geloescht
2. zip -r aus Workspace-Root:
   - installer.sh, update.sh, .mas-mode, .gitignore
   - framework/.projects.yaml
   - framework/$PROJECT/ (recipes + docs + config + tests + python)
   - mas-engineer/ (recipe + tools + docs + plans + .state)
3. Ausschluesse: *.git* .backups __pycache__ *.pyc *.pyo improve-log*
4. Validierung: 5 Cores, 47 Specialists, 44 FW-Subs, 36 MAS-Subs, >=40 Tools, kein pycache

### Modi:
| Befehl | Beschreibung |
|:-------|:-------------|
| dev_build.sh | Framework-Modus (nur aktives Projekt) |
| dev_build.sh --full | FULL-Modus (MAS + ALLE Projekte aus .projects.yaml) |
| dev_build.sh --dry-run | Nur pruefen, nichts bauen |
| dev_build.sh --version x.y.z | Version setzen |

## Installation (installer.sh)
cd dist && unzip mas-framework-*.zip && ./installer.sh

### install_mas():
| Schritt | Quelle | Ziel |
|:-------:|:-------|:-----|
| M1 | mas-engineer/recipe/dev-mas-engineer.yaml | ~/.config/goose/recipes/ |
| M2 | mas-engineer/recipe/sub/sub_mas-*.yaml (36) | ~/.config/goose/recipes/sub/ |
| M3 | mas-engineer/recipe/template/ | ~/.config/goose/recipes/template/ |
| M4 | mas-engineer/tools/* (43) | ~/.config/goose/recipes/mas-engineer-tools/ |
| M5 | mas-engineer/docs/* | ~/.config/goose/docs/mas-engineer/ |
| M6 | mas-engineer/.state/* | ~/.config/goose/.state/ |

### install_framework():
| Schritt | Quelle | Ziel |
|:-------:|:-------|:-----|
| F1 | framework/dev-team/ | ~/.local/share/goose/framework/ |
| F2 | 4 Core-Rezepte | ~/.config/goose/recipes/ |
| F3 | core/specialist-constitution.yaml | ~/.config/goose/recipes/core/ |
| F4 | specialist_*.yaml (47) | ~/.config/goose/recipes/ |
| F5 | sub_*.yaml (44) | ~/.config/goose/recipes/ |
| F6 | framework/docs/ | ~/.config/goose/docs/ |
| F7 | config.yaml | ~/.config/goose/config.yaml (merge) |
| F8 | .projects.yaml | ~/.config/goose/.projects.yaml |

## Update (update.sh)
| Befehl | Beschreibung |
|:-------|:-------------|
| ./update.sh --mas | Nur MAS aus Workspace syncen |
| ./update.sh --framework | Nur Framework aus Workspace syncen |
| ./update.sh --mas --dry-run | MAS-Trockentest |
| ./update.sh --help | Hilfe |

## Auto-Build (dev_autobuild.sh)
| Befehl | Beschreibung |
|:-------|:-------------|
| dev_autobuild.sh | Auto-Build (prueft ob Commit seit letztem ZIP) |
| dev_autobuild.sh --force | Immer bauen |
| dev_autobuild.sh --status | Nur pruefen |
| dev_autobuild.sh --install | Bauen + update.sh --mas |

Keine eigene Logik mehr — delegiert an dev_build.sh.
