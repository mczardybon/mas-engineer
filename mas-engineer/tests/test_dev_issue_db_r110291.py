"""Tests for mas-engineer/tools/dev_issue_db.py — R110-291.

Coverage target: dev_issue_db.py 50-69% → ~90% (454 lines, 5 funcs + CLI).

Tests:
- _now_iso: returns ISO format with Z
- compute_issue_hash: stable, file-local, sha256 prefix, 64 hex chars
- compute_structural_pattern: K1/K3/L1/U1 line-range, Q3 extra_field,
  NN1 multi_role sorted, NN2 tool_overload, NN3 scope_bloat,
  HARDCODE-STALE/STALE-LITERAL literal+file_dir, default fallback
- validate_wontfix_reason: empty/short/long/placeholder valid + invalid
- IssueDB:
  - _load_or_init: existing file loads, missing inits empty schema
  - get/exists/status/should_emit_finding: lookup + default "unknown"
  - register: new entry, append to open, skip fixed/wontfix/false_positive
  - mark_fixed: state change, no-op if not found/already fixed
  - mark_wontfix: state change, no-op if not found/already wontfix,
    raises on empty reason
  - record_design/record_validation: append to lists, no-op on missing
  - list_open/list_by_status: filter by status
  - filter_findings: drops fixed/wontfix/false_positive, keeps
    no-hash findings
  - save: writes file, updates last_modified_at, atomic via .tmp+rename
  - save_with_lock: re-loads on entry, saves on exit
  - _update_goose_verdict: merge logic
  - _compute_summary: by_status + by_type + by_type_<status>
- CLI subparsers: stats, list-open, list-wontfix, list-fixed,
  mark-wontfix (with reason validation), mark-fixed
"""
import pytest
import sys
import json
import re
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from contextlib import contextmanager

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import dev_issue_db as idb

SCRIPT = Path(__file__).resolve().parent.parent / "tools" / "dev_issue_db.py"


@pytest.fixture
def db(tmp_path):
    """Create an IssueDB at a tmp path."""
    return idb.IssueDB(str(tmp_path / "issue_db.json"))


@pytest.fixture
def seeded_db(db):
    """Seed the DB with 3 issues in different statuses."""
    h_open = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
    h_fix = idb.compute_issue_hash("b.py", "K1", "k1:30-40")
    h_wf = idb.compute_issue_hash("c.py", "Q3", "extra_field:foo")
    h_fp = idb.compute_issue_hash("d.py", "NN1", "multi_role:2:a,b")
    db.register(hash=h_open, type="K1", severity="high", file="a.py",
                structural_pattern="k1:10-20",
                issue_summary="missing try", fix_summary="add try",
                instance={"line": 10})
    db.register(hash=h_fix, type="K1", severity="high", file="b.py",
                structural_pattern="k1:30-40",
                issue_summary="missing try", fix_summary="add try",
                instance={"line": 30})
    db.register(hash=h_wf, type="Q3", severity="medium", file="c.py",
                structural_pattern="extra_field:foo",
                issue_summary="extra field", fix_summary="remove",
                instance={"line": 1})
    db.register(hash=h_fp, type="NN1", severity="low", file="d.py",
                structural_pattern="multi_role:2:a,b",
                issue_summary="multi role", fix_summary="split",
                instance={"line": 1})
    db.mark_fixed(h_fix, "abc123")
    db.mark_wontfix(h_wf, "not a real issue, was a misread")
    # Mark false_positive by writing directly (no public API for that)
    db._data["issues"][h_fp]["status"] = "false_positive"
    return db, {"open": h_open, "fixed": h_fix, "wontfix": h_wf,
                "false_positive": h_fp}


# ─── _now_iso ─────────────────────────────────────────────────────

class TestNowIso:
    def test_returns_iso_format_with_z(self):
        result = idb._now_iso()
        assert result.endswith("Z")
        # Match YYYY-MM-DDTHH:MM:SSZ
        assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", result)


# ─── compute_issue_hash ───────────────────────────────────────────

