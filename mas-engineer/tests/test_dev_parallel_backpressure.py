"""
test_dev_parallel_backpressure.py — R110-158

Tests the new BoundedSemaphore backpressure feature in
ParalllPool.run(tasks, backpressure=N).

Verifies:
  1. Default (backpressure=None) behavior is unchanged
  2. backpressure=N limits concurrently-executing tasks to N
  3. All tasks eventually complete (no deadlock)
  4. backpressure=1 acts as a strict serial executor
  5. Higher backpressure values (N > max_workers) don't add throttling
  6. Exception in one task does not block other tasks
  7. Empty task list returns empty dict (backward compat)
"""
import sys
import threading
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT / "tools"))

import dev_parallel as dp  # noqa: E402


# ─── Tests ───────────────────────────────────────────────────────

def test_default_no_backpressure_unchanged():
    """(1) Default behavior: all tasks run as soon as worker available.
    No backpressure semaphore. (No new BoundedSemaphore created.)"""
    pool = dp.ParalllPool(max_workers=4)
    results = pool.run([
        {"id": "a", "fn": lambda: 1},
        {"id": "b", "fn": lambda: 2},
        {"id": "c", "fn": lambda: 3},
    ])
    assert results == {"a": 1, "b": 2, "c": 3}


def test_backpressure_limits_concurrency():
    """(2) backpressure=2 ensures at most 2 tasks run concurrently,
    even when 4 workers are available."""
    concurrent = 0
    max_concurrent = 0
    lock = threading.Lock()

    def _track_and_sleep():
        nonlocal concurrent, max_concurrent
        with lock:
            concurrent += 1
            max_concurrent = max(max_concurrent, concurrent)
        time.sleep(0.05)  # hold the slot briefly
        with lock:
            concurrent -= 1
        return 1

    pool = dp.ParalllPool(max_workers=8)
    tasks = [{"id": f"t{i}", "fn": _track_and_sleep}
             for i in range(10)]
    results = pool.run(tasks, backpressure=2)
    assert len(results) == 10
    # At no point did more than 2 run simultaneously
    assert max_concurrent <= 2
    # And we actually hit the limit (2) — confirms semaphore is engaged
    assert max_concurrent == 2


def test_all_tasks_complete_no_deadlock():
    """(3) Even with backpressure=1 and many tasks, all complete."""
    pool = dp.ParalllPool(max_workers=2)
    tasks = [{"id": f"t{i}", "fn": lambda i=i: i * 2}
             for i in range(20)]
    results = pool.run(tasks, backpressure=1)
    assert len(results) == 20
    for i in range(20):
        assert results[f"t{i}"] == i * 2


def test_backpressure_one_is_serial():
    """(4) backpressure=1 acts as a strict serial executor."""
    start_times = []
    end_times = []
    lock = threading.Lock()

    def _record():
        with lock:
            start_times.append(time.monotonic())
        time.sleep(0.01)
        with lock:
            end_times.append(time.monotonic())
        return 1

    pool = dp.ParalllPool(max_workers=8)
    tasks = [{"id": f"t{i}", "fn": _record} for i in range(4)]
    pool.run(tasks, backpressure=1)
    # With serial execution, task N must END before task N+1 STARTS
    assert len(start_times) == 4
    assert len(end_times) == 4
    for i in range(1, 4):
        assert end_times[i - 1] <= start_times[i], (
            f"task {i} started at {start_times[i]:.3f} but task "
            f"{i-1} ended at {end_times[i-1]:.3f} — NOT serial"
        )


def test_backpressure_higher_than_workers_no_extra_throttle():
    """(5) backpressure=100 with max_workers=4 → at most 4 concurrent
    (limited by the thread pool, not the semaphore)."""
    concurrent = 0
    max_concurrent = 0
    lock = threading.Lock()

    def _track():
        nonlocal concurrent, max_concurrent
        with lock:
            concurrent += 1
            max_concurrent = max(max_concurrent, concurrent)
        time.sleep(0.02)
        with lock:
            concurrent -= 1
        return 1

    pool = dp.ParalllPool(max_workers=4)
    tasks = [{"id": f"t{i}", "fn": _track} for i in range(8)]
    pool.run(tasks, backpressure=100)
    # 4 workers, no extra throttling
    assert max_concurrent <= 4
    assert max_concurrent == 4


def test_exception_does_not_deadlock():
    """(6) A task that raises should not block siblings, even with
    backpressure. The semaphore must release on the finally path."""
    pool = dp.ParalllPool(max_workers=2)
    tasks = [
        {"id": "ok1", "fn": lambda: 1},
        {"id": "fail", "fn": lambda: (_ for _ in ()).throw(RuntimeError("boom"))},
        {"id": "ok2", "fn": lambda: 3},
    ]
    results = pool.run(tasks, backpressure=1)
    assert results["ok1"] == 1
    assert results["ok2"] == 3
    assert "error" in results["fail"]
    assert "boom" in results["fail"]["error"]


def test_empty_task_list():
    """(7) Empty list returns empty dict (backward compat)."""
    pool = dp.ParalllPool(max_workers=4)
    assert pool.run([]) == {}
    assert pool.run([], backpressure=1) == {}
