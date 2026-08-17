"""R110-177 PHASE 5 tests: im-validator marks fixed / records outcome in
Issue-DB (STEP 0.5c + 0.5d).

Spec: .mase/directives/R110-177-im-pipeline-issue-db.md PHASE 5.4 (5 tests).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

from dev_issue_db import IssueDB, compute_issue_hash  # noqa: E402


def _mk_issue(tmp_path, ftype="K1", file="recipe/sub/sub_mas-foo.yaml"):
    db = IssueDB(str(tmp_path / "issue_db.json"))
    h = compute_issue_hash(file, ftype, f"{ftype.lower()}:38-42")
    db.register(hash=h, type=ftype, severity="medium", file=file,
                structural_pattern=f"{ftype.lower()}:38-42",
                issue_summary="issue", fix_summary="fix", instance={})
    db.save()
    return db, h


# ---------- 1. APPROVED -> fixed ----------

def test_validator_approved_marks_fixed(tmp_path):
    db, h = _mk_issue(tmp_path)
    db.mark_fixed(h, "abc1234", validated_by="im-validator")
    db.save()
    issue = IssueDB(str(tmp_path / "issue_db.json")).get(h)
    assert issue["status"] == "fixed"
    assert issue["past_validation_outcomes"][-1]["verdict"] == "APPROVED"


# ---------- 2. REJECTED -> stays open ----------

def test_validator_rejected_keeps_open(tmp_path):
    db, h = _mk_issue(tmp_path)
    db.record_validation(h, "REJECTED", "timeout value out of range",
                         validated_by="im-validator")
    db.save()
    issue = IssueDB(str(tmp_path / "issue_db.json")).get(h)
    assert issue["status"] == "open"
    outcomes = issue["past_validation_outcomes"]
    assert outcomes[-1]["verdict"] == "REJECTED"
    assert outcomes[-1]["reason"] == "timeout value out of range"


# ---------- 3. coronashield reason ----------

def test_validator_records_coronashield_reason(tmp_path):
    db, h = _mk_issue(tmp_path)
    pv = {"issue_hash": h, "verdict": "REJECTED",
          "rejection_source": "coronashield:R10",
          "reason": "R10 requires yaml.safe_load validation first"}
    if pv.get("rejection_source", "").startswith("coronashield"):
        db.record_validation(h, "SKIPPED",
                             f"coronashield:{pv['rejection_source']}:"
                             f"{pv.get('reason', '')}",
                             validated_by="im-validator")
    db.save()
    issue = IssueDB(str(tmp_path / "issue_db.json")).get(h)
    reason = issue["past_validation_outcomes"][-1]["reason"]
    assert "coronashield:R10" in reason
    assert issue["status"] == "open"  # blocked, not fixed


# ---------- 4. commit_sha on approved ----------

def test_validator_records_commit_sha_on_approved(tmp_path):
    db, h = _mk_issue(tmp_path)
    db.mark_fixed(h, "9f86d081884c7d659a2feaa0c55ad015", validated_by="im-validator")
    db.save()
    issue = IssueDB(str(tmp_path / "issue_db.json")).get(h)
    outcome = issue["past_validation_outcomes"][-1]
    assert outcome["verdict"] == "APPROVED"
    assert outcome["commit_sha"] == "9f86d081884c7d659a2feaa0c55ad015"


# ---------- 5. SKIPPED -> stays open ----------

def test_validator_skipped_keeps_open(tmp_path):
    db, h = _mk_issue(tmp_path)
    db.record_validation(h, "SKIPPED", "patch superseded by newer design",
                         validated_by="im-validator")
    db.save()
    issue = IssueDB(str(tmp_path / "issue_db.json")).get(h)
    assert issue["status"] == "open"
    assert issue["past_validation_outcomes"][-1]["verdict"] == "SKIPPED"
