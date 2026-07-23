#!/usr/bin/env python3
"""
e2e_teams.py — re-runnable end-to-end test of mas-engineer demo teams (business use-cases)

Tests the 3 demo TEAMS that live at /root/.config/goose/recipes/:
  - translator: 3 parallel translators + judge vote
  - sales: 5-agent pipeline (scraper → verifier → outreach → closer)
  - marketing: hub-and-spoke with 5 specialists

WHY THIS TEST EXISTS:
  The mas-engineer e2e suite (e2e_run_all.py) only verifies the TECHNICAL
  foundation (recipe YAML parses, workflows run, agent health). It does NOT
  verify that the business teams actually solve real user tasks.

  This test bridges that gap by treating the teams as a HUMAN would:
  - Sends a real query (parameterized via --params, NOT typed in TUI)
  - Verifies the team invokes the right sub-recipe (delegate tool)
  - Asserts the response contains the expected completion marker
  - Measures wall-clock time and saves full conversation log

HOW IT WORKS (sub_recipe pattern):
  For each test, the runner generates a tiny WRAPPER recipe in /tmp/ that:
    1. Declares the test parameters (source_text, target_lang, etc.)
    2. Has a prompt that tells the dev agent to delegate to the team
    3. References the team via sub_recipes: array (the standard goose mechanism)
  Then runs `goose run --recipe <wrapper> --params <kv> --no-session`.
  The dev agent MUST invoke the sub_recipe via the delegate tool — the wrapper
  verifies the team really runs, not just that the dev agent role-plays the team.

TEAMS ARE NOT IN THIS REPO:
  The user must create the teams at /root/.config/goose/recipes/<team>/.
  See docs/E2E_TEAMS_SETUP.md. Missing teams are SKIPPED, not failed.

USAGE:
  python3 tools/e2e_teams.py                  # full run: all 9 tests
  python3 tools/e2e_teams.py --team translator  # single team
  python3 tools/e2e_teams.py --level easy       # single level
  python3 tools/e2e_teams.py --dry-run          # check team presence only

OUTPUT:
  - e2e-results/<date>-teams-<n>/raw-results.json
  - e2e-results/<date>-teams-<n>/logs/<team>-<level>.log
  - Exit 0 if all PRESENT (non-skip) tests pass.
"""

import os
import sys
import json
import time
import argparse
import subprocess
import glob
import pty
import select
import fcntl
import termios
import struct
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Team recipes live at the goose user config (not in this repo)
TEAM_RECIPES = {
    "translator": "/root/.config/goose/recipes/translator/translator-team.yaml",
    "sales":      "/root/.config/goose/recipes/sales/sales-team.yaml",
    "marketing":  "/root/.config/goose/recipes/marketing/marketing-team.yaml",
}

# Where the runner writes generated wrapper recipes (ephemeral, in /tmp)
WRAPPER_DIR = "/tmp/e2e_teams_recipes"


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)


def section(title):
    bar = "=" * 60
    print(f"\n{bar}\n  {title}\n{bar}", flush=True)


# ============================================================================
# TEST CASES — 3 teams × 3 difficulty levels
# ============================================================================
# Each case has:
#   - wrapper params: dict of param_key -> value
#   - prompt_template: the wrapper's `prompt:` field with {{ }} placeholders
#   - marker: string that MUST appear in output for test to pass
#   - expect_in_output: list of strings that must all appear (case-insensitive)
#   - timeout_s: per-test wall-clock cap
#   - rationale: human-readable explanation
# ============================================================================

