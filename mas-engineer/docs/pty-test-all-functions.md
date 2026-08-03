# PTY Test for All MAS-Engineer Functions

Reproducible live-PTY end-to-end test for every `sub_mas-*.yaml` recipe in
the mas-engineer repository. Generalized from R110-27 (which was hardcoded
to 30 demo-team agents) into a CLI that auto-discovers, wraps, and tests
the **entire** sub-agent fleet.

## What it does

For each `recipe/sub/sub_mas-*.yaml`:

1. Builds a **canary prompt**: "Identify yourself (name + version) and
   state your primary function in one sentence."
2. Wraps it in a `wrappers/<name>.yaml` recipe that:
   - Loads the original sub-agent as a sub_recipe
   - Owns the canary prompt (so `--no-session` works)
   - Sets `max_steps: 5` (just answer + exit)
3. Runs `goose run --recipe <wrapper> --no-session` via `script(1)` PTY
4. Parses output: PASS / FAIL / TIMEOUT / AUTH_FAIL / NOT_FOUND / EMPTY
5. Writes per-agent log + aggregate `SUMMARY.txt` + `RESULT.json`

## Usage

```bash
# Smoke: first 3 dev-* recipes (~7s)
bash scripts/r11070-mas-engineer-all-functions-pty.sh --first 3 --filter dev

# Full run: all ~110 recipes (~6-10 min)
bash scripts/r11070-mas-engineer-all-functions-pty.sh

# Filter by category
bash scripts/r11070-mas-engineer-all-functions-pty.sh --filter dashboard
bash scripts/r11070-mas-engineer-all-functions-pty.sh --filter e2e
bash scripts/r11070-mas-engineer-all-functions-pty.sh --filter python-repair

# Custom timeout (default 120s)
bash scripts/r11070-mas-engineer-all-functions-pty.sh --timeout 60

# Build wrappers/tasks only, don't invoke goose
bash scripts/r11070-mas-engineer-all-functions-pty.sh --dry-run

# Custom result dir
bash scripts/r11070-mas-engineer-all-functions-pty.sh --result-dir /tmp/my-run
```

## CLI flags

| Flag | Effect | Default |
|------|--------|---------|
| `--filter SUBSTR` | only test recipes whose name contains SUBSTR | all |
| `--first N` | only test first N recipes (after filter) | all |
| `--dry-run` | only build wrappers/tasks, do not invoke goose | off |
| `--timeout SEC` | per-recipe timeout | 120 |
| `--result-dir DIR` | custom result dir | timestamped `e2e-results/<date>-r11070-...` |

## Output structure

```
<result-dir>/
├── .dry-run                     # only if --dry-run
├── tasks.yaml                   # canary prompts (one per recipe)
├── manifest.json                # recipe inventory (name, title, description)
├── wrappers/                    # generated wrapper-recipes
│   ├── agent-guardian.yaml
│   ├── bootstrap.yaml
│   └── ...
├── agent-logs/                  # per-recipe logs (polished)
│   ├── agent-guardian.log
│   ├── agent-guardian.log.pty.log
│   └── ...
├── SUMMARY.txt                  # human-readable table
└── RESULT.json                  # machine-readable (n_pass, n_fail, ...)
```

## Pipeline steps (verbose)

The script runs 4 steps in order. Each fails fast on error.

**Step 0 — fail-fast validation**
- `DEEPSEEK_API_KEY` length ≥ 30 (not a placeholder)
- `OPENAI_API_KEY` shim from `DEEPSEEK_API_KEY` (if empty)
- `OPENAI_HOST=https://api.deepseek.com` (no /v1)
- `GOOSE_MODEL=deepseek-v4-flash` (not `-chat`)
- `PATH` includes `/root/.local/bin`

**Step 1 — API smoke**
- `curl /v1/models` with bearer token, expects HTTP 200

