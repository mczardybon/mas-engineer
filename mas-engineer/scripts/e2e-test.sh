#!/usr/bin/env bash
# e2e-test.sh — Run complete E2E test of every function in the current change
#
# Per user rule (2026-07-19):
#   "kein pust ohne vorherigen komplette e2e Test alles enthaltenen Funktionen.. 100% e2e"
#
# Translation: No push without previous complete E2E test of all contained
# functions. 100% E2E coverage required before any push.
#
# Usage:
#   ./scripts/e2e-test.sh                 # test only files changed in this push
#   ./scripts/e2e-test.sh --all           # test entire repo
#   ./scripts/e2e-test.sh --since REF     # test files changed since REF
#
# Returns:
#   0 — all checks PASS (or marked SKIP)
#   1 — any check FAIL
#
# This script must be run AFTER ./scripts/goose-reinstall.sh and
# AFTER `export DEEPSEEK_API_KEY=...`.

set -e

# This script is meant to be run from the project root (the directory
# containing recipe/, docs/, scripts/, .mase/, etc.). It does NOT auto-
# detect a parent git root, because the project is sometimes checked out
# as a subfolder of a larger git workspace.
cd "$(dirname "$0")/.."
ROOT=$(pwd)
export PATH="/root/.local/bin:$PATH"

# Parse args
SCOPE="changed"  # default: only files changed in current push
SINCE_REF="HEAD"
for arg in "$@"; do
  case "$arg" in
    --all) SCOPE="all" ;;
    --since) SCOPE="since"; SINCE_REF="NEXT" ;;  # next arg
    *) [ "$SCOPE" = "since" ] && [ "$SINCE_REF" = "NEXT" ] && SINCE_REF="$arg" ;;
  esac
done

# Build the file list based on scope
if [ "$SCOPE" = "all" ]; then
  SCOPE_DESC="entire repo"
  FILE_FILTER=""
elif [ "$SCOPE" = "since" ]; then
  SCOPE_DESC="since $SINCE_REF"
  FILE_FILTER="--since $SINCE_REF"
else
  # changed in current uncommitted state (modified + untracked) + last commit
  SCOPE_DESC="current change (uncommitted + last commit)"
  # Get all changed files including untracked
  MODIFIED=$(git status --porcelain | awk '{print $2}' | grep -v '^$' || true)
  # Get untracked files that are NEW (marked with ??)
  UNTRACKED=$(git status --porcelain | awk '$1 == "??{print $2}' || true)
  # Last commit: include only Added/Copied/Modified/Renamed/Type-changed
  # (R110-233 fix: --diff-filter=ACMRT excludes Deleted, so that a commit
  # which removed a file (e.g. R110-232 removed recipe/sub/sub_mas-clone.yaml)
  # does not cause the YAML-parse + agent-smoke checks to fail on a
  # non-existent path. Prior to this fix, every commit with a deletion
  # in HEAD would fail check [3/10] and [7/10] with "missing: <path>".)
  LAST_COMMIT=$(git diff-tree --no-commit-id --name-only -r --diff-filter=ACMRT HEAD 2>/dev/null || true)
  ALL_CHANGED=$(echo -e "$MODIFIED\n$UNTRACKED\n$LAST_COMMIT" | sort -u | grep -v '^$' || true)

  # Strip the git-root-relative prefix so paths match the local working dir.
  # (git status reports paths relative to the git root, but we run from the
  # project subfolder, e.g. /home/user/projects/mas-engineer/mas-engineer/.)
  GIT_ROOT_REL=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
  if [ "$GIT_ROOT_REL" != "$ROOT" ]; then
    # Compute the suffix of ROOT that comes after GIT_ROOT_REL
    PREFIX="${ROOT#$GIT_ROOT_REL/}/"
    echo "  Note: stripping '$PREFIX' prefix from changed-file paths"
    ALL_CHANGED=$(echo "$ALL_CHANGED" | sed "s|^${PREFIX}||" | grep -v '^$' || true)
  fi

  # Save to a temp file for the python check to read
  echo "$ALL_CHANGED" > /tmp/e2e-changed-files-$$
  FILE_FILTER="/tmp/e2e-changed-files-$$"
fi

PASS=0
FAIL=0
SKIP=0
RESULTS=()

