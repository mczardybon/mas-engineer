# MAS-Engineer Prompts

This folder contains **ready-to-use prompts** for MAS-Engineer. Each
prompt is a complete, tested example that builds a real Multi-Agent
System. Use them as:

- **Templates** — copy and modify for your own projects
- **Learning material** — see how a well-structured prompt looks
- **Working demos** — paste them into a goose session and they just work

## How to use

### Option 1: paste into goose session

```bash
cd /tmp/mas-engineer/mas-engineer
goose session
# then paste the prompt below
```

### Option 2: pipe to goose from command line

```bash
cd /tmp/mas-engineer/mas-engineer
cat prompts/research-team.txt | goose run --no-session -i -
```

### Option 3: load via the demo-runner sub-recipe

```bash
goose run --recipe recipe/sub/sub_mas-demo-runner.yaml --no-session
```

This is the same prompt, but wrapped in a sub-recipe that asks for
R01 confirmation first.

## Available prompts

| Prompt | Builds | Time | Tests |
|--------|--------|------|-------|
| [research-team.txt](research-team.txt) | 5-agent research pipeline + dashboard | ~3 min | 14/14 PASS |

## Anatomy of a good MAS-Engineer prompt

Every prompt here follows the same structure:

1. **Goal** — what to build, where to put it
2. **STEP 1** — initialize project skeleton (use `dev_generic_init.py`)
3. **STEP 2** — define each agent (role, inputs, outputs, MANDATORY gates)
4. **STEP 3** — wire agents together (orchestrator + sub_recipes)
5. **STEP 4** — setup dashboard (copy MCP server, npm install, register extension)
6. **STEP 5** — live tests (goose --explain, yaml.safe_load, dashboard checks)
7. **STEP 6** — report results (file list, test table, architecture diagram)
8. **Critical guard** — non-negotiable rules (e.g. "source-verifier is MANDATORY")

## Design your own prompt

Use one of the examples as a template. The pattern is:

```
Build a complete Multi-Agent System called "<name>" at <path>.
Do NOT just plan it — actually create the files, run live tests,
and report results.

STEP 1 — Initialize the project skeleton
Run: python3 ~/.config/goose/recipes/tools/dev_generic_init.py
     --init <path> --components all

STEP 2 — Create N agents in <path>/recipe/sub/:

1. <name>-orchestrator.yaml (root)
   - <responsibilities>

2. <specialist-1>.yaml
   - <responsibilities>

3. <specialist-2>.yaml (MANDATORY — quality gate)
   - <responsibilities>

[... more agents as needed ...]

STEP 3 — Create orchestrator root recipe that references all agents
via sub_recipes field.

STEP 4 — DASHBOARD SETUP
a) Copy MCP server files from mas-engineer to <path>/.mas/mcp/
b) Run npm install
c) Register framework-dashboard extension in ~/.config/goose/config.yaml
d) First dashboard refresh via dev_dashboard_data.py

STEP 5 — LIVE TEST (mandatory):
a) goose run --recipe <root> --no-session --explain
b) ... (one per agent)
N) yaml.safe_load all recipes

STEP 6 — Report:
- List all files created
- Show dashboard data.json summary
- Show test PASS/FAIL table
- Show architecture diagram

Critical: every result MUST pass through <quality-gate-name> before
reaching the user. No unverified claims escape the pipeline.
```

## Tips for writing your own

- **Be specific about MANDATORY gates** — what quality controls must
  never be bypassed?
- **Define inputs and outputs** for each agent explicitly
- **Make it testable** — include concrete checks in STEP 5
- **Include dashboard setup** — users expect visual feedback
- **Show architecture** — a diagram in STEP 6 helps the user understand

## See also

- [docs/DEMO-RESEARCH-TEAM.md](../docs/DEMO-RESEARCH-TEAM.md) — Detailed
  guide for the research-team demo
- [docs/governance.md](../docs/governance.md) — R-rules MAS-Engineer follows
- [docs/lessons-learned.md](../docs/lessons-learned.md) — Hard-won knowledge
