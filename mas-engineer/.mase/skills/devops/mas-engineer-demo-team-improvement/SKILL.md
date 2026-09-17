---
name: mas-engineer-demo-team-improvement
description: How to improve mas-engineer demo-team projects (the recipes the mas itself generates) — file layout, R32 split pattern, constitution fix, validation workflow
category: devops
---

## When to use

Load this skill when: How to improve mas-engineer demo-team projects (the recipes the mas itself generates) — file layout, R32 split pattern, constitution fix, validation workflow.

For mas-engineer framework development, this skill provides domain-specific guidance that supersedes generic workflows.



# MAS-Engineer Demo-Team Improvement

The demo-team is a **mas-engineer-generated project tree** at `recipe/sub/demo-team/`. The mas builds these for users (e.g. research-team, code-reviewer) — they are NOT mas-internal agents.

## File layout (post-R32)

recipe/sub/demo-team/
├── code-reviewer.yaml              # USER-FACING entry (thin delegator)
├── code-reviewer-ORIGINAL.yaml    # Archived original (legacy/)
├── demo-runner.yaml                # MAS-INTERNAL: runs research-team demo
├── analytics-reporter.yaml         # MAS-INTERNAL
├── code-reviewer-{director,reporter,synthesizer,validator}.yaml  # PRE-EXISTING (pre-R32 multi-role)
└── cr-{validator,validator-orchestrator,validator-crosschecker,validator-scorer,...}.yaml  # R32 SPLIT (16 files)

Legacy archive: `recipe/sub/legacy/code-reviewer-*-ORIGINAL.yaml`

## R32 split pattern (NN1 finding: multi-role agent)

For each multi-role agent (5-6 distinct roles in one file), mas-engineer created:

1. **Thin delegator** (original filename) — e.g. `cr-validator.yaml`
   - has same name as before, but stripped to 1 role + delegation
   - references orchestrator: "delegate to cr-validator-orchestrator"
2. **Orchestrator** (1 file) — `cr-validator-orchestrator.yaml`
   - coordinates the 2 sub-agents
3. **Sub-agents** (2 files) — `cr-validator-crosschecker.yaml`, `cr-validator-scorer.yaml`
   - each has 1 focused role

Total: 4 agents × 4 files = **16 sub-agent files** created.

## CRITICAL: constitution-reference bug

R31 + R32 both **forgot to add** `constitution: sub_mas-master-constitution.yaml` to newly created sub-agents. 100% of pre-existing sub-agents have it, but 0% of new ones did.

**Symptom:** post-push e2e 9-check (see below) flags them.
**Fix:** add `constitution: sub_mas-master-constitution.yaml` line right after `name:` line in every new sub-agent file.

This bug exists in **both** R31 (21 files) and R32 (16 files) = 37 files. Single commit fix.

## Pre-push e2e (9-check) — manual replacement for sub_mas-pre-push-validator

`sub_mas-pre-push-validator.yaml` is **interactive** (R01 confirmation), so we run the 9 checks directly:

1. YAML syntax: `find recipe -name "*.yaml" | xargs python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))"`
2. Constitution coverage: parse all recipe/sub/**/*.yaml, count `constitution: sub_mas-master-constitution.yaml` — should be 100% of sub-agents
3. Duplicate names: `Counter(yaml.safe_load(f).get('name') for f in ...)` — flag if any name appears >1×
4. Secret scan: `git ls-files | xargs grep -lE "sk-[a-f0-9]{30,}|ghp_[A-Za-z0-9]{30,}"`
5. No .bak files: `git ls-files | grep -E "\.bak$|\.backup"`
6. New files complete: all new files have name+version 1.0.0+constitution
7. Originals archived: `ls recipe/sub/legacy/*-ORIGINAL.yaml`
8. Sub-recipe refs: extract `sub_mas-[a-z0-9-]+` from all files, diff against existing
9. Schedule updated: `grep "R32\|round: 32" .mase/schedule.yaml`

## How to run demo-team e2e

`demo-runner.yaml` is **interactive** (asks R01 confirmation). Don't run it via `--no-session`. It will hang.

Instead: run the 9-check e2e above (catches structural issues) and trust manual user-prompt testing for runtime behavior.

## Recipe-run command (R32-style)

```bash
export PATH="$HOME/.local/bin:$PATH"
export RECURSION_OVERRIDE=2
export MAS_TASK=SPLIT_DEMO_TEAM  # or similar task name
export MAS_CONFIRM=yes
export MAS_APPROVE=y
export MAS_WEB_RESEARCH=no
export MAS_FINDINGS_FILE=/path/to/findings.json
export MAS_TARGET_SCOPE=recipe/sub/demo-team
export OPENAI_API_KEY=sk-...
export OPENAI_HOST=https://api.deepseek.com
export DEEPSEEK_API_KEY=sk-...
cd /workspace/mas-engineer-src/mas-engineer
goose run --recipe recipe/sub/sub_mas-general-improver.yaml --no-session --with-builtin developer \
  --params "workspace=/workspace/mas-engineer-src/mas-engineer,task=SPLIT_DEMO_TEAM,confirm=yes,approve=y,web_research=no,override_mode=full,findings_file=...,target_scope=recipe/sub/demo-team"
```

## Pitfalls

- `--no-session` + `RECURSION_OVERRIDE=2` is the only reliable way to run mas-engineer non-interactively
- mas-engineer takes ~3-5 min per round (design+validate+apply)
- pre-push-validator is interactive — do manual 9-check instead
- demo-runner is interactive — don't try to test demo-team e2e via goose
- sub-agents MUST have `constitution: sub_mas-master-constitution.yaml` (pre-existing 100% have it, new ones don't)
- legacy files keep `name:` field even though they share name with new thin delegator — this is intentional

## Related skills

- `im-pipeline-v2-with-developer` — how to run mas-engineer pipeline
- `mandatory-e2e-before-push` — e2e gate
- `pre-push-goose-validation` — pre-push checks
- `mas-engineer-verification-theater-guard` — don't trust "PASS" claims
- `secret-leak-defense` — secret scan before push

## R35 outcomes (2026-07-24, commit afa5502)

- mas-engineer R35 **DID** add constitution-reference to all 8 new sub-agents — F-CONST-002 fixed
- BUT it did NOT address F-CONST-001 (9 pre-existing missing), F-VALID-001 (validator check), F-VALID-002 (non-interactive mode)
- **Lesson:** user-findings are INPUT but mas-engineer prioritizes its own scan/rank output. To get specific findings addressed, may need to put them in recipe/instructions/ as a persistent rule, not as one-shot input.
- 20 files in commit, +1940/-336, 11 new sub-agents, 3 splits