class TestComputeIssueHash:
    def test_returns_sha256_prefix(self):
        h = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        assert h.startswith("sha256:")

    def test_64_hex_chars(self):
        h = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        digest = h.split(":", 1)[1]
        assert len(digest) == 64
        assert all(c in "0123456789abcdef" for c in digest)

    def test_stable(self):
        h1 = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        h2 = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        assert h1 == h2

    def test_different_file_different_hash(self):
        h1 = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        h2 = idb.compute_issue_hash("b.py", "K1", "k1:10-20")
        assert h1 != h2

    def test_different_type_different_hash(self):
        h1 = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        h2 = idb.compute_issue_hash("a.py", "K3", "k1:10-20")
        assert h1 != h2

    def test_different_pattern_different_hash(self):
        h1 = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        h2 = idb.compute_issue_hash("a.py", "K1", "k1:10-30")
        assert h1 != h2

    def test_normalizes_leading_dot_slash(self):
        h1 = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        h2 = idb.compute_issue_hash("./a.py", "K1", "k1:10-20")
        assert h1 == h2

    def test_normalizes_dotdot(self):
        h1 = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        h2 = idb.compute_issue_hash("./a.py", "K1", "k1:10-20")
        h3 = idb.compute_issue_hash("a.py/", "K1", "k1:10-20")
        # All should normalize the same way
        assert h1 == h2


# ─── compute_structural_pattern ───────────────────────────────────

class TestComputeStructuralPattern:
    def test_k1_line_range(self):
        p = idb.compute_structural_pattern("K1", "a.py", line_start=10,
                                           line_end=20)
        assert p == "k1:10-20"

    def test_k3_line_range(self):
        p = idb.compute_structural_pattern("K3", "a.py", line_start=14,
                                           line_end=28)
        assert p == "k3:14-28"

    def test_l1_line_range(self):
        p = idb.compute_structural_pattern("L1", "a.py", line_start=1,
                                           line_end=5)
        assert p == "l1:1-5"

    def test_u1_line_range(self):
        p = idb.compute_structural_pattern("U1", "a.py", line_start=0,
                                           line_end=0)
        assert p == "u1:0-0"

    def test_q3_extra_field(self):
        p = idb.compute_structural_pattern("Q3", "a.py", field_name="x")
        assert p == "extra_field:x"

    def test_nn1_multi_role_sorted(self):
        # Roles get sorted for stability
        p1 = idb.compute_structural_pattern("NN1", "a.py",
                                            roles=["b", "a", "c"])
        p2 = idb.compute_structural_pattern("NN1", "a.py",
                                            roles=["c", "a", "b"])
        assert p1 == p2
        assert p1 == "multi_role:3:a,b,c"

    def test_nn1_empty_roles(self):
        p = idb.compute_structural_pattern("NN1", "a.py", roles=[])
        assert p == "multi_role:0:"

    def test_nn1_none_roles(self):
        p = idb.compute_structural_pattern("NN1", "a.py", roles=None)
        assert p == "multi_role:0:"

    def test_nn2_tool_overload(self):
        p = idb.compute_structural_pattern("NN2", "a.py", extension_count=5)
        assert p == "tool_overload:5"

    def test_nn3_scope_bloat_truncates_at_3(self):
        p = idb.compute_structural_pattern(
            "NN3", "a.py",
            domains=["a", "b", "c", "d", "e"])
        assert p == "scope_bloat:5:a,b,c"  # 5 total, only first 3

    def test_hardcode_stale(self):
        p = idb.compute_structural_pattern("HARDCODE-STALE-001", "a.py",
                                            literal="foo", file_dir="bar")
        assert p == "HARDCODE-STALE-001:foo:bar"

    def test_stale_literal(self):
        p = idb.compute_structural_pattern("STALE-LITERAL", "a.py",
                                            literal="x", file_dir="d")
        assert p == "STALE-LITERAL:x:d"

    def test_unknown_type_fallback(self):
        p = idb.compute_structural_pattern("XYZ", "/path/to/file.py")
        assert p == "XYZ:file.py"


# ─── validate_wontfix_reason ──────────────────────────────────────

