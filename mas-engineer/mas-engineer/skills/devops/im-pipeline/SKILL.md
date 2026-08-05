---
name: im-pipeline
description: How to run mas-engineer's self-improvement IM-Pipeline (FIND→RANK→DESIGN→VALIDATE→APPLY) end-to-end with REAL file edits via the developer extension — plus the rule that Hermes never edits mas-engineer files directly, and the pattern for wiring an orphaned sub-expert into the pipeline via mandatory summon. Supersedes im-pipeline-v2-with-developer, im-pipeline-goose-expert-integration, and mas-engineer-e2e-im-test (merged 2026-07-28).
category: devops
---

# MAS-Engineer IM-Pipeline — running it, wiring experts into it, and who's allowed to edit what

## The non-negotiable rule (2026-07-21, user pushed back hard)

> "du testest den mas-engineer in der goose cli wie ein Mensch es tun wird.. du gibst dem mas Anweisungen so daß er sich mittels improvement verbessert! alles immer in einem echtem e2e lauf"

**Hermes NEVER writes mas-engineer files (recipes / instructions / agent code / manifests) directly.** Hermes gives the mas-engineer natural-language improvement tasks and runs them through the real improvement workflow — mas-engineer must fix itself.

Scope is always the **complete** functionality, not just the piece being changed: "du sollst immer die komplette Funktionalität des mas-engineer in der goose cli testen." Adding one new sub-agent still means exercising the pre-push-validator, the improvement pipeline, IM dispatch, etc. — not just the new recipe in isolation.

The ONE exception: the user explicitly says "schreib das selbst" (write it yourself). Confirm first ("du meinst wirklich direkt? dann ja, mache ich.") before editing files by hand.

If mas-engineer isn't running in the session, say so — don't silently write code instead. Offer: start it, or (with explicit confirmation) write it yourself.

## Critical setup — the key enabler for real file edits

`sub_mas-*` recipes by default only have the `summon` extension (delegate + load — read-only). To get real file writes, add `--with-builtin developer`:

```bash
goose run --with-builtin developer --recipe /root/.config/goose/recipes/sub/sub_mas-im-finder.yaml --no-session
```

The `developer` extension provides `shell`, `read_file`, `write_file`, `edit`, `tree`. Without it, the pipeline only produces proposals, never real edits.

## The 5-phase pipeline (run each phase separately, not chained in one recipe)

```bash
export DEEPSEEK_API_KEY="sk-..."
export OPENAI_API_KEY="$DEEPSEEK_API_KEY"
export OPENAI_HOST="https://api.deepseek.com"
cd <mas-engineer-workspace>
export GOOSE_SESSION_TAG="[im-pipeline]"

# Phase 1: FIND — analyze project, write findings.yaml (~4 min)
echo "ack" | goose run --with-builtin developer --recipe recipe/sub/sub_mas-im-finder.yaml --no-session

# Phase 2: RANK — prioritize findings (~1.5 min)
echo "ack" | goose run --with-builtin developer --recipe recipe/sub/sub_mas-im-rank.yaml --no-session

# Phase 3: DESIGN — create patches (~1.5 min)
echo "ack" | goose run --with-builtin developer --recipe recipe/sub/sub_mas-im-designer.yaml --no-session

# Phase 4: VALIDATE — check Goose-compliance (~2 min)
echo "ack" | goose run --with-builtin developer --recipe recipe/sub/sub_mas-im-validator.yaml --no-session

# Phase 5: GENERAL-IMPROVER — interactive (R01 confirmation), must be told explicitly to apply
echo "FULL_IMPROVEMENT - apply all CONFORM patches. ack" | goose run --with-builtin developer \
  --recipe recipe/sub/sub_mas-general-improver.yaml --no-session
```
Total runtime ≈ 10 minutes for a handful of patches.

Output artifacts, all in `.state/pipeline/`: `findings.yaml`, `ranked_findings.yaml`, `patches.yaml` (file/field/from/to/reason), `validation.yaml` (CONFORM/VIOLATION verdicts).

### Pitfall — cwd muss mas-engineer/ sein, sonst `recipe/sub/...` nicht gefunden

R36-R101 Pattern. Die Pipeline-Recipe-Pfade (`recipe/sub/sub_mas-im-*.yaml`)
sind RELATIV. Wenn du `cd mas-engineer/` vergisst, schlägt goose fehl mit
"recipe not found". Vor jedem Phase-Block:

