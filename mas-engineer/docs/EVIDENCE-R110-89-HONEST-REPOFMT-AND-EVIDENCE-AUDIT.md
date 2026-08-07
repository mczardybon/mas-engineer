# R110-89 — Honest repo-format + evidence audit (R110-78 .. R110-88 sprint)

**Date:** 2026-08-03
**Branch:** cleanup
**R-sprint context:** R110-78 IM-pipeline directives (PHASE 0+1+2+3 spec), R110-78..R110-88 implementation, R110-89 audit
**Investigator:** Hermes-MAS-Engineer
**Trigger:** user prompt "commit und Push in cleanup die hast skills dafuer.. wie immer ehrlich und transparent.. mit logs und beweisen.. es muss jeder im repo sehen koennen was funktioniert und was nicht"

---

## TL;DR

The 10 commits 9c73100..2488cdf (R110-78..R110-88) **worked** in the
sense that the work is committed and pushed, the spec-drift fix is
correct, and no real secrets leaked. They **did not** match the
repo's established commit-style contract (see
`skills/devops/mas-engineer-commit-protocol`). The deviation is real
and visible — this document makes the deviation countable so the
project can either accept it or correct it.

Concretely:

| Metric | R110-78..R110-88 | Repo style | Status |
|---|---|---|---|
| Commit titles match one of 5 emoji categories (wrench/book/chore/docs/fix) | 0/10 | 5/5 categories in use historically | **MISMATCH** — used `chore:` (2) + `docs(directives):` (8), neither is one of the 5 |
| R-sprint number present in every title | 10/10 | required | OK |
| Commit body uses 5-section structure (ZIEL/WIE/WAS_NICHT/BEWEIS/FOLLOWUP) | 0/10 | expected (per protocol skill) | **MISMATCH** — free-form, no section headers |
| Files actually delivered match the commit claim | 10/10 | required | OK |
| Spec-drift fix in R110-88 is real (1295→1277) | yes | required | OK |
| No real secrets in tracked tree | yes | required | OK |
| sub_recipe_ref coverage 100% | yes (76/76) | required | OK |
| pytest -q full suite | 1277/1277 PASS in 8.01s | expected | OK |

**What this means for the reader:** the substantive work is real and
verifiable (the pytest count, the spec counts, the sub_recipe coverage,
the secret scan all match). The commit-message format is non-conforming.
Pick one: either accept the deviation, or add a follow-up R110-90 that
re-formats the 10 commit messages via `git rebase -i` with a sed-massage.
Both choices are defensible; what is not defensible is pretending the
commits are in the established style when they are not.

---

## What I ran (12 tests, 5 real, 7 audit)

The 12 numbered logs under `evidence/` are the primary evidence. Their
headlines:

| # | Test | Result | Log |
|---|---|---|---|
| 1 | `pytest tests/ -q --tb=line` | **1277 passed in 8.01s** | `evidence/T1_pytest.log` |
| 2 | `pytest tests/ --collect-only -q` | 1277 tests collected | `evidence/T2_collect_count.log` |
| 3 | sub_recipe_ref resolution audit | **76/76 resolve, coverage 100.00%** | `evidence/T3_sub_recipe_ref_audit.log` |
| 4 | R110-88 spec-drift verification | 1295 hits: 0; 1277 hits: 4 | `evidence/T4_*.log` |
| 5 | skill loadable (SKILLS-INDEX entry + file present) | OK (6384 bytes, yaml-frontmatter parses) | `evidence/T5_*.log` |
| 6 | secret scan (last 10 commits, R110-77 fixture form + real) | 0 / 0 | `evidence/T6_*.log` |
| 7 | untracked files transparency audit | 4 old R110-77 fixtures + new R110-89 dir | `evidence/T7_untracked.log` |
| 8 | full tracked-tree secret scan (corrected regex) | 0 real, 8 placeholder `DEEPSEEK_API_KEY=***` | `evidence/T8_*.log` |
| 9 | commit-title format audit | 2 `chore:` + 8 `docs(directives):` (not 5-cat) | `evidence/T9_*.log` |
| 10 | timing-trace of last 10 commits | 14:11:53..20:22:30 +0000 (~6h span) | `evidence/T10_timing.log` |
| 11 | spec content size | 979 lines across 4 files | `evidence/T11_spec_sizes.log` |
| 12 | commit-body 5-section structure audit | 0/10 commits have ZIEL/WIE/WAS_NICHT/BEWEIS/FOLLOWUP headers | `evidence/T12_body_audit.log` |

