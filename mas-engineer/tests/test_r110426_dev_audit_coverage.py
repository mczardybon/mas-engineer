"""R110-426 — coverage-push r6: tools/dev_audit.py 0% → 100%.

Pure-stdlib audit-log + lock + pre-commit-check module (111 lines).
Easy target — monkeypatch MAS_DIR/STATE_DIR/AUDIT_FILE/LOCK_FILE onto
tmp_path, then exercise every function + the CLI dispatch.

Targets:
- _load: missing file → [] ; populated file → entries
- log: OK status (no lock), CRITICAL status (creates lock file), goal
  truncation (>200 chars), GOOSE_SESSION_TAG env var, ensure STATE_DIR
  created on demand
- check: no-lock-no-violations (exit 0), lock-exists (exit 1),
  violations-exit-1, last-action-not-OK (exit 1)
- status: empty (no entries), with mixed OK/BLOCKED/CRITICAL counts,
  with lock-file present
- unlock: no-lock (return), lock-without-force (exit 1), lock-with-force
  (removes file + logs UNLOCK action)
- violations: empty (no violations), with violations
- main: --log (all args), --check, --status, --unlock, --unlock --force,
  --violations, no-args (exit 1), unknown-cmd (exit 1)
- __main__ exec block via in-process exec()
"""

import io
import json
import os
import sys
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.dev_audit as aud  # noqa: E402


@pytest.fixture
def ws(tmp_path, monkeypatch):
    """Synthetic workspace with monkeypatched module paths."""
    state_dir = tmp_path / ".mase"
    audit_file = state_dir / "audit.log.jsonl"
    lock_file = state_dir / ".disziplin_lock"
    monkeypatch.setattr(aud, "MAS_DIR", str(tmp_path))
    monkeypatch.setattr(aud, "STATE_DIR", str(state_dir))
    monkeypatch.setattr(aud, "AUDIT_FILE", str(audit_file))
    monkeypatch.setattr(aud, "LOCK_FILE", str(lock_file))
    return tmp_path


def _write_audit(entries):
    """Write a list of dicts to AUDIT_FILE as jsonl."""
    p = Path(aud.AUDIT_FILE)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


# ─────────────────────────────────────────────────────────────────────
# _load
# ─────────────────────────────────────────────────────────────────────
class TestLoad:
    def test_missing_returns_empty(self, ws):
        assert aud._load() == []

    def test_populated_returns_entries(self, ws):
        _write_audit([
            {"ts": "2024-01-01T00:00:00", "status": "OK",
             "action": "WRITE", "agent": "x", "ziel": "f", "rule": ""},
            {"ts": "2024-01-02T00:00:00", "status": "BLOCKED",
             "action": "READ", "agent": "y", "ziel": "g", "rule": "R1"},
        ])
        entries = aud._load()
        assert len(entries) == 2
        assert entries[0]["status"] == "OK"

    def test_blank_lines_ignored(self, ws):
        Path(aud.AUDIT_FILE).parent.mkdir(parents=True, exist_ok=True)
        Path(aud.AUDIT_FILE).write_text(
            '{"ts": "t1", "status": "OK"}\n\n\n'
            '{"ts": "t2", "status": "OK"}\n'
        )
        entries = aud._load()
        assert len(entries) == 2


