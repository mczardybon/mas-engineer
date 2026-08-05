---
name: mas-engineer-demo-prompt-research-team
description: How to demo MAS-Engineer to a new user — one prompt that creates a 5-agent research team with source verification AND dashboard
category: devops
---

# MAS-Engineer Demo: Research Team (with Dashboard)

## When to use

User just installed MAS-Engineer and wants a working demo to prove it works.
Run this prompt to generate a complete "research-team" MAS at /tmp/research-team,
including a fully configured MCP dashboard.

## What gets created

5 interconnected agents + dashboard infrastructure:
- research-team.yaml (orchestrator)
- web-searcher.yaml, source-verifier.yaml (MANDATORY), fact-extractor.yaml, synthesizer.yaml
- .mas/dashboards/data.json (12 keys, 5 agents scored)
- .mas/mcp/server.js (Node.js MCP server, 3335 bytes)
- .mas/mcp/dashboard.html (19.5KB, chart.js webapp)
- .mas/mcp/mas-dispatch-monitor.html (second dashboard)
- ~/.config/goose/config.yaml: framework-dashboard extension registered

## Critical: how to invoke the prompt

**The prompt is NOT for `goose run --recipe dev-mas-engineer`!**

**Use:**
```bash
cd <path-to-mas-engineer-checkout>/mas-engineer   # your local repo path
cat /path/to/prompt.txt | goose run --no-session -i -
```

The `-i -` reads from stdin, and NOT specifying `--recipe` lets MAS-Engineer
bootstrap itself from the project context (the .mas-mode file).

**Why:** `--recipe` and `-i` are mutually exclusive. With `--recipe` the prompt
goes to that specific recipe. Without `--recipe` + `-i -` the prompt goes to
the default session, which detects the MAS context.

## The demo prompt (copy-paste)

```
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

STEP 4 — LIVE TEST (mandatory):
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

STEP 5 — Report:
- List all 6 files created with line counts.
- Show PASS/FAIL for each of the 5 + 6 = 11 checks.
- Show any YAML errors with line numbers.

Critical: every research result MUST pass through source-verifier
before reaching the user. No unverified claims in the final output.
```

## Verified result (2026-07-18, with dashboard)

- Runtime: 162 seconds
- 5 real YAML files + dashboard infrastructure
- research-team.yaml  — orchestrator with 4 sub_recipes
- web-searcher.yaml, source-verifier.yaml (MANDATORY), fact-extractor.yaml, synthesizer.yaml
- .mas/dashboards/data.json (1500B, 12 keys, agents: total=5, healthy=5, avg_score=1.0)
- .mas/mcp/server.js (3335B, starts: "Framework Dashboard MCP Server running")
- .mas/mcp/dashboard.html (19.5KB), mas-dispatch-monitor.html
- ~/.config/goose/config.yaml: framework-dashboard extension registered
- 14/14 tests PASS (5x goose --explain + 6x yaml.safe_load + 3x dashboard)

## Pitfalls

1. **`goose run --recipe X | cat prompt` does NOT work** — the master recipe
   ignores stdin. The prompt must go via `goose run -i -` (no --recipe).
2. **`-i -` and `--recipe` are mutually exclusive** — goose CLI error.
3. **User must be IN the mas-engineer directory** so context (`.mas-mode`) is
   detected.
4. **The "ack" at the end of the prompt** is the acknowledgement that satisfies
   the confirmation rule (R01).
5. **MAS-Engineer will delegate** to sub_mas-generic-init (for skeleton) and
   to its sub-recipe designer (for the 5 YAMLs). It works without
   `--with-builtin developer` because it has the `summon` extension.
6. **Demo project is at /tmp/research-team** — not in git, not pushed anywhere.

## How to verify after the run

```bash
# 1. Files exist
ls /tmp/research-team/recipe/
ls /tmp/research-team/recipe/sub/

# 2. All load
for f in /tmp/research-team/recipe/research-team.yaml \
         /tmp/research-team/recipe/sub/web-searcher.yaml \
         /tmp/research-team/recipe/sub/source-verifier.yaml \
         /tmp/research-team/recipe/sub/fact-extractor.yaml \
         /tmp/research-team/recipe/sub/synthesizer.yaml; do
  goose run --recipe $f --no-session --explain
done

# 3. YAMLs valid
python3 -c "import yaml; [yaml.safe_load(open(f)) for f in \
  ['/tmp/research-team/recipe/research-team.yaml',
   '/tmp/research-team/recipe/sub/web-searcher.yaml',
   '/tmp/research-team/recipe/sub/source-verifier.yaml',
   '/tmp/research-team/recipe/sub/fact-extractor.yaml',
   '/tmp/research-team/recipe/sub/synthesizer.yaml']]"
```