```bash
pwd   # MUSS mit /mas-engineer enden
```

`RECURSION_OVERRIDE=2` und `MAS_TASK` / `MAS_CONFIRM=yes` / `MAS_APPROVE=y`
sind die ENV-Toggles die R01-Confirmation und R10-Approval der sub-agents
überschreiben. Ohne diese toggles wartet der general-improver auf
menschliche Bestätigung und läuft nicht durch.

`MAS_WEB_RESEARCH=no` ist Default — explizit setzen wenn du den Finder
zwingen willst offline zu arbeiten (spart ~30s pro Run).

### IM_TOP_N env var — R110-106 lesson (2026-08-04)

**Default ist 5** (R57: `IM_TOP_N_DEFAULT=5`). Für spec-drift detection
oder wenn viele NN1-ähnliche findings erwartet werden:

```bash
export IM_TOP_N=30              # 6× default; covers R110-105 SD-findings
export IM_TOP_N_MULTIPLIER=3    # finder scans 3× top_N
```

**⚠ KNOWN BUG (R110-106-FOLLOW-UP, noch NICHT gefixt in 3b80259):**
`recipe/instructions/sub_mas-im-designer.md` Z.163 hat hardcoded
"STEP 1 — DRAFT ONE PATCH FOR EACH TOP-5 FINDING" — der designer
ignoriert IM_TOP_N und drafted nur für die ersten 5. Fix-spec ist
in `.directives/R110-106-designer-im-top-n-respect.md` (130 lines,
im R110-106 commit mitgepusht). Workaround bis der fix applied ist:
findings die jenseits top-5 sind werden als "beyond IM_TOP_N=5 scope"
markiert und müssen manuell in den nächsten run gehoben werden, oder
via R110-106-FOLLOW-UP directive neu draften lassen. Beleg: R110-105
e2e-pilot fand 16 implementable findings, designer drafted 1 (F-022),
15 wurden als "beyond scope" geskippt.

**Wenn `apply_only` schon einen fix angewendet hat und ein neuer
run startet:** der improver erkennt das via backup-file
(`.state/backups/<file>.bak.YYYYMMDD`) und markiert den patch als
"already applied" — idempotent, kein doppel-patch. Beleg: R110-106
run 2 hat F-001 nicht doppelt gepatcht obwohl der fix im working tree
war.

## The actual e2e test (3 steps, always via the real entry point)

1. Give mas-engineer the task in natural language (be specific about scope, e.g. what to scan, what to wire in, where to document it).
2. Run the improvement recipe yourself — do NOT edit files:
   ```bash
   timeout 600 goose run --recipe recipe/im-pipeline-dev-v2.yaml --no-session
   # or for simpler tasks:
   timeout 600 goose run --recipe recipe/sub/sub_mas-general-improver.yaml --no-session
   ```
3. Verify e2e: did mas-engineer actually commit (`git log --oneline -3`)? Were files actually created/updated (`git show --stat HEAD`)? Does the relevant e2e test/replay script pass?

**"Real e2e" means**: same entry point a human uses (`goose run --recipe ...` from CLI), same model/env/timeout, mas-engineer does the file writes in its own working dir (not Hermes), and the outcome is committed changes in git — not "I wrote 5 files in this chat".

Pre-test a candidate claim against the verification-theater self-audit before trusting it:
```bash
python3 tools/dev_self_auditor.py --scope <PATH> --output /tmp/x.yaml
echo $?  # 0=PASS, 1=BLOCK
```

## Wiring an orphaned sub-expert into the pipeline (mandatory-summon pattern)

Use when you discover a sub-agent that's defined but never invoked (an orphan) — e.g. a `goose-expert` or `framework-expert` that should be consulted but isn't wired into any upstream trigger.

1. **Add `extensions: [summon]`** to every agent that needs to delegate to it, and raise limits (summon needs more time/steps than the 60s/25-step default):
   ```yaml
   extensions:
     - summon
   settings:
     timeout: 180
     max_steps: 40
   ```
