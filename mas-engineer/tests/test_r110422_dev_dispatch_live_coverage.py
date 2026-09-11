"""R110-422 — coverage-push r4: tools/dev_dispatch_live.py 0% → ~95%.

Pure-stdlib daemon module, 126 executable stmts, currently 0%.
Targets every function plus the argparse main() dispatch.

Targets:
- _read_dispatch_log() missing file + valid entries + corrupt JSON + OSError
- _summarize() empty + mixed-status + avg-duration + last_entry_ts
- _write_dashboard_cache() new file + merge with existing + corrupt-existing
  + cache_dir-create-failure
- _run_once() integration: read → summarize → write
- _run_daemon() pid-write-fail + log-open-fail + happy-path-short + SIGTERM
- main() all 3 modes + no-args-helperror
"""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import dev_dispatch_live as dl  # noqa: E402


@pytest.fixture
def tmp_ws(tmp_path, monkeypatch):
    """Workspace root + monkeypatch DISPATCH_LOG to a tmp file."""
    log = tmp_path / "mas-dispatch.ndjson"
    monkeypatch.setattr(dl, "DISPATCH_LOG", str(log))
    return tmp_path


def _write_entry(log_path: Path, **kwargs):
    entry = {
        "id": "x", "parent_id": None, "ts": "now",
        "from": "a", "to": "b", "task": "t", "mode": "sync",
        "status": "running", "duration_ms": None,
    }
    entry.update(kwargs)
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")


# =============================================================================
# _read_dispatch_log
# =============================================================================
class TestReadDispatchLog:
    def test_missing_file_returns_empty(self, tmp_ws):
        assert dl._read_dispatch_log() == []

    def test_valid_entries(self, tmp_ws):
        log = tmp_ws / "mas-dispatch.ndjson"
        _write_entry(log, id="e1", status="running")
        _write_entry(log, id="e2", status="done")
        assert len(dl._read_dispatch_log()) == 2

    def test_corrupt_json_skipped(self, tmp_ws):
        log = tmp_ws / "mas-dispatch.ndjson"
        with open(log, "a") as f:
            f.write("garbage\n")
        _write_entry(log, id="e1")
        with open(log, "a") as f:
            f.write("more-garbage\n")
        entries = dl._read_dispatch_log()
        assert len(entries) == 1
        assert entries[0]["id"] == "e1"

    def test_blank_lines_skipped(self, tmp_ws):
        log = tmp_ws / "mas-dispatch.ndjson"
        log.write_text("\n   \n")
        assert dl._read_dispatch_log() == []


# =============================================================================
# _summarize
# =============================================================================
class TestSummarize:
    def test_empty(self):
        s = dl._summarize([])
        assert s["total_dispatches"] == 0
        assert s["running"] == 0
        assert s["done"] == 0
        assert s["errors"] == 0
        assert s["avg_duration_ms"] == 0
        assert s["last_entry_ts"] is None
        assert "timestamp" in s

    def test_mixed_statuses(self):
        entries = [
            {"status": "running", "duration_ms": 100, "ts": "2026-09-11T10:00:00Z"},
            {"status": "done", "duration_ms": 200, "ts": "2026-09-11T10:01:00Z"},
            {"status": "done", "duration_ms": 300, "ts": "2026-09-11T10:02:00Z"},
            {"status": "error", "duration_ms": 50, "ts": "2026-09-11T10:03:00Z"},
            {"status": "done", "errors": ["x"], "duration_ms": 150, "ts": "2026-09-11T10:04:00Z"},
        ]
        s = dl._summarize(entries)
        assert s["total_dispatches"] == 5
        assert s["running"] == 1
        assert s["done"] == 3
        # 2 errors: one with status="error" + one with errors=[]
        assert s["errors"] == 2
        # avg of 100,200,300,50,150 = 160
        assert s["avg_duration_ms"] == 160.0
        # last_entry_ts is last entry's ts
        assert s["last_entry_ts"] == "2026-09-11T10:04:00Z"

    def test_none_durations_excluded_from_avg(self):
        entries = [
            {"status": "running", "duration_ms": None, "ts": "t1"},
            {"status": "done", "duration_ms": 100, "ts": "t2"},
        ]
        s = dl._summarize(entries)
        # Only 100 in durations list → avg = 100
        assert s["avg_duration_ms"] == 100.0


