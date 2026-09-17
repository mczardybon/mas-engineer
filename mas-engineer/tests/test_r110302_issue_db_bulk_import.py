"""
test_r110302_issue_db_bulk_import.py — R110-302 Coverage Sprint for
tools/dev_issue_db_bulk_import.py.

Target: dev_issue_db_bulk_import.py (97 lines, 51 stmts).
R110-302 imports the tool as a library and tests:

  - load_findings(path)   (5 tests: yaml ranked_findings layout, json
                          findings layout, data.findings nested layout,
                          non-dict top-level returns [], non-list
                          findings key returns [])
  - main()                (7 tests: no --source → argparse rc=2, empty
                          findings → sys.exit(1) + stderr, basic happy
                          path registers N issues, skipped finding
                          (missing type/file), duplicate hash idempotency
                          (re-import skips duplicates, no double instance
                          count), default --db path, --default-status
                          false_positive choice)
  - __main__ guard        (1 runpy test that executes the script with
                          run_name='__main__' so coverage attributes the
                          `if __name__ == "__main__":` line to this test.)

Total: 13 new tests.

Pitfall (R110-78 cat-3 / R110-302): the tool's `main()` does
`sys.exit(1)` directly when there are no findings, so direct calls to
`mod.main()` raise SystemExit, NOT return 1. We catch SystemExit in
those tests.

Pitfall (R110-177 PHASE 7.5 idempotency): re-importing the same source
must NOT double instance_count. We verify this by re-running main() and
asserting the db still has instance_count=1 for the hash.

Pitfall: dev_issue_db_bulk_import.py imports `from dev_issue_db import
...` AFTER inserting its own dir on sys.path. When WE import it from
tests/, our conftest already puts REPO_ROOT on sys.path so the
underlying `dev_issue_db` module resolves correctly. But because the
tool does `sys.path.insert(0, os.path.dirname(__file__))` at import
time, the import is order-stable regardless.

Pitfall: load_findings() also does `import yaml` lazily. We must have
PyYAML available — it is a hard project dep.
"""
import json
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOL = REPO_ROOT / "tools" / "dev_issue_db_bulk_import.py"
TOOLS_DIR = TOOL.parent


def _import_tool():
    """Import dev_issue_db_bulk_import as a library.

    The module is safe to import (no module-level sys.argv parsing).
    Returns the loaded module.
    """
    sys.path.insert(0, str(TOOLS_DIR))
    if "dev_issue_db_bulk_import" in sys.modules:
        del sys.modules["dev_issue_db_bulk_import"]
    import dev_issue_db_bulk_import
    return dev_issue_db_bulk_import


def _seed_issue_db(db_path: Path) -> None:
    """Write a minimal valid issue_db.json with the right schema."""
    initial = {
        "schema_version": "1.0.0",
        "created_at": "2026-08-28T00:00:00Z",
        "last_modified_at": "2026-08-28T00:00:00Z",
        "last_modified_by": "test_seed",
        "summary": {
            "total_issues": 0,
            "by_status": {"open": 0, "fixed": 0, "wontfix": 0,
                          "false_positive": 0},
            "by_type": {},
        },
        "issues": {},
    }
    db_path.write_text(json.dumps(initial, indent=2))


# ─────────────────────────────────────────────────────────────────────
# load_findings — pure-function tests
# ─────────────────────────────────────────────────────────────────────

def test_load_findings_yaml_ranked_findings_layout(tmp_path):
    """load_findings accepts yaml with top-level `ranked_findings` key."""
    mod = _import_tool()
    src = tmp_path / "findings.yaml"
    src.write_text(
        "ranked_findings:\n"
        "  - id: A1\n"
        "    type: K1\n"
        "    file: recipe/test.yaml\n"
        "    severity: high\n"
        "  - id: A2\n"
        "    type: Q3\n"
        "    file: recipe/test2.yaml\n"
        "    severity: medium\n"
    )
    findings = mod.load_findings(str(src))
    assert isinstance(findings, list)
    assert len(findings) == 2
    assert findings[0]["id"] == "A1"
    assert findings[1]["type"] == "Q3"


def test_load_findings_json_findings_layout(tmp_path):
    """load_findings accepts json with top-level `findings` key."""
    mod = _import_tool()
    src = tmp_path / "findings.json"
    payload = {
        "findings": [
            {"id": "B1", "type": "K1", "file": "x.py"},
            {"id": "B2", "type": "K3", "file": "y.py"},
            {"id": "B3", "type": "NN1", "file": "z.py"},
        ]
    }
    src.write_text(json.dumps(payload))
    findings = mod.load_findings(str(src))
    assert len(findings) == 3
    assert [f["id"] for f in findings] == ["B1", "B2", "B3"]


