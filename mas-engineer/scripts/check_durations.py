#!/usr/bin/env python3
"""
check_durations.py — test-duration regression detector.

Compares the slowest N tests from a current pytest run against a
checked-in baseline JSON. Exits 1 if any of the top-N tests
regresses by more than --threshold-pct (default 20%).

Why this exists (R110-238):
    pytest-benchmark with --benchmark-compare-fail is a good tool but
    it is overkill for "is the test suite still fast enough?". For a
    project of this size, capturing pytest --durations=N output and
    diffing it against a baseline file is enough, has no extra deps,
    and is easy to maintain.

Why not auto-update the baseline:
    Auto-updating the baseline hides regressions. A human must look
    at the diff and decide "yes, this slowdown is expected" before
    bumping the baseline. This is the same principle as not pinning
    a known-vulnerable dep version just because pip-audit flagged it.

Usage:
    pytest tests/ --durations=20 > pytest-output.log 2>&1
    python scripts/check_durations.py \\
        --current pytest-output.log \\
        --baseline tests/durations-baseline.json \\
        --top-n 20 \\
        --threshold-pct 20

Exit codes:
    0 = no regression detected (or current run is faster)
    1 = regression detected; one or more top-N tests slower than
        threshold-pct of baseline
    2 = usage error (bad args, missing file, malformed baseline)
"""

import argparse
import json
import re
import sys
from pathlib import Path


# pytest --durations=N output lines look like:
#   1.23s call     tests/test_foo.py::test_bar
#   0.45s setup    tests/test_foo.py::test_baz
# We only care about 'call' (the actual test body), not setup/teardown.
DURATION_RE = re.compile(
    r"^\s*(?P<seconds>[0-9]+\.[0-9]+)s\s+(?P<phase>call|setup|teardown)\s+"
    r"(?P<test_id>\S+)\s*$"
)


def parse_durations_log(path: Path, top_n: int) -> dict[str, float]:
    """Parse pytest --durations log and return top-N test_id -> seconds.

    Only 'call' phase is counted (the actual test body). When the same
    test_id appears multiple times (parametrize), we keep the maximum
    observed duration — that is the worst case the user will hit.
    """
    durations: dict[str, float] = {}
    with path.open() as f:
        for line in f:
            m = DURATION_RE.match(line)
            if not m:
                continue
            if m.group("phase") != "call":
                continue
            test_id = m.group("test_id")
            seconds = float(m.group("seconds"))
            # Keep the max (worst case) for parametrize.
            if test_id not in durations or seconds > durations[test_id]:
                durations[test_id] = seconds
    # Sort by duration descending, take top N.
    top = dict(sorted(durations.items(), key=lambda kv: kv[1], reverse=True)[:top_n])
    return top


def load_baseline(path: Path) -> dict[str, float]:
    if not path.exists():
        return {}
    with path.open() as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"baseline at {path} is not a dict")
    return {k: float(v) for k, v in data.items()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--current", required=True, type=Path, help="Path to pytest --durations log")
    ap.add_argument("--baseline", required=True, type=Path, help="Path to baseline JSON")
    ap.add_argument("--top-n", type=int, default=20, help="Number of slowest tests to compare (default 20)")
    ap.add_argument("--threshold-pct", type=float, default=20.0, help="Regression threshold percent (default 20)")
    ap.add_argument("--update-baseline", action="store_true", help="Overwrite the baseline with the current run (use with care)")
    args = ap.parse_args()

    if not args.current.exists():
        print(f"ERROR: current log not found: {args.current}", file=sys.stderr)
        return 2
    if not args.update_baseline and not args.baseline.exists():
        print(f"ERROR: baseline not found: {args.baseline} (use --update-baseline to create it)", file=sys.stderr)
        return 2

    current = parse_durations_log(args.current, args.top_n)
    baseline = {} if args.update_baseline else load_baseline(args.baseline)

    if args.update_baseline:
        # Creating / updating the baseline path. Sort for stable diffs.
        sorted_current = dict(sorted(current.items(), key=lambda kv: kv[1], reverse=True))
        args.baseline.parent.mkdir(parents=True, exist_ok=True)
        with args.baseline.open("w") as f:
            json.dump(sorted_current, f, indent=2, sort_keys=True)
        print(f"Baseline written: {args.baseline} ({len(sorted_current)} tests)")
        return 0

    if not current:
        print("ERROR: no durations parsed from current log. Was pytest run with --durations=N?", file=sys.stderr)
        return 2

    # Regression detection: for each test in current that's also in baseline,
    # compare. Tests in current but not in baseline are not regressions
    # (they are new tests; their first run establishes their own baseline).
    # Tests in baseline but not in current are ignored (they were removed
    # or renamed; not a regression).
    regressions: list[tuple[str, float, float, float]] = []
    for test_id, cur_seconds in current.items():
        if test_id not in baseline:
            continue
        base_seconds = baseline[test_id]
        if base_seconds <= 0:
            continue
        delta_pct = ((cur_seconds - base_seconds) / base_seconds) * 100.0
        if delta_pct > args.threshold_pct:
            regressions.append((test_id, base_seconds, cur_seconds, delta_pct))

    if not regressions:
        print(f"OK: {len(current)} tests compared, 0 regressions > {args.threshold_pct}%")
        # Also report a quick "faster than baseline" count for context.
        faster = sum(1 for tid, secs in current.items()
                     if tid in baseline and secs < baseline[tid])
        if faster:
            print(f"     ({faster} tests faster than baseline)")
        return 0

    print(f"REGRESSION: {len(regressions)} test(s) regressed by > {args.threshold_pct}%")
    print()
    print(f"{'test_id':<70} {'baseline':>10} {'current':>10} {'delta':>8}")
    print("-" * 100)
    for test_id, base_s, cur_s, delta in sorted(regressions, key=lambda r: -r[3]):
        # Truncate long test_ids to keep the table readable.
        tid_display = test_id if len(test_id) <= 70 else test_id[:67] + "..."
        print(f"{tid_display:<70} {base_s:>9.3f}s {cur_s:>9.3f}s {delta:>+7.1f}%")
    return 1


if __name__ == "__main__":
    sys.exit(main())
