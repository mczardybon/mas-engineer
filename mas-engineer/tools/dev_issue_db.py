#!/usr/bin/env python3
"""Persistent Issue-Database for the IM-pipeline (R110-177, PHASE 1).

Issue-centric rewrite of the improvement pipeline: every scanner-emit
gets a stable `issue_hash = sha256(file|type|structural_pattern)`.
The db (`.mase/pipeline/issue_db.json`) tracks first_seen / last_seen /
instances / status (open|fixed|wontfix|false_positive) / past_designs /
past_validation_outcomes across runs — so re-runs dedup against known
issues instead of re-emitting the same file-centric noise.

Spec: .mase/directives/R110-177-im-pipeline-issue-db.md (PHASE 1.3-1.8)
R110-177-ADAPTATION (documented in apply commit): `compute_structural_pattern`
(originally specified inside dev_im_finder_scan.py, PHASE 2.2) lives HERE so it
is unit-testable without triggering the scanner's heavy module-level scan.
The scanner imports it from this module.
"""
import contextlib
import hashlib
import json
import os
from typing import Dict, List, Optional

SCHEMA_VERSION = "1.0.0"


def _now_iso() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def compute_issue_hash(file: str, type: str, structural_pattern: str) -> str:
    """Stable hash for issue identity.

    structural_pattern: scanner-specific, e.g.:
      - "missing_try_except:38-42" (K1)
      - "extra_field:settings.timeout" (Q3)
      - "no_retry_on_subprocess:14-28" (K3)
      - "multi_role:5:['analyze','validate']" (NN1)
      - "hardcoded_count:1277:tests" (HARDCODE-STALE-001)
      - "stale_literal:'sales':recipe/sub" (STALE-LITERAL)

    Args:
      file: relativ zum mas-engineer cwd (z.B. "recipe/sub/sub_mas-foo.yaml")
      type: scanner-type (K1, K3, NN1, etc.)
      structural_pattern: scanner-emitted pattern (NORMALISIERT, kein random text)

    Returns:
      "sha256:" + 64-char lowercase hex digest

    Properties:
      - stable: same (file, type, structural_pattern) -> same hash
      - file-local: pattern in different file = different hash
      - line-bucketed: pattern in same line-range = same hash,
        pattern in different line-range = different hash
        (BUT: NN1 uses role-list, not line-range, so renames don't reset)
      - scanner-version-INSENSITIVE: hash MUST NOT include scanner_version
    """
    # Normalize file path (resolve symlinks, remove leading ./)
    norm_file = os.path.normpath(file).lstrip('./')
    # Structural pattern is already normalized by caller
    raw = f"{norm_file}|{type}|{structural_pattern}"
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compute_structural_pattern(ftype: str, file: str, **kwargs) -> str:
    """Generate stable structural pattern per finding-type.

    R110-177-ADAPTATION: specified in PHASE 2.2 as a helper inside
    dev_im_finder_scan.py; implemented here (dev_issue_db.py) so the
    scanner and the tests share one importable definition.

    Properties:
      - line-bucketed types: pattern includes line_range
      - content-agnostic: same issue after file-edit = same pattern
      - type-specific: NN1 uses role-list, K1 uses line-range, etc.
    """
    if ftype in ('K1', 'K3', 'L1', 'U1'):
        # line-range-based, scanner already has line numbers
        return f"{ftype.lower()}:{kwargs.get('line_start', 0)}-{kwargs.get('line_end', 0)}"
    elif ftype == 'Q3':
        return f"extra_field:{kwargs.get('field_name', 'unknown')}"
    elif ftype == 'NN1':
        roles = sorted(kwargs.get('roles', []) or [])
        return f"multi_role:{len(roles)}:{','.join(roles)}"
    elif ftype == 'NN2':
        return f"tool_overload:{kwargs.get('extension_count', 0)}"
    elif ftype == 'NN3':
        domains = sorted(kwargs.get('domains', []) or [])
        return f"scope_bloat:{len(domains)}:{','.join(domains[:3])}"
    elif ftype.startswith('HARDCODE-STALE') or ftype.startswith('STALE-LITERAL'):
        return f"{ftype}:{kwargs.get('literal', '')}:{kwargs.get('file_dir', '')}"
    else:
        # default: include file basename + type
        return f"{ftype}:{os.path.basename(file)}"


