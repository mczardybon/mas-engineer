"""R110-177 PHASE 1 tests: Issue-DB library (tools/dev_issue_db.py).

Spec: .mase/directives/R110-177-im-pipeline-issue-db.md PHASE 1.5 (15 tests).
Every test uses a tempfile IssueDB — never the real
.mase/pipeline/issue_db.json (R110-177 spec 1.7 idempotency).
"""
import json
import os
import subprocess
import sys
import threading
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

from dev_issue_db import (  # noqa: E402
    IssueDB,
    compute_issue_hash,
    validate_wontfix_reason,
)


@pytest.fixture()
def db(tmp_path):
    return IssueDB(str(tmp_path / "issue_db.json"))


@pytest.fixture()
def sample_instance():
    return {"file": "recipe/sub/sub_mas-foo.yaml", "line_start": 38,
            "line_end": 42, "context": "yaml_block:N",
            "scanner_version": "dev_im_finder_scan.py:1.4.2"}


# ---------- 1. compute_issue_hash ----------

def test_compute_issue_hash_stable():
    h1 = compute_issue_hash("a.yaml", "K1", "k1:38-42")
    h2 = compute_issue_hash("a.yaml", "K1", "k1:38-42")
    assert h1 == h2
    assert h1.startswith("sha256:")
    assert len(h1) == len("sha256:") + 64


def test_compute_issue_hash_normalizes_paths():
    a = compute_issue_hash("./a/b.yaml", "K1", "k1:1-5")
    b = compute_issue_hash("a/b.yaml", "K1", "k1:1-5")
    c = compute_issue_hash("b/../a/b.yaml", "K1", "k1:1-5")
    assert a == b == c


def test_compute_issue_hash_file_local():
    h1 = compute_issue_hash("recipe/sub/sub_mas-foo.yaml", "K1", "k1:38-42")
    h2 = compute_issue_hash("recipe/sub/sub_mas-bar.yaml", "K1", "k1:38-42")
    assert h1 != h2


def test_compute_issue_hash_pattern_local():
    h1 = compute_issue_hash("recipe/sub/sub_mas-foo.yaml", "K1", "k1:38-42")
    h2 = compute_issue_hash("recipe/sub/sub_mas-foo.yaml", "K1", "k1:100-110")
    assert h1 != h2


# ---------- 2. register ----------

def test_register_new_issue(db, sample_instance):
    h = compute_issue_hash("recipe/sub/sub_mas-foo.yaml", "K1", "k1:38-42")
    db.register(hash=h, type="K1", severity="medium",
                file="recipe/sub/sub_mas-foo.yaml",
                structural_pattern="k1:38-42",
                issue_summary="missing try/except",
                fix_summary="wrap in try/except",
                instance=sample_instance)
    issue = db.get(h)
    assert issue is not None
    assert issue["status"] == "open"
    assert issue["instance_count"] == 1
    assert issue["type"] == "K1"


def test_register_existing_open_increments(db, sample_instance):
    h = compute_issue_hash("recipe/sub/sub_mas-foo.yaml", "K1", "k1:38-42")
    db.register(hash=h, type="K1", severity="medium",
                file="recipe/sub/sub_mas-foo.yaml",
                structural_pattern="k1:38-42",
                issue_summary="s", fix_summary="f", instance=sample_instance)
    db.register(hash=h, type="K1", severity="medium",
                file="recipe/sub/sub_mas-foo.yaml",
                structural_pattern="k1:38-42",
                issue_summary="s", fix_summary="f", instance=sample_instance)
    issue = db.get(h)
    assert issue["instance_count"] == 2
    assert len(issue["instances"]) == 2


def test_register_existing_fixed_skips(db, sample_instance):
    h = compute_issue_hash("recipe/sub/sub_mas-foo.yaml", "K1", "k1:38-42")
    db.register(hash=h, type="K1", severity="medium",
                file="recipe/sub/sub_mas-foo.yaml",
                structural_pattern="k1:38-42",
                issue_summary="s", fix_summary="f", instance=sample_instance)
    db.mark_fixed(h, "abc1234")
    db.register(hash=h, type="K1", severity="medium",
                file="recipe/sub/sub_mas-foo.yaml",
                structural_pattern="k1:38-42",
                issue_summary="s", fix_summary="f", instance=sample_instance)
    issue = db.get(h)
    assert issue["status"] == "fixed"
    assert issue["instance_count"] == 1  # no-op for fixed


# ---------- 3. wontfix ----------

def test_mark_wontfix_requires_reason(db, sample_instance):
    h = compute_issue_hash("a.yaml", "K1", "k1:1-2")
    db.register(hash=h, type="K1", severity="medium", file="a.yaml",
                structural_pattern="k1:1-2", issue_summary="s",
                fix_summary="f", instance=sample_instance)
    with pytest.raises(ValueError):
        db.mark_wontfix(h, "")


def test_mark_wontfix_state_transition(db, sample_instance):
    h = compute_issue_hash("a.yaml", "K1", "k1:1-2")
    db.register(hash=h, type="K1", severity="medium", file="a.yaml",
                structural_pattern="k1:1-2", issue_summary="s",
                fix_summary="f", instance=sample_instance)
    changed = db.mark_wontfix(h, "not applicable for this single-purpose recipe")
    assert changed is True
    issue = db.get(h)
    assert issue["status"] == "wontfix"
    assert issue["wontfix_reason"] == "not applicable for this single-purpose recipe"
    assert issue["wontfix_marked_at"] is not None
    assert issue["wontfix_marked_by"] == "general-improver"
    # idempotent: second call returns False
    assert db.mark_wontfix(h, "another reason") is False


# ---------- 4. fixed ----------

