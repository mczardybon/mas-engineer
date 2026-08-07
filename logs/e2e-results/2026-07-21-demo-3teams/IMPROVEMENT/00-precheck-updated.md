# IM-PROVEMENT Pre-Check (Task 24) — UPDATED
Timestamp: 2026-07-21 10:59:42

## Additional finding: 2 sub-recipes have wrong `type: builtin` for summon
- /root/.config/goose/recipes/sub/sub_mas-team-packager.yaml
- /root/.config/goose/recipes/sub/sub_mas-general-improver.yaml

## Root cause
Issue 7355/7570: summon was moved to platform extension in goose 1.24.0 (PR #6964).
Recipe authors used `type: builtin` (which was correct pre-1.24).

## Correct value
`type: platform` (confirmed by other recipes in same directory that work).

## Plan adjustment
- Cannot run general-improver via goose CLI right now (it would fail to load summon itself)
- Must first patch sub_mas-general-improver.yaml AND sub_mas-team-packager.yaml
- Then run improvement pipeline

## Or alternative
Since manual fix already applied to the 3 teams, we can:
- Document the additional bug (type: builtin vs platform) as finding
- Patch the 2 recipes in-place
- Run general-improver to verify and search for any other affected recipes