def test_load_findings_yaml_data_findings_nested_layout(tmp_path):
    """load_findings accepts yaml nested under `data.findings` (R110-24 layout)."""
    mod = _import_tool()
    src = tmp_path / "findings.yaml"
    src.write_text(
        "data:\n"
        "  findings:\n"
        "    - id: C1\n"
        "      type: K1\n"
        "      file: recipe/c1.yaml\n"
        "    - id: C2\n"
        "      type: L1\n"
        "      file: recipe/c2.yaml\n"
    )
    findings = mod.load_findings(str(src))
    assert len(findings) == 2
    assert findings[0]["id"] == "C1"


def test_load_findings_top_level_list_returns_empty(tmp_path):
    """load_findings: non-dict top-level (e.g. a bare list) returns []."""
    mod = _import_tool()
    src = tmp_path / "list_only.yaml"
    src.write_text("- just\n- a\n- list\n")
    findings = mod.load_findings(str(src))
    assert findings == []


def test_load_findings_non_list_findings_key_returns_empty(tmp_path):
    """load_findings: if `findings` key is not a list, returns []."""
    mod = _import_tool()
    src = tmp_path / "bad.yaml"
    src.write_text(
        "findings:\n"
        "  not: a list\n"
        "  but: a dict\n"
    )
    findings = mod.load_findings(str(src))
    assert findings == []


def test_load_findings_no_findings_keys_returns_empty(tmp_path):
    """load_findings: dict with no findings keys → []. (Coverage for else-branch.)"""
    mod = _import_tool()
    src = tmp_path / "empty.yaml"
    src.write_text("metadata:\n  some: thing\n")
    findings = mod.load_findings(str(src))
    assert findings == []


# ─────────────────────────────────────────────────────────────────────
# main() — CLI tests
# ─────────────────────────────────────────────────────────────────────

def test_main_no_source_arg_exits_2(monkeypatch):
    """main() with no --source → argparse exits 2 (argparse SystemExit)."""
    mod = _import_tool()
    monkeypatch.setattr(sys, "argv", ["dev_issue_db_bulk_import.py"])
    with pytest.raises(SystemExit) as excinfo:
        mod.main()
    # argparse exits with 2 on missing required args
    assert excinfo.value.code == 2


def test_main_no_findings_exits_1_with_stderr(
    capsys, monkeypatch, tmp_path
):
    """main() with no findings in source → sys.exit(1) + stderr message."""
    mod = _import_tool()
    src = tmp_path / "empty.yaml"
    src.write_text("metadata:\n  no_findings: true\n")
    db = tmp_path / "issue_db.json"
    _seed_issue_db(db)
    monkeypatch.setattr(
        sys, "argv",
        ["dev_issue_db_bulk_import.py",
         "--source", str(src), "--db", str(db)]
    )
    with pytest.raises(SystemExit) as excinfo:
        mod.main()
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "No findings" in captured.err


def test_main_happy_path_registers_all_issues(
    capsys, monkeypatch, tmp_path
):
    """main() registers each finding, prints summary, saves db."""
    mod = _import_tool()
    src = tmp_path / "findings.yaml"
    src.write_text(
        "findings:\n"
        "  - id: F1\n"
        "    type: K1\n"
        "    file: recipe/r1.yaml\n"
        "    severity: high\n"
        "    issue: missing retry\n"
        "    fix: add try/except\n"
        "  - id: F2\n"
        "    type: Q3\n"
        "    file: recipe/r2.yaml\n"
        "    severity: medium\n"
    )
    db = tmp_path / "issue_db.json"
    _seed_issue_db(db)
    monkeypatch.setattr(
        sys, "argv",
        ["dev_issue_db_bulk_import.py",
         "--source", str(src), "--db", str(db)]
    )
    rc = mod.main()
    assert rc is None  # main() returns None on success (no explicit return)
    captured = capsys.readouterr()
    assert "BULK-IMPORT: registered 2 issues" in captured.out
    assert "skipped 0" in captured.out
    assert "duplicates 0" in captured.out
    # DB now has 2 issues
    db_data = json.loads(db.read_text())
    assert db_data["summary"]["total_issues"] == 2
    assert len(db_data["issues"]) == 2


def test_main_skips_findings_missing_type_or_file(
    capsys, monkeypatch, tmp_path
):
    """main() counts skipped for findings without 'type' or 'file'."""
    mod = _import_tool()
    src = tmp_path / "mixed.yaml"
    src.write_text(
        "findings:\n"
        "  - id: GOOD\n"
        "    type: K1\n"
        "    file: recipe/good.yaml\n"
        "  - id: NOTYPE\n"
        "    file: recipe/notype.yaml\n"
        "  - id: NOFILE\n"
        "    type: Q3\n"
        "  - id: EMPTY\n"
    )
    db = tmp_path / "issue_db.json"
    _seed_issue_db(db)
    monkeypatch.setattr(
        sys, "argv",
        ["dev_issue_db_bulk_import.py",
         "--source", str(src), "--db", str(db)]
    )
    mod.main()
    captured = capsys.readouterr()
    assert "registered 1 issues" in captured.out
    assert "skipped 3" in captured.out
    assert "duplicates 0" in captured.out
    db_data = json.loads(db.read_text())
    assert db_data["summary"]["total_issues"] == 1


