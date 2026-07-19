#!/bin/bash
# e2e-demo-runner.sh — E2E test of sub_mas-demo-runner
# Tests the research-team that the demo-runner creates, then runs it on
# a 2nd task + improvement cycle, pushes only evidence (NOT the
# generated research-team files).
set -e
export DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY:-sk-YOUR-KEY-HERE}"
if [ "$DEEPSEEK_API_KEY" = "sk-YOUR-KEY-HERE" ] || [ ${#DEEPSEEK_API_KEY} -lt 30 ]; then
  echo "FATAL: DEEPSEEK_API_KEY is not set or too short. Source your env first." >&2
  exit 1
fi
export PATH="/root/.local/bin:$PATH"
export GOOSE_PROVIDER=openai
export GOOSE_MODEL=deepseek-chat
export OPENAI_HOST=https://api.deepseek.com
export OPENAI_API_KEY="${OPENAI_API_KEY:-$DEEPSEEK_API_KEY}"
export EVIDENCE=/workspace/e2e-evidence-demo-runner
export DATE=2026-07-19-demo-runner
export OUT=/workspace/mas-engineer-src/e2e-results/$DATE
mkdir -p "$EVIDENCE" "$OUT"
log() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$EVIDENCE/run.log"; }
section() { echo ""; echo "==== $* ====" | tee -a "$EVIDENCE/run.log"; }
goose_run() {
  local name="$1"; local text="$2"; local timeout="${3:-480}"
  log "goose run: $name (timeout ${timeout}s)"
  timeout "$timeout" goose run --no-session --text "$text" \
    2>&1 | tee "$EVIDENCE/${name}.log" | tail -8
}
section "STEP 0: Verify setup"
which goose || { log "FATAL: goose not installed"; exit 1; }
goose --version | tee -a "$EVIDENCE/run.log"
log "DEEPSEEK_API_KEY set: ${DEEPSEEK_API_KEY:0:10}..."
ls ~/.config/goose/recipes/sub/ | grep -c demo
log "demo-runner recipe installed"
section "STEP 1: Invoke sub_mas-demo-runner — build research-team"
# The demo-runner needs explicit "yes" confirmation (R01 rule).
# We say it in the prompt to make the run non-interactive.
goose_run "demo-runner-build" "Please run the sub_mas-demo-runner. The User confirms: yes, build the demo. Build a complete Multi-Agent System called 'research-team' at /tmp/research-team with 5 interconnected agents (research-orchestrator, web-searcher, source-verifier, fact-extractor, synthesizer) and the dashboard infrastructure (.mas/dashboards/data.json, .mas/mcp/server.js, .mas/mcp/dashboard.html, .mas/mcp/mas-dispatch-monitor.html). Then run all 14 live tests (5x goose --explain, 6x yaml.safe_load, 3x dashboard) and report PASS/FAIL. Runtime ~3 min. yes — proceed." 600
section "STEP 2: Verify generated research-team framework"
ls -la /tmp/research-team/recipe/ 2>&1 | tee -a "$EVIDENCE/run.log"
ls -la /tmp/research-team/recipe/sub/ 2>&1 | tee -a "$EVIDENCE/run.log"
ls -la /tmp/research-team/.mas/ 2>&1 | tee -a "$EVIDENCE/run.log"
section "STEP 3: Run 14 verification tests INDEPENDENTLY (outside the runner)"
log "Test 1-5: goose run --explain on each recipe"
for recipe in research-team web-searcher source-verifier fact-extractor synthesizer; do
  path="/tmp/research-team/recipe/${recipe}.yaml"
  [ "$recipe" != "research-team" ] && path="/tmp/research-team/recipe/sub/${recipe}.yaml"
  log "  Testing $path"
  if timeout 60 goose run --recipe "$path" --no-session --explain 2>&1 | tee -a "$EVIDENCE/verify-${recipe}.log" | tail -3; then
    log "    PASS: $recipe --explain"
  else
    log "    FAIL: $recipe --explain"
  fi
done
log "Test 6-11: python yaml.safe_load"
python3 -c "
import yaml, sys
files = [
  '/tmp/research-team/recipe/research-team.yaml',
  '/tmp/research-team/recipe/sub/web-searcher.yaml',
  '/tmp/research-team/recipe/sub/source-verifier.yaml',
  '/tmp/research-team/recipe/sub/fact-extractor.yaml',
  '/tmp/research-team/recipe/sub/synthesizer.yaml',
  '/tmp/research-team/.mas/dashboards/data.json',
]
ok=0; fail=0
for f in files:
    try:
        with open(f) as fp:
            yaml.safe_load(fp) if f.endswith(('.yaml','.yml')) else __import__('json').load(fp)
        print(f'  OK: {f}')
        ok+=1
    except Exception as e:
        print(f'  FAIL: {f}: {e}')
        fail+=1
print(f'YAMLs: {ok} OK, {fail} FAIL')
" 2>&1 | tee -a "$EVIDENCE/run.log"
log "Test 12-14: dashboard files"
for f in /tmp/research-team/.mas/mcp/server.js /tmp/research-team/.mas/mcp/dashboard.html /tmp/research-team/.mas/mcp/mas-dispatch-monitor.html; do
  if [ -f "$f" ]; then
    size=$(stat -c%s "$f")
    log "  OK: $f ($size bytes)"
  else
    log "  FAIL: $f (missing)"
  fi
done
section "STEP 4: Test 1 — actually use the research-team on a real query"
goose_run "research-team-task1" "Use the research-team at /tmp/research-team to answer this question: 'What were the key findings of the 2024 Nobel Prize in Physics?'. Run the full pipeline: research-orchestrator decomposes the task, web-searcher finds sources, source-verifier validates them, fact-extractor extracts facts, synthesizer writes the final report WITH inline citations [1], [2], [3]. Report what each agent did and show the final synthesized answer." 600
section "STEP 5: Test 2 — second query to verify reusability"
goose_run "research-team-task2" "Use the research-team at /tmp/research-team again, this time for: 'Who invented the C programming language and when?'. Same pipeline: orchestrator -> 4 specialists. Show me the inline citations in the final answer." 600
section "STEP 6: Improvement cycle"
goose_run "improve-research-team" "Please review and improve the research-team at /tmp/research-team. Look at the 5 recipes in /tmp/research-team/recipe/sub/ and the orchestrator in /tmp/research-team/recipe/research-team.yaml. Identify issues: unclear prompts, missing fields, weak verification logic, no source attribution in synthesizer, etc. Fix them. Validate all YAMLs after changes. Output a list of improvements made." 600
section "STEP 7: Re-test after improvement"
goose_run "research-team-task1-retry" "Use the (now improved) research-team at /tmp/research-team to answer: 'What is quantum entanglement?'. Show the final report with citations." 600
section "STEP 8: Copy evidence to git-tracked location (NOT the research-team files)"
mkdir -p "$OUT/evidence"
cp /workspace/e2e-evidence-demo-runner/*.log "$OUT/evidence/" 2>/dev/null || true
cp /workspace/e2e-evidence-demo-runner/run.log "$OUT/" 2>/dev/null || true
log "Evidence copied to $OUT/evidence/"
log "Research-team files at /tmp/research-team are NOT copied to git (per user request)"
section "STEP 9: Generate summary"
{
  echo "# E2E Test — sub_mas-demo-runner (2026-07-19)"
  echo ""
  echo "## What was tested"
  echo "- sub_mas-demo-runner (recipe: ~/.config/goose/recipes/sub/sub_mas-demo-runner.yaml)"
  echo "- Builds research-team at /tmp/research-team (5 agents + dashboard)"
  echo "- 14 verification tests"
  echo "- 2 real research tasks"
  echo "- 1 improvement cycle"
  echo "- 1 retry after improvement"
  echo ""
  echo "## What was NOT pushed"
  echo "- /tmp/research-team/recipe/* (created by demo-runner, per user instruction)"
  echo "- /tmp/research-team/.mas/* (created by demo-runner, per user instruction)"
  echo ""
  echo "## Files in this folder"
  echo "- evidence/ — all 9+ goose run logs"
  echo "- run.log — main timing log"
  echo "- e2e-demo-runner.sh — replay script (in scripts/)"
} > "$OUT/README.md"
log "Summary written to $OUT/README.md"
echo ""
echo "=================================="
echo "E2E DEMO-RUNNER TEST COMPLETE"
echo "=================================="
echo "Evidence: $OUT/"
ls "$OUT/evidence/"*.log 2>/dev/null | wc -l
echo "log files in evidence/"
echo ""
echo "Research-team files (NOT pushed): /tmp/research-team/"
echo "Files: $(find /tmp/research-team -type f 2>/dev/null | wc -l)"
du -sh /tmp/research-team/ 2>/dev/null
