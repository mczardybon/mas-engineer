# Commit Strategy — 2026-07-24 E2E Run

## Status
- ✅ FULL_IMPROVEMENT R41 applied 10 patches (P6, P7, P8, P9, P11, P12, P13, P14, P15, P16)
- ✅ APPLY_ONLY R42 confirmed idempotency
- ⚠️ Pre-push-validator: 10/11 PASS, 1 BLOCKED (Check 10: e2e-baseline 80.95% < 93.33%)
- ⚠️ ROOT-CAUSE: 1 of mas's applied patches (P8 in
  `sub_mas-framework-scan-agent.yaml`) has `promint:` typo instead of `prompt:`
- ⚠️ Per user-correction 2026-07-23 ("Hermes editiert keine Datein, Mas muss
  alles selbst machen"), this typo must be fixed by mas in next round, not by
  Hermes.

## Decision
**Commit 1 (now):** documentation-only — e2e evidence + report + state files
**Commit 2 (later, after mas fix):** recipe edits (P6-P16) + legacy backup

This way:
- e2e evidence is preserved on master (searchable for future runs)
- mas's own-bug-in-patch is documented and visible
- mas can fix `promint:` in next round and we commit recipes after

## Files for Commit 1

```
?? mas-engineer/.mase/pipeline/signal_apply_only_done_20260724_1746.yaml
?? docs/E2E-SELF-IMPROVEMENT-REPORT-2026-07-24.md
?? mas-engineer/logs/e2e-evidence-gen2/                         (4 logs)
```

Plus modified state files:
```
 M mas-engineer/.mase/pipeline/patches.yaml
 M mas-engineer/.mase/pipeline/self_audit.yaml
 M mas-engineer/.mase/pipeline/signals.log
 M mas-engineer/.mase/pipeline/validation.yaml
 M mas-engineer/.mase/pre-push-e2e-baseline.json
 M mas-engineer/.mase/schedule.yaml
 M mas-engineer/.mase/todo.md
```

## Files for Commit 2 (after mas fixes promint typo)

```
 M mas-engineer/recipe/sub/security-scanner.yaml
 M mas-engineer/recipe/sub/sub_mas-framework-scan-agent.yaml
 M mas-engineer/recipe/sub/sub_mas-intention-parser.yaml
 M mas-engineer/recipe/sub/sub_mas-test-director.yaml
?? mas-engineer/recipe/sub/legacy/sub_mas-framework-scan-agent-ORIGINAL.yaml
?? mas-engineer/recipe/sub/sub_mas-framework-auditor.yaml
?? mas-engineer/recipe/sub/sub_mas-security-sqli-scanner.yaml
?? mas-engineer/recipe/sub/sub_mas-test-executor.yaml
?? mas-engineer/recipe/sub/sub_mas-test-validator.yaml
```

## Mas's bug — what needs fixing

In `recipe/sub/sub_mas-framework-scan-agent.yaml` (P8 in R41):
```yaml
# WRONG (current state):
promint: |
  ...

# RIGHT (after mas fix):
prompt: |
  ...
```

This typo was introduced by mas's own P8 patch — it survived the
self-audit (R09) and R10 (yaml-syntax) because YAML treats `promint`
as a valid custom key. Only pre-push-validator's recipe-schema-check
detects that `prompt` field is missing.