def test_main_idempotent_reimport_does_not_double_count(
    capsys, monkeypatch, tmp_path
):
    """main() called twice: second run reports duplicates, db instance_count stays 1.

    This is the R110-177 PHASE 7.5 invariant: re-importing the same
    source must NOT double instance_count. We register the same source
    twice and assert the issue's instance_count remains 1.
    """
    mod = _import_tool()
    src = tmp_path / "findings.yaml"
    src.write_text(
        "findings:\n"
        "  - id: DUP1\n"
        "    type: K1\n"
        "    file: recipe/dup.yaml\n"
        "    severity: low\n"
    )
    db = tmp_path / "issue_db.json"
    _seed_issue_db(db)

    # First import
    monkeypatch.setattr(
        sys, "argv",
        ["dev_issue_db_bulk_import.py",
         "--source", str(src), "--db", str(db)]
    )
    mod.main()
    db_data = json.loads(db.read_text())
    assert db_data["summary"]["total_issues"] == 1
    first_issue = next(iter(db_data["issues"].values()))
    assert first_issue["instance_count"] == 1

    # Second import: same source → should report 1 duplicate
    mod.main()
    captured = capsys.readouterr()
    assert "registered 0 issues" in captured.out
    assert "duplicates 1" in captured.out
    db_data = json.loads(db.read_text())
    assert db_data["summary"]["total_issues"] == 1
    # CRITICAL: instance_count must still be 1 (no double-count)
    first_issue = next(iter(db_data["issues"].values()))
    assert first_issue["instance_count"] == 1


def test_main_default_db_path(
    capsys, monkeypatch, tmp_path
):
    """main() with no --db uses default '.mase/pipeline/issue_db.json'."""
    mod = _import_tool()
    src = tmp_path / "findings.yaml"
    src.write_text(
        "findings:\n"
        "  - id: DB1\n"
        "    type: K1\n"
        "    file: recipe/db1.yaml\n"
    )
    # Pre-create the default-path db
    default_db_dir = tmp_path / ".mase" / "pipeline"
    default_db_dir.mkdir(parents=True)
    default_db = default_db_dir / "issue_db.json"
    _seed_issue_db(default_db)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys, "argv",
        ["dev_issue_db_bulk_import.py", "--source", str(src)]
    )
    mod.main()
    captured = capsys.readouterr()
    assert "DB: .mase/pipeline/issue_db.json" in captured.out
    # db was saved at the default path
    assert default_db.exists()
    db_data = json.loads(default_db.read_text())
    assert db_data["summary"]["total_issues"] == 1


def test_main_false_positive_default_status_accepted(
    capsys, monkeypatch, tmp_path
):
    """main() accepts --default-status false_positive (cov for choices branch)."""
    mod = _import_tool()
    src = tmp_path / "findings.yaml"
    src.write_text(
        "findings:\n"
        "  - id: FP1\n"
        "    type: K1\n"
        "    file: recipe/fp1.yaml\n"
    )
    db = tmp_path / "issue_db.json"
    _seed_issue_db(db)
    monkeypatch.setattr(
        sys, "argv",
        ["dev_issue_db_bulk_import.py",
         "--source", str(src), "--db", str(db),
         "--default-status", "false_positive"]
    )
    # Should NOT exit; just verifies the choice 'false_positive' parses.
    mod.main()
    captured = capsys.readouterr()
    assert "registered 1 issues" in captured.out


# ─────────────────────────────────────────────────────────────────────
# __main__ guard — exercises line 97 for 100% coverage
# ─────────────────────────────────────────────────────────────────────

def test_main_runpy_under_dunder_main(monkeypatch, tmp_path):
    """Execute the script via `runpy.run_path(__name__='__main__')` to
    hit the `if __name__ == "__main__":` line IN-PROCESS, so coverage.py
    attributes the line to this test.

    We use a source with no findings → main() does sys.exit(1) → runpy
    catches the SystemExit and returns the code.
    """
    src = tmp_path / "empty.yaml"
    src.write_text("metadata:\n  no_findings: true\n")
    db = tmp_path / "issue_db.json"
    _seed_issue_db(db)
    monkeypatch.setattr(
        sys, "argv",
        ["dev_issue_db_bulk_import.py",
         "--source", str(src), "--db", str(db)]
    )
    # run_path with run_name='__main__' makes `if __name__ == "__main__":` True
    # We catch SystemExit because sys.exit() raises it.
    with pytest.raises(SystemExit) as excinfo:
        runpy.run_path(str(TOOL), run_name="__main__")
    assert excinfo.value.code == 1