2. **Add a STEP 0.5 mandatory-consultation block** to each upstream agent, keyed by finding/patch type-prefix:
   ```yaml
   ## ⛔ STEP 0.5 — GOOSE-EXPERT CONSULTATION (MANDATORY)
   For EACH finding/patch whose `type` starts with these prefixes, SUMMON first:
   | Prefix   | Scope          | Why mandatory                          |
   |----------|----------------|------------------------------------------|
   | A1-A5    | subagents      | Timeout/steps limits are version-specific |
   | MM1-MM9  | YAML structure | Required fields vary by Goose version   |
   ```
3. **Define the verdict schema** the expert returns:
   ```yaml
   finding.goose_verdict:
     verdict: CONFORM | RESTRICTED | NOT_POSSIBLE
     confidence: HIGH | MEDIUM | LOW
     explanation: "<one-line>"
     alternatives: ["<list>"]   # only at NOT_POSSIBLE
   ```
4. **Add an R-numbered rule** to the master constitution making the consultation mandatory, with a citation:
   ```yaml
   ⛔⛔⛔⛔⛔ GOOSE-EXPERT CONSULTATION (R11) For any task touching Goose
   architecture (types A*/B*/D*/MM*/JJ*/S*/HH*/LL*): MANDATORY summon of
   sub_mas-goose-expert BEFORE drafting/validating. Skipping = finding
   REJECTED downstream.
   ```
5. **Reference the R-rule at the bottom of each upstream agent's restrictions** so the trigger and the enforcement are both discoverable.

**Why this works**: `summon` is Goose's native MCP for on-demand sub-agent loading. Orphan agents stay orphaned because no upstream has the trigger to invoke them; making the consultation mandatory in the trigger table forces real use, and downstream stages (im-validator) can reject anything that skipped the summon step.

**Common wrong solution to avoid**: a static numerical limits check (e.g. "timeout must be 60–3600") catches bad numbers but misses architectural issues like "this pattern is deprecated in Goose vN" — that needs real consultation, not a static rules list.

**Verification after wiring an expert in**: `sub_mas-pre-push-validator` still passes; every upstream agent lists `summon` in `extensions:`; the constitution has the new R-rule; push normally.

## YAML gotcha: I_AM prefix with pipes

Never write an unquoted colon inside a flow-style prompt line — it collides with YAML mapping syntax:
```yaml
# BREAKS:
prompt: I am dev-mas-engineer (v1.0.0) | MODE-CHECK: mas-engineer | 🦆 ...
```
Always use a literal block scalar instead:
```yaml
prompt: |
  I am dev-mas-engineer (v1.0.0) | MODE-CHECK: mas-engineer | 🦆 ...
```

## Verification after any patch apply

```python
import yaml
for f in modified_files:
    data = yaml.safe_load(open(f))          # must not raise
    assert 'I am' in str(data.get('prompt', ''))

import subprocess
for f in modified_files:
    r = subprocess.run(['goose', 'run', '--recipe', f, '--no-session', '--explain'],
                        capture_output=True, text=True)
    assert r.returncode == 0 and 'Loading recipe' in r.stdout
```

