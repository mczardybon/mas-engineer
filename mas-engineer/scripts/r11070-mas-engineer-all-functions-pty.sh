#!/usr/bin/env bash
# scripts/r11070-mas-engineer-all-functions-pty.sh
# Reproducible live-PTY test: ALL sub_mas-*.yaml recipes in mas-engineer repo.
#
# Each recipe is "instructions-only" (no prompt: that's the canary in --no-session).
# Wait — actually most sub_mas-*.yaml have a `prompt:` field already. We build
# wrapper-recipes that INCLUDE the original as a sub_recipe, with a small canary
# task that asks "identify yourself + your primary function". This way:
#   - The wrapper owns the prompt (canary), so --no-session works
#   - The sub_recipe (real) owns the role/instructions
#   - Goose dispatches to the sub_recipe via the LLM's load/delegate
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
#
# Usage:
#   bash scripts/r11070-mas-engineer-all-functions-pty.sh              # all 112
#   bash scripts/r11070-mas-engineer-all-functions-pty.sh --first 20   # smoke
#   bash scripts/r11070-mas-engineer-all-functions-pty.sh --filter dev  # sub_mas-dev-*
#   bash scripts/r11070-mas-engineer-all-functions-pty.sh --dry-run     # only build wrappers
#   bash scripts/r11070-mas-engineer-all-functions-pty.sh --timeout 60

set -e
set -u
set -o pipefail

# === CONFIG ===
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RECIPE_DIR="$MAS_ROOT/recipe/sub"
RESULT_DIR_BASE="$MAS_ROOT/e2e-results"
TIMESTAMP="$(date -u +%Y-%m-%d)"
RESULT_DIR="$RESULT_DIR_BASE/${TIMESTAMP}-r11070-mas-engineer-all-functions-pty"
GOOSE_BIN="/root/.local/bin/goose"
TIMEOUT_PER_AGENT=120   # seconds (some agents need full LLM reasoning)

# === CLI FLAGS ===
FILTER=""
FIRST_N=0
DRY_RUN=0
CUSTOM_TIMEOUT=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --filter)  FILTER="$2"; shift 2;;
    --first)   FIRST_N="$2"; shift 2;;
    --dry-run) DRY_RUN=1; shift;;
    --timeout) CUSTOM_TIMEOUT="$2"; shift 2;;
    --result-dir) RESULT_DIR="$2"; shift 2;;
    -h|--help)
      echo "Usage: $0 [--filter SUBSTR] [--first N] [--dry-run] [--timeout SEC] [--result-dir DIR]"
      echo "  --filter SUBSTR  only test recipes whose name contains SUBSTR (e.g. dev, dashboard, e2e)"
      echo "  --first N        only test first N recipes (after filter)"
      echo "  --dry-run        only build wrappers/tasks, do not run goose"
      echo "  --timeout SEC    per-agent timeout (default 120)"
      echo "  --result-dir DIR custom result dir (overrides default timestamped one)"
      exit 0;;
    *) echo "Unknown flag: $1" >&2; exit 1;;
  esac
done
[[ $CUSTOM_TIMEOUT -gt 0 ]] && TIMEOUT_PER_AGENT=$CUSTOM_TIMEOUT

# Derived paths (AFTER flag parsing so --result-dir works)
TASKS_FILE="$RESULT_DIR/tasks.yaml"
LOG_DIR="$RESULT_DIR/agent-logs"
WRAPPER_DIR="$RESULT_DIR/wrappers"
SUMMARY_FILE="$RESULT_DIR/SUMMARY.txt"
JSON_FILE="$RESULT_DIR/RESULT.json"

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
echo "  Filter:                  ${FILTER:-<none>}"
echo "  First N:                 ${FIRST_N:-<all>}"
echo "  Dry-run:                 $DRY_RUN"
echo "  Timeout per agent:       ${TIMEOUT_PER_AGENT}s"
echo

# === STEP 1: verify goose sees the config + API works ===
echo "=== STEP 1: API key smoke (curl /v1/models) ==="
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $DEEPSEEK_API_KEY" https://api.deepseek.com/v1/models)
echo "  HTTP $HTTP_CODE (expect 200)"
if [ "$HTTP_CODE" != "200" ]; then
  echo "FATAL: API key invalid (HTTP $HTTP_CODE). Aborting." >&2
  exit 1
fi
echo

# === STEP 2: discover + build manifest + tasks + wrappers ===
echo "=== STEP 2: discover sub_mas-*.yaml recipes + build tasks.yaml + wrappers ==="
mkdir -p "$LOG_DIR" "$WRAPPER_DIR"

