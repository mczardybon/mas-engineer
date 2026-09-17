#!/usr/bin/env python3
"""R110-582 closure-delegation scanner.

Scans `.mase/directives/R*.md` and ranks candidates for closure-delegation
to the IM-pipeline. Closure evidence requirements:
  - Has commit SHAs in body
  - Has follow-up git-commits referencing the directive
  - No active-blocker language

USAGE: from repo root: python3 logs/r110582-closure-delegation/scan-directives.py

OUTPUT: ranked list of closure candidates to stdout.
"""
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DIRECTIVES = REPO / ".mase" / "directives"


def has_status(text):
    return bool(re.search(r"^## Status\s*\n", text, re.MULTILINE))


def score(text):
    s = 0
    sha_hits = re.findall(r"\b[0-9a-f]{7,8}\b", text)
    s += min(len(sha_hits) * 2, 10)
    s += 5 if "shipped" in text.lower() else 0
    s += 5 if "implemented" in text.lower() else 0
    s += 5 if "pushed to" in text.lower() else 0
    s += 3 if "merged" in text.lower() else 0
    s += 3 if "PR #" in text or "Pull Request" in text else 0
    s -= 5 if "TODO" in text or "TBD" in text else 0
    s -= 5 if "blocked" in text.lower() else 0
    return s


def followup_commits(n):
    """Run git log to find commits referencing R110-N."""
    out = subprocess.run(
        ["git", "log", "--all", "--oneline", "--grep=" + f"R110-{n}"],
        capture_output=True, text=True, cwd=str(REPO),
    )
    return [l for l in out.stdout.split("\n") if l]


def main():
    rows = []
    for f in sorted(DIRECTIVES.glob("R*.md")):
        text = f.read_text(encoding="utf-8")
        if has_status(text):
            continue
        m = re.search(r"R110-(\d+)", f.name)
        if not m:
            continue
        n = int(m.group(1))
        if 579 <= n <= 580:  # skip active-this-session
            continue
        s = score(text)
        follows = followup_commits(n)
        rows.append((n, f.name, s, len(follows), follows[:3]))

    # Rank by score + followup-count combined
    rows.sort(key=lambda r: -((r[2] or 0) + r[3]))

    print(f"{'R-N':<6} {'Directive':<55} {'score':<6} {'followups':<10} {'latest commits'}")
    print("-" * 100)
    for n, name, sc, fc, latest in rows:
        latest_msg = "; ".join(c.split(" ", 1)[1][:50] for c in latest) if latest else "(none)"
        print(f"R110-{n:<3} {name[:55]:<55} {sc:<6} {fc:<10} {latest_msg}")
    print(f"\nTotal: {len(rows)} (without ## Status section, excluding active R110-579+)")


if __name__ == "__main__":
    sys.exit(main())