# ─────────────────────────────────────────────────────────────────────
# log
# ─────────────────────────────────────────────────────────────────────
class TestLog:
    def test_ok_status_appends_entry(self, ws):
        aud.log("WRITE", "gatekeeper", "f.py", "OK", "R1")
        entries = aud._load()
        assert len(entries) == 1
        e = entries[0]
        assert e["action"] == "WRITE"
        assert e["agent"] == "gatekeeper"
        assert e["ziel"] == "f.py"
        assert e["status"] == "OK"
        assert e["rule"] == "R1"
        assert "ts" in e

    def test_critical_creates_lock(self, ws, capsys):
        aud.log("WRITE", "gate", "f", "CRITICAL", "violation-1")
        assert Path(aud.LOCK_FILE).exists()
        content = Path(aud.LOCK_FILE).read_text()
        assert "CRITICAL" in content
        assert "violation-1" in content
        out = capsys.readouterr().out
        assert "CRITICAL" in out

    def test_goal_truncated_200_chars(self, ws):
        long_goal = "x" * 300
        aud.log("WRITE", "g", long_goal, "OK")
        e = aud._load()[0]
        assert len(e["ziel"]) == 200

    def test_goal_exactly_200_chars_kept(self, ws):
        goal = "x" * 200
        aud.log("WRITE", "g", goal, "OK")
        e = aud._load()[0]
        assert e["ziel"] == goal

    def test_goal_under_200_chars_kept(self, ws):
        goal = "x" * 50
        aud.log("WRITE", "g", goal, "OK")
        e = aud._load()[0]
        assert e["ziel"] == goal

    def test_session_tag_from_env(self, ws, monkeypatch):
        monkeypatch.setenv("GOOSE_SESSION_TAG", "session-42")
        aud.log("WRITE", "g", "f", "OK")
        e = aud._load()[0]
        assert e["session"] == "session-42"

    def test_session_tag_empty_when_env_missing(self, ws, monkeypatch):
        monkeypatch.delenv("GOOSE_SESSION_TAG", raising=False)
        aud.log("WRITE", "g", "f", "OK")
        e = aud._load()[0]
        assert e["session"] == ""

    def test_state_dir_created_on_demand(self, ws):
        # STATE_DIR doesn't exist yet → log creates it
        assert not Path(aud.STATE_DIR).exists()
        aud.log("WRITE", "g", "f", "OK")
        assert Path(aud.STATE_DIR).exists()

    def test_no_rule_default_empty(self, ws):
        aud.log("WRITE", "g", "f", "OK")
        e = aud._load()[0]
        assert e["rule"] == ""


# ─────────────────────────────────────────────────────────────────────
# check (pre-commit)
# ─────────────────────────────────────────────────────────────────────
class TestCheck:
    def test_clean_exit_zero(self, ws, monkeypatch):
        # No lock, no entries, no violations → exit 0
        monkeypatch.setattr(sys, "exit", lambda code=0: (_ for _ in ()).throw(SystemExit(code)))
        with pytest.raises(SystemExit) as exc:
            aud.check()
        assert exc.value.code == 0

    def test_lock_exists_blocks(self, ws, monkeypatch, capsys):
        Path(aud.LOCK_FILE).parent.mkdir(parents=True, exist_ok=True)
        Path(aud.LOCK_FILE).write_text("CRITICAL: prior violation")
        with pytest.raises(SystemExit) as exc:
            aud.check()
        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "BLOCKIERT" in out
        assert "prior violation" in out

    def test_violations_block(self, ws, monkeypatch, capsys):
        _write_audit([
            {"ts": "2024-01-01T00:00:00", "status": "BLOCKED",
             "action": "WRITE", "agent": "g", "ziel": "f.py", "rule": "R1"},
        ])
        with pytest.raises(SystemExit) as exc:
            aud.check()
        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "BLOCKIERT" in out
        assert "R1" in out

    def test_last_action_not_ok_blocks(self, ws, monkeypatch, capsys):
        # Status not BLOCKED/CRITICAL but not OK either → blocks
        _write_audit([
            {"ts": "2024-01-01T00:00:00", "status": "WARN",
             "action": "x", "agent": "g", "ziel": "f", "rule": ""},
        ])
        with pytest.raises(SystemExit) as exc:
            aud.check()
        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "Letzte action not OK" in out

    def test_last_action_ok_passes(self, ws, monkeypatch, capsys):
        _write_audit([
            {"ts": "2024-01-01T00:00:00", "status": "OK",
             "action": "x", "agent": "g", "ziel": "f", "rule": ""},
        ])
        with pytest.raises(SystemExit) as exc:
            aud.check()
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "bestanden" in out