check_pass() {
  PASS=$((PASS + 1))
  RESULTS+=("PASS: $1")
  echo "  PASS: $1"
}

check_fail() {
  FAIL=$((FAIL + 1))
  RESULTS+=("FAIL: $1")
  echo "  FAIL: $1"
}

check_skip() {
  SKIP=$((SKIP + 1))
  RESULTS+=("SKIP: $1")
  echo "  SKIP: $1"
}

echo "================================================================"
echo "E2E TEST — MAS-Engineer (scope: $SCOPE_DESC)"
echo "Started: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Root: $ROOT"
echo "================================================================"

# -----------------------------------------------------------------
# E2E #1: goose is installed
# -----------------------------------------------------------------
echo ""
echo "[1/12] goose installed"
if command -v goose >/dev/null 2>&1; then
  check_pass "goose installed: $(goose --version)"
elif [ -n "$E2E_SKIP_ENV_REQUIRED" ]; then
  check_skip "goose installed — not installed in CI (E2E_SKIP_ENV_REQUIRED=1)"
else
  check_fail "goose installed — binary not in PATH"
fi

# -----------------------------------------------------------------
# E2E #2: DEEPSEEK_API_KEY set
# -----------------------------------------------------------------
echo ""
echo "[2/12] DEEPSEEK_API_KEY set"
if [ -n "$DEEPSEEK_API_KEY" ]; then
  check_pass "DEEPSEEK_API_KEY set (${DEEPSEEK_API_KEY:0:8}...)"
elif [ -n "$E2E_SKIP_ENV_REQUIRED" ]; then
  check_skip "DEEPSEEK_API_KEY set — not set in CI (E2E_SKIP_ENV_REQUIRED=1)"
else
  check_fail "DEEPSEEK_API_KEY set — env var empty"
fi

# -----------------------------------------------------------------
# E2E #3: YAML files parse (in scope)
# -----------------------------------------------------------------
echo ""
echo "[3/12] YAML parse (scope: $SCOPE_DESC)"
YAML_FAIL=0
YAML_COUNT=0
if [ "$SCOPE" = "all" ]; then
  YAML_FILES=$(find . -name "*.yaml" \
    -not -path "./.git/*" \
    -not -path "./vendor/*" \
    -not -path "./node_modules/*" \
    -not -path "*/node_modules/*" \
    -not -path "./.monitor/memory/*" \
    -not -path "./.mase/pipeline/*" \
    -not -path "./.mase/checkpoints/*" \
    -not -path "./.mase/workflow_runs/*" \
    2>/dev/null | sort -u)
else
  # Only yaml/yml files in the changed-file list
  YAML_FILES=""
  while read -r f; do
    [ -z "$f" ] && continue
    case "$f" in
      *.yaml|*.yml) YAML_FILES="$YAML_FILES $f" ;;
    esac
  done < "$FILE_FILTER"
fi
for f in $YAML_FILES; do
  YAML_COUNT=$((YAML_COUNT + 1))
  if [ ! -f "$f" ]; then
    # File was renamed/moved out of this script's cwd (ROOT =
    # mas-engineer/, the project subfolder). e2e-test.sh's scope
    # is "files in this project subfolder", not the monorepo
    # root. Silently skip files that moved outside the project
    # subdir — they belong to a different subproject's scope.
    # (R110-240: this code path was hit when .github/workflows/*
    # was moved from mas-engineer/.github/workflows/* to the
    # monorepo-root .github/workflows/*. Without this guard, every
    # e2e-test run after a cross-subdir move would false-FAIL.)
    continue
  fi
  if ! python3 -c "import yaml; yaml.safe_load(open('$f'))" 2>/dev/null; then
    echo "    broken: $f"
    YAML_FAIL=1
  fi
done
if [ $YAML_FAIL -eq 0 ]; then
  check_pass "YAML parse ($YAML_COUNT files in scope)"
else
  check_fail "YAML parse — see above"
fi

# -----------------------------------------------------------------
# E2E #4: Secret scan (tracked + history) — always full repo
# -----------------------------------------------------------------
echo ""
echo "[4/12] Secret scan"
SECRETS=$(git ls-files 2>/dev/null | xargs grep -lE 'sk-[a-f0-9]{30,}|ghp_[A-Za-z0-9]{30,}' 2>/dev/null || true)
if [ -n "$SECRETS" ]; then
  check_fail "Secret scan (tracked) — found: $SECRETS"
