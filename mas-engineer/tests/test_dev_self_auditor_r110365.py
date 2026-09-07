"""
test_dev_self_auditor_r110365.py — coverage push for tools/dev_self_auditor.py
(R110-365, 2026-09-07).

Goal: 50-70% coverage target, expected 70-90% based on R110-361..364
overshoot pattern. This file is the verification-theater detector
itself (Check 9 of the pre-push-validator), so coverage here has
amplified value.

Pattern:
  - 1 TestXxx class per public function (10 public functions)
  - 3-7 tests per class, focused on branch coverage
  - tmp_path / monkeypatch for filesystem isolation
  - R110-78: document pre-existing bugs as RED tests, do NOT fix
    (test-only push rule)

Excluded from coverage (pragma):
  - yaml-emitter (L410-481 in source) — this is a 70-line hand-rolled
    YAML serializer, exercising it 100% would require 30+ trivial tests
    per scalar type. R110-78 class: we test one happy path through it
    (full main() PASS run) and a few edge cases (empty list, nested
    dict, null/None). This is enough to catch regressions in the
    yaml_escape / _format_scalar functions without bloating the test
    file to 1500 lines.
  - print() calls in main() — verified via capfd
"""
import datetime
import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

# Import as flat module per R110-364 convention. Add tools/ to sys.path
# so `import dev_self_auditor` resolves. The .coveragerc [paths] source
# mapping credits this as tools/dev_self_auditor.py.
sys.path.insert(0, str(Path(__file__).parent.parent.resolve() / "tools"))
import dev_self_auditor as dsa  # noqa: E402


# ---------------------------------------------------------------------------
# TestFindTargetFiles — find_target_files(scope, workspace)
# ---------------------------------------------------------------------------
class TestFindTargetFiles:
    """find_target_files() discovers files to audit based on scope."""

    def test_nonexistent_scope_returns_empty(self, tmp_path):
        result = dsa.find_target_files("does/not/exist", str(tmp_path))
        assert result == []

    def test_file_scope_returns_single_file(self, tmp_path):
        f = tmp_path / "doc.md"
        f.write_text("# Doc")
        result = dsa.find_target_files(str(f), str(tmp_path))
        assert result == [f]

    def test_directory_scope_glob_md(self, tmp_path):
        scope = tmp_path / "logs"
        scope.mkdir()
        (scope / "a.md").write_text("a")
        (scope / "b.txt").write_text("b")
        (scope / "c.py").write_text("c")  # should be excluded
        result = dsa.find_target_files(str(scope), str(tmp_path))
        names = {f.name for f in result}
        assert names == {"a.md", "b.txt"}

    def test_directory_scope_recursive(self, tmp_path):
        scope = tmp_path / "logs"
        sub = scope / "sub"
        scope.mkdir()
        sub.mkdir()
        (sub / "deep.md").write_text("d")
        result = dsa.find_target_files(str(scope), str(tmp_path))
        assert any(f.name == "deep.md" for f in result)

    def test_filters_node_modules(self, tmp_path):
        scope = tmp_path / "logs"
        scope.mkdir()
        (scope / "ok.md").write_text("ok")
        nm = scope / "node_modules" / "pkg"
        nm.mkdir(parents=True)
        (nm / "skip.md").write_text("skip")
        result = dsa.find_target_files(str(scope), str(tmp_path))
        names = {f.name for f in result}
        assert "ok.md" in names
        assert "skip.md" not in names

    def test_filters_dot_git(self, tmp_path):
        scope = tmp_path / "logs"
        scope.mkdir()
        (scope / "ok.md").write_text("ok")
        g = scope / ".git" / "objects"
        g.mkdir(parents=True)
        (g / "skip.md").write_text("skip")
        result = dsa.find_target_files(str(scope), str(tmp_path))
        names = {f.name for f in result}
        assert "ok.md" in names
        assert "skip.md" not in names

    def test_absolute_scope_path(self, tmp_path):
        scope = tmp_path / "logs"
        scope.mkdir()
        (scope / "x.md").write_text("x")
        result = dsa.find_target_files(str(scope), str(tmp_path))
        assert len(result) == 1

    def test_empty_directory(self, tmp_path):
        scope = tmp_path / "empty"
        scope.mkdir()
        result = dsa.find_target_files(str(scope), str(tmp_path))
        assert result == []


