# Provider-Configuration in mas-engineer

**Status:** R108-11 — Zentralisierte Provider-Config via env-vars.
**Date:** 2026-07-27
**Updated:** 2026-07-28 — deepseek-chat → deepseek-v4-flash (R110-1)
**Updated:** 2026-07-28 — R110-3 fix: OPENAI_HOST reverted (do NOT add /v1, goose does that)
**Evidence:** `logs/e2e-results/2026-07-28-r1101-pty-verification/README.md` (R110-2)

## Problem

In 215 recipe-yamls `settings.goose_provider: openai` was hardcoded. This had two drawbacks:

1. **Provider-switching is effortful**: 215 files have to be edited individually
2. **Inconsistency**: Some recipes had other values, tool-yamls others

## Solution

**Central Config:** `mas-engineer/.mase/goose-defaults.env`

Before every recipe-run:

```bash
cd /workspace/mas-engineer-src
source mas-engineer/.mase/goose-defaults.env
goose run --recipe mas-engineer/recipe/sub/sub_mas-migration-helper.yaml
```

## How does it work?

Goose precedence (highest first):

1. **Environment variables** (`GOOSE_PROVIDER`, `GOOSE_MODEL`, `OPENAI_HOST`, `OPENAI_API_KEY`)
2. **Recipe settings** (`settings.goose_provider`, `settings.goose_model`)
3. **Built-in defaults** (`openai` + `deepseek-v4-flash`)

→ When env-vars are set, recipe settings are ignored.

Verified R108-11: goose 1.43.0 reads `openai deepseek-chat` from env-var, even when recipe has no `settings.goose_provider`.

## Switching providers

```bash
# Switch to Anthropic
export GOOSE_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-...
goose run --recipe <recipe.yaml>

# Switch to Ollama (local)
export GOOSE_PROVIDER=ollama
export OLLAMA_HOST=http://localhost:11434
goose run --recipe <recipe.yaml>

# Switch to OpenAI (real, not DeepSeek-compatible)
export GOOSE_PROVIDER=openai
export OPENAI_API_KEY=sk-...  # real OpenAI key
unset OPENAI_HOST  # important: otherwise deepseek gets hit
goose run --recipe <recipe.yaml>
```

## What about the 215 recipe-yamls?

**Current:** `settings.goose_provider: openai` is still present, but env-vars override it.
**Planned R109+:** Cleanup — remove provider-settings from recipes, as soon as e2e-tests for all 215 are possible.

## Auto-load (optional)

Add to `~/.bashrc`:

```bash
# Auto-load mas-engineer provider defaults
[ -f /workspace/mas-engineer-src/mas-engineer/.mase/goose-defaults.env ] && \
  source /workspace/mas-engineer-src/mas-engineer/.mase/goose-defaults.env
```

## Validation

```bash
# Check: is .mase/goose-defaults.env valid?
bash -n mas-engineer/.mase/goose-defaults.env && echo "OK"

# Check: provider effectively set after source?
source mas-engineer/.mase/goose-defaults.env
echo "GOOSE_PROVIDER=$GOOSE_PROVIDER"     # expected: openai
echo "GOOSE_MODEL=$GOOSE_MODEL"           # expected: deepseek-v4-flash (not deepseek-chat, deprecated 2026-07-23)
echo "OPENAI_HOST=$OPENAI_HOST"           # expected: https://api.deepseek.com (NO /v1, goose 1.44 adds it)
```

## Common errors (2026-07-28, updated R110-3)

| Error | Symptom | Fix |
|-------|---------|-----|
| `OPENAI_HOST=https://api.deepseek.com/v1` (with `/v1`) | 404 Not Found at `/v1/v1/chat/completions` | omit `/v1` — goose 1.44 appends it internally |
| `GOOSE_MODEL=deepseek-chat` | 401 Unauthorized (deprecated 2026-07-23) | use `deepseek-v4-flash` |
| `OPENAI_API_KEY` in `~/.config/goose/config.yaml` | `goose info --check` reports Auth: FAILED | set as env-var |
| Key in commit message / markdown file | GitHub revoked + email alert | `sk-***REDACTED***` placeholder |

**Important (R110-3 lesson):** R110-1 had the OPENAI_HOST row of the common-errors table INVERTED
("without /v1 → 404, fix: append /v1"). Reality is exactly the opposite: WITH /v1 → 404 (doubled),
WITHOUT /v1 → 18/18 PASS. PTY evidence: `logs/e2e-results/2026-07-28-r1101-pty-verification/`.

## R108-11 References

- Commit: see `git log --oneline | head`
- Research: `goose-docs.ai/docs/guides/environment-variables/`
- Test: `goose run --recipe /tmp/test-no-provider.yaml` (no `settings.goose_provider`) → env-var wins.