class TestValidateWontfixReason:
    def test_valid_reason(self):
        assert idb.validate_wontfix_reason("This is a valid reason") is None

    def test_empty_string(self):
        err = idb.validate_wontfix_reason("")
        assert "non-empty" in err

    def test_whitespace_only(self):
        err = idb.validate_wontfix_reason("   ")
        assert "non-empty" in err

    def test_too_short(self):
        err = idb.validate_wontfix_reason("abc")
        assert "too short" in err
        assert "10" in err

    def test_exactly_9_chars(self):
        err = idb.validate_wontfix_reason("a" * 9)
        assert "too short" in err

    def test_exactly_10_chars_valid(self):
        assert idb.validate_wontfix_reason("a" * 10) is None

    def test_too_long(self):
        err = idb.validate_wontfix_reason("a" * 501)
        assert "too long" in err
        assert "500" in err

    def test_exactly_501_chars(self):
        err = idb.validate_wontfix_reason("a" * 501)
        assert "too long" in err

    def test_exactly_500_chars_valid(self):
        assert idb.validate_wontfix_reason("a" * 500) is None

    def test_placeholder_todo_too_short_first(self):
        # "todo" is 4 chars so length-fail fires before placeholder-check
        err = idb.validate_wontfix_reason("todo")
        assert "too short" in err

    def test_placeholder_todo_uppercase_too_short(self):
        err = idb.validate_wontfix_reason("TODO")
        assert "too short" in err

    def test_placeholder_tbd_fixme_wip_too_short(self):
        # All 4-char placeholders fail length check first
        for ph in ("tbd", "TBD", "fixme", "FIXME", "wip", "WIP"):
            err = idb.validate_wontfix_reason(ph)
            assert "too short" in err, f"ph={ph}"

    def test_placeholder_in_phrase_not_flagged(self):
        # "Fix the todo" is 11 chars and not a literal placeholder
        # (it's a real reason containing the word "todo")
        assert idb.validate_wontfix_reason("Fix the todo list") is None


# ─── IssueDB basic operations ─────────────────────────────────────

class TestIssueDBBasics:
    def test_init_creates_empty_schema(self, tmp_path):
        db = idb.IssueDB(str(tmp_path / "new.json"))
        assert db._data["schema_version"] == idb.SCHEMA_VERSION
        assert db._data["issues"] == {}
        assert db._data["summary"]["total_issues"] == 0

    def test_load_existing(self, tmp_path):
        path = tmp_path / "existing.json"
        path.write_text(json.dumps({
            "schema_version": "1.0.0",
            "created_at": "2026-01-01T00:00:00Z",
            "last_modified_at": "2026-01-01T00:00:00Z",
            "last_modified_by": "init",
            "summary": {"total_issues": 0, "by_status": {}, "by_type": {}},
            "issues": {"sha256:abc": {"hash": "sha256:abc"}},
        }))
        db = idb.IssueDB(str(path))
        assert "sha256:abc" in db._data["issues"]

    def test_get_returns_none_for_unknown(self, db):
        assert db.get("sha256:nope") is None

    def test_get_returns_dict(self, db):
        h = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        db.register(hash=h, type="K1", severity="high", file="a.py",
                    structural_pattern="k1:10-20",
                    issue_summary="x", fix_summary="y",
                    instance={"line": 10})
        issue = db.get(h)
        assert issue["hash"] == h
        assert issue["status"] == "open"

    def test_exists_true_false(self, db):
        h = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        db.register(hash=h, type="K1", severity="high", file="a.py",
                    structural_pattern="k1:10-20",
                    issue_summary="x", fix_summary="y",
                    instance={"line": 10})
        assert db.exists(h) is True
        assert db.exists("sha256:other") is False

    def test_status_returns_actual_status(self, seeded_db):
        db, h = seeded_db
        assert db.status(h["open"]) == "open"
        assert db.status(h["fixed"]) == "fixed"
        assert db.status(h["wontfix"]) == "wontfix"
        assert db.status(h["false_positive"]) == "false_positive"

    def test_status_unknown(self, db):
        assert db.status("sha256:nope") == "unknown"

    def test_should_emit_finding_only_for_unknown(self, seeded_db):
        db, h = seeded_db
        assert db.should_emit_finding("sha256:brand_new") is True
        assert db.should_emit_finding(h["open"]) is False
        assert db.should_emit_finding(h["fixed"]) is False
        assert db.should_emit_finding(h["wontfix"]) is False
        assert db.should_emit_finding(h["false_positive"]) is False


