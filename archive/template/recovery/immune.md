# Recovery Immune Template

## Purpose
YAML-Prevention & Syntax-Shield before each edit. First shield for MAS-Engineer.
Validates YAML, Python, and Shell syntax; prevents the 4/4 crash types.

## Source Sub-Recipe
sub_mas-recovery-immune — "Coronashield" YAML-Immune System

## When To Use
- Before any YAML file edit
- Before any Python file execution
- Before any Shell script start
- Anytime state validation is needed

## Steps
1. Validate YAML syntax via python3 yaml.safe_load
2. Check Python compatibility (syntax compile)
3. Run bash -n on shell scripts
4. Verify git state and workspace integrity
5. Emit observations with severity P1/P2/P3

## Input
- signal: 'CHECK_YAML' | 'CHECK_SYNTAX' | 'VERIFY_STATE'
- file_path, file_type (yaml|python|bash)
- workspace, state_path

## Output
- coronashield.log
- mas_result with validation_log entries (ok|error|warning)
- score and per-check detail

## Edge Cases
- Empty file → P2 warning
- Unicode errors → P3 info (try utf-8)
- Binary file detected → P1 error
- YAML exception not from yaml.Error → P1 error
