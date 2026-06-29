#!/usr/bin/env python3
"""
dev_update_schedule.py — Self-Improve Timing update
===========================================================
Version: 1.0.0
Aufruf: python3 dev_update_schedule.py <workspace> <findings_count> <duration_sec>

Updated .state/schedule.yaml after a Self-Improve-Runde.
"""

import sys, yaml
from pathlib import Path
from datetime import datetime


def update_schedule(workspace: str, findings_count: int, duration_sec: int):
    """Adds a new round to schedule.yaml and calculates metrics."""
    
    bp_path = Path(workspace) / "mas-engineer" / ".state" / "schedule.yaml"
    
    try:
        with open(bp_path) as f:
            bp = yaml.safe_load(f) or {}
    except FileNotFoundError:
        bp = {
            "version": "1.0.0",
            "history": [],
            "metrics": {},
            "recommendation": {"status": "ready"}
        }
    
    # New Runde entryen
    bp.setdefault("history", []).append({
        "round": len(bp["history"]) + 1,
        "time": datetime.now().isoformat(),
        "findings_count": findings_count,
        "duration_sec": duration_sec
    })
    
    # Only letzte 10 Runden keep
    bp["history"] = bp["history"][-10:]
    
    # Metriken new calculate
    h = bp["history"]
    n = len(h)
    
    metrics = bp.setdefault("metrics", {})
    
    if n > 1:
        intervals = []
        for i in range(n - 1):
            t1 = h[i]["time"] if isinstance(h[i]["time"], datetime) else datetime.fromisoformat(str(h[i]["time"]))
            t2 = h[i+1]["time"] if isinstance(h[i+1]["time"], datetime) else datetime.fromisoformat(str(h[i+1]["time"]))
            intervals.append((t2 - t1).total_seconds() / 60)
        metrics["avg_interval_min"] = int(sum(intervals) / len(intervals))
    
    metrics["avg_duration_sec"] = int(sum(e["duration_sec"] for e in h) / n)
    metrics["avg_findings_per_round"] = round(sum(e["findings_count"] for e in h) / n, 1)
    metrics["rounds_without_findings"] = sum(1 for e in h if e["findings_count"] == 0)
    
    # Recommendation
    letzte_3 = h[-3:]
    findings_sum = sum(e["findings_count"] for e in letzte_3)
    
    rec = bp.setdefault("recommendation", {})
    if findings_sum == 0:
        rec.update({"status": "pause_recommended", "reason": "3 Runden ohne Findings — Pause recommended"})
    elif findings_sum < 5:
        rec.update({"status": "pause_recommended", "reason": "Wenige Findings — Pause recommended"})
    else:
        rec.update({"status": "ready", "reason": "Genug Findings — naechste Runde ready"})
    rec["next_round_after"] = "30m"
    
    bp["last_updated"] = datetime.now().isoformat()
    bp["version"] = "1.0.0"
    
    with open(bp_path, "w") as f:
        yaml.dump(bp, f, default_flow_style=False)
    
    n = len(bp["history"])
    status = bp["recommendation"]["status"]
    print(f"✅ Runde {n} in schedule.yaml saved. Status: {status}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: dev_update_schedule.py <workspace> <findings_count> <duration_sec>")
        sys.exit(1)
    
    update_schedule(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