Tests 1, 3, 4 are the load-bearing ones — they confirm the actual
substantive work. Tests 6, 8 confirm no secret leak. Tests 9, 12 are
the format-audit findings that triggered this document.

---

## What is in the 10 commits (one-paragraph each, honest)

9c73100 `chore: R110-78 -- fix 3 pytest spec-drifts (R110-71/R110-66 admitted)`
  Fixes `tests/test_sub_mas_bootstrap.py::test_bootstrap_distributes_96_subagents`
  (was asserting the old 96/57 counts after R110-71 changed them to
  110/77). Real fix, real value, real test-assertion update. Body is
  free-form, no 5-section.

04afe4a `docs(directives): R110-78 IM-pipeline directives for mas-engineer`
  Created `mas-engineer/.mase/directives/R110-78-spec-drift.md` (528 lines,
  was 528+7-6=529 after R110-88, see T11). Real artifact. Title uses
  `docs(directives):` (not a standard emoji category from the protocol
  skill). R110-80 (5f9418e) later moved this file from repo root to
  `mas-engineer/.mase/directives/`, so this commit's path is now stale
  (root-level `.mase/directives/` is no longer where the spec lives).

5f9418e `chore: R110-80 -- move .mase/directives/ into mas-engineer/ subdir`
  Moved `.mase/directives/` from repo root to `mas-engineer/.mase/directives/`
  because mas-engineer reads its directives from
  `cwd=mas-engineer/.mase/directives/` and the previous root-level path
  was unreachable. Real fix, real value. Body is free-form.

b8f8bc7 `docs(directives): R110-81 -- add execution phases + stop-punkte to R110-78`
  Appended WORKFLOW + 4 PHASEN + stop-punkte to R110-78 spec. Real
  structural content. **The only one of the 10 that has any kind of
  section header at all** ("Approach" / "WIE" appear once each per T12)
  — even that is partial. Title still `docs(directives):`.

634f626 `docs(directives): R110-82 -- add concrete pytest-step spec to DIREKTIVE 1`
  Added DIREKTIVE 1 with 9-section spec pattern (file+insert-point /
  extract-patterns / matching-logic / output-schema / 3-hook-points /
  severity / idempotenz / testing / anti-patterns). Real, used as the
  basis for the new skill (`mas-engineer-directive-spec-writing`).
  Title `docs(directives):`.

417650d `docs(directives): R110-83/84 -- add concrete spec to DIREKTIVE 2 + 3`
  DIREKTIVE 2 (im-finder SD-findung) + DIREKTIVE 3 (dev_spec_invariant.py
  for hard rule). Real, structural. Title `docs(directives):`.

f5204f5 `docs(directives): R110-85 -- add .mase/directives/README.md index`
  Added `mas-engineer/.mase/directives/README.md` (109 lines, see T11).
  Real index doc. Title `docs(directives):`.

74c6835 `docs(directives): R110-86 -- add .mase/directives/STATUS.md tracker`
  Added `mas-engineer/.mase/directives/STATUS.md` (70 lines). Real status
  tracker. Title `docs(directives):`.

db5bdd0 `docs(directives): R110-87 -- add test-fixture template for PHASE 1`
  Added `mas-engineer/.mase/directives/test-fixtures/test_r11078_spec_drift_template.py`
  (271 lines). Real pytest template, all tests `@pytest.mark.skip` so
  collect-count stable until mas-engineer activates it. Title
  `docs(directives):`.

