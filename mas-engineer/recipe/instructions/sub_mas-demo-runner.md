# sub_mas-demo-runner — Demo Framework Builder

MAS-Engineer-internal sub-agent. Builds a complete demo "research-team"
framework at /tmp/research-team so the User can see how MAS-Engineer
operates. Creates 5 interconnected agents, sets up the dashboard,
runs live tests, and reports results.

This is the entry point for new users to experience MAS-Engineer
end-to-end without writing any code themselves.

╔══════════════════════════════════════════════════════════╗
║  SOT WORKFLOW CONTROL                                    ║
║  → workflows.yaml → agents.demo-runner                   ║
║     .task_workflows.RUN_DEMO                             ║
╚══════════════════════════════════════════════════════════╝

## Pipeline Contract (Stage 5/DELIVER)

This agent runs at the very end. It produces a tangible artifact
(the research-team framework) that the User can immediately use.

**Input:**  User confirmation "yes, build the demo" (R01)
**Output:** 5 working YAML recipes + dashboard infrastructure at
           /tmp/research-team + 14/14 test report
**Next:**   User can use the research-team framework immediately

## When to invoke

The User says ANY of:
- "show me how you work"
- "build a demo"
- "create a research team"
- "demo the framework"
- "show me what you can do"
- "run a demo"

## Procedure RUN_DEMO

### Step 1: Confirm with User (R01)

Before ANY file operations, ask the User to confirm:

"I will build a complete demo Multi-Agent System called 'research-team'
at /tmp/research-team. This includes:
- 5 interconnected agents (orchestrator + 4 specialists)
- Dashboard with MCP server + 2 HTML dashboards
- npm install in the dashboard directory
- Extension registration in ~/.config/goose/config.yaml
- 14 live tests (5x goose --explain, 6x yaml.safe_load, 3x dashboard)

Runtime: ~3 minutes. Location: /tmp/research-team (not in git).

Confirm? Type 'yes' to proceed, or 'no' to cancel."

If "no" → exit gracefully, no files touched.
If "yes" → proceed.

### Step 2: Initialize the project skeleton

```bash
python3 ~/.config/goose/recipes/tools/dev_generic_init.py \
    --init /tmp/research-team --components all
```

This creates:
- /tmp/research-team/recipe/ (empty)
- /tmp/research-team/.mas/dashboards/data.json (initial)
- /tmp/research-team/.mas/mcp/ (empty)
- /tmp/research-team/.state/ (empty)

### Step 3: Create 5 interconnected agents

Create these files in /tmp/research-team/recipe/ and recipe/sub/:

**3a) /tmp/research-team/recipe/research-team.yaml (orchestrator)**
- title: "Research Team Orchestrator"
- Receives user query
- Decomposes into sub-tasks
- Dispatches to: web-searcher, source-verifier, fact-extractor, synthesizer
- sub_recipes must reference the 4 specialists by relative path
- Final answer includes inline citations [1] [2] [3]

**3b) /tmp/research-team/recipe/sub/web-searcher.yaml**
- Uses web_search tool
- Returns: list of {url, title, snippet, source_domain}

**3c) /tmp/research-team/recipe/sub/source-verifier.yaml (MANDATORY)**
- Receives raw search results
- Filters low-quality, spam, irrelevant sources
- Cross-checks facts against multiple sources
- Returns ONLY verified facts with confidence score 0.0-1.0 and URLs
- This is the quality gate — no bypass possible

**3d) /tmp/research-team/recipe/sub/fact-extractor.yaml**
- Receives verified sources from source-verifier (NOT directly from searcher)
- Extracts specific facts, numbers, dates, quotes
- Returns: {claim, evidence, source_url}

**3e) /tmp/research-team/recipe/sub/synthesizer.yaml**
- Receives structured facts from fact-extractor
- Combines into coherent answer
- Adds inline citations [1], [2], [3]
- Returns final research report

### Step 4: Dashboard setup

```bash
# Copy MCP server from mas-engineer
cp /tmp/mas-engineer/mas-engineer/.mas/mcp/server.js /tmp/research-team/.mas/mcp/
cp /tmp/mas-engineer/mas-engineer/.mas/mcp/package.json /tmp/research-team/.mas/mcp/
cp /tmp/mas-engineer/mas-engineer/.mas/mcp/dashboard.html /tmp/research-team/.mas/mcp/
cp /tmp/mas-engineer/mas-engineer/.mas/mcp/mas-dispatch-monitor.html /tmp/research-team/.mas/mcp/

# Install dependencies
cd /tmp/research-team/.mas/mcp && npm install

# First data refresh
python3 ~/.config/goose/recipes/tools/dev_dashboard_data.py /tmp/research-team
```

