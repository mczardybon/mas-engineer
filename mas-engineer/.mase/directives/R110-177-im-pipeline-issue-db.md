# R110-177 — IM-pipeline issue-centric rewriter (Plan C: Issue-DB)

## Context (R110-176 hit)

R110-176 e2e (2026-08-17): 5/5 phases PASS, **0 patches applied**.
Diagnose (R110-177 dialog-notiz, 2026-08-17):

| Metric | Value | Root cause |
|---|---|---|
| Raw findings | 1690 | Scanner ist file-centric statt issue-centric |
| Goose verdicts | 257 (15.2%) | LLM nur fuer 15% erreicht (cost cap) |
| Severity medium | 35 (2.1%) | 1655 low = kosmetik die niemand fixen muss |
| Top-10 ranked | 10 NN1 | NN1-detector emittiert FPs (prohibition-blocks) |
| Designed | 0 | R52/R10 blocken korrekt, weil signal zu schlecht |
| Applied | 0 | — |

**Top-5 by_type (663/1690 = 39%):**
- K1 (129): missing try/except — pro FILE ohne try/except, NICHT pro issue
- K3 (135): no retry on transient errors — pro FILE ohne retry
- L1 (132): session cleanup missing — pro FILE ohne cleanup
- Q3 (136): extra field — pro UNBEKANNTEM FELD (oft false positive)
- U1 (131): not undoable — pro FILE ohne backup

Plan A (severity-threshold + dedup) und Plan B (statischer pre-filter + LLM-vorfilter)
wurden in R110-177-dialog-notiz vorgeschlagen. **Plan C (issue-DB)** ist hier
spezifiziert — der einzige plan der das signal-to-noise **strukturell** loest,
statt jeden run erneut die gleiche filter-arbeit machen zu lassen.

## Goal

mas-engineer's IM-pipeline soll **issue-centric** statt **file-centric** arbeiten.
Konkrete ziele:

1. **Issue-Hashing:** Pro scanner-emit wird ein `issue_hash = hash(file + type + structural_pattern)`
   berechnet. Gleicher hash = gleiches issue (ueber runs hinweg).
2. **Issue-DB** (`.mase/pipeline/issue_db.json` — PERSISTENT EVIDENCE ARCHIVE,
   neben patches.yaml / validation.yaml / self_audit.yaml / signal_*.yaml /
   round*_findings.json): first_seen / last_seen / instances / status
   (open/fixed/wontfix) / past_designs / past_validation_outcomes.
3. **Finder-Dedup:** Neuer hash = neue finding. Existierender hash mit
   status=open = instanz++ (kein neuer write). Status=fixed = skip komplett.
4. **Rank-Status-Aware:** OPEN issues only. Wontfix-issues fliegen raus.
5. **Validator-Tracking:** Apply success → status=fixed (mit file+commit
   reference). Apply fail / coronashield-block → status bleibt open +
   `past_validation_outcomes[]` appended.
6. **Wontfix-Action:** General-improver kann issues explizit als wontfix
   markieren mit reason (interaktive prompt, R01-gated).
7. **Re-run-Effekt:** Run 1: 1690 findings → 1690 neue issues in db.
   Run 2: 1690 scanner-emits → ~50 wirklich neue (file-changes seit run 1)
   + ~1640 deduplicated + ~0 wontfix. Top-10 = sehr wahrscheinlich patches.

## WARUM `.mase/pipeline/issue_db.json` (NICHT `.state/`)

Per `docs/REVIEW-2026-07-18.md` + R110-78/R110-175 etablierte konvention:

- `.mas/` (singular) = MCP + dashboard runtime (server.js, dashboard.html,
  cost.yaml) — FRAMEWORK-RUNTIME, NICHT fuer data
- `.state/` = framework-state (rules, knowledge, templates, schedule,
  workflow) + transient run-state (.state/pipeline/findings.yaml,
  ranked_findings.yaml — gitignored) + persistent run-state
  (.state/pipeline/patches.yaml, validation.yaml — committed)
- `.mase/` (plural, mit "e") = **PERSISTENT EVIDENCE ARCHIVE**
  (.mase/pipeline/patches.yaml, validation.yaml, self_audit.yaml,
  signal_*.yaml, round*_findings.json, im_apply_only_log.yaml) —
  **HIER GEHOERT DIE ISSUE-DB HIN** (commit auf milestone-basis,
  akkumuliert ueber runs)

**VERWEchslung-trap (R110-78 lesson):** 3 dirs mit aehnlichen namen, 2 zwecke:

| Dir | Zweck | Git? |
|---|---|---|
| `.mas/` | MCP + dashboard runtime (singular) | committed (server.js) + gitignored (data.json) |
| `.state/` | framework + transient run-state | mixed (transient gitignored, persistent committed) |
| `.mase/` | PERSISTENT EVIDENCE ARCHIVE (plural mit "e") | committed (außer .immune_clean) |

Issue-DB ist **persistent evidence archive** → `.mase/pipeline/issue_db.json`.
Niemals in `.state/`, dort waere sie nach `.gitignore`-regel unsichtbar.

================================================================
PHASE 1 — Issue-DB schema + helper tool (`tools/dev_issue_db.py`)
================================================================

## 1.1 EXACT FILE + INSERT-POINT

**NEUE DATEI:** `mas-engineer/tools/dev_issue_db.py` (reines Python-modul,
KEIN sh-Script). Wird sowohl von im-finder (read+write), im-rank
(read+filter), im-validator (read+update), und general-improver
(read+mark-wontfix) aufgerufen.

## 1.2 SCHEMA (`.mase/pipeline/issue_db.json`)

```json
{
  "schema_version": "1.0.0",
  "created_at": "2026-08-17T15:30:00Z",
  "last_modified_at": "2026-08-17T15:30:00Z",
  "last_modified_by": "im-finder",
  "summary": {
    "total_issues": 0,
    "by_status": {"open": 0, "fixed": 0, "wontfix": 0, "false_positive": 0},
    "by_type": {"K1": 0, "K3": 0, "...": 0}
  },
  "issues": {
    "<issue_hash>": {
      "hash": "sha256:<64 hex chars>",
      "type": "K1",
      "severity": "medium",
      "file": "recipe/sub/sub_mas-foo.yaml",
      "structural_pattern": "missing_try_except:38-42",
      "first_seen": "2026-08-17T15:30:00Z",
      "last_seen": "2026-08-17T15:30:00Z",
      "instance_count": 1,
      "instances": [
        {"file": "recipe/sub/sub_mas-foo.yaml", "line_start": 38, "line_end": 42, "context": "yaml_block:N", "scanner_version": "dev_im_finder_scan.py:1.4.2"}
      ],
      "status": "open",
      "issue_summary": "missing try/except in critical section",
      "fix_summary": "wrap subprocess.run in try/except",
      "goose_verdict": {
        "verdict": "CONFORM",
        "confidence": "HIGH",
        "explanation": "...",
        "alternatives": [],
        "first_verdict_at": "2026-08-17T15:30:00Z",
        "verdict_count": 1
      },
      "past_designs": [
        {
          "designed_at": "2026-08-17T15:30:00Z",
          "designed_by": "im-designer",
          "patch": {"file": "...", "field": "...", "from": "...", "to": "..."},
          "goose_verdict": "CONFORM",
          "verdict_explanation": "...",
          "design_run_id": "uuid-v4"
        }
      ],
      "past_validation_outcomes": [
        {
          "validated_at": "2026-08-17T15:30:00Z",
          "validated_by": "im-validator",
          "verdict": "APPROVED|REJECTED|SKIPPED",
          "reason": "...",
          "commit_sha": "abc1234"  // nur bei APPROVED + applied
        }
      ],
      "wontfix_reason": null,  // string, nur wenn status=wontfix
      "wontfix_marked_at": null,
      "wontfix_marked_by": null
    }
  }
}
```