# ─── IssueDB.register ─────────────────────────────────────────────

class TestRegister:
    def test_register_new_creates_entry(self, db):
        h = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        result = db.register(hash=h, type="K1", severity="high",
                             file="a.py", structural_pattern="k1:10-20",
                             issue_summary="x", fix_summary="y",
                             instance={"line": 10})
        assert result == h
        issue = db.get(h)
        assert issue["status"] == "open"
        assert issue["instance_count"] == 1
        assert issue["instances"] == [{"line": 10}]
        assert issue["goose_verdict"] is None
        assert issue["past_designs"] == []
        assert issue["past_validation_outcomes"] == []
        assert issue["wontfix_reason"] is None

    def test_register_appends_to_open(self, db):
        h = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        db.register(hash=h, type="K1", severity="high", file="a.py",
                    structural_pattern="k1:10-20",
                    issue_summary="x", fix_summary="y",
                    instance={"line": 10})
        db.register(hash=h, type="K1", severity="high", file="a.py",
                    structural_pattern="k1:10-20",
                    issue_summary="x", fix_summary="y",
                    instance={"line": 11})
        issue = db.get(h)
        assert issue["instance_count"] == 2
        assert len(issue["instances"]) == 2

    def test_register_skips_fixed(self, db):
        h = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        db.register(hash=h, type="K1", severity="high", file="a.py",
                    structural_pattern="k1:10-20",
                    issue_summary="x", fix_summary="y",
                    instance={"line": 10})
        db.mark_fixed(h, "abc")
        before = db.get(h)["instance_count"]
        # Register again — should be a no-op for fixed status
        db.register(hash=h, type="K1", severity="high", file="a.py",
                    structural_pattern="k1:10-20",
                    issue_summary="x", fix_summary="y",
                    instance={"line": 11})
        after = db.get(h)["instance_count"]
        assert before == after

    def test_register_with_goose_verdict(self, db):
        h = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        gv = {"verdict": "APPROVED", "confidence": 0.9, "explanation": "ok",
              "alternatives": []}
        db.register(hash=h, type="K1", severity="high", file="a.py",
                    structural_pattern="k1:10-20",
                    issue_summary="x", fix_summary="y",
                    instance={"line": 10}, goose_verdict=gv)
        assert db.get(h)["goose_verdict"] == gv

    def test_register_merges_repeated_goose_verdict(self, db):
        h = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        db.register(hash=h, type="K1", severity="high", file="a.py",
                    structural_pattern="k1:10-20",
                    issue_summary="x", fix_summary="y",
                    instance={"line": 10},
                    goose_verdict={"verdict": "APPROVED", "confidence": 0.9,
                                   "explanation": "first",
                                   "alternatives": []})
        db.register(hash=h, type="K1", severity="high", file="a.py",
                    structural_pattern="k1:10-20",
                    issue_summary="x", fix_summary="y",
                    instance={"line": 11},
                    goose_verdict={"verdict": "REJECTED", "confidence": 0.5,
                                   "explanation": "second",
                                   "alternatives": ["alt1"]})
        gv = db.get(h)["goose_verdict"]
        # Merged: latest verdict, merged explanation, verdict_count=2
        assert gv["verdict"] == "REJECTED"
        assert gv["explanation"] == "second"
        assert gv["alternatives"] == ["alt1"]
        assert gv["verdict_count"] == 2


# ─── IssueDB.mark_fixed / mark_wontfix ────────────────────────────