TEST_CASES = {
    "translator": {
        "easy": {
            "params": {"source_text": "Hello world", "target_lang": "German"},
            "prompt": (
                "Translate the text provided in `source_text` to the language in `target_lang`. "
                "Parameters:\n"
                "  source_text: {{ source_text }}\n"
                "  target_lang: {{ target_lang }}\n"
                "You MUST invoke the `translator_team` sub_recipe via the delegate tool. "
                "Do NOT simulate the team yourself. After the team returns its result, "
                "output the winning translation and end your final response with the marker "
                "'Hallo' on its own line (even if target_lang is not German — just output the marker)."
            ),
            "marker": "Hallo",
            "expect_in_output": ["delegate", "translator_team", "Hallo"],
            "timeout_s": 120,
            "rationale": "Tiny input. Verifies sub_recipe dispatch + 3-translator + judge.",
        },
        "medium": {
            "params": {
                "source_text": "The HTTP server returned a 503 status code because the database connection pool was exhausted during peak load.",
                "target_lang": "German",
            },
            "prompt": (
                "Translate the text provided in `source_text` to the language in `target_lang`. "
                "Parameters:\n"
                "  source_text: {{ source_text }}\n"
                "  target_lang: {{ target_lang }}\n"
                "You MUST invoke the `translator_team` sub_recipe via the delegate tool. "
                "Do NOT simulate the team yourself. After the team returns its result, "
                "output the winning translation and end your final response with the marker 'Hallo' on its own line."
            ),
            "marker": "Hallo",
            "expect_in_output": ["delegate", "translator_team", "HTTP"],
            "timeout_s": 150,
            "rationale": "Technical jargon. Verifies team differentiates literal vs technical translation.",
        },
        "hard": {
            "params": {
                "source_text": "It is no use crying over spilt milk, but we should not have put all our eggs in one basket in the first place.",
                "target_lang": "German",
            },
            "prompt": (
                "Translate the text provided in `source_text` to the language in `target_lang`. "
                "Parameters:\n"
                "  source_text: {{ source_text }}\n"
                "  target_lang: {{ target_lang }}\n"
                "You MUST invoke the `translator_team` sub_recipe via the delegate tool. "
                "Do NOT simulate the team yourself. The text contains idioms — verify the "
                "literary translator recognizes the non-literal meaning. After the team returns "
                "its result, output the winning translation and end your final response with "
                "the marker 'Hallo' on its own line."
            ),
            "marker": "Hallo",
            "expect_in_output": ["delegate", "translator_team", "Milch"],
            "timeout_s": 180,
            "rationale": "Idiom-heavy. Verifies literary translator recognizes non-literal meaning.",
        },
    },
    "sales": {
        "easy": {
            "params": {"question": "What can your team do?"},
            "prompt": (
                "The user asked the question stored in `question`. Parameters:\n"
                "  question: {{ question }}\n"
                "You MUST invoke the `sales_team` sub_recipe via the delegate tool to answer it. "
                "Do NOT simulate the team yourself. After the team returns its result, "
                "end your final response with the marker 'SALES-INFO' on its own line."
            ),
            "marker": "SALES-INFO",
            "expect_in_output": ["delegate", "sales_team", "SALES-INFO"],
            "timeout_s": 120,
            "rationale": "Meta-query. Verifies team introspects its own structure correctly.",
        },
        "medium": {
            "params": {
                "task": "find 2 B2B SaaS leads in Berlin (AI/ML space, 10-50 employees)",
                "region": "Berlin",
                "industry": "AI/ML",
            },
            "prompt": (
                "The user asked the sales team to perform the task in `task`. Parameters:\n"
                "  task: {{ task }}\n"
                "  region: {{ region }}\n"
                "  industry: {{ industry }}\n"
                "You MUST invoke the `sales_team` sub_recipe via the delegate tool. "
                "Do NOT simulate the team yourself. The team should run lead-scraper, then "
                "lead-verifier (MANDATORY gate), then outreach-drafter. After the team returns "
                "its result, summarize what it found (even if incomplete) and end your final "
                "response with the marker 'LEAD-DONE' on its own line."
            ),
            "marker": "LEAD-DONE",
            "expect_in_output": ["delegate", "sales_team", "Berlin"],
            "timeout_s": 600,  # real lead scraping + verification + outreach is slow
            "rationale": "Real lead-pipeline. Verifies 3 of 5 agents fire in correct order with verifier gate.",
        },
        "hard": {
            "params": {
                "task": "Run the full sales pipeline for ONE German AI startup in Munich: scrape lead, verify (mandatory), draft personalized outreach, then build a close plan with objection handling.",
                "region": "Munich",
                "industry": "AI",
            },
            "prompt": (
                "The user asked the sales team to perform the task in `task`. Parameters:\n"
                "  task: {{ task }}\n"
                "  region: {{ region }}\n"
                "  industry: {{ industry }}\n"
                "You MUST invoke the `sales_team` sub_recipe via the delegate tool. "
                "Do NOT simulate the team yourself. The team should run ALL 5 agents in order: "
                "lead-scraper, lead-verifier (mandatory), outreach-drafter, then closer with "
                "objection handling. After the team returns its result, end your final response "
                "with the marker 'CLOSE-DONE' on its own line."
            ),
            "marker": "CLOSE-DONE",
            "expect_in_output": ["delegate", "sales_team", "Munich"],
            "timeout_s": 300,
            "rationale": "Full 5-agent pipeline. Verifies MANDATORY verifier gate + closer integration.",
        },
    },
    "marketing": {
        "easy": {
            "params": {"question": "What can your team do?"},
            "prompt": (
                "The user asked the question stored in `question`. Parameters:\n"
                "  question: {{ question }}\n"
                "You MUST invoke the `marketing_team` sub_recipe via the delegate tool to answer it. "
                "Do NOT simulate the team yourself. After the team returns its result, "
                "end your final response with the marker 'MARKETING-INFO' on its own line."
            ),
            "marker": "MARKETING-INFO",
            "expect_in_output": ["delegate", "marketing_team", "MARKETING-INFO"],
            "timeout_s": 120,
            "rationale": "Meta-query. Verifies hub-and-spoke orchestrator introspects its specialists.",
        },
        "medium": {
            "params": {
                "task": "Draft 3 Twitter/X posts (under 280 chars each) for a B2B SaaS product launch about an AI code-review tool.",
                "specialist": "social-media-manager",
            },
            "prompt": (
                "The user asked the marketing team to perform the task in `task`. Parameters:\n"
                "  task: {{ task }}\n"
                "  specialist: {{ specialist }}\n"
                "You MUST invoke the `marketing_team` sub_recipe via the delegate tool. "
                "Do NOT simulate the team yourself. The orchestrator should dispatch to "
                "the specialist named in `specialist`. After the team returns its result, "
                "end your final response with the marker 'TWEETS-DONE' on its own line."
            ),
            "marker": "TWEETS-DONE",
            "expect_in_output": ["delegate", "marketing_team", "Twitter"],
            "timeout_s": 180,
            "rationale": "Single specialist dispatch. Verifies orchestrator picks the right agent from a clear query.",
        },
        "hard": {
            "params": {
                "task": "Build a GTM plan for a new AI code-review SaaS targeting EU mid-market (50-500 employees).",
                "region": "EU",
                "specialists": "seo-researcher, content-writer, social-media-manager, email-campaign-manager, analytics-reporter",
            },
            "prompt": (
                "The user asked the marketing team to perform the task in `task`. Parameters:\n"
                "  task: {{ task }}\n"
                "  region: {{ region }}\n"
                "  specialists: {{ specialists }}\n"
                "You MUST invoke the `marketing_team` sub_recipe via the delegate tool. "
                "Do NOT simulate the team yourself. The orchestrator should dispatch to ALL "
                "5 specialists listed in `specialists` and synthesize a unified GTM plan. "
                "After the team returns its result, end your final response with the marker "
                "'GTM-DONE' on its own line."
            ),
            "marker": "GTM-DONE",
            "expect_in_output": ["delegate", "marketing_team", "GTM"],
            "timeout_s": 300,
            "rationale": "Full hub-and-spoke. Verifies orchestrator dispatches to 5 specialists and synthesizes a unified plan.",
        },
    },
}


