---
name: pre-push-gate
description: The complete pre-push gate for mas-engineer — secret scan, goose pre-push-validator run, the mandatory 100% e2e (happy-path + edge-case) rule, and the post-flight sub_recipe_ref audit that catches what the validator misses. Supersedes mandatory-e2e-before-push, pre-push-goose-validation, and mas-push-post-flight-audit (merged 2026-07-28, previously 3 overlapping skills covering different angles of the same "never push unvalidated code" rule).
category: devops
---

## When to use

Load this skill when: The complete pre-push gate for mas-engineer — secret scan, goose pre-push-validator run, the mandatory 100% e2e (happy-path + edge-case) rule, and the post-flight sub_recipe_ref audit that catches what the validator misses. Supersedes mandatory-e2e-before-push, pre-push-goose-validation, and mas-push-post-flight-audit (merged 2026-07-28, previously 3 overlapping skills covering different angles of the same "never push unvalidated code" rule).

For mas-engineer framework development, this skill provides domain-specific guidance that supersedes generic workflows.



# Pre-Push Gate — secret scan → validator → e2e → post-flight audit

## The rules this enforces (both are hard user rules, not suggestions)

1. **(2026-07-19, German)**: "kein pust ohne vorherigen komplette e2e Test alles enthaltenen Funktionen.. 100% e2e" — never push without a complete e2e test of every function in the change batch.
2. **(mczardybon)**: "lass vor jedem Push goose mit dem Mas engineer laufen.. nur funktionierendes darf gepusht werden" — always run the goose pre-push-validator before every push; only working code gets pushed.

Both apply together. The validator run is one part of the full e2e gate.

## When this applies
New agents, workflows, sub-agents; changes to runtime behavior (recipes, tools, scripts); new docs that change how the system is used; anything the user will run or interact with.

Does NOT strictly require the full procedure: pure typo fixes with no behavior change, comment-only changes, README index updates that only add links to existing files. When in doubt, treat it as runtime-affecting.

## Step 0 — Secret scan (CRITICAL, run first, every time)

```bash
cd <repo>
# 1. Tracked files (working tree)
SECRETS=$(git ls-files | xargs grep -lE "sk-[a-f0-9]{30,}|DEEPSEEK_API_KEY=[a-z0-9]|ghp_[A-Za-z0-9]{30,}|[0-9]{8,10}:AA[A-Za-z0-9_-]{30,}|api[_-]?key.*['\"][a-zA-Z0-9]{20,}" 2>/dev/null)
# 2. Full git history (catches deleted-but-still-in-history leaks)
HIST_SECRETS=$(git rev-list --all 2>/dev/null | while read c; do git ls-tree -r "$c" 2>/dev/null; done | grep -E "sk-[a-f0-9]{30,}|ghp_[A-Za-z0-9]{30,}" 2>/dev/null | head -3)
if [ -n "$SECRETS" ] || [ -n "$HIST_SECRETS" ]; then
  echo "BLOCKED: secrets found"; exit 1
fi
echo "OK: no secrets in tracked files or git history"
```
- Real keys live ONLY in the process environment, never inlined in skills/code/docs/commits.
- Gotcha: skill files themselves sometimes accumulate stale keys — that's why this check exists; keep this file key-free too.
- Gotcha: `git ls-files` only checks currently-tracked files — a key added then deleted is still in history, hence the second check.
- For full defense-in-depth (pre-commit/pre-push hooks, redacted-display ≠ file-redaction, incident response), see the `secret-leak-defense` skill.

## Step 1 — Run the goose pre-push-validator (real LLM, real CLI)

```bash
export PATH="/root/.local/bin:$PATH"
# DEEPSEEK_API_KEY must already be in env
cd <repo>
timeout 120 goose run --recipe recipe/sub/sub_mas-pre-push-validator.yaml --no-session
```
- rc=0 with all checks passed = OK. Takes ~40–90s (real LLM reasoning) — a 90s wait or exit 124 is normal for the full check set, not a failure.
- Writes `.mase/pipeline/pre_push_validation.yaml`. If `status: blocked`, fix `blocked_reasons` first, then re-run.

**The validator's checks include**: P1 (high-severity) findings = 0; no hardcoded `/home/<user>/` paths; all YAML valid; all Python compiles; all shell scripts syntactically valid; no German characters in English-only code/docs; git-status warning (uncommitted, non-blocking).

