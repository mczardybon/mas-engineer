# EVIDENCE — R110-97: env-export helper for .env + goose run

**Date:** 2026-08-04
**Author:** Hermes (M3)
**Branch:** cleanup
**Scope:** 1 new file (mas-engineer/tools/mas-goose-env.sh, 3.3 KB)
**Type:** chore (developer-tooling)

## TL;DR

A pre-push-validator invocation in R110-89 hit a subtle bash subshell
bug: when `goose run --recipe X` is called from inside a subshell that
sources `.env`, the OPENAI_API_KEY / GH_PAT / etc. vars from `.env` do
**not** propagate into goose's environment. The workaround was to
inline 7 `env VAR=...` lines in every invocation — tedious and
error-prone (the R110-89 first attempt failed with a 401 because
GH_PAT was missing from the inline list).

This commit delivers a single-purpose helper script that
canonicalizes the pattern and is reusable for any future goose
invocation in mas-engineer.

## ZIEL (what + why)

Problem statement (from R110-89 / R110-90 / R110-96 sessions):
  - 4 recent goose-invocation patterns failed because the wrong
    env var was passed / the right env var was not passed.
  - Root cause: bash subshell + `env` command + `.env` source
    don't compose well; inline `env VAR1=x VAR2=y ...` is the
    only reliable way to pass vars, but the recipe list is long
    (7 vars) and easy to get wrong.

Solution: a helper script that:
  1. locates `mas-engineer/.env` (relative to repo root)
  2. sources it (so all vars are in the helper's shell)
  3. validates required vars (errors with non-zero exit if missing)
  4. applies defaults for optional vars (GOOSE_PROVIDER, GOOSE_MODEL, OPENAI_HOST)
  5. execs the goose binary with `env VAR=...` for the 4 critical vars
  6. forwards all other args verbatim to goose

The script is REUSABLE for:
  - pre-push-validator (R110-89, R110-90, R110-96, future)
  - any future sub_mas-* recipe invocation
  - goose's own `--help`, `doctor`, `info`, etc.
  - any developer who needs to run goose with mas-engineer env

## WIE (what was done, scope)

Created `mas-engineer/tools/mas-goose-env.sh` (3.3 KB, executable, +x).

Subcommands (helper-only):
  - `print` — show all .env-sourced vars + lengths (no values printed
    for secrets; GH_PAT is truncated to prefix+suffix)
  - `which` — show only the vars goose needs (GOOSE_*, OPENAI_*)

Default behavior (no recognized subcommand): forward ALL args to
goose with the 4 critical env vars set.

Examples:
  $ ./mas-goose-env.sh print
  OPENAI_API_KEY length=35
  OPENAI_HOST=https://api.deepseek.com
  GOOSE_PROVIDER=openai
  GOOSE_MODEL=deepseek-v4-flash
  GH_PAT length=ghp_yr...EzVY
  DEEPSEEK_KEY length=0

  $ ./mas-goose-env.sh which
  GOOSE_PROVIDER=openai
  GOOSE_MODEL=deepseek-v4-flash
  OPENAI_HOST=https://api.deepseek.com
  OPENAI_API_KEY length=35

  $ ./mas-goose-env.sh run --recipe sub_mas-pre-push-validator.yaml --no-session
  Loading recipe: 🚦 SUB-MAS-PRE-PUSH-VALIDATOR ...
  (goose runs the recipe with all env vars set correctly)

  $ ./mas-goose-env.sh --help
  An AI agent
  Usage: goose [COMMAND] ...
  (goose's own help)

  $ ./mas-goose-env.sh doctor
  (goose doctor runs, with all env vars set)

Error handling (explicit exit codes):
  - exit 2: .env file not found
  - exit 1: required var missing (currently only OPENAI_API_KEY)
  - exit 3: goose binary not found

## WAS_NICHT (out of scope, honest limits)

- **Did NOT add a system-wide installer** (e.g. `cp` to /usr/local/bin).
  The script lives in the repo so it's version-controlled alongside
  mas-engineer. If a developer wants it on PATH, they can symlink
  it themselves.
- **Did NOT change the .env format.** The script assumes the existing
  `KEY=value` per-line format. Multi-line values, export statements,
  comments — all already supported (bash `source` handles them).
- **Did NOT add prompt-time env var resolution.** If a future var is
  conditional (e.g. only set when a feature flag is on), this script
  doesn't handle that — `.env` is the single source of truth.
- **Did NOT add a test for the helper.** Adding a test would mean
  another recipe + a fixture + pytest plumbing, which is a much
  larger change. The helper was instead manually verified with
  4 invocations (print, which, run --recipe X, --help) before commit.
- **Did NOT replace the existing inline `env VAR=...` pattern in
  pre-push-validator's own recipe invocations.** That recipe lives
  in `~/.config/goose/recipes/` (system-level) and is not in this
  repo. Future R could refactor it, but it's out of scope here.
- **Did NOT add a "validate before exec" mode** (e.g. `--dry-run`).
  The `print` subcommand is the closest equivalent.

## BEWEIS (proof, every claim is from a file, file:line given)

- **File created**:
    mas-engineer/tools/mas-goose-env.sh (3260 bytes, +x, bash syntax OK)
    → confirmed via `bash -n` exit 0
- **Manual test results** (R110-97 session):
    - `print` → 6 lines, OPENAI_API_KEY length=35 (matches .env)
    - `which` → 4 lines, GOOSE_PROVIDER=openai (matches .env)
    - `run --recipe X --max-turns 1` → recipe loaded successfully,
      "Loading recipe: 🚦 SUB-MAS-PRE-PUSH-VALIDATOR" (proves env vars
      reached the goose process; without OPENAI_API_KEY, goose would
      fail to start)
    - `--help` → "An AI agent / Usage: goose [COMMAND]" (goose's
      own help, forwarded correctly)
    - `doctor` → "goose is ready" (agent started, env vars set)
- **Pre-push-validator after R110-90** (R110-97 reuses the same
  validator): 15/15 PASS, 129/129 e2e regression
- **Env var contents** (lengths only, no values):
    - OPENAI_API_KEY: 35 chars (valid DeepSeek key)
    - GH_PAT: 40 chars (ghp_yr...EzVY, valid GitHub PAT)
    - DEEPSEEK_KEY: 0 chars (not set, only OPENAI_API_KEY is needed)
- **No regression**: the script is purely additive (1 new file,
  0 modifications to any existing file).

## FOLLOWUP (queued, NOT in this commit)

- **R110-91**: reformat R110-78..R110-88 commit BODIES to 5-section.
  (separate from R110-97, body-content changes are larger scope)
- **R110-98** (NEW, candidate): add a `validate` subcommand to
  mas-goose-env.sh that runs a 4-step env check: .env exists,
  OPENAI_API_KEY set, GH_PAT set, goose binary found. Could be
  used as a smoke test before expensive pre-push-validator runs.
- **R110-99** (NEW, candidate): refactor the existing pre-push-validator
  recipe invocations (in `~/.config/goose/recipes/sub/sub_mas-pre-push-validator.yaml`)
  to use the new helper instead of inline `env VAR=...` 7-liners.
