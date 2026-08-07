# Recovery Safezone Template

## Purpose
Fork Workspace. Creates a complete copy of the Workspace.
Changes happen ONLY in the Fork; main workspace stays untouched.
Only at explicit MERGE (after complete validation) is active.

## Source Sub-Recipe
sub_mas-recovery-safezone — Fork Workspace

## When To Use
- Experimental or destructive refactors
- Multi-agent parallel exploration
- Untrusted recipe validation
- Anything that might break the main workspace

## Steps
1. Check if a fork is already active (symlink mas-engineer_active)
2. Generate fork name (timestamp or fork_name)
3. Copy workspace to mas-engineer_fork_{name}
4. Set symlink mas-engineer_active → mas-engineer_fork_{name}
5. Validate fork with yaml.safe_load on master-constitution
6. Emit DONE with fork path; main stays untouched

## Input
- signal: 'FORK' | 'MERGE' | 'ABORT' | 'DIFF'
- workspace, fork_name
- merge_strategy (overwrite|selective) for MERGE

## Output
- mas-engineer_fork_{name}/ (parallel copy)
- mas-engineer_active symlink
- mas_result confirming "Main untouched"

## Edge Cases
- Fork already exists → warning + 'MERGE first'
- No main workspace → P1 error + '--init first'
- Permission denied on copy → P1 error
- Merge conflicts → P2 with diff report
