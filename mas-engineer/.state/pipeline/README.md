# Improvement-Pipeline Data Files

This directory holds the persistent output of each Improvement-Pipeline stage.

## Files

| File | Written by | Read by | Schema |
|------|------------|---------|--------|
| `findings.yaml` | im-finder (Stage 1) | im-rank (Stage 2) | findings[] with {id, type, severity, file, issue, impact, fix} |
| `ranked_findings.yaml` | im-rank (Stage 2) | im-designer (Stage 3) | ranked_findings[] with {id, priority, severity, type, file, rank_score} |
| `patches.yaml` | im-designer (Stage 3) | im-validator (Stage 4) | patches[] with {file, field, from, to, reason, type, priority, current_chars, target_chars} |
| `validation.yaml` | im-validator (Stage 4) | general-improver (Stage 5) | validation: {status, details, recommendation[], approved_count, rejected_count} |

## Reset

To start a fresh pipeline run, clear the directory:
```
rm -f .state/pipeline/*.yaml
```

## Convention

Each stage's file MUST start with:
```yaml
stage: <1-5>
agent: <name>
timestamp: <ISO-8601>
input_file: <path to previous stage's output, or 'none'>
# <schema description>
```

This makes the data flow auditable: each file knows its own stage, agent, and predecessor.