Common fixes when blocked: run the im-finder for P1 findings; replace hardcoded paths with `${HOME}/...`; add a `prompt:` (≥30 chars) + `instructions:` to a recipe missing them; translate stray German text.

## Step 2 — Full e2e test of every function in the batch (the "100% e2e" rule)

For every function or feature in the change: run it once with realistic input via the real entry point a human would use.

Required test types for a typical batch (agents + workflows + docs):
- **Agent smoke test**: invoke each new agent via goose, expect a DONE signal.
- **Workflow integration test**: trigger each new workflow, expect success.
- **Install/uninstall dry-run**: if the change adds an install script, run it in a temp dir, verify files land, then uninstall.
- **Doc link check**: grep all `](path)` references in new docs, verify each path exists.
- **YAML parse**: `python3 -c "import yaml; yaml.safe_load(open(f))"` for every new/modified `.yaml`.
- **Secret scan**: (Step 0, repeated here as part of the checklist) must return 0 hits.
- **Mixed-language scan**: grep English-only docs for German words (accept false positives like "will", "am", "was", "an" — also valid English).

All must be true before push: every new agent invoked and returned expected output; every new workflow ran end-to-end without abort; install/uninstall succeeded in a temp dir; every doc link resolves; every YAML parses; zero secrets; zero real German words; **every pytest test in the changed packages passes** (see Pytest spec-drift rule below).

**Pytest spec-drift rule (R110-78, 2026-08-03)**: when a commit changes a count, version number, or any hard-coded number/string that other tests assert (e.g. R110-71 changed `sub_mas-bootstrap.yaml` from "96 sub-agents" to "110 sub-agents" but did not update `test_sub_mas_bootstrap.py::test_bootstrap_distributes_96_subagents` — the test failed permanently until R110-78 fixed it 1 commit later). The fix has two parts:

1. **The fix-it-now part**: before declaring a count/version/etc. fix complete, run `python3 -m pytest tests/ -q --collect-only | grep -E "<test_name>|<number>"` and grep the staged diff for the new value; any test that asserts the OLD value needs a 1-line update in the SAME commit (or in an immediate follow-up like R110-78).

2. **The prevent-it-later part**: `python3 -m pytest -q mas-engineer/tests/` (or whichever test dir covers the changed code) is part of the Step 2 checklist, alongside the agent smoke / workflow integration / install dry-run. If the test dir does not exist for the package you changed, that itself is a finding to surface to the user (some packages have no test coverage yet — note it explicitly, do not silently skip).

The `pytest -q` step takes ~10s for the mas-engineer test suite (1295 tests as of 2026-08-03) and catches spec-drift BEFORE push. It is cheaper than the goose pre-push-validator (~90s) and runs first, so a spec-drift failure does not waste a validator run.

**If E2E is genuinely not possible** (no API key, environment broken, time pressure): do not silently push. Stop, tell the user why, list what wasn't tested, and ask whether to push anyway (their call) or wait.

### Beyond happy-path: edge-case (EC) tests
The "100% e2e" rule covers the happy path — real bugs hide in edge cases happy-path tests never trigger: empty inputs, boundary values, corrupted/malformed inputs, permission failures (read-only mounts), time-based logic (future timestamps, DST), resource exhaustion.

**Lesson from R101 (2026-07-27)**: `sqlite3.OperationalError` does not catch all sqlite storage errors — a corrupted DB raised an unhandled `sqlite3.DatabaseError`. A 30-minute EC-test pass caught it; the happy-path suite never would have.

Pattern: happy-path e2e first (above), then 5–10 EC tests as a small Python harness with synthetic inputs (synthetic corrupted DBs, `chmod 444` read-only files, random-bytes corruption, future timestamps), one assert per error class. Fix and re-run all EC + happy-path on any failure. Skippable only for changes that definitely don't touch storage/input-handling code (pure doc/typo fixes); any `tools/` or `storage/`-touching change requires EC tests.

## Step 3 — Document the e2e result in the commit

```
E2E result: PASS
- Agent smoke: <N>/<N> PASS (list)
- Workflow integration: <N>/<N> PASS (list)
- Install dry-run: PASS
- Doc links: <N>/<N> resolve
- YAML parse: <N>/<N> PASS
- Secrets: 0
- German words: 0 (or N false-positives noted)
```

