#!/usr/bin/env bash
# scripts/r11027-reproducible-30agent-live-pty.sh
# Reproducible live-PTY test: 30 agents × 1 real LLM task each.
#
# Each agent recipe (sub_mas-X.yaml) is a "instructions-only" recipe (no prompt:
# field). goose's --no-session mode requires a prompt to be present. So we build
# a wrapper recipe (R110-27 wrapper) per agent that has the task as its prompt
# and includes the original agent recipe as a sub_recipe.
#
# Gotchas applied (see goose-cli-e2e-testing skill):
#   #2  OPENAI_API_KEY from env, not config
#   #3  GOOSE_MODEL=deepseek-v4-flash (not -chat)
#   #3b OPENAI_HOST = https://api.deepseek.com (NO /v1)
#   #16 NO export X=*** after source
#   #17 set -o pipefail
#   #18 OPENAI_API_KEY falls back to DEEPSEEK_API_KEY
#   #19 script -qec uses bash -c (not sh default)
#   #20 no overwrite after source

set -e
set -u
set -o pipefail

# === CONFIG ===
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RECIPE_DIR="/tmp/multi-arch-30/recipe/sub"
RESULT_DIR="$MAS_ROOT/e2e-results/2026-07-29-r11027-reproducible-30agent-live-pty"
TASKS_FILE="$RESULT_DIR/tasks.yaml"
LOG_DIR="$RESULT_DIR/agent-logs"
WRAPPER_DIR="$RESULT_DIR/wrappers"
SUMMARY_FILE="$RESULT_DIR/SUMMARY.txt"
JSON_FILE="$RESULT_DIR/RESULT.json"
GOOSE_BIN="/root/.local/bin/goose"
TIMEOUT_PER_AGENT=120   # seconds (some agents need full LLM reasoning)

# === STEP 0: fail-fast (gotcha #16, #20) ===
echo "=== STEP 0: validation ==="
if [ -z "${DEEPSEEK_API_KEY:-}" ] || [ "$DEEPSEEK_API_KEY" = "***" ]; then
  echo "FATAL: DEEPSEEK_API_KEY not set or is literal-placeholder." >&2
  echo "Source .env first: source mas-engineer/.env" >&2
  exit 1
