#!/usr/bin/env bash
# mas-goose-env.sh -- single-purpose helper: source mas-engineer/.env and exec goose with all needed env vars set
#
# Why: `goose run` does NOT inherit shell vars from a sourced .env in some invocations
# (e.g. when wrapped in `env VAR=... bash -c "..."`, the parent shell vars get lost).
# This script is the canonical "I want to run goose with mas-engineer env" entry point.
#
# Usage:
#   mas-engineer/tools/mas-goose-env.sh print               # show all .env vars (sanity check)
#   mas-engineer/tools/mas-goose-env.sh which               # show GOOSE_* + OPENAI_* (what goose gets)
#   mas-engineer/tools/mas-goose-env.sh <goose-args...>     # forward ALL args to goose binary
#
# Examples (use the simplest form that works for your case):
#   $ ./mas-goose-env.sh run --recipe sub_mas-pre-push-validator.yaml --no-session
#   $ ./mas-goose-env.sh --help                              # goose's own --help
#   $ ./mas-goose-env.sh doctor                              # goose's doctor subcommand
#
# Reads: mas-engineer/.env (relative to repo root, 2 levels up from this script)
# Required vars (errors if missing): OPENAI_API_KEY
# Optional vars (defaults applied if missing): GOOSE_PROVIDER, GOOSE_MODEL, OPENAI_HOST
# Passed-through (no validation): GH_PAT, DEEPSEEK_KEY, any other
#
# Exit codes: 0=ok, 1=missing required var, 2=.env not found, 3=goose not found
set -euo pipefail

# locate repo root (this script lives in mas-engineer/tools/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="$REPO_ROOT/mas-engineer/.env"

# 1. sanity: .env exists
if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: .env not found at $ENV_FILE" >&2
    exit 2
fi

# 2. source .env
# shellcheck disable=SC1090
. "$ENV_FILE"

# 3. validate required vars
: "${OPENAI_API_KEY:?ERROR: OPENAI_API_KEY is required in .env}"

# 4. apply defaults for optional vars
: "${GOOSE_PROVIDER:=openai}"
: "${OPENAI_HOST:=https://api.deepseek.com}"
: "${GOOSE_MODEL:=deepseek-v4-flash}"

# 5. dispatch: 'print' and 'which' are helper-only, everything else forwards to goose
subcommand="${1:-}"
case "$subcommand" in
    print)
        echo "OPENAI_API_KEY length=${#OPENAI_API_KEY}"
        echo "OPENAI_HOST=$OPENAI_HOST"
        echo "GOOSE_PROVIDER=$GOOSE_PROVIDER"
        echo "GOOSE_MODEL=$GOOSE_MODEL"
        echo "GH_PAT length=${GH_PAT:-0}"
        echo "DEEPSEEK_KEY length=${DEEPSEEK_KEY:-0}"
        exit 0
        ;;
    which)
        echo "GOOSE_PROVIDER=$GOOSE_PROVIDER"
        echo "GOOSE_MODEL=$GOOSE_MODEL"
        echo "OPENAI_HOST=$OPENAI_HOST"
        echo "OPENAI_API_KEY length=${#OPENAI_API_KEY}"
        exit 0
        ;;
esac

# 6. forward all args to goose with env vars set
GOOSE_BIN="${GOOSE_BIN:-/root/.local/bin/goose}"
if [ ! -x "$GOOSE_BIN" ]; then
    if command -v goose >/dev/null 2>&1; then
        GOOSE_BIN="$(command -v goose)"
    else
        echo "ERROR: goose not found at $GOOSE_BIN and not in PATH" >&2
        exit 3
    fi
fi
# exec replaces this script (no extra shell layer)
exec env \
    OPENAI_API_KEY="$OPENAI_API_KEY" \
    OPENAI_HOST="$OPENAI_HOST" \
    GOOSE_PROVIDER="$GOOSE_PROVIDER" \
    GOOSE_MODEL="$GOOSE_MODEL" \
    "$GOOSE_BIN" "$@"
