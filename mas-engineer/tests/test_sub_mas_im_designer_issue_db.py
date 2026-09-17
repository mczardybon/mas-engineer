"""R110-177 PHASE 4 tests: im-designer records verdict (STEP 0.5b) + patch
(STEP 1.4) in Issue-DB.

Spec: .mase/directives/R110-177-im-pipeline-issue-db.md PHASE 4.4 (4 tests).
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

from dev_issue_db import IssueDB, compute_issue_hash  # noqa: E402


def _mk_db_with_issue(tmp_path):
    db = IssueDB(str(tmp_path / "issue_db.json"))
    h = compute_issue_hash("recipe/sub/sub_mas-foo.yaml", "K1", "k1:38-42")
    db.register(hash=h, type="K1", severity="medium",
                file="recipe/sub/sub_mas-foo.yaml",
                structural_pattern="k1:38-42",
                issue_summary="missing try/except",
                fix_summary="wrap in try/except",
                instance={})
    db.save()
    return db, h


def _record_verdict(db, h, run_id, verdict="CONFORM"):
    db.record_design(
        issue_hash=h,
        patch={},  # STEP 0.5b: no patch yet
        goose_verdict=verdict,
        verdict_explanation="Goose accepts per-recipe override",
        design_run_id=run_id,
    )
    db.save()


def test_designer_records_verdict_at_step_0_5b(tmp_path):
    db, h = _mk_db_with_issue(tmp_path)
    _record_verdict(db, h, "run-1")
    issue = IssueDB(str(tmp_path / "issue_db.json")).get(h)
    assert len(issue["past_designs"]) == 1
    entry = issue["past_designs"][0]
    assert entry["goose_verdict"] == "CONFORM"
    assert entry["patch"] == {}  # empty at STEP 0.5b
    assert entry["design_run_id"] == "run-1"


def test_designer_updates_patch_at_step_1_5(tmp_path):
    db, h = _mk_db_with_issue(tmp_path)
    _record_verdict(db, h, "run-1")
    # STEP 1.4: update the past_design entry with the drafted patch
    issue = db.get(h)
    for entry in issue["past_designs"]:
        if entry.get("design_run_id") == "run-1":
            entry["patch"] = {
                "file": "recipe/sub/sub_mas-foo.yaml",
                "field": "settings.max_turns",
                "from": "5",
                "to": "20",
            }
            break
    db.save()
    issue2 = IssueDB(str(tmp_path / "issue_db.json")).get(h)
    assert issue2["past_designs"][0]["patch"]["field"] == "settings.max_turns"
    assert issue2["past_designs"][0]["patch"]["to"] == "20"


def test_designer_aborts_between_steps_preserves_verdict(tmp_path):
    db, h = _mk_db_with_issue(tmp_path)
    _record_verdict(db, h, "run-1")
    # crash between 0.5b and 1.4: no patch update happens
    # -> db must still contain the verdict-only entry
    issue = IssueDB(str(tmp_path / "issue_db.json")).get(h)
    assert len(issue["past_designs"]) == 1
    assert issue["past_designs"][0]["goose_verdict"] == "CONFORM"
    assert issue["past_designs"][0]["patch"] == {}
    assert issue["status"] == "open"


def test_designer_design_run_id_unique(tmp_path):
    db, h = _mk_db_with_issue(tmp_path)
    run_a = str(uuid.uuid4())
    run_b = str(uuid.uuid4())
    assert run_a != run_b
    _record_verdict(db, h, run_a)
    _record_verdict(db, h, run_b)
    issue = IssueDB(str(tmp_path / "issue_db.json")).get(h)
    assert len(issue["past_designs"]) == 2
    assert issue["past_designs"][0]["design_run_id"] == run_a
    assert issue["past_designs"][1]["design_run_id"] == run_b
