#!/usr/bin/env python3
"""dev_dispatch_live.py — Live Dispatch Daemon v1.0.0
====================================================
Monitors the dispatch log in real-time and emits status updates.
Watches /tmp/mas-dispatch.ndjson for new entries and refreshes
the dashboard cache every N seconds.

call:
  python3 dev_dispatch_live.py --daemon
      → run as background daemon (writes .mas/live-daemon.pid)
  python3 dev_dispatch_live.py --status
      → print current dispatch summary
  python3 dev_dispatch_live.py --once
      → run one refresh cycle and exit
"""
import argparse
import json
import os
import signal
import sys
import tempfile
import time
from pathlib import Path

DISPATCH_LOG = os.path.join(tempfile.gettempdir(), "mas-dispatch.ndjson")
DASHBOARD_DATA_DIR = ".mas/dashboards"
DASHBOARD_DATA_FILE = "data.json"
REFRESH_INTERVAL = 5  # seconds


def _read_dispatch_log() -> list:
    """Read all dispatch entries from log."""
    if not os.path.exists(DISPATCH_LOG):
        return []
    entries = []
    try:
        with open(DISPATCH_LOG) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except OSError:
        pass
    return entries


def _summarize(entries: list) -> dict:
    """Build a status summary from dispatch entries."""
    total = len(entries)
    running = sum(1 for e in entries if e.get("status") == "running")
    done = sum(1 for e in entries if e.get("status") == "done")
    errors = sum(1 for e in entries if e.get("status") == "error" or e.get("errors"))
    durations = [e["duration_ms"] for e in entries if e.get("duration_ms") is not None]
    avg_duration_ms = sum(durations) / len(durations) if durations else 0
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_dispatches": total,
        "running": running,
        "done": done,
        "errors": errors,
        "avg_duration_ms": round(avg_duration_ms, 1),
        "last_entry_ts": entries[-1].get("ts") if entries else None,
    }


def _write_dashboard_cache(workspace: str, summary: dict) -> None:
    """Write the live summary to the dashboard cache."""
    cache_dir = os.path.join(workspace, DASHBOARD_DATA_DIR)
    cache_file = os.path.join(cache_dir, DASHBOARD_DATA_FILE)
    try:
        os.makedirs(cache_dir, exist_ok=True)
        # Read existing data if present
        existing = {}
        if os.path.exists(cache_file):
            try:
                with open(cache_file) as f:
                    existing = json.load(f)
            except (OSError, json.JSONDecodeError):
                existing = {}
        # Merge with new live data
        existing["live"] = summary
        with open(cache_file, "w") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
    except OSError as e:
        print(f"[daemon] cache write failed: {e}", file=sys.stderr)


def _run_once(workspace: str) -> dict:
    """Run one refresh cycle."""
    entries = _read_dispatch_log()
    summary = _summarize(entries)
    _write_dashboard_cache(workspace, summary)
    return summary


def _run_daemon(workspace: str, pid_file: str, log_file: str) -> int:
    """Run as a background daemon."""
    # Write PID file
    pid = os.getpid()
    try:
        os.makedirs(os.path.dirname(pid_file), exist_ok=True)
        with open(pid_file, "w") as f:
            f.write(str(pid))
    except OSError as e:
        print(f"[daemon] cannot write PID file: {e}", file=sys.stderr)
        return 1

    # Setup signal handler for graceful shutdown
    stop_requested = {"flag": False}

    def _handle_stop(signum, frame):
        stop_requested["flag"] = True

    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)

    # Open log file
    try:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        log_fh = open(log_file, "a")
    except OSError as e:
        print(f"[daemon] cannot open log file: {e}", file=sys.stderr)
        return 1

    print(f"[daemon] started (PID {pid}), refreshing every {REFRESH_INTERVAL}s", file=log_fh)
    log_fh.flush()

    try:
        while not stop_requested["flag"]:
            try:
                summary = _run_once(workspace)
                ts = time.strftime("%H:%M:%S", time.gmtime())
                print(
                    f"[{ts}] live: {summary['total_dispatches']} total, "
                    f"{summary['running']} running, {summary['done']} done, "
                    f"{summary['errors']} errors",
                    file=log_fh
                )
                log_fh.flush()
            except Exception as e:
                print(f"[daemon] cycle error: {e}", file=log_fh)
                log_fh.flush()
            # Sleep in small chunks so signals are responsive
            for _ in range(REFRESH_INTERVAL):
                if stop_requested["flag"]:
                    break
                time.sleep(1)
    finally:
        log_fh.close()
        try:
            os.remove(pid_file)
        except OSError:
            pass
        print(f"[daemon] stopped (PID {pid})", file=sys.stderr)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Live dispatch daemon")
    parser.add_argument("--daemon", action="store_true", help="Run as background daemon")
    parser.add_argument("--status", action="store_true", help="Print current summary and exit")
    parser.add_argument("--once", action="store_true", help="Run one refresh cycle and exit")
    parser.add_argument("--workspace", default=os.getcwd(), help="Workspace root")
    parser.add_argument("--pid-file", default=None, help="PID file path (daemon mode)")
    parser.add_argument("--log-file", default=None, help="Log file path (daemon mode)")
    args = parser.parse_args()

    if args.status:
        summary = _run_once(args.workspace)
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0

    if args.once:
        summary = _run_once(args.workspace)
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0

    if args.daemon:
        pid_file = args.pid_file or os.path.join(args.workspace, ".mas", "live-daemon.pid")
        log_file = args.log_file or os.path.join(args.workspace, ".mas", "live-daemon.log")
        return _run_daemon(args.workspace, pid_file, log_file)

    # No mode: print help
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