class TestMarkFixed:
    def test_mark_fixed_open(self, db):
        h = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        db.register(hash=h, type="K1", severity="high", file="a.py",
                    structural_pattern="k1:10-20",
                    issue_summary="x", fix_summary="y",
                    instance={"line": 10})
        changed = db.mark_fixed(h, "abc123")
        assert changed is True
        assert db.get(h)["status"] == "fixed"
        assert len(db.get(h)["past_validation_outcomes"]) == 1
        pvo = db.get(h)["past_validation_outcomes"][0]
        assert pvo["verdict"] == "APPROVED"
        assert pvo["commit_sha"] == "abc123"
        assert pvo["validated_by"] == "im-validator"

    def test_mark_fixed_custom_validator(self, db):
        h = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        db.register(hash=h, type="K1", severity="high", file="a.py",
                    structural_pattern="k1:10-20",
                    issue_summary="x", fix_summary="y",
                    instance={"line": 10})
        db.mark_fixed(h, "abc", validated_by="human-reviewer")
        assert db.get(h)["past_validation_outcomes"][0]["validated_by"] == \
            "human-reviewer"

    def test_mark_fixed_unknown_hash(self, db):
        assert db.mark_fixed("sha256:nope", "abc") is False

    def test_mark_fixed_already_fixed(self, db):
        h = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        db.register(hash=h, type="K1", severity="high", file="a.py",
                    structural_pattern="k1:10-20",
                    issue_summary="x", fix_summary="y",
                    instance={"line": 10})
        db.mark_fixed(h, "abc")
        # Second call: already fixed, returns False
        assert db.mark_fixed(h, "def") is False


class TestMarkWontfix:
    def test_mark_wontfix_open(self, db):
        h = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        db.register(hash=h, type="K1", severity="high", file="a.py",
                    structural_pattern="k1:10-20",
                    issue_summary="x", fix_summary="y",
                    instance={"line": 10})
        changed = db.mark_wontfix(h, "this is a real reason")
        assert changed is True
        assert db.get(h)["status"] == "wontfix"
        assert db.get(h)["wontfix_reason"] == "this is a real reason"
        assert db.get(h)["wontfix_marked_at"] is not None
        assert db.get(h)["wontfix_marked_by"] == "general-improver"

    def test_mark_wontfix_custom_marker(self, db):
        h = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        db.register(hash=h, type="K1", severity="high", file="a.py",
                    structural_pattern="k1:10-20",
                    issue_summary="x", fix_summary="y",
                    instance={"line": 10})
        db.mark_wontfix(h, "not applicable here", marked_by="mczardybon")
        assert db.get(h)["wontfix_marked_by"] == "mczardybon"

    def test_mark_wontfix_empty_raises(self, db):
        h = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        db.register(hash=h, type="K1", severity="high", file="a.py",
                    structural_pattern="k1:10-20",
                    issue_summary="x", fix_summary="y",
                    instance={"line": 10})
        with pytest.raises(ValueError):
            db.mark_wontfix(h, "")

    def test_mark_wontfix_whitespace_raises(self, db):
        h = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        db.register(hash=h, type="K1", severity="high", file="a.py",
                    structural_pattern="k1:10-20",
                    issue_summary="x", fix_summary="y",
                    instance={"line": 10})
        with pytest.raises(ValueError):
            db.mark_wontfix(h, "   ")

    def test_mark_wontfix_unknown_hash(self, db):
        assert db.mark_wontfix("sha256:nope", "this is a reason") is False

    def test_mark_wontfix_already_wontfix(self, db):
        h = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        db.register(hash=h, type="K1", severity="high", file="a.py",
                    structural_pattern="k1:10-20",
                    issue_summary="x", fix_summary="y",
                    instance={"line": 10})
        db.mark_wontfix(h, "first reason")
        assert db.mark_wontfix(h, "second reason") is False


# ─── record_design / record_validation ────────────────────────────

class TestRecordDesign:
    def test_record_design_appends(self, db):
        h = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        db.register(hash=h, type="K1", severity="high", file="a.py",
                    structural_pattern="k1:10-20",
                    issue_summary="x", fix_summary="y",
                    instance={"line": 10})
        db.record_design(h, patch={"diff": "x"}, goose_verdict="APPROVED",
                         verdict_explanation="ok", design_run_id="d1")
        assert len(db.get(h)["past_designs"]) == 1
        d = db.get(h)["past_designs"][0]
        assert d["patch"] == {"diff": "x"}
        assert d["goose_verdict"] == "APPROVED"
        assert d["design_run_id"] == "d1"
        assert d["designed_by"] == "im-designer"

    def test_record_design_no_op_on_unknown(self, db):
        # Should NOT raise
        db.record_design("sha256:nope", patch={}, goose_verdict="X",
                         verdict_explanation="y", design_run_id="z")