fi
KEY_LEN=${#DEEPSEEK_API_KEY}
if [ "$KEY_LEN" -lt 30 ]; then
  echo "FATAL: DEEPSEEK_API_KEY length=$KEY_LEN, expected 30+. Probably placeholder." >&2
  exit 1
fi
# Shim (gotcha #18) — only set OPENAI_API_KEY if empty/placeholder
if [ -z "${OPENAI_API_KEY:-}" ] || [ "$OPENAI_API_KEY" = "***" ]; then
  export OPENAI_API_KEY="$DEEPSEEK_API_KEY"
fi
# OPENAI_HOST — no /v1 (gotcha #3b)
export OPENAI_HOST="https://api.deepseek.com"
export GOOSE_PROVIDER=openai
export GOOSE_MODEL=deepseek-v4-flash
export GOOSE_TELEMETRY_ENABLED=false
export PATH="/root/.local/bin:$PATH"
export TERM=xterm-256color
export MAS_NO_SESSION=1
export RECURSION_OVERRIDE=2

echo "  DEEPSEEK_API_KEY length: $KEY_LEN (OK, real key)"
echo "  OPENAI_API_KEY length:   ${#OPENAI_API_KEY} (OK)"
echo "  OPENAI_HOST:             $OPENAI_HOST (OK, no /v1)"
echo "  GOOSE_MODEL:             $GOOSE_MODEL"
echo "  GOOSE bin:               $GOOSE_BIN"
echo "  Recipe dir:              $RECIPE_DIR"
echo "  Result dir:              $RESULT_DIR"
echo

# === STEP 1: verify goose sees the config + API works ===
echo "=== STEP 1: API key smoke (curl /v1/models) ==="
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $OPENAI_API_KEY" https://api.deepseek.com/v1/models)
echo "  HTTP $HTTP_CODE (expect 200)"
if [ "$HTTP_CODE" != "200" ]; then
  echo "FATAL: API key invalid (HTTP $HTTP_CODE). Aborting." >&2
  exit 1
fi
echo

# === STEP 2: prepare wrapper-recipes ===
echo "=== STEP 2: build 30 wrapper recipes (with prompt: + sub_recipes) ==="
mkdir -p "$LOG_DIR" "$WRAPPER_DIR"

python3 <<PYEOF
import os, yaml
TASKS_FILE = "$TASKS_FILE"
RECIPE_DIR = "$RECIPE_DIR"
WRAPPER_DIR = "$WRAPPER_DIR"
tasks = yaml.safe_load(open(TASKS_FILE))
print(f"  Tasks: {len(tasks)}")
for agent_name, task_text in tasks.items():
    agent_recipe = f"{RECIPE_DIR}/sub_mas-{agent_name}.yaml"
    wrapper = {
        'name': f'r11027-{agent_name}',
        'description': f'R110-27 wrapper injecting task for {agent_name}',
        'title': f'R110-27 wrapper — {agent_name}',
        'version': '1.0.0',
        'prompt': task_text,
        'sub_recipes': [{'name': agent_name, 'path': agent_recipe}],
        'extensions': [{'type': 'builtin', 'name': 'developer'}],
    }
    with open(f"{WRAPPER_DIR}/{agent_name}.yaml", "w") as f:
        yaml.safe_dump(wrapper, f, default_flow_style=False, sort_keys=False, allow_unicode=True, width=120)
print(f"  Wrote {len(tasks)} wrapper recipes to {WRAPPER_DIR}/")
PYEOF
echo

# === STEP 3: run 30 agents, one at a time, real LLM calls ===
echo "=== STEP 3: run 30 agents (real LLM, ${TIMEOUT_PER_AGENT}s timeout each) ==="
echo "  estimated total: 30 × ~10-20s = ~5-10 min"
echo

# Init SUMMARY + JSON
{
  echo "R110-27 30-agent reproducible live-PTY test"
  echo "Started: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "Recipes: $RECIPE_DIR"
  echo "Wrappers: $WRAPPER_DIR"
  echo "Model:   $GOOSE_MODEL"
  echo
  printf "%-35s %-12s %7s %7s %s\n" "AGENT" "STATUS" "TIME" "BYTES" "RC"
  echo "------------------------------------------------------------------------------------------"
} > "$SUMMARY_FILE"

echo '{"started_at":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'","agents":[' > "$JSON_FILE"

# Run agents
python3 <<PYEOF
import os, time, subprocess, json, re, yaml

TASKS_FILE = "$TASKS_FILE"
WRAPPER_DIR = "$WRAPPER_DIR"
LOG_DIR = "$LOG_DIR"
JSON_FILE = "$JSON_FILE"
SUMMARY_FILE = "$SUMMARY_FILE"
TIMEOUT = $TIMEOUT_PER_AGENT
GOOSE_BIN = "$GOOSE_BIN"
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
OPENAI_HOST = os.environ["OPENAI_HOST"]
GOOSE_MODEL = os.environ["GOOSE_MODEL"]

ansi_re = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]|\r")
err_re = re.compile(r"(401 Unauthorized|Authentication failed|404 Not Found|FATAL:)", re.IGNORECASE)

tasks = yaml.safe_load(open(TASKS_FILE))
results = []

