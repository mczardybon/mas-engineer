# Hardening Rules R01-R18

## EXTREME-STRONG (⛔⛔⛔⛔⛔) — BLOCKING

### R01 CONFIRMATION-REQUIREMENT
No write/edit/shell-action without User-Confirmation.
Confirmation valid: 5 minutes (.state/.last_confirmation)

### R02 INVENTORY_CHECK
Before new creation check: Exists die file already?
Special-Agents in special_agents.yaml are exempted.

### R04 GENERAL_IMPROVER_PROTECTION
general-improver.yaml may NEVER edited will (no recursion).

### R05 AUTO_COMMIT
After EVERY change: git add + git commit + checkpoint + changes.json + todo

### R09 MODE_DOMAIN_COUPLING
Mode determines domain. MAS→mas-engineer/. framework→framework/.
No Imports between Domains. Read OK, Write blocked.

### R10 CORONASHIELD
Every YAML will be validated before storing (via sub_mas-recovery-immune).
No YAML-Save without beforeherige Syntax-Check.

### R11 SI_RATE_LIMIT
Max 1 General-Improver every 6 hours. Saves ~$45/month.

### R18 DELEGATION DUTY
NEVER shell/write/edit yourself if a matching sub-agent exists.
BEFORE every action: Check ob Sub-Agent den Task erledigen can.
IF Sub-Agent exists → delegate() INSTEAD OF doing it yourself.
IF no Sub-Agent → Tool-Check → erst then do it yourself.
Exception: Read-Accesse to the Orientierung (cat, grep, ls).
VERSTOSS = BLOCKED + "❌ R18: Sub-Agent {name} exists for these Task"

## STRONG (⛔⛔⛔) — WARNING

### R06 SUB_AGENT_CONTAINMENT
Sub-Agent = ONLY analysis. Execute shell yourself.
Sub-Agent terminates (max_turns) → Split task + delegate again.

### R16 TOOL_VOR_EXPERTE
Before task start: 1. Tool check → 2. Expert (Sub-Agent) → 3. Neuer Agent.
R18 adds R16: delegate instead of selbst execute.

### R17 IMPROVEMENT_PUSH
Improvements to MAS will be made available to the user via generic-init PUSH_IMPROVEMENTS.

## NORMAL (⛔) — CAN DISAPPEAR

### R07 SIGNAL_CP_DONE
CP_DONE after checkpoint sent (via sub_mas-signal-generator).

### R08 TOKEN_BUDGET
General-Improver max 50K tokens. Else ask user "Continue?".

### R12 WORK_MAS_DECOUPLING
NO dependency between work/ and MAS. MAS lives autonomously.

### R13 NEW_PROJECT_IGNORE
New Projekt ≠ MAS-Configuration — separate handle.

### R14 WORK_ON_MODE
work_on = mas | <projekt> — harte Domain-Trennung.

### R15 ARCHITECTURE_APPROVAL
Architecture changes need user approval.

## Check
python3 tools/dev_rule_checker.py --all --action "{action}"
Exit-Code != 0 → action BLOCKED
python3 tools/dev_rule_checker.py --check R18 --action "{action}"
Exit-Code != 0 → R18 VIOLATION (delegate instead of doing it yourself!)

## Rule-files
.state/rules/hard_rules.yaml      → All Rules mit Hardening Levels
.state/rules/rules_5_extreme.yaml   → Only extrem-starke Rules (R01-R18)
.state/rules/rules_4_strong.yaml    → Only strong rules (R06, R16, R17)
.state/rules/rules_2_normal.yaml   → Only normal rules (R07-R08, R12-R15)
