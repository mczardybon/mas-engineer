---
name: mas-engineer-workflow
description: Development workflow for MAS-Engineer Goose AI MCP project (github.com/mczardybon/mas-engineer)
category: devops
---

## When to use

Load this skill when: Development workflow for MAS-Engineer Goose AI MCP project (github.com/mczardybon/mas-engineer).

For mas-engineer framework development, this skill provides domain-specific guidance that supersedes generic workflows.



# MAS-Engineer Development Workflow

## Context
Goose AI MCP Multi-Agent System project. German-speaking user (mczardybon). Repository: github.com/mczardybon/mas-engineer

## Key Requirements
- **ALL text must be English only** — no mixed German/English
- **Translations must be semantic** ("sinngemäß übersetzt"), not word-for-word
- Project uses German-influenced naming ("mas" = Multi-Agent System)
- User corrects any mixed language immediately

## GitHub Push Pattern (CRITICAL, GH013 v2)

ALWAYS security-check VOR push:
- Use `<REDACTED>` for any test-fixture that looks like a PAT
- github ALERTS on anything matching PAT regex (even fake `ghp_aBcD...0123`)

Push command (master branch, mczardybon/mas-engineer):

```bash
# Use the actual PAT from Hermes memory, NOT from env or files:
git remote set-url origin https://${HERMES_GH_PAT}@github.com/mczardybon/mas-engineer.git
git push origin master
```

Verified push on 2026-07-22: 3 commits (339b460, f1f9589, e95a1f7) + 36431f0, ec7f262, 0874683.

## RECURSION_OVERRIDE Pattern (CRITICAL, IM-008, 2026-07-22)

mas-engineer self-improvement pipeline has a 24h cooldown between FULL_IMPROVEMENT runs. To run again within 24h, use the RECURSION_OVERRIDE env var:

```bash
# RECURSION_OVERRIDE=1 → APPLY_ONLY (apply pending patches, no new findings)
# RECURSION_OVERRIDE=2 → FULL pipeline (skip 24h cooldown, operator-initiated)

RECURSION_OVERRIDE=2 \
MAS_TASK=FULL_IMPROVEMENT \
MAS_CONFIRM=yes \
MAS_APPROVE=y \
MAS_WEB_RESEARCH=no \
goose run --recipe mas-engineer/recipe/sub/sub_mas-general-improver.yaml \
  --params "workspace=/path/to/mas-engineer-src,scan_scope=mas-engineer/recipe/sub/,task=FULL_IMPROVEMENT"
```

**Always** run as PTY background process (`pty=true`, `background=true`, `notify_on_complete=true`) to capture the full raw log. NEVER use `goose run --no-session` (it ends after 1 question and ignores stdin).

After completion:
1. Save PTY log to e2e-results/<date>-mas-engineer-runs/
2. Update `mas-engineer/.mase/schedule.yaml` (round++, timestamp)
3. Update `mas-engineer/.mase/changes.json` (add entry with run_id, patches, type, reason)
4. Commit (recipe changes + e2e-results in SAME commit)
5. Push to github

Verified successful 3 runs on 2026-07-22:
- run #0: framework mode APPLY_ONLY (idempotent) — proc_a77b60c36fed
- run #1: mas mode APPLY_ONLY (idempotent) — proc_70b717c031ab
- run #2: mas mode FULL pipeline, 5 marketing recipes + temperature:0.3 (MM4) — proc_cd2ad5c66396, commit 0874683
- run #3: mas mode FULL pipeline, 5 mas-recipes + summon (JJ1 critical fix static-analyzer) + 4x SINGLE ROLE (NN1) — proc_1066244a7182, commit 36431f0

## Semantic German→English Translation Rules

When translating German text to English, use meaning-preserving translations:

| German Pattern | English Equivalent |
|--------------|------------------|
| `Verhaltens*` | `Behavioral*` |
| `Ausführungs*` | `Execution*` |
| `Verarbeitungs*` | `Processing*` |
| `Kommunikations*` | `Communication*` |
| `Koordinations*` | `Coordination*` |
| `Synchronisations*` | `Synchronization*` |
| `Integrations*` | `Integration*` |
| `Zusammenarbeits*` | `Collaboration*` |
| `Qualitäts*` | `Quality*` |
| `Fehler*` | `Error*` |
| `Optimierung*` | `Optimization*` |
| `Konfiguration*` | `Configuration*` |
| `Initialisierung*` | `Initialization*` |
| `Steuerungs*` | `Control*` |
| `Bewertungs*` | `Assessment*` |
| `Meldungs*` | `Message*` |
| `Prüfung` | `Check` |
| `Überprüfung` | `Review` |
| `Analyse` (noun) | `Analysis` |
| `Analysen` (plural) | `Analyses` |
| `Bestaetigung` | `Confirmation` |
| `durchgeführt` | `executed` or `performed` |
| `erstellt` | `created` or `established` |
| `übernommen` | `taken over` or `handled` |
| `vorhanden` | `exists` or `available` |
| `festgelegt` | `set` or `configured` |

## Common Typo Patterns in This Project

From user's memory:
- `typee` → `type`
- `recipit` → `recipe`
- `heoldh` → `health`
- `imperver` → `improver`
- `ditign` → `design`
- `ditigner` → `designer`
- `titt` → `test`
- `refrith` → `refresh`
- `check_typee` → `check_type`
- `ittore` → `restore`
- `bitt` → `best`
- `argumentParser` → `ArgumentParser`
- `modulese_from_spec` → `module_from_spec`
- `exec_modulese` → `exec_module`

## Repository Structure

```
mas-engineer/
├── mas-engineer/tools/     # Python tools (~42 files)
├── mas-engineer/.mase/   # YAML configs, templates
│   ├── workflows.yaml
│   ├── best-practices.yaml
│   ├── templates/agent_schema.yaml
│   └── sub/               # Sub-agent YAMLs
├── mas-engineer/recipe/   # Recipe definitions
└── mas-engineer/docs/     # Documentation
```

## GitHub PAT
Stored in Hermes memory as `GH_PAT`. Reference: memory target="user". Never inline the raw token in skills or code.

## Telegram Bot Token
Stored in `~/.hermes/.env` as `TELEGRAM_BOT_TOKEN`. Never inline the raw token in skills, code, or commits.