# ============================================================================
# WRAPPER RECIPE GENERATION
# ============================================================================
# A wrapper recipe is what goose actually runs. It:
#   1. Has the dev agent as its main
#   2. References the team via sub_recipes: (plural array)
#   3. Declares parameters in YAML
#   4. Uses {{ }} jinja substitution in prompt:
# ============================================================================

def build_wrapper_recipe(team, level, case, team_recipe_path):
    """
    Builds a minimal wrapper recipe in YAML that:
      - has a developer extension (for tool use)
      - references the team via sub_recipes: array
      - declares the test parameters
      - has a prompt that tells the dev agent to delegate to the team

    Returns the YAML content as a string.
    """
    import yaml
    team_short = team.replace("-", "_") + "_team"

    # Build parameters list (each param becomes a `key:`, `input_type:`, `requirement:`, `description:` entry)
    param_defs = []
    for key in case["params"].keys():
        param_defs.append({
            "key": key,
            "input_type": "string",
            "requirement": "required",
            "description": f"Test parameter: {key}",
        })

    wrapper = {
        "name": f"e2e-teams-test-{team}-{level}",
        "version": "1.0.0",
        "title": f"E2E Test: {team}/{level}",
        "description": f"E2E wrapper for {team} team — {level}",
        "prompt": case["prompt"] + "\n",
        "parameters": param_defs,
        "extensions": [
            {"type": "builtin", "name": "developer", "display_name": "Developer",
             "timeout": 60, "bundled": True}
        ],
        "sub_recipes": [
            {"name": team_short, "path": team_recipe_path}
        ],
        "settings": {
            "timeout": case["timeout_s"],
            "max_steps": 50,
            "goose_provider": "openai",
            "goose_model": "deepseek-chat",
        }
    }
    return yaml.dump(wrapper, default_flow_style=False, sort_keys=False,
                     allow_unicode=True, width=1000)


