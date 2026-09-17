"""R110-177 PHASE 2 tests: scanner issue-hash + dedup against Issue-DB.

Spec: .mase/directives/R110-177-im-pipeline-issue-db.md PHASE 2.6 (8 tests).

All scanner runs use a synthetic minimal recipe dir + a tempfile issue-db
(never the real .mase/pipeline/issue_db.json), keeping runs fast and
deterministic.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
SCANNER = REPO_ROOT / "tools" / "dev_im_finder_scan.py"

sys.path.insert(0, str(REPO_ROOT / "tools"))


def _make_scope(tmp_path):
    """Synthetic recipe dir that deterministically triggers scanner findings.

    A minimal yaml missing prompt/instructions/constitution/description
    triggers MM2, MM3, H1, Q1 (several) — enough to exercise dedup.
    """
    d = tmp_path / "recipes"
    d.mkdir()
    (d / "bad_agent.yaml").write_text(
        "about: test\nname: bad_agent\nversion: '1.0'\n")
    return d


def _run_scanner(cwd, *args, timeout=120):
    r = subprocess.run(
        [sys.executable, str(SCANNER), *args],
        capture_output=True, text=True, timeout=timeout, cwd=str(cwd))
    assert r.returncode == 0, f"scanner failed: {r.stderr[-500:]}"
    out = r.stdout
    assert "---JSON_START---" in out
    j = json.loads(out.split("---JSON_START---")[1])
    return j


# ---------- 1. issue_hash on every finding ----------

def test_finder_emits_issue_hash_field(tmp_path):
    d = _make_scope(tmp_path)
    j = _run_scanner(tmp_path, f"--scope={d.name}")
    assert len(j["findings"]) >= 1, "synthetic scope must emit findings"
    for f in j["findings"]:
        assert "issue_hash" in f, f"finding {f['id']} missing issue_hash"
        assert f["issue_hash"].startswith("sha256:")
        assert "structural_pattern" in f


# ---------- 2. dedup against existing db ----------

def test_finder_dedup_against_existing_db(tmp_path):
    d = _make_scope(tmp_path)
    dbp = tmp_path / "issue_db.json"
    # run 1: populate db, emit all
    j1 = _run_scanner(tmp_path, f"--scope={d.name}",
                      f"--issue-db={dbp}")
    assert len(j1["findings"]) >= 1
    db = json.loads(dbp.read_text())
    h = next(iter(db["issues"]))
    before = db["issues"][h]["instance_count"]
    # run 2: re-run, finding X must NOT be re-emitted; instance_count +1
    j2 = _run_scanner(tmp_path, f"--scope={d.name}",
                      f"--issue-db={dbp}")
    hashes2 = {f["issue_hash"] for f in j2["findings"]}
    assert h not in hashes2, "known open issue must not be re-emitted"
    db2 = json.loads(dbp.read_text())
    assert db2["issues"][h]["instance_count"] == before + 1


# ---------- 3. skip fixed ----------

def test_finder_skips_fixed_issues(tmp_path):
    from dev_issue_db import IssueDB
    d = _make_scope(tmp_path)
    dbp = tmp_path / "issue_db.json"
    _run_scanner(tmp_path, f"--scope={d.name}", f"--issue-db={dbp}")
    db = IssueDB(str(dbp))
    h = db.list_open()[0]
    db.mark_fixed(h, "abc1234")
    db.save()
    j = _run_scanner(tmp_path, f"--scope={d.name}", f"--issue-db={dbp}")
    hashes = {f["issue_hash"] for f in j["findings"]}
    assert h not in hashes, "fixed issue must not be emitted"


# ---------- 4. skip wontfix ----------

def test_finder_skips_wontfix_issues(tmp_path):
    from dev_issue_db import IssueDB
    d = _make_scope(tmp_path)
    dbp = tmp_path / "issue_db.json"
    _run_scanner(tmp_path, f"--scope={d.name}", f"--issue-db={dbp}")
    db = IssueDB(str(dbp))
    h = db.list_open()[0]
    db.mark_wontfix(h, "explicitly declined by operator review")
    db.save()
    j = _run_scanner(tmp_path, f"--scope={d.name}", f"--issue-db={dbp}")
    hashes = {f["issue_hash"] for f in j["findings"]}
    assert h not in hashes, "wontfix issue must not be emitted"


# ---------- 5/6. structural pattern generation ----------

def test_finder_structural_pattern_k1():
    from dev_issue_db import compute_structural_pattern
    pat = compute_structural_pattern("K1", "recipe/sub/sub_mas-foo.yaml",
                                     line_start=38, line_end=42)
    assert pat == "k1:38-42"


def test_finder_structural_pattern_nn1():
    from dev_issue_db import compute_structural_pattern
    pat = compute_structural_pattern("NN1", "recipe/sub/sub_mas-foo.yaml",
                                     roles=["analyze", "validate"])
    # roles are sorted: validate before analyze alphabetically? no —
    # sorted(["analyze","validate"]) = ["analyze","validate"]
    assert pat == "multi_role:2:analyze,validate"
    # order-insensitive: reversed input gives same pattern
    pat2 = compute_structural_pattern("NN1", "recipe/sub/sub_mas-foo.yaml",
                                      roles=["validate", "analyze"])
    assert pat2 == pat


# ---------- 7. atomic db save ----------

def test_finder_atomic_db_save(tmp_path):
    d = _make_scope(tmp_path)
    dbp = tmp_path / "issue_db.json"
    _run_scanner(tmp_path, f"--scope={d.name}", f"--issue-db={dbp}")
    # db is valid JSON after scanner run
    data = json.loads(dbp.read_text())
    assert data["schema_version"] == "1.0.0"
    # simulate crash mid-write: partial .tmp file must not corrupt db path
    dbp.with_name(dbp.name + ".tmp").write_text('{"partial":')
    assert json.loads(dbp.read_text()) is not None
    # scanner re-run after "crash" still works (ignores stray .tmp)
    j = _run_scanner(tmp_path, f"--scope={d.name}", f"--issue-db={dbp}")
    assert len(j["findings"]) == 0  # all known


# ---------- 8. preserve history ----------

def test_finder_preserves_history(tmp_path):
    from dev_issue_db import IssueDB
    d = _make_scope(tmp_path)
    dbp = tmp_path / "issue_db.json"
    _run_scanner(tmp_path, f"--scope={d.name}", f"--issue-db={dbp}")
    db = IssueDB(str(dbp))
    h = db.list_open()[0]
    for i in range(3):
        db.record_design(
            issue_hash=h, patch={"file": "x", "field": "y"},
            goose_verdict="CONFORM", verdict_explanation="ok",
            design_run_id=f"run-{i}")
    db.save()
    assert len(db.get(h)["past_designs"]) == 3
    # re-run scanner: register must NOT clear past_designs
    _run_scanner(tmp_path, f"--scope={d.name}", f"--issue-db={dbp}")
    db2 = IssueDB(str(dbp))
    assert len(db2.get(h)["past_designs"]) == 3, \
        "past_designs must be preserved across scanner runs"