**Invarianten** (vom helper garantiert):
- `hash` ist IMMER `sha256:<64 hex chars>`, lowercase
- `instance_count` == `len(instances)`
- `status` ∈ {open, fixed, wontfix, false_positive}
- `last_seen >= first_seen`
- `wontfix_reason` is not null iff status == wontfix
- `goose_verdict` is null ODER verdict ∈ {CONFORM, RESTRICTED, NOT_POSSIBLE}

## 1.3 HASH-FUNKTION

```python
import hashlib

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
      - stable: same (file, type, structural_pattern) → same hash
      - file-local: pattern in different file = different hash
      - line-bucketed: pattern in same line-range = same hash,
        pattern in different line-range = different hash
        (BUT: NN1 uses role-list, not line-range, so renames don't reset)
      - scanner-version-INSENSITIVE: hash MUST NOT include scanner_version
        (older runs must dedup with newer runs of same issue)
    """
    # Normalize file path (resolve symlinks, remove leading ./)
    norm_file = os.path.normpath(file).lstrip('./')
    # Structural pattern is already normalized by caller
    raw = f"{norm_file}|{type}|{structural_pattern}"
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()
```

**Properties (im test zu verifizieren):**
- Same file + type + pattern → same hash
- Different file → different hash
- Different line-range → different hash (for line-bucketed types)
- Same line-range after file-edit (e.g. comment added) → SAME hash
  (structural_pattern is generated by scanner, not by file content)
- Schema change (add field to issue) → hash UNCHANGED (hash only on identity triple)
- Scanner version bump → hash UNCHANGED

## 1.4 PUBLIC API VON `tools/dev_issue_db.py`

```python
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
                "schema_version": "1.0.0",
                "created_at": _now_iso(),
                "last_modified_at": _now_iso(),
                "last_modified_by": "init",
                "summary": {"total_issues": 0, "by_status": {...}, "by_type": {}},
                "issues": {}
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
        - unknown hash → YES (new issue)
        - open → NO (already known, just instance++)
        - fixed → NO (skip, but record in instances for history)
        - wontfix → NO (skip)
        - false_positive → NO (skip)
        Returns True iff status == 'unknown' (caller increments via register).
        """
        s = self.status(issue_hash)
        return s == "unknown"

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
                      design_run_id: str, designed_by: str = "im-designer") -> None:
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
        return [h for h, i in self._data["issues"].items() if i["status"] == "open"]

    def list_by_status(self, status: str) -> List[str]:
        return [h for h, i in self._data["issues"].items() if i["status"] == status]

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

    def save_with_lock(self, timeout: int = 30):
        """Save with file-locking (fcntl.flock) for concurrent im-finder/rank/validator.

        Lock strategy: each stage acquires exclusive lock for the duration of
        its read-modify-write. Lock is released automatically on process exit
        (fcntl.flock is held by file-descriptor, closed on exit).
        """
        import fcntl
        with open(self._lock_path, "w") as lock_fh:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
            try:
                # Re-load in case another process modified
                self._load_or_init()
                # Caller does their modifications here
                yield  # (caller pattern: `with db.save_with_lock(): db.modify(...)`)
                self.save()
            finally:
                fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)

    def _compute_summary(self) -> Dict:
        summary = {
            "total_issues": len(self._data["issues"]),
            "by_status": {"open": 0, "fixed": 0, "wontfix": 0, "false_positive": 0},
            "by_type": {},
        }
        for i in self._data["issues"].values():
            s = i["status"]
            if s in summary["by_status"]:
                summary["by_status"][s] += 1
            t = i["type"]
            summary["by_type"][t] = summary["by_type"].get(t, 0) + 1
        return summary
```

**CLI WRAPPER** (am ende der datei, fuer manuelle inspection + tests):

```python
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
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
    # ... etc
```

## 1.5 TESTS (`tests/test_dev_issue_db.py`)

NEUE DATEI: `mas-engineer/tests/test_dev_issue_db.py` (pytest-discoverable,
im standard-tests/ tree, ALSO pytest-count +1).

Test cases (minimum 8):
1. `test_compute_issue_hash_stable`: same args → same hash
2. `test_compute_issue_hash_normalizes_paths`: `./a/b` == `a/b` == `b/../a/b`
3. `test_compute_issue_hash_file_local`: different file → different hash
4. `test_compute_issue_hash_pattern_local`: same file, different pattern → different hash
5. `test_register_new_issue`: unknown hash → creates entry, status=open, count=1
6. `test_register_existing_open_increments`: same hash 2x → count=2, last_seen updated
7. `test_register_existing_fixed_skips`: status=fixed → register is no-op
8. `test_mark_wontfix_requires_reason`: empty reason → ValueError
9. `test_mark_wontfix_state_transition`: open → wontfix, wontfix_reason set
10. `test_mark_fixed_state_transition`: open → fixed, past_validation appended
11. `test_save_atomic_no_partial`: simulate crash mid-write, db must be valid JSON
12. `test_concurrent_lock_blocks`: 2 threads, 2nd waits for 1st's lock release
13. `test_cli_stats_prints_summary`: subprocess call, parse stdout JSON
14. `test_schema_invariants_after_register`: instance_count == len(instances)
15. `test_schema_invariants_after_wontfix`: wontfix_reason not null iff status=wontfix

**EXPECTED pytest-count growth:** R110-177 start ~1544 (post R110-171/R110-173),
PHASE 1 adds +15 tests → 1559.

## 1.6 INTEGRATION HOOK-POINTS

PHASE 1 hat KEINE integrations (helper ist pure-library, no caller yet).
PHASE 2-5 wire es in die pipeline.

## 1.7 IDEMPOTENZ

- `dev_issue_db.py` ist reines library + CLI. Re-running `test_dev_issue_db.py`
  ist deterministisch (jeder test nutzt tempfile-IssueDB, nicht die echte db).
- Production db (`.mase/pipeline/issue_db.json`) wird initial leer erstellt
  wenn nicht existent. **Niemals ueberschreiben ohne diff-confirmation.**

