# Recovery Checkpoint Template

## Purpose
Snapshot-System. Creates complete workspace snapshots BEFORE changes.
Stores recipe/, tools/, docs/, state/ under .state/checkpoints/{timestamp}/.
Enables surgical restore ("Restore state from before 3 steps").

## Source Sub-Recipe
sub_mas-recovery-checkpoint — Snapshot-System

## When To Use
- Before risky multi-step changes
- Before merging a safezone fork
- Before any structural refactor
- Periodically during long sessions

## Steps
1. Generate timestamp (date +%Y%m%d_%H%M%S)
2. Copy recipe/ tree to .state/checkpoints/{ts}/recipe/
3. Copy tools/ tree to .state/checkpoints/{ts}/tools/
4. Copy docs/ tree to .state/checkpoints/{ts}/docs/
5. Copy state/ tree to .state/checkpoints/{ts}/state/
6. Write manifest with file counts and hashes
7. Emit signal DONE with snapshot path

## Input
- signal: 'SNAPSHOT' | 'RESTORE' | 'LIST' | 'PURGE'
- workspace, label (optional human-readable tag)
- target_timestamp (for RESTORE)

## Output
- .state/checkpoints/{timestamp}/ (full mirror)
- checkpoint_manifest.json (hashes + counts)
- mas_result with restore point reference

## Edge Cases
- Disk space low → P1 error before copy
- Existing snapshot with same ts → append suffix
- Restore target missing → P1 error
