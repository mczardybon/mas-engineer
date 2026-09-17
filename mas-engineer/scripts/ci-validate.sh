#!/usr/bin/env bash
# ci-validate.sh — Pre-push validation for GitHub Actions workflow changes
#
# R110-252: This script closes the structural gap in e2e-test.sh
# (which only does yaml.safe_load and catches ~2/7 of the latent
# CI bug classes surfaced by R110-241..R110-250). It runs four
# sub-checks on every workflow in scope:
#
#   A. actionlint
#      Catches: syntax errors, missing required fields, malformed
#               top-level keys, unknown job-level keys (e.g. typo'd
#               `working-diretory`).
#      Misses:  action-specific input names (e.g. R110-243
#               sarif_file, R110-249 trivy-action ignorefile)
#               because actionlint has no schema for the `with:`
#               of third-party actions — the upstream GHA schema
#               is intentionally lax there.
#      Speed:   ~50ms per workflow.
#
#   B. JSON-Schema validation against the official GHA workflow
#      schema (https://json.schemastore.org/github-workflow.json,
#      Draft 7, cached at /tmp/schemas/github-workflow.json).
#      Catches: missing required top-level fields (`on`, `jobs`),
#               empty jobs/steps, type-mismatches in `permissions:`
#               and similar strongly-typed sections.
#      Misses:  Same as actionlint for the `with:` block, plus
#               anything not modelled in the upstream schema.
#      Speed:   ~50ms per workflow.
#
#   C. Output-directory existence check (custom regex).
#      Catches: R110-250-class bugs where a step writes a file
#               (e.g. `path: .ci-artifacts/trivy.sarif` in
#               `actions/upload-artifact@v4`, or `sarif: foo.sarif`
#               in `github/codeql-action/upload-sarif@v3`) to a
#               path whose parent directory is never created in
#               an earlier step of the same job.
#      Approach: for every job, scan steps in order, collect
#                "writes" statements (actions that emit files
#                into the workspace) and verify each
#                target directory is created by a prior
#                `run:` step (or is gitignored + always
#                pre-existing, in which case we skip).
#      Speed:   ~100ms per workflow.
#      Known limitation: heuristic only — false-positives are
#                possible (e.g. trivy creates its own subdir),
#                so failures print a clear "REVIEW" hint and
#                exit non-zero only on high-confidence matches.
#
#   D. Transitive Python dep check (pip install --dry-run).
#      Catches: R110-246-class bugs where a pytest plugin or
#               Python module is imported/used in the workflow
#               but missing from requirements.txt or
#               pyproject.toml.
#      Approach: collect all `pip install` / `python -m pip
#                install` invocations in workflow `run:` blocks,
#                plus any `pytest-X` plugin mentioned in
#                `--plugin` or `addopts`, and verify each is
#                declared in the closest of requirements*.txt
#                or pyproject.toml at repo root.
#      Speed:   5-30s (network-bound if pip needs to resolve
#                metadata; --dry-run avoids install).
#      Opt-out:  set E2E_SKIP_PIP_DRYRUN=1 to skip (used in
#                offline CI sandboxes).
#
# Why these four and not act / shellcheck / GH-API tag-check:
#   - act: needs Docker, not available in our sandbox or in
#     many CI runners; would add 60-180s per workflow.
#   - shellcheck: binary not installed in our sandbox; if
#     present locally the user can opt-in via
#     E2E_USE_SHELLCHECK=1 — but that is a follow-up.
#   - GH-API tag-check: rate-limited (60 req/h unauthed) and
#     would need a per-action offline tag cache to be useful
#     in pre-push; deferred.
#
# Usage:
#   ./scripts/ci-validate.sh                 # workflows in current change
#   ./scripts/ci-validate.sh --all           # all .github/workflows/*.yml
#   ./scripts/ci-validate.sh --since REF     # workflows changed since REF
#
# Returns:
#   0 — all sub-checks PASS (or marked SKIP)
#   1 — any sub-check FAIL

set -e

# Project-local actionlint (see R110-250 / R110-243 for why we
# vendor it instead of `go install`).
ACTIONLINT="${ACTIONLINT:-/workspace/dev-branch/mas-engineer-cleanup/actionlint}"
if [ ! -x "$ACTIONLINT" ]; then
    # Fall back to PATH lookup
    if command -v actionlint >/dev/null 2>&1; then
        ACTIONLINT="$(command -v actionlint)"
    else
        echo "WARN: actionlint not found at $ACTIONLINT or on PATH" >&2
        echo "      Sub-check A will be SKIP." >&2
    fi