## 1.8 OUT OF SCOPE (PHASE 1)

- KEIN scanner-update (PHASE 2)
- KEIN rank/designer/validator-update (PHASE 3-5)
- KEIN general-improver-prompt-update (PHASE 6)
- KEIN bulk-import von R110-176-findings in die db (PHASE 7, optional)

================================================================
PHASE 2 — Finder: hash + dedup gegen Issue-DB
================================================================

## 2.1 EXACT FILE + INSERT-POINT

**MODIFY:** `mas-engineer/tools/dev_im_finder_scan.py`
- INSERT-POINT 1: nach `import` block (oben), add `from dev_issue_db import IssueDB, compute_issue_hash`
- INSERT-POINT 2: `add_finding()` function (Z. 104-112), MODIFY to add
  `issue_hash` field + dedup-check
- INSERT-POINT 3: end of main (Z. 460+), add IssueDB save block

## 2.2 STRUCTURAL_PATTERN NORMALISIERUNG

Jeder scanner-type braucht einen `structural_pattern` generator. Wird
als helper-funktion in `dev_im_finder_scan.py` ergaenzt:

```python
def compute_structural_pattern(ftype: str, file: str, **kwargs) -> str:
    """Generate stable structural pattern per finding-type.

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
        roles = sorted(kwargs.get('roles', []))
        return f"multi_role:{len(roles)}:{','.join(roles)}"
    elif ftype == 'NN2':
        return f"tool_overload:{kwargs.get('extension_count', 0)}"
    elif ftype == 'NN3':
        domains = sorted(kwargs.get('domains', []))
        return f"scope_bloat:{len(domains)}:{','.join(domains[:3])}"
    elif ftype in ('HARDCODE-STALE-001', 'STALE-LITERAL-001', ...):
        return f"{ftype}:{kwargs.get('literal', '')}:{kwargs.get('file_dir', '')}"
    else:
        # default: include file basename + type
        return f"{ftype}:{os.path.basename(file)}"
```

## 2.3 MODIFIED `add_finding()` (PHASE 2)

```python
# Add module-level state for IssueDB
_ISSUE_DB = None  # lazy-init in main

def _get_issue_db():
    global _ISSUE_DB
    if _ISSUE_DB is None:
        from dev_issue_db import IssueDB
        _ISSUE_DB = IssueDB(db_path='.mase/pipeline/issue_db.json')
    return _ISSUE_DB

def add_finding(ftype, severity, file, issue, impact, fix,
                *, line_start=None, line_end=None, **pattern_kwargs):
    global fid
    if severity not in SEVERITY_FILTER:
        return
    fid += 1
    finding_id = f'F-{fid:03d}'

    # PHASE 2: compute structural pattern + issue_hash
    struct_pattern = compute_structural_pattern(
        ftype, file,
        line_start=line_start, line_end=line_end, **pattern_kwargs
    )
    issue_hash = compute_issue_hash(file, ftype, struct_pattern)

    # PHASE 2: dedup against IssueDB
    db = _get_issue_db()
    instance = {
        "file": file,
        "line_start": line_start,
        "line_end": line_end,
        "context": pattern_kwargs.get('context', 'unknown'),
        "scanner_version": "dev_im_finder_scan.py:1.5.0",
        "finding_id": finding_id,
    }
    db.register(
        hash=issue_hash, type=ftype, severity=severity, file=file,
        structural_pattern=struct_pattern, issue_summary=issue,
        fix_summary=fix, instance=instance,
    )

    findings.append({
        'id': finding_id,
        'type': ftype,
        'severity': severity,
        'file': file,
        'issue': issue,
        'impact': impact,
        'fix': fix,
        'issue_hash': issue_hash,  # NEW
        'structural_pattern': struct_pattern,  # NEW
    })
```

## 2.4 FINDER-CALLER UPDATE (each scanner-detector)

Each `add_finding(...)` call-site muss um `line_start=`, `line_end=`, und
type-specific kwargs erweitert werden. Beispiel:

**VORHER (K1, Z. ~400, ohne line-info):**
```python
add_finding('K1', 'medium', yp,
            'missing try/except in critical section',
            'unhandled exception may crash agent',
            'wrap in try/except')
```

**NACHHER (PHASE 2, mit line-info):**
```python
# Bestimme line_start/line_end aus scanner-detection
add_finding('K1', 'medium', yp,
            'missing try/except in critical section',
            'unhandled exception may crash agent',
            'wrap in try/except',
            line_start=line_no, line_end=line_no + 5,
            context='yaml_body')
```

**Wichtig:** `add_finding()` bleibt **backward-compatible** (kwargs mit
defaults). Bestehende call-sites ohne line-info funktionieren weiter,
nur dass sie `line_start=None, line_end=None` haben → pattern wird
type-spezifisch (z.B. fuer K1: `k1:None-None`, was zu **doppeltem
emittieren fuehrt** wenn der scanner mehrfach drueber laeuft).

**Deshalb:** PHASE 2 umfasst auch die migration der ~80 add_finding-call-sites
in `dev_im_finder_scan.py` (Z. 130-440). Jeder call-site bekommt:
- `line_start=`, `line_end=` aus dem scan-context (zeile + 5 typischerweise)
- type-spezifische kwargs (`roles=` fuer NN1, `extension_count=` fuer NN2, etc.)

**EXPECTED:** 1690 findings (R110-176) → ~1200-1500 nach add-line-info
(pattern-bucketing eliminiert false-multiplicity), dann ~50% davon sind
duplicate-of-existing nach PHASE 7 (bulk-import).

## 2.5 FINDER MAIN: save IssueDB

Am ende von `dev_im_finder_scan.py:main()` (nach JSON output, Z. 460):

```python
# PHASE 2: persist issue-db
db = _get_issue_db()
db.save()  # atomic write
print(f"ISSUE_DB: total={db._data['summary']['total_issues']} "
      f"open={db._data['summary']['by_status']['open']} "
      f"fixed={db._data['summary']['by_status']['fixed']} "
      f"wontfix={db._data['summary']['by_status']['wontfix']}")
```

## 2.6 TESTS

NEUE DATEI: `mas-engineer/tests/test_dev_im_finder_scan_dedup.py`

Test cases (minimum 6):
1. `test_finder_emits_issue_hash_field`: every finding has issue_hash
2. `test_finder_dedup_against_existing_db`: pre-populated db with hash X,
   re-run scanner, finding X NOT re-emitted (instance count +1 in db)
3. `test_finder_skips_fixed_issues`: pre-populated db with status=fixed
   for hash X, scanner does not emit X at all
4. `test_finder_skips_wontfix_issues`: same for wontfix
5. `test_finder_structural_pattern_k1`: K1 finding generates
   `k1:38-42`-style pattern
6. `test_finder_structural_pattern_nn1`: NN1 with roles=[a,b] generates
   `multi_role:2:a,b` (sorted)
7. `test_finder_atomic_db_save`: simulated crash mid-save, db file is
   either fully-old or fully-new (never partial)
