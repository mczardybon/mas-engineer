# MAS-Engineer Demo — Multi-Architecture 30-Agent Team

After installing MAS-Engineer, this is the recommended **stress-test demo**
that proves mas-engineer can build a 30-agent multi-architecture MAS
and run it end-to-end. It creates a complete system at `/tmp/multi-arch-30`
with 6 teams × 5 agents (3 different architectures), a master
orchestrator, full dashboard, and runs 44 live tests.

## What you get

A working 30-agent system with three orchestration architectures:

```
                        task input
                            |
                            v
              master-orchestrator            (root, routes to 1 of 6 teams)
                            |
   +------------------------+------------------------+
   |                        |                        |
   v                        v                        v
code-review-team   security-scan-team   data-quality-team
[HIERARCHICAL]      [FLAT]               [PIPELINE]
1 lead + 4 specs    5 peer scanners      5 sequential stages
   |                        |                        |
   v                        v                        v
perf-eval-team      refactor-team         doc-gen-team
[HIERARCHICAL]      [FLAT]                [PIPELINE]
1 lead + 4 specs    5 peer advisors       5 sequential stages

Total: 6 teams × 5 agents = 30 agents
Architectures: 10 HIERARCHICAL + 10 FLAT + 10 PIPELINE
```

Plus a complete dashboard:
- `/tmp/multi-arch-30/.mas/dashboards/data.json` (30 agents scored)
- `/tmp/multi-arch-30/.mas/mcp/server.js` (Node.js MCP server)
- `/tmp/multi-arch-30/.mas/mcp/dashboard.html` (chart.js webapp)
- `~/.config/goose/config.yaml`: `multi-arch-30-dashboard` extension registered
- `/tmp/multi-arch-30/.state/routing-test.jsonl` (6/6 routing correct)

**Why three architectures?** Same topology (6 teams × 5 agents), three
collaboration patterns. HIERARCHICAL = lead delegates. FLAT = peer vote.
PIPELINE = stage-handoff. Master orchestrator picks the right team by
task content. This proves mas-engineer handles architectural diversity,
not just one shape.

## How to run

### Option 1: via MAS-Engineer (recommended)

In any goose session inside `mas-engineer/`, just say:

```
Build the 30-agent multi-arch demo team and run all 44 tests.
```

MAS-Engineer will:
1. Confirm with you (R01 rule — once)
2. Delegate to sub_mas-dev-director → sub_mas-dev-builder
3. Initialize the project at `/tmp/multi-arch-30`
4. Generate 37 YAML recipes + 30 markdown instructions
5. Set up the dashboard (MCP server + data.json)
6. Run 44 live tests (master + 6 teams + 30 agents + routing)
7. Report PASS/FAIL with file inventory + routing table

Total runtime: ~2 minutes.

### Option 2: direct via the test recipe

```bash
cd /path/to/mas-engineer
goose run --recipe /root/.config/goose/recipes/dev-mas-engineer-30agents.yaml --no-session
```

The recipe is shipped pre-configured with the full 30-agent prompt.

### Option 3: manual (the original way)

If you want full control, the full prompt is below. Save it to
`/tmp/mas-engineer-30-prompt.txt` and run:

```bash
cd /path/to/mas-engineer
goose run --no-session -i - < /tmp/mas-engineer-30-prompt.txt
```

## Prerequisites

The user must have these set up before running:

1. **`~/.config/goose/config.yaml`** with provider=openai:

   ```yaml
   GOOSE_PROVIDER: openai
   GOOSE_MODEL: deepseek-v4-flash
   OPENAI_HOST: https://api.deepseek.com
   # Note: OPENAI_API_KEY is intentionally NOT here.
   # It must come via env-var (see #2).
   ```

2. **Environment variables** (the deepseek-via-openai shim):

   ```bash
   export DEEPSEEK_API_KEY=sk-...        # from platform.deepseek.com
   export OPENAI_API_KEY="$DEEPSEEK_API_KEY"   # alias: goose reads this
   export OPENAI_HOST="https://api.deepseek.com"   # NO /v1 suffix
   export GOOSE_MODEL="deepseek-v4-flash"
   export GOOSE_TELEMETRY_ENABLED=false
   ```

   Or source from the mas-engineer `.env` (see `.env.example` for the
   full template — **never commit real keys**).

