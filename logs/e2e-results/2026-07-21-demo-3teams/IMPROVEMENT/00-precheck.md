# IM-PROVEMENT Pre-Check (Task 24)
Timestamp: 2026-07-21 10:59:24

## Findings
- goose CLI: 1.43.0 available at /root/.local/bin/goose
- general-improver recipe: /root/.config/goose/recipes/sub/sub_mas-general-improver.yaml
- instructions: /workspace/mas-engineer-src/mas-engineer/recipe/instructions/sub_mas-general-improver.md
- Bug class confirmed: Issue 7355/7570 (PR #6964) — sub_recipes/load moved from builtins to summon platform extension; recipes with own extensions-block need explicit `extensions: [summon]`

## 3 teams to fix
1. /tmp/sales-team/recipe/sales-team.yaml
2. /tmp/translator-team/recipe/translator-team.yaml
3. /tmp/marketing-team/recipe/marketing-team.yaml

## Status BEFORE improvement run
- All 3 already have `extensions: [summon]` applied manually (manual fix from earlier this session)
- 3 sub-orchestrators (sales-orchestrator, translator-orchestrator, marketing-orchestrator) had it originally
- Manual fix verified via `goose run --recipe ... --render-recipe` (no parse error)
- E2E blocked: DEEPSEEK_API_KEY not in env (sandbox restriction)

## Plan
- Run general-improver with explicit prompt to confirm the fix-pattern is correct and search for any other affected recipes
- Re-E2E if key available; otherwise document and rely on manual fix