## Step 4 — Push

```bash
git add <files>
git commit -m "..."
export GH_PAT="$(hermes memory get GH_PAT 2>/dev/null)"   # never hardcode
git remote set-url origin "https://${GH_PAT}@github.com/<user>/<repo>.git"
git push origin master
git remote set-url origin https://github.com/<user>/<repo>.git
unset GH_PAT
```

### Pitfall — 403 "denied to <user>" (R108-9, R108-11)

If `git push` returns a 403 with text like "denied to mczardybon", the
remote URL has the wrong user embedded (or is pointing at the wrong
account). Check before assuming a credentials problem:

```bash
git config remote.origin.url
```

If the user is not `<your-actual-github-user>/<repo>`, the push will be
rejected even with a valid PAT. Re-set the remote before retrying:

```bash
git remote set-url origin https://${GH_PAT}@github.com/<your-actual-user>/<repo>.git
```

**Variant of the same bug:** the `.env` file may have a key named
`GH_PAT_CLASSIC` while the pre-push-gate uses `GH_PAT`. These are TWO
different vars. Loading the wrong one will silently pass `ghp_XS...rq2N`
(literal placeholder text) as the PAT, which fails push with 403.
**Always use the var name the skill expects: `GH_PAT`** (not `GH_PAT_CLASSIC`,
not `GH_TOKEN`, not `GITHUB_TOKEN` unless the skill is updated).

If `git ls-files | grep -lE "sk-[a-f0-9]{30,}|ghp_[A-Za-z0-9]{30,}"` returns
any matches, scrub BEFORE `git add` — GitHub blocks pushes with secrets
under rule GH013.

## Step 5 — Post-flight audit (Hermes-side, catches what the validator misses)

**Why this exists**: R45 shipped 4 directors referencing 5 non-existent sub_recipes. The pre-push-validator passed (11/11) and e2e was 100% (128/128) — but coverage silently dropped from 50/96 to 50/101 (49.5%). The user noticed before any internal test did. Root cause: the validator has no sub_recipe_ref_resolution check, the im-designer stage treats "requires separate creation" as informational not blocking, and NN1 director-patches aren't atomic. This is the operator-side mitigation until the mas-side pipeline fixes it structurally.

Run after every successful push, before reporting back to the user:

```bash
python3 << 'EOF'
import yaml, glob, os, json
broken, total_refs, total_sub = [], 0, 0
for f in glob.glob('recipe/sub/*.yaml'):
    if 'ORIGINAL' in f: continue
    total_sub += 1
    try:
        d = yaml.safe_load(open(f))
    except Exception:
        continue
    if not d: continue
    for s in d.get('sub_recipes', []):
        total_refs += 1
        path = s.get('path', '').lstrip('./')
        full = os.path.join(os.path.dirname(f), path)
        if not os.path.exists(full):
            broken.append({'director': os.path.basename(f), 'ref': s.get('name'), 'path': path})
result = {'sub_agents': total_sub, 'sub_recipe_refs': total_refs, 'broken_refs': broken,
          'coverage_pct': round(100 * (1 - len(broken)/max(total_refs,1)), 2)}
print(json.dumps(result, indent=2))
if broken:
    print(f'\nBROKEN {len(broken)} SUB_RECIPE REFS - REGRESSION'); exit(1)
print(f'\nOK all {total_refs} sub_recipe refs resolve. Coverage {result["coverage_pct"]}%')
EOF
```

If broken refs are found: write them to a findings file for the next FIX_SPECIFIC round, and archive evidence:
```bash
mkdir -p e2e-evidence-gen2
cp /tmp/post_flight_audit.json e2e-evidence-gen2/post-flight-audit-RROUND.json
git add e2e-evidence-gen2/post-flight-audit-RROUND.json
git commit -m "docs(evidence): post-flight audit - N refs, M broken"
```

Acceptance: runs in <10s, fails loudly on any broken ref, archives evidence every time.

**Known pitfalls**: `dev_changes.py` has a known `'/' not supported between str and int` bug — don't rely on it from the operator side. `findings_*_structural.yaml`-style design-stage concepts can't be applied by FIX_SPECIFIC and get ignored by FULL_IMPROVEMENT too — this is the mas-side blind spot this audit exists to catch from outside. Large draft-findings files (500KB+) must never be committed — gitignore them.