3. **cwd must be inside the mas-engineer project** when invoking
   `goose run`. The dev-mas-engineer recipe does a STEP 0 MODE-CHECK
   and aborts if cwd is outside. From `/workspace/mas-engineer-src/mas-engineer/`
   this is auto-detected via `.mas-mode` and `.goosehints`.

## The full prompt

Copy everything between the lines:

```
═══════════════════════════════════════════════════════════════════
Build a complete Multi-Agent System called "multi-arch-30" at
/tmp/multi-arch-30. Do NOT just plan it — actually create the
files, run live tests, and report results.

ARCHITECTURE: 6 teams × 5 agents = 30 agents, each team uses a
             different orchestration architecture. Master orchestrator
             on top routes incoming tasks to the right team.

  task input (description)
      |
      v
  master-orchestrator                (root, routes to 1 of 6 teams)
      |
      +-- team selection by content type ----+
      |                                      |
      +-> code-review-team     [HIERARCHICAL]   (1 lead + 4 specialists)
      +-> security-scan-team   [FLAT]            (5 peer scanners + consensus)
      +-> data-quality-team    [PIPELINE]        (5 sequential stages)
      +-> perf-eval-team       [HIERARCHICAL]
      +-> refactor-team        [FLAT]
      +-> doc-gen-team         [PIPELINE]


ARCHITECTURE DISTRIBUTION:
- HIERARCHICAL: code-review-team, perf-eval-team (10 agents)
- FLAT:         security-scan-team, refactor-team (10 agents)
- PIPELINE:     data-quality-team, doc-gen-team (10 agents)


STEP 1 — Initialize the project skeleton
Run: python3 ~/.config/goose/recipes/tools/dev_generic_init.py \
     --init /tmp/multi-arch-30 --components all

STEP 2 — Create 30 agents in /tmp/multi-arch-30/recipe/sub/
         (6 teams × 5 agents each, plus 1 master orchestrator at
          /tmp/multi-arch-30/recipe/multi-arch-30.yaml)

=== TEAM 1: code-review-team [HIERARCHICAL] ===
Lead agent delegates to 4 specialists. Lead aggregates, makes final call.

1. code-review-lead.yaml (LEAD — receives task, delegates, aggregates)
2. code-review-style.yaml (SPECIALIST — PEP8/formatting)
3. code-review-perf.yaml (SPECIALIST — algorithmic complexity)
4. code-review-correctness.yaml (SPECIALIST — logic bugs)
5. code-review-readability.yaml (SPECIALIST — naming/comments)

=== TEAM 2: security-scan-team [FLAT] ===
5 equal-weight scanners. Consensus on findings.
1. security-scan-1-sast.yaml      (static analysis)
2. security-scan-2-secrets.yaml   (hardcoded creds)
3. security-scan-3-deps.yaml      (vulnerable deps)
4. security-scan-4-input.yaml     (injection: SQLi/XSS/cmd)
5. security-scan-5-crypto.yaml    (weak hash/cipher/random)

=== TEAM 3: data-quality-team [PIPELINE] ===
Stage 1 → Stage 2 → Stage 3 → Stage 4 → Stage 5. Sequential handoff.
1. dq-stage-1-profile.yaml   (rows, columns, types, missing %)
2. dq-stage-2-validate.yaml  (schema/types/range checks)
3. dq-stage-3-anomalies.yaml (outliers, duplicates, drift)
4. dq-stage-4-enrich.yaml    (imputation suggestions, dedup key)
5. dq-stage-5-report.yaml    (score 0-100, findings, recommendations)

=== TEAM 4: perf-eval-team [HIERARCHICAL] ===
Same shape as code-review-team but for runtime perf.
1. perf-eval-lead.yaml
2. perf-eval-cpu.yaml        (hot functions, algorithmic)
3. perf-eval-memory.yaml     (allocations, leaks, GC pressure)
4. perf-eval-io.yaml         (disk, network, serialization)
5. perf-eval-concurrency.yaml (locks, contention, races)

=== TEAM 5: refactor-team [FLAT] ===
5 equal-weight refactoring advisors. User picks suggestions.
1. refactor-1-simplify.yaml   (complex expressions)
2. refactor-2-extract.yaml    (extract function/class)
3. refactor-3-rename.yaml     (better names)
4. refactor-4-patterns.yaml   (apply design patterns)
5. refactor-5-decompose.yaml  (split god classes)

=== TEAM 6: doc-gen-team [PIPELINE] ===
Stage-by-stage doc generation.
1. doc-gen-1-analyze.yaml   (parse code, find public API)
2. doc-gen-2-skeleton.yaml  (generate doc skeletons)
3. doc-gen-3-examples.yaml  (add usage examples)
4. doc-gen-4-crosslink.yaml (cross-link related symbols)
5. doc-gen-5-render.yaml    (final markdown/HTML render)


STEP 3 — Create master orchestrator at /tmp/multi-arch-30/recipe/multi-arch-30.yaml
         that references all 6 team recipes via sub_recipes.

STEP 4 — Create instructions/ folder with one .md per agent (30 files).
         Each instruction describes role, inputs, outputs, and
         the architecture it operates in.

STEP 5 — DASHBOARD SETUP (mandatory)
a) cd /tmp/multi-arch-30
b) mkdir -p .mas/mcp
c) Copy MCP server files from mas-engineer:
     cp /workspace/dev-branch/mas-engineer/.mas/mcp/server.js .mas/mcp/
     cp /workspace/dev-branch/mas-engineer/.mas/mcp/package.json .mas/mcp/
     cp /workspace/dev-branch/mas-engineer/.mas/mcp/dashboard.html .mas/mcp/
d) cd .mas/mcp && npm install
e) Register multi-arch-30-dashboard extension in
   ~/.config/goose/config.yaml (under extensions:)
f) First dashboard-data refresh:
   python3 ~/.config/goose/recipes/tools/dev_dashboard_data.py /tmp/multi-arch-30
g) Verify: cat /tmp/multi-arch-30/.mas/dashboards/data.json
   Check "agents.total" >= 30 and "agents.healthy" == total

STEP 6 — LIVE TEST (mandatory, run each one):
a) goose run --recipe /tmp/multi-arch-30/recipe/multi-arch-30.yaml --no-session --explain
b-g) goose run --recipe /tmp/multi-arch-30/recipe/teams/<team>.yaml --no-session --explain
     (6 teams: code-review, security-scan, data-quality, perf-eval, refactor, doc-gen)
h) For each of 30 agent recipes, run:
   goose run --recipe <agent> --no-session --explain
i) python3 -c "import yaml, glob; [yaml.safe_load(open(f)) for f in \
   glob.glob('/tmp/multi-arch-30/recipe/**/*.yaml', recursive=True)]"
   Expect: 37 files parse (1 master + 6 team + 30 agent)

STEP 7 — ROUTING TEST:
Send 6 sample tasks (one per team) through the master orchestrator
and verify the orchestrator picks the correct team:
1. "Review this Python file for bugs"  → code-review-team (HIERARCHICAL)
2. "Check this code for SQL injection" → security-scan-team (FLAT)
3. "Analyze this CSV for missing values" → data-quality-team (PIPELINE)
4. "Profile this function's runtime"   → perf-eval-team (HIERARCHICAL)
5. "Simplify this 200-line function"   → refactor-team (FLAT)
6. "Generate docs for this module"     → doc-gen-team (PIPELINE)
Save the routing decisions to /tmp/multi-arch-30/.state/routing-test.jsonl

STEP 8 — Report:
- Total files created (expect 37 yaml + 30 md + dashboard files = 70+)
- Dashboard data.json summary (30+ agents.healthy)
- PASS/FAIL for: 7 team-recipe runs + 30 agent-recipe runs
                 + 1 yaml-parse-all + 6 routing tests = 44 checks
- Architecture distribution: 10 HIERARCHICAL, 10 FLAT, 10 PIPELINE
- Any YAML errors with line numbers
- List of all files with line counts

Critical:
- 6 teams × 5 agents = 30 agents exactly
- 2 HIERARCHICAL teams, 2 FLAT teams, 2 PIPELINE teams
- Master orchestrator MUST route to the right team
- All YAMLs MUST parse
- Dashboard MUST show 30 healthy agents
═══════════════════════════════════════════════════════════════════
```

