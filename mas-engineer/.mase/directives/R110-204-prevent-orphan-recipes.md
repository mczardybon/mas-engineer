# R110-204 — Prevent orphan-recipe bugs at registration time (DETECTION→CORRECTION→PREVENTION cycle)

## Context (the bug R110-203 just fixed)

R110-195 added `sub_mas-design-patches.yaml` (commit 1c3e66e) but never
registered it in `.mase/workflows.yaml` configs.mas-self.sub_agents. The
recipe was an orphan — undispatchable from any workflow. R110-203 fixed
it manually (1 line in workflows.yaml), Check 17 caught it, 1614/1614
pytest pass after fix.

But this is the SECOND time the same pattern bit us (R110-31 originally
documented the rule, R110-78 was a follow-up spec-drift, R110-198 added
Check 21 for caller-chains but not for orphan registration). The rule
exists in prose but is not enforced at recipe-creation time.

## Goal

Move orphan-recipe detection from "found by Check 17 after the fact"
to "blocked at commit time before the orphan ever lands". Two layers:

1. **DETECTION (already exists)**: `test_recipe_registry_consistency.py`
   has `test_mas_self_recipes_registered` — 108 recipes must all be
   in `workflows.yaml.configs.mas-self.sub_agents`. PASS now, but
   only ran AFTER the orphan was already in HEAD.

2. **CORRECTION (manual this time)**: 1-line edit in workflows.yaml
   to add `sub_mas-design-patches` to the `design:` subgroup.
   Should have been a CI-block, not a manual fix.

3. **PREVENTION (this directive's goal)**: add a pre-commit + pre-push
   check that compares `recipe/sub/*.yaml` against
   `.mase/workflows.yaml` configs.mas-self.sub_agents and BLOCKS
   any commit that adds a new recipe without registering it. This
   turns the orphan-bug class from "human-fix-required" to
   "machine-blocked-at-creation".

## Required changes (3 files)

### 1. `tools/dev_check_orphan_recipes.py` (NEW, ~80 lines)

Standalone Python script (no deps beyond stdlib + PyYAML), exit
0=clean / 1=orphan-found. Mirrors the test logic but runs as a
CLI tool so it can be wired into the pre-push-validator (Check 23)
and into a pre-commit hook (R110-128 follow-up).

Algorithm:
```
- glob recipe/sub/*.yaml (skip ORIGINAL_*)
- for each: parse, get name (e.g. "sub_mas-design-patches")
- load .mase/workflows.yaml, walk configs.mas-self.sub_agents
  (the dict-of-lists structure with category keys like
  `git:`, `python:`, `design:`, `dev:`, etc.)
- flatten all values to a set of registered names
- orphans = registered_recipes - workflow_sub_agents
- if orphans: print table + exit 1
- else: print "OK" + exit 0
```

Accept `--json` for CI consumption. The script is the SOURCE OF
TRUTH for what "registered" means — both the test and Check 23
call it.

### 2. `recipe/sub/sub_mas-pre-push-validator.yaml` (UPDATE, +1 check)

Add Check 23 — orphan-recipe detection — to the existing check list.
The check:
- runs `python3 tools/dev_check_orphan_recipes.py --json`
- if exit 1: append to blocked_reasons
- if exit 0: append to passed_checks

This is structural: every pre-push run will catch the orphan
BEFORE the push, not after. R110-198 was the same lesson for
caller-chains (Check 21); R110-204 is the same lesson for
registry-orhpans (Check 23).

### 3. `tests/test_dev_check_orphan_recipes.py` (NEW, ~60 lines)

Pytest test for the new tool. 4 cases:
- (a) clean state: 0 orphans, exit 0
- (b) add a temp `recipe/sub/sub_test-orphan-xyz.yaml` (not in
       registry), tool returns 1 with that name in the orphan list
- (c) remove the temp file, tool returns 0
- (d) `--json` output schema check (has `orphans` key, list of
       `{name, recipe_file}` dicts)

This is the regression test that the tool itself works. Pattern
from R110-195/R110-196 — every new tool gets a pytest.

## Acceptance

- [ ] `python3 tools/dev_check_orphan_recipes.py` exits 0 on
      current HEAD (1614/1614 pytest still passes)
- [ ] When a temp orphan is added, tool exits 1 with the orphan
      name in output
- [ ] Check 23 in pre-push-validator catches the same orphan and
      blocks push
- [ ] `python3 -m pytest tests/test_dev_check_orphan_recipes.py
      -v` shows 4 passed
- [ ] Full pytest: 1618+ passed (1614 existing + 4 new), 0 failed
- [ ] pre-push-validator: 23/23 checks passed
- [ ] Commit message: explains the DETECTION→CORRECTION→PREVENTION
      cycle this directive enacts

## Why this is a real cycle, not a doc-only fix

R110-195 (DETECTION) added the recipe, missed registration.
R110-203 (CORRECTION) fixed the registry manually.
R110-204 (PREVENTION) makes the manual fix structurally
unnecessary: any future recipe-add without a registry update
will be blocked by Check 23, with a clear error message
pointing to the missing entry. The cycle is closed.

## Out of scope

- Auto-update the registry (writing workflows.yaml from the tool) —
  too magical, mas-engineer's general-improver should design the
  right category placement, not a heuristic
- Generalizing to other registries (configs.mas-team.sub_agents,
  configs.<other-domain>.sub_agents) — follow-up directive
- Pre-commit hook wiring (`.githooks/pre-commit`) — separate
  R-numbered directive, this one is the validator-layer fix

## Cross-refs

- R110-31 (workflow registration rule, originally documented)
- R110-78 (spec-drift spec, R110-128 follow-up for hardcoded
  path prevention)
- R110-195 (sub_mas-design-patches added, missed registration)
- R110-198 (Check 21 for caller-chains, pattern twin of Check 23)
- R110-203 (manual fix of the orphan, this directive's WHY)