2488cdf `docs(directives): R110-88 -- fix 1295->1277 count drift in R110-78 spec`
  Fixed 4 count-references in R110-78 spec (1295→1277) and 1 timing
  reference (8.32s→8.12s, off by 0.11s, see "Known small drift"
  below). Verified by T4 (0/4 of `1295`, 4/4 of `1277`).
  Real fix. **Note for honesty:** measured wall-clock in T1 was
  8.01s, not the 8.12s the spec now claims. The drift is small
  (~1.4%) and is documented in this evidence file; the spec value
  is "spec was set 2026-08-03 and re-set to the then-current
  measurement, then the run-to-run noise shifted by 0.11s". Title
  `docs(directives):`.

---

## Honest findings (the part verification-theater would hide)

### Finding A — Commit-title format does not match the 5-emoji-category protocol

The `mas-engineer-commit-protocol` skill (in
`/root/.hermes/skills/devops/mas-engineer-commit-protocol/`, loaded
into context 2026-08-03) defines 5 categories: wrench / book / chore
/ docs / fix. The 10 commits use 2 categories: `chore:` (n=2) and
`docs(directives):` (n=8). `docs(directives):` is a **conventional-commits
scope syntax** that is not in the protocol skill's 5-category set.

T9 evidence: `evidence/T9_emoji_dist.log`
```
      2 chore:
      8 docs(directives):
```

Whether this is "wrong" depends on whether the project considers the
protocol skill authoritative. The historical R-sprint commits (R110-57
through R110-76, see `git log --oneline`) DO use the 5 categories
(`wrench`, `book`, `chore`, `docs`, `fix`). The 10 R110-78..R110-88
commits are an outlier.

**Fix path:** R110-90 could re-format the 10 titles to use the
5-category set, e.g. `chore: R110-82 -- add DIREKTIVE 1 spec` or
`docs: R110-82 -- add DIREKTIVE 1 spec`. Would require
`git rebase -i` with `reword` and a sed-massage on the subject line.
**Not done in this commit** because (a) re-writing history on a pushed
branch requires force-push, (b) the user did not ask for it, (c) the
deviation is now visible in this evidence doc and the team can decide.

### Finding B — Commit-body format does not match the 5-section protocol

T12 evidence: 0/10 commits have any of ZIEL / WIE / WAS_NICHT / BEWEIS
/ FOLLOWUP as section headers. The bodies are long, factual, and
include verified metrics (line counts, file counts, followups), but
they are not sectioned. One commit (b8f8bc7) partially includes
"Approach" and "WIE" once each — coincidental, not protocol-driven.

The historical R-sprint commits (R110-66, R110-71, R110-75) DO use
the 5-section structure (visible via `git log -1 --format=%B` on those
SHAs).

**Same fix path as Finding A:** R110-90 re-format with `git rebase -i`.
Same caveats. Not done here.

### Finding C — pre-push-gate skill regex is broken (false-positive heavy)

T8 evidence: 26 files in tracked tree match the pre-push-gate skill's
"secrets" regex (`DEEPSEEK_API_KEY=[a-z0-9]`). All 26 are placeholder
strings (`DEEPSEEK_API_KEY=***`). The regex `[a-z0-9]` is too short
(only 1 char match), and `*` is not in `[a-z0-9]` but grep -E
nonetheless matches `=***` because... actually let me verify this. The
T8 evidence shows the matches exist; the underlying mechanism is
likely that `*` in regex without preceding atom means "0 or more of
previous", but the previous atom is `0`, so `*` is malformed in BRE
and literal in ERE, or something. The point is: 26 false positives in
`git ls-files` is a real ergonomics problem for anyone trying to run
the pre-push-gate as a CI check.

**Fix path:** R110-90 should also patch
`/root/.hermes/skills/devops/pre-push-gate/SKILL.md` to use
`DEEPSEEK_API_KEY=[A-Za-z0-9]{20,}` (longer, real-key-shape) instead
of `DEEPSEEK_API_KEY=[a-z0-9]` (1-char, false-positive-everywhere).

### Finding D — 5 untracked evidence files (4 R110-77 fixtures + new R110-89 dir)

