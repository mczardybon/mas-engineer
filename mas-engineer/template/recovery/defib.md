# Recovery Defib Template

## Purpose
Emergency revival. The LAST RESORT — if nothing else works.
No YAML parses? No sub-agent starts? DEFIB is the answer.
Loads a minimal emergency config (ONLY immune + timeline) and restores step by step.

## Source Sub-Recipe
sub_mas-recovery-defib — Emergency revival

## When To Use
- All other recovery stages have FAILED
- YAML parsing completely broken
- Sub-agents cannot start at all
- Last-chance revival before full re-init

## Steps
1. Write minimal dev-mas-engineer.yaml (EMERGENCY-MAS, recovery-mode)
2. Register ONLY immune + timeline sub-recipes
3. Set prompt to RECOVERY-mode (recovery --restore-best)
4. Validate the minimal config parses
5. Emit RESURRECT signal with minimal-config path
6. Gradual restore: add back other sub-recipes one by one

## Input
- signal: 'DEFIB' | 'RESURRECT' | 'DIAGNOSE'
- workspace
- reason (why defib was needed)

## Output
- recipe/dev-mas-engineer.yaml (minimal)
- defib.log with revival steps
- mas_result with recovery_step trail

## Edge Cases
- Workspace completely missing → P1: full re-init required
- Minimal config fails to parse → CRITICAL: manual intervention
- CAUTION: DEFIB corrupts current state — only after all else fails
