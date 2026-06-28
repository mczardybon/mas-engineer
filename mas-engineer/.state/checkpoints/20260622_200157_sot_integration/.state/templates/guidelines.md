# 00-GUIDELINES.md — Projekt-Richtlinien

## Session-Tagging für Analyse

Der Generic-Improver (sub_mas-entfernt) analysiert NUR Sessions
die zu Deinem Projekt gehoren. Dafur gibt es 3 Filter-Ebenen:

### Empfohlen: Tag im Session-Namen
Starte jede Session mit Deinem Projekttag:
```
[projekt-name] Analyse-Session
```

Der Tag `[projekt-name]` wird automatisch in `.goosehints` gesetzt.
Beim Start siehst Du: GOOSE_SESSION_TAG=[projekt-name]

### Automatisch: working_dir
Falls kein Tag gesetzt ist, filtert der Improver uber das
Arbeitsverzeichnis (working_dir). Funktioniert wenn Du immer
aus dem gleichen Verzeichnis startest.

### Fallback: Letzte Sessions ohne MAS
Wenn weder Tag noch working_dir matchen, nimmt der Improver
die letzten N Sessions die NICHT vom MAS-Engineer stammen.

## Tools: Entwicklung vs. Installation (WICHTIG)

**Dein Projekt hat `tools/` als Symlink auf die MAS-Installation.**
Deshalb gilt:

### Entwicklung (im MAS-Workspace)
- `work/mas-engineer/tools/dev_*.py` → Quellcode (Git, Versionierung)
- Hier änderst du Tools für neue Features oder Bugfixes
- Changes müssen per `update.sh --mas` installiert werden

### Betrieb (MAS runs)
- `~/.config/goose/recipes/mas-engineer-tools/dev_*.py` → Installierte Kopie
- **MAS verwendet IMMER die installierte Kopie, NIE den Workspace!**
- Per Symlink in deinem Projekt: `tools/dev_*.py` → zeigt auf die installierte Kopie

### Workflow: Tool ändern
```
1. Ändern:       work/mas-engineer/tools/dev_xxx.py
2. Installieren:  cd work && bash update.sh --mas
3. Checkn:        tools/dev_xxx.py --help    (runs jetzt neue Version)
4. Testen:        (Projekt-Funktionalität testen)
5. Committen:     git add ... && git commit
6. Distribuieren: dev_build.sh --full
```

Nach `update.sh --mas` sind deine Changes live — sowohl für MAS als auch für alle externen Projekte (da die auf den gleichen Symlink zeigen).

### Symlink check
```bash
ls -la tools/
# lrwxrwxrwx tools -> /home/user/.config/goose/recipes/mas-engineer-tools
```
Wenn der Symlink tot ist: `python3 tools/dev_generic_init.py --repair-symlinks`
