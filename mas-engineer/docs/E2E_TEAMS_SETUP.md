# E2E Teams Test — Setup Guide

## What this test does

`tools/e2e_teams.py` is a real end-to-end test of the three demo business teams
that you create locally. It treats each team as a human would:

- Sends a real query (parameterized, not typed in a TUI)
- Verifies the team invokes the right sub-recipe via the `delegate` tool
- Asserts the response contains the expected completion marker
- Measures wall-clock time and saves full conversation logs

**3 teams × 3 difficulty levels = 9 tests** that take ~25 minutes total.

## Why the teams are not in this repo

mas-engineer is a framework. The demo teams (translator, sales, marketing) are
**example compositions** of the framework. Different users have different
business needs — your "sales team" might be different from another user's.

So you create the teams locally at `~/.config/goose/recipes/<team>/`. The
mas-engineer e2e test then verifies your teams actually solve real tasks.

## Where the teams must live

```
~/.config/goose/recipes/
├── translator/
│   └── translator-team.yaml
├── sales/
│   └── sales-team.yaml
└── marketing/
    └── marketing-team.yaml
```

Missing teams are **skipped** (not failed). Create all three for a full 9/9 run.

## How the test invokes your team

For each test, the runner generates a tiny **wrapper recipe** in `/tmp/`:

```yaml
name: e2e-teams-test-<team>-<level>
parameters:
  - key: source_text
    input_type: string
    requirement: required
    description: Text to translate
  - key: target_lang
    input_type: string
    requirement: required
    description: Target language
prompt: |
  Translate {{ source_text }} to {{ target_lang }}.
  You MUST invoke the `translator_team` sub_recipe via the delegate tool.
  Do NOT simulate the team yourself.
extensions:
  - type: builtin
    name: developer
sub_recipes:
  - name: translator_team
    path: /root/.config/goose/recipes/translator/translator-team.yaml
```

Then runs:
```bash
goose run --recipe <wrapper> --params source_text=Hello --params target_lang=German --no-session
```

The dev agent MUST invoke the sub_recipe via the `delegate` tool — this verifies
your team really runs, not just that the dev agent role-plays the team.

## What your team's recipe must declare

The team recipe must be **parameterizable** (declare parameters and use `{{ }}`
jinja substitution) so the wrapper can pass test inputs:

```yaml
# translator-team.yaml
name: translator-team
version: 1.0.0
title: Translation Team
description: 3 parallel translators + judge vote
prompt: |
  You are the translation team orchestrator.
  Translate the user's `source_text` to `target_lang` using 3 styles in parallel.
  Then have the judge vote for the best.
parameters:
  - key: source_text
    input_type: string
    requirement: required
    description: The text to translate
  - key: target_lang
    input_type: string
    requirement: required
    description: The target language (e.g. German, French)
  - key: source_lang
    input_type: string
    requirement: optional
    default: auto
    description: The source language (auto-detect if not provided)
extensions:
  - type: builtin
    name: developer
sub_recipes:
  - name: literal
    path: /path/to/literal.yaml
  - name: literary
    path: /path/to/literary.yaml
  - name: technical
    path: /path/to/technical.yaml
  - name: judge
    path: /path/to/judge.yaml
```

## Test cases per team

### translator
| Level  | Source text                                  | Target  | Marker     | Timeout |
|--------|----------------------------------------------|---------|------------|---------|
| easy   | "Hello world"                                | German  | `Hallo`    | 120s    |
| medium | HTTP-503 error explanation                  | German  | `Hallo`    | 150s    |
| hard   | Two English idioms (spilt milk, eggs in one basket) | German  | `Hallo`    | 180s    |

### sales
| Level  | Task                                                                | Marker         | Timeout |
|--------|---------------------------------------------------------------------|----------------|---------|
| easy   | "What can your team do?"                                            | `SALES-INFO`   | 120s    |
| medium | "Find 2 B2B SaaS leads in Berlin (AI/ML)"                          | `LEAD-DONE`    | 600s    |
| hard   | Full 5-agent pipeline for one Munich AI startup                    | `CLOSE-DONE`   | 300s    |

### marketing
| Level  | Task                                                                | Marker            | Timeout |
|--------|---------------------------------------------------------------------|-------------------|---------|
| easy   | "What can your team do?"                                            | `MARKETING-INFO`  | 120s    |
| medium | Draft 3 Twitter/X posts for AI code-review tool launch              | `TWEETS-DONE`     | 180s    |
| hard   | Full GTM plan for EU mid-market (5 specialists)                     | `GTM-DONE`        | 300s    |

## How to run

```bash
# Full 9-test suite (~25 min)
python3 tools/e2e_teams.py

# Single team
python3 tools/e2e_teams.py --team translator

# Single level
python3 tools/e2e_teams.py --level easy

# Just check team presence
python3 tools/e2e_teams.py --dry-run
```

## What gets saved

```
e2e-results/2026-07-22-teams-N/
├── raw-results.json          # full structured results
└── logs/
    ├── translator-easy.log   # last 2k chars of output
    ├── translator-medium.log
    ├── translator-hard.log
    ├── sales-easy.log
    ...
```

## Reading the results

Each test result has:
- `status`: `ok` / `fail` / `timeout` / `skip`
- `elapsed_s`: wall-clock time
- `marker_found`: bool, was the completion marker in the output?
- `sub_recipe_invoked`: bool, was the team actually called via `delegate`?
- `missing_keywords`: list of expected keywords that weren't found
- `reason`: human-readable failure explanation

A test passes only if:
1. The marker appears in the output
2. The `delegate` tool was called with the team name (NOT simulated)
3. All `expect_in_output` keywords are present

## What if a test fails?

1. **Check the log** at `e2e-results/<date>-teams-N/logs/<team>-<level>.log`
   (ANSI color codes are stripped automatically for readability)
2. Look for the `▸ delegate` tool call — is it pointing at your team?
3. Look for the sub-agent's tool calls (`▸ [subagent:XXX] shell`) — are they
   actually executing your team's logic?
4. If the team is being simulated (no `▸ delegate` call), the prompt is too
   weak — strengthen the wrapper's `prompt:` field to demand sub_recipe use.

## Implementation notes (for the curious)

The runner uses a **wrapper recipe pattern**:

- The wrapper recipe in `/tmp/e2e_teams_recipes/` declares the test parameters
  and references your team via the `sub_recipes:` array (plural).
- The wrapper's `prompt:` field uses `{{ }}` jinja substitution so test
  parameters (e.g. `source_text`) get passed to your team.
- The wrapper's prompt STRONGLY tells the dev agent to invoke the team via
  the `delegate` tool — this prevents the dev agent from role-playing the
  team itself.

**Why markers may not match in raw PTY output:** goose color-codes each
character of rendered text with ANSI escape codes. The runner strips
ANSI codes before matching markers — see `ansi_re.sub("", text)` in
`run_team_test()`.

## Prerequisites

- `goose` CLI installed at `/root/.local/bin/goose`
- DeepSeek API key configured (or any OpenAI-compatible endpoint via `OPENAI_HOST`)
- Your 3 team recipes at the paths shown above
- Each team recipe must declare parameters and use `{{ }}` jinja substitution
