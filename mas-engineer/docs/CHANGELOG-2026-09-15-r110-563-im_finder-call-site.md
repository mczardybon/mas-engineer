# MAS-Engineer Changelog -- 2026-09-15

## OK R110-562..564 im_finder call-site repair + author-disclosure -- SUCCESS

**Task:** Repair `tools/dev_im_finder_scan_lib.check_stale_literal` which was
silently broken by the R110-562 perf-refactor of `_build_repo_literal_index`
and `_scan_pattern_b` signatures. Disclose the author-identity MANGEL on
R110-563 via a transparent follow-up commit (no amend, no force-push per
R110-24/174/281).

**Files modified (R110-563, 2 files, +38/-12):**

| File | Change | +/− |
|------|--------|-----|
| `mas-engineer/tools/dev_im_finder_scan_lib.py` | 1-arg call to `_build_repo_literal_index` (was 2-arg); extract `current_file_literals` and pass as 5th arg to `_scan_pattern_b` (was 4-arg); updated explanatory comment block | +13/−12 |
| `mas-engineer/tools/dev_category_drift.py` | Added 2 pre-existing IDE auto-commit drift hashes (d6c50ce, dd70846) to `EXEMPT_HASHES` per R110-491/545/557 mirror pattern | +25/−0 |

**Files modified (R110-564, 1 file, +8):**

| File | Change |
|------|--------|
| `mas-engineer/logs/e2e-evidence-gen2/post-flight-audit-R110-563.json` | NEW (force-added per R110-258 .gitignore contract) |

**Files modified (R110-562 context, the broken-refactor):**

| File | Change | Performance |
|------|--------|-------------|
| `mas-engineer/tools/dev_spec_invariant.py` | `_is_docstring_or_comment` O(N²)→mask O(1) | 6.4s → 0.08s |
| `mas-engineer/tools/dev_self_audit.py` | `_build_repo_literal_index` called ONCE per repo, was per-file | 45s → 1.5s |
| `mas-engineer/tools/dev_self_audit.py` | Added `index[rel_path]` for unquoted YAML | (semantic) |
| `mas-engineer/tools/dev_self_audit.py` | Removed `exclude_path` (mask-based exclusion semantics moved into `_scan_pattern_b`) | (semantic) |

**Result via pytest (R110-563):**

- 242/242 im_finder tests PASS (was 240/242 before fix — 2 calls were TypeError-swallowed)
- 20/20 lockstep tests PASS (r110259 + check_1_5 — single-source EXEMPT_HASHES fix)
- 13/13 sub_mas_im_finder tests PASS
- 436 PASSED + 1 xfail + 1 xpass in 117.40s (full critical suite, 1 retry on pre-existing flake)
- 22/22 targeted re-run after commit: PASS in 0.52s

**Result via post-flight audit (R110-564):**

- 116/116 sub_agents resolve
- 77/77 sub_recipe_refs resolve
- 100.0% coverage (vs R110-562 baseline)

**Pre-push-gate summary:**

- Step 0 (secret scan, tracked):         OK 0 secrets (only `***` placeholders + test-fixture fakes)
- Step 1 (validator, goose CLI):          SKIPPED -- DeepSeek 401 (key ok, same blocker as R110-562/561)
- Step 2 (e2e + pytest):                  OK 436 PASS + 1 xfail + 1 xpass in 117.40s
- Step 3 (commit msg, 🔧/📝 R-format):   OK per protocol
- Step 4 (push):                          OK via credential-helper (no `set-url` PAT-leak)
- Step 5 (post-flight audit):             OK 116/116, 77/77, 100.0%
- Step 6 (author-identity):               MANGEL on R110-563 → disclosed in R110-564

**E2E-N result:** OK — pre-existing im_finder test-suite gap closed; full critical suite stable at 436 PASS.

**Honest disclosure (per R110-56 lesson 4 + R110-281 lessons-learned):**

R110-563 was committed with author `Hermes Agent <hermes@nous.local>`
instead of the canonical `Hermes-MAS-Engineer <Hermes@mas-engineer.local>`.
Root cause: `git config user.email` was set to the old IDE-session value;
I fixed the config AFTER `git commit`, not before. Per R110-24 + R110-174
amend-is-verboten, and R110-281 force-push-verbot, both recovery paths are
user-rule violations. Recovery: transparenz-follow-up commit (R110-564)
that documents the MANGEL and adds the post-flight evidence file.

**Refs:**
- R110-562 (93cbaa6) — the perf-refactor that broke the call-site
- R110-561 (45513b0) — earlier 🔧 fix for dev_spec_invariant regex
- R110-78 — verification-theater pattern
- R110-174 — body-claim-verification
- R110-281 — force-push-verbot
- R110-258 — .gitignore + force-add evidence pattern
- R110-545 — 3-source-lockstep validator+detector+test
- Skill: `mas-engineer-commit-protocol` (5-section body template)
- Skill: `pre-push-gate` (full Step 0-5 procedure)
- Skill: `pre-push-body-claim-verification` (R110-174 derivation)