## Cross-cutting rule: never delete failed-test evidence (2026-07-19)

Failed tests — even self-authored ones — are part of the project's transparency trail. Do not delete them in cleanup commits. If a folder is obsolete because a v2 succeeded, **rename** it with an `-ARCHIVED-<reason>` suffix and add a README documenting the failure mode; have the v2 folder cross-reference the archive. Deleting failed evidence makes the success look like the only attempt, which is misleading — honest projects keep the failure visible.

## Pitfalls for shell-script-based e2e wrappers (R110-24, 2026-07-29)

**1. `script -qec` defaults to POSIX `sh` (no `source` builtin).**
If you use `script -qec "source .env && goose run" log`, the
`source` fails silently in POSIX sh. Result: env vars are never
set in the inner shell, goose gets empty `OPENAI_API_KEY`, returns
401. Fix: `script -qec ". ./.env && goose run" log` (POSIX dot
form), or `script -qec "bash -c 'source .env && goose run'" log`,
or `source .env` in the parent shell before `script -qec`.

**2. Wrapper scripts that overwrite `source .env` output with literal `***`.**
Pattern: `source .env; export KEY="***"` — the `***` is a literal
3-char string that overwrites the real 35-char key. Fix: use the
shim pattern (`if [ -z "$KEY" ]; then export KEY="$OTHER"; fi`),
never a literal placeholder. See `secret-leak-defense` §"Common
leak vectors" #1 and #5.

**3. `tee | tail` without `set -o pipefail` masks 401s.**
If your wrapper does `goose run 2>&1 | tee log | tail -5`, the
pipeline's exit code is `tail`'s (always 0). Goose can return 0
even when the API call inside it 401'd. Add `set -o pipefail` and
grep the log for "401|Authentication failed" before printing
"TEST COMPLETE". See `mas-engineer-verification-theater-guard`
"THE 3RD VARIANT" for full pattern.

**4. Display-redaction in agent output looks like stub but isn't.**
If `cat .env` shows `KEY=***`, that's display-layer redaction, not
a real stub. Use `od -c` or `bash -c 'source .env && echo
"length=${#KEY}"'` to verify what's actually loaded. Length=35
(typical sk-/ghp_ format) = real key, not stub.

## Pitfall — validator internal 200s cap (R110-69, 2026-08-03)

The goose pre-push-validator has an internal `timeout_secs: 200`
that can fire BEFORE the outer shell `timeout 300` expires, especially
during Check 14 (multi-dim sub-agent coverage) which spawns subprocess
calls. Symptom: `rc=124` from outer timeout, but log shows
"All 15 checks executed" and "All checks complete" — the validator
finished the work, just couldn't write the final `pre_push_validation.yaml`.

**Fix when this happens**: re-run with longer outer timeout
(`timeout 420 goose run --recipe ...`) so the 3 final writes
(baseline + coverage + pre_push_validation.yaml) complete. Two
retry-attempts at 240s timeout burned 8 minutes; 420s is the
working number for R110-69 (rc=0, full validation written).

NEVER manually write `pre_push_validation.yaml` — that's
verification-theater. Re-run the validator with more time
instead.

## Pitfall — e2e-results/ is gitignored (R110-69, 2026-08-03)

`e2e-results/` is in `mas-engineer/.gitignore` to keep large
e2e logs out of the repo. The pre-push-validator writes the
current-run evidence to `e2e-results/<date>-run-N/raw-results.json`
(working-tree only) and stores the path in
`.mase/pre-push-e2e-baseline.json` as `baseline_source`. This is
by design — a fresh clone has no `e2e-results/` and the baseline
field is informational, not load-bearing. The validator's "fallback"
branch handles missing evidence. Do NOT "fix" the baseline_source
to a non-gitignored path; the contract is intentional.

## Reference
- User corrections: 2026-07-19 (both rules), 2026-07-23 (mas must fix mas, not Hermes), 2026-07-29 (R110-24 shell-script pitfalls), 2026-08-03 (R110-69 validator 200s cap + e2e-results/ gitignore contract)
- Related skills: `secret-leak-defense` (deeper secret-hygiene), `mas-engineer-verification-theater-guard` (don't let the e2e report overclaim), `goose-cli-e2e-testing` (how to actually run the tests this gate requires)
