"""R110-478 — coverage-push r15: tools/dev_category_drift.py 65% → 100%

84 stmts. Missed: 4 lines (249-250, 279-280) when imported via
'dev_category_drift' (legacy direct-import). When properly imported
via 'tools.dev_category_drift' (package form), 29 lines missed.

KEY OBSERVATIONS:
- classify_drift has 5 branches in order:
  1. EXEMPT_HASHES prefix match → exempt
  2. cutoff_date pre-protocol → exempt
  3. EXEMPT_PREFIXES or NON_PROTOCOL_NOISE → exempt
  4. CONVENTIONAL_COMMIT_RE match → conform
  5. ALLOWED_EMOJI_PREFIXES start → conform
  6. R_SPRINT_COLON_RE match → conform
  7. else → drift
- run_git_log runs `git log` subprocess with --since=N days.
- format_human builds multi-line string with drift/exempt lists.
- main() returns: 0 (no drift), 1 (drift), 2 (bad usage)

PITFALLS:
- EXEMPT_HASHES matches ONLY the first 7 chars of the hash
- cutoff_date comparison uses c["date"][:10] (date prefix only)
- NON_PROTOCOL_NOISE comparison is .lower() — case-insensitive
- ALLOWED_EMOJI_PREFIXES are START-MATCHES, not equals
- R_SPRINT_COLON_RE accepts "R110-303:" OR "R110-303 phase 2:"
  OR "R110-303 follow-up:" OR "R110-303 sub-name:" etc.
"""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools import dev_category_drift as dcd  # noqa: E402


def make_commit(hash, date, subject):
    return {"hash": hash, "date": date, "subject": subject}