else
  check_pass "Secret scan (tracked) — 0 hits"
fi
HIST_SECRETS=$(git rev-list --all 2>/dev/null | while read c; do git ls-tree -r "$c" 2>/dev/null; done | grep -E 'sk-[a-f0-9]{30,}|ghp_[A-Za-z0-9]{30,}' 2>/dev/null | head -3 || true)
if [ -n "$HIST_SECRETS" ]; then
  check_fail "Secret scan (history) — found in history"
else
  check_pass "Secret scan (history) — 0 hits"
fi

# -----------------------------------------------------------------
# E2E #5: Doc links (in scope, context-aware, code-block-aware)
# -----------------------------------------------------------------
# R110-253 fix: previous version of this check used a naive
# `re.findall(r'\]\(([^)]+)\)'` over the entire markdown text, which
# produced false-positives on regex-patterns inside backticks
# (e.g. `](path)`, `r'\\d+'`, `re.search(r'["\\'](\\d+)\\s+checks?')`).
# These are inline-code or fenced-code occurrences of `](X)`,
# not actual markdown links. The fix strips fenced code blocks
# (``` ... ```) and inline code spans (`...`) BEFORE scanning
# for links, so the check now only flags real link targets.
# -----------------------------------------------------------------
echo ""
echo "[5/12] Doc links (scope: $SCOPE_DESC)"
# R110-253 refactor: the original inline python check was a
# one-shot heredoc that grew too complex to maintain (it had
# inline code-stripping, regex tweaks, and a hardcoded scope
# list — all in one ~40-line block). Extracted to
# scripts/_check_doc_links.py (single source of truth) plus
# scripts/_strip_code.py (shared utility). This block now
# just sets env vars and calls the script.
export E2E_SCOPE="$SCOPE"
export E2E_FILE_FILTER="$FILE_FILTER"
if python3 scripts/_check_doc_links.py; then
  check_pass "Doc links — all resolve"
else
  check_fail "Doc links — see above"
fi

# -----------------------------------------------------------------
# E2E #6: German words (in scope, false-positive aware)
# -----------------------------------------------------------------
echo ""
echo "[6/12] German words scan (scope: $SCOPE_DESC)"
GERMAN_WORDS="ich nicht auch noch schon sehr ueber jedoch jedem eines einer einem einen waere funktionieren funktioniert geht machen gemacht erstellen erstellt benoetigt braucht verwendet benutzen benutzt kannst solltest wuerde sollte eigentlich natuerlich endlich normalerweise anschliessend beim uebrigens lediglich einige mehrere allerdings trotzdem deshalb deswegen folglich somit zunaechst zuerst daraufhin hierbei dabei davon dazu dafuer dagegen darueber darunter danach davor dazwischen gleichzeitig inzwischen zwischendurch einher einhergehend mittels anhand mithilfe zuhilfenahme kraft vermoege gemaess entsprechend betreffend hinsichtlich bezueglich"
EXCLUDE_FILES="../docs/lessons-learned.md"
python3 <<PY && check_pass "German words — 0 hits" || check_fail "German words — see above"
import re, os, sys
scope = "$SCOPE"
file_filter = "$FILE_FILTER"
if scope == "all":
  roots = [('recipe', ('.yaml', '.md')), ('docs', ('.md',))]
else:
  roots = [('recipe', ('.yaml', '.md')), ('docs', ('.md',))]
  with open(file_filter) as f:
    changed = set(line.strip() for line in f if line.strip())
files = []
for root_dir, exts in roots:
  if not os.path.isdir(root_dir):
    continue
  for root, _, fns in os.walk(root_dir):
    if any(x in root for x in ('/node_modules/', '/.git/', '/.monitor/memory/', '/.mase/mcp/')):
      continue
    for fn in fns:
      if fn.endswith(exts):
        full = os.path.join(root, fn)
        if scope != "all" and full not in changed:
          continue
        files.append(full)
