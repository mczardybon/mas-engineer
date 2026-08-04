# R110-94 — Add Check 16+ (Historical Category Drift) to pre-push-validator

**Status:** DRAFT (2026-08-04)
**Author:** Hermes (R110-92 follow-up)
**Target:** `recipe/sub/sub_mas-pre-push-validator.yaml` + `recipe/instructions/sub_mas-pre-push-validator.md`

## Goal

Augment the existing pre-push-validator (currently 15 checks) with a new
**Check 16+** that invokes the standalone `tools/dev_category_drift.py`
script (R110-92) and **BLOCKS the push** if drift > 0.

## Why

- `Check 1.5` (existing) validates ONLY the **latest commit's subject** at
  push time. It cannot see historical drift.
- `tools/dev_category_drift.py` (R110-92) is the standalone detector
  that scans all commits in a date window and classifies them as
  conform/drift/exempt.
- After R110-90 rebase, all NEW commits follow the 5-category convention.
  But historical commits in the window can still be flagged, and a new
  contributor could push drift without Check 1.5 catching it.

## Scope

1. New Check 16+ in `sub_mas-pre-push-validator` (yaml + .md).
2. Drift detector script (`tools/dev_category_drift.py`) — already
   shipped in R110-92, ee0b242.
3. Test-fixture template in `.directives/test-fixtures/` (see file
   `test_check_16_drift.py.template`).

## 9-Section Spec

### 1. EXACT FILE + INSERT-POINT

- `mas-engineer/recipe/instructions/sub_mas-pre-push-validator.md`
  - INSERT after the existing Check 14 (end of checks), before
    "## Boundaries" section. (Find the `## Boundaries` heading and
    insert a new `### Check 16+` section immediately before it.)
- `mas-engineer/recipe/sub/sub_mas-pre-push-validator.yaml`
  - Bump version 2.1.0 → 2.2.0
  - Bump description: "15 critical checks" → "16 critical checks"
  - Bump prompt: "15 checks before git push" → "16 checks before git push"
  - Bump prompt: "if blocked, NO push allowed" reference to include
    Check 16+

### 2. EXTRACT-FUNCTIONS / REGEX / PATTERNS

The Check 16+ section is a bash code block (matching the pattern of
Check 1.5 in the same file). Shape:

```bash
cd $WORKSPACE
python3 tools/dev_category_drift.py --since 30 --json > /tmp/drift.json
DRIFT_COUNT=$(python3 -c "import json; d=json.load(open('/tmp/drift.json')); print(d['drift_count'])")
if [ "$DRIFT_COUNT" -gt 0 ]; then
    echo "❌ BLOCKED: Check 16+ — $DRIFT_COUNT historical commits violate the 5-category convention"
    echo "   Run: python3 tools/dev_category_drift.py --since 30"
    echo "   For details. To exempt historical pre-protocol commits:"
    echo "     --convention-since 2026-08-04   (default, post-R110-90 effective enforcement)"
    exit 1
fi
echo "✅ Check 16+ passed: no category drift in last 30 days"
```

### 3. MATCHING / SEARCH LOGIC

- Invocation: `python3 tools/dev_category_drift.py --since 30 --json`
- Exit code 0 = conform, 1 = drift, 2 = usage error.
- The Check 16+ block should:
  - Parse the JSON output
  - Extract `drift_count` field
  - If `drift_count > 0`: print each drift commit (sha + subject) for
    the validator's `blocked_reasons` field, then `exit 1`.

### 4. OUTPUT-SCHEMA / FINDING-SCHEMA

Drift detector JSON output (already shipped in R110-92):

```json
{
  "window_days": 30,
  "cutoff_date": "2026-08-04",
  "scanned": 482,
  "drift_count": 0,
  "conform_count": 3,
  "exempt_count": 479,
  "drift": [],
  "conform": [...],
  "exempt": [...]
}
```

Validator `blocked_reasons` entry on drift:

```yaml
- check: "16+"
  reason: "Check 16+ — 5 historical commits violate 5-category convention"
  drift_commits:
    - {sha: "abc1234", subject: "chore(release): v1.0", date: "2026-08-05"}
    - ...
  fix_command: "python3 tools/dev_category_drift.py --since 30"
  override: "python3 tools/dev_category_drift.py --convention-since <earlier-date>"
```

### 5. INTEGRATION HOOK-POINTS

- **im-finder**: Should detect "pre-push-validator has 15 checks, drift
  detector exists but not wired" as a P2 finding. Reference
  `tools/dev_category_drift.py` exists check: `test -f tools/dev_category_drift.py`.
