# UX-Bug E2E Validation Report (2026-07-25)

## UX-Bug 1: --recipe + --text incompatible
**Status:** CONFIRMED (real goose CLI behavior, not fixable in MAS code)
- Test: `goose run --recipe x.yaml --text "hello"`
- Result: `error: the argument '--recipe' cannot be used with '--text'`
- Source: `goose run --help` output
- Workaround: put task in recipe's `prompt:` field
- Already documented in `~/.hermes/skills/goose-cli-e2e-runner/SKILL.md`

## UX-Bug 2: OPENAI_API_KEY in config file is IGNORED
**Status:** CONFIRMED (real goose bug, workaround in place)
- Test: 
  - config-file key: `sk-REDACTED-DEEPSEEK (35 chars)` (35 bytes)
  - env var: same key
  - without env: `Provider Check: Auth: FAILED 401`
  - with env: `Provider Check: Auth: ok, Connection: ok`
- Source: `goose info --check`
- Workaround: always set OPENAI_API_KEY in env (per `goose-cli-e2e-runner` skill)

## UX-Bug 3: deepseek-chat model is GONE (the one we fix)
**Status:** FIXED ✅ — was 400 error, now works
- Test (before fix): `curl .../v1/chat/completions -d 'model: deepseek-chat'` → 400 "supported API model names are deepseek-v4-pro or deepseek-v4-flash, but you passed deepseek-chat"
- Test (after fix): `model: deepseek-v4-flash` → 200 OK, 16 tokens
- Test (after fix in templates): `goose run --recipe recipe/test-mas-user.yaml` → starts with `● new session · openai deepseek-v4-flash`, delegates to director
- Files fixed: 8 (auto-dashboard-v2-update.yaml, dev_template_generator.py ×2, e2e_teams.py, dev_workspace.py, dev_template_engine.py, dev_install.sh, dashboard_prd_template.py)
- Bonus: F-1561 MODE-CHECK protocol confirmed working in real run

## Result
3 UX-Bugs investigated. 1 was a real MAS-config issue (fixed).
2 are real goose-CLI quirks (documented, not fixable in MAS code).
