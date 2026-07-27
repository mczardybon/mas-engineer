#!/bin/bash
cd /workspace
export DEEPSEEK_API_KEY=<REDACTED> "^DEEPSEEK_API_KEY=<REDACTED>" /workspace/mas-engineer-src/mas-engineer/.env | cut -d= -f2-)
export OPENAI_API_KEY=<REDACTED>
export PATH="/root/.local/bin:$PATH"
export GOOSE_PROVIDER=openai
export GOOSE_MODEL=deepseek-v4-flash
export OPENAI_HOST=https://api.deepseek.com
PROMPT="Review the code at /workspace/mas-engineer-src/e2e-results/2026-07-27-pty-test/sample_code.py using code-reviewer. Use the recipe at /tmp/code-reviewer/recipe/code-reviewer.yaml. Report all issues found."
timeout 480 goose run --no-session --text "$PROMPT"
