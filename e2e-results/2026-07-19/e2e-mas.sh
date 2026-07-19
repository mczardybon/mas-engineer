#!/bin/bash
# e2e-mas.sh — full E2E test of mas-engineer with 2 new teams
# Run from /workspace. Works after fresh sandbox reset.
# Usage: ./e2e-mas.sh
set -e
export DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY:-sk-YOUR-KEY-HERE}"
export PATH="/root/.local/bin:$PATH"
export GOOSE_PROVIDER=openai
export GOOSE_MODEL=deepseek-chat
export OPENAI_HOST=https://api.deepseek.com
export OPENAI_API_KEY="${OPENAI_API_KEY:-$DEEPSEEK_API_KEY}"
# Auto-detect available deepseek model
if curl -sS -m 5 -H "Authorization: Bearer $DEEPSEEK_API_KEY" https://api.deepseek.com/v1/models 2>/dev/null | grep -q "deepseek-v4-flash"; then
  export GOOSE_MODEL=deepseek-v4-flash
fi
export WORKSPACE=/workspace
export MAS_DIR=/workspace/mas-engineer-src
export TEAM1_DIR=/workspace/team1
export TEAM2_DIR=/workspace/team2
export EVIDENCE=/workspace/e2e-evidence
mkdir -p "$EVIDENCE"
log() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$EVIDENCE/run.log"; }
section() { echo ""; echo "==== $* ====" | tee -a "$EVIDENCE/run.log"; }
goose_run() {
  local name="$1"; local text="$2"; local timeout="${3:-480}"
  log "goose run: $name (timeout ${timeout}s)"
  timeout "$timeout" goose run --no-session --text "$text" \
    2>&1 | tee "$EVIDENCE/${name}.log" | tail -5
}
goose_recipe() {
  local name="$1"; local recipe="$2"; local timeout="${3:-480}"
  log "goose run --recipe: $name (timeout ${timeout}s)"
  timeout "$timeout" goose run --recipe "$recipe" --no-session \
    2>&1 | tee "$EVIDENCE/${name}.log" | tail -5
}
section "STEP 0: Verify goose + deepseek config"
which goose || { log "FATAL: goose not installed"; exit 1; }
goose --version | tee -a "$EVIDENCE/run.log"
log "DEEPSEEK_API_KEY set: ${DEEPSEEK_API_KEY:0:10}..."
log "OPENAI_HOST: $OPENAI_HOST"
log "GOOSE_MODEL: $GOOSE_MODEL"
section "STEP 1: Verify mas-engineer installed in goose"
ls ~/.config/goose/recipes/*.yaml 2>&1 | head -5 | tee -a "$EVIDENCE/run.log"
ls ~/.config/goose/recipes/sub/ 2>&1 | wc -l | tee -a "$EVIDENCE/run.log"
section "STEP 2: Create TEAM 1 (code-review-team)"
mkdir -p "$TEAM1_DIR"
goose_run "team1-create" \
  "Create a new sub-agent team called 'code-review-team' in $TEAM1_DIR. The team should have 3 sub-agents: (1) static-analyzer for Python syntax/lint issues, (2) security-scanner for security issues like SQL injection/hardcoded secrets/unsafe deserialization, (3) code-reviewer that synthesizes findings. Create real working files in $TEAM1_DIR/recipe/ (yaml + md) and register in $TEAM1_DIR/.state/workflows.yaml. Use the template at /workspace/mas-engineer/recipe/template/agent_template.yaml. Validate every YAML with python yaml.safe_load. After all 3 agents are created, output a summary listing the created files."
section "STEP 3: Create TEAM 2 (data-quality-team)"
mkdir -p "$TEAM2_DIR"
goose_run "team2-create" \
  "Create a new sub-agent team called 'data-quality-team' in $TEAM2_DIR. The team should have 3 sub-agents: (1) data-profiler for analyzing CSV/JSON datasets (rows, columns, types, missing values), (2) anomaly-detector for finding outliers and duplicates, (3) quality-reporter that synthesizes findings into a quality report with score 0-100. Create real working files in $TEAM2_DIR/recipe/ (yaml + md) and register in $TEAM2_DIR/.state/workflows.yaml. Use the template at /workspace/mas-engineer/recipe/template/agent_template.yaml. Validate every YAML with python yaml.safe_load."
section "STEP 4: Validate created files"
for d in "$TEAM1_DIR" "$TEAM2_DIR"; do
  log "Validating $d"
  find "$d" -name "*.yaml" -o -name "*.yml" 2>/dev/null | while read f; do
    if python3 -c "import yaml; yaml.safe_load(open('$f'))" 2>/dev/null; then
      echo "  OK: $f" | tee -a "$EVIDENCE/run.log"
    else
      echo "  FAIL: $f" | tee -a "$EVIDENCE/run.log"
    fi
  done
done
section "STEP 5: TEAM 1 — run first task (review vulnerable code)"
cat > "$TEAM1_DIR/vulnerable_app.py" << 'EOF'
import sqlite3, pickle, subprocess
DB_PASSWORD = "SuperSecret123!"
def get_user(username):
    conn = sqlite3.connect("app.db")
    query = f"SELECT * FROM users WHERE name = '{username}'"
    return conn.execute(query).fetchone()
def load_data(filename):
    with open(filename, 'rb') as f: return pickle.load(f)
def run_command(cmd):
    return subprocess.call(f"echo {cmd}", shell=True)
def divide(a, b): return a / b
EOF
TEAM1_RECIPE=$(find "$TEAM1_DIR" -name "*team*.yaml" -o -name "code-review-team.yaml" 2>/dev/null | head -1)
if [ -z "$TEAM1_RECIPE" ]; then
  log "TEAM 1 root recipe not found, using default agent"
  goose_run "team1-task1" \
    "I have a Python file at $TEAM1_DIR/vulnerable_app.py. Please review it using the code-review team in $TEAM1_DIR/recipe/. The team has 3 sub-agents: static-analyzer, security-scanner, code-reviewer. Use them to produce a code review report with findings (severity, CWE, recommendation). Output the final review."
else
  log "Found TEAM 1 root recipe: $TEAM1_RECIPE"
  goose_run "team1-task1" \
    "Please review the file $TEAM1_DIR/vulnerable_app.py using the code-review team in $TEAM1_DIR/recipe/sub/. Use the 3 sub-agents (static-analyzer, security-scanner, code-reviewer) in fan-out/fan-in pattern. Produce a final review report with findings including severity, CWE references, and recommendations. Save reports to .state/reports/."
fi
section "STEP 6: TEAM 2 — run first task (analyze dataset)"
mkdir -p "$TEAM1_DIR/data" "$TEAM2_DIR/data"
cat > "$TEAM2_DIR/data/sample_dataset.csv" << 'EOF'
id,name,age,salary,department,join_date,email
1,Alice,29,75000,Engineering,2021-03-15,alice@example.com
2,Bob,45,92000,Engineering,2019-07-22,bob@example.com
3,Charlie,34,68000,Marketing,2022-01-10,charlie@example.com
4,Diana,28,72000,Marketing,2023-06-05,diana@example.com
5,Eve,150,50000,Engineering,2020-01-01,eve@example.com
6,Alice,29,75000,Engineering,2021-03-15,alice@example.com
EOF
TEAM2_RECIPE=$(find "$TEAM2_DIR" -name "*team*.yaml" -o -name "data-quality*.yaml" 2>/dev/null | head -1)
if [ -z "$TEAM2_RECIPE" ]; then
  log "TEAM 2 root recipe not found, using default agent"
  goose_run "team2-task1" \
    "I have a CSV dataset at $TEAM2_DIR/data/sample_dataset.csv. Please analyze it using the data-quality team in $TEAM2_DIR/recipe/. The team has 3 sub-agents: data-profiler, anomaly-detector, quality-reporter. Use them to produce a quality report with score 0-100 and findings."
else
  log "Found TEAM 2 root recipe: $TEAM2_RECIPE"
  goose_run "team2-task1" \
    "Please analyze the dataset at $TEAM2_DIR/data/sample_dataset.csv using the data-quality team in $TEAM2_DIR/recipe/sub/. Use the 3 sub-agents in sequence. Extract the file path from this prompt. Produce a final quality report with score 0-100."
fi
section "STEP 7: USER-FIX — if team 2 orchestrator asks for input"
if grep -l "please provide\|file path" "$EVIDENCE/team2-task1.log" 2>/dev/null; then
  log "Team 2 orchestrator needs file-path-from-prompt fix. Asking MAS to fix."
  goose_run "team2-fix-orchestrator" \
    "The data-quality-team orchestrator in $TEAM2_RECIPE keeps asking the user to provide a file path. I want to pass the file path in my initial prompt like 'analyze /path/to/file.csv' and have the orchestrator extract it. Please fix the recipe to: (1) read the file path from the user's prompt, (2) not ask for it, (3) extract the path with regex, (4) if no path is found, use a sensible default like ./data/sample.csv. Test by running it with a file path and confirm it produces a report without asking questions."
fi
section "STEP 8: RE-RUN TEAM 2 after fix"
goose_run "team2-task1-retry" \
  "Please analyze the dataset at $TEAM2_DIR/data/sample_dataset.csv using the data-quality team. The file path is /workspace/team2/data/sample_dataset.csv. Run the full pipeline and produce a quality report with score 0-100."
section "STEP 9: IMPROVEMENT cycle for both teams"
goose_run "improve-team1" \
  "Please review and improve the code-review-team in $TEAM1_DIR/. Look at the recipes in $TEAM1_DIR/recipe/sub/ and the instructions in $TEAM1_DIR/recipe/instructions/. Identify any issues (formatting, missing fields, unclear prompts, etc.) and fix them. Validate all YAMLs after changes. Output a list of improvements made."
goose_run "improve-team2" \
  "Please review and improve the data-quality-team in $TEAM2_DIR/. Look at the recipes in $TEAM2_DIR/recipe/sub/ and the instructions in $TEAM2_DIR/recipe/instructions/. Identify any issues (formatting, missing fields, unclear prompts, etc.) and fix them. Validate all YAMLs after changes. Output a list of improvements made."
section "STEP 10: 2nd TASK for both teams"
cat > "$TEAM1_DIR/second_snippet.py" << 'EOF'
import hashlib
def hash_password(pwd):
    return hashlib.md5(pwd.encode()).hexdigest()
password = input("Enter password: ")
print(hash_password(password))
EOF
goose_run "team1-task2" \
  "Please review this second Python snippet: $TEAM1_DIR/second_snippet.py — it has a weak hash function. Use the code-review-team in $TEAM1_DIR/recipe/sub/ to analyze it. Produce a review report focused on security."
cat > "$TEAM2_DIR/data/messy_dataset.csv" << 'EOF'
id,name,age,salary,city
1,Alice,29,75000,Berlin
2,,45,92000,Berlin
3,Charlie,34,,Munich
4,Diana,28,72000,
5,Eve,150,50000,Berlin
6,Alice,29,75000,Berlin
7,,,,
EOF
goose_run "team2-task2" \
  "Please analyze this second dataset: $TEAM2_DIR/data/messy_dataset.csv — it has many missing values, outliers, and duplicates. Use the data-quality-team in $TEAM2_DIR/recipe/sub/ to produce a quality report with score 0-100."
section "STEP 11: Generate final report"
ls -la "$EVIDENCE/"*.log 2>&1 | head -20
log "E2E test complete. Evidence in $EVIDENCE/"
echo ""
echo "=================================="
echo "E2E TEST COMPLETE"
echo "=================================="
echo "Evidence: $EVIDENCE/"
ls "$EVIDENCE/"*.log
echo ""
echo "Team 1 files: $(find $TEAM1_DIR -type f 2>/dev/null | wc -l)"
echo "Team 2 files: $(find $TEAM2_DIR -type f 2>/dev/null | wc -l)"
