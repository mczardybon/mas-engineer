"""R110-446 — coverage-push r8: tools/dev_issue_db_bulk_import.py 0% → 100%.

Bulk-import tool for run-findings (97 lines).

Targets:
- load_findings: JSON file → dict; YAML file → dict; empty dict
  → [] (no findings); list instead of dict → []; findings key
  missing → []; 'ranked_findings' top-level → used; 'findings'
  top-level → used; 'data.findings' nested → used; findings
  is not a list → []; accepts .yaml/.yml extensions
- main: --source required; --db default
  '.mase/pipeline/issue_db.json'; --default-status
  'open'|'false_positive'; missing findings → stderr + exit 1;
  valid findings → registered/skipped/duplicates counted;
  finding missing 'type' or 'file' → skipped; duplicate hash
  → duplicates++; structural_pattern = "{type}:{id}"; summary
  printed at end; default-status 'false_positive' accepted
"""

import json
import sys
import subprocess
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.dev_issue_db_bulk_import as bi  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# load_findings
# ─────────────────────────────────────────────────────────────────────
class TestLoadFindings:
    def test_json_with_ranked_findings(self, tmp_path):
        f = tmp_path / "findings.json"
        f.write_text(json.dumps({
            "ranked_findings": [{"type": "x", "file": "a.py"}]}))
        r = bi.load_findings(str(f))
        assert len(r) == 1
        assert r[0]["type"] == "x"

    def test_yaml_with_findings(self, tmp_path):
        f = tmp_path / "findings.yaml"
        f.write_text(yaml.safe_dump({
            "findings": [{"type": "y", "file": "b.py"}]}))
        r = bi.load_findings(str(f))
        assert len(r) == 1

    def test_yaml_extension_yml(self, tmp_path):
        f = tmp_path / "findings.yml"
        f.write_text(yaml.safe_dump({
            "findings": [{"type": "z", "file": "c.py"}]}))
        r = bi.load_findings(str(f))
        assert len(r) == 1

    def test_data_findings_nested(self, tmp_path):
        f = tmp_path / "findings.yaml"
        f.write_text(yaml.safe_dump({
            "data": {"findings": [{"type": "q", "file": "d.py"}]}}))
        r = bi.load_findings(str(f))
        assert len(r) == 1

    def test_empty_data(self, tmp_path):
        f = tmp_path / "findings.yaml"
        f.write_text(yaml.safe_dump({}))
        r = bi.load_findings(str(f))
        assert r == []

    def test_top_level_list_returns_empty(self, tmp_path):
        # data is a list → returns []
        f = tmp_path / "findings.yaml"
        f.write_text(yaml.safe_dump([{"type": "x"}]))
        r = bi.load_findings(str(f))
        assert r == []

    def test_findings_not_a_list(self, tmp_path):
        f = tmp_path / "findings.yaml"
        f.write_text(yaml.safe_dump({"findings": "not a list"}))
        r = bi.load_findings(str(f))
        assert r == []

    def test_ranked_findings_wins_over_findings(self, tmp_path):
        f = tmp_path / "findings.yaml"
        f.write_text(yaml.safe_dump({
            "ranked_findings": [{"type": "R"}],
            "findings": [{"type": "F"}]}))
        r = bi.load_findings(str(f))
        assert r[0]["type"] == "R"

    def test_findings_wins_over_data_findings(self, tmp_path):
        f = tmp_path / "findings.yaml"
        f.write_text(yaml.safe_dump({
            "findings": [{"type": "F"}],
            "data": {"findings": [{"type": "D"}]}}))
        r = bi.load_findings(str(f))
        assert r[0]["type"] == "F"


