# WORKLOAD-MONITOR: Implementierungsplan

**Erstellt:** 2026-06-15  
**Status:** Geplant  
**Gesamtaufwand:** ~27 Minuten

---

## Problem

Der Generic-Improver und SI haben **keine Workload-Analyse**. Sie erkennen nicht, wenn ein Agent überlastet ist (>80% Kapazität). Keine automatische Entlastung durch Sub-Agents oder Special-Agents.

---

## Lösung: Workload-Monitor

```ascii
┌─────────────────────────────────────────────────────────────────┐
│  dev_workload_monitor.py                                       │
│  ─────────────────────────                                     │
│  - scan()          → Liest Session-DB + Changes + Tools        │
│  - analyze()       → Berechnet Workload pro Agent              │
│  - recommend()     → Generiert Optimierungs-Vorschläge        │
│  - auto_deploy()   → Erzeugt Sub-/Special-Agent (optional)    │
│  - report()        → Gibt Report im JSON/Markdown              │
└─────────────────────────────────────────────────────────────────┘
```

### Metriken (pro Agent)

| Metrik | Quelle | Max-Punkte | Gewicht |
|--------|--------|------------|---------|
| Token-Verbrauch | Session-DB | 40 | 40% |
| Anfrage-Häufigkeit | Session-DB | 30 | 30% |
| Changes-Häufigkeit | changes.json | 20 | 20% |
| Fehler-Rate | Session-DB | 10 | 10% |

### Schwellwerte

| Score | Level | Reaktion |
|-------|-------|----------|
| 0-40% | 🟢 Idle | Kein Handlungsbedarf |
| 40-60% | 📊 Normal | Beobachten |
| 60-80% | ⚠️ Erhöht | Optional Sub-Agent vorschlagen |
| 80-100% | 🔴 Kritisch | Automatisch Sub-Agent deployen |

---

## 5 Implementierungs-Schritte

```
S1 (dev_workload_monitor.py)       → KEINE ABH.             [10 Min]
    ↓
S2 (auto_deploy)                   → ABH. VON S1            [ 5 Min]
S3 (im-designer.yaml Schritt 5c)   → ABH. VON S1            [ 5 Min]
S4 (dev_mode.sh --workload-report)  → ABH. VON S1            [ 2 Min]
S5 (Main-Recipe Trigger)           → ABH. VON S1 (Referenz) [ 5 Min]

GESAMT: ~27 Min
```

---

### Schritt 1: `dev_workload_monitor.py` — Kernlogik

**Datei:** `mas-engineer/tools/dev_workload_monitor.py` (120 Zeilen)

**Funktionen:**
- `scan_sessions(agent_name, hours)` → Liest Session-DB, aggregiert Metriken
- `scan_changes(agent_name, hours)` → Liest changes.json für Changes-Häufigkeit
- `compute_workload(session_stats, change_stats)` → Berechnet Score 0-100%
- `recommend(workloads, threshold)` → Generiert Optimierungs-Vorschläge
- `report(workloads, recommendations)` → Formatiert als Markdown/JSON
- `main()` → CLI: `--agent, --hours, --threshold, --deploy, --json`

**Aufruf:** `python3 dev_workload_monitor.py [--agent <name>] [--hours 24] [--threshold 80]`

**Test:** Report mit allen 36 Agenten + Scores

---

### Schritt 2: Auto-Deploy bei kritischer Last

**Erweiterung:** `dev_workload_monitor.py` + `auto_deploy()`

**Logik:**
```python
def auto_deploy(recommendation):
    """Erzeuge Sub-Agent bei kritischer Last."""
    agent = recommendation['agent']
    sub_name = f"sub_mas-{agent}-relief"
    
    # Erstelle agent_schema.yaml Eintrag
    new_agent = { emoji: '⚡', title: ..., description: ..., ... }
    
    # Add in SOT ein + generiere YAML
    schema['agents'][sub_name] = new_agent
    subprocess.run(['python3', 'tools/dev_yaml_generator.py', '--target', '.'])
```

**Test:** `--deploy --agent framework-scanner` → `sub_mas-framework-scanner-relief.yaml` erstellt

---

### Schritt 3: SI-Designer Schritt 5c

**Datei:** `mas-engineer/recipe/sub/sub_mas-im-designer.yaml`

**Neuer Schritt nach 5a:**
```yaml
SCHRITT 5c: Workload-Analyse
  python3 {tools}/dev_workload_monitor.py --hours 24
  -> {N} Agenten, {critical} kritisch, {elevated} erhöht
  
  WENN critical > 0:
    Frage: "Sub-Agents deployen?"
    WENN ja: python3 ... --deploy --agent {agent}
```

---

### Schritt 4: `dev_mode.sh --workload-report`

**Datei:** `mas-engineer/tools/dev_mode.sh`

**Neue Option:**
```bash
--workload-report|--wr [--hours 24] [--threshold 80]
  → python3 tools/dev_workload_monitor.py [args]
```

---

### Schritt 5: Main-Recipe + Sub-Agent Trigger

**Datei:** `mas-engineer/recipe/dev-mas-engineer.yaml` (prompt_1)

**Neuer Block:**
```yaml
WORKLOAD-MONITOR (automatisch):
  Bei JEDER Session: prüfe ob ein Agent >80% erreicht
  → Wenn Ja: Workload-Report + Frage ob Sub-Agent deployt
  → Auto-Deploy bei >95%
```

**Sub-Agent prompt-Integration (alle 36):**
```
WORKLOAD: Bei >80% Auslastung → melden beim Main-Recipe.
Ein Relief-Agent kann erstellt werden.
```

---

## Test-Matrix

| Test | Erwartet |
|------|----------|
| `python3 dev_workload_monitor.py` | Report mit 36 Agenten, Scores 0-100% |
| `--agent agent-guardian` | Nur dieser Agent |
| `--threshold 50` | Nur Agenten >50% |
| `--deploy --agent framework-scanner` | Relief-Agent erstellt |
| `dev_mode.sh --workload-report` | Gleicher Output |
| SI-RUN Schritt 5c | Workload-Report im SI-Output |