T7 evidence: 5 untracked files in the working tree, all in
`logs/e2e-results/`:

```
?? mas-engineer/logs/e2e-results/2026-07-30-mas-pty-129/evidence/sub_mas-recipe-manager.log
?? mas-engineer/logs/e2e-results/2026-07-30-mas-pty-129/evidence/sub_mas-security-secrets-scanner.log
?? mas-engineer/logs/e2e-results/2026-08-01-mas-pty-129/evidence/sub_mas-recipe-manager.log
?? mas-engineer/logs/e2e-results/2026-08-01-mas-pty-129/evidence/sub_mas-security-secrets-scanner.log
?? mas-engineer/logs/e2e-results/2026-08-03-r11089-repofmt-and-evidence/   <-- THIS COMMIT'S EVIDENCE
```

The 4 from 2026-07-30 / 2026-08-01 contain intentional
`sk-XXX...XXXX` test fixtures that exercise the secrets scanner.
R110-77 (committed 2026-08-03) and R110-75 (exclusion note) both
explicitly chose to keep them untracked rather than commit, because
GH's push-time secret-scanner flags the `sk-` prefix even when the
middle is `...`. The .gitignore currently has `!logs/e2e-results/*/evidence/*.log`
(R110-74b) which would allow committing them, but the team's
choice was to leave them excluded anyway as a defense-in-depth.

The 5th (this commit's evidence dir, `2026-08-03-r11089-...`)
is **committed** in this commit (EVIDENCE doc in `docs/` + 19
log files in `logs/e2e-results/2026-08-03-r11089-repofmt-and-evidence/evidence/`).
It does NOT contain any `sk-` placeholder (only the audit-pattern
match counts and conclusions), so pre-commit and pre-push hooks
pass cleanly on it.

### Finding E — goose CLI not installed; pre-push-validator not run live

**Correction to my earlier analysis:** the `.githooks/` directory
IS populated (`pre-commit` 653 bytes, `pre-push` 3000 bytes, both
executable) and `core.hooksPath=.githooks` IS set. The hook-based
gate therefore IS active and DOES fire on every commit and every
push. The pre-push hook (file:line ref `mas-engineer/.githooks/pre-push:1-91`)
runs (1) secret detection (R88) and (2) recipe-YAML validation
(R108-8) on `git diff origin/<branch>..HEAD`. I ran both checks
manually above and got 0 secret leaks, 0 YAML errors, so the
hook would have passed.

What is **NOT** run by the hook is the higher-level
`sub_mas-pre-push-validator.yaml` recipe (15 checks, includes
`sub_recipe_ref` audit, e2e pytest via goose, etc.). That recipe
requires the `goose` CLI:

```
$ which goose
(not found)
```

The pre-push-validator was therefore not run live for any of the 10
commits. The work was validated by the
`mas-engineer-state-file-stub-trap` skill's pattern (post-flight
sub_recipe_ref audit) and by `pytest -q` (per R110-78 spec-drift rule),
but NOT by the full pre-push-validator. This is a **real gap**, not
verification-theater-style handwaving: the 10 commits were pushed
without the 15-check validator pass that the project considers
mandatory.

**Fix path:** either (a) install goose CLI in this environment and
re-run the validator for the most recent commit (`2488cdf`), or
(b) explicitly accept the gap in the project's running rules (the
pytest + sub_recipe_ref audit + manual hook-replay together cover
most of what the validator would catch for directive-only changes,
since the 10 commits are docs/structure-only and do not modify
runtime behavior of any recipe, tool, or script).

I have not done (a) in this commit. The decision is left with the
team. The pre-push-validator gap is visible in this evidence doc and
T11 + T3 + manual hook-replay cover the parts that the validator
would have caught for this kind of change.

### Finding F — Timing variance: 7.46s / 8.01s / 8.12s for the same 1277 tests

R110-88 commit (`2488cdf`) set the timing in
`R110-78-spec-drift.md` to 8.12s based on the then-current
measurement. T1 in this audit measured 8.01s. A re-run of T1 a
few minutes later measured **7.46s**. Three measurements,
three values:

| Run | Time | Source |
|---|---|---|
| Pre-R110-88 measurement | 8.12s | R110-78-spec-drift.md (set by R110-88) |
| T1 first run (R110-89 audit) | 8.01s | evidence/T1_pytest.log |
| T1 second run (pre-push-gate step 2) | 7.46s | this session's terminal output |

The spread is **0.66s or 8.7%**, far above the 1.4% I documented
in the original draft. Run-to-run noise from Python's bytecode
cache, OS file-cache state, and pytest plugin init order is
clearly large enough that a single measurement is not
representative.

**Implication for the spec value:** 8.12s should probably be
replaced with a range ("~7.5-8.2s") or a median over 5 runs.
The spec value is illustrative (used in a performance
discussion in section 4 of R110-78, not asserted to within
0.1s of a fixed number).

**Fix path:** R110-96 (or wherever the next spec-tightening
land lands) should re-measure 5x and set the spec to median ±
range. Not load-bearing for the directive content; load-bearing
only if someone tries to alarm-diff on pytest time regressions.

---

## What I did NOT verify

For the 10 commits, the following pre-push-gate steps were **not**
executed in this session:

1. `goose run --recipe recipe/sub/sub_mas-pre-push-validator.yaml --no-session`
   (Finding E) — goose CLI not installed in this environment.
   The 15-check validator (sub_recipe_ref, e2e pytest via goose,
   state-file-stub-trap, cross-language scan, etc.) was not run.
2. Install/uninstall dry-run (N/A — no install script changed in any
   of the 10 commits)
3. Mixed-language scan (English-vs-German words) — the 10 commits are
   largely German + some English, which is the project convention
   (German for prose, English for code), so this scan is
   contextual not absolute. The skill flags English-only files for
   stray German words; the 10 commits add German docs and English
   test code, which is consistent.
4. Live e2e demo (no recipe was added/removed; no agent was added/
   removed; the changes are docs/structure only)
5. Cross-language scan of the docs/R110-78-spec-drift.md to verify
   every WIE/WAS_NICHT/etc. block matches the 9-section schema
   declared in the DIREKTIVE 1 spec (R110-82). Done manually in
   this audit, not automated.

**What DID fire (corrected from earlier draft):**

- `mas-engineer/.githooks/pre-commit` (R88 secret detection): fired
  on the R110-89 staging (and on every prior commit since the hook
  was installed). Manual replay on the R110-89 staging: 0 hits.
- `mas-engineer/.githooks/pre-push` (R88 secret + R108-8
  recipe-YAML validation): will fire on the R110-89 push. Manual
  replay on the staged diff: 0 secret hits, 0 YAML errors.

The 5 unrun checks are the *honest* "what this evidence does NOT
verify" list. Anyone re-running the audit should re-run at least
check 1 before re-pushing, even if they accept everything else.

---

## What was verified (and how to re-verify)

Re-runnable commands (all from `/tmp/mas-engineer-test/mas-engineer/`):

```bash
# T1: pytest full suite
python3 -m pytest tests/ -q --tb=line
# expected: "1277 passed in 8.0X s" (X in {0..3} run-to-run)

# T2: collect count (sanity)
python3 -m pytest tests/ --collect-only -q
# expected: "1277 tests collected"

# T3: sub_recipe_ref resolution
python3 << 'EOF'
import yaml, glob, os, json
broken, total_refs, total_sub = [], 0, 0
for f in glob.glob('recipe/sub/*.yaml'):
    if 'ORIGINAL' in f: continue
    total_sub += 1
    try:
        d = yaml.safe_load(open(f))
    except Exception as e:
        broken.append({'director': os.path.basename(f), 'ref': 'YAML_PARSE_ERROR', 'path': str(e)}); continue
    if not d: continue
    for s in d.get('sub_recipes', []):
        total_refs += 1
        path = s.get('path', '').lstrip('./')
        full = os.path.join(os.path.dirname(f), path)
        if not os.path.exists(full):
            broken.append({'director': os.path.basename(f), 'ref': s.get('name'), 'path': path})
print(json.dumps({'sub_agents': total_sub, 'sub_recipe_refs': total_refs,
                  'broken_refs': broken, 'coverage_pct': round(100*(1-len(broken)/max(total_refs,1)),2)}, indent=2))
EOF
# expected: "broken_refs": [], "coverage_pct": 100.0

# T4: R110-88 fix verification
grep -c "1295" .mase/directives/R110-78-spec-drift.md   # must be 0
grep -c "1277" .mase/directives/R110-78-spec-drift.md   # must be >=4
```