# ─────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────
class TestMain:
    def test_no_findings_exits_1(self, tmp_path, capsys):
        src = tmp_path / "empty.yaml"
        src.write_text(yaml.safe_dump({}))
        db = tmp_path / "db.json"
        old_argv = sys.argv
        sys.argv = ["dev_issue_db_bulk_import.py",
                    "--source", str(src),
                    "--db", str(db)]
        code = 0
        try:
            try:
                bi.main()
            except SystemExit as e:
                code = e.code if e.code is not None else 0
        finally:
            sys.argv = old_argv
        assert code == 1
        err = capsys.readouterr().err
        assert "No findings" in err

    def test_basic_import(self, tmp_path, capsys):
        src = tmp_path / "findings.yaml"
        src.write_text(yaml.safe_dump({
            "findings": [
                {"type": "Bug", "file": "a.py",
                 "id": "F1", "issue": "broken",
                 "fix": "fix it", "severity": "high"},
            ]}))
        db = tmp_path / "db.json"
        old_argv = sys.argv
        sys.argv = ["dev_issue_db_bulk_import.py",
                    "--source", str(src),
                    "--db", str(db)]
        try:
            bi.main()
        finally:
            sys.argv = old_argv
        out = capsys.readouterr().out
        assert "BULK-IMPORT" in out
        assert "registered 1" in out
        # DB file was created
        assert db.exists()

    def test_skips_missing_type(self, tmp_path, capsys):
        src = tmp_path / "findings.yaml"
        src.write_text(yaml.safe_dump({
            "findings": [
                {"file": "a.py", "id": "F1"},  # no type
                {"type": "Bug", "file": "b.py", "id": "F2"},
            ]}))
        db = tmp_path / "db.json"
        old_argv = sys.argv
        sys.argv = ["dev_issue_db_bulk_import.py",
                    "--source", str(src),
                    "--db", str(db)]
        try:
            bi.main()
        finally:
            sys.argv = old_argv
        out = capsys.readouterr().out
        assert "skipped 1" in out
        assert "registered 1" in out

    def test_skips_missing_file(self, tmp_path, capsys):
        src = tmp_path / "findings.yaml"
        src.write_text(yaml.safe_dump({
            "findings": [
                {"type": "Bug", "id": "F1"},  # no file
            ]}))
        db = tmp_path / "db.json"
        old_argv = sys.argv
        sys.argv = ["dev_issue_db_bulk_import.py",
                    "--source", str(src),
                    "--db", str(db)]
        try:
            bi.main()
        finally:
            sys.argv = old_argv
        out = capsys.readouterr().out
        assert "skipped 1" in out

    def test_duplicate_hash_increments_duplicates(self, tmp_path, capsys):
        src = tmp_path / "findings.yaml"
        # Same file+type+id → same hash → second is duplicate
        src.write_text(yaml.safe_dump({
            "findings": [
                {"type": "Bug", "file": "a.py", "id": "F1"},
                {"type": "Bug", "file": "a.py", "id": "F1"},
            ]}))
        db = tmp_path / "db.json"
        old_argv = sys.argv
        sys.argv = ["dev_issue_db_bulk_import.py",
                    "--source", str(src),
                    "--db", str(db)]
        try:
            bi.main()
        finally:
            sys.argv = old_argv
        out = capsys.readouterr().out
        assert "duplicates 1" in out
        assert "registered 1" in out

    def test_default_status_false_positive(self, tmp_path, capsys):
        src = tmp_path / "findings.yaml"
        src.write_text(yaml.safe_dump({
            "findings": [
                {"type": "Bug", "file": "a.py", "id": "F1"},
            ]}))
        db = tmp_path / "db.json"
        old_argv = sys.argv
        sys.argv = ["dev_issue_db_bulk_import.py",
                    "--source", str(src),
                    "--db", str(db),
                    "--default-status", "false_positive"]
        try:
            bi.main()
        finally:
            sys.argv = old_argv
        # Should not exit with error
        out = capsys.readouterr().out
        assert "registered 1" in out

    def test_invalid_default_status_exits(self, tmp_path):
        src = tmp_path / "findings.yaml"
        src.write_text(yaml.safe_dump({"findings": []}))
        db = tmp_path / "db.json"
        old_argv = sys.argv
        sys.argv = ["dev_issue_db_bulk_import.py",
                    "--source", str(src),
                    "--db", str(db),
                    "--default-status", "bogus"]
        code = 0
        try:
            try:
                bi.main()
            except SystemExit as e:
                code = e.code if e.code is not None else 0
        finally:
            sys.argv = old_argv
        # argparse exits with code 2 on invalid choice
        assert code == 2

    def test_structural_pattern_format(self, tmp_path):
        src = tmp_path / "findings.yaml"
        src.write_text(yaml.safe_dump({
            "findings": [
                {"type": "BUG_TYPE", "file": "a.py", "id": "F1"},
            ]}))
        db = tmp_path / "db.json"
        old_argv = sys.argv
        sys.argv = ["dev_issue_db_bulk_import.py",
                    "--source", str(src),
                    "--db", str(db)]
        try:
            bi.main()
        finally:
            sys.argv = old_argv
        # Reload DB and check the structural_pattern
        with open(db) as f:
            data = json.load(f)
        issue = list(data["issues"].values())[0]
        # type is lowercased in structural_pattern
        assert issue["structural_pattern"] == "bug_type:F1"

    def test_missing_source_exits(self, tmp_path):
        db = tmp_path / "db.json"
        old_argv = sys.argv
        sys.argv = ["dev_issue_db_bulk_import.py",
                    "--source", "/nonexistent/path.yaml",
                    "--db", str(db)]
        code = 0
        try:
            try:
                bi.main()
            except (SystemExit, FileNotFoundError) as e:
                code = getattr(e, "code", 1) or 1
        finally:
            sys.argv = old_argv
        # FileNotFoundError → exit code 1 or SystemExit
        assert code != 0

    def test_summary_printed(self, tmp_path, capsys):
        src = tmp_path / "findings.yaml"
        src.write_text(yaml.safe_dump({
            "findings": [
                {"type": "Bug", "file": "a.py", "id": "F1",
                 "severity": "high"},
            ]}))
        db = tmp_path / "db.json"
        old_argv = sys.argv
        sys.argv = ["dev_issue_db_bulk_import.py",
                    "--source", str(src),
                    "--db", str(db)]
        try:
            bi.main()
        finally:
            sys.argv = old_argv
        out = capsys.readouterr().out
        assert "Summary:" in out

    def test_default_db_path(self, tmp_path, monkeypatch, capsys):
        src = tmp_path / "findings.yaml"
        src.write_text(yaml.safe_dump({
            "findings": [
                {"type": "Bug", "file": "a.py", "id": "F1"},
            ]}))
        # Pre-create the default DB directory (IssueDB.save uses
        # .mase/pipeline/ and doesn't create it).
        (tmp_path / ".mase" / "pipeline").mkdir(parents=True)
        monkeypatch.chdir(tmp_path)
        old_argv = sys.argv
        sys.argv = ["dev_issue_db_bulk_import.py",
                    "--source", str(src)]
        try:
            bi.main()
        finally:
            sys.argv = old_argv
        # Default db path is '.mase/pipeline/issue_db.json'
        assert (tmp_path / ".mase" / "pipeline" / "issue_db.json").exists()
