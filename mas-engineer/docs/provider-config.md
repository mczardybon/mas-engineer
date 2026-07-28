# Provider-Configuration in mas-engineer

**Status:** R108-11 — Zentralisierte Provider-Config via env-vars.
**Date:** 2026-07-27
**Updated:** 2026-07-28 — deepseek-chat → deepseek-v4-flash, OPENAI_HOST /v1 fix

## Problem

In 215 recipe-yamls war `settings.goose_provider: openai` hardcodiert. Das hatte zwei Nachteile:

1. **Provider-Wechsel aufwändig**: 215 files einzeln editieren
2. **Inkonsistenz**: Manche recipes hatten andere werte, tool-yamls andere

## Lösung

**Zentrale Config:** `mas-engineer/.state/goose-defaults.env`

Vor jedem recipe-run:

```bash
cd /workspace/mas-engineer-src
source mas-engineer/.state/goose-defaults.env
goose run --recipe mas-engineer/recipe/sub/sub_mas-migration-helper.yaml
```

## Wie funktioniert es?

Goose precedence (höchste zuerst):

1. **Environment variables** (`GOOSE_PROVIDER`, `GOOSE_MODEL`, `OPENAI_HOST`, `OPENAI_API_KEY`)
2. **Recipe settings** (`settings.goose_provider`, `settings.goose_model`)
3. **Built-in defaults** (`openai` + `deepseek-v4-flash`)

→ Wenn die env-vars gesetzt sind, werden recipe-settings ignoriert.

Verified R108-11: goose 1.43.0 nimmt `openai deepseek-chat` aus env-var, auch wenn recipe kein `settings.goose_provider` hat.

## Provider wechseln

```bash
# Auf Anthropic wechseln
export GOOSE_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-...
goose run --recipe <recipe.yaml>

# Auf Ollama (lokal)
export GOOSE_PROVIDER=ollama
export OLLAMA_HOST=http://localhost:11434
goose run --recipe <recipe.yaml>

# Auf OpenAI (echtes, statt DeepSeek-kompatibel)
export GOOSE_PROVIDER=openai
export OPENAI_API_KEY=sk-...  # echter OpenAI key
unset OPENAI_HOST  # wichtig: sonst wird deepseek getroffen
goose run --recipe <recipe.yaml>
```

## Was ist mit den 215 recipe-yamls?

**Aktuell:** `settings.goose_provider: openai` steht noch drin, wird aber von env-var überschrieben.
**Geplant R109+:** Cleanup — provider-settings aus recipes entfernen, sobald e2e-tests für alle 215 möglich.

## Auto-load (optional)

Füge in `~/.bashrc`:

```bash
# Auto-load mas-engineer provider defaults
[ -f /workspace/mas-engineer-src/mas-engineer/.state/goose-defaults.env ] && \
  source /workspace/mas-engineer-src/mas-engineer/.state/goose-defaults.env
```

## Validierung

```bash
# Check: ist .state/goose-defaults.env gültig?
bash -n mas-engineer/.state/goose-defaults.env && echo "OK"

# Check: provider effektiv gesetzt nach source?
source mas-engineer/.state/goose-defaults.env
echo "GOOSE_PROVIDER=$GOOSE_PROVIDER"     # soll: openai
echo "GOOSE_MODEL=$GOOSE_MODEL"           # soll: deepseek-v4-flash (not deepseek-chat, deprecated 2026-07-23)
echo "OPENAI_HOST=$OPENAI_HOST"           # soll: https://api.deepseek.com/v1 (with /v1!)
```

## Häufige Fehler (2026-07-28)

| Fehler | Symptom | Fix |
|--------|---------|-----|
| `OPENAI_HOST=https://api.deepseek.com` (ohne `/v1`) | 404 Not Found | `/v1` anhängen |
| `GOOSE_MODEL=deepseek-chat` | 401 Unauthorized | `deepseek-v4-flash` benutzen |
| `OPENAI_API_KEY` in `~/.config/goose/config.yaml` | `goose info --check` meldet Auth: FAILED | Als env-var setzen |
| Key in commit message / markdown file | GitHub revoked + email alert | `sk-***REDACTED***` placeholder |

## R108-11 Referenzen

- Commit: siehe `git log --oneline | head`
- Research: `goose-docs.ai/docs/guides/environment-variables/`
- Test: `goose run --recipe /tmp/test-no-provider.yaml` (kein `settings.goose_provider`) → env-var gewinnt.