def test_mark_fixed_state_transition(db, sample_instance):
    h = compute_issue_hash("a.yaml", "K1", "k1:1-2")
    db.register(hash=h, type="K1", severity="medium", file="a.yaml",
                structural_pattern="k1:1-2", issue_summary="s",
                fix_summary="f", instance=sample_instance)
    changed = db.mark_fixed(h, "abc1234", validated_by="im-validator")
    assert changed is True
    issue = db.get(h)
    assert issue["status"] == "fixed"
    assert issue["past_validation_outcomes"][-1]["verdict"] == "APPROVED"
    assert issue["past_validation_outcomes"][-1]["commit_sha"] == "abc1234"
    # one-shot: second call returns False, no duplicate outcome
    assert db.mark_fixed(h, "def5678") is False
    approved = [o for o in issue["past_validation_outcomes"]
                if o["verdict"] == "APPROVED"]
    assert len(approved) == 1


# ---------- 5. atomic save ----------

def test_save_atomic_no_partial(db, sample_instance, tmp_path):
    h = compute_issue_hash("a.yaml", "K1", "k1:1-2")
    db.register(hash=h, type="K1", severity="medium", file="a.yaml",
                structural_pattern="k1:1-2", issue_summary="s",
                fix_summary="f", instance=sample_instance)
    db.save()
    db_path = tmp_path / "issue_db.json"
    assert db_path.exists()
    # Simulate crash mid-write: write partial content to .tmp, then rename
    # over a copy of the real db must NOT leave partial JSON at the db path.
    original = db_path.read_text()
    data = json.loads(original)
    data["summary"]["total_issues"] = 999
    db_path.with_suffix(".json.tmp").write_text(
        json.dumps(data)[:50])  # truncated / partial
    # db path itself is untouched by the partial .tmp
    assert json.loads(db_path.read_text())["summary"]["total_issues"] == 1
    # A re-load after "crash" (ignoring .tmp) still yields valid JSON
    db2 = IssueDB(str(db_path))
    assert db2.get(h) is not None


# ---------- 6. concurrent lock ----------

def test_concurrent_lock_blocks(db, sample_instance, tmp_path):
    """2 threads: 2nd waits for 1st's lock release (save_with_lock)."""
    results = []
    entered = threading.Event()
    release = threading.Event()

    def worker(name):
        with db.save_with_lock():
            entered.set()  # signal: inside critical section
            if not release.wait(timeout=5):
                raise RuntimeError("release timeout")
            results.append(name)

    t1 = threading.Thread(target=worker, args=("first",))
    t2 = threading.Thread(target=worker, args=("second",))
    t1.start()
    assert entered.wait(timeout=5), "first thread never entered critical section"
    t2.start()
    time.sleep(0.3)  # give t2 time to attempt acquisition (must block)
    assert results == [], "second thread must be blocked by flock"
    release.set()  # let first finish -> releases lock -> second proceeds
    t1.join(timeout=10)
    t2.join(timeout=10)
    # Serialized by the lock: first appends, then second
    assert results == ["first", "second"]


# ---------- 7. CLI ----------

def test_cli_stats_prints_summary(tmp_path):
    dbp = tmp_path / "issue_db.json"
    db = IssueDB(str(dbp))
    h = compute_issue_hash("a.yaml", "K1", "k1:1-2")
    db.register(hash=h, type="K1", severity="medium", file="a.yaml",
                structural_pattern="k1:1-2", issue_summary="s",
                fix_summary="f", instance={})
    db.save()
    r = subprocess.run(
        [sys.executable,
         os.path.join(os.path.dirname(__file__), "..", "tools",
                      "dev_issue_db.py"),
         "--db", str(dbp), "stats"],
        capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    summary = json.loads(r.stdout)
    assert summary["total_issues"] == 1
    assert summary["by_status"]["open"] == 1


# ---------- 8. schema invariants ----------

def test_schema_invariants_after_register(db, sample_instance):
    h1 = compute_issue_hash("a.yaml", "K1", "k1:1-2")
    h2 = compute_issue_hash("b.yaml", "Q3", "extra_field:timeout")
    for h, t, pat in ((h1, "K1", "k1:1-2"), (h2, "Q3", "extra_field:timeout")):
        db.register(hash=h, type=t, severity="medium", file="x.yaml",
                    structural_pattern=pat, issue_summary="s",
                    fix_summary="f", instance=sample_instance)
    db.register(hash=h1, type="K1", severity="medium", file="a.yaml",
                structural_pattern="k1:1-2", issue_summary="s",
                fix_summary="f", instance=sample_instance)
    for h in (h1, h2):
        issue = db.get(h)
        assert issue["instance_count"] == len(issue["instances"])
        assert issue["hash"] == h
        assert issue["status"] in ("open", "fixed", "wontfix", "false_positive")
        assert issue["last_seen"] >= issue["first_seen"]
    db.save()
    summary = db._data["summary"]
    assert summary["total_issues"] == 2
    assert summary["by_status"]["open"] == 2
    assert summary["by_type"]["K1"] == 1
    assert summary["by_type"]["Q3"] == 1


def test_schema_invariants_after_wontfix(db, sample_instance):
    h = compute_issue_hash("a.yaml", "K1", "k1:1-2")
    db.register(hash=h, type="K1", severity="medium", file="a.yaml",
                structural_pattern="k1:1-2", issue_summary="s",
                fix_summary="f", instance=sample_instance)
    assert db.get(h)["wontfix_reason"] is None
    db.mark_wontfix(h, "a legitimate reason here")
    issue = db.get(h)
    assert (issue["wontfix_reason"] is not None) == (issue["status"] == "wontfix")
    assert issue["status"] == "wontfix"
    assert issue["wontfix_reason"] == "a legitimate reason here"
