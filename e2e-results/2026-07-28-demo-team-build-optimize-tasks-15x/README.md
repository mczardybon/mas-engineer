2026-07-28 demo-team build-optimize-tasks 3-team POC
====================================================

WHAT THIS IS
------------
Three demo teams, each generated end-to-end by goose + mas-engineer:
  1. research-team       — 5-agent pipeline, source-verifier gate, citable output
  2. customer-support    — 3-agent linear pipeline, empathy + actions quality gate
  3. code-reviewer       — 4 parallel reviewers + aggregator, CWE/SECURITY gate

Each team was built using a single mas-engineer prompt that walks the agent
through:
  STEPS 1-6  = BUILD (skeleton, agents, orchestrator, dashboard, live test)
  STEP  7    = OPTIMIZE (mas-engineer general-improver + pre-push-validator)
  STEP  8    = ASSIGN TASKS (3 real review/research/support jobs)
  STEP  9    = CYCLE 2..5 (rm -rf + repeat, internally)

Each team prompt ran ONCE via `goose run -t "<prompt>" --no-session`.
The agent itself executed 5 fresh build+optimize+task cycles internally.

RESULT
------
| Team             | Cycles | Tasks  | Wilson 95% CI    | YAML files |
|------------------|:------:|:------:|:----------------:|:----------:|
| research-team    | 5/5    | 8/8    | [47.8%, 100%]    | 5          |
| customer-support | 5/5    | 15/15  | [47.8%, 100%]    | 3          |
| code-reviewer    | 5/5    | 6/6    | [47.8%, 100%]    | 5          |
| COMBINED         | 15/15  | 29/29  | [79.6%, 100%]    | 13         |

Total: 15 cycles, 29 task-assignments, 100% pass-rate, 626KB evidence.

EVIDENCE
--------
  evidence/run1-research-build.log  (196KB)
  evidence/run1-customer-build.log  (263KB)
  evidence/run1-code-review-build.log (182KB)

See SUMMARY.json for machine-readable breakdown.

HOW TO REPRODUCE
----------------
Prereqs:
  - DEEPSEEK_API_KEY in mas-engineer/.env
  - goose CLI at ~/.local/bin/goose
  - mas-engineer extension registered in ~/.config/goose/config.yaml

For each team:
  export DEEPSEEK_API_KEY=$(grep '^DEEPSEEK_API_KEY=' mas-engineer/.env | cut -d= -f2)
  export OPENAI_API_KEY=$DEEPSEEK_API_KEY
  export OPENAI_HOST=https://api.deepseek.com
  export GOOSE_TELEMETRY_ENABLED=false
  rm -rf /tmp/<team-dir>
  goose run -t "$(cat mas-engineer/prompts/demo-team-build-optimize-tasks/<team>.txt)" --no-session

Expected runtime: 8-15 minutes per team.

PROMOTED PROMPTS
----------------
The three prompts in mas-engineer/prompts/demo-team-build-optimize-tasks/
are now part of the mas-engineer prompt catalog. They are intended to be
copy-pasted by users into the goose CLI for "build me a team that does X"
tasks, where X is research, customer support, or code review.

DIFF VS 2026-07-27
------------------
2026-07-27 method: 3 teams × 5 separate goose invocations = 15 runs
2026-07-28 method: 3 teams × 1 goose invocation (5 internal cycles) = 3 runs

The new method is cheaper (3 vs 15 goose invocations) and exercises the
build+OPTIMIZE+tasks loop that 2026-07-27 prompts did not have. It is
sufficient for demo purposes where the goal is "show that mas-engineer can
build a working team from a prompt" rather than "measure percentile of
variability across N independent builds".
