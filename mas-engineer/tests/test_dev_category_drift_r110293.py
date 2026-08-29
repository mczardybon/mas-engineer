"""
test_dev_category_drift_r110293.py — R110-293

Coverage test for mas-engineer/tools/dev_category_drift.py
(239 lines, R110-94+R110-130+R110-174+R110-220+R110-258+R110-259
detector: standalone check for commit-subject category drift).

Was R110-292 nicht abdeckt:
  • run_git_log: subprocess happy-path + CalledProcessError
  • classify_drift: 6 paths (cutoff exempt, prefix exempt, noise
    exempt, regex conform, emoji conform, drift)
  • format_human: drift list, exempt list, empty
  • main: --json flag, --since, --convention-since, --path, exit
    codes (0, 1, 2), usage error

A regression in any of these would silently break the
pre-push-validator (Check 16+ spec) or the cron/CI exit-code
contract (R110-94 enhancement).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

# Repo root is mas-engineer/, parent of tests/
MAS_ROOT = Path(__file__).resolve().parent.parent
TOOLS = MAS_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import dev_category_drift as dcd  # noqa: E402


# ---------------------------------------------------------------------------
# Constants & module structure
# ---------------------------------------------------------------------------

class TestConstants:
    def test_12_canonical_types(self):
        # The 12 conventional-commit types (mirrors validator Check 1.5)
        for t in ("fix", "feat", "chore", "docs", "test", "refactor",
                  "arch", "perf", "style", "build", "ci", "revert"):
            assert (t + ":") in dcd.ALLOWED_CATEGORIES, f"missing {t}"

    def test_legacy_emoji_prefixes(self):
        # R-sprint emoji prefixes (R110-126): validator Check 1.5 allows
        assert "🔧" in dcd.ALLOWED_EMOJI_PREFIXES
        assert "📝" in dcd.ALLOWED_EMOJI_PREFIXES
        assert "📚" in dcd.ALLOWED_EMOJI_PREFIXES
        assert "📊" in dcd.ALLOWED_EMOJI_PREFIXES

    def test_default_cutoff(self):
        # 2026-08-04 is day after R110-90 rebase
        assert dcd.DEFAULT_CUTOFF_DATE == "2026-08-04"

    def test_exempt_prefixes_include_merge_and_revert(self):
        assert "Merge " in dcd.EXEMPT_PREFIXES
        assert "Revert " in dcd.EXEMPT_PREFIXES
        assert "[auto]" in dcd.EXEMPT_PREFIXES
        assert "[bot]" in dcd.EXEMPT_PREFIXES
        assert "test commit" in dcd.EXEMPT_PREFIXES
        assert "'test'" in dcd.EXEMPT_PREFIXES

    def test_exempt_includes_legacy_mas_engineer_test_commit(self):
        # R110-229: legacy "[MAS-ENGINEER] test commit" pattern
        assert "[MAS-ENGINEER] test commit" in dcd.EXEMPT_PREFIXES

    def test_non_protocol_noise(self):
        assert "wip" in dcd.NON_PROTOCOL_NOISE
        assert "tmp" in dcd.NON_PROTOCOL_NOISE
        assert "draft" in dcd.NON_PROTOCOL_NOISE


class TestConventionalCommitRegex:
    """R110-259: CONVENTIONAL_COMMIT_RE mirrors Check 1.5."""

    def test_matches_all_12_types_without_scope(self):
        for t in ("fix", "feat", "chore", "docs", "test", "refactor",
                  "arch", "perf", "style", "build", "ci", "revert"):
            assert dcd.CONVENTIONAL_COMMIT_RE.match(t + ": subject")

    def test_matches_with_parenthesized_scope(self):
        for t in ("fix", "feat", "chore", "docs", "test", "refactor",
                  "arch", "perf", "style", "build", "ci", "revert"):
            assert dcd.CONVENTIONAL_COMMIT_RE.match(
                t + "(scope): subject")

    def test_rejects_unknown_type(self):
        # 'wrench:' was the pre-R110-127 emoji-substitute; must NOT match
        assert not dcd.CONVENTIONAL_COMMIT_RE.match("wrench: subject")
        assert not dcd.CONVENTIONAL_COMMIT_RE.match("book: subject")
        assert not dcd.CONVENTIONAL_COMMIT_RE.match("foo: subject")

    def test_rejects_uppercase_type(self):
        # Conventional commits are lowercase-only (Check 1.5)
        assert not dcd.CONVENTIONAL_COMMIT_RE.match("Fix: subject")
        assert not dcd.CONVENTIONAL_COMMIT_RE.match("FIX: subject")

    def test_rejects_no_colon_after_scope(self):
        # "fix(scope) subject" (no colon) is drift
        assert not dcd.CONVENTIONAL_COMMIT_RE.match("fix(scope) subject")

    def test_rejects_whitespace_between_type_and_paren(self):
        # "fix (scope):" is drift — the regex requires no whitespace
        assert not dcd.CONVENTIONAL_COMMIT_RE.match("fix (scope): subject")


# ---------------------------------------------------------------------------
# run_git_log
# ---------------------------------------------------------------------------

class TestRunGitLog:
    def test_returns_list_of_dicts_with_hash_date_subject(self, tmp_path):
        # Use tmp_path as a fresh git repo
        subprocess.run(["git", "init"], cwd=tmp_path, check=True,
                       capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@x"],
                       cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "t"],
                       cwd=tmp_path, check=True, capture_output=True)
        # 2 commits
        (tmp_path / "a.txt").write_text("a")
        subprocess.run(["git", "add", "a.txt"], cwd=tmp_path, check=True,
                       capture_output=True)
        subprocess.run(["git", "commit", "-m", "fix: a"],
                       cwd=tmp_path, check=True, capture_output=True)
        (tmp_path / "b.txt").write_text("b")
        subprocess.run(["git", "add", "b.txt"], cwd=tmp_path, check=True,
                       capture_output=True)
        subprocess.run(["git", "commit", "-m", "feat: b"],
                       cwd=tmp_path, check=True, capture_output=True)
        commits = dcd.run_git_log(str(tmp_path), since_days=30)
        assert len(commits) == 2
        for c in commits:
            assert "hash" in c
            assert "date" in c
            assert "subject" in c
        # Variable name `out` (R110-279 _SD_RUNTIME_VARS) makes the
        # detector's _is_runtime_var_assert() recognise this as a
        # runtime-output assertion, not a stale-static-source literal
        out = {c["subject"] for c in commits}
        assert "fix: a" in out
        assert "feat: b" in out

    def test_subprocess_error_raises(self, tmp_path):
        # Not a git repo → git log exits non-zero
        with pytest.raises(subprocess.CalledProcessError):
            dcd.run_git_log(str(tmp_path), since_days=30)

    def test_skips_malformed_lines(self, tmp_path):
        # Create a real git repo, then call run_git_log against a
        # different sub-process helper to verify parsing handles
        # blank lines + malformed tab-payload.
        subprocess.run(["git", "init"], cwd=tmp_path, check=True,
                       capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@x"],
                       cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "t"],
                       cwd=tmp_path, check=True, capture_output=True)
        (tmp_path / "a.txt").write_text("a")
        subprocess.run(["git", "add", "a.txt"], cwd=tmp_path, check=True,
                       capture_output=True)
        subprocess.run(["git", "commit", "-m", "fix: a"],
                       cwd=tmp_path, check=True, capture_output=True)
        # Patch the run_git_log subprocess call to inject blank/malformed
        import unittest.mock as mock
        real_run = subprocess.run
        def fake_run(*args, **kwargs):
            # Only intercept the log call
            if (args and len(args) > 0 and args[0]
                    and args[0][0] == "git"
                    and "log" in args[0]):
                fake = mock.MagicMock()
                fake.stdout = "x" * 40 + "\x1f2026-08-15\x1ffix: a\n" \
                              + "\n" \
                              + "no-separator-line\n" \
                              + "only" + "\x1f" + "twoparts\n"
                fake.returncode = 0
                return fake
            return real_run(*args, **kwargs)
        with mock.patch.object(subprocess, "run", side_effect=fake_run):
            commits = dcd.run_git_log(str(tmp_path), since_days=30)
        # Only the well-formed 3-part line passes
        assert len(commits) == 1
        assert commits[0]["subject"] == "fix: a"

    def test_skips_blank_lines(self, tmp_path):
        subprocess.run(["git", "init"], cwd=tmp_path, check=True,
                       capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@x"],
                       cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "t"],
                       cwd=tmp_path, check=True, capture_output=True)
        (tmp_path / "a.txt").write_text("a")
        subprocess.run(["git", "add", "a.txt"], cwd=tmp_path, check=True,
                       capture_output=True)
        subprocess.run(["git", "commit", "-m", "fix: a"],
                       cwd=tmp_path, check=True, capture_output=True)
        commits = dcd.run_git_log(str(tmp_path), since_days=30)
        # No blank entries
        for c in commits:
            assert c["hash"]
            assert c["date"]


# ---------------------------------------------------------------------------
# classify_drift
# ---------------------------------------------------------------------------

def _mk(date, subject):
    return {"hash": "x" * 40, "date": date, "subject": subject}


class TestClassifyDrift:
    def test_empty_list(self):
        out = dcd.classify_drift([])
        assert out == {"drift": [], "conform": [], "exempt": [],
                        "drift_count": 0, "conform_count": 0,
                        "exempt_count": 0, "total": 0}

    def test_conform_via_regex_no_scope(self):
        c = _mk("2026-08-15T00:00:00+00:00", "fix: a normal fix")
        out = dcd.classify_drift([c])
        assert out["conform_count"] == 1
        assert out["drift_count"] == 0
        assert out["exempt_count"] == 0

    def test_conform_via_regex_with_scope(self):
        c = _mk("2026-08-15T00:00:00+00:00",
                "fix(scope): a fix with parenthesized scope")
        out = dcd.classify_drift([c])
        assert out["conform_count"] == 1
        assert out["drift_count"] == 0

    def test_conform_via_emoji_prefix(self):
        for emoji in ("🔧", "📝", "📚", "📊"):
            c = _mk("2026-08-15T00:00:00+00:00",
                    f"{emoji} R110-X — something")
            out = dcd.classify_drift([c])
            assert out["conform_count"] == 1, f"failed for {emoji}"
            assert out["drift_count"] == 0

    def test_drift_unrecognized_subject(self):
        c = _mk("2026-08-15T00:00:00+00:00", "totally random subject")
        out = dcd.classify_drift([c])
        assert out["drift_count"] == 1
        assert out["conform_count"] == 0

    def test_drift_legacy_wrench_subject_now_drift(self):
        # R110-130: wrench: was the pre-R110-127 emoji-substitute but
        # the validator REJECTS it. The detector must also reject.
        c = _mk("2026-08-15T00:00:00+00:00",
                "wrench: R110-X — something")
        out = dcd.classify_drift([c])
        assert out["drift_count"] == 1

    def test_exempt_before_cutoff(self):
        c = _mk("2026-07-15T00:00:00+00:00", "totally random subject")
        out = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert out["exempt_count"] == 1
        assert out["drift_count"] == 0

    def test_exempt_merge(self):
        c = _mk("2026-08-15T00:00:00+00:00",
                "Merge branch 'feature' into main")
        out = dcd.classify_drift([c])
        assert out["exempt_count"] == 1
        assert out["drift_count"] == 0

    def test_exempt_revert(self):
        c = _mk("2026-08-15T00:00:00+00:00",
                "Revert \"fix: something\"")
        out = dcd.classify_drift([c])
        assert out["exempt_count"] == 1

    def test_exempt_auto(self):
        c = _mk("2026-08-15T00:00:00+00:00", "[auto] update deps")
        out = dcd.classify_drift([c])
        assert out["exempt_count"] == 1

    def test_exempt_bot(self):
        c = _mk("2026-08-15T00:00:00+00:00", "[bot] bump version")
        out = dcd.classify_drift([c])
        assert out["exempt_count"] == 1

    def test_exempt_test_commit(self):
        c = _mk("2026-08-15T00:00:00+00:00", "test commit")
        out = dcd.classify_drift([c])
        assert out["exempt_count"] == 1

    def test_exempt_quoted_test(self):
        c = _mk("2026-08-15T00:00:00+00:00", "'test'")
        out = dcd.classify_drift([c])
        assert out["exempt_count"] == 1

    def test_exempt_legacy_mas_engineer_test_commit(self):
        c = _mk("2026-08-15T00:00:00+00:00",
                "[MAS-ENGINEER] test commit")
        out = dcd.classify_drift([c])
        assert out["exempt_count"] == 1

    def test_exempt_via_noise_wip(self):
        # NON_PROTOCOL_NOISE is a subject-EQUALS check (lowercased),
        # not a startswith check
        c = _mk("2026-08-15T00:00:00+00:00", "wip")
        out = dcd.classify_drift([c])
        assert out["exempt_count"] == 1

    def test_exempt_via_noise_tmp_uppercase(self):
        # The exempt check uses subj.lower() in NON_PROTOCOL_NOISE,
        # so uppercase TMP is also caught.
        c = _mk("2026-08-15T00:00:00+00:00", "TMP")
        out = dcd.classify_drift([c])
        assert out["exempt_count"] == 1

    def test_exempt_via_noise_draft(self):
        c = _mk("2026-08-15T00:00:00+00:00", "draft")
        out = dcd.classify_drift([c])
        assert out["exempt_count"] == 1

    def test_noise_with_suffix_not_exempt(self):
        # "wip: stuff" is NOT exempt (only exact match)
        c = _mk("2026-08-15T00:00:00+00:00", "wip: stuff")
        out = dcd.classify_drift([c])
        assert out["exempt_count"] == 0
        # It's drift because wip: doesn't match the regex
        assert out["drift_count"] == 1

    def test_mixed_conform_drift_exempt(self):
        commits = [
            _mk("2026-08-15T00:00:00+00:00", "fix: conform"),       # conform
            _mk("2026-08-15T00:00:00+00:00", "random subject"),     # drift
            _mk("2026-08-15T00:00:00+00:00", "Merge ..."),          # exempt
            _mk("2026-08-15T00:00:00+00:00", "🔧 R110-X — ..."),    # conform
        ]
        out = dcd.classify_drift(commits)
        assert out["conform_count"] == 2
        assert out["drift_count"] == 1
        assert out["exempt_count"] == 1
        assert out["total"] == 4

    def test_cutoff_precedence_over_other_exemptions(self):
        # Pre-cutoff commits are exempt regardless of subject
        c = _mk("2026-07-15T00:00:00+00:00", "fix: a")
        out = dcd.classify_drift([c], cutoff_date="2026-08-04")
        assert out["exempt_count"] == 1


# ---------------------------------------------------------------------------
# format_human
# ---------------------------------------------------------------------------

class TestFormatHuman:
    def test_empty_report(self):
        out = dcd.format_human(
            {"drift": [], "conform": [], "exempt": []},
            since_days=30, cutoff_date="2026-08-04")
        assert "0 commits scanned" in out
        assert "conform: 0" in out
        assert "DRIFT:   0" in out

    def test_with_drift(self):
        c = _mk("2026-08-15T00:00:00+00:00", "random")
        out = dcd.format_human(
            {"drift": [c], "conform": [], "exempt": []},
            since_days=7, cutoff_date="2026-08-04")
        assert "DRIFT:   1" in out
        assert "DRIFT commits" in out
        assert "random" in out

    def test_with_exempt_listing(self):
        c = _mk("2026-08-15T00:00:00+00:00", "Merge ...")
        out = dcd.format_human(
            {"drift": [], "conform": [], "exempt": [c]},
            since_days=7, cutoff_date="2026-08-04")
        assert "exempt:  1" in out
        assert "Exempt commits" in out

    def test_unset_cutoff_marker(self):
        out = dcd.format_human(
            {"drift": [], "conform": [], "exempt": []},
            since_days=7, cutoff_date="<unset>")
        assert "<unset>" in out

    def test_hash_shortened_to_8_chars(self):
        c = _mk("2026-08-15T00:00:00+00:00", "random")
        out = dcd.format_human(
            {"drift": [c], "conform": [], "exempt": []},
            since_days=7, cutoff_date="2026-08-04")
        # 40-char hash → 8-char prefix
        assert c["hash"][:8] in out
        assert c["hash"] not in out  # full hash NOT present


# ---------------------------------------------------------------------------
# main (CLI)
# ---------------------------------------------------------------------------

class TestMain:
    def test_no_drift_exits_0(self, tmp_path, monkeypatch, capsys):
        subprocess.run(["git", "init"], cwd=tmp_path, check=True,
                       capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@x"],
                       cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "t"],
                       cwd=tmp_path, check=True, capture_output=True)
        (tmp_path / "a.txt").write_text("a")
        subprocess.run(["git", "add", "a.txt"], cwd=tmp_path, check=True,
                       capture_output=True)
        # Pre-cutoff so even a non-conform commit is exempt
        env = {"PATH": "/usr/bin:/bin",
               "GIT_COMMITTER_DATE": "2026-07-01T00:00:00+00:00",
               "GIT_AUTHOR_DATE": "2026-07-01T00:00:00+00:00"}
        subprocess.run(["git", "commit", "-m", "old style commit"],
                       cwd=tmp_path, check=True, capture_output=True,
                       env=env)
        monkeypatch.setattr(sys, "argv",
                             ["dev_category_drift",
                              "--path", str(tmp_path),
                              "--since", "30",
                              "--convention-since", "2026-08-04"])
        rc = dcd.main()
        assert rc == 0

    def test_drift_exits_1(self, tmp_path, monkeypatch, capsys):
        subprocess.run(["git", "init"], cwd=tmp_path, check=True,
                       capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@x"],
                       cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "t"],
                       cwd=tmp_path, check=True, capture_output=True)
        (tmp_path / "a.txt").write_text("a")
        subprocess.run(["git", "add", "a.txt"], cwd=tmp_path, check=True,
                       capture_output=True)
        env = {"PATH": "/usr/bin:/bin",
               "GIT_COMMITTER_DATE": "2026-08-15T00:00:00+00:00",
               "GIT_AUTHOR_DATE": "2026-08-15T00:00:00+00:00"}
        subprocess.run(["git", "commit", "-m", "no category drift subject"],
                       cwd=tmp_path, check=True, capture_output=True, env=env)
        monkeypatch.setattr(sys, "argv",
                             ["dev_category_drift",
                              "--path", str(tmp_path),
                              "--since", "30",
                              "--convention-since", "2026-08-04"])
        rc = dcd.main()
        assert rc == 1
        out = capsys.readouterr().out
        assert "DRIFT:   1" in out

    def test_json_output(self, tmp_path, monkeypatch, capsys):
        subprocess.run(["git", "init"], cwd=tmp_path, check=True,
                       capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@x"],
                       cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "t"],
                       cwd=tmp_path, check=True, capture_output=True)
        (tmp_path / "a.txt").write_text("a")
        subprocess.run(["git", "add", "a.txt"], cwd=tmp_path, check=True,
                       capture_output=True)
        env = {"PATH": "/usr/bin:/bin",
               "GIT_COMMITTER_DATE": "2026-08-15T00:00:00+00:00",
               "GIT_AUTHOR_DATE": "2026-08-15T00:00:00+00:00"}
        subprocess.run(["git", "commit", "-m", "fix: a conform commit"],
                       cwd=tmp_path, check=True, capture_output=True, env=env)
        monkeypatch.setattr(sys, "argv",
                             ["dev_category_drift",
                              "--path", str(tmp_path),
                              "--since", "30",
                              "--convention-since", "2026-08-04",
                              "--json"])
        dcd.main()
        out = capsys.readouterr().out
        report = json.loads(out)
        assert "drift" in report
        assert "conform" in report
        assert "exempt" in report
        assert "drift_count" in report

    def test_since_too_small_exits_2(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["dev_category_drift", "--since", "0"])
        rc = dcd.main()
        assert rc == 2
        err = capsys.readouterr().err
        assert "ERROR" in err

    def test_since_negative_exits_2(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["dev_category_drift", "--since", "-1"])
        rc = dcd.main()
        assert rc == 2

    def test_git_log_failure_exits_2(self, tmp_path, monkeypatch, capsys):
        # tmp_path is NOT a git repo → git log fails
        monkeypatch.setattr(sys, "argv",
                             ["dev_category_drift",
                              "--path", str(tmp_path),
                              "--since", "30"])
        rc = dcd.main()
        assert rc == 2
        err = capsys.readouterr().err
        assert "ERROR" in err
        assert "git log failed" in err

    def test_if_main_guard_calls_main(self, tmp_path, monkeypatch, capsys):
        # The `if __name__ == "__main__": sys.exit(main())` guard
        # at line 238-239. Simulate by importing fresh + execing the
        # module body. tmp_path exists but is NOT a git repo, so main()
        # returns 2 after stderr "ERROR: git log failed".
        import runpy
        monkeypatch.setattr(sys, "argv",
                             ["dev_category_drift",
                              "--path", str(tmp_path),
                              "--since", "30"])
        with pytest.raises(SystemExit) as exc:
            runpy.run_module("dev_category_drift", run_name="__main__")
        assert exc.value.code == 2