# ─────────────────────────────────────────────────────────────────────
# classify_drift — branch coverage
# ─────────────────────────────────────────────────────────────────────
class TestClassifyDrift:
    # --- Branch 1: EXEMPT_HASHES ---
    def test_exempt_hash_short_match(self):
        # EXEMPT_HASHES contains "e382acd" (7 chars)
        c = make_commit("e382acd0123", "2026-09-07", "[]")
        r = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert len(r["exempt"]) == 1
        assert len(r["drift"]) == 0

    def test_exempt_hash_7char_only(self):
        # Only the first 7 chars matter
        c = make_commit("e382acd", "2026-09-07", "[]")
        r = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert len(r["exempt"]) == 1

    def test_non_exempt_hash_drifts(self):
        c = make_commit("ffffffff", "2026-09-07", "[]")
        r = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert len(r["drift"]) == 1

    # --- Branch 2: cutoff_date pre-protocol ---
    def test_pre_cutoff_exempt(self):
        # Date before cutoff_date → exempt (even with bad subject)
        c = make_commit("aaa1111", "2026-07-01T00:00:00+00:00", "random garbage subject")
        r = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert len(r["exempt"]) == 1

    def test_no_cutoff_no_exemption(self):
        # No cutoff_date → no pre-protocol exemption
        c = make_commit("aaa1111", "2026-07-01T00:00:00+00:00", "random garbage subject")
        r = dcd.classify_drift([c])
        assert len(r["drift"]) == 1

    def test_post_cutoff_with_bad_subject_drifts(self):
        c = make_commit("aaa1111", "2026-08-15T00:00:00+00:00", "random garbage subject")
        r = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert len(r["drift"]) == 1

    # --- Branch 3: EXEMPT_PREFIXES ---
    def test_merge_exempt(self):
        c = make_commit("aaa1111", "2026-09-07", "Merge branch 'x'")
        r = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert len(r["exempt"]) == 1

    def test_revert_exempt(self):
        c = make_commit("aaa1111", "2026-09-07", "Revert \"fix: foo\"")
        r = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert len(r["exempt"]) == 1

    def test_auto_exempt(self):
        c = make_commit("aaa1111", "2026-09-07", "[auto] update foo")
        r = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert len(r["exempt"]) == 1

    def test_bot_exempt(self):
        c = make_commit("aaa1111", "2026-09-07", "[bot] rebuild")
        r = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert len(r["exempt"]) == 1

    def test_test_commit_exempt(self):
        c = make_commit("aaa1111", "2026-09-07", "test commit")
        r = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert len(r["exempt"]) == 1

    def test_quoted_test_exempt(self):
        c = make_commit("aaa1111", "2026-09-07", "'test'")
        r = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert len(r["exempt"]) == 1

    def test_mas_engineer_test_commit_exempt(self):
        # R110-229 legacy pattern
        c = make_commit("aaa1111", "2026-09-07", "[MAS-ENGINEER] test commit")
        r = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert len(r["exempt"]) == 1

    def test_non_protocol_noise_wip(self):
        # NON_PROTOCOL_NOISE uses subj.lower() == noise (exact match)
        c = make_commit("aaa1111", "2026-09-07", "wip")
        r = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert len(r["exempt"]) == 1

    def test_non_protocol_noise_wip_uppercase(self):
        # case-insensitive via .lower()
        c = make_commit("aaa1111", "2026-09-07", "WIP")
        r = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert len(r["exempt"]) == 1

    def test_non_protocol_noise_tmp(self):
        c = make_commit("aaa1111", "2026-09-07", "tmp")
        r = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert len(r["exempt"]) == 1

    def test_non_protocol_noise_draft(self):
        c = make_commit("aaa1111", "2026-09-07", "draft")
        r = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert len(r["exempt"]) == 1

    def test_non_protocol_noise_substring_drifts(self):
        # "wip" not in subject as exact value → no exemption
        c = make_commit("aaa1111", "2026-09-07", "wip do not merge yet")
        r = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert len(r["drift"]) == 1

    # --- Branch 4: CONVENTIONAL_COMMIT_RE ---
    def test_fix_conform(self):
        c = make_commit("aaa1111", "2026-09-07", "fix: R110-478 broken parser")
        r = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert len(r["conform"]) == 1

    def test_fix_with_scope_conform(self):
        c = make_commit("aaa1111", "2026-09-07", "fix(parser): R110-478 broken")
        r = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert len(r["conform"]) == 1

    def test_feat_conform(self):
        c = make_commit("aaa1111", "2026-09-07", "feat: add new option")
        r = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert len(r["conform"]) == 1

    def test_all_12_types_conform(self):
        for t in ("fix", "feat", "chore", "docs", "test", "refactor",
                  "arch", "perf", "style", "build", "ci", "revert"):
            c = make_commit("aaa1111", "2026-09-07", f"{t}: example subject")
            r = dcd.classify_drift([c], cutoff_date="2026-08-04")
            assert len(r["conform"]) == 1, f"{t} should be conform"

    # --- Branch 5: ALLOWED_EMOJI_PREFIXES ---
    def test_emoji_wrench_conform(self):
        c = make_commit("aaa1111", "2026-09-07", "🔧 R110-478 — fix parser")
        r = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert len(r["conform"]) == 1

    def test_emoji_book_conform(self):
        c = make_commit("aaa1111", "2026-09-07", "📚 R110-478 — add docs")
        r = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert len(r["conform"]) == 1

    def test_emoji_others_conform(self):
        for e in ("📝", "📊", "🧹"):
            c = make_commit("aaa1111", "2026-09-07", f"{e} R110-478 — example")
            r = dcd.classify_drift([c], cutoff_date="2026-08-04")
            assert len(r["conform"]) == 1, f"{e} should be conform"

    # --- Branch 6: R_SPRINT_COLON_RE ---
    def test_r_sprint_colon_conform(self):
        # "R110-303: <topic> — desc"
        c = make_commit("aaa1111", "2026-09-07", "R110-303: phase 2 — coverage tests")
        r = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert len(r["conform"]) == 1

    def test_r_sprint_followup_conform(self):
        c = make_commit("aaa1111", "2026-09-07", "R110-303 follow-up: fix test")
        r = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert len(r["conform"]) == 1

    def test_r_sprint_subname_conform(self):
        c = make_commit("aaa1111", "2026-09-07", "R110-304 sub-name: do thing")
        r = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert len(r["conform"]) == 1

    def test_r_sprint_no_space_no_colon_drifts(self):
        # "R110-303" without ":" → no match
        c = make_commit("aaa1111", "2026-09-07", "R110-303 example subject")
        r = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert len(r["drift"]) == 1

    # --- Branch 7: drift (default) ---
    def test_random_subject_drifts(self):
        c = make_commit("aaa1111", "2026-09-07", "totally random commit message")
        r = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert len(r["drift"]) == 1

    def test_empty_subject_drifts(self):
        c = make_commit("aaa1111", "2026-09-07", "[]")
        r = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert len(r["drift"]) == 1

    def test_legacy_wrench_colon_drifts(self):
        # "wrench:" is NO longer in ALLOWED_CATEGORIES (R110-130)
        c = make_commit("aaa1111", "2026-09-07", "wrench: do the thing")
        r = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert len(r["drift"]) == 1

    def test_legacy_book_colon_drifts(self):
        c = make_commit("aaa1111", "2026-09-07", "book: do the thing")
        r = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert len(r["drift"]) == 1

    # --- Multiple commits mixed ---
    def test_mixed_commits(self):
        commits = [
            make_commit("aaa1111", "2026-09-07", "fix: good"),
            make_commit("bbb2222", "2026-09-07", "totally random"),
            make_commit("ccc3333", "2026-09-07", "🔧 R110-478 — also good"),
            make_commit("ddd4444", "2026-09-07", "Merge x"),
            make_commit("e382acd", "2026-09-07", "[]"),  # in EXEMPT_HASHES
        ]
        r = dcd.classify_drift(commits, cutoff_date="2026-08-04")
        assert r["total"] == 5
        assert r["conform_count"] == 2
        assert r["drift_count"] == 1
        assert r["exempt_count"] == 2

    # --- Subject whitespace stripped ---
    def test_subject_with_leading_whitespace(self):
        c = make_commit("aaa1111", "2026-09-07", "   fix: stripped subject")
        r = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert len(r["conform"]) == 1