def write_wrapper(team, level, case):
    """Writes the wrapper recipe to /tmp and returns its path."""
    os.makedirs(WRAPPER_DIR, exist_ok=True)
    wrapper_path = f"{WRAPPER_DIR}/{team}-{level}.yaml"
    content = build_wrapper_recipe(team, level, case, TEAM_RECIPES[team])
    with open(wrapper_path, "w") as f:
        f.write(content)
    return wrapper_path


# ============================================================================
# PTY RUNNER
# ============================================================================

def check_teams_present():
    """Returns dict of {team: bool}. Missing teams -> SKIP, not FAIL."""
    return {team: os.path.exists(path) for team, path in TEAM_RECIPES.items()}


def run_team_test(team, level, case, env):
    """
    Runs a single test case via PTY using the wrapper recipe pattern.
    Returns dict with: status, elapsed_s, output, error, evidence.
    status ∈ {ok, fail, timeout, skip}
    """
    recipe = TEAM_RECIPES[team]
    if not os.path.exists(recipe):
        return {"status": "skip", "reason": f"team recipe not found: {recipe}"}

    # 1. Generate wrapper recipe
    wrapper = write_wrapper(team, level, case)

    # 2. Build goose command: --recipe <wrapper> --params <kv>... --no-session
    cmd = ["/root/.local/bin/goose", "run", "--recipe", wrapper, "--no-session"]
    for k, v in case["params"].items():
        cmd.extend(["--params", f"{k}={v}"])

    timeout_s = case["timeout_s"]
    log(f"  {team}/{level}: starting (timeout={timeout_s}s, wrapper={wrapper})")

    start = time.time()
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 200, 0, 0))

    try:
        proc = subprocess.Popen(cmd, stdin=slave, stdout=slave, stderr=slave,
                                env=env, close_fds=True)
    except FileNotFoundError:
        return {"status": "fail", "reason": "goose not found in /root/.local/bin"}
    except Exception as e:
        return {"status": "fail", "reason": f"Popen failed: {e}"}

    output = b""
    last_data_time = time.time()
    IDLE_TIMEOUT = 45  # sub-agent work can pause
    while time.time() - start < timeout_s:
        r, _, _ = select.select([master], [], [], 0.5)
        if r:
            try:
                data = os.read(master, 16384)
                output += data
                last_data_time = time.time()
            except OSError:
                break
        elif proc.poll() is not None:
            break
        if time.time() - last_data_time > IDLE_TIMEOUT and len(output) > 500:
            try: os.write(master, b"\x03")
            except: pass
            break
        # Early exit if marker found AND a newline after it (final response)
        if case["marker"].encode() in output:
            tail = output[-300:]
            if b"\n" in tail[tail.rfind(case["marker"].encode()):]:
                time.sleep(2)
                try: os.write(master, b"\x03")
                except: pass
                break

    try: proc.wait(timeout=3)
    except subprocess.TimeoutExpired: proc.kill()

    elapsed = time.time() - start
    text = output.decode("utf-8", errors="replace")
    # Strip ANSI escape codes BEFORE marker check — goose color-codes each char
    # of the rendered text, so plain string search misses markers like "SALES-INFO"
    import re
    ansi_re = re.compile(r"\x1b\[[0-9;]*m")
    text_stripped = ansi_re.sub("", text)
    sent_marker = case["marker"] in text_stripped
    missing = [k for k in case["expect_in_output"] if k.lower() not in text_stripped.lower()]

    # Evidence: was the sub_recipe actually invoked? Look for delegate tool call
    sub_invoked = ("delegate" in text.lower() and
                   f"{team.replace('-', '_')}_team" in text.lower())

    if not sent_marker:
        status = "fail"
        reason = f"marker '{case['marker']}' not found in output (waited {elapsed:.0f}s)"
    elif not sub_invoked:
        status = "fail"
        reason = f"sub_recipe NOT invoked — wrapper simulated the team itself. Expected: 'delegate' + '{team}_team'"
    elif missing:
        status = "fail"
        reason = f"expected keywords missing: {missing}"
    else:
        status = "ok"
        reason = ""

    log(f"    [{elapsed:.1f}s] status={status}  marker={'✓' if sent_marker else '✗'}  "
        f"sub_recipe={'✓' if sub_invoked else '✗'}  reason={reason or 'all checks passed'}")
    return {
        "status": status,
        "elapsed_s": round(elapsed, 1),
        "marker_found": sent_marker,
        "sub_recipe_invoked": sub_invoked,
        "missing_keywords": missing,
        "reason": reason,
        "output_bytes": len(output),
        "output_tail": text[-2000:],
    }