# =============================================================================
# _write_dashboard_cache
# =============================================================================
class TestWriteDashboardCache:
    def test_creates_dir_and_writes_file(self, tmp_ws):
        summary = {"foo": "bar", "total_dispatches": 1}
        dl._write_dashboard_cache(str(tmp_ws), summary)
        cache = tmp_ws / ".mase" / "dashboards" / "data.json"
        assert cache.exists()
        data = json.loads(cache.read_text())
        assert data["live"] == summary

    def test_merges_with_existing(self, tmp_ws):
        # Pre-seed cache with non-"live" data
        cache_dir = tmp_ws / ".mase" / "dashboards"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "data.json"
        cache_file.write_text(json.dumps({"history": {"x": 1}}))
        summary = {"foo": "bar"}
        dl._write_dashboard_cache(str(tmp_ws), summary)
        data = json.loads(cache_file.read_text())
        assert data["history"] == {"x": 1}
        assert data["live"] == summary

    def test_corrupt_existing_replaced(self, tmp_ws):
        cache_dir = tmp_ws / ".mase" / "dashboards"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "data.json"
        cache_file.write_text("not valid json {{{")
        summary = {"foo": "bar"}
        dl._write_dashboard_cache(str(tmp_ws), summary)
        data = json.loads(cache_file.read_text())
        # Existing was corrupt → reset to {}, then live added
        assert data == {"live": summary}

    def test_workspace_creation_failure_handled(self, tmp_ws, monkeypatch, capsys):
        """Force makedirs to raise OSError → error printed to stderr, no crash."""
        def boom(*a, **kw):
            raise OSError("forced")
        monkeypatch.setattr(os, "makedirs", boom)
        dl._write_dashboard_cache(str(tmp_ws), {"foo": "bar"})
        err = capsys.readouterr().err
        assert "cache write failed" in err


# =============================================================================
# _run_once
# =============================================================================
class TestRunOnce:
    def test_returns_summary_and_writes_cache(self, tmp_ws):
        log = tmp_ws / "mas-dispatch.ndjson"
        _write_entry(log, id="e1", status="done", duration_ms=100)
        s = dl._run_once(str(tmp_ws))
        assert s["total_dispatches"] == 1
        assert s["done"] == 1
        cache = tmp_ws / ".mase" / "dashboards" / "data.json"
        assert cache.exists()


