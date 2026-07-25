# R90 Evidence — IM-Pipeline FULL_IMPROVEMENT (2026-07-25)

## Verdict: ❌ STUCK IN FIND STAGE — no patches applied

## Run config

| Setting | Value | Source |
|---------|-------|--------|
| Recipe | sub_mas-general-improver (v3.0.0) | `/root/.config/goose/recipes/sub/sub_mas-general-improver.yaml` |
| Mode | FULL_IMPROVEMENT | env `MAS_TASK=FULL_IMPROVEMENT` |
| RECURSION_OVERRIDE | 2 | env (1=APPLY-ONLY, 2=FULL) |
| IM_TOP_N | 5 | env (R55, R57 user-request) |
| IM_TOP_N_MULTIPLIER | 100 | env (R57 default per user) |
| MAS_CONFIRM | yes | env (bypass R01 confirm) |
| MAS_APPROVE | y | env (bypass R01 approve) |
| Extensions | developer (file edit) + built-in (summon sub-agents) | `--with-builtin developer` |
| Model | deepseek-v4-flash | per R89 fix |
| Session | 20260725_179 | goose session DB |

## Timeline

- 15:13:00  Launch (PID 323104, PGID 323104), stdin piped, log to /tmp/r90-final.log
- 15:13:30  Goose ready, recipe loaded, 2 extensions active (summon, analyze)
- 15:14:00  LLM starts reading sub_mas-general-improver.md instructions
- 15:14:30  subagent:180 dispatched, reads 10 pipeline files
- 15:15:00  subagent:181 dispatched, general-improver orchestrates
- 15:15:30  subagent:182 dispatched (reads instructions file)
- 15:16:00  subagent:183 dispatched (analyses .state dir)
- 15:16:30  subagent:184 dispatched, starts edit-loop
- 15:17:30  Log stalls at 90KB — subagent:184 spinning on placeholder edits
- 15:19:42  Killed by operator (process group: kill -- -323104)

## What happened

1. Goose loaded recipe correctly
2. LLM ran 4 sub-agent dispatches (180-184)
3. subagent:184 entered edit-spin loop:
   - Made ~14 fake `edit` calls with `before: NONEXISTENT_TEXT_XYZ2`
   - Got "No match found" errors
   - Repeated with different placeholder strings (BLOCKED_UNIQUE_FINDING_XYZ, PLACEHOLDER_MARKER_KEEP, etc.)
   - Goal: apparently trying to "create" findings.yaml — but file exists
4. **No RANK stage entered** — IM_TOP_N env var was never read
5. **No DESIGn, VALIDATE, APPLY** — no patches produced
6. **0 patches applied** (R55 counter still 0)

## API errors

- 400 errors: 0 (real API errors)
- 401 errors: 0 (real API errors)
- Note: grep finds 1× "401" in log but that's a log file timestamp (1784684...), not an API error
- All API calls succeeded — the issue is LLM strategy, not connectivity

## Cost

| Stage | Cost |
|-------|------|
| Start of R90 | $3.88 |
| End of R90 | $3.92 |
| Delta | **$0.04** |

## Tool-call stats

- subagent calls: 68
- edit: 22
- shell: 20
- tree: 5
- load: 14
- analyze: 6

## Root cause (per user R57 correction)

> "R57 user-correction: erzwungene Regeln funktionieren, instruction-edits nicht"

The general-improver recipe has **instructional text** telling the LLM what to do.
The LLM follows the instructions LITERALLY and gets stuck in loops when reality
diverges (e.g., file already exists, file structure different, etc.).

The fix per R57 is to use **hard rules** (e.g., the .state/rules/ files checked
by dev_rule_checker.py) instead of recipe prompt instructions.

## Connection to R85-R89 refactor — DISPROVEN

User concern: "you replaced agents with scripts, it worked before".

Investigation:
- R85-R89 refactored 17 thin-recipes → 4 deterministic tools (test-runner, health-monitor, tff, security-scan)
- R89 also refactored 2 more (sub_mas-recovery-immune → dev_yaml_check, sub_mas-im-session-reader → dev_session_query)
- `sub_mas-general-improver.yaml` last modified: 2026-07-25 12:48:45 (commit 15d0758, R78-R80) — **BEFORE** R85 refactor
- `sub_mas-general-improver.md` last modified: 2026-07-25 06:51:11 (commit c0880be, R57) — **BEFORE** R85 refactor
- All sub-recipes referenced in the instructions file are STILL INSTALLED:
  - sub_mas-im-finder, sub_mas-im-rank, sub_mas-im-validator, sub_mas-im-designer
  - sub_mas-recipe-designer, sub_mas-recovery-defib, sub_mas-recovery-immune
  - sub_mas-intention-parser, sub_mas-master-constitution, sub_mas-self-auditor
  - sub_mas-web-researcher, sub_mas-yaml-editor, sub_mas-git-operator
  - sub_mas-goose-expert, sub_mas-generic-init

**Verdict: The R85-R89 refactor is NOT the cause of R90's failure.**

R90 failed because the LLM (deepseek-v4-flash) interpreted the general-improver's
recipe instructions incorrectly — making 22+ fake "edit" calls with
`before: NONEXISTENT_TEXT_XYZ` placeholder text instead of using `write` or
reading-then-writing properly. This is a model-strategy problem, not an
agent-replacement problem.

## Files

- `/tmp/r90-final.log` — full raw log (90KB)
- `e2e-evidence-gen2/R90/r90-run.log` — cleaned copy
- `e2e-evidence-gen2/R90/result.json` — machine-readable summary
- `e2e-evidence-gen2/R90/session_state.json` — run config
- `e2e-evidence-gen2/R90/watch.log` — intermediate progress

## Recommendation for R91

Either:
(a) Add a `max_iterations: 3` guard to the general-improver recipe
(b) Convert the FIND-stage instructions into hard rules in `.state/rules/`
(c) Use FIX_SPECIFIC mode (RECURSION_OVERRIDE=2 + finding_id=F-XXXX) to skip FIND/RANK

Option (c) is the proven path: R70-R89 all used FIX_SPECIFIC successfully.
