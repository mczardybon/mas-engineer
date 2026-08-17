"""R110-177 PHASE 7 tests: bulk-import tool (tools/dev_issue_db_bulk_import.py).

Spec: .mase/directives/R110-177-im-pipeline-issue-db.md PHASE 7.4 (3 tests).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
BULK = REPO_ROOT / "tools" / "dev_issue_db_bulk_import.py"


def _run_bulk(source, db_path, tmp_path):
    r = subprocess.run(
        [sys.executable, str(BULK), "--source", str(source),
         "--db", str(db_path)],
        capture_output=True, text=True, timeout=60, cwd=str(tmp_path))
    assert r.returncode == 0, f"bulk-import failed: {r.stderr[-500:]}"
    return r.stdout


# ---------- 1. creates db from findings yaml ----------

def test_bulk_import_creates_db_from_findings_yaml(tmp_path):
    src = tmp_path / "findings.yaml"
    src.write_text(
        "stage: 1\nagent: im-finder\ndata:\n  findings:\n"
        "  - id: F-001\n    type: NN1\n    severity: medium\n"
        "    file: recipe/sub/sub_mas-foo.yaml\n    issue: multi-role\n"
        "    fix: split\n"
        "  - id: F-002\n    type: K1\n    severity: medium\n"
        "    file: recipe/sub/sub_mas-bar.yaml\n    issue: no try/except\n"
        "    fix: wrap\n")
    dbp = tmp_path / "issue_db.json"
    out = _run_bulk(src, dbp, tmp_path)
    assert "registered 2 issues" in out
    data = json.loads(dbp.read_text())
    assert data["summary"]["total_issues"] == 2
    assert data["summary"]["by_status"]["open"] == 2
    types = data["summary"]["by_type"]
    assert types["NN1"] == 1 and types["K1"] == 1
    # all issues carry the bulk-import instance context
    for h, issue in data["issues"].items():
        assert issue["instances"][0]["context"] == "bulk-import"
        assert issue["status"] == "open"


# ---------- 2. handles missing fields ----------

def test_bulk_import_handles_missing_fields(tmp_path):
    src = tmp_path / "findings.yaml"
    src.write_text(
        "data:\n  findings:\n"
        "  - id: F-001\n    type: NN1\n    severity: medium\n"
        "    file: recipe/sub/a.yaml\n    issue: x\n    fix: y\n"
        "  - id: F-002\n    severity: medium\n    issue: no type\n"  # no type/file
        "  - id: F-003\n    type: K1\n    issue: no file\n")          # no file
    dbp = tmp_path / "issue_db.json"
    out = _run_bulk(src, dbp, tmp_path)
    assert "registered 1 issues" in out, out
    assert "skipped 2" in out, out
    data = json.loads(dbp.read_text())
    assert data["summary"]["total_issues"] == 1


# ---------- 3. idempotent re-run ----------

def test_bulk_import_idempotent(tmp_path):
    src = tmp_path / "findings.yaml"
    src.write_text(
        "data:\n  findings:\n"
        "  - id: F-001\n    type: NN1\n    severity: medium\n"
        "    file: recipe/sub/sub_mas-foo.yaml\n    issue: multi-role\n"
        "    fix: split\n")
    dbp = tmp_path / "issue_db.json"
    out1 = _run_bulk(src, dbp, tmp_path)
    out2 = _run_bulk(src, dbp, tmp_path)
    assert "registered 1 issues" in out1
    assert "registered 0 issues" in out2  # re-run produces 0 new entries (7.5)
    data = json.loads(dbp.read_text())
    assert data["summary"]["total_issues"] == 1, \
        "re-running bulk-import must not duplicate issues"
    # instance_count stays 1 (bulk-import dedups at the script level)
    issue = next(iter(data["issues"].values()))
    assert issue["instance_count"] == 1