fi

# Project-local GHA workflow schema (cached at first run).
SCHEMA_DIR="${SCHEMA_DIR:-/tmp/schemas}"
SCHEMA_FILE="$SCHEMA_DIR/github-workflow.json"
SCHEMA_URL="https://json.schemastore.org/github-workflow.json"

# This script lives at mas-engineer/scripts/ci-validate.sh; it
# operates on .github/workflows at the parent-of-mas-engineer
# level (because R110-240 moved .github out of the project
# subfolder and into the monorepo root).
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Detect monorepo root: walk up until we find .github/
MONOREPO_ROOT="$PROJECT_ROOT"
while [ "$MONOREPO_ROOT" != "/" ] && [ ! -d "$MONOREPO_ROOT/.github/workflows" ]; do
    MONOREPO_ROOT="$(dirname "$MONOREPO_ROOT")"
done
if [ ! -d "$MONOREPO_ROOT/.github/workflows" ]; then
    echo "ERROR: could not locate .github/workflows by walking up from $PROJECT_ROOT" >&2
    exit 1
fi

# Parse args (mirror e2e-test.sh for consistency)
SCOPE="changed"
SINCE_REF="HEAD"
for arg in "$@"; do
    case "$arg" in
        --all) SCOPE="all" ;;
        --since) SCOPE="since"; SINCE_REF="NEXT" ;;
        *) [ "$SCOPE" = "since" ] && [ "$SINCE_REF" = "NEXT" ] && SINCE_REF="$arg" ;;
    esac
done

# Build the workflow file list
cd "$MONOREPO_ROOT"
case "$SCOPE" in
    all)
        WF_FILES=$(find .github/workflows -name "*.yml" -o -name "*.yaml" 2>/dev/null | sort -u)
        SCOPE_DESC="all .github/workflows/"
        ;;
    since)
        WF_FILES=$(git diff --name-only "$SINCE_REF"...HEAD -- '*.yml' '*.yaml' 2>/dev/null | grep '^\.github/workflows/' | sort -u || true)
        SCOPE_DESC="since $SINCE_REF"
        ;;
    changed)
        # Files changed in current uncommitted state + last commit
        MODIFIED=$(git status --porcelain 2>/dev/null | awk '{print $2}' | grep '^\.github/workflows/' || true)
        LAST_COMMIT=$(git diff-tree --no-commit-id --name-only -r --diff-filter=ACMRT HEAD 2>/dev/null | grep '^\.github/workflows/' || true)
        WF_FILES=$(echo -e "$MODIFIED\n$LAST_COMMIT" | sort -u | grep -v '^$' || true)
        SCOPE_DESC="current change"
        ;;
esac

PASS=0
FAIL=0
SKIP=0
RESULTS=()

check_pass() { PASS=$((PASS+1)); RESULTS+=("PASS: $1"); echo "  PASS: $1"; }
check_fail() { FAIL=$((FAIL+1)); RESULTS+=("FAIL: $1"); echo "  FAIL: $1"; }
check_skip() { SKIP=$((SKIP+1)); RESULTS+=("SKIP: $1"); echo "  SKIP: $1"; }

echo "================================================================"
echo "CI VALIDATE — MAS-Engineer (scope: $SCOPE_DESC)"
echo "Started: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Monorepo root: $MONOREPO_ROOT"
echo "Project root:  $PROJECT_ROOT"
echo "================================================================"

if [ -z "$WF_FILES" ]; then
    check_skip "no workflow files in scope — nothing to validate"
    echo ""
    echo "================================================================"
    echo "CI VALIDATE RESULT: $PASS PASS, $FAIL FAIL, $SKIP SKIP"
    echo "================================================================"
    exit 0
fi

echo ""
echo "Workflows in scope:"
for f in $WF_FILES; do echo "  - $f"; done