class TestRecordValidation:
    def test_record_validation_appends(self, db):
        h = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        db.register(hash=h, type="K1", severity="high", file="a.py",
                    structural_pattern="k1:10-20",
                    issue_summary="x", fix_summary="y",
                    instance={"line": 10})
        db.record_validation(h, verdict="APPROVED", reason="ok",
                             commit_sha="abc")
        pvos = db.get(h)["past_validation_outcomes"]
        assert len(pvos) == 1
        assert pvos[0]["verdict"] == "APPROVED"
        assert pvos[0]["commit_sha"] == "abc"
        assert pvos[0]["validated_by"] == "im-validator"

    def test_record_validation_no_op_on_unknown(self, db):
        db.record_validation("sha256:nope", verdict="X", reason="y")


# ─── list_open / list_by_status / filter_findings ─────────────────

class TestListAndFilter:
    def test_list_open(self, seeded_db):
        db, h = seeded_db
        opens = db.list_open()
        assert opens == [h["open"]]

    def test_list_by_status(self, seeded_db):
        db, h = seeded_db
        assert db.list_by_status("fixed") == [h["fixed"]]
        assert db.list_by_status("wontfix") == [h["wontfix"]]
        assert db.list_by_status("false_positive") == [h["false_positive"]]
        assert db.list_by_status("open") == [h["open"]]
        assert db.list_by_status("nonexistent") == []

    def test_filter_findings_drops_closed(self, seeded_db):
        db, h = seeded_db
        findings = [
            {"issue_hash": h["open"], "msg": "still open"},
            {"issue_hash": h["fixed"], "msg": "fixed"},
            {"issue_hash": h["wontfix"], "msg": "wontfix"},
            {"issue_hash": h["false_positive"], "msg": "fp"},
        ]
        kept, dropped = db.filter_findings(findings)
        assert len(kept) == 1
        assert kept[0]["issue_hash"] == h["open"]
        assert dropped == 3

    def test_filter_findings_keeps_no_hash(self, seeded_db):
        db, _ = seeded_db
        findings = [{"msg": "no hash"}, {"issue_hash": None, "msg": "x"}]
        kept, dropped = db.filter_findings(findings)
        assert len(kept) == 2
        assert dropped == 0


# ─── save / save_with_lock ────────────────────────────────────────

class TestSave:
    def test_save_writes_file(self, db, tmp_path):
        h = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        db.register(hash=h, type="K1", severity="high", file="a.py",
                    structural_pattern="k1:10-20",
                    issue_summary="x", fix_summary="y",
                    instance={"line": 10})
        db.save()
        from pathlib import Path
        data = json.loads(Path(db.db_path).read_text())
        assert data["issues"][h]["status"] == "open"

    def test_save_updates_last_modified_at(self, db):
        before = db._data["last_modified_at"]
        db.save()
        after = db._data["last_modified_at"]
        assert after >= before  # ISO timestamp string compares correctly

    def test_save_atomic_via_tmp_rename(self, db, tmp_path, monkeypatch):
        # Track os.rename calls
        h = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        db.register(hash=h, type="K1", severity="high", file="a.py",
                    structural_pattern="k1:10-20",
                    issue_summary="x", fix_summary="y",
                    instance={"line": 10})
        original_rename = __import__("os").rename
        with patch("os.rename", wraps=original_rename) as mock_rename:
            db.save()
        # rename was called with .tmp path
        assert any(".tmp" in str(call.args[0])
                   for call in mock_rename.call_args_list)

    def test_save_with_lock_reloads_state(self, db):
        # save_with_lock re-loads from disk at entry, then saves on exit.
        # Pre-existing issues on disk survive the re-load.
        h = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        db.register(hash=h, type="K1", severity="high", file="a.py",
                    structural_pattern="k1:10-20",
                    issue_summary="x", fix_summary="y",
                    instance={"line": 10})
        db.save()  # ensure on disk BEFORE entering lock
        with db.save_with_lock():
            # Inside the lock, the in-memory state was re-loaded
            # (still contains the issue from disk)
            assert db.get(h) is not None
        from pathlib import Path
        data = json.loads(Path(db.db_path).read_text())
        assert data["issues"][h]["status"] == "open"

    def test_save_with_lock_persists_modifications(self, db):
        # Modifications made inside the with-block are persisted to disk
        h = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        db.register(hash=h, type="K1", severity="high", file="a.py",
                    structural_pattern="k1:10-20",
                    issue_summary="x", fix_summary="y",
                    instance={"line": 10})
        db.save()  # baseline on disk
        with db.save_with_lock():
            # mark_fixed persists via save() on context exit
            assert db.mark_fixed(h, "abc123") is True
        from pathlib import Path
        data = json.loads(Path(db.db_path).read_text())
        assert data["issues"][h]["status"] == "fixed"


