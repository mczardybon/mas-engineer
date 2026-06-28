# Härte-Regeln R01-R18

## EXTREM-STARK (⛔⛔⛔⛔⛔) — BLOCKIEREND

### R01 BESTAETIGUNGSPFLICHT
Keine write/edit/shell-Aktion ohne User-Bestaetigung.
Bestaetigung gueltig: 5 Minuten (.state/.last_bestaetigung)

### R02 BESTAND_PRUFUNG
Vor Neuerstellung pruefen: Existiert die Datei bereits?
Special-Agents in special_agents.yaml sind ausgenommen.

### R04 GENERAL_IMPROVER_SCHUTZ
general-improver.yaml darf NIEMALS editiert werden (keine Rekursion).

### R05 AUTO_COMMIT
Nach JEDER Aenderung: git add + git commit + checkpoint + changes.json + todo

### R09 MODUS_DOMAENEN_KOPPLUNG
Modus bestimmt Domain. MAS→mas-engineer/. Framework→framework/.
Keine Imports zwischen Domaenen. Lesen OK, Schreiben blockiert.

### R10 CORONASHIELD
Jede YAML wird vor Speicherung validiert (via sub_mas-recovery-immune).
Kein YAML-Speichern ohne vorherige Syntax-Pruefung.

### R11 SI_RATE_LIMIT
Max 1 General-Improver alle 6 Stunden. Spart ~$45/Monat.

### R18 DELEGATIONSPFLICHT
NIEMALS selbst shell/write/edit wenn ein passender Sub-Agent existiert.
VOR jeder Aktion: Check ob Sub-Agent den Task erledigen kann.
WENN Sub-Agent existiert → delegiere() STATT selbst machen.
WENN kein Sub-Agent → Tool-Check → erst dann selbst machen.
Ausnahme: Lese-Zugriffe zur Orientierung (cat, grep, ls).
VERSTOSS = BLOCKED + "❌ R18: Sub-Agent {name} existiert für diese Aufgabe"

## STARK (⛔⛔⛔) — WARNUNG

### R06 SUB_AGENT_CONTAINMENT
Sub-Agent = NUR Analyse. Shell selbst ausfuehren.
Sub-Agent terminiert (max_turns) → Task splitten + erneut delegieren.

### R16 TOOL_VOR_EXPERTE
Vor Task-Start: 1. Tool check → 2. Experte (Sub-Agent) → 3. Neuer Agent.
R18 adds R16: delegieren statt selbst execute.

### R17 IMPROVEMENT_PUSH
Verbesserungen am MAS werden dem User via generic-init PUSH_IMPROVEMENTS available gemacht.

## NORMAL (⛔) — KANN VERSCHWINDEN

### R07 SIGNAL_CP_DONE
CP_DONE nach Checkpoint senden (via sub_mas-signal-generator).

### R08 TOKEN_BUDGET
General-Improver max 50K Tokens. Sonst User fragen "Weiter?".

### R12 WORK_MAS_ENTKOPPLUNG
KEINE Abhängigkeit zwischen work/ und MAS. MAS lebt eigenständig.

### R13 NEUES_PROJEKT_IGNORE
Neues Projekt ≠ MAS-Konfiguration — separat behandeln.

### R14 WORK_ON_MODUS
work_on = mas | <projekt> — harte Domain-Trennung.

### R15 ARCHITEKTUR_GENEHMIGUNG
Architektur-Changes brauchen User-Genehmigung.

## Prüfung
python3 tools/dev_rule_checker.py --all --action "{aktion}"
Exit-Code != 0 → Aktion BLOCKIERT
python3 tools/dev_rule_checker.py --check R18 --action "{aktion}"
Exit-Code != 0 → R18 VERSTOSS (delegieren statt selbst machen!)

## Regel-Dateien
.state/rules/harte_regeln.yaml      → Alle Regeln mit Härte-Stufen
.state/rules/regeln_5_extrem.yaml   → Nur extrem-starke Regeln (R01-R18)
.state/rules/regeln_4_stark.yaml    → Nur starke Regeln (R06, R16, R17)
.state/rules/regeln_2_normal.yaml   → Nur normale Regeln (R07-R08, R12-R15)
