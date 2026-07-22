# Recovery Timeline Template

## Purpose
Time-travel system. Analyzes ALL checkpoints for YAML validity.
Finds the BEST (most recent valid) checkpoint automatically.
Combines checkpoint data + changes.json + YAML health.

## Source Sub-Recipe
sub_mas-recovery-timeline — Time-travel system

## When To Use
- After a failed change with no obvious rollback point
- When current state is corrupted but checkpoints exist
- Periodic health audit across all snapshots
- Picking the safest restore target automatically

## Steps
1. Enumerate .state/checkpoints/ entries
2. For each, run yaml.safe_load on all recipe files
3. Score each checkpoint: recency + validity + completeness
4. Cross-reference with changes.json deltas
5. Pick BEST checkpoint (highest score, most recent)
6. Emit recommendations and full ranking

## Input
- signal: 'FIND_BEST' | 'LIST_VALID' | 'RANK' | 'COMPARE'
- workspace
- min_score (optional threshold)

## Output
- timeline_report.json
- ranked_checkpoints[].yaml
- mas_result with best_checkpoint.path and score

## Edge Cases
- No checkpoints found → P1 error
- All checkpoints invalid → P1 error (escalate to defib)
- changes.json corrupted → P3 warning, skip delta bonus
