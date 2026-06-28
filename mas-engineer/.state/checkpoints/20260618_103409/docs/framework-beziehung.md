# MAS ↔ Framework Beziehung — v1.0.0

## Kernprinzip

**MAS ist der Framework-Entwickler.** Wie ein DevOps-Ingenieur entwickelt,
testet, deployt und überwacht MAS das Framework — von aussen.
Das Framework weiss nichts von MAS.

```
┌────────────────────────────────────┐
│  🧠 MAS-ENGINEER                   │
│  Entwickelt, testet, deployt       │
│  Kennt Framework-Strukturen        │
│  Läuft IMMER — auch ohne Framework │
└────────────────────────────────────┘
              │ entwickelt │ testet │ deployt
              ▼
┌────────────────────────────────────┐
│  📦 FRAMEWORK (agent/)             │
│  Läuft eigenständig                │
│  Kennt MAS NICHT                   │
│  Keine MAS-Referenzen              │
└────────────────────────────────────┘
```

## MAS kennt Framework
- Seine eigenen Sub-Agenten (sub_mas-*)
- Seine Tools (dev_*.py)
- Seine Docs (manifest, governance, procedures)
- SEINE entwickelten Frameworks (Workspace, installiert, deployed)
- Framework-Strukturen (um sie zu analysieren, testen, patchen)
- Framework-Recipes (um sie zu bearbeiten, installieren, starten)

## MAS darf mit Framework
- Framework-Recipes lesen → cat, yaml.safe_load
- Framework-Recipes editieren → dev_editor.py, edit-Tool
- Framework testen → pytest, dev_test_runner.py (via bash)
- Framework installieren → dev_workspace.py --install
- Framework starten → dev_workspace.py --launch
- Framework deployen → dev_workspace.py --deploy
- Framework migrieren → dev_migration.py
- Framework scannen → dev_observer.py
- Framework auditen → sub_mas-config-auditor

## MAS darf NICHT
- Framework-Recipes in MAS-Recipe einbetten
- Framework-Agenten als MAS-Sub-Agenten nutzen
- Framework-Konzepte als MAS-Konzepte bezeichnen

## Framework kennt
- NICHTS von MAS
- Nur seine eigenen Recipes, Docs, Tools

## Sicherheit

### MAS standalone (runs ohne Framework)
- MAS-Recipe ist KOMPLETT eigenständig
- MAS-Sub-Agenten referenzieren NUR MAS-Konzepte
- MAS runs mit: dev-mas-engineer.yaml + sub_mas-*.yaml + dev_*.py
- MAS braucht KEIN Framework zum Funktionieren

### Framework standalone (runs ohne MAS)
- Framework runs ohne MAS
- Framework-Agenten kennen MAS nicht
- Framework-Docs referenzieren MAS nicht

### Keine Kreuzung
- Framework-Recipes haben KEINE sub_mas-*-Dateien
- MAS-Recipe hat KEINE framework-*-Dateien
- MAS-Tools liegen in mas-engineer-tools/ (nicht framework/)

## Workflows

### work_on_mas — MAS selbst entwickeln
- Sub-Agenten (sub_mas-*.yaml) editieren
- Tools (dev_*.py) verbessern
- Docs aktualisieren
- MAS optimieren (self-improve)

### work_on_framework — Framework entwickeln
- Framework-Recipes lesen und patchen
- Framework testen (pytest)
- Framework installieren/deinstallieren
- Framework migrieren
- Neue Features entwickeln

### work_on_mas_dev — Framework entwickeln (mit MAS-Tools)
- Framework-Recipes bearbeiten (mit dev_editor.py)
- Framework testen (mit dev_test.py)
- Framework scannen (mit dev_observer.py)
- MAS bleibt available für Support

## Regeln (UNANTASBAR)

1. **MAS ≠ Framework** — Zwei getrennte Welten
2. **MAS kennt Framework** — Framework kennt MAS nicht
3. **MAS standalone** — Läuft IMMER, auch ohne Framework
4. **Framework standalone** — Läuft IMMER, auch ohne MAS
5. **Keine Kreuzung** — Keine sub_mas-* in Framework, keine framework-* in MAS
6. **MAS hat volle Freiheit** — Darf Framework lesen, editieren, testen, installieren, starten, deployen