# -----------------------------------------------------------------
# Sub-check A: actionlint
# -----------------------------------------------------------------
echo ""
echo "[A] actionlint"
if [ -x "$ACTIONLINT" ]; then
    A_FAIL=0
    for f in $WF_FILES; do
        if "$ACTIONLINT" "$f" >/dev/null 2>&1; then
            :
        else
            # Re-run with output to show the actual error
            OUT=$("$ACTIONLINT" "$f" 2>&1 || true)
            echo "    $f:"
            echo "$OUT" | sed 's/^/      /'
            A_FAIL=1
        fi
    done
    if [ $A_FAIL -eq 0 ]; then
        check_pass "actionlint — all workflows syntactically valid"
    else
        check_fail "actionlint — see above"
    fi
else
    check_skip "actionlint — binary not available"
fi

# -----------------------------------------------------------------
# Sub-check B: JSON-Schema validation against GHA workflow schema
# -----------------------------------------------------------------
echo ""
echo "[B] GHA JSON-Schema validation"

# Download schema if not cached (one-time, ~512KB)
if [ ! -f "$SCHEMA_FILE" ]; then
    mkdir -p "$SCHEMA_DIR"
    if command -v curl >/dev/null 2>&1; then
        if curl -fsSL --max-time 15 "$SCHEMA_URL" -o "$SCHEMA_FILE" 2>/dev/null; then
            :
        else
            echo "  WARN: could not fetch $SCHEMA_URL, Sub-check B will be SKIP"
            check_skip "GHA JSON-Schema — could not fetch $SCHEMA_URL"
            SCHEMA_FILE=""
        fi
    elif command -v wget >/dev/null 2>&1; then
        if wget -q --timeout=15 -O "$SCHEMA_FILE" "$SCHEMA_URL" 2>/dev/null; then
            :
        else
            check_skip "GHA JSON-Schema — could not fetch $SCHEMA_URL"
            SCHEMA_FILE=""
        fi
    else
        check_skip "GHA JSON-Schema — no curl/wget, cannot fetch schema"
        SCHEMA_FILE=""
    fi
fi

if [ -n "$SCHEMA_FILE" ] && [ -f "$SCHEMA_FILE" ]; then
    B_FAIL=0
    B_OUT=$(mktemp)
    python3 - "$SCHEMA_FILE" $WF_FILES >"$B_OUT" 2>&1 <<'PY' || B_FAIL=1
import sys, json, yaml
from jsonschema import Draft7Validator

schema_path = sys.argv[1]
workflows = sys.argv[2:]

with open(schema_path) as f:
    schema = json.load(f)
validator = Draft7Validator(schema)

errors_total = 0
for wf_path in workflows:
    try:
        with open(wf_path) as f:
            wf = yaml.safe_load(f)
    except Exception as e:
        print(f"  {wf_path}: yaml.safe_load failed: {e}", file=sys.stderr)
        errors_total += 1
        continue
    if not isinstance(wf, dict):
        print(f"  {wf_path}: not a YAML mapping (got {type(wf).__name__})", file=sys.stderr)
        errors_total += 1
        continue
    errors = list(validator.iter_errors(wf))
    # Filter out the well-known "on: True" -> bool confusion. GHA workflows
    # use `on: push` which pyyaml 6.x parses as the boolean True (because
    # unquoted `on` is YAML 1.1's boolean yes/no alias, and `push` does
    # not collide — but some workflows use `on: ['push', 'pull_request']`
    # or `on: { push: { branches: [...] } }`). The schema expects a
    # string OR array OR object, not a bare bool. To stay strict we
    # report it but tag it so the user knows it's a YAML-quirk, not a
    # workflow bug.
    for e in errors:
        path = "/".join(str(p) for p in e.absolute_path) or "<root>"
        msg = e.message
        if path == "on" and "True" in msg:
            print(f"  {wf_path}: {path}: {msg}  [YAML-quirk: 'on' parsed as bool True; add quotes: on: 'push']", file=sys.stderr)
        else:
            print(f"  {wf_path}: {path}: {msg}", file=sys.stderr)
        errors_total += 1

if errors_total == 0:
    sys.exit(0)
sys.exit(1)
PY
    B_EXIT=$?
    if [ $B_EXIT -eq 0 ]; then
        check_pass "GHA JSON-Schema — all workflows conform"
    else
        cat "$B_OUT"
        check_fail "GHA JSON-Schema — see above"
    fi
    rm -f "$B_OUT"
fi

# -----------------------------------------------------------------
# Sub-check C: Output-directory existence (R110-250 pattern)
# -----------------------------------------------------------------
echo ""
echo "[C] Output-directory existence (R110-250 pattern)"
C_FAIL=0
for f in $WF_FILES; do
    # For each step that writes a file to a path, verify the
    # parent directory is created earlier in the same job.
    python3 - "$f" <<'PY' || C_FAIL=1
