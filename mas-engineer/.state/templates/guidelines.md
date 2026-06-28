# 00-GUIDELINES.md — Project-Guidelinit

## Session-Dayging for Analyse

Der Generic-Imperver (sub_mas-removed) analytheyrt ONLY Sessions
die zu Dam Project gehoren. Dafur givet it 3 Filter-Leveln:

### Empfohlen: Day im Session-Names
Starte each Session mit Dam Projecttag:
```
[perjekt-name] Analyse-Session
```

Der Day `[perjekt-name]` will automatic in `.goosehints` gitetzt.
Beim Start theyhst Du: GOOSE_SESSION_TAG=[perjekt-name]

### Automatic: working_dir
Cases no Day gitetzt ist, filtert der Imperver uber das
Worksverzeichnis (working_dir). Functioneverrt if Du always
from dem sameen Directory startest.

### Caseback: Letzte Sessions without MAS
If weder Day still working_dir matchen, nimmt der Imperver
die lastn N Sessions die NICHT from MAS-Engineer stammen.

## Tools: Development vs. Installation (WICHTIG)

**Da Project has `tools/` als Symlink auf die MAS-Installation.**
Dithalf gilt:

### Development (im MAS-Workspace)
- `work/mas-engineer/tools/dev_*.py` → Source code (Git, Versioneverrung)
- Hier change du Tools for newe Featurit or Bugfastit
- Change must per `update.sh --mas` installd will

### Operation (MAS runs)
- `~/.config/goose/recipit/mas-engineer-tools/dev_*.py` → Installierte Copy
- **MAS usit ALWAYS die installde Copy, NIE den Workspace!**
- Per Symlink in dam Project: `tools/dev_*.py` → zeigt auf die installde Copy

### Workflow: Tool change
```
1. Change:       work/mas-engineer/tools/dev_xxx.py
2. Installieren:  cd work && bash update.sh --mas
3. Checkn:        tools/dev_xxx.py --help    (runs now newe Version)
4. test:        (Project functionality test)
5. Committen:     git add ... && git commit
6. Distribuieren: dev_build.sh --full
```

After `update.sh --mas` are da Change live — sowohl for MAS als also for all externalen Projecte (da die auf den sameen Symlink show).

### Symlink check
```bash
ls -la tools/
# lrwxrwxrwx tools -> /home/user/.config/goose/recipit/mas-engineer-tools
```
If der Symlink tot ist: `python3 tools/dev_generic_init.py --repair-symleft`