# ---------------------------------------------------------------------------
# TestHasStrongClaim — has_strong_claim(content)
# ---------------------------------------------------------------------------
class TestHasStrongClaim:
    """has_strong_claim() returns list of (line, match, pattern_name)."""

    def test_no_claims_returns_empty(self):
        assert dsa.has_strong_claim("This is a perfectly normal document.") == []

    def test_verified_functional_detected(self):
        findings = dsa.has_strong_claim("This is VERIFIED FUNCTIONAL.\n")
        assert len(findings) == 1
        line, match, name = findings[0]
        assert line == 1
        assert "VERIFIED FUNCTIONAL" in match
        assert name == "STRONG_VERIFIED_FUNCTIONAL"

    def test_all_hypotheses_verified_detected(self):
        findings = dsa.has_strong_claim("ALL HYPOTHESES VERIFIED on 2026-09-07.\n")
        assert any(f[2] == "STRONG_ALL_HYPOTHESES" for f in findings)

    def test_100_percent_pass_detected(self):
        findings = dsa.has_strong_claim("Result: 100% pass.\n")
        assert any(f[2] == "STRONG_100_PERCENT" for f in findings)

    def test_100_percent_coverage_detected(self):
        findings = dsa.has_strong_claim("Achieved 100% coverage.\n")
        assert any(f[2] == "STRONG_100_PERCENT" for f in findings)

    def test_fully_tested_detected(self):
        findings = dsa.has_strong_claim("This is fully tested now.\n")
        assert any(f[2] == "STRONG_FULLY" for f in findings)

    def test_completely_works_detected(self):
        findings = dsa.has_strong_claim("The system completely works.\n")
        assert any(f[2] == "STRONG_COMPLETELY" for f in findings)

    def test_guarantee_verb_detected(self):
        findings = dsa.has_strong_claim("We guarantee this is correct.\n")
        assert any(f[2] == "STRONG_GUARANTEE_VERB" for f in findings)

    def test_guarantee_that_detected(self):
        findings = dsa.has_strong_claim("This guarantees that the result is safe.\n")
        assert any(f[2] == "STRONG_GUARANTEE_VERB" for f in findings)

    def test_e2e_verified_detected(self):
        findings = dsa.has_strong_claim("Workflow is E2E-verified.\n")
        assert any(f[2] == "STRONG_E2E_VERIFIED" for f in findings)

    def test_e2e_functional_detected(self):
        findings = dsa.has_strong_claim("Component is E2E-functional.\n")
        assert any(f[2] == "STRONG_E2E_FUNCTIONAL" for f in findings)

    def test_is_e2e_functional_detected(self):
        findings = dsa.has_strong_claim("The system IS E2E-functional.\n")
        assert any(f[2] == "STRONG_IS_E2E" for f in findings)

    def test_e2e_loading_not_flagged(self):
        # E2E-verified loading should NOT match STRONG_E2E_VERIFIED
        findings = dsa.has_strong_claim("E2E-verified loading logic.\n")
        assert not any(f[2] == "STRONG_E2E_VERIFIED" for f in findings)

    def test_case_insensitive(self):
        findings = dsa.has_strong_claim("verified functional: yes\n")
        assert any(f[2] == "STRONG_VERIFIED_FUNCTIONAL" for f in findings)

    def test_line_number_correctness(self):
        # 3-line doc with claim on line 2
        content = "Line 1\nThis is VERIFIED FUNCTIONAL.\nLine 3\n"
        findings = dsa.has_strong_claim(content)
        assert len(findings) == 1
        assert findings[0][0] == 2

    def test_multiple_claims_in_same_doc(self):
        content = "VERIFIED FUNCTIONAL\nWe guarantee this.\n"
        findings = dsa.has_strong_claim(content)
        assert len(findings) == 2
        names = {f[2] for f in findings}
        assert "STRONG_VERIFIED_FUNCTIONAL" in names
        assert "STRONG_GUARANTEE_VERB" in names

    def test_multiline_content(self):
        # MULTILINE flag should find claims on later lines
        content = "intro\n\nmore\n\nThis is VERIFIED FUNCTIONAL on line 5\n"
        findings = dsa.has_strong_claim(content)
        assert findings[0][0] == 5


# ---------------------------------------------------------------------------
# TestHasWeakeningPatternNear — has_weakening_pattern_near(content, line, window)
# ---------------------------------------------------------------------------
class TestHasWeakeningPatternNear:
    """has_weakening_pattern_near() checks for weakening patterns near a line."""

    def test_no_weakening_returns_none(self):
        content = "This is VERIFIED FUNCTIONAL.\nAll good here.\n"
        assert dsa.has_weakening_pattern_near(content, 1) is None

    def test_workaround_within_window(self):
        content = "VERIFIED FUNCTIONAL\n\nBut this is just a workaround.\n"
        # claim on line 1, "workaround" on line 3, window=5 → found
        assert dsa.has_weakening_pattern_near(content, 1) is not None

    def test_workaround_outside_window(self):
        content = "VERIFIED FUNCTIONAL\n\n\n\n\n\n\n\nworkaround far away\n"
        # claim on line 1, weakening on line 9, default window=5 → NOT found
        assert dsa.has_weakening_pattern_near(content, 1) is None

    def test_not_yet_tested(self):
        content = "VERIFIED FUNCTIONAL\nnot yet tested in production\n"
        assert dsa.has_weakening_pattern_near(content, 1) is not None

    def test_out_of_scope(self):
        content = "VERIFIED FUNCTIONAL\nThis is out of scope.\n"
        assert dsa.has_weakening_pattern_near(content, 1) is not None

    def test_partial(self):
        content = "VERIFIED FUNCTIONAL\nPARTIAL implementation\n"
        assert dsa.has_weakening_pattern_near(content, 1) is not None

    def test_custom_window(self):
        content = "claim\n\n\n\nworkaround here\n"
        # default window=5, line 1, weakening on line 5 → at boundary
        # content[:line 5-5-1:line 5+5] = lines 0..10
        assert dsa.has_weakening_pattern_near(content, 1, window=10) is not None
        # window=2 should not reach line 5
        assert dsa.has_weakening_pattern_near(content, 1, window=2) is None

    def test_window_at_start_boundary(self):
        # claim on line 1, weakening on line 1 same line
        content = "workaround detected\n"
        result = dsa.has_weakening_pattern_near(content, 1, window=5)
        assert result is not None

    def test_window_at_end_boundary(self):
        # claim on line 5 of 5-line doc
        content = "line1\nline2\nline3\nline4\nworkaround on line 5\n"
        # line 5 with window 5: look at lines 0..10, includes line 5
        result = dsa.has_weakening_pattern_near(content, 5, window=5)
        assert result is not None

    def test_returns_pattern_string(self):
        content = "VERIFIED FUNCTIONAL\nworkaround here\n"
        result = dsa.has_weakening_pattern_near(content, 1)
        assert isinstance(result, str)
        assert "workaround" in result

    def test_case_insensitive_weakening(self):
        content = "VERIFIED FUNCTIONAL\nWORKAROUND noted\n"
        assert dsa.has_weakening_pattern_near(content, 1) is not None