# =============================================================================
# _run_daemon
# =============================================================================
class TestRunDaemon:
    def test_pid_file_write_failure_returns_1(self, tmp_ws, monkeypatch, capsys):
        def boom(*a, **kw):
            raise OSError("forced")
        monkeypatch.setattr(os, "makedirs", boom)
        rc = dl._run_daemon(str(tmp_ws), "/bad/pid", str(tmp_ws / "log"))
        assert rc == 1
        assert "cannot write PID file" in capsys.readouterr().err

    def test_log_file_open_failure_returns_1(self, tmp_ws, monkeypatch, capsys):
        # PID write succeeds; log open fails
        monkeypatch.setattr(os, "makedirs", lambda *a, **kw: None)
        rc = dl._run_daemon(str(tmp_ws), str(tmp_ws / "ok.pid"),
                             "/nonexistent-dir/log")
        assert rc == 1
        assert "cannot open log file" in capsys.readouterr().err

    def test_daemon_short_run_then_sigterm(self, tmp_ws, monkeypatch):
        """Run daemon in subprocess (real process), send SIGTERM, verify
        clean exit and PID file cleanup. Run-time 1s refresh."""
        import signal as sig
        import subprocess
        script = Path(__file__).resolve().parents[1] / "tools" / "dev_dispatch_live.py"
        pid_file = tmp_ws / "daemon.pid"
        log_file = tmp_ws / "daemon.log"
        # env MONKEYPATCH: set REFRESH_INTERVAL via PYTHONSTARTUP? No.
        # Just patch the module from a small wrapper script.
        wrapper = tmp_ws / "run.py"
        wrapper.write_text(
            f"import sys, os; sys.path.insert(0, '{script.parent}'); "
            "import dev_dispatch_live; dev_dispatch_live.REFRESH_INTERVAL = 1; "
            f"sys.argv = ['x', '--daemon', '--workspace', '{tmp_ws}', "
            f"'--pid-file', '{pid_file}', '--log-file', '{log_file}']; "
            "sys.exit(dev_dispatch_live.main())\n"
        )
        env = os.environ.copy()
        env["PYTHONPATH"] = str(script.parent) + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.Popen([sys.executable, str(wrapper)],
                                env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        # Wait for PID file
        deadline = time.time() + 3
        while time.time() < deadline and not pid_file.exists():
            time.sleep(0.05)
        assert pid_file.exists(), "daemon didn't write PID file in 3s"
        pid = int(pid_file.read_text().strip())
        # Send SIGTERM
        os.kill(pid, sig.SIGTERM)
        # Wait for clean exit
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            assert False, "daemon didn't stop within 5s after SIGTERM"
        assert proc.returncode == 0
        # PID file cleaned up by daemon
        assert not pid_file.exists()


# =============================================================================
# main (argparse)
# =============================================================================
class TestMain:
    def test_status_mode(self, tmp_ws, monkeypatch, capsys):
        log = tmp_ws / "mas-dispatch.ndjson"
        _write_entry(log, id="e1", status="done", duration_ms=100)
        monkeypatch.setattr(sys, "argv", ["x", "--status", "--workspace", str(tmp_ws)])
        rc = dl.main()
        assert rc == 0
        out = capsys.readouterr().out
        # Should be valid JSON
        data = json.loads(out)
        assert data["total_dispatches"] == 1

    def test_once_mode(self, tmp_ws, monkeypatch, capsys):
        log = tmp_ws / "mas-dispatch.ndjson"
        _write_entry(log, id="e1")
        monkeypatch.setattr(sys, "argv", ["x", "--once", "--workspace", str(tmp_ws)])
        rc = dl.main()
        assert rc == 0
        out = capsys.readouterr().out
        json.loads(out)  # valid JSON

    def test_no_mode_prints_help_and_returns_1(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["x"])
        rc = dl.main()
        assert rc == 1
        out = capsys.readouterr().out
        assert "usage" in out.lower() or "--status" in out

    def test_daemon_mode_short_run(self, tmp_ws, monkeypatch):
        """--daemon via main() in subprocess, SIGTERM, verify clean exit."""
        import signal as sig
        import subprocess
        script = Path(__file__).resolve().parents[1] / "tools" / "dev_dispatch_live.py"
        pid_file = tmp_ws / "d.pid"
        log_file = tmp_ws / "d.log"
        wrapper = tmp_ws / "run.py"
        wrapper.write_text(
            f"import sys; sys.path.insert(0, '{script.parent}'); "
            "import dev_dispatch_live; dev_dispatch_live.REFRESH_INTERVAL = 1; "
            f"sys.argv = ['x', '--daemon', '--workspace', '{tmp_ws}', "
            f"'--pid-file', '{pid_file}', '--log-file', '{log_file}']; "
            "sys.exit(dev_dispatch_live.main())\n"
        )
        env = os.environ.copy()
        env["PYTHONPATH"] = str(script.parent) + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.Popen([sys.executable, str(wrapper)],
                                env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        deadline = time.time() + 3
        while time.time() < deadline and not pid_file.exists():
            time.sleep(0.05)
        assert pid_file.exists()
        pid = int(pid_file.read_text().strip())
        os.kill(pid, sig.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            assert False, "daemon didn't stop within 5s"
        assert proc.returncode == 0


# =============================================================================
# Subprocess smoke (catches __main__-block execution)
# =============================================================================
class TestCliSubprocess:
    def test_status_subprocess(self, tmp_path):
        script = Path(__file__).resolve().parents[1] / "tools" / "dev_dispatch_live.py"
        r = subprocess.run(
            [sys.executable, str(script), "--status", "--workspace", str(tmp_path)],
            capture_output=True, text=True,
        )
        assert r.returncode == 0
        # Empty log → total_dispatches: 0
        data = json.loads(r.stdout)
        assert data["total_dispatches"] == 0

    def test_help_subprocess(self):
        script = Path(__file__).resolve().parents[1] / "tools" / "dev_dispatch_live.py"
        r = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True, text=True,
        )
        assert r.returncode == 1
        assert "--status" in r.stdout
        assert "--daemon" in r.stdout