8. `test_finder_preserves_history`: pre-populated with 3 past_designs,
   re-run scanner preserves them (does not clear)

**EXPECTED pytest-count growth:** PHASE 2 adds +8 tests → 1567.

## 2.7 IDEMPOTENZ

- Re-running scanner 2x ohne file-changes: 2nd run emittiert 0 findings
  (alle dedupliziert), aber issue-db-instance_count erhoeht sich nicht
  (weil register nur bei status=open inkrementiert, was beim re-emit
  nicht passiert — der scanner-springt via should_emit_finding raus)
- **CRITICAL:** `_ISSUE_DB = None` global + `_get_issue_db()` lazy-init
  ist absichtlich — pytest kann den scanner pro-test mit eigenem
  db-path initialisieren ohne interference

## 2.8 OUT OF SCOPE (PHASE 2)

- KEIN update von `sub_mas-im-finder.md` recipe (PHASE 3 verlinkt es)
- KEIN update von im-rank (PHASE 3)
- KEIN bulk-import von R110-176 (PHASE 7)

================================================================
PHASE 3 — Rank: status-aware filter gegen Issue-DB
================================================================

## 3.1 EXACT FILE + INSERT-POINT

**MODIFY:** `mas-engineer/recipe/instructions/sub_mas-im-rank.md` (151 lines)
- INSERT-POINT: zwischen STEP 1 (REMOVE DUPLICATES, Z. ~60) und STEP 1.5
  (APPLY SEVERITY CEILING, Z. ~70), add neuer STEP 1.4
- INSERT-POINT 2: am ende, add HINWEIS zu IssueDB-status

## 3.2 NEUER STEP 1.4 — ISSUE-DB STATUS FILTER

In `sub_mas-im-rank.md`, nach STEP 1 (REMOVE DUPLICATES) und vor STEP 1.5:

```markdown
## STEP 1.4 — APPLY ISSUE-DB STATUS FILTER (R110-177, PHASE 3)

**🚨 NEW IN R110-177: filter against persistent issue-db. 🚨**

Before sorting by severity, consult `.mase/pipeline/issue_db.json` and
REMOVE any finding whose `issue_hash` is already in the db with
status=fixed, wontfix, or false_positive.

Procedure:
1. LOAD: `python3 -c "from dev_issue_db import IssueDB; db=IssueDB(); print(','.join(db.list_by_status('fixed')+db.list_by_status('wontfix')))"`
2. BUILD: set `excluded_hashes = {h for h in db.list_by_status('fixed')} | {h for h in db.list_by_status('wontfix')} | {h for h in db.list_by_status('false_positive')}`
3. FILTER: for each finding in findings[], if `finding.issue_hash in excluded_hashes`: DROP + log "ISSUE-DB-SKIP: <hash> (<status>)"
4. LOG: `issue_db_filtered: <count> findings dropped (status=fixed/wontfix/false_positive)`

**Why this is correct:**
- R110-176 had 1690 findings, all "new" (no prior db). After PHASE 7
  (bulk-import), R110-178 run: 1690 scanner-emits, but most are
  already in db as open → no rank-time filtering. Future R110-179
  run with no file changes: ALL findings filtered (because no new
  issues, all known).
- The filter is RANK-TIME, not FINDER-TIME. Finder still records
  instances for history. Rank just doesn't promote already-resolved
  issues to top-N.

**Edge case: hash missing in db (finder didn't add it).**
- Defensive: if `finding.issue_hash` is None or empty, KEEP finding
  (finder will catch on next run after PHASE 2 fully deployed)
- Log "WARNING: finding without issue_hash, keeping for rank"
```

## 3.3 RANKED_FINDINGS OUTPUT EXTENSION

Modify `ranked_findings.yaml` output to include `issue_db_filtered` field
und behalte `issue_hash` in jedem finding:

```yaml
# .state/pipeline/ranked_findings.yaml — written by im-rank
stage: 2
agent: im-rank
timestamp: <ISO-8601>
input_file: .state/pipeline/findings.yaml
ceiling_filtered: 0
active_ceiling: high
issue_db_filtered: 0          # NEW (R110-177)
issue_db_status_counts: {     # NEW (R110-177)
  fixed: 0,
  wontfix: 0,
  false_positive: 0,
}
ranked_findings:
- id: F-001
  type: NN1
  severity: medium
  file: recipe/sub/sub_mas-foo.yaml
  rank_score: 75
  priority: 1
  goose_verdict: ...
  issue_hash: sha256:abc...   # NEW (R110-177) — pass-through from finder
```

## 3.4 TEST

NEUE DATEI: `mas-engineer/tests/test_sub_mas_im_rank_issue_db.py` (5 tests)

Cases:
1. `test_rank_filters_fixed`: pre-populated db with 3 fixed hashes,
   rank input has those + 5 new → output has 5
2. `test_rank_filters_wontfix`: same for wontfix
3. `test_rank_logs_issue_db_filtered_count`: count matches expectation
4. `test_rank_passes_through_issue_hash`: every output finding has issue_hash
5. `test_rank_handles_missing_hash`: finding without issue_hash kept + warning logged

**EXPECTED pytest-count growth:** +5 tests → 1572.

## 3.5 IDEMPOTENZ

- Rank liest IssueDB read-only. Re-running rank without db-change = same result.
- Filter ist konservativ: filter entfernt NUR known-fixed/wontfix/false_positive.
  Unknown hashes werden durchgelassen (default-safe).

## 3.6 OUT OF SCOPE (PHASE 3)

- KEIN update von finder/designer/validator (eigene phasen)
- KEIN wontfix-action (PHASE 6)

================================================================
PHASE 4 — Designer: record designs in Issue-DB
================================================================

## 4.1 EXACT FILE + INSERT-POINT

**MODIFY:** `mas-engineer/recipe/instructions/sub_mas-im-designer.md` (348 lines)
- INSERT-POINT: in STEP 0.5 (GOOSE-EXPERT CONSULTATION) block, after
  verdict received, add STEP 0.5b (RECORD DESIGN TO ISSUE-DB)
- INSERT-POINT 2: in STEP 1 (DRAFT PATCH) block, after patch is
  drafted, add ISSUE-DB RECORD call

## 4.2 NEUER STEP 0.5b — RECORD DESIGN TO ISSUE-DB (PHASE 4)

After receiving goose-expert verdict in STEP 0.5, BEFORE proceeding
to STEP 1 (DRAFT PATCH), record the design decision:

```markdown
## STEP 0.5b — RECORD DESIGN INTENT TO ISSUE-DB (R110-177, PHASE 4)

For EACH finding the goose-expert was consulted on, AFTER the verdict
arrives, RECORD the design decision in `.mase/pipeline/issue_db.json`:

```python
import uuid
from dev_issue_db import IssueDB

design_run_id = str(uuid.uuid4())  # one per im-designer invocation

