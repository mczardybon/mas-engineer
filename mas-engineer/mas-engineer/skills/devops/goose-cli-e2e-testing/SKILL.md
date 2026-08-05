---
name: goose-cli-e2e-testing
description: How to actually run and test a goose CLI recipe end-to-end like a human operator — PTY/interactive control, the --recipe+--text incompatibility, config-file vs env-var auth, model-name gotchas, OPENAI_HOST /v1 requirement, sub_recipes dispatch, R10 CORONASHIELD manual validation, and the full evidence/verification checklist. Supersedes goose-cli-human-operator, mas-engineer-goose-cli-human-test, and goose-cli-e2e-runner (merged 2026-07-28, previously 3 overlapping skills discovered independently on 2026-07-19, 2026-07-22, 2026-07-23; extended 2026-07-28 with 5 new gotchas from real e2e run; extended 2026-07-29 with R10 CORONASHIELD gotcha + scripts/r11028-r10-validate.py tool from R110-28/R110-29).
category: devops
---

# Goose CLI E2E Testing — human-operator pattern, gotchas, and evidence checklist

## When to use
- Testing mas-engineer (or any goose-recipe-based framework) end-to-end, the way a human developer would — not via wrapper scripts that call `goose run` internally and just report "all PASS".
- Any time you need to run `goose run --recipe X` and INTERACT with it (multi-turn, follow-ups, mid-session tasks).
- NOT for simple one-shot tasks without a recipe (use `goose run -t "..."` instead — see gotcha #1 below).

## Core principles (user corrections, 2026-07-19 / 2026-07-22)
1. **Install into a real goose instance** (recipes go to `~/.config/goose/recipes/`).
2. **Operate the CLI like a human** — short prompts, short commands, no orchestration framework wrapped around the goose calls.
3. **NO wrapper scripts that call `goose run` internally** and then claim "all PASS" — the user explicitly rejected this pattern.
4. **Fresh start before each test run**: `rm -rf /tmp/<team-name>` and any stale e2e-evidence folder so old logs don't pollute results.
5. **Real key in the shell environment only, never in a file**:
   ```bash
   export DEEPSEEK_API_KEY=sk-...      # real key here, never committed
   export PATH="/root/.local/bin:$PATH"
   export GOOSE_PROVIDER=openai
   export GOOSE_MODEL=deepseek-v4-flash   # NOT deepseek-chat — see gotcha #3
   export OPENAI_HOST=https://api.deepseek.com   # NO /v1 — see gotcha #3b/c
   export OPENAI_API_KEY=$DEEPSEEK_API_KEY
   ```
   Use `***REDACTED***` as a placeholder in any markdown/code sample that mentions the key.

## Key gotchas (each verified with proof)

### 1. `--recipe` and `--text` are mutually exclusive
```
error: the argument '--recipe <RECIPE_NAME or FULL_PATH_TO_RECIPE_FILE>' cannot be used with '--text <TEXT>'
```
The docs say `-t, --text <TEXT>` works, but not together with `--recipe`. To pass a task non-interactively, put it in the recipe's `prompt:` field, not via CLI flag. (Observed 2026-07-22.)

### 2. Config-file `OPENAI_API_KEY` is silently ignored (partial fix)
Even with a byte-perfect key in `/root/.config/goose/config.yaml`, `goose info --check` returns `Auth: FAILED 401`. The **same key** set as an environment variable returns 200. Verified identical 35 bytes both ways — this is a goose-internal bug or undocumented requirement.
**Fix: always set `OPENAI_API_KEY` in the environment, never rely on the config file alone.**
**However**: `OPENAI_HOST` and `OPENAI_MODEL` in the config file ARE respected (verified 2026-07-28 with `/root/.config/goose/config.yaml`). So:
- `OPENAI_HOST`, `OPENAI_MODEL`, `GOOSE_TELEMETRY_ENABLED` → config-file OK
- `OPENAI_API_KEY` → MUST be env-var, never config-file alone

### 3. `deepseek-chat` model is deprecated/gone
`/v1/models` only returns `deepseek-v4-flash` and `deepseek-v4-pro`. A config with `GOOSE_MODEL: deepseek-chat` 401s because the model doesn't exist server-side. Use `deepseek-v4-flash` (faster, cheaper) or `deepseek-v4-pro`.

### 3b. `OPENAI_HOST` MUST NOT end with `/v1` — goose adds it internally (R110-3 fix)
**CORRECTED 2026-07-28 (R110-3):** `OPENAI_HOST=https://api.deepseek.com` (NO trailing `/v1`).
With `/v1` already in the env-var, goose's internal client appends another `/v1` and the
final URL becomes `https://api.deepseek.com/v1/v1/chat/completions` → HTTP 404.
Without `/v1`, goose builds `https://api.deepseek.com/v1/chat/completions` → 200 OK.

**Verified 2026-07-28 in `e2e-results/2026-07-28-r1103-regression-test/`:**
- Scenario A (R110-3 fix, no /v1): exit 0, 19.4s, 13647 bytes log, LLM responded.
- Scenario B (R110-1 broken, with /v1): 404 at `/v1/v1/chat/completions` (regression reproduced).

**Why the old #3b was wrong:** It claimed "MUST end with /v1" — that was the R110-1 commit
message's incorrect claim. The actual 404 in the broken state was at `/v1/v1/...` (double),
not at `/chat/completions` (single). R110-2 PTY evidence + R110-3 fix proved this.

**This was the silent blocker for 3 days (2026-07-23 to 2026-07-28)**, then **re-introduced
for 1 commit (R110-1, c5e854d, 2026-07-28)**, then **fixed for real in R110-3 (2e5c1bb)**.

### 3c. Server endpoints (curl/requests) DO need `/v1` — only the env-var doesn't
When you manually `curl` the deepseek API, the URL DOES end with `/v1`:
```bash
curl -H "Authorization: Bearer $KEY" https://api.deepseek.com/v1/models   # /v1 here is correct
```
The asymmetry: the **server** is at `/v1/models`, but the **env-var** `OPENAI_HOST` should
NOT include `/v1` (goose adds it). Two different things, easy to confuse. R110-1 confused them.

### 15. NEVER trust a fix-commit message without re-running the e2e test (R110 lesson, 2026-07-28)
R110-1 (c5e854d) claimed "verified 4 scenarios e2e" in its commit message. The diff was
never actually executed. The fix introduced a regression (double /v1 → 404). R110-2 had
to add PTY evidence to discover this. R110-3 fixed it.

**Rule:** BEFORE trusting any "verified e2e" claim in a commit message, do BOTH:
1. `git show <hash> -- <file>` — read the actual diff, not just the message.
2. Re-run the test scenario end-to-end yourself (e2e-results/.../evidence/log file).

If only the message changed but no log file was added, the test was NOT actually run.
"Verified" without evidence is a VT-WARN red flag.

### 16. NEVER commit wrapper-scripts that overwrite env vars with `***` placeholders (R110-4c, 2026-07-28)
`scripts/e2e-full-pipeline.sh` had L6/L10:
```bash
export DEEPSEEK_API_KEY=***
export OPENAI_API_KEY=***
```
These literal-placeholder values overwrote any caller-provided env vars (e.g. from
`source .env`), turning every API request into `Authorization: Bearer ***` → 401. 9/9
LLM calls errored. The `tee | tail` + missing `pipefail` (gotcha #17) hid the failures,
so the script still printed "E2E TEST COMPLETE".

**Rule for any wrapper that calls `goose run`:** inherit env vars from caller, fail fast
at script start if they're missing, NEVER overwrite with literal placeholders.

**The fail-fast pattern (mandatory at script start):**
```bash
set -e
set -o pipefail       # <-- ALWAYS pair with set -e if you use pipes
# Validate that keys are real (not literal placeholders)
if [ -z "$DEEPSEEK_API_KEY" ] || [ "$DEEPSEEK_API_KEY" = "***" ]; then
  echo "FATAL: DEEPSEEK_API_KEY not set or is placeholder." >&2
  echo "Source .env first: source mas-engineer/.env && bash scripts/$SCRIPT.sh" >&2
  exit 1
fi
# OPENAI_API_KEY is the goose-compat shim for DEEPSEEK_API_KEY.
# Only fall back if OPENAI_API_KEY is empty/placeholder.
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "***" ]; then
  export OPENAI_API_KEY="$DEEPSEEK_API_KEY"
fi
```

**The 3-condition audit (pre-commit) for any script that wraps `goose run`:**
```bash
for script in scripts/*.sh scripts/e2e-*.sh; do
  [ -f "$script" ] || continue
  # Condition 1: hardcoded placeholder in export
  if grep -qE "^export [A-Z_]+=\*\*\*" "$script"; then
    echo "BLOCKED: $script has literal *** placeholder in export"
  fi
  # Condition 2: curl with Bearer ***
  if grep -qE "Bearer \*\*\*" "$script"; then
    echo "BLOCKED: $script has Bearer *** in curl"
  fi
done
```

### 17. `tee | tail` pipes in wrapper scripts → use `set -o pipefail` (R110-4c, 2026-07-28)
The common pattern in mas-engineer wrapper scripts:
```bash
timeout $t goose run ... 2>&1 | tee "$EVIDENCE/${name}.log" | tail -5
```
Without `set -o pipefail`, the pipeline's exit code is `tail`'s (always 0). So even
if every `goose run` returns 1 (or worse, returns 0 with 401 errors inside the log),
the script doesn't notice. The final "E2E TEST COMPLETE" prints unconditionally.

**Rule:** if you use pipes in a wrapper that has `set -e`, ALWAYS add `set -o pipefail`.
But pipefail alone isn't enough: `goose` may return 0 even when the API call inside it
401s (the error is in the log, not the exit code). So ALWAYS add the grep-on-log
counter in your final summary step too.

The full defensive pattern is in skill `mas-engineer-verification-theater-guard`,
section "THE 3RD VARIANT".

### 19. `script -qec` defaults to `sh` (POSIX), not bash — `source` fails silently (R110-24 BUG-3, 2026-07-29)
**Symptom:** `source .env` inside `script -qec "command" log` worked in some tests but not others.
The OPENAI_API_KEY length printed as 35 in one test, 0 in another.

**Root cause:** `script -qec` (the util-linux `script` command) defaults to invoking `sh`
(POSIX shell), not `bash`. In POSIX `sh`, `source` is NOT defined — only `.` (dot) is.
So `source .env` exits with an error that gets swallowed by the pipe, and the env vars
are never set in the subshell.

**Fixes (any of these works):**
```bash
# Option A: source in PARENT shell (env is inherited)
source .env
script -qec "goose run --recipe X" log   # env vars inherited, not re-sourced

# Option B: use `.` (POSIX dot) inside the command
script -qec ". ./.env && goose run --recipe X" log

# Option C: prefix with `env` (no script -qec needed)
env OPENAI_API_KEY="$KEY" OPENAI_HOST="..." script -qec "goose run" log

# Option D: explicit shell override (best for complex scripts)
script -qec "bash -c 'source .env && goose run --recipe X'" log
```

**Rule:** if you use `script -qec` for PTY mode and need bash-specific features
(`source`, arrays, `[[`, etc.), either source in the parent shell or override the
shell with `bash -c`.

### 20. NEVER overwrite `source .env` output with literal placeholders (R110-24 BUG-2, 2026-07-29)
**Symptom:** step2-script rc=0 in 1 second with `401 unauthorized` from goose.
A `tee | tail` pattern hid it from view (gotcha #17).

**Root cause (the actual bug):**
```bash
source /workspace/dev-branch/mas-engineer/.env
export OPENAI_API_KEY="***"   # ← BUG: literal placeholder overwrites the real key
export DEEPSEEK_API_KEY="***"  # ← same
```

`source .env` correctly sets the real 35-char key. But the next line `export
OPENAI_API_KEY="***"` overwrites it with the literal 3-char placeholder. Every
subsequent API call sends `Authorization: Bearer ***` → 401.

**Display-redaction trap (R110-24 also exposed this):** when you `cat` or `grep` a
file containing the real key, your terminal/agent output layer auto-redacts it
to `***` in the display. So `cat .env` shows `***` even though the file on disk
has the real 35-char key. This makes the bug invisible — you can't tell the
placeholder is wrong because the display-layer redacts the real value too.

**Diagnostic that works:**
```bash
# Use od -c to see ACTUAL bytes (not display-redacted)
sed -n '14p' /path/.env | od -c | head -3
# expect: 4-byte hex chars visible

# Check length, not value (length works even when value is redacted)
bash -c 'source .env && echo "length=${#OPENAI_API_KEY}"'
# expect: length=35 (sk- + 32 hex chars)

# Test the key directly
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $OPENAI_API_KEY" https://api.deepseek.com/v1/models
# expect: 200
```

**Rule:** if you `source .env` in a script, do NOT add any `export VAR=***` line
afterwards. `source` is enough. If you need a fallback, use the shim pattern
(gotcha #18), never a literal placeholder.

### 18. `OPENAI_API_KEY` fallback to `DEEPSEEK_API_KEY` is the standard mas-engineer pattern (R110-4c)
The mas-engineer `.env` file only contains `DEEPSEEK_API_KEY` (the user-facing key).
Goose needs `OPENAI_API_KEY` to be set (gotcha #2 — config-file OPENAI_API_KEY is
silently ignored). The standard shim:
```bash
# In .env: only DEEPSEEK_API_KEY is set
# At script start: derive OPENAI_API_KEY from DEEPSEEK_API_KEY
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "***" ]; then
  export OPENAI_API_KEY="$DEEPSEEK_API_KEY"
fi
```
This way, callers (e2e-test.sh, e2e-full-pipeline.sh, ad-hoc goose runs) only need to
`source .env` for the one key, and the shim is transparent. NEVER put a literal
`OPENAI_API_KEY=$DEEPSEEK_API_KEY` export in a script's global config — it overrides
the caller's env var on every `source` and is hard to debug.

### 4. Interactive mode needs a TRUE PTY, not a pipe
Goose's REPL needs a real PTY to show the full menu/spinner and accept keystrokes. With a plain pipe it often exits immediately or hangs. `subprocess.PIPE` for stdin is the wrong approach — use `pty.openpty()` for stdin/stdout/stderr (same slave fd for all three).

### 5. `--no-session` is broken for multi-turn
`goose run --no-session` exits after one question even if there's more to do. For multi-turn e2e, omit `--no-session` and drive it interactively instead.

### 6. PTY multi-turn needs a second submit
The process can exit after the first response unless you explicitly submit more input. The first submit may trigger an LLM response like "shall I proceed?" — a second submit (`process(action="submit", data="yes, proceed")`) is needed to actually execute the plan. Symptom: process shows "exited" with rc 0 right after the plan is presented, but no tool-calls actually happened. For non-interactive multi-turn, pipe `printf "task\nyes\n"` into goose.

### 7. Long-report generation can hang 90–100+ seconds
Not a crash — the process is still running, but `process poll` returns the same preview for a long time while `uptime_seconds` keeps climbing. Heuristic: if uptime > 60s AND no new `▸` tool-call marker appeared in the last 30s, it's probably stuck in LLM generation, not dead. Options: wait longer (some reports take 3–5 min), kill and retry on `deepseek-v4-pro`, or add an explicit line-count constraint to the recipe's prompt.

### 8. `goose-costed` PATH-discovery footgun (container-specific)
When a wrapper invokes `os.execvp("goose", ...)` from a sub-shell that lacks `/root/.local/bin` in `PATH`, it crashes with `FileNotFoundError: ... 'goose'`. This was a **latent bug since R73**: the behavior-coverage gate silently returned 0/117 for weeks because nobody went through the wrapper except the coverage tool itself (the validator calls `goose` directly, PATH was fine there). Fixed 2026-07-27 by probing `shutil.which("goose")` first, falling back to 3 known install paths.
**Pattern for any wrapper: never `os.execvp("tool", ...)` without a PATH-discovery step first.**

### 9. Backup/state files must never be committed
A parallel session can auto-generate `*.backup-pre-rN-reset`, `signal_*_done_*.yaml`, `pipeline/backup/*.yaml` as part of its own working tree. These are temporary state, not deliverables — one squash accidentally buried 4 real lines of fix under 1200+ lines of backup noise. Before `git add`/`git commit`:
```bash
git status --short
git reset HEAD -- '*.backup-pre-r*-reset' '*.state/pipeline/backup/*' \
  '*.state/pipeline/signal_*' '*.state/schedule.yaml.backup-*' \
  '*.state/changes.json.backup-*' || true
git diff --cached --stat   # verify only real changes remain staged
```
Ask "what did I NOT change myself?" before every commit if a parallel session might have been active.

### 10. Force-push only with `--force-with-lease`
When squashing auto-commits, `git push --force-with-lease origin <branch>` only pushes if nobody else pushed in the meantime. **Never use bare `--force`** — it can destroy concurrent work. If rejected: pull, rebase, re-squash.

### 11. `sub_recipes:` paths are resolved relative to the recipe's directory (2026-07-28)
When a recipe uses `sub_recipes: [{name: X, path: ./sub/X.yaml}]`, goose resolves the path relative to the recipe file's own directory, NOT the cwd. If you `goose run --recipe /abs/path/to/recipes/root.yaml`, then `./sub/X.yaml` resolves to `/abs/path/to/recipes/sub/X.yaml`. This is correct behavior, but easy to get wrong when symlinking recipes.
**Pattern:** put sub_recipes in a `./sub/` subdirectory of the parent recipe, and use `./sub/X.yaml` (NOT absolute paths).

**R110-29 gotcha (2026-07-29):** if the wrapper-recipe's own directory doesn't have the sub/ folder (e.g. you write wrappers to a fresh `e2e-results/.../wrappers/` dir without copying the sub_recipes alongside), relative paths fail. **Fix:** either use absolute paths in wrapper-recipes, or place wrappers next to their sub_recipes.

**R10 CORONASHIELD enforcement (R110-29, 2026-07-29):** mas-engineer does NOT auto-validate recipe-wrappers. After you build a wrapper with `yaml.safe_dump` and before you `goose run`, run `scripts/r11028-r10-validate.py <wrapper-dir> --strict`. It catches (1) YAML parse errors, (2) safe_dump → safe_load round-trip loss, (3) sub_recipe path resolution failures (the BUG-1 class), (4) missing required fields. Simulated BUG-1 (relative path to nonexistent sub/) is caught in <0.1s, before any `goose run` is invoked. Without this, the 6/6 FAIL in 0.6s of R110-28 iteration 1 would not have been caught. See gotcha #21 for full tool reference.

### 12. Top-level orchestrator recipes need `extensions:` to expose `delegate`/`summon` (2026-07-28)
A top-level recipe that wants to load sub-recipes via the LLM's `delegate` tool MUST list the `summon` platform extension:
```yaml
extensions:
  - type: platform
    name: summon
  - type: builtin
    name: developer
```
Without this, the LLM correctly reports "delegate tool not available" (verified in run-3 of `e2e-results/2026-07-28-real-run/`). Thin-delegator recipes (R18) that ONLY chain via `sub_recipes:` don't need this — goose handles dispatch automatically.

### 13. LLM can self-bootstrap missing deps (2026-07-28, sub_mas-unix-test-runner)
A well-prompted recipe can make the LLM detect missing tools (e.g., `pytest`) and install them autonomously:
```
> pytest is missing. Let me install it and re-run:
> ▸ shell command: pip3 install pytest pyyaml 2>&1 | tail -5
> Successfully installed iniconfig-2.3.0 ... pytest-9.1.1
```
This works in `--no-session` mode and is the cleanest E2E proof: real shell + real LLM reasoning + real test results. Use it as the canonical "is the install healthy?" smoke test.

### 14. `sub_recipes` interactive vs non-interactive dispatch (2026-07-28)
- `--no-session` mode: LLM gets the full prompt from the recipe, runs it, outputs once, exits. Works for autonomous recipes.
- Interactive (PTY) mode: LLM can ask follow-ups, await user input, multi-turn. Required for "thin-delegator" recipes (R18) that explicitly wait for the user to specify a task type.
**Rule of thumb:** if the recipe's `prompt:` ends with a question ("What would you like to delegate?"), it needs interactive mode. If it ends with a concrete task ("Run pytest on $FILE"), it works in `--no-session`.

### 21. R10 CORONASHIELD — manual validation required for wrapper-recipes (R110-29, 2026-07-29)
**Background:** R10 from `sub_mas-yaml-editor.md` says: "Validate each YAML (yaml.safe_load) before storage." But R10 is a **workflow protocol**, not an auto-enforcer. mas-engineer does NOT run any validation step at `goose run` time. R10 is enforced only when the yaml-editor agent is invoked (R18 delegation) AND the dev_editor.py workflow is used.

If you write recipe-wrappers with `yaml.safe_dump` outside the mas-engineer workflow (e.g. test scripts in `scripts/`), **R10 is never invoked** and your wrappers can have BUG-1 class errors that only surface when goose tries to load them.

**The BUG-1 class (R110-28, real):** in R110-28 iteration 1, all 6 wrapper-recipes failed in 0 seconds with rc=1 because the wrappers were written to `e2e-results/.../wrappers/` with relative `path: ./sub_mas-X.yaml` references, but the `sub/` folder lived in `/tmp/multi-arch-30/recipe/sub/`. 0/6 PASS in 0.6s walltime wasted.

**The fix:** `scripts/r11028-r10-validate.py` (R110-29) — a standalone validator you run BEFORE `goose run`:

```bash
# Default mode: parse + round-trip + path resolution + required fields
python3 scripts/r11028-r10-validate.py /path/to/wrapper-dir

# Strict mode: also requires title/description (production wrappers)
python3 scripts/r11028-r10-validate.py /path/to/wrapper-dir --strict
```

What it checks (4 categories):
1. `yaml.safe_load` parse (BEFORE)
2. `safe_dump → safe_load` round-trip (AFTER, catches serialization loss)
3. Sub-recipe path resolution (the BUG-1 class) — reports "sub_recipe path does not exist" if the path is wrong
4. Required fields (name, version, prompt ≥20 chars, sub_recipes) + optional title/description in strict mode

Integration pattern (R110-28 STEP 2 in the team-composition script):
```bash
# --- Step 2: R10 CORONASHIELD pre-flight validation ---
if ! python3 scripts/r11028-r10-validate.py "$WRAPPER_DIR" --strict; then
  echo "FATAL: R10 validation failed. Fix wrapper-recipes first." >&2
  exit 1
fi
# Now safe to goose run
```

**Rule for any recipe-pack test script:** include R10 pre-flight before `goose run`. The validator runs in <0.5s, catches the BUG-1 class, and saves a 12-minute API call waste per failed iteration.

## Working PTY pattern (full code)

```python
import subprocess, os, time, pty, select, fcntl, re

env = os.environ.copy()
env['OPENAI_API_KEY'] = env['DEEPSEEK_API_KEY']   # goose needs this even for deepseek
env['OPENAI_HOST'] = 'https://api.deepseek.com'   # NO /v1 — gotcha #3b (R110-3 fix)
env['GOOSE_TELEMETRY_ENABLED'] = 'false'
env['TERM'] = 'xterm-256color'

master_fd, slave_fd = pty.openpty()
cmd = ['goose', 'run', '--recipe', 'recipe/dev-mas-engineer.yaml', '--interactive']
p = subprocess.Popen(cmd, stdin=slave_fd, stdout=slave_fd, stderr=slave_fd,
                     env=env, close_fds=True)
os.close(slave_fd)

fl = fcntl.fcntl(master_fd, fcntl.F_GETFL)
fcntl.fcntl(master_fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

# Wait for ready signal
buf = ''
deadline = time.time() + 30
while time.time() < deadline:
    try:
        data = os.read(master_fd, 8192).decode('utf-8', errors='replace')
        if data:
            buf += data
            if 'What would you like' in buf or 'goose is ready' in buf:
                break
    except (BlockingIOError, OSError):
        time.sleep(0.2)

# Send task, then poll for a marker your recipe emits on completion
os.write(master_fd, ("Your task here" + '\n').encode())
all_buf = buf
start = time.time()
while time.time() - start < 600:
    try:
        data = os.read(master_fd, 8192).decode('utf-8', errors='replace')
        if data:
            all_buf += data
            if 'YOUR-MARKER' in all_buf:
                time.sleep(2)
                break
    except (BlockingIOError, OSError):
        if p.poll() is not None:
            break
        time.sleep(0.5)

# Cleanup
os.write(master_fd, b'\x03')  # Ctrl-C
try: p.wait(timeout=3)
except Exception:
    p.terminate(); p.wait(timeout=3)
os.close(master_fd)
```

Strip ANSI codes when reading output: `re.sub(r'\x1b\[[0-9;]*[a-zA-Z]|\r', '', text)`.

If stuck: `pkill -9 -f "goose run"`.

## Verification commands (is the key/model even valid?)
```bash
curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $KEY" https://api.deepseek.com/v1/models
# 200 = valid, 401 = invalid/revoked
curl -s -H "Authorization: Bearer $KEY" https://api.deepseek.com/v1/models   # lists usable model names
curl -X POST -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"echo OK"}]}' \
  https://api.deepseek.com/v1/chat/completions
```
Note: terminal output redacts keys on print (`sk-cca...cf22`) — verify actual byte length with `xxd`/`od -c` if it matters.

## Evidence-folder checklist (what "real e2e" means, not a synthetic test)

1. All `goose run` log files exist and are non-empty.
2. Zero `401 Unauthorized` / `Authentication failed` in any log.
3. Team/output files actually exist on disk (`find /tmp/<team> -type f` returns real content, not 0).
4. Output contains real citations/sources/content, not placeholders.
5. Pre-push secret scan returns CLEAN (see `secret-leak-defense` skill).
6. The README describing the run is written **from the actual log contents** — count real PASS marks, real files created, real errors — never write it before the runs finish, never paraphrase what you expect to have happened.
7. **R10 CORONASHIELD pre-flight passed** — see gotcha #21. Before any `goose run`, run `scripts/r11028-r10-validate.py <wrapper-dir> --strict`. Save the validator's output alongside the run logs as evidence that the wrappers were verified R10-conform.

```bash
mkdir -p e2e-results/<date>/evidence
cp h-*.log e2e-results/<date>/evidence/
# then write README from what's actually in those logs
```

## Pre-push requirement
User rule: only push commits representing a complete e2e run. A 100% e2e commit must contain the actual test/recipe output (not just a "ready" banner), pass/fail counts, an honest list of what was NOT tested, and the raw PTY log with tool-call markers. Tool-only commits or "we set up the harness but didn't run it" — do not push; revert first.

## Common pitfalls
- `set -e` in a wrapper script does NOT catch goose failures — goose returns 0 even when an internal API call 401'd. You must `grep -c 401` the log.
- `set -o pipefail` is REQUIRED if you use `tee | tail` or any other pipe. Without it, `set -e` won't fire even for fatal errors upstream.
- `write_file` auto-expands a real key if present in the source string — always template with `***REDACTED***`.
- Some demo-runner recipes are hardcoded to a specific team-name/path and don't accept parameters — check the recipe before assuming you can rename the target.
- `nohup bash -c '...' &` returns immediately — poll or `sleep + tail`, don't assume it's done.
- **R110 trap:** `OPENAI_HOST` env-var is the BASE URL (no /v1), but curl/requests use the FULL endpoint
  (with /v1). See gotcha #3c. Don't conflate them when reading code.
- **R110-4c trap:** Never `export DEEPSEEK_API_KEY=***` in a wrapper script — it overwrites the
  caller's env var. Inherit from caller, fail-fast if empty/placeholder, use the
  `OPENAI_API_KEY=$DEEPSEEK_API_KEY` shim. See gotchas #16 and #18.
- **R110-28 / R10 trap:** if you build recipe-wrappers outside the mas-engineer workflow,
  R10 (yaml validation) is never enforced. Run `scripts/r11028-r10-validate.py --strict`
  before `goose run` to catch BUG-1 class errors (sub_recipe path resolution). See gotcha #21.

## Reference
- Verified: 2026-07-22, 2026-07-23, 2026-07-27 (goose-costed PATH fix, commit 35b0e03), 2026-07-28 (10 e2e runs in `e2e-results/2026-07-28-real-run/`), 2026-07-28 (R110-2 + R110-3 PTY evidence in `e2e-results/2026-07-28-r1101-pty-verification/` and `e2e-results/2026-07-28-r1103-regression-test/`), 2026-07-29 (R110-27 30-agent live-PTY 30/30 PASS in `e2e-results/2026-07-29-r11027-30-agent-live-pty/`), 2026-07-29 (R110-28 team-composition 4/6 PASS in `e2e-results/2026-07-29-r11028-team-composition-live-pty/`), 2026-07-29 (R110-29 R10 CORONASHIELD retro-fit in `e2e-results/2026-07-29-r11028-team-composition-live-pty/RESULT.md`)
- Related skills: `pre-push-gate` (secret scan + validator run before push), `mas-engineer-verification-theater-guard` (don't overclaim what these logs show)

## MAS-ENGINEER COMMIT-STYLE (load BEFORE any commit, 2026-07-28)

VOR jedem commit in mas-engineer: lies `docs/commit-push-protocol-2026-07-27.md` UND prüfe `git log -10` für den aktuellen stil. **Niemals aus dem bauch committen.** Das repo hat 5 emoji-kategorien mit klaren rollen + einen R-sprint-counter.

**5 Emoji-Kategorien:**
- 📚 `R<n>-<m> — <titles> (N tests)` = R-sprint sprint-commit (mehrere tests, coverage-vor/nach, EVIDENCE-PATTERN block, cum-stats, forward-pointer)
- 🔧 `R<n>-<m> — <fix-title> (N files)` = R-sprint fix-commit (Bug + Fix + E2E-szenarien)
- 📊 `EVIDENCE — R<n>-<m>` = post-test evidence summary
- 📋 `docs: <topic>` = transparenz-bericht (obsolescence, inspection, protocol-updates)
- 🗑️ `chore: delete <file> (<count>/<count> verifiziert)` = obsolete-deletion

Conventional alternativen wenn KEIN R-sprint: `fix(scope):`, `docs(scope):`, `e2e(scope):`, `merge:`.

**Letzte R-number vor commit prüfen:** `git log --oneline | grep -oE "R[0-9]+" | sort -u | tail -5`. R-numbering ist strict sequenziell (R108-1..R108-13, R109-1, R110-1...). Bei R109 → mein fix ist R110-1.

**Commit-body MUSS enthalten (5 sections):**
1. **Bug** — was war kaputt, mit reproducer (command + output)
2. **Fix** — was wurde geändert, file-list mit line-counts
3. **E2E** — verifizierte szenarien mit PASS/FAIL counts
4. **Pre-push-gate** — Step 0 (secrets) + Step 1 (hook) + Step 2 (pytest) + Step 3 (msg) + Step 4 (push) + Step 5 (post-flight) als checklist
5. **Files (N)** — modified/added/removed breakdown

**Branch:** `Dev` ist main, `new-agent` ist typische working-branch (auch mein workspace). Push zur working-branch, nicht direkt zu Dev (außer explizit angewiesen).

**Hooks sind nicht per default aktiv:** `git config core.hooksPath mas-engineer/.githooks` SETZEN. Hooks in `mas-engineer/.githooks/{pre-commit,pre-push}` greifen sonst nicht.

**Push-pattern (per protokoll section 3, defensiv):**
```bash
export GH_PAT=$(grep '^GH_PAT=' mas-engineer/.env | cut -d'=' -f2)
git remote set-url origin https://${GH_PAT}@github.com/mczardybon/mas-engineer.git
git push origin <branch>
git remote set-url origin https://github.com/mczardybon/mas-engineer.git   # ← CRITICAL: reset!
```

**Post-flight VERIFIZIEREN (VT-WARN gilt auch hier):**
```bash
git show <hash> --stat                              # was wurde TATSÄCHLICH committed
git show <hash> | grep -E "sk-[a-f0-9]{32,}|ghp_[A-Za-z0-9]{30,}"   # 0 secrets
git log origin/<branch>..HEAD --oneline             # was wurde TATSÄCHLICH gepusht
```

**Author-Identity:** `Hermes-MAS-Engineer <Hermes@mas-engineer.local>` (per `git config user.email/name`). Andere Hermes-instanz benutzt `Hermes Agent <ramses@hermes.ai>` — verwechseln ist ein verifikations-fehler.

## Quick e2e smoke test (canonical "is goose working?" check)
```bash
# 1. Verify key + model
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $DEEPSEEK_API_KEY" https://api.deepseek.com/v1/models
# expect: 200

# 2. Verify goose sees the config
goose info --check
# expect: Auth: OK

# 3. Run a 30-second autonomous recipe (real LLM + real shell + real test)
mkdir -p e2e-results/$(date +%F)/evidence
goose run --recipe /path/to/mas-engineer/recipe/sub/sub_mas-unix-test-runner.yaml --no-session \
  2>&1 | tee e2e-results/$(date +%F)/evidence/smoke-test.log
# expect: "18 passed in 0.89s" + "✅ UNIX-TEST-RUNNER (v2.0.0) — ALL CHECKS PASSED"
```
If step 1 fails: key is invalid/rotated. If step 2 fails: check `~/.config/goose/config.yaml` has
`OPENAI_HOST: https://api.deepseek.com` (NO /v1 — see gotcha #3b). If step 3 fails: re-read gotchas 1–3c above.