# ─────────────────────────────────────────────────────────────────────
# run_git_log — real subprocess against test repo
# ─────────────────────────────────────────────────────────────────────
class TestRunGitLog:
    def test_empty_repo(self, tmp_path):
        # No git repo → subprocess.CalledProcessError raised
        with pytest.raises(Exception):
            dcd.run_git_log(str(tmp_path), 30)

    def test_valid_repo(self):
        # Use the actual repo — git log has many commits
        commits = dcd.run_git_log(".", 365)
        assert isinstance(commits, list)
        assert len(commits) > 0
        assert "hash" in commits[0]
        assert "date" in commits[0]
        assert "subject" in commits[0]

    def test_invalid_repo_path(self, tmp_path):
        with pytest.raises(subprocess.CalledProcessError):
            dcd.run_git_log(str(tmp_path), 30, cutoff_date="2026-08-04")

    def test_blank_lines_in_git_output(self, monkeypatch):
        # Mock subprocess.run to return stdout with blank lines
        fake_result = type("R", (), {
            "stdout": "aaa1111\x1f2026-09-07T00:00:00+00:00\x1fsubject1\n\n   \nbbb2222\x1f2026-09-07T00:00:00+00:00\x1fsubject2\n",
            "stderr": "",
            "returncode": 0,
        })()
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: fake_result)
        commits = dcd.run_git_log(".", 30)
        assert len(commits) == 2  # blank lines skipped

    def test_malformed_lines_skipped(self, monkeypatch):
        # Mock subprocess.run to return stdout with malformed lines
        # (lines without 3 parts separated by \x1f)
        fake_result = type("R", (), {
            "stdout": (
                "aaa1111\x1f2026-09-07T00:00:00+00:00\x1fsubject1\n"
                "broken_line_no_separator\n"
                "bbb2222\x1f2026-09-07T00:00:00+00:00\x1fsubject2\n"
                "ccc3333\x1f2026-09-07T00:00:00+00:00\n"  # only 2 parts
                "ddd4444\x1fdate\x1fsubject3\n"
            ),
            "stderr": "",
            "returncode": 0,
        })()
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: fake_result)
        commits = dcd.run_git_log(".", 30)
        # Only the well-formed lines (3 parts) are kept
        assert len(commits) == 3
        hashes = [c["hash"] for c in commits]
        assert "aaa1111" in hashes
        assert "bbb2222" in hashes
        assert "ddd4444" in hashes

    def test_called_process_error_in_cli(self):
        # When git log fails, main() catches CalledProcessError → exit 2
        # Patch run_git_log directly on the module to simulate CalledProcessError
        from unittest.mock import patch as mpatch
        old_argv = sys.argv
        sys.argv = ["dev_category_drift.py", "--since", "1"]
        try:
            with mpatch.object(dcd, "run_git_log",
                               side_effect=subprocess.CalledProcessError(
                                   128, "git log", stderr="fatal: not a git repo")):
                rc = dcd.main()
                assert rc == 2
        finally:
            sys.argv = old_argv


