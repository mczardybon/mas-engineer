#!/bin/bash
set -e
cd /workspace
export DEEPSEEK_API_KEY=<REDACTED> "^DEEPSEEK_API_KEY=<REDACTED>" /workspace/mas-engineer-src/mas-engineer/.env | cut -d= -f2-)
export OPENAI_API_KEY=<REDACTED>
export PATH="/root/.local/bin:$PATH"
export GOOSE_PROVIDER=openai
export GOOSE_MODEL=deepseek-v4-flash
export OPENAI_HOST=https://api.deepseek.com
PROMPT_FILE=/workspace/mas-engineer-src/mas-engineer/prompts/demo-team/code-reviewer.txt
timeout 600 goose run --no-session --text "$(cat $PROMPT_FILE)"
