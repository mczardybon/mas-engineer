# MAS-Architektur v1.0.0

## Systemaufbau
```
┌──────────────────────────────────────────────────┐
│  DEV-MAS-ENGINEER (dev-mas-engineer.yaml)        │
│  - Entwickelt/ueberwacht/testet/patcht Framework │
│  - 36 Sub-Agenten (sub_mas-*.yaml)              │
│  - 43 Tools (mas-engineer-tools/)                │
│  - Laeuft IMMER (auch ohne Framework)            │
└──────────┬───────────────────────────────────────┘
           │ delegate()
           ▼
┌──────────────────────────────────────────────────┐
│  FRAMEWORK v2.42.0                               │
│  - 4 Core-Recipes (executor, planner, ...)       │
│  - 47 Specialists (sicherheit, backend, ...)     │
│  - 44 Sub-Agenten (sub_dispatcher, ...)          │
│  - Laeuft IMMER (auch ohne MAS)                  │
└──────────────────────────────────────────────────┘
```

## Rollenverteilung
- **MAS = Entwickler des Frameworks** (analysiert, patcht, testet, deployt)
- **Framework = Produktivsystem** (weiss nichts von MAS)
- **User = Entscheider** (MAS schlaegt vor, User entscheidet)

## Domain separation (R09)
- MAS schreibt NUR in mas-engineer/
- Framework schreibt NUR in framework/
- Lesen in andere domain ist OK
- Durchgesetzt via: registry.yaml + dev_rule_checker.py R09

## Verzeichnisstruktur (Workspace)
```
work/
├── mas-engineer/         ← MAS (eigenstaendiger Entwickler)
│   ├── recipe/           → dev-mas-engineer.yaml + sub/sub_mas-*.yaml
│   ├── tools/            → 43 Dev-Tools
│   ├── docs/             → Manifest, Governance, Procedures
│   ├── plans/            → Dashboard-Bauplaene
│   └── .state/           → Regeln, Domaenen, Agents, Wissen
├── framework/            ← FRAMEWORK (Produktivsystem)
│   └── dev-team/
│       ├── recipes/      → 47 Specialists + 44 Subs + 4 Cores
│       ├── docs/         → Governance, Protokolle, Boundaries
│       ├── config.yaml
│       ├── tests/        → pytest
│       └── python/       → Admin-Skripte
├── installer.sh, update.sh, .mas-mode
├── repo/                 → HomeAssistant-Core (anderes Projekt)
└── dist/                 → Gebaute ZIPs
```

## Installationsziele (nach ./installer.sh)
```
~/.config/goose/recipes/  (RECIPE_PATH):
├── dev-mas-engineer.yaml     ← Core-Recipe
├── executor.yaml             ← FW Core 1/4
├── planner.yaml              ← FW Core 2/4
├── framework-controller.yaml ← FW Core 3/4
├── framework-starter.yaml    ← FW Core 4/4
├── specialist_*.yaml (47)    ← Direkt auffindbar fuer delegate()
├── sub_*.yaml (44)           ← Direkt auffindbar fuer delegate()
├── sub/sub_mas-*.yaml (36)   ← MAS-Sub-Agenten
├── core/specialist-constitution.yaml
└── mas-engineer-tools/ (43)  ← Tools

~/.local/share/goose/framework/dev-team/:
├── config.yaml, docs/, tests/, python/
```

## Härte-System (Methoden 1+5+6+9+10)
```
prompt_1 (800 Tokens)  → ⛔⛔⛔⛔⛔ NIE geloescht
prompt_2 (500 Tokens)  → ⛔⛔⛔ bleibt bis Turn-Ende
prompt_3 (300 Tokens)  → ⛔ kann verschwinden
```

| Methode | Mechanismus | Tool |
|:-------:|:------------|:-----|
| 5 | Reaktivierungs-Anker (alle 5 Schritte) | dev_rule_refresh.sh |
| 6 | Härte-Propagation (bei delegate) | dev_haerte_propagation.py |
| 9 | Regel-Test (vor jeder Aktion) | dev_rule_checker.py |
| 10 | Multi-Prompt (3 Stufen) | prompt_1+prompt_2+prompt_3 |