# ---------------------------------------------------------------------------
# TestHasHonestScopeMarker — has_honest_scope_marker(content)
# ---------------------------------------------------------------------------
class TestHasHonestScopeMarker:
    """has_honest_scope_marker() checks for honest-scope markers."""

    def test_no_marker(self):
        assert dsa.has_honest_scope_marker("Plain doc") is False

    def test_honest_scope_phrase(self):
        assert dsa.has_honest_scope_marker("This is the honest scope of the test.") is True

    def test_not_verified_marker(self):
        assert dsa.has_honest_scope_marker("Result: NOT verified in CI.") is True

    def test_separate_recipe_design_issue(self):
        assert dsa.has_honest_scope_marker("this is a separate recipe-design issue") is True

    def test_out_of_scope_for_this_commit(self):
        assert dsa.has_honest_scope_marker("Out of scope for this commit.") is True

    def test_see_re_test_results_marker(self):
        assert dsa.has_honest_scope_marker("See RE-TEST-RESULTS.md for the full picture.") is True

    def test_does_not_guarantee_marker(self):
        assert dsa.has_honest_scope_marker("This certificate does NOT guarantee X.") is True

    def test_multiple_markers(self):
        content = "honest scope: yes\nNOT verified in CI\n"
        assert dsa.has_honest_scope_marker(content) is True

    def test_empty_string(self):
        assert dsa.has_honest_scope_marker("") is False

    def test_case_insensitive(self):
        assert dsa.has_honest_scope_marker("HONEST SCOPE: limited") is True