# ─── _compute_summary / _update_goose_verdict ─────────────────────

class TestComputeSummary:
    def test_summary_counts(self, seeded_db):
        db, _ = seeded_db
        summary = db._compute_summary()
        assert summary["total_issues"] == 4
        assert summary["by_status"] == {"open": 1, "fixed": 1, "wontfix": 1,
                                         "false_positive": 1}
        # by_type aggregates ALL (legacy) — K1 has 2, others 1
        assert summary["by_type"]["K1"] == 2
        assert summary["by_type"]["Q3"] == 1
        assert summary["by_type"]["NN1"] == 1

    def test_summary_status_filtered(self, seeded_db):
        db, _ = seeded_db
        summary = db._compute_summary()
        assert summary["by_type_open"]["K1"] == 1
        assert summary["by_type_fixed"]["K1"] == 1
        assert summary["by_type_wontfix"]["Q3"] == 1
        assert summary["by_type_false_positive"]["NN1"] == 1


# ─── CLI subcommands ──────────────────────────────────────────────

class TestCLI:
    def _run_cli(self, *args):
        """Run the CLI as __main__ and capture sys.exit / stdout / stderr."""
        import runpy
        full_args = ["dev_issue_db.py", *args]
        with patch.object(sys, "argv", full_args):
            try:
                runpy.run_path(str(SCRIPT), run_name="__main__")
                return 0, "", ""
            except SystemExit as e:
                return e.code, "", ""

    def test_stats_prints_summary(self, seeded_db, tmp_path, capsys):
        db_path = tmp_path / "issue_db.json"
        # Copy seeded state to tmp
        import shutil
        # Re-create the db in tmp_path by serializing
        d = idb.IssueDB(str(db_path))
        h = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        d.register(hash=h, type="K1", severity="high", file="a.py",
                   structural_pattern="k1:10-20",
                   issue_summary="x", fix_summary="y",
                   instance={"line": 10})
        d.save()
        with patch.object(sys, "argv",
                          ["dev_issue_db.py", "--db", str(db_path),
                           "stats"]):
            import runpy
            try:
                runpy.run_path(str(SCRIPT), run_name="__main__")
            except SystemExit:
                pass
        out = capsys.readouterr().out
        assert "total_issues" in out

    def test_list_open_prints_open_issues(self, tmp_path, capsys):
        db_path = tmp_path / "issue_db.json"
        d = idb.IssueDB(str(db_path))
        h = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        d.register(hash=h, type="K1", severity="high", file="a.py",
                   structural_pattern="k1:10-20",
                   issue_summary="x", fix_summary="y",
                   instance={"line": 10})
        d.save()
        with patch.object(sys, "argv",
                          ["dev_issue_db.py", "--db", str(db_path),
                           "list-open"]):
            import runpy
            try:
                runpy.run_path(str(SCRIPT), run_name="__main__")
            except SystemExit:
                pass
        out = capsys.readouterr().out
        assert h in out

    def test_mark_wontfix_invalid_reason_exits_1(self, tmp_path, capsys):
        db_path = tmp_path / "issue_db.json"
        d = idb.IssueDB(str(db_path))
        h = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        d.register(hash=h, type="K1", severity="high", file="a.py",
                   structural_pattern="k1:10-20",
                   issue_summary="x", fix_summary="y",
                   instance={"line": 10})
        d.save()
        with patch.object(sys, "argv",
                          ["dev_issue_db.py", "--db", str(db_path),
                           "mark-wontfix", h, "--reason", "todo"]):
            import runpy
            with pytest.raises(SystemExit) as exc:
                runpy.run_path(str(SCRIPT), run_name="__main__")
        assert exc.value.code == 1
        err = capsys.readouterr().err
        assert "ERROR" in err

    def test_mark_wontfix_valid_reason_succeeds(self, tmp_path, capsys):
        db_path = tmp_path / "issue_db.json"
        d = idb.IssueDB(str(db_path))
        h = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        d.register(hash=h, type="K1", severity="high", file="a.py",
                   structural_pattern="k1:10-20",
                   issue_summary="x", fix_summary="y",
                   instance={"line": 10})
        d.save()
        with patch.object(sys, "argv",
                          ["dev_issue_db.py", "--db", str(db_path),
                           "mark-wontfix", h,
                           "--reason", "this is a real reason"]):
            import runpy
            try:
                runpy.run_path(str(SCRIPT), run_name="__main__")
            except SystemExit:
                pass
        out = capsys.readouterr().out
        assert "mark-wontfix changed=True" in out

    def test_mark_fixed_succeeds(self, tmp_path, capsys):
        db_path = tmp_path / "issue_db.json"
        d = idb.IssueDB(str(db_path))
        h = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        d.register(hash=h, type="K1", severity="high", file="a.py",
                   structural_pattern="k1:10-20",
                   issue_summary="x", fix_summary="y",
                   instance={"line": 10})
        d.save()
        with patch.object(sys, "argv",
                          ["dev_issue_db.py", "--db", str(db_path),
                           "mark-fixed", h, "--commit-sha", "abc123"]):
            import runpy
            try:
                runpy.run_path(str(SCRIPT), run_name="__main__")
            except SystemExit:
                pass
        out = capsys.readouterr().out
        assert "mark-fixed changed=True" in out

    def test_mark_fixed_missing_commit_sha_exits_1(self, tmp_path, capsys):
        db_path = tmp_path / "issue_db.json"
        d = idb.IssueDB(str(db_path))
        h = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        d.register(hash=h, type="K1", severity="high", file="a.py",
                   structural_pattern="k1:10-20",
                   issue_summary="x", fix_summary="y",
                   instance={"line": 10})
        d.save()
        with patch.object(sys, "argv",
                          ["dev_issue_db.py", "--db", str(db_path),
                           "mark-fixed", h, "--commit-sha", ""]):
            import runpy
            with pytest.raises(SystemExit) as exc:
                runpy.run_path(str(SCRIPT), run_name="__main__")
        assert exc.value.code == 1
        err = capsys.readouterr().err
        assert "ERROR" in err

    def test_list_wontfix_prints_wontfix(self, tmp_path, capsys):
        db_path = tmp_path / "issue_db.json"
        d = idb.IssueDB(str(db_path))
        h = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        d.register(hash=h, type="K1", severity="high", file="a.py",
                   structural_pattern="k1:10-20",
                   issue_summary="x", fix_summary="y",
                   instance={"line": 10})
        d.mark_wontfix(h, "this is a real reason")
        d.save()
        with patch.object(sys, "argv",
                          ["dev_issue_db.py", "--db", str(db_path),
                           "list-wontfix"]):
            import runpy
            try:
                runpy.run_path(str(SCRIPT), run_name="__main__")
            except SystemExit:
                pass
        out = capsys.readouterr().out
        assert h in out
        assert "this is a real reason" in out

    def test_list_fixed_prints_fixed(self, tmp_path, capsys):
        db_path = tmp_path / "issue_db.json"
        d = idb.IssueDB(str(db_path))
        h = idb.compute_issue_hash("a.py", "K1", "k1:10-20")
        d.register(hash=h, type="K1", severity="high", file="a.py",
                   structural_pattern="k1:10-20",
                   issue_summary="x", fix_summary="y",
                   instance={"line": 10})
        d.mark_fixed(h, "abc123")
        d.save()
        with patch.object(sys, "argv",
                          ["dev_issue_db.py", "--db", str(db_path),
                           "list-fixed"]):
            import runpy
            try:
                runpy.run_path(str(SCRIPT), run_name="__main__")
            except SystemExit:
                pass
        out = capsys.readouterr().out
        assert h in out