def validate_wontfix_reason(reason: str) -> Optional[str]:
    """Validate a wontfix reason per R110-177 PHASE 6.3.

    Returns None if valid, else an error message string.
    Rules:
      - non-empty
      - minimum 10 chars
      - maximum 500 chars
      - not a placeholder ("todo", "tbd", "fixme", "wip")
    """
    if not reason or not reason.strip():
        return "wontfix reason must be non-empty"
    r = reason.strip()
    if len(r) < 10:
        return f"wontfix reason too short ({len(r)} chars, min 10)"
    if len(r) > 500:
        return f"wontfix reason too long ({len(r)} chars, max 500)"
    if r.lower() in ('todo', 'tbd', 'fixme', 'wip'):
        return f"wontfix reason is a placeholder: {r!r}"
    return None


class IssueDB:
    """Persistent issue database. ACID via file-locking + atomic-rename."""

    def __init__(self, db_path: str = ".mase/pipeline/issue_db.json"):
        self.db_path = db_path
        self._lock_path = db_path + ".lock"
        self._load_or_init()

    def _load_or_init(self):
        """Load existing db or initialize empty schema."""
        if os.path.exists(self.db_path):
            with open(self.db_path) as f:
                self._data = json.load(f)
        else:
            self._data = {
                "schema_version": SCHEMA_VERSION,
                "created_at": _now_iso(),
                "last_modified_at": _now_iso(),
                "last_modified_by": "init",
                "summary": {
                    "total_issues": 0,
                    "by_status": {"open": 0, "fixed": 0, "wontfix": 0,
                                  "false_positive": 0},
                    "by_type": {},
                },
                "issues": {},
            }

    def get(self, issue_hash: str) -> Optional[Dict]:
        """Return issue dict or None."""
        return self._data["issues"].get(issue_hash)

    def exists(self, issue_hash: str) -> bool:
        return issue_hash in self._data["issues"]

    def status(self, issue_hash: str) -> str:
        """Return 'open' | 'fixed' | 'wontfix' | 'false_positive' | 'unknown'."""
        issue = self.get(issue_hash)
        return issue["status"] if issue else "unknown"

    def should_emit_finding(self, issue_hash: str) -> bool:
        """Finder hook: should this scanner-emit become a new finding?
        - unknown hash -> YES (new issue)
        - open -> NO (already known, just instance++)
        - fixed -> NO (skip, but record in instances for history)
        - wontfix -> NO (skip)
        - false_positive -> NO (skip)
        Returns True iff status == 'unknown'.
        """
        return self.status(issue_hash) == "unknown"

    def register(self, *, hash: str, type: str, severity: str, file: str,
                 structural_pattern: str, issue_summary: str, fix_summary: str,
                 instance: Dict, goose_verdict: Optional[Dict] = None) -> str:
        """Register new issue OR append instance to existing one.

        If hash unknown: create new entry, instance_count=1, status=open.
        If hash known with status=open: append instance, increment count.
        If hash known with status=fixed/wontfix/false_positive: log + skip
        (caller should NOT have called us — defensive).

        Returns the issue_hash (always same as input).
        """
        if self.exists(hash):
            issue = self.get(hash)
            if issue["status"] == "open":
                issue["instance_count"] += 1
                issue["instances"].append(instance)
                issue["last_seen"] = _now_iso()
                if goose_verdict:
                    self._update_goose_verdict(issue, goose_verdict)
            else:
                # status=fixed/wontfix/false_positive: log but don't modify
                pass
        else:
            self._data["issues"][hash] = {
                "hash": hash, "type": type, "severity": severity,
                "file": file, "structural_pattern": structural_pattern,
                "first_seen": _now_iso(), "last_seen": _now_iso(),
                "instance_count": 1, "instances": [instance],
                "status": "open", "issue_summary": issue_summary,
                "fix_summary": fix_summary,
                "goose_verdict": goose_verdict,
                "past_designs": [], "past_validation_outcomes": [],
                "wontfix_reason": None, "wontfix_marked_at": None,
                "wontfix_marked_by": None,
            }
        return hash

    def mark_fixed(self, issue_hash: str, commit_sha: str,
                   validated_by: str = "im-validator") -> bool:
        """Mark issue as fixed. Append past_validation_outcome.

        Returns True if state changed (was open, now fixed), False otherwise.
        """
        issue = self.get(issue_hash)
        if not issue:
            return False
        if issue["status"] == "open":
            issue["status"] = "fixed"
            issue["past_validation_outcomes"].append({
                "validated_at": _now_iso(),
                "validated_by": validated_by,
                "verdict": "APPROVED",
                "reason": "patch applied successfully",
                "commit_sha": commit_sha,
            })
            return True
        return False

    def mark_wontfix(self, issue_hash: str, reason: str,
                     marked_by: str = "general-improver") -> bool:
        """Mark issue as wontfix. Requires non-empty reason.

        Returns True if state changed, False if already wontfix or not found.
        """
        if not reason or not reason.strip():
            raise ValueError("wontfix reason must be non-empty")
        issue = self.get(issue_hash)
        if not issue:
            return False
        if issue["status"] == "wontfix":
            return False
        issue["status"] = "wontfix"
        issue["wontfix_reason"] = reason
        issue["wontfix_marked_at"] = _now_iso()
        issue["wontfix_marked_by"] = marked_by
        return True

    def record_design(self, issue_hash: str, patch: Dict,
                      goose_verdict: str, verdict_explanation: str,
                      design_run_id: str,
                      designed_by: str = "im-designer") -> None:
        """Append to past_designs (called when im-designer drafts a patch)."""
        issue = self.get(issue_hash)
        if not issue:
            return
        issue["past_designs"].append({
            "designed_at": _now_iso(),
            "designed_by": designed_by,
            "patch": patch,
            "goose_verdict": goose_verdict,
            "verdict_explanation": verdict_explanation,
            "design_run_id": design_run_id,
        })

    def record_validation(self, issue_hash: str, verdict: str, reason: str,
                          commit_sha: Optional[str] = None,
                          validated_by: str = "im-validator") -> None:
        """Append to past_validation_outcomes (called by im-validator)."""
        issue = self.get(issue_hash)
        if not issue:
            return
        issue["past_validation_outcomes"].append({
            "validated_at": _now_iso(),
            "validated_by": validated_by,
            "verdict": verdict,
            "reason": reason,
            "commit_sha": commit_sha,
        })

    def list_open(self) -> List[str]:
        """Return hashes of all open issues (rank-stage input)."""
        return [h for h, i in self._data["issues"].items()
                if i["status"] == "open"]

    def list_by_status(self, status: str) -> List[str]:
        return [h for h, i in self._data["issues"].items()
                if i["status"] == status]

    def filter_findings(self, findings: List[Dict]) -> List[Dict]:
        """R110-177 PHASE 3 (im-rank STEP 1.4): drop findings whose
        issue_hash is already fixed / wontfix / false_positive in the db.

        Defensive: findings without issue_hash are KEPT (finder will catch
        on next run after PHASE 2 fully deployed).
        """
        excluded = set()
        for s in ('fixed', 'wontfix', 'false_positive'):
            excluded |= set(self.list_by_status(s))
        out = []
        dropped = 0
        for f in findings:
            h = f.get('issue_hash')
            if not h:
                out.append(f)  # keep + warn (logged by caller)
                continue
            if h in excluded:
                dropped += 1
                continue
            out.append(f)
        return out, dropped

    def save(self):
        """Atomic save: write to .tmp, fsync, rename. Updates summary."""
        self._data["last_modified_at"] = _now_iso()
        self._data["summary"] = self._compute_summary()
        tmp_path = self.db_path + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(self._data, f, indent=2, sort_keys=False)
            f.flush()
            os.fsync(f.fileno())
        os.rename(tmp_path, self.db_path)

    @contextlib.contextmanager
    def save_with_lock(self, timeout: int = 30):
        """Save with file-locking (fcntl.flock) for concurrent im-finder/rank/validator.

        Lock strategy: each stage acquires exclusive lock for the duration of
        its read-modify-write. Lock is released automatically on process exit
        (fcntl.flock is held by file-descriptor, closed on exit).

        Usage (per R110-177 spec 1.4 caller pattern):
            with db.save_with_lock():
                db.modify(...)
        """
        import contextlib
        import fcntl
        with open(self._lock_path, "w") as lock_fh:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
            try:
                # Re-load in case another process modified
                self._load_or_init()
                # Caller does their modifications here
                yield self
                self.save()
            finally:
                fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)

    def _update_goose_verdict(self, issue: Dict,
                              goose_verdict: Dict) -> None:
        cur = issue.get("goose_verdict")
        if cur is None:
            issue["goose_verdict"] = goose_verdict
            return
        # Merge: keep first_verdict_at, increment verdict_count
        cur["verdict"] = goose_verdict.get("verdict", cur["verdict"])
        cur["confidence"] = goose_verdict.get("confidence", cur["confidence"])
        if goose_verdict.get("explanation"):
            cur["explanation"] = goose_verdict["explanation"]
        if goose_verdict.get("alternatives"):
            cur["alternatives"] = goose_verdict["alternatives"]
        cur["verdict_count"] = cur.get("verdict_count", 1) + 1

    def _compute_summary(self) -> Dict:
        summary = {
            "total_issues": len(self._data["issues"]),
            "by_status": {"open": 0, "fixed": 0, "wontfix": 0,
                          "false_positive": 0},
            "by_type": {},
        }
        for i in self._data["issues"].values():
            s = i["status"]
            if s in summary["by_status"]:
                summary["by_status"][s] += 1
            t = i["type"]
            summary["by_type"][t] = summary["by_type"].get(t, 0) + 1
        return summary


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Issue-DB inspection CLI (R110-177)")
    p.add_argument("--db", default=".mase/pipeline/issue_db.json")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("stats")
    sub.add_parser("list-open")
    sub.add_parser("list-wontfix")
    sub.add_parser("list-fixed")
    mark_w = sub.add_parser("mark-wontfix")
    mark_w.add_argument("hash")
    mark_w.add_argument("--reason", required=True)
    args = p.parse_args()
    db = IssueDB(args.db)
    if args.cmd == "stats":
        print(json.dumps(db._data["summary"], indent=2))
    elif args.cmd == "list-open":
        for h in db.list_open():
            i = db.get(h)
            print(f"{h}  {i['type']:8s}  {i['file']}")
    elif args.cmd == "list-wontfix":
        for h in db.list_by_status("wontfix"):
            i = db.get(h)
            print(f"{h}  {i['type']:8s}  {i['file']}  {i['wontfix_reason']}")
    elif args.cmd == "list-fixed":
        for h in db.list_by_status("fixed"):
            i = db.get(h)
            print(f"{h}  {i['type']:8s}  {i['file']}")
    elif args.cmd == "mark-wontfix":
        err = validate_wontfix_reason(args.reason)
        if err:
            print(f"ERROR: {err}", file=__import__('sys').stderr)
            __import__('sys').exit(1)
        changed = db.mark_wontfix(args.hash, args.reason)
        db.save()
        print(f"mark-wontfix changed={changed}")