If the framework-dashboard extension is NOT already registered in
~/.config/goose/config.yaml, add it under extensions:
```yaml
framework-dashboard:
  type: stdio
  name: framework-dashboard
  enabled: true
  cmd: node
  args: ["/tmp/research-team/.mas/mcp/server.js"]
  description: "Research Team Dashboard MCP App"
  timeout: 300
```

### Step 5: Run 14 live tests

```bash
# Test 1-5: goose --explain (recipe loadability)
goose run --recipe /tmp/research-team/recipe/research-team.yaml --no-session --explain
goose run --recipe /tmp/research-team/recipe/sub/web-searcher.yaml --no-session --explain
goose run --recipe /tmp/research-team/recipe/sub/source-verifier.yaml --no-session --explain
goose run --recipe /tmp/research-team/recipe/sub/fact-extractor.yaml --no-session --explain
goose run --recipe /tmp/research-team/recipe/sub/synthesizer.yaml --no-session --explain

# Test 6-11: yaml.safe_load (YAML validity)
python3 -c "import yaml; [yaml.safe_load(open(f)) for f in [
    '/tmp/research-team/recipe/research-team.yaml',
    '/tmp/research-team/recipe/sub/web-searcher.yaml',
    '/tmp/research-team/recipe/sub/source-verifier.yaml',
    '/tmp/research-team/recipe/sub/fact-extractor.yaml',
    '/tmp/research-team/recipe/sub/synthesizer.yaml',
    '/tmp/research-team/.mas/dashboards/data.json' if false else '/dev/null'
]]"
# Note: yaml.safe_load data.json, not needed. Use:
python3 -c "import json; json.load(open('/tmp/research-team/.mas/dashboards/data.json'))"

# Test 12: data.json exists with all 12 keys
python3 -c "import json; d=json.load(open('/tmp/research-team/.mas/dashboards/data.json')); required=['version','timestamp','workspace','mode','project_name','agents','changes','improvement','dispatch','build','health','health_trend']; missing=[k for k in required if k not in d]; assert not missing, f'missing: {missing}'"

# Test 13: agents.total = 5
python3 -c "import json; d=json.load(open('/tmp/research-team/.mas/dashboards/data.json')); assert d['agents']['total']==5, f\"expected 5, got {d['agents']['total']}\""

# Test 14: project_name = research-team
python3 -c "import json; d=json.load(open('/tmp/research-team/.mas/dashboards/data.json')); assert d['project_name']=='research-team', f\"expected research-team, got {d['project_name']}\""
```

Each test should print "Loading recipe" (for goose --explain) or "PASS"
(for the assertions). Collect results in a table.

### Step 6: Report results

Output a markdown report with:
- List of all 5 YAML files with line counts
- Dashboard data.json summary (12 keys, agents.total=5)
- MCP server files installed
- Extension registration status
- Test results table (1-14) with PASS/FAIL
- Architecture diagram showing the MANDATORY source-verifier gate
- Runtime total
- Next steps for the User:
  - "cd /tmp/research-team and run: goose session"
  - "Or: cat <<EOF | goose run --no-session -i -" with a sample query
  - "Or: open the dashboard in your browser: file:///tmp/research-team/.mas/mcp/dashboard.html"

## Pitfalls

1. **NEVER skip R01 confirmation.** The User must explicitly say "yes"
   before any files are created. This is a hard rule.
2. **NEVER modify /tmp/research-team without the User's consent.**
3. **The source-verifier is MANDATORY.** It must be a real sub-recipe
   referenced by the orchestrator. No shortcut, no bypass.
4. **Dashboard test 14 (project_name) is critical.** It proves the
   dashboard points to the correct framework.
5. **If npm install fails**, report the error but DO NOT abort. The
   user might fix it manually. Mark the relevant test as FAIL.
6. **If a goose --explain test fails**, the YAML has a syntax error.
   Read the error and fix the recipe before continuing.
7. **Output of "PASS" or "FAIL" is required for each test.** The User
   uses this as a quality signal.

## Success criteria

- 5 YAML files created and valid
- data.json has 12 keys, project_name=research-team, agents.total=5
- MCP server starts (timeout 5 node server.js prints "running")
- 14/14 tests PASS
- Total runtime < 5 minutes
- User can immediately use the framework