## Pitfalls
1. Without `--with-builtin developer`, sub-agents can only delegate, not write — pipeline produces proposals only.
2. General-improver is interactive (R01) — it will not auto-apply without an explicit task or manual confirmation.
3. `I_AM | MODE-CHECK` breaks YAML unless wrapped in `prompt: |`.
4. Some demo/test projects are not git repos — don't try to push them.
5. The 60s goose internal timeout is per-call, not total — each phase can legitimately take 2–4 minutes.
6. Recipe-dir discovery depends on `GOOSE_SESSION_TAG` / `.mas-mode` marker files in the workspace.
7. Hermes writing the file directly bypasses mas-engineer and is NOT a real e2e test — always check `git show --stat HEAD` shows the change came from a goose session, not a hand-edit. Even a tiny requested change still goes through the im-pipeline; a user asking for something small is not license to "just fix it by hand."
8. If mas-engineer doesn't fully complete a task, don't finish it by hand — re-run with a clearer prompt or escalate to the user.
9. **`watch_patterns` for background process monitoring is greedy** (R110-67 hit 2026-08-03). Bare `404` matches BOTH HTTP-404 errors AND Python line-number references like `tools/dev_generic_init.py:404:`. A pattern match during a successful 4.9k-line LLM run fired on a code citation, not an actual HTTP failure. Tighten patterns to either HTTP-context (`^404\s|HTTP.*404|Status.*404`) or use `head -5` of the log for the actual exit-code instead of pattern-matching. Verify by grepping the log for the pattern in context (`grep -nC2 "404" log.log`) before trusting the alarm.
10. **Pre-push-validator Check 17 (pytest-run) braucht ~10s für ~1300 tests** (R110-78, gemessen 2026-08-04: 1281 tests in 7.63s). Bei wachsendem test-corpus (R110-94 hatte +37 → R110-78 hätte jetzt ~1300) ist 10-15s realistisch. Wenn der validator länger als 60s hängt: ist Check 17 — entweder timeout hochsetzen oder `--testmon` für nur-geänderte tests benutzen. Beleg: R110-106 pre-push-validator hängte bei 140s+ in Check 17, ist erst nach 200s durchgelaufen.
11. **Deepseek stream-output kann mid-pipeline abbrechen** (R110-106 hit). Symptom: log endet mitten in einem JSON-block (`{` ohne close), process exit aber output unvollständig. Ursache: deepseek antwortet mit `length`-finish-reason statt `stop`. Workaround: phase-Output in `.state/pipeline/<phase>.yaml` checken (wird geschrieben BEVOR stream zurückkommt), und nur den `tail` des logs für completion-status verwenden. Bei stream-abort: phase re-run (idempotent, überschreibt output).

## Running in FRAMEWORK mode (USER-directed, R110-24 pattern, 2026-07-29)

When the user says "run framework-improver on user-agents" or "use mode=framework":

1. **Set `.mas-mode` to `framework`** in the workspace root BEFORE running:
   ```bash
   echo "framework" > /workspace/dev-branch/mas-engineer/.mas-mode
   ```
   This tells the im-finder to scan BOTH `recipe/sub/*` (framework internals) AND
   `recipe/multi-arch-30/*` (user/team recipes). Without it, the default `mas` mode
   only scans the team-recipes.

2. **Expect im-rank to prioritize `recipe/sub/*` over team-recipes.** This is
   correct behavior, not a bug: framework directors (dev-director, test-director,
   git-operator) have 7-9 roles each (high NN1 score), while team sub-agents are
   intentionally single-role. The top-5 ranked findings will be framework agents.

3. **Coronashield R10 will block most patches as designed.** When 0 patches are
   applied, that's the safe outcome — the validator catches orphaned cross-refs,
   missing before/after YAML, and micro-splits. Look for `patches_blocked: N`
   in the schedule history to confirm the blocker is working, not a regression.

4. **Verify with the team-recipe e2e AFTER the run.** A 0-patch framework run
   is still a success if the existing teams still pass 100%:
   ```bash
   bash scripts/run-30agent-test.sh   # 44/44 expected
   ```

5. **User-scope-filter is a future improvement.** If USER wants improver to focus
   on team-recipes specifically, the im-finder would need a `--scope=team-recipes`
   flag (not yet implemented). Until then, USER must accept that framework-recipes
   are higher-priority targets.

## Reference
- Verified 2026-07-18: 5/5 phases EXIT=0, 5/5 patches CONFORM, 3 files patched, 6/6 YAML valid, 3/3 recipes load.
- Verified 2026-07-29 (R110-24): PTY framework-improver (605s) + PTY 30-agent test (131s) — 44/44 PASS, 0 applied, coronashield R10 blocked as designed. Branch r11024-pty-full-test (commit 2d338097).
- Verified 2026-08-04 (R110-106): IM_TOP_N=30 e2e — finder→rank→designer drafted 1 patch (F-022), validator APPROVED, improver applied. 2 spec-drifts fixed (F-001 path, F-022 test-literal 14→17). Commit 3b80259 pushed to origin/cleanup. pytest 1281/1281 PASS in 7.6s. IM-designer TOP-5 hardcode bug NOT fixed in this run (R110-106-FOLLOW-UP directive documents fix-spec).
- User corrections: 2026-07-21 (Hermes never edits mas-engineer files), 2026-07-23 (same, reinforced)
- Related skills: `pre-push-gate` (validator + e2e before any push), `goose-cli-e2e-testing` (how to actually drive the CLI), `mas-engineer-verification-theater-guard` (don't overclaim pipeline results)