# ─────────────────────────────────────────────────────────────────────
# format_human
# ─────────────────────────────────────────────────────────────────────
class TestFormatHuman:
    def test_no_commits(self):
        report = {"drift": [], "conform": [], "exempt": []}
        out = dcd.format_human(report, 30, cutoff_date="2026-08-04")
        assert "30 days" in out
        assert "conform: 0" in out
        assert "DRIFT:   0" in out

    def test_with_drift(self):
        report = {
            "drift": [{"hash": "aaa1111", "date": "2026-09-07T00:00:00+00:00", "subject": "bad subject"}],
            "conform": [{"hash": "bbb2222", "date": "2026-09-07T00:00:00+00:00", "subject": "fix: good"}],
            "exempt": [],
        }
        out = dcd.format_human(report, 30, cutoff_date="2026-08-04")
        assert "DRIFT commits" in out
        assert "aaa1111" in out
        assert "bad subject" in out
        assert "2026-09-07" in out

    def test_with_exempt(self):
        report = {
            "drift": [],
            "conform": [],
            "exempt": [{"hash": "ccc3333", "date": "2026-09-07T00:00:00+00:00", "subject": "Merge x"}],
        }
        out = dcd.format_human(report, 30, cutoff_date="2026-08-04")
        assert "Exempt commits" in out
        assert "merge/revert/auto/bot/noise" in out


# ─────────────────────────────────────────────────────────────────────
# __main__ CLI via subprocess
# ─────────────────────────────────────────────────────────────────────
class TestCLI:
    def test_cli_clean(self):
        # --since 1 day may have drift if commits today; just check exit code
        r = subprocess.run(
            [sys.executable, "tools/dev_category_drift.py", "--since", "1"],
            capture_output=True, text=True, cwd="."
        )
        # Either exit 0 (clean) or 1 (drift) — but should NOT be 2 (usage error)
        assert r.returncode in (0, 1)

    def test_cli_json_flag(self):
        r = subprocess.run(
            [sys.executable, "tools/dev_category_drift.py", "--since", "1", "--json"],
            capture_output=True, text=True, cwd="."
        )
        parsed = json.loads(r.stdout)
        assert "drift" in parsed
        assert "conform" in parsed
        assert "exempt" in parsed

    def test_cli_usage_error_zero(self):
        # --since 0 → usage error → exit 2
        r = subprocess.run(
            [sys.executable, "tools/dev_category_drift.py", "--since", "0"],
            capture_output=True, text=True, cwd="."
        )
        assert r.returncode == 2
        assert "ERROR" in r.stderr

    def test_cli_usage_error_negative(self):
        r = subprocess.run(
            [sys.executable, "tools/dev_category_drift.py", "--since", "-5"],
            capture_output=True, text=True, cwd="."
        )
        assert r.returncode == 2

    def test_cli_bad_path(self):
        # Nonexistent path → subprocess.run raises FileNotFoundError
        with pytest.raises(FileNotFoundError):
            dcd.run_git_log("/nonexistent/repo", 30)

    def test_cli_custom_cutoff_date(self):
        r = subprocess.run(
            [sys.executable, "tools/dev_category_drift.py", "--since", "1",
             "--convention-since", "2026-08-04", "--json"],
            capture_output=True, text=True, cwd="."
        )
        parsed = json.loads(r.stdout)
        assert "drift" in parsed


# Required imports for subprocess calls
import subprocess
