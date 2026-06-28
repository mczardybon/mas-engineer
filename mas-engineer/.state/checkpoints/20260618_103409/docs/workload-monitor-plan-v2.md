# WORKLOAD-MONITOR: Implementierungsplan V2 (SOT-konform)

**Erstellt:** 2026-06-15  
**Gesamtaufwand:** ~30 Minuten

---

## Kern-Architektur (SOT-konform)

```ascii
dev_workload_monitor.py
  │
  ├─ scan_sessions()    → Session-DB
  ├─ compute_workload() → Score 0-100%
  ├─ recommend()        → Vorschläge
  │
  └─ deploy_relief_agent()  ← NEU: SOT-konform
       │
       ├─ 1. Lese agent_schema.yaml (SOT)
       ├─ 2. Add neuen Agent in SOT ein
       │     { name: "sub_mas-{agent}-relief",
       │       emoji: "⚡",
       │       title: "...",
       │       instructions: "...",
       │       prompt: "..." }
       ├─ 3. Speichere SOT
       ├─ 4. Rufe dev_yaml_generator.py --target . auf
       │     → Erzeugt sub_mas-{agent}-relief.yaml
       └─ 5. Validiere: 37/37 YAMLs valide?
```

### Kein manuelles YAML-Erstellen!
Der Generator macht das. Wir manipulieren nur das SOT.

---

## 5 Schritte

### Schritt 1: `dev_workload_monitor.py` — Kernlogik (10 Min)

**Datei:** `mas-engineer/tools/dev_workload_monitor.py`

```python
def scan_sessions(agent_name=None, hours=24):
    """Lese Session-DB, aggregiere pro Agent."""
    # Verbinde ~/.config/goose/sessions/sessions.db
    # SELECT agent_name, COUNT(*), SUM(total_tokens), COUNT(*) FILTER(WHERE error)
    # FROM sessions WHERE session_type='sub_agent' AND created_at > now-24h
    # GROUP BY agent_name
    # Rückgabe: [{name, count, tokens, errors}, ...]

def compute_workload(sessions):
    """Score 0-100% aus Token-Verbrauch + Anfrage-Frequenz."""
    # max_tokens = max(s.total_tokens)
    # max_count = max(s.count)
    # score = (tokens/max_tokens * 40) + (count/max_count * 30) + (errors/max_errors * 30)
    # level = idle/normal/elevated/critical
    # Rückgabe: [{name, score, level, tokens, count, errors}, ...]

def recommend(workloads, threshold=80):
    """Generiere Vorschläge für Workloads > threshold."""
    # for wl in workloads where wl.score >= threshold:
    #   yield {agent, score, level, suggestion}

def main():
    """CLI: --agent, --hours, --threshold, --deploy, --json, --all"""
```

**CLI-Aufrufe:**
```bash
# Report alle Agenten
python3 dev_workload_monitor.py --hours 24

# Report mit Threshold
python3 dev_workload_monitor.py --threshold 80

# JSON-Output für SI-Designer
python3 dev_workload_monitor.py --json

# Auto-Deploy für kritische Agenten
python3 dev_workload_monitor.py --deploy
```

---

### Schritt 2: `deploy_relief_agent()` — SOT-konform (5 Min)

```python
def deploy_relief_agent(agent_name):
    """Erzeuge Relief-Agent via SOT + Generator."""
    import yaml, subprocess, os
    
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    schema_path = os.path.join(base, ".state/templates/agent_schema.yaml")
    
    # 1. Lese SOT
    schema = yaml.safe_load(open(schema_path))
    
    # 2. Generiere Relief-Agent-Namen
    relief_name = f"{agent_name}-relief"
    
    # 3. Check ob bereits vorhanden
    if relief_name in schema.get("agents", {}):
        return f"⚠️ {relief_name} existiert bereits"
    
    # 4. Erstelle neuen Agent-Eintrag im SOT
    schema.setdefault("agents", {})[relief_name] = {
        "emoji": "⚡",
        "title": f"SUB-MAS-{agent_name.upper()}-RELIEF — Entlastung fuer {agent_name}",
        "description": f"v1.0.0 | MAS: Relief-Agent, automatisch erzeugt per Workload-Monitor",
        "instructions": (
            f"# {agent_name}-relief\n\n"
            f"Entlastet {agent_name} bei hoher Workload.\n\n"
            f"### Tasks\n"
            f"- Uebernimmt Standard-Routine-Tasks von {agent_name}\n"
            f- Delegiert komplexe Faelle zurueck an {agent_name}\n"
            f"- Arbeitet autark — kein Zugriff auf {agent_name}'s State\n\n"
            f"### Grenzen\n"
            f"- KEINE Aenderungen an {agent_name}'s Konfiguration\n"
            f"- KEINE Entscheidungen ohne Ruecksprache\n"
            f"- NUR vordefinierte Tasks ausfuehren"
        ),
        "prompt": (
            f"⚡ {agent_name.upper()}-RELIEF (v1.0.0)\n\n"
            f"  NUR Routine-Tasks — Delegiere komplexes an {agent_name}\n"
            f"  ⛔⛔⛔⛔⛔ BESTAETIGUNGSPFLICHT (R01) Vor write/edit/shell\n"
            f"  ⛔⛔⛔⛔⛔ MODUS-DOMANEN-KOPPLUNG (R09) NUR mas-engineer/"
        )
    }
    
    # 5. Speichere SOT
    with open(schema_path, 'w') as f:
        yaml.dump(schema, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    
    # 6. Generiere YAML aus SOT
    gen_path = os.path.join(base, "tools/dev_yaml_generator.py")
    r = subprocess.run(['python3', gen_path, '--target', base], 
                      capture_output=True, text=True)
    
    # 7. Validiere
    sub_dir = os.path.join(base, "recipe/sub")
    valid = 0
    for f in os.listdir(sub_dir):
        if f.endswith('.yaml'):
            try:
                yaml.safe_load(open(os.path.join(sub_dir, f)))
                valid += 1
            except:
                pass
    
    return f"✅ {relief_name} deployed ({valid}/37 YAMLs valide)"
```

