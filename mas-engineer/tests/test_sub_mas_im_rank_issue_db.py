"""R110-177 PHASE 3 tests: im-rank STEP 1.4 issue-db status filter.

Spec: .mase/directives/R110-177-im-pipeline-issue-db.md PHASE 3.4 (5 tests).
The rank filter logic (STEP 1.4) is implemented by
`IssueDB.filter_findings()` in tools/dev_issue_db.py — these tests
validate the recipe's described behavior against that helper.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

from dev_issue_db import IssueDB, compute_issue_hash  # noqa: E402


def _mk_finding(fid, ftype, file, severity="medium"):
    pat = f"{ftype.lower()}:1-5"
    return {
        "id": fid,
        "type": ftype,
        "severity": severity,
        "file": file,
        "issue": f"{ftype} issue",
        "impact": "impact",
        "fix": "fix",
        "issue_hash": compute_issue_hash(file, ftype, pat),
        "structural_pattern": pat,
    }


def _mk_db(tmp_path, statuses):
    """statuses: list of (status, finding) tuples."""
    db = IssueDB(str(tmp_path / "issue_db.json"))
    for st, f in statuses:
        h = f["issue_hash"]
        db.register(hash=h, type=f["type"], severity=f["severity"],
                    file=f["file"],
                    structural_pattern=f["structural_pattern"],
                    issue_summary=f["issue"], fix_summary=f["fix"],
                    instance={})
        if st == "fixed":
            db.mark_fixed(h, "abc1234")
        elif st == "wontfix":
            db.mark_wontfix(h, "explicitly declined by operator review")
        elif st == "false_positive":
            issue = db.get(h)
            issue["status"] = "false_positive"
    db.save()
    return db


# ---------- 1/2. status filtering ----------

def test_rank_filters_fixed(tmp_path):
    new1 = _mk_finding("F-001", "K1", "recipe/sub/a.yaml")
    new2 = _mk_finding("F-002", "K3", "recipe/sub/b.yaml")
    fixed1 = _mk_finding("F-003", "L1", "recipe/sub/c.yaml")
    _mk_db(tmp_path, [("fixed", fixed1)])
    db = IssueDB(str(tmp_path / "issue_db.json"))
    kept, dropped = db.filter_findings([new1, new2, fixed1])
    assert dropped == 1
    assert {f["id"] for f in kept} == {"F-001", "F-002"}
    assert fixed1["id"] not in {f["id"] for f in kept}


def test_rank_filters_wontfix(tmp_path):
    new1 = _mk_finding("F-001", "K1", "recipe/sub/a.yaml")
    wont1 = _mk_finding("F-002", "NN1", "recipe/sub/b.yaml")
    wont2 = _mk_finding("F-003", "NN2", "recipe/sub/c.yaml")
    _mk_db(tmp_path, [("wontfix", wont1), ("wontfix", wont2)])
    db = IssueDB(str(tmp_path / "issue_db.json"))
    kept, dropped = db.filter_findings([new1, wont1, wont2])
    assert dropped == 2
    assert [f["id"] for f in kept] == ["F-001"]


# ---------- 3. filtered count ----------

def test_rank_logs_issue_db_filtered_count(tmp_path):
    findings = [_mk_finding(f"F-{i:03d}", t, f"recipe/sub/f{i}.yaml")
                for i, t in enumerate(["K1", "K3", "L1", "Q3", "U1"])]
    # 2 of 5 are fixed
    _mk_db(tmp_path, [("fixed", findings[1]), ("fixed", findings[3])])
    db = IssueDB(str(tmp_path / "issue_db.json"))
    kept, dropped = db.filter_findings(findings)
    assert dropped == 2
    assert len(kept) == 3
    # the count is what STEP 1.4 logs as issue_db_filtered
    assert dropped == 2


# ---------- 4. issue_hash pass-through ----------

def test_rank_passes_through_issue_hash(tmp_path):
    findings = [_mk_finding("F-001", "K1", "recipe/sub/a.yaml")]
    _mk_db(tmp_path, [])
    db = IssueDB(str(tmp_path / "issue_db.json"))
    kept, _ = db.filter_findings(findings)
    assert len(kept) == 1
    assert kept[0]["issue_hash"].startswith("sha256:")
    assert kept[0]["issue_hash"] == findings[0]["issue_hash"]


# ---------- 5. missing hash -> keep + warn ----------

def test_rank_handles_missing_hash(tmp_path):
    db = IssueDB(str(tmp_path / "issue_db.json"))
    no_hash = {"id": "F-001", "type": "K1", "severity": "medium",
               "file": "recipe/sub/a.yaml", "issue": "x", "impact": "y",
               "fix": "z"}  # no issue_hash
    kept, dropped = db.filter_findings([no_hash])
    assert dropped == 0
    assert len(kept) == 1, "finding without issue_hash must be kept (defensive)"