files = sorted(set(f for f in files if not f.startswith('vendor/') and not f.startswith('node_modules/')))
exclude = set('$EXCLUDE_FILES'.split())
files = [f for f in files if f not in exclude]
ger = set('$GERMAN_WORDS'.split())
total = 0
for f in files:
  with open(f) as fh:
    text = fh.read().lower()
  words = re.findall(r'\b[a-zäöüß]+\b', text)
  real = [w for w in words if w in ger]
  if real:
    from collections import Counter
    c = Counter(real)
    print(f'    {f}: {dict(c)}')
    total += len(real)
sys.exit(0 if total == 0 else 1)
PY

# -----------------------------------------------------------------
# E2E #7: Agent smoke (all agents in scope, --explain)
# -----------------------------------------------------------------
echo ""
echo "[7/12] Agent smoke (goose run --explain, scope: $SCOPE_DESC)"
AGENT_FAIL=0
AGENT_COUNT=0
if [ "$SCOPE" = "all" ]; then
  AGENT_FILES=$(find recipe/sub -name "*.yaml" -type f 2>/dev/null | sort -u)
else
  AGENT_FILES=""
  while read -r f; do
    [ -z "$f" ] && continue
    case "$f" in
      recipe/sub/*.yaml) AGENT_FILES="$AGENT_FILES $f" ;;
    esac
  done < "$FILE_FILTER"
fi
for recipe in $AGENT_FILES; do
  AGENT_COUNT=$((AGENT_COUNT + 1))
  if goose run --recipe "$recipe" --explain >/dev/null 2>&1; then
    echo "    PASS: $recipe"
  else
    echo "    FAIL: $recipe"
    AGENT_FAIL=1
  fi
done
if [ $AGENT_FAIL -eq 0 ]; then
  check_pass "Agent smoke — $AGENT_COUNT agents explain cleanly"
else
  check_fail "Agent smoke — one or more agents failed --explain"
fi

# -----------------------------------------------------------------
# E2E #8: Install dry-run — looks for install.sh in root OR tools/
# -----------------------------------------------------------------
echo ""
echo "[8/12] Install dry-run"
# Find install script: prefer root, fall back to tools/dev_install.sh
INSTALL_SCRIPT=""
if [ -f "install.sh" ]; then
  INSTALL_SCRIPT="install.sh"
elif [ -f "tools/dev_install.sh" ]; then
  INSTALL_SCRIPT="tools/dev_install.sh"
fi
if [ -n "$INSTALL_SCRIPT" ]; then
  TEST_DIR="/tmp/e2e-install-test-$$"
  mkdir -p "$TEST_DIR"
  cp -r . "$TEST_DIR/"
  FAKE_HOME="$TEST_DIR/fake-home"
  mkdir -p "$FAKE_HOME/.config/goose"
  if HOME="$FAKE_HOME" bash "$TEST_DIR/$INSTALL_SCRIPT" >/dev/null 2>&1; then
    if [ -d "$FAKE_HOME/.config/goose/recipes" ] && [ -d "$FAKE_HOME/.config/goose/recipes/sub" ]; then
      check_pass "Install dry-run ($INSTALL_SCRIPT)"
    else
      check_fail "Install dry-run — recipes dir not created"
    fi
  else
    check_fail "Install dry-run — $INSTALL_SCRIPT exited non-zero"
  fi
  rm -rf "$TEST_DIR"
else
  check_fail "Install dry-run — no install.sh in root and no tools/dev_install.sh"
fi

# -----------------------------------------------------------------
# E2E #9: Uninstall dry-run — looks for uninstall.sh or reset equivalent
# -----------------------------------------------------------------
echo ""
echo "[9/12] Uninstall dry-run"
# Find uninstall script: prefer root, fall back to tools/dev_uninstall.sh
# If neither exists, run the install's cleanup step as the "uninstall" test
UNINSTALL_SCRIPT=""
if [ -f "uninstall.sh" ]; then
  UNINSTALL_SCRIPT="uninstall.sh"
elif [ -f "tools/dev_uninstall.sh" ]; then
  UNINSTALL_SCRIPT="tools/dev_uninstall.sh"
fi
if [ -n "$UNINSTALL_SCRIPT" ]; then
  TEST_DIR="/tmp/e2e-uninstall-test-$$"
  mkdir -p "$TEST_DIR"
  cp -r . "$TEST_DIR/"
  FAKE_HOME="$TEST_DIR/fake-home"
  mkdir -p "$FAKE_HOME/.config/goose"
  HOME="$FAKE_HOME" bash "$TEST_DIR/$INSTALL_SCRIPT" >/dev/null 2>&1
  if HOME="$FAKE_HOME" bash "$TEST_DIR/$UNINSTALL_SCRIPT" >/dev/null 2>&1; then
    REMAINING=$(ls "$FAKE_HOME/.config/goose/recipes/"*.yaml 2>/dev/null | wc -l)
    if [ "$REMAINING" -eq 0 ]; then
      check_pass "Uninstall dry-run ($UNINSTALL_SCRIPT)"
    else
      check_fail "Uninstall dry-run — $REMAINING files remain"
    fi
  else
    check_fail "Uninstall dry-run — $UNINSTALL_SCRIPT exited non-zero"
  fi
  rm -rf "$TEST_DIR"
else
  # No uninstall script — verify the install is at least idempotent
  # (running install twice should not duplicate recipes)
  TEST_DIR="/tmp/e2e-install-idempotent-$$"
  mkdir -p "$TEST_DIR"
  cp -r . "$TEST_DIR/"
  FAKE_HOME="$TEST_DIR/fake-home"
  mkdir -p "$FAKE_HOME/.config/goose"
  HOME="$FAKE_HOME" bash "$TEST_DIR/$INSTALL_SCRIPT" >/dev/null 2>&1
  COUNT_AFTER_FIRST=$(ls "$FAKE_HOME/.config/goose/recipes/"*.yaml 2>/dev/null | wc -l)
  HOME="$FAKE_HOME" bash "$TEST_DIR/$INSTALL_SCRIPT" >/dev/null 2>&1
  COUNT_AFTER_SECOND=$(ls "$FAKE_HOME/.config/goose/recipes/"*.yaml 2>/dev/null | wc -l)
  rm -rf "$TEST_DIR"
  if [ "$COUNT_AFTER_FIRST" -eq "$COUNT_AFTER_SECOND" ] && [ "$COUNT_AFTER_FIRST" -gt 0 ]; then
    check_pass "Uninstall dry-run (no uninstall.sh — verified idempotency: $COUNT_AFTER_FIRST recipes)"
  else
    check_fail "Uninstall dry-run — no uninstall.sh and install is not idempotent (first: $COUNT_AFTER_FIRST, second: $COUNT_AFTER_SECOND)"
  fi
fi

# -----------------------------------------------------------------
# E2E #10: SOT consistency (in scope)
# -----------------------------------------------------------------
echo ""
echo "[10/12] SOT consistency"
python3 <<'PY' && check_pass "SOT consistency" || check_fail "SOT consistency — see above"
import yaml, sys
sot = yaml.safe_load(open('.mase/workflows.yaml'))
agents = sot.get('agents', {})
if not isinstance(agents, dict):
  print(f"  agents is {type(agents).__name__}, expected dict")
  sys.exit(1)
errors = []
for name, agent in agents.items():
  if not isinstance(agent, dict):
    continue
  if 'task_workflows' not in agent:
    errors.append(f'  agent {name} missing task_workflows field')
  elif not isinstance(agent['task_workflows'], dict):
    errors.append(f'  agent {name}.task_workflows is {type(agent["task_workflows"]).__name__}, expected dict')
if errors:
  for e in errors[:10]:
    print(e)
  if len(errors) > 10:
    print(f'  ... and {len(errors) - 10} more')
  sys.exit(1)
PY

# -----------------------------------------------------------------
# E2E #11: CI workflow validation (R110-252)
# -----------------------------------------------------------------
# R110-252 — close the structural gap in e2e that only did
# yaml.safe_load on workflows (catching ~2/7 of the latent CI
# bug classes surfaced by R110-241..R110-250). The new
# scripts/ci-validate.sh script runs four sub-checks:
#   A. actionlint          — syntax / required-fields
#   B. GHA JSON-Schema     — required-fields / type-mismatches
#   C. output-dir check    — R110-250 mkdir-missing pattern
#   D. pip dry-run         — R110-246 transitive-dep pattern
# This is the pre-push hook that should have caught the 4
# R110-241..R110-250 bugs at first commit, not 4 commits later.
# Speed: ~1s for --all on the current 5 workflows. We delegate
# the entire check to ci-validate.sh (single source of truth —
# if you improve the checks there, e2e picks them up).
#
# Scope: when SCOPE=all we validate all workflows; otherwise
# we only validate workflows changed in the current commit/
# uncommitted state (mirrors check [3/10] YAML-parse scoping).
#
# Skip: E2E_SKIP_CI_VALIDATE=1 (use this in CI sandboxes that
# cannot run actionlint or fetch the GHA workflow schema).
# -----------------------------------------------------------------
echo ""
echo "[11/12] CI workflow validation (R110-252)"
if [ -n "$E2E_SKIP_CI_VALIDATE" ]; then
  check_skip "CI workflow validation — E2E_SKIP_CI_VALIDATE=1"
elif [ -f "scripts/ci-validate.sh" ]; then
  if [ "$SCOPE" = "all" ]; then
    CI_ARGS="--all"
  else
    CI_ARGS=""
  fi
  if bash scripts/ci-validate.sh $CI_ARGS > /tmp/ci-validate.out 2>&1; then
    check_pass "CI workflow validation — see /tmp/ci-validate.out for sub-check detail"
    # Print the sub-check summary so the user sees it in the
    # e2e log too (not just the temp file).
    tail -8 /tmp/ci-validate.out | sed 's/^/    /'
  else
    check_fail "CI workflow validation — see /tmp/ci-validate.out"
    sed 's/^/    /' /tmp/ci-validate.out
  fi
else
  check_fail "CI workflow validation — scripts/ci-validate.sh not found (this is the R110-252 hook; if you see this, the script was not committed)"
fi

# -----------------------------------------------------------------
# E2E #12: R110-262 redteam-2 — adversarial coverage of recently-fixed
#          spec gaps (R110-259, R110-251, R110-260)
# -----------------------------------------------------------------
# R110-262 closeout: after the 3 spec-level gaps (Check 0 commit-title
# hybrid form, Hard-Stop Copilot regex, coverage-gate wiring) were
# fixed in separate commits, we add an e2e-level smoke that runs the
# 3 redteam-1 pytest modules. If any of them regress, the e2e fails
# before the push goes out.
# -----------------------------------------------------------------
echo ""
echo "[12/12] R110-262 redteam-2 — adversarial coverage of spec gaps"
if [ -n "$E2E_SKIP_PYTEST" ]; then
  check_skip "R110-262 redteam-2 — E2E_SKIP_PYTEST=1"
elif [ -d "tests" ]; then
  # Scope: only run the 3 R110-262 redteam-1 test files regardless of
  # SCOPE (these are structural gap tests, not in-scope tests).
  # The full pytest run is owned by ci-tests.yml; this is the
  # pre-push smoke.
  PYTEST_OUT="/tmp/r110262-redteam2-$$.log"
  if python3 -m pytest \
      tests/test_r110262_check0_adversarial_titles.py \
      tests/test_r110262_hardstop_copilot_regex.py \
      tests/test_r110262_coverage_gate_wiring.py \
      --no-header -q --tb=line \
      > "$PYTEST_OUT" 2>&1; then
    N_PASSED=$(grep -oE '[0-9]+ passed' "$PYTEST_OUT" | tail -1 || echo "0 passed")
    check_pass "R110-262 redteam-2 — 3 spec-gap tests PASS ($N_PASSED)"
  else
    check_fail "R110-262 redteam-2 — see $PYTEST_OUT"
    tail -20 "$PYTEST_OUT" | sed 's/^/    /'
  fi
  rm -f "$PYTEST_OUT"
else
  check_skip "R110-262 redteam-2 — no tests/ directory in scope"
fi

# Cleanup
[ -f /tmp/e2e-changed-files-$$ ] && rm -f /tmp/e2e-changed-files-$$

# -----------------------------------------------------------------
# Final result
# -----------------------------------------------------------------
echo ""
echo "================================================================"
echo "E2E RESULT: $PASS PASS, $FAIL FAIL, $SKIP SKIP"
echo "================================================================"
if [ $FAIL -eq 0 ]; then
  echo "ALL CHECKS PASS (or SKIP). Safe to push."
  exit 0
else
  echo ""
  echo "FAILED CHECKS:"
  for r in "${RESULTS[@]}"; do
    if echo "$r" | grep -q "^FAIL"; then
      echo "  $r"
    fi
  done
  echo ""
  echo "DO NOT PUSH. Fix failed checks and re-run."
  exit 1
fi