# ─────────────────────────────────────────────────────────────────────
# status
# ─────────────────────────────────────────────────────────────────────
class TestStatus:
    def test_empty_no_entries(self, ws, capsys):
        aud.status()
        out = capsys.readouterr().out
        assert "Empty" in out

    def test_mixed_counts(self, ws, capsys):
        _write_audit([
            {"ts": "2024-01-01T00:00:00", "status": "OK",
             "action": "x", "agent": "g", "ziel": "f", "rule": ""},
            {"ts": "2024-01-02T00:00:00", "status": "OK",
             "action": "x", "agent": "g", "ziel": "f", "rule": ""},
            {"ts": "2024-01-03T00:00:00", "status": "BLOCKED",
             "action": "x", "agent": "g", "ziel": "f", "rule": "R1"},
            {"ts": "2024-01-04T00:00:00", "status": "CRITICAL",
             "action": "x", "agent": "g", "ziel": "f", "rule": "R2"},
        ])
        aud.status()
        out = capsys.readouterr().out
        assert "2" in out  # 2 OK
        assert "1" in out  # 1 BLOCKED + 1 CRITICAL

    def test_status_only_ok_no_violations(self, ws, capsys):
        _write_audit([
            {"ts": "2024-01-01T00:00:00", "status": "OK",
             "action": "x", "agent": "g", "ziel": "f", "rule": ""},
        ])
        aud.status()
        out = capsys.readouterr().out
        # No "Letzte Violations" line
        assert "Violations" not in out

    def test_status_with_lock(self, ws, capsys):
        _write_audit([
            {"ts": "2024-01-01T00:00:00", "status": "CRITICAL",
             "action": "x", "agent": "g", "ziel": "f", "rule": "R1"},
        ])
        Path(aud.LOCK_FILE).parent.mkdir(parents=True, exist_ok=True)
        Path(aud.LOCK_FILE).write_text("CRITICAL: R1 - WRITE")
        aud.status()
        out = capsys.readouterr().out
        assert "GEFRIERT" in out


# ─────────────────────────────────────────────────────────────────────
# unlock
# ─────────────────────────────────────────────────────────────────────
class TestUnlock:
    def test_no_lock_returns(self, ws, monkeypatch, capsys):
        aud.unlock()
        out = capsys.readouterr().out
        assert "not gefroren" in out

    def test_lock_without_force_exits(self, ws, monkeypatch):
        Path(aud.LOCK_FILE).parent.mkdir(parents=True, exist_ok=True)
        Path(aud.LOCK_FILE).write_text("CRITICAL: prior")
        sys.argv = ["dev_audit.py"]  # no --force
        with pytest.raises(SystemExit) as exc:
            aud.unlock()
        assert exc.value.code == 1
        # Lock still exists
        assert Path(aud.LOCK_FILE).exists()

    def test_lock_with_force_removes_and_logs(self, ws, monkeypatch, capsys):
        Path(aud.LOCK_FILE).parent.mkdir(parents=True, exist_ok=True)
        Path(aud.LOCK_FILE).write_text("CRITICAL: prior")
        sys.argv = ["dev_audit.py", "--force"]
        aud.unlock()
        assert not Path(aud.LOCK_FILE).exists()
        # UNLOCK action logged
        entries = aud._load()
        assert any(e["action"] == "UNLOCK" for e in entries)
        out = capsys.readouterr().out
        assert "entriegelt" in out


# ─────────────────────────────────────────────────────────────────────
# violations
# ─────────────────────────────────────────────────────────────────────
class TestViolations:
    def test_no_violations(self, ws, capsys):
        _write_audit([
            {"ts": "2024-01-01T00:00:00", "status": "OK",
             "action": "x", "agent": "g", "ziel": "f", "rule": ""},
        ])
        aud.violations()
        out = capsys.readouterr().out
        assert "No Violations" in out

    def test_with_violations(self, ws, capsys):
        _write_audit([
            {"ts": "2024-01-01T00:00:00", "status": "BLOCKED",
             "action": "x", "agent": "g", "ziel": "f.py", "rule": "R1"},
            {"ts": "2024-01-02T00:00:00", "status": "CRITICAL",
             "action": "y", "agent": "h", "ziel": "g.py", "rule": "R2"},
            {"ts": "2024-01-03T00:00:00", "status": "OK",
             "action": "z", "agent": "i", "ziel": "h.py", "rule": ""},
        ])
        aud.violations()
        out = capsys.readouterr().out
        assert "2 Violations" in out
        assert "R1" in out
        assert "R2" in out

    def test_no_entries(self, ws, capsys):
        aud.violations()
        out = capsys.readouterr().out
        assert "No Violations" in out