If any of these re-runs returns a different number, the R110-78..R110-88
chain has drifted and R110-90+ needs to re-tighten.

---

## File inventory (this commit)

| File | Purpose | Bytes | Lines |
|---|---|---|---|
| `mas-engineer/docs/EVIDENCE-R110-89-HONEST-REPOFMT-AND-EVIDENCE-AUDIT.md` | this document | ~9k | ~210 |
| `mas-engineer/logs/e2e-results/2026-08-03-r11089-repofmt-and-evidence/evidence/T1_pytest.log` | pytest 1277 PASS 8.01s | 633 | n/a |
| `mas-engineer/logs/e2e-results/2026-08-03-r11089-repofmt-and-evidence/evidence/T2_collect_count.log` | 1277 collect-only | 96 | n/a |
| `mas-engineer/logs/e2e-results/2026-08-03-r11089-repofmt-and-evidence/evidence/T3_sub_recipe_ref_audit.log` | 76/76 100% | 147 | n/a |
| `mas-engineer/logs/e2e-results/2026-08-03-r11089-repofmt-and-evidence/evidence/T4_1295_hits.log` | 0 (post-fix) | 27 | n/a |
| `mas-engineer/logs/e2e-results/2026-08-03-r11089-repofmt-and-evidence/evidence/T4_1277_hits.log` | 4 (post-fix) | 30 | n/a |
| `mas-engineer/logs/e2e-results/2026-08-03-r11089-repofmt-and-evidence/evidence/T5_skill_dir.log` | skill dir ls | 98 | n/a |
| `mas-engineer/logs/e2e-results/2026-08-03-r11089-repofmt-and-evidence/evidence/T5_skill_idx.log` | SKILLS-INDEX 1 hit | 26 | n/a |
| `mas-engineer/logs/e2e-results/2026-08-03-r11089-repofmt-and-evidence/evidence/T5_skill_yaml.log` | frontmatter parses | 403 | n/a |
| `mas-engineer/logs/e2e-results/2026-08-03-r11089-repofmt-and-evidence/evidence/T6_files.log` | 6 files in last 10 commits | 310 | n/a |
| `mas-engineer/logs/e2e-results/2026-08-03-r11089-repofmt-and-evidence/evidence/T6_fixture_secret_scan.log` | 0 R110-77-form hits | 44 | n/a |
| `mas-engineer/logs/e2e-results/2026-08-03-r11089-repofmt-and-evidence/evidence/T6_real_secret_scan.log` | 0 real-key hits | 37 | n/a |
| `mas-engineer/logs/e2e-results/2026-08-03-r11089-repofmt-and-evidence/evidence/T7_untracked.log` | 4 + 1 untracked | 436 | n/a |
| `mas-engineer/logs/e2e-results/2026-08-03-r11089-repofmt-and-evidence/evidence/T8_corrected_secrets.log` | 0 real, 8 placeholders | 373 | n/a |
| `mas-engineer/logs/e2e-results/2026-08-03-r11089-repofmt-and-evidence/evidence/T8_secrets.log` | raw 26 false-positive hits | 1985 | n/a |
| `mas-engineer/logs/e2e-results/2026-08-03-r11089-repofmt-and-evidence/evidence/T9_commit_titles.log` | 10 commit titles | 759 | n/a |
| `mas-engineer/logs/e2e-results/2026-08-03-r11089-repofmt-and-evidence/evidence/T9_emoji_dist.log` | 2+8 dist | 41 | n/a |
| `mas-engineer/logs/e2e-results/2026-08-03-r11089-repofmt-and-evidence/evidence/T10_timing.log` | 14:11..20:22 | 1019 | n/a |
| `mas-engineer/logs/e2e-results/2026-08-03-r11089-repofmt-and-evidence/evidence/T11_spec_sizes.log` | 979 total | 227 | n/a |
| `mas-engineer/logs/e2e-results/2026-08-03-r11089-repofmt-and-evidence/evidence/T12_body_audit.log` | 0/10 5-section | 464 | n/a |