for f in findings_with_verdicts:
    db = IssueDB()
    db.record_design(
        issue_hash=f['issue_hash'],
        patch=f.get('proposed_patch', {}),  # may be empty at STEP 0.5b
        goose_verdict=f['goose_verdict']['verdict'],
        verdict_explanation=f['goose_verdict']['explanation'],
        design_run_id=design_run_id,
    )
db.save()
```

**Why at STEP 0.5b (not STEP 1):**
- The verdict is the design CONSTRAINT (CONFORM/RESTRICTED/NOT_POSSIBLE).
- Recording the verdict tells future runs "this issue was consulted
  on at <timestamp>, expert said X". If the verdict was NOT_POSSIBLE,
  the future run knows: don't re-summon, just skip.
- Recording proposed_patch (even if empty) is the COMMITMENT — from now on,
  the issue has a past_design entry. If the run aborts before STEP 1,
  past_designs still shows the design attempt.
```

## 4.3 NEUER STEP 1.5 — UPDATE PROPOSED_PATCH IN ISSUE-DB (PHASE 4)

After STEP 1 (DRAFT PATCH) completes, the `proposed_patch` field is
populated. Update the past_designs entry:

```markdown
## STEP 1.5 — UPDATE PROPOSED_PATCH IN ISSUE-DB (R110-177, PHASE 4)

For each patch drafted in STEP 1, UPDATE the past_designs entry with
the actual proposed patch (which may differ from the STEP 0.5b intent):

```python
for patch in patches_yaml:
    db = IssueDB()
    # Find the past_design entry for this finding+run, update its patch
    issue = db.get(patch['issue_hash'])
    if not issue:
        continue
    for entry in issue.get('past_designs', []):
        if entry.get('design_run_id') == design_run_id:
            entry['patch'] = {
                'file': patch['file'],
                'field': patch['field'],
                'from': patch['from'],
                'to': patch['to'],
            }
            break
db.save()
```

**Why split (STEP 0.5b + STEP 1.5):**
- STEP 0.5b captures VERDICT (cheap, before patch exists)
- STEP 1.5 captures PATCH (expensive, after draft)
- If run aborts between, db has verdict but not patch — recoverable
  on next run by re-deriving patch from finding
```

## 4.4 TEST

NEUE DATEI: `mas-engineer/tests/test_sub_mas_im_designer_issue_db.py` (4 tests)

Cases:
1. `test_designer_records_verdict_at_step_0_5b`: issue.past_designs has entry
   with verdict but empty patch
2. `test_designer_updates_patch_at_step_1_5`: entry's patch is filled
3. `test_designer_aborts_between_steps_preserves_verdict`: simulate
   crash between 0.5b and 1.5, db has verdict-only entry
4. `test_designer_design_run_id_unique`: 2nd invocation gets different uuid

**EXPECTED pytest-count growth:** +4 tests → 1576.

## 4.5 IDEMPOTENZ

- record_design append-only. Re-running designer without finding-change
  appends a NEW past_design entry (different design_run_id), nicht
  den alten ueberschreiben. History preserved.

## 4.6 OUT OF SCOPE (PHASE 4)

- KEIN update von validator (PHASE 5)
- KEIN update von general-improver (PHASE 6)

================================================================
PHASE 5 — Validator: mark-fixed / record-outcome in Issue-DB
================================================================

## 5.1 EXACT FILE + INSERT-POINT

**MODIFY:** `mas-engineer/recipe/instructions/sub_mas-im-validator.md` (200 lines)
- INSERT-POINT: in STEP 0.5 (GOOSE-EXPERT POST-VALIDATION) block, after
  verdict received, add STEP 0.5c (RECORD VALIDATION OUTCOME)
- INSERT-POINT 2: nach "All-Restricted Detection" block (STEP 0.5b),
  add STEP 0.5d (UPDATE ISSUE-DB STATUS)

## 5.2 NEUER STEP 0.5c — RECORD VALIDATION OUTCOME (PHASE 5)

After receiving post-validation verdict in STEP 0.5, record:

```markdown
## STEP 0.5c — RECORD VALIDATION OUTCOME TO ISSUE-DB (R110-177, PHASE 5)

For each validated patch, AFTER goose-expert verdict arrives, RECORD
the validation outcome in `.mase/pipeline/issue_db.json`:

```python
from dev_issue_db import IssueDB

for patch_validation in validation_results:
    db = IssueDB()
    if patch_validation['verdict'] == 'APPROVED':
        # APPROVED + applied: mark as fixed
        db.mark_fixed(
            issue_hash=patch_validation['issue_hash'],
            commit_sha=patch_validation.get('commit_sha', 'unknown'),
            validated_by='im-validator',
        )
    else:
        # REJECTED or SKIPPED: just record outcome
        db.record_validation(
            issue_hash=patch_validation['issue_hash'],
            verdict=patch_validation['verdict'],
            reason=patch_validation.get('reason', ''),
            commit_sha=patch_validation.get('commit_sha'),
            validated_by='im-validator',
        )
db.save()
```

**Why mark-fixed ONLY at validator (not at apply):**
- Validator is the source of truth for "patch was applied correctly"
- If validator says APPROVED → mark fixed (commit_sha recorded)
- If validator says REJECTED → status stays open, but
  past_validation_outcomes has the rejection (for debugging)
- General-improver (apply stage) doesn't write to issue-db directly —
  it just applies the patch, validator confirms, validator marks fixed
```

## 5.3 NEUER STEP 0.5d — UPDATE CORONASHIELD-BLOCK COUNT (PHASE 5)

For issues that are coronashield-blocked, append outcome with
specific reason (so future runs know NOT to re-attempt):

```markdown
## STEP 0.5d — RECORD CORONASHIELD-BLOCK OUTCOME (R110-177, PHASE 5)

For issues where validation.verdict=REJECTED due to coronashield (R10,
R52, etc.), record SPECIFIC reason in past_validation_outcomes:

```python
if patch_validation['rejection_source'].startswith('coronashield'):
    db.record_validation(
        issue_hash=patch_validation['issue_hash'],
        verdict='SKIPPED',
        reason=f"coronashield:{patch_validation['rejection_source']}:{patch_validation['reason']}",
        validated_by='im-validator',
    )
```

**Why:**
- future runs can grep `past_validation_outcomes[].reason` for
  `coronashield:R10` and KNOW this issue is permanently blocked
- Enables a future PHASE 8 "wontfix-auto-coronashield" that
  auto-marks blocked issues as wontfix after N attempts
```

## 5.4 TEST

NEUE DATEI: `mas-engineer/tests/test_sub_mas_im_validator_issue_db.py` (5 tests)

Cases:
1. `test_validator_approved_marks_fixed`: APPROVED verdict → status=fixed
2. `test_validator_rejected_keeps_open`: REJECTED verdict → status=open,
   past_validation_outcomes has REJECTED entry
3. `test_validator_records_coronashield_reason`: R10-blocked → reason
   contains "coronashield:R10"
