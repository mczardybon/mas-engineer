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
   r'^(fix|feat|chore|docs|test|refactor|arch|perf|style|build|ci|revert)(\([^)]+\))?:'
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
ALLOWED_EMOJI_PREFIXES = ("🔧", "📝", "📚", "📊")

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