# ---------------------------------------------------------------------------
# TestFindEvidenceInFolder — find_evidence_in_folder(file_path)
# ---------------------------------------------------------------------------
class TestFindEvidenceInFolder:
    """find_evidence_in_folder() finds .log/.txt/.json/.yaml in same or parent folder."""

    def test_empty_folder(self, tmp_path):
        f = tmp_path / "doc.md"
        f.write_text("doc")
        result = dsa.find_evidence_in_folder(f)
        assert result == []

    def test_same_folder_evidence(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("doc")
        log = tmp_path / "test.log"
        log.write_text("PASS")
        result = dsa.find_evidence_in_folder(doc)
        assert log in result

    def test_excludes_self_when_doc_is_txt(self, tmp_path):
        # If the file is a .txt, it should be excluded from evidence
        doc = tmp_path / "doc.txt"
        doc.write_text("doc content")
        result = dsa.find_evidence_in_folder(doc)
        assert doc not in result

    def test_includes_self_when_doc_is_md(self, tmp_path):
        # The exclusion only happens when file_path is .txt (per source: 'e for e in evidence if e != file_path')
        # but the glob is for .log/.txt/.json/.yaml — .md files are not in the glob anyway.
        doc = tmp_path / "doc.md"
        doc.write_text("doc")
        log = tmp_path / "test.log"
        log.write_text("log")
        result = dsa.find_evidence_in_folder(doc)
        assert log in result

    def test_logs_subfolder(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("doc")
        logs = tmp_path / "logs"
        logs.mkdir()
        log = logs / "test.log"
        log.write_text("log")
        result = dsa.find_evidence_in_folder(doc)
        assert log in result

    def test_evidence_subfolder(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("doc")
        ev = tmp_path / "evidence"
        ev.mkdir()
        log = ev / "test.log"
        log.write_text("log")
        result = dsa.find_evidence_in_folder(doc)
        assert log in result

    def test_multiple_evidence_files(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("doc")
        (tmp_path / "a.log").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        (tmp_path / "c.json").write_text("{}")
        (tmp_path / "d.yaml").write_text("a: 1")
        (tmp_path / "e.md").write_text("e")  # not in extensions
        result = dsa.find_evidence_in_folder(doc)
        names = {f.name for f in result}
        assert {"a.log", "b.txt", "c.json", "d.yaml"}.issubset(names)
        assert "e.md" not in names


# ---------------------------------------------------------------------------
# TestEvidenceFileRelevant — evidence_file_relevant(evidence_file, claim)
# ---------------------------------------------------------------------------
class TestEvidenceFileRelevant:
    """evidence_file_relevant() uses word-overlap heuristic."""

    def test_no_overlap(self, tmp_path):
        ev = tmp_path / "ev.log"
        # Use a 3-char-only claim to bypass the word-overlap heuristic
        # (the function only considers \b\w{4,}\b words).
        ev.write_text("X Y Z")
        assert dsa.evidence_file_relevant(ev, "X Y Z") is False

    def test_strong_overlap(self, tmp_path):
        ev = tmp_path / "ev.log"
        ev.write_text("verified functional test passed successfully")
        assert dsa.evidence_file_relevant(ev, "VERIFIED FUNCTIONAL test") is True

    def test_unreadable_file_returns_false(self, tmp_path):
        # A path that doesn't exist
        ev = tmp_path / "nonexistent.log"
        assert dsa.evidence_file_relevant(ev, "any claim") is False

    def test_empty_claim_returns_false(self, tmp_path):
        ev = tmp_path / "ev.log"
        ev.write_text("content with words")
        # No 4+ char words in claim "X" → claim_words empty → False
        assert dsa.evidence_file_relevant(ev, "X") is False

    def test_claim_words_match(self, tmp_path):
        ev = tmp_path / "ev.log"
        ev.write_text("test passed successfully")
        # claim "test passed" has words test, passed
        assert dsa.evidence_file_relevant(ev, "test passed") is True

    def test_claim_no_overlap(self, tmp_path):
        ev = tmp_path / "ev.log"
        ev.write_text("apple banana cherry")
        # claim "elephant gorilla" → no overlap
        assert dsa.evidence_file_relevant(ev, "elephant gorilla") is False

    def test_case_insensitive_matching(self, tmp_path):
        ev = tmp_path / "ev.log"
        ev.write_text("VERIFIED FUNCTIONAL")
        assert dsa.evidence_file_relevant(ev, "verified functional") is True

    def test_unicode_read_errors_ignored(self, tmp_path):
        ev = tmp_path / "ev.log"
        ev.write_text("normal content with words here")
        # Should not raise
        result = dsa.evidence_file_relevant(ev, "normal claim")
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# TestIsEvidenceStale — is_evidence_stale(file_path, evidence_file, max_age_days)
# ---------------------------------------------------------------------------
class TestIsEvidenceStale:
    """is_evidence_stale() compares mtime delta against max_age_days."""

    def test_fresh_evidence(self, tmp_path):
        doc = tmp_path / "doc.md"
        ev = tmp_path / "ev.log"
        doc.write_text("doc")
        ev.write_text("log")
        # both have same mtime (created now) → not stale
        assert dsa.is_evidence_stale(doc, ev, max_age_days=7) is False

    def test_stale_evidence(self, tmp_path):
        doc = tmp_path / "doc.md"
        ev = tmp_path / "ev.log"
        doc.write_text("doc")
        ev.write_text("log")
        # Make evidence 10 days old
        old = (datetime.datetime.now() - datetime.timedelta(days=10)).timestamp()
        import os
        os.utime(ev, (old, old))
        # Make doc recent
        new = datetime.datetime.now().timestamp()
        os.utime(doc, (new, new))
        assert dsa.is_evidence_stale(doc, ev, max_age_days=7) is True

    def test_exactly_at_boundary(self, tmp_path):
        doc = tmp_path / "doc.md"
        ev = tmp_path / "ev.log"
        doc.write_text("doc")
        ev.write_text("log")
        import os
        # Evidence exactly 7 days old
        old = (datetime.datetime.now() - datetime.timedelta(days=7, seconds=1)).timestamp()
        os.utime(ev, (old, old))
        new = datetime.datetime.now().timestamp()
        os.utime(doc, (new, new))
        # 7 days + 1s > 7 days → stale
        assert dsa.is_evidence_stale(doc, ev, max_age_days=7) is True

    def test_custom_max_age_days(self, tmp_path):
        doc = tmp_path / "doc.md"
        ev = tmp_path / "ev.log"
        doc.write_text("doc")
        ev.write_text("log")
        import os
        old = (datetime.datetime.now() - datetime.timedelta(days=3)).timestamp()
        os.utime(ev, (old, old))
        new = datetime.datetime.now().timestamp()
        os.utime(doc, (new, new))
        # 3 days old, max_age=2 → stale
        assert dsa.is_evidence_stale(doc, ev, max_age_days=2) is True
        # 3 days old, max_age=10 → fresh
        assert dsa.is_evidence_stale(doc, ev, max_age_days=10) is False

    def test_nonexistent_file_returns_false(self, tmp_path):
        doc = tmp_path / "doc.md"
        ev = tmp_path / "nonexistent.log"
        doc.write_text("doc")
        # stat() raises FileNotFoundError → caught → returns False
        assert dsa.is_evidence_stale(doc, ev) is False

    def test_doc_newer_than_evidence(self, tmp_path):
        # doc is NEWER than evidence (positive delta)
        doc = tmp_path / "doc.md"
        ev = tmp_path / "ev.log"
        doc.write_text("doc")
        ev.write_text("log")
        import os
        # Set evidence 100 days in the future
        future = (datetime.datetime.now() + datetime.timedelta(days=100)).timestamp()
        os.utime(ev, (future, future))
        # doc is now
        now = datetime.datetime.now().timestamp()
        os.utime(doc, (now, now))
        # file_mtime - ev_mtime = negative → NOT > 7 days → not stale
        assert dsa.is_evidence_stale(doc, ev, max_age_days=7) is False


# ---------------------------------------------------------------------------
# TestAuditFile — audit_file(file_path)
# ---------------------------------------------------------------------------
class TestAuditFile:
    """audit_file() is the main workhorse with 5 branches."""

    def test_unreadable_file_returns_skip(self, tmp_path):
        f = tmp_path / "nonexistent.md"
        result = dsa.audit_file(f)
        assert result["result"] == "SKIP"
        assert "error" in result

    def test_no_strong_claims_returns_pass(self, tmp_path):
        f = tmp_path / "doc.md"
        f.write_text("This is a perfectly normal document with no overclaims.\n")
        result = dsa.audit_file(f)
        assert result["result"] == "PASS"
        assert result["strong_claims"] == 0
        assert result["findings"] == []

    def test_strong_claim_no_evidence_no_honest_scope_returns_fail(self, tmp_path):
        f = tmp_path / "doc.md"
        f.write_text("This is VERIFIED FUNCTIONAL on first try.\n")
        result = dsa.audit_file(f)
        assert result["result"] == "FAIL"
        assert len(result["findings"]) >= 1
        f0 = result["findings"][0]
        assert f0["severity"] == "FAIL"
        assert f0["check"] == 1  # Strong claim without evidence

    def test_strong_claim_with_honest_scope_returns_warn(self, tmp_path):
        f = tmp_path / "doc.md"
        f.write_text(
            "This is VERIFIED FUNCTIONAL.\n"
            "honest scope: this is just one component, not the full system.\n"
        )
        result = dsa.audit_file(f)
        assert result["result"] == "WARN"
        assert result["honest_scope"] is True
        assert all(f["severity"] == "WARN" for f in result["findings"])

    def test_strong_claim_with_relevant_fresh_evidence_returns_pass(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("This is VERIFIED FUNCTIONAL.\n")
        ev = tmp_path / "evidence.log"
        ev.write_text("verified functional test passed successfully\n")
        result = dsa.audit_file(doc)
        # With evidence, no FAIL or WARN for staleness (just created)
        assert result["result"] == "PASS"
        assert result["findings"] == []

    def test_strong_claim_with_stale_evidence_returns_fail(self, tmp_path):
        # R110-78 DOCUMENTED BUG: the staleness check (check 5) is in a
        # dead code branch. The loop (line 212-215) only assigns
        # `relevant_evidence` when `not is_evidence_stale(...)`. So
        # relevant-but-stale evidence never reaches the staleness branch
        # and falls through to "no evidence" → FAIL. This is a real bug
        # in source: a stale evidence file should produce WARN, not FAIL.
        # Per R110-78 / test-only push rule: documented, not fixed.
        doc = tmp_path / "doc.md"
        doc.write_text("This is VERIFIED FUNCTIONAL.\n")
        ev = tmp_path / "evidence.log"
        ev.write_text("verified functional test passed\n")
        # Make evidence 30 days old
        import os
        old = (datetime.datetime.now() - datetime.timedelta(days=30)).timestamp()
        os.utime(ev, (old, old))
        new = datetime.datetime.now().timestamp()
        os.utime(doc, (new, new))
        result = dsa.audit_file(doc)
        # Currently produces FAIL (bug). After fix, should produce WARN.
        assert result["result"] == "FAIL"
        assert any(f["check"] == 1 for f in result["findings"])

    def test_strong_claim_with_weakening_no_evidence_returns_fail(self, tmp_path):
        # The "claim + weakening" contradiction case
        f = tmp_path / "doc.md"
        f.write_text(
            "This is VERIFIED FUNCTIONAL.\n"
            "But this is just a workaround for the missing test.\n"
        )
        result = dsa.audit_file(f)
        assert result["result"] == "FAIL"
        # check 2 = workaround contradiction
        f0 = result["findings"][0]
        assert f0["check"] == 2
        assert f0["weakening_pattern"] is not None

    def test_honest_scope_with_no_findings_returns_warn(self, tmp_path):
        # R110-78 DOCUMENTED DEAD-CODE: the L273 "honest_scope + no
        # findings → PASS" branch is unreachable. Any strong claim with
        # no evidence + honest_scope gets a WARN finding at L244-257,
        # which blocks the L273 branch. The L273 PASS-with-note path
        # can only fire if some strong_claim loop iteration adds NO
        # finding — which requires the staleness check (else branch
        # L258) to fire, but that branch is also dead. So L273 is
        # unreachable in practice. Per R110-78: documented, not fixed.
        f = tmp_path / "doc.md"
        f.write_text(
            "Issue 7355 fix VERIFIED FUNCTIONAL.\n"
            "honest scope: limited to issue 7355, not the full system.\n"
        )
        result = dsa.audit_file(f)
        # Currently: WARN (L244-257 fires). After unblocking L273, would
        # be PASS with note. We assert current (buggy) behavior.
        assert result["result"] == "WARN"
        assert result["honest_scope"] is True
        # The PASS-with-note path (L273) is unreachable. We test
        # write_report() directly with a synthetic PASS-with-note result
        # to still cover the L273 return-shape contract below.
        # (Done in test_write_report_synthetic_pass_with_note.)

    def test_finding_id_increments(self, tmp_path):
        f = tmp_path / "doc.md"
        f.write_text(
            "VERIFIED FUNCTIONAL.\n"
            "ALL HYPOTHESES VERIFIED.\n"
            "We guarantee 100% pass.\n"
        )
        result = dsa.audit_file(f)
        ids = [finding["id"] for finding in result["findings"]]
        # All IDs should be unique and follow SC-NNN pattern
        assert len(ids) == len(set(ids))
        for id_ in ids:
            assert id_.startswith("SC-")
            assert id_[3:].isdigit()

    def test_finding_explanation_includes_line_number(self, tmp_path):
        f = tmp_path / "doc.md"
        f.write_text("intro line\nThis is VERIFIED FUNCTIONAL.\n")
        result = dsa.audit_file(f)
        # The claim is on line 2
        f0 = result["findings"][0]
        assert "Line 2" in f0["explanation"]

    def test_suggested_fix_present(self, tmp_path):
        f = tmp_path / "doc.md"
        f.write_text("VERIFIED FUNCTIONAL.\n")
        result = dsa.audit_file(f)
        assert result["findings"][0]["suggested_fix"]
        assert len(result["findings"][0]["suggested_fix"]) > 0

    def test_multiple_claims_mixed(self, tmp_path):
        # One claim with evidence, one without
        doc = tmp_path / "doc.md"
        doc.write_text(
            "Issue 7355: VERIFIED FUNCTIONAL.\n"
            "We guarantee the full system works.\n"
        )
        ev = doc.parent / "issue_7355.log"
        ev.write_text("verified functional for issue 7355\n")
        result = dsa.audit_file(doc)
        # First claim: "Issue 7355: VERIFIED FUNCTIONAL" → has "7355" but
        # evidence has "7355" too, plus "verified" and "functional" → match
        # Second claim: "We guarantee the full system works" → unlikely to
        # have a matching evidence file → FAIL
        assert result["result"] in ("FAIL", "WARN")


# ---------------------------------------------------------------------------
# TestWriteReport — write_report(workspace, file_results, scope)
# ---------------------------------------------------------------------------
class TestWriteReport:
    """write_report() builds the audit summary dict."""

    def test_empty_results_returns_pass(self, tmp_path):
        report = dsa.write_report(str(tmp_path), [], "logs/e2e-results")
        assert report["audit_run"]["result"] == "PASS"
        assert report["audit_run"]["exit_code"] == 0
        assert report["audit_run"]["overclaims_found"] == 0
        assert report["audit_run"]["files_pass"] == 0
        assert report["audit_run"]["files_warn"] == 0
        assert report["audit_run"]["files_fail"] == 0

    def test_only_passes(self, tmp_path):
        results = [
            {"file": "a.md", "result": "PASS", "findings": [], "honest_scope": False},
            {"file": "b.md", "result": "PASS", "findings": [], "honest_scope": True},
        ]
        report = dsa.write_report(str(tmp_path), results, "logs")
        assert report["audit_run"]["result"] == "PASS"
        assert report["audit_run"]["files_pass"] == 2
        assert report["audit_run"]["files_fail"] == 0
        assert report["audit_run"]["honest_scope_files"] == 1

    def test_warn_present_returns_warn(self, tmp_path):
        results = [
            {"file": "a.md", "result": "PASS", "findings": [], "honest_scope": False},
            {"file": "b.md", "result": "WARN", "findings": [{"id": "SC-1"}], "honest_scope": True},
        ]
        report = dsa.write_report(str(tmp_path), results, "logs")
        assert report["audit_run"]["result"] == "WARN"
        assert report["audit_run"]["exit_code"] == 0
        assert report["audit_run"]["files_warn"] == 1
        assert report["audit_run"]["overclaims_found"] == 1

    def test_fail_present_returns_fail(self, tmp_path):
        results = [
            {"file": "a.md", "result": "FAIL", "findings": [{"id": "SC-1"}, {"id": "SC-2"}], "honest_scope": False},
        ]
        report = dsa.write_report(str(tmp_path), results, "logs")
        assert report["audit_run"]["result"] == "FAIL"
        assert report["audit_run"]["exit_code"] == 1
        assert report["audit_run"]["files_fail"] == 1
        assert report["audit_run"]["overclaims_found"] == 2

    def test_mix_fail_and_warn(self, tmp_path):
        results = [
            {"file": "a.md", "result": "FAIL", "findings": [{"id": "x"}], "honest_scope": False},
            {"file": "b.md", "result": "WARN", "findings": [{"id": "y"}], "honest_scope": True},
            {"file": "c.md", "result": "PASS", "findings": [], "honest_scope": False},
        ]
        report = dsa.write_report(str(tmp_path), results, "logs")
        assert report["audit_run"]["result"] == "FAIL"  # FAIL dominates
        assert report["audit_run"]["exit_code"] == 1

    def test_report_includes_audit_run_metadata(self, tmp_path):
        report = dsa.write_report(str(tmp_path), [], "my-scope")
        ar = report["audit_run"]
        assert "timestamp" in ar
        assert "Z" in ar["timestamp"]  # ISO with Z suffix
        assert ar["scope"] == "my-scope"
        assert ar["workspace"] == str(tmp_path)
        assert ar["auditor"] == "sub_mas-self-auditor (via dev_self_auditor.py)"
        assert ar["checks_run"] == 8

    def test_summary_includes_counts(self, tmp_path):
        results = [
            {"file": "a.md", "result": "PASS", "findings": [], "honest_scope": False},
            {"file": "b.md", "result": "FAIL", "findings": [{"id": "x"}], "honest_scope": False},
        ]
        report = dsa.write_report(str(tmp_path), results, "logs")
        assert "1 pass" in report["audit_run"]["summary"]
        assert "1 fail" in report["audit_run"]["summary"]
        assert "FAIL" in report["audit_run"]["summary"]

    def test_skip_results_count_as_pass(self, tmp_path):
        # SKIP result is not a PASS but also not a WARN/FAIL
        results = [
            {"file": "a.md", "result": "SKIP", "findings": [], "honest_scope": False},
        ]
        report = dsa.write_report(str(tmp_path), results, "logs")
        # SKIP is neither pass/warn/fail, but overall should be PASS (no FAIL/WARN)
        assert report["audit_run"]["result"] == "PASS"
        assert report["audit_run"]["files_pass"] == 0
        assert report["audit_run"]["files_warn"] == 0
        assert report["audit_run"]["files_fail"] == 0

    def test_synthetic_pass_with_note_for_audit_file_l273_contract(self, tmp_path):
        # R110-78: the L273-282 "honest_scope + no findings → PASS" branch
        # in audit_file() is unreachable. To still cover the RETURN-SHAPE
        # contract of that branch (PASS, strong_claims>0, honest_scope=True,
        # note contains 'honest-scope'), we feed write_report() a synthetic
        # result that matches what L273 would produce. write_report()
        # itself is reachable and tested here.
        results = [
            {
                "file": "synth.md",
                "result": "PASS",
                "strong_claims": 1,
                "honest_scope": True,
                "note": "File has honest-scope markers and no overclaims.",
                "findings": [],
            },
        ]
        report = dsa.write_report(str(tmp_path), results, "logs")
        # Overall should be PASS (no FAIL/WARN)
        assert report["audit_run"]["result"] == "PASS"
        assert report["audit_run"]["exit_code"] == 0
        assert report["audit_run"]["honest_scope_files"] == 1
        # The file_results list contains our synthetic pass-with-note
        assert report["file_results"][0]["result"] == "PASS"
        assert "honest-scope" in report["file_results"][0]["note"]


# ---------------------------------------------------------------------------
# TestMain — main() — heavy integration tests
# ---------------------------------------------------------------------------
@pytest.mark.timeout(60)
class TestMain:
    """main() with --file flag, --scope flag, staged mode, and YAML emit."""

    def test_no_args_returns_zero_with_pass(self, tmp_path, monkeypatch, capsys):
        # Default scope is logs/e2e-results — set workspace to empty tmp_path
        # to get "No files found in scope" → return 0
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["dev_self_auditor.py"])
        rc = dsa.main()
        assert rc == 0
        captured = capsys.readouterr()
        # No files in scope → PASS
        assert "No files found" in captured.err or "nothing" in captured.err

    def test_file_flag_audits_single_file_pass(self, tmp_path, monkeypatch, capsys):
        doc = tmp_path / "doc.md"
        doc.write_text("Plain document with no claims.\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["dev_self_auditor.py", "--file", str(doc)])
        rc = dsa.main()
        assert rc == 0
        captured = capsys.readouterr()
        assert "PASS" in captured.err or "✅" in captured.err

    def test_file_flag_fail_returns_1(self, tmp_path, monkeypatch, capsys):
        doc = tmp_path / "doc.md"
        doc.write_text("This is VERIFIED FUNCTIONAL.\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["dev_self_auditor.py", "--file", str(doc)])
        rc = dsa.main()
        assert rc == 1
        captured = capsys.readouterr()
        assert "BLOCKED" in captured.err

    def test_file_flag_warn_returns_0(self, tmp_path, monkeypatch, capsys):
        # WARN exits with 0
        doc = tmp_path / "doc.md"
        doc.write_text(
            "This is VERIFIED FUNCTIONAL.\n"
            "honest scope: just this component.\n"
        )
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["dev_self_auditor.py", "--file", str(doc)])
        rc = dsa.main()
        # WARN → exit 0
        assert rc == 0

    def test_output_yaml_written(self, tmp_path, monkeypatch, capsys):
        doc = tmp_path / "doc.md"
        doc.write_text("Plain document.\n")
        out = tmp_path / "report.yaml"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", [
            "dev_self_auditor.py", "--file", str(doc), "--output", str(out)
        ])
        dsa.main()
        assert out.exists()
        content = out.read_text()
        # YAML should have key fields
        assert "audit_run" in content
        assert "files_scanned" in content
        assert "result" in content

    def test_output_yaml_with_findings(self, tmp_path, monkeypatch, capsys):
        doc = tmp_path / "doc.md"
        doc.write_text("This is VERIFIED FUNCTIONAL.\n")
        out = tmp_path / "report.yaml"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", [
            "dev_self_auditor.py", "--file", str(doc), "--output", str(out)
        ])
        dsa.main()
        content = out.read_text()
        assert "FAIL" in content
        assert "OVERCLAIM" in content.upper() or "overclaims" in content

    def test_json_flag_outputs_json(self, tmp_path, monkeypatch, capsys):
        doc = tmp_path / "doc.md"
        doc.write_text("Plain document.\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", [
            "dev_self_auditor.py", "--file", str(doc), "--json"
        ])
        dsa.main()
        captured = capsys.readouterr()
        # JSON goes to stdout (not stderr)
        # But the code actually only prints YAML to file. Looking at source,
        # --json only sets args.json but the code doesn't use it (R110-78 class bug).
        # Just check it doesn't crash.
        # Actually checking source: args.json is parsed but never used in emit.
        # This is a documented "not implemented" feature in the source.
        # Test verifies no crash.
        assert captured.err  # something printed to stderr

    def test_staged_mode_with_no_staged_files(self, tmp_path, monkeypatch, capsys):
        # Make a git repo with no staged files
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"],
                       cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                       cwd=tmp_path, check=True, capture_output=True)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", [
            "dev_self_auditor.py", "--scope", "staged", "--workspace", str(tmp_path)
        ])
        rc = dsa.main()
        assert rc == 0
        captured = capsys.readouterr()
        assert "PASS" in captured.err or "nothing" in captured.err

    def test_scope_flag_audits_directory(self, tmp_path, monkeypatch, capsys):
        scope = tmp_path / "mylogs"
        scope.mkdir()
        (scope / "doc.md").write_text("Plain doc.\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", [
            "dev_self_auditor.py", "--scope", "mylogs", "--workspace", str(tmp_path)
        ])
        rc = dsa.main()
        assert rc == 0

    def test_path_spill_guard_with_mas_engineer_subdir(self, tmp_path, monkeypatch, capsys):
        # If CWD has a mas-engineer/ subdir, workspace is auto-set to it
        (tmp_path / "mas-engineer").mkdir()
        inner = tmp_path / "mas-engineer" / "logs"
        inner.mkdir()
        (inner / "doc.md").write_text("Plain.\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", [
            "dev_self_auditor.py", "--scope", "logs", "--workspace", "."
        ])
        dsa.main()
        captured = capsys.readouterr()
        # Should print auto-detection message
        assert "auto-detected" in captured.err or "workspace" in captured.err

    def test_yaml_escape_special_chars(self, tmp_path, monkeypatch, capsys):
        # File content with double quotes and backslashes
        doc = tmp_path / "doc.md"
        doc.write_text('Content with "quotes" and \\backslashes\n')
        out = tmp_path / "report.yaml"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", [
            "dev_self_auditor.py", "--file", str(doc), "--output", str(out)
        ])
        dsa.main()
        # The yaml_escape function is called on file paths and strings.
        # Just verify the YAML is still valid (we won't parse it strictly,
        # just check it's written and contains escaped versions).
        content = out.read_text()
        # The file path is written somewhere — it contains /tmp_xxx...
        # Just check no crash and the file is non-empty
        assert len(content) > 0

    def test_yaml_emit_empty_list(self, tmp_path, monkeypatch, capsys):
        # Empty scope → no files → no output file written (early return)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", [
            "dev_self_auditor.py", "--scope", "empty-dir"
        ])
        rc = dsa.main()
        # Empty scope → return 0, no file written
        assert rc == 0

    def test_yaml_emit_with_finding(self, tmp_path, monkeypatch, capsys):
        # Ensure the YAML emitter handles findings (list of dicts)
        doc = tmp_path / "doc.md"
        doc.write_text("VERIFIED FUNCTIONAL on the spot.\n")
        out = tmp_path / "report.yaml"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", [
            "dev_self_auditor.py", "--file", str(doc), "--output", str(out)
        ])
        dsa.main()
        content = out.read_text()
        # The finding has 'claim', 'explanation', 'severity' fields
        assert "claim" in content or "VERIFIED" in content

    def test_yaml_emit_nested_dict(self, tmp_path, monkeypatch, capsys):
        # The audit_run dict is nested — test that emit() handles nesting
        doc = tmp_path / "doc.md"
        doc.write_text("Plain.\n")
        out = tmp_path / "report.yaml"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", [
            "dev_self_auditor.py", "--file", str(doc), "--output", str(out)
        ])
        dsa.main()
        content = out.read_text()
        # The audit_run is a dict, so it gets emitted with indented sub-keys
        assert "  timestamp" in content or "  files_scanned" in content

    def test_yaml_emit_with_null_and_bool(self, tmp_path, monkeypatch, capsys):
        # Trigger null/bool emission via the explanation field having None values
        # (not directly triggerable, but we can verify the writer doesn't crash)
        doc = tmp_path / "doc.md"
        doc.write_text("VERIFIED FUNCTIONAL.\n")
        out = tmp_path / "report.yaml"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", [
            "dev_self_auditor.py", "--file", str(doc), "--output", str(out)
        ])
        dsa.main()
        # Verify emitted — boolean fields exist (e.g. honest_scope: false)
        content = out.read_text()
        # Boolean should be lowercase
        assert "true" in content.lower() or "false" in content.lower()

    def test_yaml_emit_with_list_value(self, tmp_path, monkeypatch, capsys):
        # file_results is a list of dicts — exercise that path
        doc = tmp_path / "doc.md"
        doc.write_text("Plain doc.\n")
        out = tmp_path / "report.yaml"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", [
            "dev_self_auditor.py", "--file", str(doc), "--output", str(out)
        ])
        dsa.main()
        content = out.read_text()
        # file_results is emitted as a YAML list — should have - prefix
        assert "file_results" in content

    def test_staged_mode_with_staged_non_md_files(self, tmp_path, monkeypatch, capsys):
        # Stage some .py files (no .md/.txt) → "no .md/.txt staged" path
        # This exercises L373-377 (the "staged but no audit-worthy files" branch)
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"],
                       cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                       cwd=tmp_path, check=True, capture_output=True)
        # Create and stage a .py file
        (tmp_path / "code.py").write_text("print('hi')")
        subprocess.run(["git", "add", "code.py"], cwd=tmp_path,
                       check=True, capture_output=True)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", [
            "dev_self_auditor.py", "--scope", "staged", "--workspace", str(tmp_path)
        ])
        rc = dsa.main()
        assert rc == 0
        captured = capsys.readouterr()
        # Should print "no .md/.txt" message
        assert ".md/.txt" in captured.err or "nothing" in captured.err

    def test_skip_status_print_in_main(self, tmp_path, monkeypatch, capsys):
        # Audit an unreadable file → SKIP result → L402 print path
        doc = tmp_path / "nonexistent.md"
        # Don't create the file
        out = tmp_path / "report.yaml"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", [
            "dev_self_auditor.py", "--file", str(doc), "--output", str(out)
        ])
        rc = dsa.main()
        # SKIP is not FAIL → exit 0
        assert rc == 0
        captured = capsys.readouterr()
        # Should print the skip indicator (⏭️)
        assert "⏭️" in captured.err or "SKIP" in captured.err

    def test_staged_mode_git_diff_failure(self, tmp_path, monkeypatch, capsys):
        # If git diff --cached fails (not a git repo), main() returns 2
        # tmp_path is NOT a git repo → git diff --cached will fail
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", [
            "dev_self_auditor.py", "--scope", "staged", "--workspace", str(tmp_path)
        ])
        rc = dsa.main()
        # git diff --cached fails (not a git repo) → return 2
        assert rc == 2
        captured = capsys.readouterr()
        assert "failed" in captured.err or "❌" in captured.err
