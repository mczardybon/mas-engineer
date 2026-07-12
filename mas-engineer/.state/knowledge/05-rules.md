# Hardening Rules R01-R18

## EXTREM-STARK (⛔⛔⛔⛔⛔) — BLOCKIEREND

### R01 CONFIRMATIONSPFLICHT
No write/edit/shell-action without User-Confirmation.
Confirmation gueltig: 5 Minuten (.state/.last_confirmation)

### R02 INVENTORY_PRUFUNG
Vor Neuerstellung check: Exists die file already?
Special-Agents in special_agents.yaml are fromgenommen.

### R04 GENERAL_IMPROVER_SCHUTZ
general-improver.yaml may NEVER edited will (no recursion).

### R05 AUTO_COMMIT
Nach JEDER Change: git add + git commit + checkpoint + changes.json + todo

### R09 MODUS_DOMAENEN_KOPPLUNG
Modus determines Domain. MAS→mas-engineer/. framework→framework/.
No Imports between Domains. Read OK, Write blocked.

### R10 CORONASHIELD
Jede YAML will before memoryung validated (via sub_mas-recovery-immune).
No YAML-Save without beforeherige Syntax-Check.

### R11 SI_RATE_LIMIT
Max 1 General-Improver all 6 Stunden. Spart ~$45/Monat.

### R18 DELEGATION DUTY
NEVER selbst shell/write/edit if a passender Sub-Agent exists.
VOR jeder action: Check ob Sub-Agent den Task erledigen can.
IF Sub-Agent exists → delegiere() STATT do it yourself.
IF no Sub-Agent → Tool-Check → erst then do it yourself.
Exception: Read-Accesse to the Orientierung (cat, grep, ls).
VERSTOSS = BLOCKED + "❌ R18: Sub-Agent {name} exists for these Task"

## STARK (⛔⛔⛔) — WARNINGUNG

### R06 SUB_AGENT_CONTAINMENT
Sub-Agent = ONLY Analyse. Shell selbst fromexecuten.
Sub-Agent terminiert (max_turns) → Task splitten + again delegate.

### R16 TOOL_VOR_EXPERTE
Vor Task-Start: 1. Tool check → 2. Expert (Sub-Agent) → 3. Neuer Agent.
R18 adds R16: delegate instead of selbst execute.

### R17 IMPROVEMENT_PUSH
Verbetterungen am MAS will dem User via generic-init PUSH_IMPROVEMENTS available gemacht.

## NORMAL (⛔) — CAN VERSCHWINDEN

### R07 SIGNAL_CP_DONE
CP_DONE after Checkpoint send (via sub_mas-signal-generator).

### R08 TOKEN_BUDGET
General-Improver max 50K tokens. Else User ask "Weiter?".

### R12 WORK_MAS_ENTKOPPLUNG
NO Dependency between work/ und MAS. MAS lebt autonomous.

### R13 NEUES_PROJEKT_IGNORE
New Projekt ≠ MAS-Configuration — separate handle.

### R14 WORK_ON_MODUS
work_on = mas | <projekt> — harte Domain-Trennung.

### R15 ARCHITEKTUR_GENEHMIGUNG
Architecture-Changes need User-Genehmigung.

## Check
python3 tools/dev_rule_checker.py --all --action "{action}"
Exit-Code != 0 → action BLOCKIERT
python3 tools/dev_rule_checker.py --check R18 --action "{action}"
Exit-Code != 0 → R18 VERSTOSS (delegate instead of doing it yourself!)

## Rule-files
.state/rules/harte_rulen.yaml      → All Rules mit Hardening Levels
.state/rules/rulen_5_extrem.yaml   → Only extrem-starke Rules (R01-R18)
.state/rules/rulen_4_stark.yaml    → Only starke Rules (R06, R16, R17)
.state/rules/rulen_2_normal.yaml   → Only normale Rules (R07-R08, R12-R15)
