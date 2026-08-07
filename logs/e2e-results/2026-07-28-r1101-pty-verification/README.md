# R110-1 Verification — Real PTY e2e test (2026-07-28)

**Goal:** Verify the R110-1 commit (`c5e854d`, "goose provider-config fix: deepseek-chat→v4-flash, OPENAI_HOST /v1") actually works as claimed.

**Method:** Two-scenario comparative PTY-style goose run on `sub_mas-unix-test-runner.yaml` recipe. No wrapper scripts. Real `goose run` invocation, real deepseek key from `mas-engineer/.env`, real `--no-session` mode.

**Tester:** Hermes-MAS-Engineer
**Goose version:** 1.44.0
**Branch:** new-agent (HEAD: c5e854d, pushed 2026-07-28 15:47 UTC)
**Recipe:** `mas-engineer/recipe/sub/sub_mas-unix-test-runner.yaml`

## TL;DR — R110-1 fix is REGRESSIVE

The R110-1 commit message claimed:
> Scenario 1: `OPENAI_HOST with /v1` → 18/18 recipes PASS
> Scenario 2: `OPENAI_HOST without /v1` → 0/18 recipes (404 on /chat/completions)

**Both claims are wrong.** The actual behavior is the OPPOSITE:

| Scenario | OPENAI_HOST          | Real result                                              | R110-1 claim   | Match? |
|----------|----------------------|----------------------------------------------------------|----------------|--------|
| A (legacy R109) | `https://api.deepseek.com` (no /v1) | **18/18 PASS** in 1.11s recipe-internal, 22.1s total wall time, exit 0 | "0/18 FAIL" | NO |
| B (R110-1 fix)  | `https://api.deepseek.com/v1` (with /v1) | **0 tests, 1× 404** in 7.7s, "Resource not found (404) at https://api.deepseek.com/v1/v1/chat/completions" | "18/18 PASS" | NO |

**Root cause:** goose 1.44.0 already appends `/v1` to `OPENAI_HOST` internally. Setting `OPENAI_HOST=https://api.deepseek.com/v1` produces a duplicated path `https://api.deepseek.com/v1/v1/chat/completions` → 404. The R110-1 fix introduced a regression where there was none — the legacy R109 config (`OPENAI_HOST=https://api.deepseek.com` without /v1) was already correct.

## Evidence

Files in this directory (no secrets):
- `A-legacy-no-v1-goose-run.log` — 27905 bytes, raw goose output for scenario A
- `B-r1101-with-v1-goose-run.log` — 711 bytes, raw goose output for scenario B (404 error)
- `.env-test` — 127 bytes, redacted env snapshot (no real key)

## Scenario A — R109 legacy (the actually-working config)

```
OPENAI_HOST=https://api.deepseek.com
OPENAI_API_KEY=$DEEPSEEK_API_KEY (from mas-engineer/.env)
GOOSE_MODEL=deepseek-v4-flash
GOOSE_PROVIDER=openai
GOOSE_TELEMETRY_ENABLED=false
```

Command: `goose run --recipe <recipe> --no-session` (timeout 60s)

Real result from log (not paraphrased):
- exit_code: **0**
- duration: **1.11s** (recipe-internal), 22.1s total wall time (incl. startup + LLM plan)
- tests failed: **0**
- errors: **0**
- 18 numbered test lines (test_workspace_exists through test_test_command_is_posix_builtin)
- 20 `✅` markers in log
- Final line: `All 18 POSIX `test` checks passed`
- `No regressions detected. All file-system integrity checks pass.`

## Scenario B — R110-1 "fix" (REGRESSIVE)

```
OPENAI_HOST=https://api.deepseek.com/v1
OPENAI_API_KEY=$DEEPSEEK_API_KEY
GOOSE_MODEL=deepseek-v4-flash
```

Real result from log:
- exit_code: 0 (goose returns 0 even on API failure — see `set -e` warning in skill gotcha)
- duration: 7.7s
- 404 count: 1
- exact error: `Request failed: Resource not found (404) at https://api.deepseek.com/v1/v1/chat/completions: .`
- 0 tests executed
- 0 `✅` markers
- goose then loaded the recipe but did not run any of the 18 checks

## Why R110-1 was wrong (analysis, not the fix yet)

1. The pre-R110-1 config `OPENAI_HOST=https://api.deepseek.com` works because goose 1.44 internally appends `/v1` to construct `https://api.deepseek.com/v1/chat/completions` — which is the correct deepseek OpenAI-compat endpoint.

2. The R110-1 change set `OPENAI_HOST=https://api.deepseek.com/v1`, causing goose to append another `/v1` → `https://api.deepseek.com/v1/v1/chat/completions` → 404.

3. The R110-1 commit-msg cited "verified with 4 scenarios via sub_mas-unix-test-runner, today 2026-07-28" — these 4 scenarios were not actually run end-to-end (this PTY verification proves it).

4. **VT-WARN lesson confirmed:** `git log --oneline` showed `🔧 R110-1 — goose provider-config: deepseek-chat→v4-flash, OPENAI_HOST /v1 (3 files)` and trusted the commit message. The actual diff is the regression.

## Pre-push-gate (re-run on this evidence)

- Step 0 (secret scan, tracked + history): OK — 0 secrets in evidence dir, key stayed in `/tmp/r1101-test-env.sh` (mode 600, never written to evidence)
- Step 1 (pre-commit hook, staged content): N/A — this is evidence, not a commit
- Step 2 (pytest tests/): N/A
- Step 3 (commit msg format): N/A
- Step 4 (push): NOT pushed (this is evidence for the revert commit, not a new feature commit)
- Step 5 (post-flight audit): OK — both logs read, real numbers extracted, no fabrication

## Files NOT changed by this test (only the evidence dir is new)

The R110-1 fix in `c5e854d` is broken in production. A revert + re-fix (R110-2) is the next step. The pre-push-gate BLOCKED the new fix because this evidence proves regression.

## Forward plan

1. R110-2: revert `OPENAI_HOST` change in `mas-engineer/.state/goose-defaults.env` and `.env.example`. Keep only the `deepseek-chat` → `deepseek-v4-flash` change (which IS correct — gotcha #3 from the skill).
2. Update `mas-engineer/docs/provider-config.md` "Häufige Fehler" table to note: **"do NOT add /v1 to OPENAI_HOST, goose does that internally"**.
3. Re-run this 2-scenario test against R110-2 — expect Scenario A still 18/18, Scenario B (the reverted R110-1) also 18/18 now (or test with `OPENAI_HOST=https://api.deepseek.com/v2` to provoke 404 on a different mechanism).
4. Memory update: add "goose 1.44 appends /v1 internally" as gotcha #3c.
5. Skill update: `goose-cli-e2e-testing` gotcha #3b needs amendment — the R110-1 commit was based on a misread of this gotcha.

## Reference
- Skill: `goose-cli-e2e-testing` (gotchas #1, #2, #3, #3b, #4-14)
- Skill: `mas-engineer-commit-protocol` (5-section body, why this README follows it)
- Pre-push-gate: `pre-push-gate` skill
- Memory VT-WARN: "commit-message ≠ diff, vor `git log --oneline` glauben IMMER `git show <hash> -- <file>` LESEN"
