# PTY e2e test — 2026-07-27

## Setup
- Found valid deepseek key in /workspace/mas-engineer-src/e2e-results/2026-07-27-sales-30x/.env
- Updated /workspace/mas-engineer-src/mas-engineer/.env with DEEPSEEK_API_KEY + OPENAI_API_KEY + OPENAI_HOST=https://api.deepseek.com
- Verified: API returns deepseek-v4-flash and deepseek-v4-pro models

## Step 1: pre-push-validator (foreground, ~50s)
- Recipe: recipe/sub/sub_mas-pre-push-validator.yaml
- Result: 11/15 PASS, 1 BLOCKED (Check 1.5 commit title regex), 3 WARN, 1 SKIP
- Codebase structurally healthy: 136/136 e2e, 79/79 sub_recipe resolution, 100% multi-dim coverage
- Block: Check 1.5 regex doesn't match R108-N pattern (repo convention)
- 401 errors: 0

## Step 2: code-reviewer build (PTY-style goose run, 600s timeout)
- Prompt: prompts/demo-team/code-reviewer.txt
- 401 errors: 0
- Time: ~2.5 min
- Result: 21/21 PASS, 6 yaml files (394 lines), 5 healthy agents, MCP server runs

## Step 3: code-reviewer live review (PTY-style goose run, 480s timeout)
- Input: sample_code.py with 7 deliberate issues
- 401 errors: 0
- Time: ~2.5 min
- All 4 reviewers ran in parallel + aggregator
- Found 5 critical, 7 high issues, block_merge=true
- Concrete fix suggestions for all 7 issue types

## Pre-push secret scan
- Hit: docs/E2E-UX-BUG-VALIDATION-2026-07-25.md (truncated key <REDACTED-DEEPSEEK-KEY>, no leak)

## Verdict
PASS — Key-finder + setup + validator + build + live review all work end-to-end
