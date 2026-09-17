#!/usr/bin/env python3
"""
15x Demo-Team Build-Optimize-Tasks E2E (3 teams × 5 runs = 15 runs)

Mirrors 2026-07-27 run_15x_demo.py methodology but:
  1. Uses NEW prompts in prompts/demo-team-build-optimize-tasks/
  2. Each cycle = BUILD + OPTIMIZE + ASSIGN-TASKS (3 phases, not 1)
  3. Prompts are intended to be COPY-PASTED BY USER INTO CLI,
     not piped (so we can verify the human-CLI loop works).

This script is the ORCHESTRATOR side: it runs the agent prompts
that mas-engineer would generate, measures pass-rate across
3 teams × 5 cycles, and reports Wilson 95% CI.

Usage:
  python3 tools/run_demo_team_15x_build_optimize_tasks.py --team research
  python3 tools/run_demo_team_15x_build_optimize_tasks.py --team all --runs 5
  python3 tools/run_demo_team_15x_build_optimize_tasks.py --dry-run   # show plan only

Output:
  e2e-results/2026-07-28-demo-team-build-optimize-tasks-15x/
    README.md
    run_15x_demo.py
    evidence/
      run1-research-build.log
      run1-research-optimize.log
      run1-research-tasks.log
      run1-research-prompt.txt
      ...
    SUMMARY.json

Tested prerequisites:
  - DEEPSEEK_API_KEY in env (or mas-engineer/.env loaded)
  - goose CLI installed at ~/.local/bin/goose
  - mas-engineer extension registered in ~/.config/goose/config.yaml
  - /tmp/<team>-team writeable
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

EVIDENCE_ROOT = Path("e2e-results/2026-07-28-demo-team-build-optimize-tasks-15x/evidence")
EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)

PROMPTS_DIR = Path("mas-engineer/prompts/demo-team-build-optimize-tasks")

TEAMS = {
    "research": {
        "prompt_file": PROMPTS_DIR / "research-team.txt",
        "team_dir": "/tmp/research-team",
        "team_name": "research-team",
    },
    "customer": {
        "prompt_file": PROMPTS_DIR / "customer-support.txt",
        "team_dir": "/tmp/customer-support",
        "team_name": "customer-support",
    },
    "code-review": {
        "prompt_file": PROMPTS_DIR / "code-reviewer.txt",
        "team_dir": "/tmp/code-reviewer",
        "team_name": "code-reviewer",
    },
}

PHASES = ["build", "optimize", "tasks"]


def setup_env() -> dict:
    """Load .env, set up goose env vars."""
    env = os.environ.copy()

    # Load mas-engineer/.env if present
    env_path = Path("mas-engineer/.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")

    ds = env.get("DEEPSEEK_API_KEY")
    if not ds:
        raise RuntimeError(
            "DEEPSEEK_API_KEY not set — refusing to run without it "
            "(no hardcoded fallback for security). "
            "Add to mas-engineer/.env or export in shell."
        )

    env["DEEPSEEK_API_KEY"] = ds
    env["OPENAI_API_KEY"] = ds
    env["OPENAI_HOST"] = "https://api.deepseek.com"
    env["OPENAI_MODEL"] = "deepseek-chat"
    env["GOOSE_TELEMETRY_ENABLED"] = "false"
    env["NO_COLOR"] = "1"
    env["TERM"] = "dumb"
    bin_path = os.path.expanduser("~/.local/bin")
    env["PATH"] = f"{bin_path}:{env.get('PATH', '')}"
    return env


def run_phase(phase: str, prompt: str, env: dict, log_path: Path,
              timeout: int = 1500) -> dict:
    """Run one phase = one fresh goose invocation.

    Args:
        phase: build|optimize|tasks (informational only, in logs)
        prompt: full prompt text (could be very long for tasks phase)
        env: env dict from setup_env()
        log_path: where to write full stdout+stderr
        timeout: max seconds (default 25 min)

    Returns:
        dict with keys: ok, duration_s, exit_code, log_path
    """
    started = time.time()
    try:
        # goose run --no-session --text <prompt>
        # We use --text (not --instructions -) because prompts are large
        # and may include newlines/quotes that would break stdin pipe.
        proc = subprocess.run(
            ["goose", "run", "--no-session", "--text", prompt],
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        exit_code = proc.returncode
        out = proc.stdout
        err = proc.stderr
        ok = exit_code == 0
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        err = (e.stderr or b"").decode(errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
        out = out + f"\n[TIMEOUT after {timeout}s]"
        err = err + f"\n[TIMEOUT after {timeout}s]"
        exit_code = -1
        ok = False
    except Exception as e:
        out = ""
        err = f"[SUBPROCESS ERROR: {e}]"
        exit_code = -2
        ok = False

    duration = time.time() - started
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        f"=== phase={phase} started={datetime.now(timezone.utc).isoformat()} ===\n"
        f"=== exit_code={exit_code} duration={duration:.1f}s ===\n\n"
        f"--- STDOUT ---\n{out}\n\n--- STDERR ---\n{err}\n"
    )
    return {
        "ok": ok,
        "duration_s": round(duration, 1),
        "exit_code": exit_code,
        "log_path": str(log_path),
    }


def extract_pass_count(log_text: str) -> tuple[int, int]:
    """Extract (passed, total) from agent log using 2026-07-27 fixed regex set."""
    patterns_passed = [
        r"(\d+)\s+of\s+\d+\s+PASS",
        r"(\d+)\s*/\s*\d+\s+checks?\s+PASS",
        r"(\d+)\s+checks?\s+PASS",
        r"✅\s*PASS[^\n]{0,40}?(\d+)",
        r"(\d+)\s*✅\s*PASS",
        r"PASS[/ ]+(\d+)\s*/\s*\d+",
    ]
    patterns_total = [
        r"(\d+)\s+of\s+\d+\s+PASS",
        r"(\d+)\s*/\s*\d+\s+checks?\s+PASS",
        r"of\s+(\d+)\s+total\s+checks",
        r"Total\s+checks:\s*(\d+)",
    ]
    passed = 0
    total = 0
    for pat in patterns_passed:
        m = re.search(pat, log_text, re.IGNORECASE)
        if m:
            passed = max(passed, int(m.group(1)))
            break
    for pat in patterns_total:
        m = re.search(pat, log_text, re.IGNORECASE)
        if m:
            # find the "of N" partner
            around = log_text[max(0, m.start() - 30):m.end() + 30]
            m2 = re.search(r"(\d+)\s*[/of]+\s*(\d+)", around)
            if m2:
                total = max(total, int(m2.group(2)))
            else:
                total = max(total, int(m.group(1)))
            break
    return passed, total


def run_cycle(team: str, run: int, env: dict, team_dir: str, prompt: str) -> dict:
    """Run one full cycle = build + optimize + tasks.

    Wipes /tmp/<team> first.
    Returns dict with all 3 phase results + cycle-level PASS/FAIL.
    """
    print(f"\n{'='*70}")
    print(f"CYCLE run={run} team={team} started={datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*70}")

    # 1. Wipe team dir
    subprocess.run(["rm", "-rf", team_dir], check=False)
    subprocess.run(["mkdir", "-p", team_dir], check=False)

    cycle_result = {"team": team, "run": run, "phases": {}}

    for phase in PHASES:
        log_path = EVIDENCE_ROOT / f"run{run}-{team}-{phase}.log"
        # Use the same full prompt for all 3 phases — the agent itself
        # walks through BUILD → OPTIMIZE → TASKS as numbered STEPS.
        # (Alternative: split into 3 separate prompts per phase. We
        # chose 1 prompt for simplicity, matching how a user would
        # paste a single command into CLI.)
        print(f"  → phase={phase} log={log_path.name}")
        res = run_phase(phase, prompt, env, log_path, timeout=1500)
        cycle_result["phases"][phase] = res
        if not res["ok"]:
            print(f"  ✗ phase={phase} FAILED (exit={res['exit_code']}, "
                  f"duration={res['duration_s']}s)")
            # Continue to next phase anyway — we want to see if later
            # phases succeed even after an early failure.

    # Pass detection
    build_log = (EVIDENCE_ROOT / f"run{run}-{team}-build.log").read_text()
    p, t = extract_pass_count(build_log)
    cycle_result["build_passed"] = p
    cycle_result["build_total"] = t
    cycle_result["build_ok"] = t > 0 and p == t

    # Optimize: count "delta" mentions
    opt_log = (EVIDENCE_ROOT / f"run{run}-{team}-optimize.log").read_text()
    delta_match = re.search(r"delta\s*=\s*(\d+)", opt_log, re.IGNORECASE)
    cycle_result["optimize_delta"] = int(delta_match.group(1)) if delta_match else 0
    cycle_result["optimize_ok"] = cycle_result["optimize_delta"] > 0

    # Tasks: count "PASS" in tasks log per task
    tasks_log = (EVIDENCE_ROOT / f"run{run}-{team}-tasks.log").read_text()
    pass_count = len(re.findall(r"\bPASS\b", tasks_log))
    fail_count = len(re.findall(r"\bFAIL\b", tasks_log))
    cycle_result["tasks_pass"] = pass_count
    cycle_result["tasks_fail"] = fail_count
    cycle_result["tasks_ok"] = pass_count >= 3 and fail_count == 0

    # Cycle-level PASS
    cycle_result["cycle_ok"] = (
        cycle_result["build_ok"]
        and cycle_result["optimize_ok"]
        and cycle_result["tasks_ok"]
    )
    print(f"  → build={cycle_result['build_passed']}/{cycle_result['build_total']} "
          f"optimize_delta={cycle_result['optimize_delta']} "
          f"tasks={cycle_result['tasks_pass']}P/{cycle_result['tasks_fail']}F "
          f"cycle_ok={cycle_result['cycle_ok']}")
    return cycle_result


def wilson_ci(passed: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson 95% CI. Returns (lower, upper) as percentages."""
    if total == 0:
        return 0.0, 0.0
    p = passed / total
    denom = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denom
    margin = z * ((p * (1 - p) + z**2 / (4 * total)) / total) ** 0.5 / denom
    return round(max(0, center - margin) * 100, 1), round(min(1, center + margin) * 100, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--team", choices=list(TEAMS.keys()) + ["all"], default="all")
    ap.add_argument("--runs", type=int, default=5, help="cycles per team (default 5)")
    ap.add_argument("--dry-run", action="store_true", help="show plan only")
    args = ap.parse_args()

    if args.dry_run:
        print("DRY RUN — would execute:")
        teams = list(TEAMS.keys()) if args.team == "all" else [args.team]
        for t in teams:
            cfg = TEAMS[t]
            if not cfg["prompt_file"].exists():
                print(f"  ✗ {t}: MISSING prompt {cfg['prompt_file']}")
            else:
                lines = len(cfg["prompt_file"].read_text().splitlines())
                print(f"  ✓ {t}: {cfg['prompt_file']} ({lines} lines) "
                      f"× {args.runs} cycles = {args.runs} runs")
        return 0

    env = setup_env()
    teams = list(TEAMS.keys()) if args.team == "all" else [args.team]
    all_cycles = []

    for team in teams:
        cfg = TEAMS[team]
        if not cfg["prompt_file"].exists():
            print(f"SKIP {team}: prompt {cfg['prompt_file']} missing")
            continue
        prompt = cfg["prompt_file"].read_text()
        for run in range(1, args.runs + 1):
            cycle = run_cycle(team, run, env, cfg["team_dir"], prompt)
            all_cycles.append(cycle)

    # Summary
    total = len(all_cycles)
    passed = sum(1 for c in all_cycles if c["cycle_ok"])
    lower, upper = wilson_ci(passed, total)
    print(f"\n{'='*70}")
    print(f"FINAL: {passed}/{total} cycles PASS, Wilson 95% CI [{lower}%, {upper}%]")
    print(f"{'='*70}")

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "methodology": "2026-07-28 demo-team build-optimize-tasks 15x",
        "teams": teams,
        "runs_per_team": args.runs,
        "total_cycles": total,
        "cycles_passed": passed,
        "wilson_95_ci": [lower, upper],
        "cycles": all_cycles,
    }
    (EVIDENCE_ROOT.parent / "SUMMARY.json").write_text(
        json.dumps(summary, indent=2)
    )
    print(f"Wrote SUMMARY.json")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