- **pre-push-validator**: PRIMARY integration point. Check 16+ block.
- **pytest-hook**: No direct hook. The test-fixture template
  (`.directives/test-fixtures/test_check_16_drift.py.template`) covers
  the drift detector's logic; the Check 16+ block itself is tested
  via the goose e2e (manual, not pytest-discoverable).

### 6. SEVERITY

- **P1 (BLOCKER)**: drift_count > 0 in the configured window. Same
  severity as Check 1.5 (subject mismatch).
- **MEDIUM (WARN, not block)**: if `drift_count > 0` but all drift
  commits are pre-`--convention-since` (i.e. the user's cutoff is
  earlier than the drift detector's internal cutoff, suggesting
  intentional historical view). Print warning, do not block.
- **P3 (optional)**: drift_count > 0 but window > 30 days. Allow
  `--since 90` to be configured (default 30).

### 7. IDEMPOTENZ

- The Check 16+ block can be detected as "already implemented" by:
  ```bash
  grep -q "Check 16+" recipe/instructions/sub_mas-pre-push-validator.md
  ```
- The drift detector can be detected as "already shipped" by:
  ```bash
  test -f mas-engineer/tools/dev_category_drift.py
  ```
- The yaml version bump (2.1.0 → 2.2.0) is the canonical "applied"
  signal.

### 8. TESTING

**Unit (pytest, via test-fixture template):**

`.directives/test-fixtures/test_check_16_drift.py.template` — copy
to `tests/test_check_16_drift.py` and unskip when implementing.

Tests:
1. `test_dev_category_drift_clean_repo` — on a repo with 0 drift in
   last 30 days, exit 0, JSON has `drift_count=0`.
2. `test_dev_category_drift_drift_repo` — on a repo with synthetic
   `chore(release)` and `book` (no colon) subjects, exit 1, JSON has
   `drift_count > 0` and lists each.
3. `test_dev_category_drift_exempt_merge` — `Merge ...` and `Revert ...`
   subjects do not count as drift.
4. `test_dev_category_drift_cutoff` — `--convention-since YYYY-MM-DD`
   correctly exempts pre-cutoff commits.
5. `test_check_16_block_when_drift` — run the embedded bash block
   directly (extract from instructions file) and assert exit 1 when
   drift > 0.

**Integration (goose e2e, manual):**

1. Run `python3 tools/dev_category_drift.py --since 30` on the
   `mas-engineer` repo. Expect exit 0 (clean per R110-92 validation).
2. Temporarily add a `chore(release): v1.0` commit, run validator,
   expect BLOCK with "Check 16+ — 1 historical commit violates 5-cat".
3. Revert the synthetic commit, re-run validator, expect PASS.

**Regression:**

- 129/129 e2e tests must still pass after the patch.
- Pre-push-validator checks 0-15 must still all pass (regression).

### 9. DO-NOT (anti-patterns, footguns, anti-scope-creep)

- **DO NOT** delete or weaken Check 1.5. Check 16+ is ADDITIVE, not
  replacement. Check 1.5 catches the LATEST commit; Check 16+ catches
  the WINDOW.
- **DO NOT** add a new check for each historical convention (5-cat,
  emoji, semver, etc.). One check, one tool (`dev_category_drift.py`),
  one protocol. Extension is the tool's job, not the validator's.
- **DO NOT** add the drift detector invocation to the im-finder or
  im-designer — they are read-only/improver agents, not push-gate.
  The validator is the correct home.
- **DO NOT** bump the check count in the recipe's prompt to "17" if
  Check 16+ is the only addition — it's "16" (15 + 1, the + is a
  version-bump marker, not a count).
- **DO NOT** include the `dev_category_drift.py` script's full source
  in the Check 16+ block. INVOKE the script, do not inline. If the
  script changes, the block stays valid.
- **DO NOT** add `--convention-since` to the Check 16+ block as a
  configurable arg. The default (2026-08-04) is correct. Power users
  can override via the script directly, not via the validator.

## Provenance

- Standalone detector shipped in R110-92 (ee0b242, +241/-0).
- This directive is the IM-pipeline-ready spec for the next
  implementation pass.
- Reference commits: R110-90 (rebase precedent), R110-89 (validator
  evidence), R110-78 (spec-drift lesson — counts must be verified).

## Acceptance criteria

- [ ] `recipe/sub/sub_mas-pre-push-validator.yaml` version bumped to 2.2.0
- [ ] `recipe/instructions/sub_mas-pre-push-validator.md` has `### Check 16+` section
- [ ] `tools/dev_category_drift.py --since 30` exits 0 on the mas-engineer repo
- [ ] Synthetic drift commit → validator BLOCKS with "Check 16+"
- [ ] 129/129 e2e tests still pass
- [ ] Commit body cites numstat + drift detector script path + Check 1.5 additive note