# Pass script-side vars to python heredoc via env (escapes bash-quoting issues)
export MAS_ROOT_SCRIPT="$MAS_ROOT"
export RECIPE_DIR_SCRIPT="$RECIPE_DIR"
export WRAPPER_DIR_SCRIPT="$WRAPPER_DIR"
export TASKS_FILE_SCRIPT="$TASKS_FILE"
export LOG_DIR_SCRIPT="$LOG_DIR"
export JSON_FILE_SCRIPT="$JSON_FILE"
export SUMMARY_FILE_SCRIPT="$SUMMARY_FILE"
export GOOSE_BIN_SCRIPT="$GOOSE_BIN"
export FILTER_SCRIPT="$FILTER"
export FIRST_N_SCRIPT="$FIRST_N"
export DRY_RUN_SCRIPT="$DRY_RUN"
export TIMEOUT_SCRIPT="$TIMEOUT_PER_AGENT"
export RESULT_DIR_SCRIPT="$RESULT_DIR"

python3 <<PYEOF
import os, yaml, glob, sys
MAS_ROOT = os.environ["MAS_ROOT_SCRIPT"]
RECIPE_DIR = os.environ["RECIPE_DIR_SCRIPT"]
WRAPPER_DIR = os.environ["WRAPPER_DIR_SCRIPT"]
TASKS_FILE = os.environ["TASKS_FILE_SCRIPT"]
FILTER = os.environ["FILTER_SCRIPT"]
FIRST_N = int(os.environ["FIRST_N_SCRIPT"])
DRY_RUN = bool(int(os.environ["DRY_RUN_SCRIPT"]))
TIMEOUT_PER_AGENT = int(os.environ["TIMEOUT_SCRIPT"])
RESULT_DIR = os.environ["RESULT_DIR_SCRIPT"]

# Discover recipes
all_recipes = sorted(glob.glob(f"{RECIPE_DIR}/sub_mas-*.yaml"))
all_recipes = [p for p in all_recipes if not p.endswith(".llm-backup-r89")]

# Filter
if FILTER:
    all_recipes = [p for p in all_recipes if FILTER in os.path.basename(p)]

# First N
if FIRST_N > 0:
    all_recipes = all_recipes[:FIRST_N]

print(f"  Discovered: {len(all_recipes)} recipes (after filter='{FILTER}', first={FIRST_N})")

# Build tasks.yaml
tasks = {}
manifest = []
for recipe_path in all_recipes:
    name = os.path.basename(recipe_path).replace("sub_mas-", "").replace(".yaml", "")
    try:
        with open(recipe_path) as f:
            rdata = yaml.safe_load(f)
    except Exception as e:
        print(f"  WARN: cannot parse {recipe_path}: {e}", file=sys.stderr)
        continue
    title = (rdata.get("title") or rdata.get("name") or name).strip()
    description = (rdata.get("description") or "").strip()[:200]
    # Canary task: minimal, asks for self-identification + primary capability
    canary = (
        f"You are: {name}\n"
        f"Recipe: {os.path.basename(recipe_path)}\n"
        f"Title: {title}\n"
        f"Description: {description}\n\n"
        f"Identify yourself (one line: name + version) and state your primary function "
        f"in one sentence. Then exit. Do NOT make tool calls, do NOT modify files."
    )
    tasks[name] = canary
    manifest.append({
        "name": name,
        "title": title,
        "description": description,
        "recipe": os.path.basename(recipe_path),
        "recipe_path": recipe_path,
    })

# Write tasks.yaml
os.makedirs(os.path.dirname(TASKS_FILE), exist_ok=True)
with open(TASKS_FILE, "w") as f:
    f.write(f"# R110-70 task definitions for mas-engineer all-functions live-PTY test\n")
    f.write(f"# Generated from {RECIPE_DIR}/sub_mas-*.yaml ({len(tasks)} recipes)\n")
    f.write(f"# Filter: {FILTER or '<none>'}, First N: {FIRST_N or '<all>'}\n")
    f.write(f"# Each task: minimal canary, asks recipe to self-identify + state primary function\n\n")
    for name, task in tasks.items():
        f.write(f"{name}: |\n")
        for line in task.split("\n"):
            f.write(f"  {line}\n")
        f.write("\n")
print(f"  Wrote {len(tasks)} tasks to {TASKS_FILE}")