**Wichtig:** `agent_name` ist der **einfache Name** (z.B. `framework-scanner`), nicht `sub_mas-framework-scanner`. Der Generator baut daraus `sub_mas-framework-scanner-relief.yaml`.

---

### Schritt 3: SI-Designer Schritt 5c — Workload-Analyse (5 Min)

**Datei:** `mas-engineer/recipe/sub/sub_mas-im-designer.yaml`

**Nach Schritt 5a einfügen:**
```yaml
SCHRITT 5c: Workload-Analyse (SOT-konform)
  WENN mode == "mas" ODER mode == "generic":
    python3 {tools}/dev_workload_monitor.py --hours 24 --json
    -> {N} Agenten, {critical} kritisch, {elevated} erhöht
    
    WENN critical > 0:
      WEISE AN: dev_workload_monitor --deploy
        python3 {tools}/dev_workload_monitor.py --deploy
        -> Für jeden Agenten >80%:
           1. Add Relief-Agent in agent_schema.yaml (SOT) ein
           2. Rufe dev_yaml_generator.py auf
           3. Validiere 37/37 YAMLs
        -> {deployed} Relief-Agents deployed
```

---

### Schritt 4: `dev_mode.sh --workload-report` (2 Min)

**Datei:** `mas-engineer/tools/dev_mode.sh`

```bash
--workload-report|--wr)
    shift
    python3 tools/dev_workload_monitor.py "$@"
    ;;
```

---

### Schritt 5: Main-Recipe Trigger (5 Min)

**Datei:** `mas-engineer/recipe/dev-mas-engineer.yaml`

**In prompt_1 nach R09 einfügen:**
```yaml
WORKLOAD-MONITOR (SOT-konform):
  Bei Session-Start: prüfe ob Agent >80%
  → WENN ja: deploy_relief_agent() über SOT + Generator
  → Auto-Deploy: SOT-Edit → Generator --target → 37/37 validieren
  → KEINE manuellen YAML-Edits — immer über SOT!
```

**In instructions:**
```
SCHRITT 0b: Workload-Check
  python3 tools/dev_workload_monitor.py --threshold 80 --json
  WENN critical > 0:
    python3 tools/dev_workload_monitor.py --deploy
```

---

## Abhängigkeiten

```
S1 (dev_workload_monitor.py)       → KEINE                 [10 Min]
S2 (deploy_relief_agent SOT)       → ABH. VON S1           [ 5 Min]
S3 (SI-Designer Schritt 5c)        → ABH. VON S1+S2        [ 5 Min]
S4 (dev_mode.sh --wr)              → ABH. VON S1           [ 2 Min]
S5 (Main-Recipe Trigger)           → ABH. VON S2           [ 5 Min]

                                   GESAMT:                ~27 Min
```

## Test-Matrix (SOT-Fokus)

| Test | Erwartet |
|------|----------|
| `python3 dev_workload_monitor.py --hours 24` | Report mit 36 Agenten |
| `--deploy` ohne `--agent` | Alle Agenten >80% deployen |
| `--deploy --agent framework-scanner` | SOT erweitert + Generator → Relief-YAML |
| Nach Deploy: `36/37 YAMLs valide`? | ✅ 37/37 (Relief + 36 Originals) |
| Relief-Agent in SOT? | ✅ In agent_schema.yaml → agents → framework-scanner-relief |
| Relief-YAML existiert? | ✅ sub_mas-framework-scanner-relief.yaml |
| Relief-Agent hat R01+R09? | ✅ Im prompt eingebaut |
| `dev_mode.sh --wr` | Gleicher Output |
| SI-RUN Schritt 5c | Workload-Report + Deploy-Frage |