for i, agent_name in enumerate(tasks.keys(), 1):
    wrapper = f"{WRAPPER_DIR}/{agent_name}.yaml"
    log_path = f"{LOG_DIR}/{agent_name}.log"

    print(f"  [{i:2d}/30] {agent_name:35s}", end=" ", flush=True)
    t0 = time.time()
    rc = 1
    response_text = ""
    error_found = None
    timed_out = False

    try:
        env = os.environ.copy()
        env["OPENAI_API_KEY"] = OPENAI_API_KEY
        env["OPENAI_HOST"] = OPENAI_HOST
        env["GOOSE_MODEL"] = GOOSE_MODEL

        # TRUE PTY per gotcha #4, #19: script -qec with bash -c
        # We use script(1) for real PTY (so the menu works), but for --no-session
        # headless mode we can just redirect stdin/stdout. However the user asked
        # for "in der goose cli PTY" so we use script -qec with bash -c.
        cmd = [
            "script", "-qec",
            f"bash -c '{GOOSE_BIN} run --recipe {wrapper} --no-session 2>&1'",
            log_path + ".pty"
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT, env=env)
        rc = proc.returncode
        # Read the actual log (script appends to logfile)
        try:
            response_text = open(log_path + ".pty").read()
        except Exception:
            response_text = proc.stdout + proc.stderr
        err_match = err_re.search(response_text)
        if err_match:
            error_found = err_match.group(1)
    except subprocess.TimeoutExpired as e:
        timed_out = True
        rc = 124
        try:
            response_text = open(log_path + ".pty").read()
        except Exception:
            response_text = ""
        error_found = "TIMEOUT"
    except Exception as e:
        rc = 1
        error_found = f"EXCEPTION:{type(e).__name__}:{e}"

    dt = time.time() - t0
    response_text = ansi_re.sub("", response_text)
    response_bytes = len(response_text.encode("utf-8"))

    # Write polished log
    with open(log_path, "w") as f:
        f.write(f"# R110-27 live log: {agent_name}\n")
        f.write(f"# Started:    {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t0))}\n")
        f.write(f"# Walltime:   {dt:.2f}s\n")
        f.write(f"# RC:         {rc}\n")
        f.write(f"# Bytes:      {response_bytes}\n")
        f.write(f"# Timed_out:  {timed_out}\n")
        f.write(f"# Error:      {error_found or 'none'}\n")
        f.write(f"# Wrapper:    {wrapper}\n")
        f.write(f"# Task-file:  {TASKS_FILE}\n")
        f.write("# " + "="*70 + "\n\n")
        f.write(response_text)
    # Also keep raw PTY log
    if os.path.exists(log_path + ".pty"):
        os.rename(log_path + ".pty", log_path + ".pty.log")

    # Status
    status = "PASS"
    if timed_out: status = "TIMEOUT"
    elif error_found == "401 Unauthorized" or error_found == "Authentication failed": status = "AUTH_FAIL"
    elif error_found == "404 Not Found": status = "NOT_FOUND"
    elif error_found and "FATAL" in (error_found or ""): status = "FAIL"
    elif rc != 0: status = "FAIL"
    elif response_bytes < 200: status = "EMPTY"

    has_response = response_bytes > 200
    has_substantive = has_response and len([l for l in response_text.split("\n") if l.strip()]) >= 3

    results.append({
        "agent": agent_name,
        "idx": i,
        "rc": rc,
        "walltime_s": round(dt, 2),
        "bytes": response_bytes,
        "status": status,
        "timed_out": timed_out,
        "error_found": error_found,
        "has_response": has_response,
        "has_substantive": has_substantive,
    })

    with open(JSON_FILE, "a") as f:
        if i > 1: f.write(",")
        json.dump(results[-1], f)

    with open(SUMMARY_FILE, "a") as f:
        f.write(f"{agent_name:35s} {status:12s} {dt:6.1f}s {response_bytes:6d} rc={rc}\n")

    print(f"{status:12s} {dt:5.1f}s {response_bytes:6d}B rc={rc}")
    if error_found: print(f"              error: {error_found}")

# Close JSON
with open(JSON_FILE, "a") as f:
    f.write("],")
    finished_at_str = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    f.write('"finished_at":"' + finished_at_str + '"')
    f.write("}")

# Final summary
n_pass = sum(1 for r in results if r["status"] == "PASS")
n_fail = sum(1 for r in results if r["status"] in ("FAIL","EMPTY","TIMEOUT","AUTH_FAIL","NOT_FOUND"))
n_substantive = sum(1 for r in results if r["has_substantive"])
total_wall = sum(r["walltime_s"] for r in results)
total_bytes = sum(r["bytes"] for r in results)
statuses = {}
for r in results:
    statuses[r["status"]] = statuses.get(r["status"], 0) + 1

print()
print(f"=== FINAL ===")
print(f"  Total agents:  {len(results)}")
print(f"  PASS:          {n_pass}")
print(f"  FAIL (total):  {n_fail}")
print(f"    by reason:   {statuses}")
print(f"  Substantive:   {n_substantive} (response > 200B AND ≥ 3 non-empty lines)")
print(f"  Total wall:    {total_wall:.1f}s")
print(f"  Total bytes:   {total_bytes}")
print(f"  Summary:       {SUMMARY_FILE}")
print(f"  JSON:          {JSON_FILE}")
print(f"  Logs:          {LOG_DIR}/")
PYEOF

SCRIPT_RC=$?

{
  echo "------------------------------------------------------------------------------------------"
  echo "Finished: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
} >> "$SUMMARY_FILE"

echo
echo "=== DONE — see $SUMMARY_FILE and $JSON_FILE ==="
exit $SCRIPT_RC