## What you should see (PASS criteria)

```
=== Test Results — 44/44 PASS ===
Master orchestrator recipe load:    1/1
6 team recipe loads:                 6/6
30 agent recipe loads:               30/30
37 YAML files parse:                 37/37
6 routing tests (correct team):      6/6

=== Dashboard ===
agents.total:     30
agents.healthy:   30
agents.degraded:  0
avg_score:        1.0

=== Routing Behavior ===
"Review this Python file for bugs"     → code-review-team     (HIERARCHICAL)
"Check this code for SQL injection"    → security-scan-team   (FLAT)
"Analyze this CSV for missing values"  → data-quality-team    (PIPELINE)
"Profile this function's runtime"      → perf-eval-team       (HIERARCHICAL)
"Simplify this 200-line function"      → refactor-team        (FLAT)
"Generate docs for this module"        → doc-gen-team         (PIPELINE)
```

## Pitfalls hit (for the next operator)

These cost time on the first run. Read before debugging.

1. **`--recipe X` is incompatible with `--text Y`** — both error out
   with "cannot be used with --recipe". Use either:
   - `goose run --recipe X --no-session` (recipe defines the agent, no
     prompt input — the recipe's "prompt:" field is what gets used)
   - `goose run --no-session -i - < prompt.txt` (no recipe — goose
     auto-detects via `.mas-mode` and `.goosehints` in cwd)

2. **`No provider configured`** — fix by creating
   `~/.config/goose/config.yaml` with `GOOSE_PROVIDER: openai`.
   Without it, goose exits before even reading the recipe.

3. **MODE-CHECK aborts** — `dev-mas-engineer` checks that cwd is
   inside the mas-engineer project scope. Run from
   `mas-engineer-src/mas-engineer/` (or any path with `.mas-mode`
   and `.goosehints`). The error message tells you what to do.

4. **Sub-recipe relative paths break outside the recipes dir** — the
   recipe's `sub_recipes[].path: ./sub/X` resolves relative to the
   recipe's own location. If you copy a recipe to `/tmp/`, the
   `./sub/X` paths will be wrong. Either:
   - keep recipes in `~/.config/goose/recipes/` (sub-recipes resolve
     correctly), or
   - rewrite the paths to absolute in your copy.

5. **OPENAI_HOST must NOT have `/v1`** — goose 1.44 already appends
   `/v1`. If you set `OPENAI_HOST=https://api.deepseek.com/v1`,
   goose builds `/v1/v1/chat/completions` and gets 404. Use
   `https://api.deepseek.com` (no /v1).

6. **OPENAI_API_KEY must be env-var, not config-file** — goose 1.44
   silently ignores `OPENAI_API_KEY` in `config.yaml`. You MUST set
   it via `export OPENAI_API_KEY="$DEEPSEEK_API_KEY"`.

7. **`dev_generic_init.py` may be missing from `~/.config/goose/recipes/tools/`**
   if the install script symlinks differently. The fallback path is
   `/workspace/<your-mas-engineer>/tools/dev_generic_init.py`. mas-engineer
   will discover this on its own by running `find`, but expect the
   first attempt to fail before it self-corrects.

8. **Auto-confirm is needed for long prompts** — when sending a
   multi-page prompt in interactive mode, goose may ask "proceed?"
   mid-paste. The PTY driver auto-replies "yes, proceed" after 6s of
   idle. If running manually, watch for the prompt and press Enter.

9. **Timeout default is 300s** — `dev-mas-engineer.yaml` has
   `settings.timeout: 300`. The full 30-agent e2e takes ~90s but
   safer to bump to 1800s in your test recipe. `settings.max_steps`
   default is 50; bump to 200 for the same reason.

10. **R01 confirmation** — mas-engineer will ask "create a new MAS?"
    on first prompt. The PTY driver auto-confirms. In manual mode,
    reply "yes, proceed" once at the start.

## Reproduce (one-shot)

```bash
# Setup env
export DEEPSEEK_API_KEY=sk-...your-key...
export OPENAI_API_KEY="$DEEPSEEK_API_KEY"
export OPENAI_HOST="https://api.deepseek.com"
export GOOSE_MODEL="deepseek-v4-flash"
export GOOSE_TELEMETRY_ENABLED=false
export PATH="/root/.local/bin:$PATH"

# Ensure config.yaml exists
mkdir -p ~/.config/goose
cat > ~/.config/goose/config.yaml <<'YAML'
GOOSE_PROVIDER: openai
GOOSE_MODEL: deepseek-v4-flash
OPENAI_HOST: https://api.deepseek.com
GOOSE_TELEMETRY_ENABLED: false
YAML

# Save the prompt (the block between the lines above) to a file
cat > /tmp/mas-engineer-30-prompt.txt <<'PROMPT'
[paste the full prompt from the "The full prompt" section]
PROMPT

# Run (from mas-engineer project root for MODE-CHECK)
cd /path/to/mas-engineer
nohup goose run --recipe /root/.config/goose/recipes/dev-mas-engineer-30agents.yaml \
  --no-session > /tmp/multi-arch-30-run.log 2>&1 &
RUN_PID=$!
echo "Run started, PID=$RUN_PID. Tail the log: tail -f /tmp/multi-arch-30-run.log"
```

Total expected runtime: **~2 minutes** (init + 30 YAMLs + 30 MDs +
dashboard + 44 tests + routing).

## Expected lessons (UNVERIFIED — pending first live run)

⚠️ **These are HYPOTHESES, not measured facts.** They describe what
we expect to observe when this demo is run for the first time. None
of these have been verified end-to-end yet. See the EVIDENCE section
at the end of this file — it is empty.

- **30-agent MAS is small for mas-engineer.** Hypothesis: it will build
  the entire system + dashboard + run 44 tests in under 2 minutes. The
  bottleneck is expected to be goose's LLM calls for file generation,
  not mas-engineer logic.
- **3 architectures, 1 master orchestrator** — hypothesis: mas-engineer
  handles architectural diversity in one project. The master
  orchestrator's keyword-based routing is expected to be correct on
  all 6 sample tasks.
- **PTY mode is fine for long prompts** — hypothesis: goose will accept
  the 8.3 KB prompt via input-feld + Enter. The auto-confirm at 6s
  idle is expected to handle the "proceed?" mid-prompt question.
- **All routing decisions land in `.state/routing-test.jsonl`** —
  expected to be auditable, machine-readable, replayable. Same pattern
  as research-team's research log.
- **Dashboard 30/30 healthy on first run** — hypothesis: no
  degradation, no retries, no warnings. The 30 agents are expected to
  be well-formed on the first generation pass.
- **`dev-mas-engineer` is the right entry point** — hypothesis: it
  delegates to `sub_mas-dev-director` → `sub_mas-dev-builder` →
  `sub_mas-generic-init`, which together handle "create a new MAS"
  requests. No need to know which sub-recipe does what.

## EVIDENCE

**Status: NOT YET RUN.** This demo has been written but not yet
executed end-to-end. No log files, no dashboard output, no routing
test results, no agent health reports. The "Expected lessons" section
above is speculation based on the R110-4 PTY pipeline results, not
on actual measurements from this 30-agent recipe.

When the first run completes, fill in this section with:
- Date + run identifier (e2e-results/<date>/)
- Real PASS/FAIL counts for: 30/30 agent recipes parsed,
  6/6 team recipes dispatched, 6/6 sample tasks routed correctly,
  dashboard shows 30 healthy agents
- Actual measured runtime
- Raw log excerpt with tool-call markers
- Honest list of what was NOT tested (e2e skill section 'Evidence
  checklist' #1-6 — the 'write README from logs' rule)

Until then, treat the "Expected lessons" section as the test
hypotheses this demo is designed to confirm or refute.

## Related docs

- `DEMO-RESEARCH-TEAM.md` — the 5-agent research team demo (simpler,
  good first run)
- `E2E-DEMO-RESEARCH-TEAM.md` — the 5-agent e2e pitfalls + lessons
- `HOWTO-CREATE-AGENT.md` — single-agent recipe design guide
- `HOWTO-PACKAGE-TEAM.md` — packaging a team as a standalone dir
- `HOWTO-TEAM-STANDALONE.md` — running a team without mas-engineer
- `HOWTO-IM-PIPELINE.md` — the self-improvement pipeline
- `../.env.example` — env template (NEVER commit real keys)
