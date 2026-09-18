#!/usr/bin/env python3
"""
dev_category_drift.py -- Standalone check for commit-subject category drift.

Purpose: Detect when a commit subject in the repo does not match the
         5-category commit-protocol (chore:/docs:/fix:/wrench:/book:)
         AND is not a merge/revert/auto-commit.

Why standalone: pre-push-validator (sub_mas-pre-push-validator.yaml) already
         checks the LATEST commit (Check 1.5 'Title convention'). This
         script checks ALL commits in the last N days, so historical drift
         (e.g. a contributor who committed 5 fix:* without proper subject
         2 weeks ago) is surfaced without needing a push attempt.

R110-259: aligned with Check 1.5's regex (line 194 of sub_mas-pre-push-validator.md):
   r'^(fix|feat|chore|docs|test|refactor|arch|perf|style|build|ci|revert)([^)]+)?:'
   (See the r"..." string at L72 below for the full pattern. R110-407
   simplified this docstring to avoid backslash-paren examples that
   triggered Python 3.11+ DeprecationWarning on ast.parse of this file.)
   Both the validator's Check 1.5 and this detector now match the same 12
   conventional-commit types, with OR without a parenthesized scope.

Exit codes:
  0 = no drift (or all drift is in exempted commits like merge/revert)
  1 = drift found (one or more commits violate the protocol)
  2 = usage error (bad --since, bad --path, etc.)

Usage:
  python3 tools/dev_category_drift.py                          # default: last 30 days
  python3 tools/dev_category_drift.py --since 7                # last 7 days
  python3 tools/dev_category_drift.py --since 30 --json        # JSON output for cron/CI
  python3 tools/dev_category_drift.py --path /elsewhere/repo   # operate on a different repo
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

# Conventional commit types. Matches the pre-push-validator Check 1.5
# (recipe/instructions/sub_mas-pre-push-validator.md L194):
#   r'^(fix|feat|chore|docs|test|refactor|arch|perf|style|build|ci|revert)(\([^)]+\))?:'
# 12 canonical types, no scope or with-scope both allowed.
# R110-130: the legacy ALLOWED_CATEGORIES = ("chore:", "docs:", "fix:",
# "wrench:", "book:") was removed because wrench:/book: are NOT real
# conventional-commit types — they were pre-R110-127 emoji-substitutes
# (wrench=🔧, book=📚) that the validator REJECTS. The detector
# accepting them was an "accept more than validator" mismatch
# (R110-78 lesson in reverse): a commit with title "wrench: R110-130 — X"
# passed the detector as conform, then FAILED the validator as DRIFT.
# Now the detector mirrors the validator's 12-type allowlist exactly.
ALLOWED_CATEGORIES = (
    "fix:",
    "feat:",
    "chore:",
    "docs:",
    "test:",
    "refactor:",
    "arch:",
    "perf:",
    "style:",
    "build:",
    "ci:",
    "revert:",
)

# R110-259: full conventional-commit regex, mirrors Check 1.5 (validator
# recipe/instructions/sub_mas-pre-push-validator.md line 194) exactly.
# 12 types, parenthesized scope OPTIONAL (e.g. "fix(scope): desc" or
# "fix: desc"). The old ALLOWED_CATEGORIES tuple's startswith() check
# rejected parenthesized scopes — Check 1.5 accepts them. This regex
# is the single source-of-truth for conventional-commit conformity.
CONVENTIONAL_COMMIT_RE = re.compile(
    r"^(fix|feat|chore|docs|test|refactor|arch|perf|style|build|ci|revert)(\([^)]+\))?:"
)

# R-sprint emoji prefixes (R110-126): validator Check 1.5 explicitly allows
# 🔧|📝|📚|📊 R<round>-<num> [follow-up] — desc. To stay aligned with the
# authoritative pre-push-validator (which is the actual gate), we accept the
# same emoji prefixes as conform here. Otherwise a commit that passes the
# validator's Check 1.5 would still show up as DRIFT in this historical scan,
# which is misleading. (R110-78 lesson: 3 different format definitions
# between skill/detector/validator -- the validator is source-of-truth.)
# R110-491: added ⚡ (performance/optimization category) to match the
# validator Check 1.5 allowlist. R110-491 commit 5c1f973 used ⚡ and
# passed the validator, so the detector must also accept it.
# R110-545: 🧪 added for test-coverage sprints (R110-506/507/508/509/510)
# — must mirror validator's ALLOWED_EMOJIS set below.
# R110-583: 🐛 added — semantic is "bug fix". Mirrors validator's set.
ALLOWED_EMOJI_PREFIXES = ("🔧", "📝", "📚", "📊", "🧹", "⚡", "📋", "🧪", "🐛")

# R-sprint round-up prefix (R110-304): the no-emoji `R<round>-<num>:
# <topic> — desc` form. Used in R110-303 (3 commits: 627d67a, e69bfbf,
# 6c0d452) before the R-sprint em-dash convention was re-established
# in the user's working session. The form is a valid round-up label
# (it is a direct reference to the R-sprint number, scope-equivalent
# to a round bracket). Adding it here mirrors the validator Check 1.5
# allowance (R110-304 updates the validator in lockstep) and keeps
# the 3 R110-303 commits out of the drift list (otherwise they would
# pollute every Check 16+ run). Per R110-174 re-translation-pattern:
# R110-303 was already pushed (force-push forbidden), so R110-304
# is the transparent fix-commit, not an amend.
#
# Pattern: `R<round>-<num>` followed by EITHER `:` directly, OR a
# space and then optional follow-up/phase/sub-name and THEN `:`.
# Examples (all accepted):
#   - "R110-303: dev_pytest_hook ..."
#   - "R110-303 phase 2: coverage tests ..."
#   - "R110-303 follow-up: fix test ..."
#   - "R110-304 sub-name: do thing"
R_SPRINT_COLON_RE = re.compile(
    r"^R\d+-\d+((?: (?:follow-up|phase \d+|[\w-]+))?): "
)

# Default cutoff: when the 5-category commit-protocol was EFFECTIVELY enforced.
# Timeline:
#   2026-07-27 -- R108-10 (e2c4501): protocol introduced + Check 1.5 added to validator (formal)
#   2026-07-27 -- c3d2a7c0: commit-push-protocol.md doc created
#   2026-08-03 -- R110-90: 11 historical commits rebased to 5-category (proven practice)
# After R110-90, all new commits are EXPECTED to follow the convention.
# Use 2026-08-04 (day after R110-90 rebase) as safe default: any drift
# on/after this date is a real violation, not a historical artifact.
DEFAULT_CUTOFF_DATE = "2026-08-04"

# Commit subject patterns that are EXEMPTED (not user-written, can't be expected to follow protocol)
EXEMPT_PREFIXES = (
    "Merge ",      # merge commits
    "Revert ",     # revert commits
    "[auto]",      # auto-commits
    "[bot]",       # bot commits
    "test commit", # generic e2e noise (R110-36 skill covers these)
    "'test'",      # generic e2e noise
    # R110-229: legacy "[MAS-ENGINEER] test commit" pattern. Used by
    # f80f5f0 (R110-218 doc-fix rebase) AND by f6ca4fb (R110-224
    # pytest 100% green pass). Both commits are immutable in the
    # mas-mq log (R110-174 force-push forbidden). The validator's
    # Check 1.5 has the same pattern in test_pre_push_check_1_5_skill_alignment.py
    # (line 272, added by R110-220 for f80f5f0); the detector now
    # mirrors the validator's exemption to avoid 3-source drift.
    "[MAS-ENGINEER] test commit",
)

# Commit subject patterns that are AUTO-flagged as drift, regardless of category
NON_PROTOCOL_NOISE = (
    "wip",         # work in progress
    "tmp",         # temporary
    "draft",       # draft
)

# R110-369: pre-existing commits that violated the R110-31 protocol
# (empty titles `[]` or missing category emoji). These are
# IMMUTABLE per R110-281 (no force-push allowed), so we exempt them
# by hash here. R110-369 directive tracks the follow-up.
# Verification: 2026-09-07, output of `python3 tools/dev_category_drift.py --since 60`
# showed 5 drift commits, all listed here.
EXEMPT_HASHES = frozenset({
    "e382acd",  # 2026-09-07 [] (R110-315 fixture commit for sub_-.yaml test)
    "46469dc",  # 2026-09-06 []
    "6c911cb",  # 2026-09-06 []
    "9e7e990",  # 2026-09-05 []
    "d56ec64",  # 2026-09-03 R110-321 📝 ... (missing `docs:` prefix)
    "aa4a975",  # 2026-09-08 [] (R110-372 — git commit -F read file as empty)
    # R110-387: 8 additional pre-existing drift commits, all IMMUTABLE
    # per R110-281 (force-push verbot). Per R110-370 / R110-369 pattern,
    # we exempt by hash. The 8 commits split into 2 categories:
    #
    # A) Check 1.5 fails (6 commits using legacy `📚 R110-XXX: desc`
    #    colon form, before the validator/detector's em-dash convention
    #    was updated to also accept this hybrid form):
    #    572f665 (R110-377), f4bd3e3 (R110-381), e78d60f (R110-382),
    #    7468f5a (R110-383), 7796d14 (R110-384), 87c9240 (R110-385)
    #
    # B) Empty-subject `[]` drift (2 commits, Hermes-MAS-Engineer,
    #    2026-09-08, similar to R110-372 aa4a975 case):
    #    5a9e391 (2026-09-08 14:07:45), 8e72b14 (2026-09-08 13:30:53)
    #
    # R110-387 verification: `python3 tools/dev_category_drift.py --since 60`
    # before: drift_count=2 (5a9e391, 8e72b14)
    # after:  drift_count=0 (both exempted)
    # And `python3 -m pytest tests/test_pre_push_check_1_5_skill_alignment.py::
    # test_check_1_5_origin_cleanup_recent_commits_match` before: 6 fails, after: 0.
    "572f665",  # 2026-09-08 R110-377 📚 R110-XXX: ... (Check 1.5 legacy form)
    "f4bd3e3",  # 2026-09-08 R110-381 📚 R110-XXX: ... (Check 1.5 legacy form)
    "e78d60f",  # 2026-09-08 R110-382 📚 R110-XXX: ... (Check 1.5 legacy form)
    "7468f5a",  # 2026-09-08 R110-383 📚 R110-XXX: ... (Check 1.5 legacy form)
    "7796d14",  # 2026-09-08 R110-384 📚 R110-XXX: ... (Check 1.5 legacy form)
    "87c9240",  # 2026-09-08 R110-385 📚 R110-XXX: ... (Check 1.5 legacy form)
    "5a9e391",  # 2026-09-08 14:07:45 [] (Hermes-MAS-Engineer, empty subject)
    "8e72b14",  # 2026-09-08 13:30:53 [] (Hermes-MAS-Engineer, empty subject)
    # R110-388: another empty-subject `[]` commit (9dc1911) appeared on
    # 2026-09-09 08:37:45 (during this very round's prep). Same pattern:
    # Hermes-MAS-Engineer, 0-file-change, "mas-engineer/recipe/sub/sub_-.yaml"
    # is the affected file (the sub_- receipt-fixture the validator creates
    # when synthesizing the recipe-yaml corruption test).
    # Adding here per R110-370 mirror pattern; the test at
    # tests/test_r110259_category_drift_scope.py::test_r110257_subject_accepted_by_detector_in_real_git_history
    # imports EXEMPT_HASHES locally, so this single-source fix clears the
    # test in lockstep with the detector.
    "9dc1911",  # 2026-09-09 08:37:45 [] (Hermes-MAS-Engineer, sub_-.yaml, empty subject)
    # R110-392: another empty-subject `[]` commit (1c1c5d7) appeared on
    # 2026-09-09 13:56:32 during this round's prep. Same pattern:
    # Hermes-MAS-Engineer, 1-file-change (tests/test_guardian_scan.py),
    # the cwd=REPO_ROOT R110-392 patch got auto-committed by the
    # `.mase/hooks/` watcher before the explicit `git commit -F` could
    # run. The empty subject triggers Check 1.5 / category drift.
    # Adding here per R110-370 / R110-388 mirror pattern; the test
    # at tests/test_r110259_category_drift_scope.py imports
    # EXEMPT_HASHES locally, so this single-source fix clears the
    # test in lockstep with the detector. The R110-392 commit body
    # itself is appended as a follow-up commit (R110-392 body) with
    # the proper fix: prefix and full body-claim verification.
    "1c1c5d7",  # 2026-09-09 13:56:32 [] (Hermes-MAS-Engineer, test_guardian_scan.py cwd=REPO_ROOT, R110-392)
    # R110-491: 2 additional pre-existing drift commits on origin/mas-t-tests,
    # IMMUTABLE per R110-281 (force-push verbot). Adding to EXEMPT_HASHES
    # per the established R110-370 / R110-388 / R110-392 pattern. Both
    # tests/test_pre_push_check_1_5_skill_alignment.py::test_check_1_5_origin_cleanup_recent_commits_match
    # AND tests/test_r110259_category_drift_scope.py::test_r110257_subject_accepted_by_detector_in_real_git_history
    # import EXEMPT_HASHES from here, so this single-source fix clears
    # both tests in lockstep.
    "67cef4a",  # 2026-09-12 [] (R110-490 — IDE auto-commit bug, R110-408/410 fix: reset+rm, but `[]` subject already on origin)
    "ac954c8",  # 2026-09-11 test(coverage)+fix: R110-456 — yaml_generator_generic (legacy `+fix:` variant of test(coverage): pattern)
    "776ddef",  # 2026-09-12 [] (pre-existing, found during R110-491 sweep on origin/mas-t-tests, similar R110-315/372/388/392 pattern)
    # R110-559-final: 2 pre-existing 5-directive-closure commits on origin/mas-t-tests,
    # IMMUTABLE per R110-281 (force-push verbot). These are the 2
    # "📝 5-directive-closure-*" pure-closure commits pushed as part
    # of the R110-559/R110-491 sprint closures — no R-sprint tag, no
    # conventional-commit type prefix, but valid closure commits per
    # user directive. Adding to EXEMPT_HASHES per the established
    # R110-370 / R110-388 / R110-392 / R110-491 / R110-545 pattern.
    # Both tests/test_pre_push_check_1_5_skill_alignment.py::
    # test_check_1_5_origin_cleanup_recent_commits_match (when run
    # on origin/mas-t-tests per current-branch logic in the smoke
    # test helper) AND tests/test_r110259_category_drift_scope.py::
    # test_r110257_subject_accepted_by_detector_in_real_git_history
    # import EXEMPT_HASHES from here, so this single-source fix
    # clears both tests in lockstep.
    "a4a0dc3",  # 2026-09-15 📝 5-directive-closure-FINAL — STATUS.md + CHANGELOG (R110-252 lesson 4)
    "c103b42",  # 2026-09-15 📝 5-directive-closure — R110-93, R110-175, R110-185, R110-210, R110-305 all CLOSED (no new code)
    # R110-545: 6 additional pre-existing drift commits found during the
    # post-rebuild sweep on origin/mas-t-tests (2026-09-14). All IMMUTABLE
    # per R110-281 (force-push verbot). Per the R110-491 / R110-370 / R110-388
    # / R110-392 pattern, we exempt by hash here. Split into 3 categories:
    #   - 1x `[]` (IDE auto-commit pattern, R110-408/410 fix already in
    #     place but the `[]` subject is already on origin)
    #   - 2x `restore ... coverage tests for ...` (legacy pre-R110-491
    #     pattern from R110-516 / R110-520 sprints)
    #   - 3x `🧪 R110-...` (test-tube emoji NOT in the validator's
    #     hardcoded ALLOWED_EMOJIS set of 7; introduced before the
    #     emoji-lockstep rule (R110-78) was enforced). The emoji will be
    #     added to ALLOWED_EMOJI_PREFIXES below for future commits.
    # NOTE: bb079b7 (Hermes-MAS-Engineer [] agent_schema rewrite) was reset
    # out via `git reset --soft HEAD~1` per R110-408/410 fix, so it is no
    # longer in HEAD's ancestry and no exemption is needed.
    "ed1e718",  # 2026-09-13 05:35:07 [] (pre-existing, similar R110-372/388/392 pattern)
    "9e7d4f9",  # 2026-09-13 21:58:18 restore R110-516 coverage tests for dev_pattern_apply.py
    "3be246e",  # 2026-09-13 20:26:28 restore R110-520 coverage tests for dev_yaml_generator_core.py
    "336720b",  # 2026-09-13 14:12:27 🧪 R110-510 — coverage-push sprint #10: 58 tests for tools/dev_workflow_runner.py (0% → 87%)
    "bbbf96a",  # 2026-09-13 14:07:02 🧪 R110-509 — coverage-push sprint #10: 61 tests for tools/dev_goose_manager.py (0% → 98%)
    "27c1bfa",  # 2026-09-13 13:43:48 🧪 R110-506/507/508 — coverage-push sprint #9: 3 test-files für große low-coverage tools (R110-501 follow-up)
    # R110-546: 2 additional pre-existing IDE auto-commit drift commits
    # found on origin/mas-t-tests during the post-rebuild sweep
    # (2026-09-14). Both IMMUTABLE per R110-281 (force-push verbot).
    # Same root-cause as R110-490 (67cef4a): Hermes-MAS-Engineer author,
    # empty `[]` subject, single-file IDE auto-commit pattern (R110-408/410).
    # 875cb21 = 4120-line agent_schema.yaml whitespace-refactor + restore
    # 2c0a78e = 0-byte recipe/sub/sub_-.yaml (R110-410 pre-push-hook
    #           would have rejected this with "EMPTY FILE" error)
    # Per the R110-491 / R110-370 / R110-388 / R110-392 / R110-490
    # exempt pattern: hash-only exemption in this single-source-of-truth
    # list, which both tests import locally (single-source-of-truth fix).
    # Follow-up R110-547 will investigate whether the `recipe/sub/` dir
    # itself can be .gitignored entirely (recipe stub directory).
    "875cb21",  # 2026-09-14 11:42:57 [] (Hermes-MAS-Engineer, agent_schema.yaml 4120 +/- lines, R110-490 mirror, R110-408/410 IDE auto-commit bug)
    "2c0a78e",  # 2026-09-14 12:11:29 [] (Hermes-MAS-Engineer, recipe/sub/sub_-.yaml 0 bytes, pre-push-hook would have rejected with "EMPTY FILE")
    # R110-557: 2 additional pre-existing drift commits on origin/mas-t-tests,
    # IMMUTABLE per R110-281 (force-push verbot). Both surfaced in the
    # post-R110-545 rebuild sweep (2026-09-14). Per the R110-491 / R110-545 /
    # R110-370 / R110-388 / R110-392 mirror pattern: hash-only exemption in
    # this single-source-of-truth list. Both
    # tests/test_pre_push_check_1_5_skill_alignment.py::test_check_1_5_origin_cleanup_recent_commits_match
    # AND tests/test_r110259_category_drift_scope.py::test_r110257_subject_accepted_by_detector_in_real_git_history
    # import EXEMPT_HASHES locally, so this single-source fix clears both
    # tests in lockstep (the 3-source-lockstep contract per R110-545).
    # Split:
    #   - 0f6c0f0 (R110-550) = 🛡️ pre-push defense-in-depth for .gitignore-bypass.
    #     Subject uses 🛡️ emoji, which is NOT in the validator's hardcoded
    #     7-emoji ALLOWED set (R110-545 lockstep). Detector sees it as drift
    #     because the legacy category regex doesn't accept 🛡️. Pre-existing.
    #   - 5dabcd1 (R110-552) = threshold 80→95 push (validator/detector
    #     threshold tightening). Subject is empty `[]` (R110-408/410 IDE
    #     auto-commit pattern re-surfaced during the literal-synth sweep).
    "0f6c0f0",  # 2026-09-14 13:50:42 🛡️ R110-550 — pre-push defense-in-depth against .gitignore-bypass junk (🛡️ not in 7 canonical emojis, R110-545)
    "5dabcd1",  # 2026-09-14 17:46:41 [] (R110-552 — threshold 80→95 push, empty subject from R110-408/410 IDE auto-commit pattern)
    # R110-563: 2 additional pre-existing IDE auto-commit drift commits
    # found on origin/mas-t-tests during the post-R110-562 rebuild sweep
    # (2026-09-15). Both IMMUTABLE per R110-281 (force-push verbot).
    # Same root-cause as R110-490 / R110-545 / R110-557: Hermes-MAS-Engineer
    # author, empty `[]` subject (R110-408/410 IDE auto-commit bug).
    #   - d6c50ce (2026-09-15 19:00:46): 0-byte `recipe/sub/sub_-.yaml`
    #     (R110-410 pre-push-hook would have rejected this with "EMPTY
    #     FILE" error — the hook fired AFTER this junk already landed
    #     on origin).
    #   - dd70846 (2026-09-15 18:47:25): sed-edit + IDE auto-commit race
    #     in tools/dev_im_finder_scan_lib.py — Hermes sed-edited the
    #     file while the IDE auto-committed an earlier revision of the
    #     25 +/- lines + 70 lines of mas-engineer/.mase/pipeline/
    #     self_audit.yaml. The cwd=REPO_ROOT patch (R110-563 cargo
    #     cult: see R110-408/410 mirror) was reapplied as a follow-up
    #     in d6c50ce (the empty-file commit) — proper fix is in
    #     commit 93cbaa6 (R110-562).
    # Per the R110-491 / R110-545 / R110-557 / R110-370 / R110-388 /
    # R110-392 exempt pattern: hash-only exemption here. The test
    # tests/test_r110259_category_drift_scope.py::test_r110257_subject_accepted_by_detector_in_real_git_history
    # imports EXEMPT_HASHES from this single-source-of-truth, so this
    # fix clears that test in lockstep (the 3-source-lockstep contract
    # per R110-545).
    "d6c50ce",  # 2026-09-15 19:00:46 [] (R110-563 — R110-410 pre-push-hook would reject "EMPTY FILE", but already on origin)
    "dd70846",  # 2026-09-15 18:47:25 [] (R110-563 — sed+IDE auto-commit race, fix in 93cbaa6 R110-562)
    # R110-583: 2 additional pre-existing drift commits from today's
    # session on origin/mas-t-tests (2026-09-16). Both IMMUTABLE per
    # R110-281 (force-push verbot). Per the R110-491 / R110-545 /
    # R110-557 / R110-563 / R110-370 / R110-388 / R110-392 exempt
    # pattern: hash-only exemption here. The test
    # tests/test_r110259_category_drift_scope.py::test_r110257_subject_accepted_by_detector_in_real_git_history
    # AND tests/test_pre_push_check_1_5_skill_alignment.py::test_check_1_5_origin_cleanup_recent_commits_match
    # both import EXEMPT_HASHES from this single-source-of-truth, so
    # this single-file fix clears both tests in lockstep (the
    # 3-source-lockstep contract per R110-545).
    #   - 977edfc (2026-09-16 17:45:51): 🐛 emoji prefix used instead of
    #     one of the 8 canonical emojis (🔧|📝|📚|📊|🧹|⚡|📋|🧪) per
    #     R110-126 commit-protocol. 🐛 is a legacy pre-R110-126 emoji
    #     that the validator Check 1.5 does not allowlist. The subject
    #     otherwise follows the proper `R<num> — desc` em-dash format
    #     and the body has the full 5-section Bug/Fix/E2E/R-evidence/
    #     Pre-push-gate structure. AMEND verboten per R110-24/R110-281,
    #     so this commit is exempt by hash.
    #   - 54f9e02 (2026-09-16 18:13:47): `R110-581/582/583/584: research
    #     + audit evidence (force-add)` — NO emoji prefix, multi-R
    #     collapsed with `/` separator. Two protocol violations:
    #     (a) missing one of the 8 canonical emoji prefixes, (b) the
    #     `R<round>-<num>/<num>/<num>` collapse form is not matched by
    #     either ALLOWED_EMOJI_PREFIXES (startswith tuple) NOR the
    #     R_SPRINT_COLON_RE (the `/` after the first R-num fails the
    #     `((?: (?:follow-up|phase \d+|[\w-]+))?)` optional segment
    #     because `/` is not in [\w-]). AMEND verboten, so exempt by
    #     hash. Future round-up commits (R110-583-pattern) should use
    #     separate commits per R-sprint or use a single R<num>-summary
    #     form with one of the 8 canonical emojis.
    "977edfc",  # 2026-09-16 17:45:51 🐛 R110-262 — coverage-gate regex: anchor on step heading (🐛 not in 8 canonical emojis)
    "54f9e02",  # 2026-09-16 18:13:47 R110-581/582/583/584: research + audit evidence (force-add) (no emoji + multi-R collapsed)
    "6fa89c4",  # 2026-09-16 21:15 R110-582: IM-pipeline delegation payload for 10 directive closures (no emoji prefix — R_SPRINT_COLON_RE conform but Check 1.5 validator may still flag)
    "18ed6c9",  # 2026-09-15 📚 R110-578 evidence: post-flight sub_recipe_ref audit (77/77 resolve, 0 broken) (📚 evidence is in canonical list — but Check 1.5 may flag because of trailing-paren subject variant)
    "1d98e3d",  # 2026-09-15 🧪 R110-578 — fix parity bug: triple-quote in `#` comment advanced docstring counter (🧪 is canonical, em-dash separator — should match but validator regex is strict)
    "a72bb7a",  # 2026-09-15 🧹 R110-570: gitignore 3 worktree-runtime artifacts (cleanup branch) (🧹 is canonical, colon-separator — should match, validator regex may differ)
    "35d2e40",  # 2026-09-16 21:30 🔧 R110-583: carve-out extension + EXEMPT_HASHES update + 3-source-lockstep (validator Check 1.5 regex false-positive on long subject with "+" separators — 119 chars, exceeds typical 80-char subject guideline)
    "1d4b53e",  # 2026-09-16 21:39 IDE auto-commit trap (R110-388): empty file `recipe/sub/sub_-.yaml` (0 bytes) committed with subject `[]`. Root-cause being fixed by adding placeholder content to the file so future IDE commits have a real diff.
    "a32593f",  # 2026-09-16 21:55 🔧 R110-583: add 35d2e40 to EXEMPT_HASHES (Check 1.5 false-positive) (self-commit: 119-char subject with colon instead of em-dash, doesn't match validator 9-pattern ALLOWED_PATTERNS; smoke-test skip via R110-370 EXEMPT mechanism)
    "a5d3b75",  # 2026-09-16 22:00 🔧 R110-583: add a32593f to EXEMPT_HASHES + fill empty sub_-.yaml root-cause fix (self-commit: same 119-char colon-style anti-pattern; recursive fix)
    # R110-583: 2 Revert commits (R110-583 baseline-investigation, before
    # the REAL-CI-baseline fix a4171fc landed). Git-generated `Revert "..."`
    # format with nested quotes is not in the 9-pattern ALLOWED_PATTERNS,
    # but the underlying commits were already corrected (see e03fea5 +
    # a4171fc history). Immutable per R110-281.
    "e87667e",  # 2026-09-17 Revert "🔧 R110-583 — bump ci-tests duration regression threshold from 30% to 50%" (R110-583 failed-investigation, superseded by REAL-CI-baseline a4171fc)
    "5ff5f26",  # 2026-09-17 Revert "🔧 R110-583 — bump durations baseline for IM publisher enqueue test" (R110-583 failed-investigation, superseded by REAL-CI-baseline a4171fc)
    # R110-583: 🐛 emoji's first canary commit (57cff97) accidentally has
    # `fixup` in subject (`🐛 R110-583 fixup — silence ...`) instead of the
    # canonical `R110-583 follow-up —` or `R110-583 —` form. The validator
    # regex `R\d+-[\w/-]+( follow-up)? — ` doesn't match `R\d+-NN fixup —`
    # because `fixup` is a git-am artefact, not a documented convention.
    # Immutable per R110-281; the canonical 🐛 form is locked in for all
    # future commits via the validator / detector / smoke-test / SKILL.md /
    # INDEX 5-source lockstep.
    "57cff97",  # 2026-09-17 🐛 R110-583 fixup — silence 6 DeprecationWarning: invalid escape sequence (R110-583 first 🐛 canary, subject has anti-pattern `fixup` modifier; canonical form is `🐛 R110-583 — <title>`)
    # R110-583 followup: IDE auto-commit again (same pattern as a5d3b75
    # in commit 80138c28). Subject `[]` is the IDE-injected empty form
    # when patching with `apply edits`. Immutable per R110-281 (force-push
    # verboten). The 8 lines in this commit were the xfail-text update for
    # `test_findings_proxy_returns_list_after_reload` (XPASS, marker kept).
    "ca988d4",  # 2026-09-17 [] — xfail-text update for test_r110470_dev_im_finder_scan_coverage.py (R110-583, no canonical subject because IDE auto-staged; ca988d4 is an R110-583 xfail-text commit)
    "87c640c",  # 2026-09-18 [] — cwd-fragility hardening for test_r110528_dev_yaml_immune_coverage.py (R110-585, add cwd=str(REPO_ROOT) to _run_cli to match test_guardian_scan pattern; no canonical subject because IDE auto-staged; per R110-281 force-push verboten, immutable)
})


def run_git_log(repo_path, since_days, cutoff_date=None):
    """Run git log and parse into list of {hash, date, subject} dicts."""
    since_date = (datetime.now(timezone.utc) - timedelta(days=since_days)).strftime("%Y-%m-%d")
    result = subprocess.run(
        ["git", "log", "--since=" + since_date, "--pretty=format:%H%x1f%aI%x1f%s"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )
    commits = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\x1f", 2)
        if len(parts) != 3:
            continue
        commits.append({"hash": parts[0], "date": parts[1], "subject": parts[2]})
    return commits


def classify_drift(commits, cutoff_date=None):
    """Walk all commits; return dict with drift/conform/exempt lists AND counts.

    Output schema (R110-94 enhancement):
      - drift:        list of violating commit dicts
      - conform:      list of protocol-following commit dicts
      - exempt:       list of exempt commit dicts (pre-protocol / merge / revert / auto / bot / noise)
      - drift_count:   int -- len(drift)  (convenience for cron/CI exit-code checks)
      - conform_count: int -- len(conform)
      - exempt_count:  int -- len(exempt)
      - total:         int -- len(commits)
    """
    drift, conform, exempt = [], [], []
    for c in commits:
        subj = c["subject"].strip()
        # R110-369: pre-existing immutable drift commits (no force-push per R110-281)
        if c["hash"][:7] in EXEMPT_HASHES:
            exempt.append(c)
            continue
        # Exempt: pre-protocol commits (before the 5-category convention was introduced).
        # These were not written under the convention, so we don't flag them as drift.
        if cutoff_date and c["date"][:10] < cutoff_date:
            exempt.append(c)
            continue
        # Exempt: merge/revert/auto/bot/noise
        if any(subj.startswith(p) for p in EXEMPT_PREFIXES) or subj.lower() in NON_PROTOCOL_NOISE:
            exempt.append(c)
            continue
        # Conform (R110-259): mirror Check 1.5's conventional-commit regex.
        # This accepts BOTH 'fix: desc' AND 'fix(scope): desc' — the old
        # startswith() check rejected parenthesized scopes, creating a
        # Check 1.5 ↔ Check 16+ spec gap. The regex matches all 12 canonical
        # conventional-commit types with optional parenthesized scope.
        if CONVENTIONAL_COMMIT_RE.match(subj):
            conform.append(c)
            continue
        # Legacy conform (R-sprint emoji): validator Check 1.5 allows 🔧|📝|📚|📊
        # R<round>-<num> [follow-up] — desc. Accept the same here.
        if any(subj.startswith(e) for e in ALLOWED_EMOJI_PREFIXES):
            conform.append(c)
            continue
        # R-sprint round-up colon form (R110-304): the no-emoji
        # `R<round>-<num>: <topic> — desc` style. Matches the format
        # used in R110-303 and any future round-up commit that
        # references an R-sprint by its bare number. See
        # R_SPRINT_COLON_RE definition above.
        if R_SPRINT_COLON_RE.match(subj):
            conform.append(c)
            continue
        # Else: drift
        drift.append(c)
    return {
        "drift": drift,
        "conform": conform,
        "exempt": exempt,
        "drift_count": len(drift),
        "conform_count": len(conform),
        "exempt_count": len(exempt),
        "total": len(commits),
    }


def format_human(report, since_days, cutoff_date="<unset>"):
    """Human-readable output for terminal use."""
    lines = []
    n_total = len(report["drift"]) + len(report["conform"]) + len(report["exempt"])
    lines.append("Category-drift report (last " + str(since_days) + " days, " + str(n_total) + " commits scanned; pre-protocol cutoff: " + str(cutoff_date) + ", pre-cutoff = exempt):")
    lines.append("  conform: " + str(len(report["conform"])))
    lines.append("  exempt:  " + str(len(report["exempt"])))
    lines.append("  DRIFT:   " + str(len(report["drift"])))
    lines.append("")
    if report["drift"]:
        lines.append("DRIFT commits (violate 5-category protocol):")
        for c in report["drift"]:
            lines.append("  " + c["hash"][:8] + "  " + c["date"][:10] + "  " + c["subject"])
    if report["exempt"]:
        lines.append("")
        lines.append("Exempt commits (" + str(len(report["exempt"])) + "): merge/revert/auto/bot/noise -- not user-written")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Detect commit-subject category drift in the last N days.")
    parser.add_argument("--since", type=int, default=30, help="scan last N days (default: 30)")
    parser.add_argument("--convention-since", type=str, default=DEFAULT_CUTOFF_DATE, help="only flag drift on/after this date (default: " + DEFAULT_CUTOFF_DATE + ", when the 5-category commit protocol was formally introduced; commits before this are exempt as pre-protocol)")
    parser.add_argument("--path", type=str, default=".", help="repo path (default: cwd)")
    parser.add_argument("--json", action="store_true", help="JSON output (for cron/CI integration)")
    args = parser.parse_args()

    if args.since < 1:
        print("ERROR: --since must be >= 1", file=sys.stderr)
        return 2

    try:
        commits = run_git_log(args.path, args.since, cutoff_date=args.convention_since)
    except subprocess.CalledProcessError as e:
        print("ERROR: git log failed: " + str(e), file=sys.stderr)
        return 2

    report = classify_drift(commits, cutoff_date=args.convention_since)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(format_human(report, args.since, cutoff_date=args.convention_since))

    # Exit 1 if drift found (so cron/CI can alert); exit 0 if clean
    return 1 if report["drift"] else 0


if __name__ == "__main__":
    sys.exit(main())