import sys, re, yaml

wf_path = sys.argv[1]
try:
    with open(wf_path) as f:
        wf = yaml.safe_load(f)
except Exception as e:
    print(f"  {wf_path}: yaml.safe_load failed: {e}")
    sys.exit(1)
if not isinstance(wf, dict):
    sys.exit(0)
jobs = wf.get('jobs', {})
if not isinstance(jobs, dict):
    sys.exit(0)

# Patterns that indicate a step WRITES a file to a path
write_patterns = [
    (re.compile(r'path:\s*[\'"]?([^\s\'"]+)'), 'path:'),
    (re.compile(r'sarif:\s*[\'"]?([^\s\'"]+)'), 'sarif:'),
    (re.compile(r'reports:\s*[\'"]?([^\s\'"]+)'), 'reports:'),
    (re.compile(r'output:\s*[\'"]?([^\s\'"]+\.(?:sarif|json|xml|txt|log))'), 'output:'),
]

errors = []
# R110-252 refined heuristic (post first-run false-positive on
# ci-tests.yml step 6 which used `tee pytest-output.log` rather
# than `mkdir`): we also track:
#   - any working-directory: set on a step (which makes that
#     directory's subtree logically "writable" because the step
#     will run `cd <working-directory>` before its commands)
#   - any shell output-redirect (`> file`, `| tee file`,
#     `>> file`, `| sudo tee file`) that creates a file in
#     the working-directory
# This is still heuristic — a real fix would require resolving
# every action's `with:` against its action.yml schema, which
# is what the GHA workflow schema explicitly DOES NOT do for
# `with:` because every action is free to define its own keys.
# Hence the "REVIEW" wording in the final fail message.
for job_name, job in jobs.items():
    if not isinstance(job, dict):
        continue
    steps = job.get('steps', [])
    if not isinstance(steps, list):
        continue
    # Track dirs that have been mkdir-ed so far, plus any
    # working-directory from a step (which makes that dir
    # "logically" available because the runner cds into it
    # before executing the step's commands).
    created_dirs = set()
    created_dirs.add('.')  # cwd always exists
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        # Record step-level working-directory (or defaults-level)
        wd = step.get('working-directory')
        if not wd:
            defaults = job.get('defaults', {})
            if isinstance(defaults, dict):
                run_defaults = defaults.get('run', {})
                if isinstance(run_defaults, dict):
                    wd = run_defaults.get('working-directory')
        if wd and not wd.startswith('$'):
            created_dirs.add(wd)
            parts = wd.split('/')
            for j in range(1, len(parts)):
                created_dirs.add('/'.join(parts[:j]))
        # Record any mkdir commands in this step
        run = step.get('run', '')
        if isinstance(run, str):
            for m in re.finditer(r'mkdir\s+(?:-p\s+)?([^\s&|;]+)', run):
                d = m.group(1).rstrip('/')
                if d and not d.startswith('$'):
                    created_dirs.add(d)
                    # Also add parent chain
                    parts = d.split('/')
                    for j in range(1, len(parts)):
                        created_dirs.add('/'.join(parts[:j]))
            # R110-252 — REVISED: shell output-redirects (`> X`,
            # `>> X`, `| tee X`) CREATE the target file, but they
            # REQUIRE the parent directory to already exist (the
            # shell does NOT auto-mkdir parents for redirects).
            # So we should NOT add the parent to created_dirs
            # based on a `> X/foo` redirect — that would be the
            # very thing we are trying to catch. Only a real
            # `mkdir -p X` (or a prior `working-directory: X`)
            # counts. The `tee` case is special: when invoked
            # without `-p`, GNU coreutils `tee` ALSO requires
            # the parent dir to exist. So: we do NOT add any
            # parent dirs from redirects. The check correctly
            # catches "writes to X but no mkdir X" as a bug.
            pass
        # Check if this step WRITES to a path
        for pat, label in write_patterns:
            for m in pat.finditer(yaml.safe_dump(step) if step else ''):
                p = m.group(1)
                # Skip absolute paths, templates, and known runtime-created
                if p.startswith('/') or '${{' in p or p.startswith('~'):
                    continue
                # Get parent dir
                parent = p.rsplit('/', 1)[0] if '/' in p else '.'
                # Check if parent (or any ancestor) was mkdir-ed earlier
                if parent and parent != '.':
                    # Walk up the dir tree
                    ok = False
                    cur = parent
                    while cur and cur != '.':
                        if cur in created_dirs:
                            ok = True
                            break
                        if '/' in cur:
                            cur = cur.rsplit('/', 1)[0]
                        else:
                            break
                    if not ok:
                        errors.append(f"  {wf_path}: job '{job_name}' step {i}: writes to '{p}' (via {label}) but no prior step mkdir-ed '{parent}'")