4. `test_validator_records_commit_sha_on_approved`: commit_sha present
5. `test_validator_skipped_keeps_open`: SKIPPED verdict → status=open

**EXPECTED pytest-count growth:** +5 tests → 1581.

## 5.5 IDEMPOTENZ

- mark_fixed is one-shot: re-running validator on same already-fixed
  issue returns False (no state change), keine doppelte past_validation.
- record_validation appends always (history grows monotonically).

## 5.6 OUT OF SCOPE (PHASE 5)

- KEIN general-improver-update (PHASE 6)
- KEIN auto-wontfix (PHASE 8, future)

================================================================
PHASE 6 — General-Improver: Wontfix-Action (interactive)
================================================================

## 6.1 EXACT FILE + INSERT-POINT

**MODIFY:** `mas-engineer/recipe/instructions/sub_mas-general-improver.md`
(via search for filename in repo — typically 300-500 lines)
- INSERT-POINT: add NEW STEP 2.7 (INTERACTIVE WONTFIX PROMPT) before
  existing STEP 3 (DRAFT PATCHES) or after STEP 2.5 (whichever is
  the last pre-design step)

## 6.2 NEUER STEP 2.7 — INTERACTIVE WONTFIX PROMPT (PHASE 6)

```markdown
## STEP 2.7 — INTERACTIVE WONTFIX PROMPT (R110-177, PHASE 6)

**🚨 NEW IN R110-177: explicit wontfix-action available to user. 🚨**

BEFORE proceeding to STEP 3 (DRAFT PATCHES), ASK the user once whether
they want to mark any open issues as `wontfix` for this run:

```
📋 ISSUE-DB STATUS: 35 open, 12 wontfix, 0 fixed

Top-5 open issues (after rank):
1. K1: recipe/sub/sub_mas-foo.yaml — missing try/except
2. K3: recipe/sub/sub_mas-bar.yaml — no retry on transient errors
3. NN1: recipe/sub/sub_mas-baz.yaml — multi-role
4. Q3: recipe/sub/sub_mas-qux.yaml — extra field
5. L1: recipe/sub/sub_mas-quux.yaml — session cleanup

Mark any of these as wontfix? Format: <hash>,<reason> (or 'no' to skip)

Examples:
- sha256:abc123...,not applicable for this single-purpose recipe
- sha256:def456...,covered by external linter rule X
```

Wait for user response:
- 'no' or empty: proceed to STEP 3 (no wontfix)
- comma-separated `<hash>,<reason>` pairs: mark each as wontfix
  (one reason per hash, reason can be multi-line until next comma-pair
  separator)
- 'all': DON'T auto-mark. Just list all 35 hashes with summaries,
  let user pick individually.

After receiving response, for each pair:

```python
from dev_issue_db import IssueDB
db = IssueDB()
for hash, reason in user_marked_pairs:
    db.mark_wontfix(
        issue_hash=hash,
        reason=reason,
        marked_by='general-improver',
    )
db.save()
```

The marked-wontfix issues are EXCLUDED from this run's STEP 3 onward
(rank-step 1.4 will re-filter them on next run, but for THIS run
the filter is already applied via the explicit in-memory exclusion).
```

## 6.3 WONTFIX-REASON VALIDATION

Reason must be:
- non-empty (rejected: empty string)
- minimum 10 chars (rejected: "n/a", "x", "no")
- maximum 500 chars (rejected: 1000-char essays)
- not a placeholder (rejected: "todo", "tbd", "fixme", "wip")

If user provides invalid reason, ASK ONCE for re-prompt. If still
invalid, mark as 'skipped' (log) und proceed.

## 6.4 TEST

NEUE DATEI: `mas-engineer/tests/test_sub_mas_general_improver_wontfix.py` (6 tests)

Cases:
1. `test_wontfix_prompt_skipped_with_no_response`: user types 'no' →
   0 issues marked, proceed to STEP 3
2. `test_wontfix_prompt_marks_single`: user types 'sha256:abc,reason X' →
   that issue status=wontfix, reason='reason X'
3. `test_wontfix_prompt_rejects_empty_reason`: 'sha256:abc,' → re-prompt
4. `test_wontfix_prompt_rejects_short_reason`: 'sha256:abc,no' → re-prompt
5. `test_wontfix_prompt_marks_multiple`: 3 pairs → 3 issues marked
6. `test_wontfix_excludes_from_this_run`: marked-wontfix issues don't
   appear in STEP 3 patch list (in-memory exclusion)

**EXPECTED pytest-count growth:** +6 tests → 1587.

## 6.5 IDEMPOTENZ

- mark_wontfix is one-shot: re-running with same hash+reason returns False.
- Wontfix-status is permanent (no auto-un-wontfix in any phase).
- Future runs of the same issue (e.g. after a refactor that "fixes"
  the file) do NOT auto-resurrect the issue — it stays wontfix
  (because the user explicitly chose not to fix it).

**Edge case:** if user marks NN1 on file X as wontfix, then file X
is renamed/moved, the issue-hash changes (new file in pattern),
new hash is registered as new open issue. Old wontfix is preserved
in db (historical).

## 6.6 OUT OF SCOPE (PHASE 6)

- KEIN auto-wontfix (PHASE 8, future)
- KEIN un-wontfix command (would require explicit re-open reason)
- KEIN bulk-wontfix (CLI: `python3 dev_issue_db.py mark-wontfix <hash>` works manually)

================================================================
PHASE 7 — Bulk-import (initial): migrate R110-176 findings
================================================================

## 7.1 EXACT FILE + INSERT-POINT

**NEUE DATEI:** `mas-engineer/tools/dev_issue_db_bulk_import.py` (one-time script)
- Reads: `.mase/pipeline/findings_R110-24-pre-framework.yaml` (oder das
  naechst-beste run-findings file) ODER runs the scanner fresh
- Writes: `.mase/pipeline/issue_db.json` (initial population)

## 7.2 INITIAL-POPULATION STRATEGY

Two options, chose ONE:

**OPTION A (preferred): use existing run-findings file**
- Read: `.mase/pipeline/findings_R110-24-pre-framework.yaml` (R110-24 run,
  hat schon format-struktur)
- For each finding: compute hash, register with status=open
- Mark all instances from the file (no goose_verdict available)

**OPTION B (fallback): re-run scanner**
- Run: `python3 tools/dev_im_finder_scan.py --scope=recipe`
- Scanner creates issue-db fresh (PHASE 2 logic)
- All 1690 findings registered as new open issues

OPTION A is preferred because:
- Uses existing evidence (R110-24 was the last FULL run with proper format)
- Faster (no scanner re-run, ~4 min saved)
- No risk of new FPs from a fresh scan polluting the db

## 7.3 SCRIPT (OPTION A)

