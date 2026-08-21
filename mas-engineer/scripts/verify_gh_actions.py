#!/usr/bin/env python3
"""
verify_gh_actions.py — Post-push validator for GitHub Actions setup.

Probes the GitHub API to confirm that:
  1. The repo's .github/workflows/ is registered (workflows endpoint
     returns at least one entry — i.e. GitHub recognized the file
     on the pushed commit)
  2. The most recent push triggered at least one workflow run
     (runs endpoint returns a non-empty list filtered by event=push)
  3. Each expected workflow has a run that completed (success or
     failure — not "in progress" forever, not "queued" forever)

This is the post-push counterpart to e2e-test.sh: e2e validates
local yaml syntax + script logic, this validates the actual
GitHub-side workflow registration + execution.

Background (R110-240):
    R110-234 created ci-tests.yml + ci-e2e-smoke.yml under
    mas-engineer/.github/workflows/. GitHub Actions only scans
    .github/workflows/ at the REPO ROOT — it does not look inside
    subdirectories. So those workflow files were pushed but never
    registered, and no CI ever ran. The bug went unnoticed because
    e2e-test.sh only does yaml.safe_load (which is content-only)
    and never checks the path is where GitHub looks for it.

    R110-240 fixes the path AND adds this verifier as a permanent
    post-push step in the pre-push-gate protocol.

Usage:
    export GH_PAT=ghp_...
    export GITHUB_REPO=mczardybon/mas-engineer  # owner/repo
    python3 scripts/verify_gh_actions.py \\
        --ref mas-t \\
        --expected ci-tests.yml,ci-e2e-smoke.yml,ci-quality.yml \\
        --wait-secs 180

Exit codes:
    0 = all checks PASS (workflows registered, runs triggered, runs
        completed within wait window)
    1 = one or more checks FAIL (workflows missing, no runs, runs
        stuck queued/in-progress, or expected workflow not found)
    2 = usage error (bad args, missing env, API auth error)

Notes:
    - We poll the runs endpoint every 10s up to --wait-secs. GitHub
      takes 5-30s to register a push and queue a workflow.
    - We accept "success" AND "failure" as "completed" — what we
      care about is that the run finished (so we can see the result),
      not that it passed. A failing run is actionable; a queued
      run after 3min is a bug.
    - The verifier requires GH_PAT with `repo` scope (public repo,
      fine for the mczardybon/mas-engineer PAT).
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request


def api_get(path: str, token: str) -> dict:
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"GH API {e.code} {path}: {body[:200]}")


def check_workflows_registered(token: str, repo: str) -> tuple[bool, list[str]]:
    """Confirm GitHub sees >= 1 workflow registered on the repo.

    Returns (ok, names). The endpoint is /actions/workflows (not
    /actions/runs). If this is empty, GitHub never registered any
    workflow file — the classic "wrong path" symptom.
    """
    data = api_get(f"/repos/{repo}/actions/workflows?per_page=100", token)
    names = [w["name"] for w in data.get("workflows", [])]
    return (len(names) > 0, names)


def check_runs_triggered(token: str, repo: str, ref: str, expected: list[str], wait_secs: int) -> tuple[bool, str]:
    """Wait for runs to appear on the ref. Returns (ok, status_string)."""
    deadline = time.time() + wait_secs
    last_total = 0
    while time.time() < deadline:
        # Filter by event=push to ignore workflow_dispatch triggers etc.
        # We look at the last 5 runs on this ref.
        data = api_get(f"/repos/{repo}/actions/runs?branch={urllib.parse.quote(ref)}&event=push&per_page=10", token)
        runs = data.get("workflow_runs", [])
        if runs:
            # we have at least one run on this ref. check if expected workflows ran
            triggered = {r["name"]: r for r in runs}
            missing = [name for name in expected if name not in triggered]
            if not missing:
                # All expected ran. Check completion status.
                statuses = [(name, r["status"], r["conclusion"]) for name, r in triggered.items()]
                completed = [(n, s, c) for n, s, c in statuses if s == "completed"]
                if len(completed) == len(expected):
                    # all done
                    summary = ", ".join(f"{n}={c}" for n, _, c in completed)
                    ok = all(c == "success" for _, _, c in completed)
                    return (ok, f"all-completed: {summary}")
                else:
                    inprog = [(n, s) for n, s, _ in statuses if s != "completed"]
                    last_total = len(runs)
                    time.sleep(10)
                    continue
            else:
                last_total = len(runs)
                time.sleep(10)
                continue
        time.sleep(10)
    return (False, f"timeout after {wait_secs}s: {last_total} runs seen, not all expected workflows completed")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ref", default="mas-t", help="Git ref (branch) to check (default mas-t)")
    ap.add_argument("--expected", default="", help="Comma-separated list of expected workflow file basenames (e.g. 'ci-tests.yml,ci-e2e-smoke.yml,ci-quality.yml')")
    ap.add_argument("--wait-secs", type=int, default=180, help="Max seconds to wait for runs to complete (default 180)")
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPO", ""), help="owner/repo (default $GITHUB_REPO)")
    args = ap.parse_args()

    token = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN") or ""
    repo = args.repo or os.environ.get("GITHUB_REPO") or ""
    if not token:
        print("ERROR: GH_PAT (or GITHUB_TOKEN) env var is required", file=sys.stderr)
        return 2
    if not repo:
        print("ERROR: --repo or $GITHUB_REPO is required", file=sys.stderr)
        return 2

    expected = [n.strip() for n in args.expected.split(",") if n.strip()]
    if not expected:
        print("ERROR: --expected is required (comma-separated workflow file basenames)", file=sys.stderr)
        return 2

    print(f"Repo: {repo}")
    print(f"Ref:  {args.ref}")
    print(f"Expected workflows: {expected}")
    print(f"Wait budget: {args.wait_secs}s")
    print()

    # Step 1: workflows registered?
    print("[1/3] Checking workflows registered on GitHub...")
    ok, names = check_workflows_registered(token, repo)
    if not ok:
        print(f"  FAIL: 0 workflows registered. GitHub sees nothing in {repo}.")
        print(f"        This means .github/workflows/ is missing, at the wrong path,")
        print(f"        or the yml files are syntactically invalid.")
        return 1
    print(f"  OK: {len(names)} workflows registered: {names}")

    # Cross-check: are our expected workflows in the list?
    expected_basenames = [os.path.basename(n) for n in expected]
    missing = [b for b in expected if b not in names and os.path.basename(b) not in names]
    if missing:
        # Try matching by file path instead of name (GH uses filename as default name)
        print(f"  WARN: expected workflows not found by name: {missing}")
        print(f"        Registered: {names}")

    # Step 2: runs triggered?
    print(f"[2/3] Waiting for runs on ref '{args.ref}' (event=push)...")
    ok, status = check_runs_triggered(token, repo, args.ref, expected, args.wait_secs)
    if not ok:
        print(f"  FAIL: {status}")
        return 1
    print(f"  OK: {status}")

    # Step 3: overall summary
    print()
    print("[3/3] Summary:")
    print(f"  Workflows registered: {len(names)}")
    print(f"  Runs on {args.ref}:   {status}")
    print()
    print("ALL CHECKS PASS. CI is alive.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