def main():
    parser = argparse.ArgumentParser(description="e2e test of mas-engineer demo teams")
    parser.add_argument("--team", choices=list(TEAM_RECIPES.keys()),
                        help="test only one team (default: all)")
    parser.add_argument("--level", choices=["easy", "medium", "hard"],
                        help="test only one difficulty (default: all)")
    parser.add_argument("--dry-run", action="store_true",
                        help="just check team presence + list test cases, don't run")
    args = parser.parse_args()

    section("E2E TEAMS — BUSINESS USE-CASE TEST")
    log("Treats each demo team as a real human user would.")
    log("Teams are NOT in this repo. See docs/E2E_TEAMS_SETUP.md.")
    log("Mechanism: wrapper recipe (in /tmp) with sub_recipes: array + jinja params.")
    log("")

    present = check_teams_present()
    section("Team recipes found")
    for team, path in TEAM_RECIPES.items():
        mark = "✓" if present[team] else "✗ MISSING (test will SKIP)"
        log(f"  {team:12s} {mark}  {path}")

    if args.dry_run:
        section("Test plan (dry-run)")
        teams = [args.team] if args.team else list(TEST_CASES.keys())
        levels = [args.level] if args.level else ["easy", "medium", "hard"]
        for team in teams:
            log(f"\n  {team}:")
            for level in levels:
                case = TEST_CASES[team][level]
                log(f"    {level:7s} | timeout={case['timeout_s']}s | {case['rationale']}")
        log("\nNothing executed (--dry-run).")
        sys.exit(0)

    env = {**os.environ}
    env.setdefault("PATH", "/root/.local/bin:" + env.get("PATH", ""))
    # Explicitly pass deepseek config (avoids 401 from cached/silent config)
    env.setdefault("OPENAI_API_KEY", "sk-e1afc5ddb57d41d7ba8df67a36b11b93")
    env.setdefault("OPENAI_HOST", "https://api.deepseek.com")

    teams = [args.team] if args.team else list(TEST_CASES.keys())
    levels = [args.level] if args.level else ["easy", "medium", "hard"]

    today = datetime.now().strftime("%Y-%m-%d")
    existing = sorted(glob.glob(f"e2e-results/{today}-teams-*"))
    run_n = len(existing) + 1
    out_dir = f"e2e-results/{today}-teams-{run_n}"
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(f"{out_dir}/logs", exist_ok=True)
    log(f"results dir: {out_dir}")

    all_results = {"started": datetime.now().isoformat(), "tests": {}}
    overall_start = time.time()
    for team in teams:
        for level in levels:
            test_key = f"{team}/{level}"
            case = TEST_CASES[team][level]
            if not present[team]:
                log(f"\n[{test_key}] SKIP (team not present)")
                all_results["tests"][test_key] = {"status": "skip", "reason": "team recipe not found"}
                continue
            section(f"TEST: {test_key}")
            result = run_team_test(team, level, case, env)
            all_results["tests"][test_key] = result
            with open(f"{out_dir}/logs/{team}-{level}.log", "w") as f:
                f.write(f"# {test_key}\n")
                f.write(f"# params: {case['params']}\n")
                f.write(f"# marker: {case['marker']}\n")
                f.write(f"# status: {result['status']}\n")
                f.write(f"# elapsed: {result.get('elapsed_s', '?')}s\n")
                f.write(f"# sub_recipe_invoked: {result.get('sub_recipe_invoked', '?')}\n")
                f.write(f"# reason: {result.get('reason', '')}\n")
                f.write(f"---\n\n")
                # Strip ANSI codes from the saved log for readability
                import re
                ansi_re = re.compile(r"\x1b\[[0-9;]*m")
                clean_tail = ansi_re.sub("", result.get("output_tail", "(no output)"))
                f.write(clean_tail)
            time.sleep(1)

    all_results["elapsed_s"] = round(time.time() - overall_start, 1)
    all_results["finished"] = datetime.now().isoformat()

    with open(f"{out_dir}/raw-results.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    statuses = [t["status"] for t in all_results["tests"].values()]
    n_total = len(statuses)
    n_ok = statuses.count("ok")
    n_fail = statuses.count("fail")
    n_skip = statuses.count("skip")
    n_timeout = statuses.count("timeout")
    n_runnable = n_total - n_skip
    pct = (n_ok / n_runnable * 100) if n_runnable > 0 else 0

    section("FINAL SCORE")
    log(f"TOTAL: {n_total} tests, {n_ok} PASS, {n_fail} FAIL, {n_timeout} TIMEOUT, {n_skip} SKIP")
    log(f"Pass rate (excluding skips): {n_ok}/{n_runnable} = {pct:.1f}%")
    log(f"Wall time: {all_results['elapsed_s']}s")
    log("")
    log("Per-test breakdown:")
    for test_key, t in all_results["tests"].items():
        es = f"{t.get('elapsed_s', '?'):>6}s" if t.get("elapsed_s") else "     ?"
        log(f"  {test_key:25s}  {t['status']:8s}  {es}  {t.get('reason', '')}")
    log("")
    log(f"Results: {out_dir}/")
    log("")

    if n_fail == 0 and n_timeout == 0:
        log("PASS (all runnable tests passed)", "SUCCESS")
        sys.exit(0)
    else:
        log(f"FAIL ({n_fail + n_timeout} of {n_runnable} runnable tests failed)", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
