---
name: bulk-findings-fixer
description: The full history and current usage of tools/bulk_findings_fixer.py — auto-fixes ~88% of mas-engineer findings via template-injection, including the v1 incident where it broke 148/148 YAML files, its root cause, and the v2 safety requirements. Supersedes bulk-findings-fixer-README.md, bulk-fixer-v1-WARNING.md, bulk-fixer-v1-bug-postmortem.md, and bulk-findings-fixer.md (merged 2026-07-28 — these were 4 files documenting one tool's evolution across 2026-07-24).
category: mas-engineer
---

# bulk_findings_fixer.py — auto-fix mas-engineer findings via template-injection

## Purpose
Apply template-injection fixes to recipe files based on `.state/pipeline/findings.yaml`. Roughly 88% of findings (1,691 of 1,929 in the round this was built for) fall into auto-fixable categories.

## ⚠️ Incident history — read before using

**2026-07-24 19:14 — v1 broke 148/148 files.** `bulk_findings_fixer.py --apply` ran across 148 files. Result: every single one produced invalid YAML. `sub_mas-pre-push-validator.yaml` failed to load:
```
Error: Invalid recipe: could not find expected ':'
  in "recipe/sub/sub_mas-pre-push-validator.yaml", line 40, column 1
```

**Root cause**: the script appended snippets to the end of each file without checking (a) whether the YAML block was already closed, or (b) whether the snippet text was itself YAML-safe. Two concrete breakages:
```yaml
# II1 snippet — BREAKS: this is a nested mapping, not plain text
OUTPUT-FORMAT: All outputs conform to:
  {ok: bool, data: <schema>, error: str|None, request_id: str}

# BB1 snippet — risk: unicode bullet chars can be misread as BOM by some parsers
PROHIBITION-LIST (R09):
  ⛔ Never edit general-improver.yaml (R04)
  ⛔ Never skip self-audit (R09)
```

**Rollback**: `git checkout -- recipe/ tools/` reverted all 148 files; the validator worked again immediately after.

**What was learned**: test YAML validity after *every* file modification — never "fire and forget" an apply step across many files. This directly reinforced the verification-theater-guard principle: apply-without-verify is not acceptable, no matter how conservative the templates look on paper.

**v2 requirements** (mandatory before any future `--apply`):
1. Wrap injected snippets in a YAML block-scalar (`prompt-fix: |\n  <snippet>`) or as `#`-comments — never raw flow-mapping-looking text appended blind.
2. Validate every file immediately after modification: `python3 -c "import yaml; yaml.safe_load(open(file))"`.
3. On any validation failure: revert that file and report it, don't continue silently.
4. Batch by concern (e.g. K1+L2 = "robustness", G2+F3+F4 = "context-awareness"), never all ~150 files in one run/commit.
5. F3/F4 (header-snippets) inject at the recipe's TOP, not the file end.

## Coverage table (from the round this was built for — recount per-round, don't assume these numbers are current)

| Type | Count | Fix |
|---|---|---|
| Q3 | 149 | FALSE-POSITIVE — 'title' is valid, skip, don't fix |
| K3 | 147 | retry-snippet |
| U1 | 144 | rollback-snippet |
| L1 | 143 | session-cleanup-snippet |
| G2 | 136 | mode-detection-snippet |
| K1 | 135 | try/except-snippet |
| L2 | 134 | log-rotation-snippet |
| II1 | 133 | format/schema-snippet (YAML-unsafe in v1 — see incident) |
| B3 | 129 | context-info-snippet |
| C2 | 121 | regex renumber steps |
| BB1 | 96 | prohibition-list-snippet (YAML-unsafe in v1 — see incident) |
| C1 | 96 | (auto-applied via BB1) |
| O1 | 88 | output-schema-snippet |
| F4 | 25 | I_AM-identity-snippet |
| F3 | 15 | MODE-CHECK-snippet |

**NOT auto-fixable, needs reasoning** (~12%): V1 (pre-apply check), B2 (prompt length varies), NN1 (multi-role agents — needs split-design), H1 (constitution ref edits), NN3 (scope_bloat — needs refactor), Y1 (O(n²) loop — needs algorithmic fix), T1/C4 (hardcoded paths / outdated refs), MM4/MM6/Q1/E1 (one-off, trivial but non-templatable).

## Usage (by mas-engineer itself, NOT by Hermes — per user-correction 2026-07-23: "Mas muss alles selbst machen")

```bash
python3 tools/bulk_findings_fixer.py --stats                    # stats only
python3 tools/bulk_findings_fixer.py --dry-run                  # see the diff, no writes
python3 tools/bulk_findings_fixer.py --apply --types K3,U1,L1   # apply specific types
python3 tools/bulk_findings_fixer.py --apply                    # apply all auto-fixable
python3 tools/bulk_findings_fixer.py --findings .state/pipeline/roundN_findings.json
```

### Idempotency
Each template carries a unique trigger-marker, e.g. `<!-- BULK-FIX:K3:retry-snippet -->`. Re-running is safe — already-injected snippets are detected and skipped. **Don't delete trigger-markers manually** — doing so causes the next run to re-insert the snippet.

### When mas should call this
After im-finder has produced `findings.yaml`, before im-validator (so `patches.yaml` includes the auto-fixed recipes), as part of a FULL_IMPROVEMENT or APPLY_ONLY run.

### After running
mas's im-validator must run the pre-push-validator's recipe-schema-check to confirm nothing broke; the e2e-test suite must run the modified recipes to confirm no regression; commit in batches, one commit per concern.

## Risk assessment
- **Low**: templates are conservative — they append to existing instructions, never delete. Still review diffs.
- **Medium**: modifying 100+ files in one run risks tripping a pre-push-validator "too many changes" rule — batch per concern.
- **High**: idempotency depends entirely on the trigger-marker surviving. Don't touch markers by hand.

## What this is NOT
- Not a magic-bullet — ~12% of findings need human/AI reasoning (NN1, NN3, MM4, MM6, MM8, T1, Y1, E1, Q1, C4, F3, F4 in edge cases).
- Not a replacement for mas-engineer's design-stage (im-designer).
- Not a single commit — it touches many files and must be split per-concern.

## Pitfalls
1. Q3 is a false-positive type — fixing it would corrupt valid `title` fields.
2. C2's regex renumbering only matches lines starting with `^\s*\d+\.\s+` — verify it didn't miscount elsewhere.
3. Deleting a trigger-marker by hand silently un-does idempotency protection.
4. Modifying 100+ files is a lot — expect the pre-push-validator to push back; batch by concern.
5. Templates only add, never delete — still worth a diff review before commit.

## File location
`tools/bulk_findings_fixer.py` (in the mas-engineer repo).

## Reference
- Incident: 2026-07-24 19:14, v1 broke 148/148 files, reverted same day
- Related skills: `pre-push-gate` (validator + e2e must both pass after any apply), `mas-engineer-verification-theater-guard` (apply-without-verify is exactly the failure mode this guards against)