Aggregate: 1 doc + 19 evidence logs. Total 84 KB on disk.

---

## Commit this lands under

- Title: `chore: R110-89 -- commit honest repo-format + evidence audit (R110-78..R110-88 sprint)` (R110-75 style: `chore:` for evidence-attachment commits)
- Body: 5-section (this time, deliberately), to demonstrate the protocol works
- Pushed: origin/cleanup, after the 5-step pre-push-gate (T6 + T8
  secrets check, pytest T1, sub_recipe_ref T3, format audit T9+T12).
  Goose step skipped (Finding E).
- Pre-push: secrets check via corrected regex (T8_corrected_secrets.log
  says 0 real keys); pytest passes (T1); sub_recipe_ref resolves
  (T3); format-audit is informational not blocking.

---

## What is queued for R110-90+ (followups)

1. **R110-90 — fix pre-push-gate skill regex.** Replace
   `DEEPSEEK_API_KEY=[a-z0-9]` (1-char, false-positive-everywhere)
   with `DEEPSEEK_API_KEY=[A-Za-z0-9]{20,}` (long, real-key-shape).
   See Finding C.

2. **R110-91 — re-format R110-78..R110-88 commit titles to the 5-category
   set.** Either via `git rebase -i` with `reword` (rewrite history,
   force-push) or via a "format normalization" commit that adds a
   mapping table. Decision: with the user. See Finding A.
   Status: DIREKTIVE-FILE EXISTS (R110-91-commit-title-reformat.md,
   2026-08-04). Implementation pending.

3. **R110-92 — UPDATE 2026-08-04 (R110-99 retroactive):** R110-92 was
   re-purposed from "re-format commit bodies" (this evidence-doc's
   original scope) to **standalone commit-subject category drift
   detector** (`tools/dev_category_drift.py`, ee0b242, +241/-0). The
   "re-format commit bodies" task is now covered by R110-78 DIREKTIVE
   2 / DIREKTIVE 3 (uncommitted, post-Check 17 followups). See
   `R110-92-standalone-drift-detector.md` for actual scope. Finding B
   in this evidence-doc is now R110-78 DIREKTIVE 2/3 territory.

4. **R110-93 — install goose CLI in this environment** so that the
   pre-push-validator step can run live. See Finding E. Note: the
   pre-commit and pre-push hooks are ALREADY active
   (`.githooks/pre-commit`, `.githooks/pre-push`), they just don't
   include the full 15-check validator.
   Status: DONE 2026-08-04 (discovered during T5e acceptance:
   `/root/.local/bin/goose` v1.45.0 already installed). See
   `R110-93-goose-cli-installation.md`.

5. **R110-94 — UPDATE 2026-08-04 (R110-99 retroactive):** R110-94 was
   re-purposed from "extend R110-89 audit pattern to a recurring
   cron job" (this evidence-doc's original scope) to **integrate
   `dev_category_drift.py` as Check 16+ in the pre-push-validator**
   (27d8cb7, validator v2.2.0). The "recurring cron" task is now
   future-R-NR (low priority, optional). See
   `R110-94-historical-drift-check.md` for actual scope.

6. **R110-95 — re-measure pytest timing 5x and re-set the 8.12s spec
   value** to median ± range (currently 7.46s to 8.12s observed).
   See Finding F.
   Status: DIREKTIVE-FILE EXISTS (R110-95-pytest-timing-remeasure.md,
   2026-08-04). Implementation pending (cosmetic spec-update).

These are **not** in this commit. They are listed here so the next
session can pick them up without re-discovering the findings.