```python
#!/usr/bin/env python3
"""One-time bulk-import of R110-24 findings into issue-db.

Run: python3 tools/dev_issue_db_bulk_import.py --source <findings.yaml>
"""
import yaml, argparse, sys
from dev_issue_db import IssueDB, compute_issue_hash, _now_iso

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', required=True,
                   help='Path to run-findings.yaml')
    p.add_argument('--db', default='.mase/pipeline/issue_db.json')
    p.add_argument('--default-status', default='open',
                   choices=['open', 'false_positive'])
    args = p.parse_args()

    with open(args.source) as f:
        data = yaml.safe_load(f)

    # R110-24 format: data['ranked_findings']: list of {id, type, severity, file, ...}
    findings = data.get('ranked_findings') or data.get('findings') or []
    if not findings:
        print(f"No findings in {args.source}", file=sys.stderr)
        sys.exit(1)

    db = IssueDB(args.db)

    for f in findings:
        if 'type' not in f or 'file' not in f:
            continue
        # For R110-24, we don't have structural_pattern, so use a generic one
        struct = f"{f['type'].lower()}:{f.get('id', 'unknown')}"
        h = compute_issue_hash(f['file'], f['type'], struct)
        instance = {
            'file': f['file'],
            'line_start': None, 'line_end': None,
            'context': 'bulk-import',
            'scanner_version': 'dev_issue_db_bulk_import.py:1.0',
            'finding_id': f.get('id', 'unknown'),
        }
        db.register(
            hash=h, type=f['type'], severity=f.get('severity', 'medium'),
            file=f['file'], structural_pattern=struct,
            issue_summary=f.get('issue', ''),
            fix_summary=f.get('fix', ''),
            instance=instance,
        )

    db.save()
    print(f"BULK-IMPORT: registered {len(findings)} issues from {args.source}")
    print(f"DB: {args.db}")
    print(f"Summary: {db._data['summary']}")

if __name__ == '__main__':
    main()
```

## 7.4 TEST

NEUE DATEI: `mas-engineer/tests/test_dev_issue_db_bulk_import.py` (3 tests)

Cases:
1. `test_bulk_import_creates_db_from_findings_yaml`: minimal yaml, run script,
   verify db populated
2. `test_bulk_import_handles_missing_fields`: yaml with no 'type' → skipped + logged
3. `test_bulk_import_idempotent`: run twice on same source → instance_count
   does NOT double (because register is dedup-aware)

**EXPECTED pytest-count growth:** +3 tests → 1590.

## 7.5 IDEMPOTENZ

- bulk-import is one-time per source file. Re-running is harmless
  (register dedups), but produces 0 new entries (all hashes already known).
- Source file is committed at `.mase/pipeline/findings_R110-24-...`,
  so re-running from same source is deterministic.

## 7.6 OUT OF SCOPE (PHASE 7)

- KEIN continuous sync (no re-import on every run)
- KEIN auto-import from other R-runs (manual only)

================================================================
PHASE 8 — E2E verification: re-run im-pipeline, confirm signal-improved
================================================================

## 8.1 EXACT FILE + INSERT-POINT

KEINE code-aenderung. Verifikations-script in `logs/e2e-evidence-gen2/`
(per R110-176 precedent).

## 8.2 VERIFIKATION (manual, post-all-phases)

After PHASE 1-7 are applied and pushed:

1. **Run scanner standalone:**
   ```bash
   cd /workspace/dev-branch/mas-engineer-cleanup/mas-engineer
   python3 tools/dev_im_finder_scan.py --scope=recipe
   ```
   Expected: 0 new findings emitted (all known via issue-db, all in
   `should_emit_finding=False` path because of dedup). Output shows
   `dedup_count: N` (count of skipped-due-to-dedup).

2. **Run full 5-phase im-pipeline (R110-178):**
   ```bash
   cd /workspace/dev-branch/mas-engineer-cleanup/mas-engineer
   echo "ack" | timeout 600 goose run --with-builtin developer \
     --recipe recipe/sub/sub_mas-im-finder.yaml --no-session
   echo "ack" | timeout 600 goose run --with-builtin developer \
     --recipe recipe/sub/sub_mas-im-rank.yaml --no-session
   echo "ack" | timeout 600 goose run --with-builtin developer \
     --recipe recipe/sub/sub_mas-im-designer.yaml --no-session
   echo "ack" | timeout 600 goose run --with-builtin developer \
     --recipe recipe/sub/sub_mas-im-validator.yaml --no-session
   echo "FULL_IMPROVEMENT - apply all CONFORM patches. ack" | timeout 600 \
     goose run --with-builtin developer \
     --recipe recipe/sub/sub_mas-general-improver.yaml --no-session
   ```

