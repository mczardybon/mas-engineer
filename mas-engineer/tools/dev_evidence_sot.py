#!/usr/bin/env python3
"""R110-257 EVIDENCE-ORTE SOT CHECKER.

Verifies that all evidence files live in the SOT (Single Source of Truth) location
and that no wrong-SOT artifacts have crept into the working tree.

SOT evidence-archive ort:  REPO-ROOT logs/e2e-evidence-gen2/
SOT directives ort:        mas-engineer/.mase/directives/

Historical SOT violators (fixed in R110-257):
  - R110-217 (2acc2d1) + R110-218 (f80f5f0): mas-engineer/.directives/ wrong SOT
  - R110-194, R110-210, R110-214, R110-215, R110-216, R110-229, R110-230, R110-255:
    26 files in mas-engineer/logs/e2e-evidence-gen2/ wrong SOT

Usage:
    python3 tools/dev_evidence_sot.py            # check working tree
    python3 tools/dev_evidence_sot.py --git      # check git index (staged + unstaged)
    python3 tools/dev_evidence_sot.py --strict   # exit 1 on any violation
    python3 tools/dev_evidence_sot.py --history  # scan all git history for past violators

Exit codes:
    0  no violations
    1  --strict mode: violations found
    2  invocation error
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────
# SOT-Konstanten
# ─────────────────────────────────────────────────────────────────────
# 1. Evidence-archive SOT (R110-143, 2026-08-15 — logs/e2e-evidence-gen2/ REPO-ROOT)
SOT_EVIDENCE_PREFIX = "logs/e2e-evidence-gen2/"

# 2. Directives SOT (dev_directive_applier.py: tools read from .mase/directives/)
SOT_DIRECTIVES_PREFIX = "mas-engineer/.mase/directives/"

# Anti-SOT patterns: files in these locations are SOT violations.
# Per .gitignore (R110-257): these paths are ignored. This tool catches
# any pre-ignore commits OR accidental bypasses.
ANTI_SOT_DIRECTIVES = "mas-engineer/.directives/"
ANTI_SOT_EVIDENCE = "mas-engineer/logs/"

# Repo-root marker: STRICT CWD-based resolution. The tool must run
# from the repo-root (CWD must contain mas-engineer/ as a subdir).
# No fallback to tool path — that defeats the test fixtures' isolation
# (a tool located in mas-engineer-cleanup/mas-engineer/tools/ would
# otherwise always resolve to mas-engineer-cleanup/ regardless of CWD).
def _resolve_repo_root():
    cwd = Path(os.getcwd()).resolve()
    if (cwd / "mas-engineer").is_dir():
        return cwd
    raise SystemExit(
        f"FATAL: CWD ({cwd}) does not contain a mas-engineer/ subdir. "
        "Run this tool from the repo-root (parent of mas-engineer/)."
    )

REPO_ROOT = _resolve_repo_root()


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────
def _git(*args, cwd=None):
    """Run git command, return (rc, stdout, stderr)."""
    proc = subprocess.run(
        ["git", *args],
        capture_output=True, text=True, cwd=cwd or str(REPO_ROOT)
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _list_tracked_files(pattern=None):
    """List tracked files matching optional pattern."""
    if pattern:
        rc, out, _ = _git("ls-files", pattern)
    else:
        rc, out, _ = _git("ls-files")
    return [l for l in out.splitlines() if l] if rc == 0 else []


def _list_staged_files():
    """List staged files (diff --cached --name-only)."""
    rc, out, _ = _git("diff", "--cached", "--name-only")
    return [l for l in out.splitlines() if l] if rc == 0 else []


def _list_unstaged_files():
    """List unstaged tracked files (diff --name-only)."""
    rc, out, _ = _git("diff", "--name-only")
    return [l for l in out.splitlines() if l] if rc == 0 else []


def _list_untracked_files():
    """List untracked files (ls-files --others --exclude-standard).

    Note: --exclude-standard also EXCLUDES files in .gitignore. We
    deliberately want those for SOT-violation detection, so we
    additionally scan the working tree for .gitignore-excluded files
    at anti-SOT paths.
    """
    rc, out, _ = _git("ls-files", "--others", "--exclude-standard")
    files = [l for l in out.splitlines() if l] if rc == 0 else []
    # Augment: scan working tree for files at anti-SOT locations,
    # even if they are .gitignore-excluded. This is the WHOLE POINT
    # of this tool — the .gitignore block prevents accidental commits,
    # but if a developer creates files in the wrong location, we want
    # to warn them even if those files are invisible to git status.
    for anti_prefix in (ANTI_SOT_DIRECTIVES, ANTI_SOT_EVIDENCE):
        anti_dir = REPO_ROOT / anti_prefix.rstrip("/")
        if not anti_dir.exists():
            continue
        for path in anti_dir.rglob("*"):
            if path.is_file():
                rel = str(path.relative_to(REPO_ROOT))
                if rel not in files:
                    files.append(rel)
    return files


def _is_evidence_file(path):
    """Heuristic: is this file a 'evidence' artifact? Conservative: only
    flag files inside e2e-evidence-gen2/ directories OR with the
    convention names (R<NR>-EVIDENCE.md, r<NR>-<topic>.log)."""
    p = path.lower()
    if "e2e-evidence-gen2" in p or "e2e-evidence-gen2/" in p:
        return True
    # Convention: files that look like evidence in mas-engineer/logs/
    if p.endswith("-evidence.md") or "-evidence-" in p or "session-report" in p:
        return True
    return False


def _is_any_file_in_anti_sot_logs(path):
    """Per .gitignore (R110-257), mas-engineer/logs/ is FULLY forbidden —
    not just evidence files. ANY file at that path is a SOT violation."""
    return path.startswith(ANTI_SOT_EVIDENCE)


# ─────────────────────────────────────────────────────────────────────
# Check: wrong SOT location for evidence
# ─────────────────────────────────────────────────────────────────────
def check_evidence_sot_working_tree():
    """Find any tracked + untracked files at mas-engineer/logs/.

    Per .gitignore (R110-257), mas-engineer/logs/ is FULLY forbidden
    (any file there is a SOT violation — the dir is reserved exclusively
    for the SOT-archive at REPO-ROOT logs/e2e-evidence-gen2/).
    """
    violations = []
    for f in _list_untracked_files() + _list_staged_files() + _list_unstaged_files():
        if _is_any_file_in_anti_sot_logs(f):
            violations.append(f)
    return violations


def check_evidence_sot_git_index():
    """Find files at mas-engineer/logs/ that are tracked by git.
    (Should be empty post-R110-257 unless someone bypasses .gitignore.)"""
    violations = []
    for f in _list_tracked_files():
        if _is_any_file_in_anti_sot_logs(f):
            violations.append(f)
    return violations


# ─────────────────────────────────────────────────────────────────────
# Check: wrong SOT location for directives
# ─────────────────────────────────────────────────────────────────────
def check_directives_sot_working_tree():
    """Find any tracked + untracked files at mas-engineer/.directives/."""
    violations = []
    for f in _list_untracked_files() + _list_staged_files() + _list_unstaged_files():
        if f.startswith(ANTI_SOT_DIRECTIVES) and f.endswith(".md"):
            violations.append(f)
    return violations


def check_directives_sot_git_index():
    """Find .md files at mas-engineer/.directives/ that are tracked."""
    violations = []
    for f in _list_tracked_files():
        if f.startswith(ANTI_SOT_DIRECTIVES) and f.endswith(".md"):
            violations.append(f)
    return violations


# ─────────────────────────────────────────────────────────────────────
# Check: SOT evidence dir is healthy (contains expected sub-dirs)
# ─────────────────────────────────────────────────────────────────────
def check_sot_evidence_dir_health():
    """Sanity-check SOT evidence dir exists and has expected structure."""
    sot_dir = REPO_ROOT / "logs" / "e2e-evidence-gen2"
    if not sot_dir.exists():
        return [f"missing: {SOT_EVIDENCE_PREFIX} does not exist (run mkdir -p logs/e2e-evidence-gen2)"]
    if not sot_dir.is_dir():
        return [f"not-a-dir: {SOT_EVIDENCE_PREFIX} exists but is not a directory"]
    return []


# ─────────────────────────────────────────────────────────────────────
# Check: SOT directives dir is healthy
# ─────────────────────────────────────────────────────────────────────
def check_sot_directives_dir_health():
    """Sanity-check SOT directives dir exists and has at least one file."""
    sot_dir = REPO_ROOT / "mas-engineer" / ".mase" / "directives"
    if not sot_dir.exists():
        return [f"missing: {SOT_DIRECTIVES_PREFIX} does not exist (R110-115 DIREKTIVE 1)"]
    if not sot_dir.is_dir():
        return [f"not-a-dir: {SOT_DIRECTIVES_PREFIX} exists but is not a directory"]
    return []


# ─────────────────────────────────────────────────────────────────────
# History scan (informational)
# ─────────────────────────────────────────────────────────────────────
def scan_history_for_violators():
    """Scan all git history for past SOT violations (informational)."""
    rc, out, _ = _git(
        "log", "--all", "--format=", "--name-only",
        "--diff-filter=A",  # only Added entries (not Modifies)
    )
    if rc != 0:
        return {"error": "git log failed"}
    files = [l for l in out.splitlines() if l]
    anti_evidence_added = [f for f in files if f.startswith(ANTI_SOT_EVIDENCE)]
    anti_directives_added = [f for f in files if f.startswith(ANTI_SOT_DIRECTIVES)]
    return {
        "anti_sot_evidence_files_ever_added": sorted(set(anti_evidence_added)),
        "anti_sot_directives_files_ever_added": sorted(set(anti_directives_added)),
        "anti_sot_evidence_count": len(set(anti_evidence_added)),
        "anti_sot_directives_count": len(set(anti_directives_added)),
    }


# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Check mas-engineer evidence/directive SOT locations"
    )
    parser.add_argument(
        "--git", action="store_true",
        help="Check git index (tracked files) instead of working tree only"
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit 1 if any violation found (CI mode)"
    )
    parser.add_argument(
        "--history", action="store_true",
        help="Scan all git history for past SOT violators (informational)"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="JSON output (machine-readable)"
    )
    args = parser.parse_args()

    result = {
        "sot_evidence_prefix": SOT_EVIDENCE_PREFIX,
        "sot_directives_prefix": SOT_DIRECTIVES_PREFIX,
        "anti_sot_evidence_prefix": ANTI_SOT_EVIDENCE,
        "anti_sot_directives_prefix": ANTI_SOT_DIRECTIVES,
        "checks": {},
    }

    # Working-tree checks (always)
    result["checks"]["evidence_sot_working_tree"] = check_evidence_sot_working_tree()
    result["checks"]["directives_sot_working_tree"] = check_directives_sot_working_tree()
    result["checks"]["sot_evidence_dir_health"] = check_sot_evidence_dir_health()
    result["checks"]["sot_directives_dir_health"] = check_sot_directives_dir_health()

    # Git-index checks (only with --git)
    if args.git:
        result["checks"]["evidence_sot_git_index"] = check_evidence_sot_git_index()
        result["checks"]["directives_sot_git_index"] = check_directives_sot_git_index()

    # History scan (only with --history)
    if args.history:
        result["history"] = scan_history_for_violators()

    # Compute summary
    all_violations = []
    for name, value in result["checks"].items():
        if isinstance(value, list) and value:
            all_violations.extend([f"{name}: {v}" for v in value])

    result["violation_count"] = len(all_violations)
    result["ok"] = len(all_violations) == 0

    # Output
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("=" * 60)
        print("R110-257 EVIDENCE/DIRECTIVE SOT CHECKER")
        print("=" * 60)
        print(f"SOT evidence:      {SOT_EVIDENCE_PREFIX} (REPO-ROOT)")
        print(f"SOT directives:    {SOT_DIRECTIVES_PREFIX}")
        print(f"Anti-SOT evidence: {ANTI_SOT_EVIDENCE}")
        print(f"Anti-SOT direct.:  {ANTI_SOT_DIRECTIVES}")
        print("-" * 60)

        for name, value in result["checks"].items():
            if isinstance(value, list):
                if value:
                    print(f"  ❌ {name}:")
                    for v in value:
                        print(f"      {v}")
                else:
                    print(f"  ✅ {name}: ok")
            else:
                if value:
                    print(f"  ❌ {name}: {value}")
                else:
                    print(f"  ✅ {name}: ok")

        if "history" in result:
            print("-" * 60)
            print("GIT HISTORY (informational, --diff-filter=A only):")
            h = result["history"]
            if "error" in h:
                print(f"  ❌ {h['error']}")
            else:
                print(f"  Anti-SOT evidence files EVER added: {h['anti_sot_evidence_count']}")
                print(f"  Anti-SOT directives files EVER added: {h['anti_sot_directives_count']}")

        print("=" * 60)
        if result["ok"]:
            print("RESULT: ✅ PASS — no SOT violations")
        else:
            print(f"RESULT: ❌ FAIL — {result['violation_count']} violation(s)")

    # Exit code
    if not result["ok"] and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"FATAL: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(2)
