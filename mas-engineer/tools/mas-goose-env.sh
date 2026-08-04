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

# 3. validate required vars (skip early-fail in 'validate' mode so user gets
# a full report of all missing vars + rc=4, not just the first one with rc=1)
if [ "${1:-}" != "validate" ]; then
    : "${OPENAI_API_KEY:?ERROR: OPENAI_API_KEY is required in .env}"
fi

# 4. apply defaults for optional vars
: "${GOOSE_PROVIDER:=openai}"
: "${OPENAI_HOST:=https://api.deepseek.com}"
: "${GOOSE_MODEL:=deepseek-v4-flash}"

# 5. dispatch: 'print', 'which', and 'validate' are helper-only; everything else forwards to goose
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
    validate)
        # Smoke test: verify everything needed to run goose is present and sane.
        # Use BEFORE expensive pre-push-validator runs to fail fast on config issues.
        # Returns: 0=all ok, 4=one or more checks failed (with details on stderr).
        # Each check prints "OK <name>" or "FAIL <name>: <reason>".
        fail_count=0
        check_pass() { echo "OK   $1"; }
        check_fail() { echo "FAIL $1: $2" >&2; fail_count=$((fail_count + 1)); }

        # Check 1: OPENAI_API_KEY set + plausible length (DeepSeek keys are 35 chars)
        KEY_LEN=0
        if [ -n "${OPENAI_API_KEY:-}" ]; then
            KEY_LEN="${#OPENAI_API_KEY}"
        fi
        if [ "$KEY_LEN" -ge 30 ]; then
            check_pass "OPENAI_API_KEY (length=$KEY_LEN)"
        else
            check_fail "OPENAI_API_KEY" "missing or too short (got length=$KEY_LEN, need >=30)"
        fi

        # Check 2: GH_PAT set + plausible format (ghp_ prefix + 30+ chars)
        if [ -n "${GH_PAT:-}" ] && [[ "${GH_PAT}" =~ ^ghp_[A-Za-z0-9]{30,}$ ]]; then
            check_pass "GH_PAT (length=${#GH_PAT}, ghp_ prefix OK)"
        else
            check_fail "GH_PAT" "missing or malformed (need ghp_<30+ alnum>)"
        fi

        # Check 3: goose binary present
        GOOSE_BIN="${GOOSE_BIN:-/root/.local/bin/goose}"
        if [ -x "$GOOSE_BIN" ]; then
            check_pass "goose binary ($GOOSE_BIN)"
        elif command -v goose >/dev/null 2>&1; then
            check_pass "goose binary ($(command -v goose) via PATH)"
        else
            check_fail "goose binary" "not found at $GOOSE_BIN and not in PATH"
        fi

        # Check 4: .env path is what we expect (sanity check after cd)
        if [ -f "$ENV_FILE" ]; then
            check_pass ".env present ($ENV_FILE)"
        else
            check_fail ".env file" "missing at $ENV_FILE"
        fi

        # Check 5: GOOSE_PROVIDER + GOOSE_MODEL + OPENAI_HOST are non-empty
        if [ -n "${GOOSE_PROVIDER:-}" ]; then check_pass "GOOSE_PROVIDER=$GOOSE_PROVIDER"; else check_fail "GOOSE_PROVIDER" "empty"; fi
        if [ -n "${GOOSE_MODEL:-}" ]; then check_pass "GOOSE_MODEL=$GOOSE_MODEL"; else check_fail "GOOSE_MODEL" "empty"; fi
        if [ -n "${OPENAI_HOST:-}" ]; then check_pass "OPENAI_HOST=$OPENAI_HOST"; else check_fail "OPENAI_HOST" "empty"; fi

        if [ "$fail_count" -eq 0 ]; then
            echo "VALIDATE OK: all checks passed, safe to run goose"
            exit 0
        else
            echo "VALIDATE FAIL: $fail_count check(s) failed" >&2
            exit 4
        fi
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
