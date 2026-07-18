# MAS-Engineer Demo — Research Team

After installing MAS-Engineer, this is the recommended first run.
It builds a complete 5-agent "research-team" framework at
`/tmp/research-team` with a fully configured dashboard, and runs
14 live tests to prove everything works.

## What you get

A working research team with 5 interconnected agents:

```
User Query
    |
    v
research-orchestrator  (root, dispatches to specialists)
    |
    +--> web-searcher       (web_search tool)
    |
    +--> source-verifier    [MANDATORY quality gate]
    |    (filters spam, cross-checks, confidence 0.0-1.0)
    |
    +--> fact-extractor     (atomic claims + evidence)
    |
    +--> synthesizer        (final report with [1][2][3])
```

Plus a complete dashboard:
- `.mas/dashboards/data.json` (12 keys, 5 agents scored)
- `.mas/mcp/server.js` (Node.js MCP server)
- `.mas/mcp/dashboard.html` (chart.js webapp, 19.5KB)
- `.mas/mcp/mas-dispatch-monitor.html` (second dashboard)
- `~/.config/goose/config.yaml`: `framework-dashboard` registered

## How to run

### Option 1: via MAS-Engineer (recommended)

In any goose session inside `/tmp/mas-engineer/mas-engineer/`, just say:

```
Run the demo.
```

MAS-Engineer will:
1. Confirm with you (R01 rule)
2. Delegate to sub_mas-demo-runner
3. Create the framework + dashboard
4. Run 14 live tests
5. Report PASS/FAIL

Total runtime: ~3 minutes.

### Option 2: direct via the demo-runner recipe

```bash
cd /tmp/mas-engineer/mas-engineer
goose run --recipe recipe/sub/sub_mas-demo-runner.yaml --no-session
```

The sub-agent will still ask for R01 confirmation on first prompt.

### Option 3: manual (the original way)

If you want full control, the full prompt is in this file under
"The full prompt" below. Paste it into a fresh goose session:

```bash
cd /tmp/mas-engineer/mas-engineer
cat <<'EOF' | goose run --no-session -i -
[paste the prompt]
EOF
```

## The full prompt

Copy everything between the lines:

```
═══════════════════════════════════════════════════════════════════

Build a complete Multi-Agent System called "research-team" at
/tmp/research-team. Do NOT just plan it — actually create the files,
run live tests, and report results.

STEP 1 — Initialize the project skeleton
Run: python3 ~/.config/goose/recipes/tools/dev_generic_init.py
     --init /tmp/research-team --components all

STEP 2 — Create 5+ interconnected agents in
         /tmp/research-team/recipe/sub/:

1. research-orchestrator.yaml (root: /tmp/research-team/recipe/
   research-team.yaml)
   - Main entry point. Receives user query.
   - Decomposes into sub-tasks.
   - Dispatches to specialists.
   - Collects results.
   - Returns synthesized final answer WITH CITATIONS.

2. web-searcher.yaml
   - Uses web_search to find sources.
   - Returns: list of {url, title, snippet, source_domain}.

3. source-verifier.yaml (MANDATORY — quality gate)
   - Receives raw search results from web-searcher.
   - Filters low-quality, spam, irrelevant, single-source claims.
   - Cross-checks facts against multiple sources.
   - Returns ONLY verified facts with confidence score (0-1) and URLs.

4. fact-extractor.yaml
   - Receives verified sources from source-verifier.
   - Extracts specific facts, numbers, dates, quotes.
   - Returns {claim, evidence, source_url}.

5. synthesizer.yaml
   - Receives structured facts from fact-extractor.
   - Combines into coherent answer.
   - Adds inline citations [1], [2], [3].
   - Returns final research report.

STEP 3 — Create the orchestrator root recipe research-team.yaml
that references all 5 sub-recipes via sub_recipes field.

STEP 4 — DASHBOARD SETUP (mandatory)
a) Set up MCP dashboard for the new project:
   - cd /tmp/research-team
   - mkdir -p .mas/mcp
   - Copy MCP server files from mas-engineer:
     cp /tmp/mas-engineer/mas-engineer/.mas/mcp/server.js .mas/mcp/
     cp /tmp/mas-engineer/mas-engineer/.mas/mcp/package.json .mas/mcp/
     cp /tmp/mas-engineer/mas-engineer/.mas/mcp/dashboard.html .mas/mcp/
     cp /tmp/mas-engineer/mas-engineer/.mas/mcp/mas-dispatch-monitor.html
        .mas/mcp/
   - Run: cd .mas/mcp && npm install
   - Register framework-dashboard extension in
     ~/.config/goose/config.yaml (under extensions:)
b) First dashboard-data refresh:
   - python3 ~/.config/goose/recipes/tools/dev_dashboard_data.py
     /tmp/research-team
c) Verify dashboard:
   - cat /tmp/research-team/.mas/dashboards/data.json | python3 -m json.tool
     (must have: version, timestamp, workspace, mode, project_name,
      agents, changes, improvement, dispatch, build, health,
      health_trend)
   - Check that "agents.total" = 5 and "agents.healthy" = 5
   - Check that "project_name" = "research-team"
   - Check that "workspace" = "/tmp/research-team"

STEP 5 — LIVE TEST (mandatory):
a) goose run --recipe /tmp/research-team/recipe/research-team.yaml
   --no-session --explain
b) goose run --recipe /tmp/research-team/recipe/sub/web-searcher.yaml
   --no-session --explain
c) goose run --recipe /tmp/research-team/recipe/sub/source-verifier.yaml
   --no-session --explain
d) goose run --recipe /tmp/research-team/recipe/sub/fact-extractor.yaml
   --no-session --explain
e) goose run --recipe /tmp/research-team/recipe/sub/synthesizer.yaml
   --no-session --explain
f) python3 -c "import yaml; [yaml.safe_load(open(f))
   for f in ['/tmp/research-team/recipe/research-team.yaml',
            '/tmp/research-team/recipe/sub/web-searcher.yaml',
            '/tmp/research-team/recipe/sub/source-verifier.yaml',
            '/tmp/research-team/recipe/sub/fact-extractor.yaml',
            '/tmp/research-team/recipe/sub/synthesizer.yaml']]"
g) Test MCP server starts: timeout 5 node /tmp/research-team/.mas/mcp/
   server.js
   (should print "Framework Dashboard MCP Server running" on stderr
    before timeout)

STEP 6 — Report:
- List all 6 yaml files created with line counts.
- Show dashboard data.json summary (12 keys, 5 agents).
- Show MCP server files installed.
- Show extension registration in config.yaml.
- Show PASS/FAIL for 5+6+4 = 15 checks.
- Show any YAML errors with line numbers.

Critical: every research result MUST pass through source-verifier
before reaching the user. No unverified claims in the final output.

═══════════════════════════════════════════════════════════════════
```

## After the demo runs

You now have a working research team. Use it:

```bash
# Interactive
cd /tmp/research-team
goose session
# Then: "Research the latest developments in fusion energy"

# Or one-shot
echo "What are the main risks of quantum computing?" | \
  goose run --recipe /tmp/research-team/recipe/research-team.yaml --no-session
```

## Verified result (2026-07-18)

- Runtime: 162 seconds (2:42 min)
- 5/5 YAML files created and valid
- 5/5 recipes load via goose --explain
- Dashboard data.json has all 12 keys
- agents.total = 5, agents.healthy = 5
- MCP server starts successfully
- framework-dashboard extension registered

## What you can do next

- **Inspect the dashboard**: `cat /tmp/research-team/.mas/dashboards/data.json`
- **Modify an agent**: edit one of the YAMLs and re-run `goose --explain`
- **Add a new agent**: copy a sub-recipe and reference it from research-team.yaml
- **Use it for real research**: replace the mock web_search with the real one
- **Delete the demo**: `rm -rf /tmp/research-team` (no git, no harm)