# ─────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────
class TestMain:
    def test_no_args_exit_1(self, ws, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["dev_audit.py"])
        with pytest.raises(SystemExit) as exc:
            aud.main()
        assert exc.value.code == 1

    def test_unknown_cmd_exit_1(self, ws, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["dev_audit.py", "--bogus"])
        with pytest.raises(SystemExit) as exc:
            aud.main()
        assert exc.value.code == 1

    def test_log_cmd_all_args(self, ws, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", [
            "dev_audit.py", "--log",
            "--action", "WRITE",
            "--agent", "gatekeeper",
            "--ziel", "f.py",
            "--status", "OK",
            "--rule", "R1",
        ])
        aud.main()
        entries = aud._load()
        assert len(entries) == 1
        assert entries[0]["action"] == "WRITE"
        out = capsys.readouterr().out
        assert "Audit:" in out

    def test_log_cmd_defaults(self, ws, monkeypatch, capsys):
        # Missing → defaults to "?" / "OK" / ""
        monkeypatch.setattr(sys, "argv", ["dev_audit.py", "--log"])
        aud.main()
        e = aud._load()[0]
        assert e["action"] == "?"
        assert e["status"] == "OK"
        assert e["rule"] == ""

    def test_check_cmd(self, ws, monkeypatch):
        # No entries → exit 0
        monkeypatch.setattr(sys, "argv", ["dev_audit.py", "--check"])
        with pytest.raises(SystemExit) as exc:
            aud.main()
        assert exc.value.code == 0

    def test_check_cmd_blocked(self, ws, monkeypatch):
        _write_audit([
            {"ts": "2024-01-01T00:00:00", "status": "BLOCKED",
             "action": "x", "agent": "g", "ziel": "f", "rule": "R1"},
        ])
        monkeypatch.setattr(sys, "argv", ["dev_audit.py", "--check"])
        with pytest.raises(SystemExit) as exc:
            aud.main()
        assert exc.value.code == 1

    def test_status_cmd(self, ws, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["dev_audit.py", "--status"])
        aud.main()
        out = capsys.readouterr().out
        assert "AUDIT" in out or "Empty" in out

    def test_unlock_cmd_no_lock(self, ws, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["dev_audit.py", "--unlock"])
        aud.main()
        out = capsys.readouterr().out
        assert "not gefroren" in out

    def test_unlock_cmd_with_force(self, ws, monkeypatch, capsys):
        Path(aud.LOCK_FILE).parent.mkdir(parents=True, exist_ok=True)
        Path(aud.LOCK_FILE).write_text("CRITICAL: prior")
        monkeypatch.setattr(sys, "argv", ["dev_audit.py", "--unlock", "--force"])
        aud.main()
        assert not Path(aud.LOCK_FILE).exists()

    def test_violations_cmd(self, ws, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["dev_audit.py", "--violations"])
        aud.main()
        out = capsys.readouterr().out
        assert "No Violations" in out


# ─────────────────────────────────────────────────────────────────────
# __main__ exec
# ─────────────────────────────────────────────────────────────────────
class TestMainExec:
    def test_exec_main(self, ws, monkeypatch):
        script = (Path(__file__).resolve().parents[1] /
                  "tools" / "dev_audit.py").read_text()
        old_argv = sys.argv
        try:
            sys.argv = ["dev_audit.py", "--violations"]
            buf = io.StringIO()
            with redirect_stdout(buf):
                exec(compile(script, "dev_audit.py", "exec"),
                     {"__name__": "__main__", "__file__": "dev_audit.py"})
            assert "No Violations" in buf.getvalue()
        finally:
            sys.argv = old_argv