# Write manifest.json (for downstream tools)
manifest_path = os.path.join(os.path.dirname(TASKS_FILE), "manifest.json")
with open(manifest_path, "w") as f:
    yaml.safe_dump(manifest, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
print(f"  Wrote manifest ({len(manifest)} entries) to {manifest_path}")

# Build wrapper-recipes
for entry in manifest:
    name = entry["name"]
    recipe_path = entry["recipe_path"]
    wrapper = {
        "name": f"r11070-{name}",
        "description": f"R110-70 wrapper injecting canary task for {name}",
        "title": f"R110-70 wrapper — {name}",
        "version": "1.0.0",
        "prompt": tasks[name],
        "sub_recipes": [{"name": name, "path": recipe_path}],
        "extensions": [
            {"type": "platform", "name": "summon"},
            {"type": "builtin", "name": "developer"},
        ],
        "settings": {
            "timeout": TIMEOUT_PER_AGENT,
            "max_steps": 5,  # canary: just answer + exit
            "goose_provider": "openai",
            "goose_model": "deepseek-v4-flash",
            "temperature": 0.0,
        },
    }
    wrapper_path = f"{WRAPPER_DIR}/{name}.yaml"
    with open(wrapper_path, "w") as f:
        yaml.safe_dump(wrapper, f, default_flow_style=False, sort_keys=False, allow_unicode=True, width=120)
print(f"  Wrote {len(manifest)} wrapper recipes to {WRAPPER_DIR}/")
print()

if DRY_RUN:
    print("=== DRY-RUN — stopping before goose invocation ===")
    with open(f"{RESULT_DIR}/.dry-run", "w") as f:
        f.write("dry-run completed\n")
    sys.exit(0)
PYEOF
echo

# Check dry-run marker (sys.exit(0) in heredoc only kills python, not bash)
if [ -f "$RESULT_DIR/.dry-run" ]; then
  echo
  echo "=== DRY-RUN COMPLETE — wrappers built, no goose runs ==="
  echo "  tasks:    $TASKS_FILE"
  echo "  manifest: $RESULT_DIR/manifest.json"
  echo "  wrappers: $WRAPPER_DIR/"
  echo "  re-run WITHOUT --dry-run to invoke goose on these wrappers"
  exit 0
fi

# === STEP 3: R10 CORONASHIELD pre-flight (gotcha #21) ===
echo "=== STEP 3: R10 CORONASHIELD pre-flight (validate wrappers) ==="
if [ -f "$MAS_ROOT/scripts/r11028-r10-validate.py" ]; then
  if ! python3 "$MAS_ROOT/scripts/r11028-r10-validate.py" "$WRAPPER_DIR" --strict; then
    echo "FATAL: R10 validation failed. Fix wrappers first." >&2
    exit 1
  fi
else
  echo "  WARN: r11028-r10-validate.py not found, skipping pre-flight"
fi
echo

# === STEP 4: run all agents, one at a time, real LLM calls ===
echo "=== STEP 4: run all agents (real LLM, ${TIMEOUT_PER_AGENT}s timeout each) ==="
N_RECIPES=$(ls "$WRAPPER_DIR"/*.yaml 2>/dev/null | wc -l)
echo "  $N_RECIPES recipes to test"
EST_S=$((N_RECIPES * 30))
EST_M=$((EST_S / 60))
echo "  estimated total: ~$EST_M min (assuming avg 30s per recipe)"
echo

# Init SUMMARY + JSON
{
  echo "R110-70 mas-engineer all-functions live-PTY test"
  echo "Started: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "Recipes: $RECIPE_DIR"
  echo "Wrappers: $WRAPPER_DIR"
  echo "Filter:  ${FILTER:-<none>}"
  echo "First N: ${FIRST_N:-<all>}"
  echo "Model:   $GOOSE_MODEL"
  echo "Timeout: ${TIMEOUT_PER_AGENT}s per recipe"
  echo
  printf "%-45s %-12s %7s %8s %s\n" "RECIPE" "STATUS" "TIME" "BYTES" "RC"
  echo "------------------------------------------------------------------------------------------------"
} > "$SUMMARY_FILE"

echo "{\"started_at\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"model\":\"$GOOSE_MODEL\",\"filter\":\"${FILTER:-}\",\"first_n\":${FIRST_N:-0},\"agents\":[" > "$JSON_FILE"

# Run agents
python3 <<PYEOF
import os, time, subprocess, json, re, yaml, glob, sys

TASKS_FILE = os.environ["TASKS_FILE_SCRIPT"]
WRAPPER_DIR = os.environ["WRAPPER_DIR_SCRIPT"]
LOG_DIR = os.environ["LOG_DIR_SCRIPT"]
JSON_FILE = os.environ["JSON_FILE_SCRIPT"]
SUMMARY_FILE = os.environ["SUMMARY_FILE_SCRIPT"]
TIMEOUT = int(os.environ["TIMEOUT_SCRIPT"])
GOOSE_BIN = os.environ["GOOSE_BIN_SCRIPT"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
OPENAI_HOST = os.environ["OPENAI_HOST"]
GOOSE_MODEL = os.environ["GOOSE_MODEL"]

ansi_re = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]|\r")
err_re = re.compile(r"(401 Unauthorized|Authentication failed|404 Not Found|FATAL:)", re.IGNORECASE)

wrappers = sorted(glob.glob(f"{WRAPPER_DIR}/*.yaml"))
print(f"  Running {len(wrappers)} agents...")
print()

results = []
for i, wrapper_path in enumerate(wrappers, 1):
    name = os.path.basename(wrapper_path).replace(".yaml", "")
    log_path = f"{LOG_DIR}/{name}.log"
    pty_path = log_path + ".pty"

    print(f"  [{i:3d}/{len(wrappers)}] {name:45s}", end=" ", flush=True)
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
        env["MAS_NO_SESSION"] = "1"
        env["RECURSION_OVERRIDE"] = "2"

        # TRUE PTY via script -qec + bash -c (gotcha #19)
        cmd = [
            "script", "-qec",
            f"bash -c '{GOOSE_BIN} run --recipe {wrapper_path} --no-session 2>&1'",
            pty_path
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT, env=env)
        rc = proc.returncode
        try:
            response_text = open(pty_path).read()
        except Exception:
            response_text = proc.stdout + proc.stderr
        err_match = err_re.search(response_text)
        if err_match:
            error_found = err_match.group(1)
    except subprocess.TimeoutExpired:
        timed_out = True
        rc = 124
        try:
            response_text = open(pty_path).read()
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
        f.write(f"# R110-70 live log: {name}\n")
        f.write(f"# Started:    {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t0))}\n")
        f.write(f"# Walltime:   {dt:.2f}s\n")
        f.write(f"# RC:         {rc}\n")
        f.write(f"# Bytes:      {response_bytes}\n")
        f.write(f"# Timed_out:  {timed_out}\n")
        f.write(f"# Error:      {error_found or 'none'}\n")
        f.write(f"# Wrapper:    {wrapper_path}\n")
        f.write(f"# Task-file:  {TASKS_FILE}\n")
        f.write("# " + "="*70 + "\n\n")
        f.write(response_text)
    if os.path.exists(pty_path):
        os.rename(pty_path, pty_path + ".log")

    # Status
    status = "PASS"
    if timed_out: status = "TIMEOUT"
    elif error_found == "401 Unauthorized" or error_found == "Authentication failed": status = "AUTH_FAIL"
    elif error_found == "404 Not Found": status = "NOT_FOUND"
    elif error_found and "FATAL" in error_found: status = "FAIL"
    elif rc != 0: status = "FAIL"
    elif response_bytes < 200: status = "EMPTY"

    has_response = response_bytes > 200
    has_substantive = has_response and len([l for l in response_text.split("\n") if l.strip()]) >= 3

    results.append({
        "recipe": name,
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
        f.write(f"{name:45s} {status:12s} {dt:6.1f}s {response_bytes:7d} rc={rc}\n")

    print(f"{status:12s} {dt:5.1f}s {response_bytes:7d}B rc={rc}")
    if error_found: print(f"              error: {error_found}")

# Close JSON
with open(JSON_FILE, "a") as f:
    f.write("],")
    f.write('"finished_at":"' + time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()) + '"')
    f.write(",")
    n_pass = sum(1 for r in results if r["status"] == "PASS")
    n_fail = sum(1 for r in results if r["status"] in ("FAIL","EMPTY","TIMEOUT","AUTH_FAIL","NOT_FOUND"))
    n_substantive = sum(1 for r in results if r["has_substantive"])
    total_wall = sum(r["walltime_s"] for r in results)
    total_bytes = sum(r["bytes"] for r in results)
    f.write(f'"n_pass":{n_pass},"n_fail":{n_fail},"n_substantive":{n_substantive},')
    f.write(f'"total_wall_s":{round(total_wall,2)},"total_bytes":{total_bytes}')
    f.write("}")

# Final summary
print()
print(f"=== FINAL ===")
print(f"  Total recipes: {len(results)}")
print(f"  PASS:          {n_pass}")
print(f"  FAIL (total):  {n_fail}")
statuses = {}
for r in results:
    statuses[r["status"]] = statuses.get(r["status"], 0) + 1
print(f"    by reason:   {statuses}")
print(f"  Substantive:   {n_substantive} (response > 200B AND >= 3 non-empty lines)")
print(f"  Total wall:    {total_wall:.1f}s")
print(f"  Total bytes:   {total_bytes}")
print(f"  Summary:       {SUMMARY_FILE}")
print(f"  JSON:          {JSON_FILE}")
print(f"  Logs:          {LOG_DIR}/")
PYEOF

SCRIPT_RC=$?

{
  echo "------------------------------------------------------------------------------------------------"
  echo "Finished: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
} >> "$SUMMARY_FILE"

echo
echo "=== DONE — see $SUMMARY_FILE and $JSON_FILE ==="
exit $SCRIPT_RC