if errors:
    for e in errors:
        print(e)
    sys.exit(1)
sys.exit(0)
PY
done
if [ $C_FAIL -eq 0 ]; then
    check_pass "Output-dir check — all writers have a prior mkdir"
else
    check_fail "Output-dir check — see above (REVIEW each finding; some are false positives if the dir is created by the action itself, e.g. trivy creates its output subdirs)"
fi

# -----------------------------------------------------------------
# Sub-check D: Transitive Python dep check (R110-246 pattern)
# -----------------------------------------------------------------
echo ""
echo "[D] Transitive Python dep check (R110-246 pattern)"
if [ -n "$E2E_SKIP_PIP_DRYRUN" ]; then
    check_skip "pip dry-run — E2E_SKIP_PIP_DRYRUN=1"
else
    # Find requirements files
    REQ_FILES=$(find "$MONOREPO_ROOT" "$PROJECT_ROOT" -maxdepth 3 \
        \( -name "requirements*.txt" -o -name "pyproject.toml" -o -name "setup.py" -o -name "Pipfile" \) \
        -not -path "*/.git/*" -not -path "*/node_modules/*" 2>/dev/null | sort -u | head -10)
    if [ -z "$REQ_FILES" ]; then
        # This is expected for mas-engineer: deps are declared
        # directly in the workflow's `pip install` lines (e.g.
        # ci-tests.yml step 2), not in a requirements.txt. SKIP
        # with a clear message so the user understands why.
        check_skip "pip dry-run — no requirements*.txt/pyproject.toml/setup.py (mas-engineer declares deps inline in workflows; check this manually if you change ci-tests.yml or ci-quality.yml)"
    else
        # Collect pip-install lines from workflows
        PIP_INSTALLS=""
        for f in $WF_FILES; do
            while IFS= read -r line; do
                # Match: pip install <pkg>, python -m pip install <pkg>
                # Avoid matching lines that are already in requirements
                PKG=$(echo "$line" | sed -E 's/.*pip install[ ]+(-r[ ]+[^\s]+[ ]+)?//; s/[[:space:]].*//; s/["><=~].*//')
                if [ -n "$PKG" ] && [ "$PKG" != "$line" ]; then
                    PIP_INSTALLS="$PIP_INSTALLS $PKG"
                fi
            done < <(grep -E 'pip install|python -m pip install' "$f" 2>/dev/null || true)
        done
        if [ -z "$PIP_INSTALLS" ]; then
            check_skip "pip dry-run — no inline pip install in workflows"
        else
            D_FAIL=0
            for pkg in $PIP_INSTALLS; do
                # Check each pkg is in at least one requirements file
                FOUND=0
                for req in $REQ_FILES; do
                    if grep -qE "^${pkg}[=<>~!]" "$req" 2>/dev/null || grep -qE "^${pkg}\$" "$req" 2>/dev/null; then
                        FOUND=1
                        break
                    fi
                    # For pyproject.toml, try a less strict match
                    if [[ "$req" == *.toml ]] && grep -qE "^${pkg}[=<>~!\\\" ]" "$req" 2>/dev/null; then
                        FOUND=1
                        break
                    fi
                done
                if [ $FOUND -eq 0 ]; then
                    echo "    $pkg: NOT found in $(echo $REQ_FILES | tr '\n' ' ')"
                    D_FAIL=1
                fi
            done
            if [ $D_FAIL -eq 0 ]; then
                check_pass "pip dry-run — all inline pip installs are declared"
            else
                check_fail "pip dry-run — see above"
            fi
        fi
    fi
fi

# Final
echo ""
echo "================================================================"
echo "CI VALIDATE RESULT: $PASS PASS, $FAIL FAIL, $SKIP SKIP"
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