3. **EXPECTED outcomes:**
   - PHASE 1 (finder): scanner-emits ≈ 0 (because all 1690 R110-176 findings
     are in db as open, will_emit=False for all → instance_count +0
     because they're already at 1 from bulk-import)
   - PHASE 2 (rank): input has 0 findings, output empty
   - PHASE 3 (designer): no patches drafted
   - PHASE 4 (validator): no patches to validate
   - PHASE 5 (general-improver): R01 confirmation, then 0 applied

4. **ACCEPTANCE:** the run completed without errors AND the issue-db
   state is unchanged (no false-positive resurrection, no lost history).

5. **Counter-test:** Make a SMALL file change (e.g. add a deliberate
   K1 issue in a test recipe), re-run scanner, expect 1 new finding +
   1 new issue in db. This proves the new-file path works.

6. **Commit evidence:**
   - `git add` issue-db.json (if changed)
   - Commit message: `📊 docs(evidence): R110-178 im-pipeline e2e 0/5 patches (issue-db dedup verified)`
   - Body: numstat, file-listing, before/after issue-db summary,
     R110-177 reference

## 8.3 SUCCESS CRITERIA (all must hold)

- [ ] `dev_issue_db.py` is importable, has 100% public-API test coverage (15 tests)
- [ ] `dev_im_finder_scan.py` emits `issue_hash` on every finding (8 tests)
- [ ] `sub_mas-im-rank` filters by issue-db status (5 tests)
- [ ] `sub_mas-im-designer` records verdict + patch in issue-db (4 tests)
- [ ] `sub_mas-im-validator` marks fixed/records outcome (5 tests)
- [ ] `sub_mas-general-improver` supports wontfix action (6 tests)
- [ ] `dev_issue_db_bulk_import.py` works for R110-24 import (3 tests)
- [ ] Total: +46 tests, pytest 1544 → 1590, all PASS
- [ ] R110-178 e2e: 5/5 phases PASS, 0 patches applied (because all known),
      but issue-db is preserved
- [ ] Counter-test: 1 small file change → 1 new issue in db, dedup works

## 8.4 ROLLBACK STRATEGY

If R110-177 breaks the pipeline (e2e fails, tests red, etc.):

1. `git revert <R110-177-commit-sha>` (single commit revert, no force-push)
2. Issue-db at `.mase/pipeline/issue_db.json` is preserved (revert doesn't
   delete files, just changes them). User can manually inspect and decide
   whether to keep db or delete.
3. Per R110-78 pattern: NEXT R-NR (R110-179) is the transparent fix-commit,
   not amend+force-push.

## 8.5 OUT OF SCOPE (PHASE 8)

- KEIN code-aenderung (verification only)
- KEIN weitere improvement-phasen (R110-180+ future)

================================================================
NICHT TUN (anti-patterns, all phases)
================================================================

- **KEIN amend+force-push nach R110-177.** Per R110-174 lesson:
  wenn R110-178 (= R110-177 applied) fehler hat, ist R110-179 der
  fix-commit, nicht amend.

- **KEIN silent schema migration.** Wenn `issue_db.json` schema sich
  aendert (z.B. von 1.0.0 auf 1.1.0), MUSS `IssueDB._load_or_init`
  einen explicit migration-step haben. Kein auto-magic.

- **KEIN file-locking ohne flock.** POSIX `fcntl.flock` ist MANDATORY
  fuer concurrent im-finder/rank/validator. `threading.Lock` reicht
  nicht (跨-prozess nicht safe).

- **KEIN atomic-write ohne fsync.** `open(tmp, "w")` ohne `fsync`
  kann nach `rename` zu leerer datei fuehren bei crash. Siehe
  `IssueDB.save()` in PHASE 1.4.

- **KEIN issue-db in `.state/`.** Per convention (.mase = persistent
  evidence, .state = transient+framework). Falscher ort = gitignored,
  unsichtbar fuer naechste runs.

- **KEIN willkürliches status-field.** Status muss in {open, fixed,
  wontfix, false_positive}. Andere strings brechen die rank-filter
  (PHASE 3.2) und summary-computation (PHASE 1.4).

- **KEIN mass-bulk-import ohne review.** PHASE 7 ist eine einmalige
  aktion. WIEDERHOLTE bulk-imports von verschiedenen R-runs ohne
  manuelle review fuehren zu duplikat-hashes (selber scanner-emit
  aus 2 runs, aber kein dedup-auf-source-file).

- **KEIN wontfix ohne reason.** Empty reason ist invariant-violation
  und wird abgelehnt (PHASE 1.4, `mark_wontfix` raises ValueError).
  User kann jederzeit via CLI `python3 dev_issue_db.py mark-wontfix
  <hash> --reason "..."` manuell markieren.

- **KEIN mark-fixed ohne commit_sha.** `mark_fixed(commit_sha=...)`
  muss real commit-sha sein. Wenn apply-success aber commit-noch-nicht-
  gepusht, uebergebe `commit_sha="<local-sha>"` (40 hex chars). Wenn
  apply-failed, NICHT mark-fixed (status bleibt open + record_validation).

- **KEIN direct edits in mas-engineer code.** Per im-pipeline rule
  (R110-77/R110-78 + mas-engineer-workflow skill): Hermes writes
  directives, mas-engineer applies them via im-pipeline. Die
  6 PHASEN hier sind spec-packages, die der im-designer als input
  bekommt und in mas-engineer code umsetzt. Hermes schreibt NICHT
  `dev_im_finder_scan.py` direkt.

================================================================
AKZEPTANZ-KRITERIEN (UEBERSICHT)
================================================================

| # | Kriterium | Wie verifizieren |
|---|---|---|
| 1 | `dev_issue_db.py` exists, public API matches PHASE 1.4 | `python3 -c "from dev_issue_db import IssueDB, compute_issue_hash"` exit 0 |
| 2 | `test_dev_issue_db.py` hat 15 tests, alle PASS | `pytest tests/test_dev_issue_db.py -v` exit 0 |
| 3 | `dev_im_finder_scan.py` emittiert `issue_hash` auf jedem finding | grep `issue_hash` in scanner + 8 tests pass |
| 4 | `sub_mas-im-rank` STEP 1.4 added, filter-by-status works | rank recipe references + 5 tests pass |
| 5 | `sub_mas-im-designer` STEP 0.5b + 1.5 added, records design | designer recipe references + 4 tests pass |
| 6 | `sub_mas-im-validator` STEP 0.5c + 0.5d added, marks fixed/records outcome | validator recipe references + 5 tests pass |
| 7 | `sub_mas-general-improver` STEP 2.7 added, wontfix-action works | improver recipe references + 6 tests pass |
| 8 | `dev_issue_db_bulk_import.py` exists, imports R110-24 findings | script + 3 tests pass |
| 9 | Total pytest growth: 1544 → 1590 (+46) | `pytest --collect-only -q` count |
| 10 | R110-178 e2e: 5/5 phases PASS, 0 patches, issue-db preserved | full goose run + git log + db diff |
| 11 | Counter-test: 1 file change → 1 new issue in db, dedup works | manual test with real scanner + db check |

================================================================
STATUS
================================================================

OPEN. 8 PHASEN, no implementation yet.

| PHASE | DIREKTIVE | Status | Commit | Effekt |
|---|---|---|---|---|
| 1 | tools/dev_issue_db.py + 15 tests | OPEN | (TBD) | Issue-DB library + schema + API + tests |
| 2 | dev_im_finder_scan.py: hash + dedup + 8 tests | OPEN | (TBD) | scanner emittiert issue_hash, dedup-gegen-db |
| 3 | sub_mas-im-rank.md STEP 1.4 + 5 tests | OPEN | (TBD) | rank filtert fixed/wontfix/false_positive raus |
| 4 | sub_mas-im-designer.md STEP 0.5b + 1.5 + 4 tests | OPEN | (TBD) | designer speichert verdict + patch in db |
| 5 | sub_mas-im-validator.md STEP 0.5c + 0.5d + 5 tests | OPEN | (TBD) | validator markiert fixed, recorded outcome |
| 6 | sub_mas-general-improver.md STEP 2.7 + 6 tests | OPEN | (TBD) | interactive wontfix-prompt mit reason-validation |
| 7 | dev_issue_db_bulk_import.py + R110-24 import + 3 tests | OPEN | (TBD) | initial-bulk: 1690 R110-24 findings in db |
| 8 | R110-178 e2e verification: 5/5 phases + counter-test | OPEN | (TBD) | proof-of-fix: 0 patches (dedup works), 1-new-issue-on-change works |

**OUT OF SCOPE (R110-177):**
- KEIN auto-wontfix (future R110-180+)
- KEIN un-wontfix (future R110-180+)
- KEIN UI/Dashboard fuer issue-db (R110-185+, separate directive)
- KEIN cross-run analytics (R110-190+, separate)
- KEIN other evidence-archive migration (patches.yaml/validation.yaml
  bleiben unveraendert, issue-db ist ZUSAETZLICH persistent layer)

**Expected effect (post-R110-177):**
- R110-178 e2e (next run after applied): 0 new findings, 0 patches
  (because all R110-176 issues are now known)
- R110-179 e2e (after 1 week of normal commits): ~5-20 new findings
  (real issues from new code), much higher patch-yield than R110-176
- R110-180+ e2e (over time): wontfix-list grows, signal becomes clearer,
  top-10 = echte issues with high patch-success probability