**Step 2 — discover + build manifest + tasks + wrappers**
- `glob recipe/sub/sub_mas-*.yaml` (excludes `*.llm-backup-r89`)
- Apply `--filter` and `--first N`
- Generate canary task per recipe
- Write `tasks.yaml`, `manifest.json`, `wrappers/*.yaml`
- If `--dry-run`: write `.dry-run` marker, exit before Step 3

**Step 3 — R10 CORONASHIELD pre-flight**
- Run `scripts/r11028-r10-validate.py` on `wrappers/`
- Abort if any wrapper is not R10-conform

**Step 4 — real LLM run per recipe**
- For each wrapper: `script -qec "bash -c 'goose run ... --no-session'" log.pty`
- Timeout: 120s (configurable via `--timeout`)
- Status classification:
  - `PASS` — rc=0, response ≥ 200B
  - `EMPTY` — rc=0, response < 200B (LLM didn't actually respond)
  - `TIMEOUT` — process killed at timeout (rc=124)
  - `AUTH_FAIL` — output contains "401 Unauthorized" or "Authentication failed"
  - `NOT_FOUND` — output contains "404 Not Found"
  - `FAIL` — any other non-zero exit
- Write per-recipe polished log + append to `SUMMARY.txt` and `RESULT.json`

## Why this is reproducible

- **Idempotent**: re-run overwrites the result-dir
- **No manual authoring**: tasks are generated from recipe YAML
- **Deterministic ordering**: `sorted(glob(...))`
- **No external state**: pure read of `recipe/sub/`, pure write to result-dir

## Gotchas applied (see goose-cli-e2e-testing skill)

- **#2** `OPENAI_API_KEY` from env, not config
- **#3** `GOOSE_MODEL=deepseek-v4-flash` (not `-chat`)
- **#3b** `OPENAI_HOST=https://api.deepseek.com` (no `/v1`)
- **#16** No `export X=***` after `source` (placeholders)
- **#17** `set -o pipefail`
- **#18** `OPENAI_API_KEY` falls back to `DEEPSEEK_API_KEY`
- **#19** `script -qec` uses `bash -c` (not `sh` default)
- **#20** No overwrite after `source`
- **#21** R10 CORONASHIELD pre-flight before any goose run

## Verification (last full run, 2026-08-03)

- Total recipes: 110 (after filter+sort)
- PASS: 110
- FAIL: 0
- Total walltime: ~6 min
- All agents identified themselves correctly
- E2E evidence: `e2e-results/2026-08-03-r11070-mas-engineer-all-functions-pty/`

## When to run

- **After any change to `recipe/sub/*.yaml`**: at least smoke test
  (`--first 10 --filter <changed-area>`) to catch obvious regressions
- **Before a release** (e.g. before `sub_mas-bootstrap` rebuilds the
  distribution): full run, expect 110/110 PASS
- **When investigating "agent X is broken" reports**: `--filter X` for
  isolated reproduction
- **CI integration** (future): the script returns rc=0 iff all PASS,
  non-zero otherwise. Suitable for `bash -e` pipeline.

## Relationship to other test infrastructure

| Script | Scope | Notes |
|--------|-------|-------|
| `scripts/r11027-reproducible-30agent-live-pty.sh` | 30 demo-team agents (hardcoded) | R110-27 — original pattern |
| `scripts/r11028-r10-validate.py` | R10 CORONASHIELD YAML validator | used as pre-flight by R110-70 |
| **`scripts/r11070-mas-engineer-all-functions-pty.sh`** | **all 110 mas-engineer sub-agents** | **this script** |
| `tests/test_*.py` (21+) | pytest unit/integration tests | python-level coverage |
| `scripts/e2e-full-pipeline.sh` | full pipeline (multiple tools) | different scope |

## See also

- `docs/goose-cli-e2e-testing.md` (skill) — PTY/CLI gotchas
- `docs/verification-theater-guard.md` (skill) — how to avoid false
  positives like the one we fixed in `r11028-r10-validate.py`
- `docs/commit-protocol.md` (skill) — what a good commit message must
  claim and how to prove it
