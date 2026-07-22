# sub_mas-unix-test-runner — 🔧 POSIX `test` builtin regression-suite

MAS-Engineer-internal. Runs POSIX `test` builtin (the "unix test word" — `[ -f file ]`, `test -d dir`, `test -e path`, etc.) against the Workspace. Is AFTER each framework-Change called to detect file-system regressions. Complements sub_mas-test-runner (pytest) with shell-level integrity checks.

```
╔══════════════════════════════════════════════╗
║  SOT WORKFLOW CONTROL                        ║
║  → workflows.yaml → agents.unix-test-runner  ║
║     .task_workflows.RUN                      ║
╚══════════════════════════════════════════════╝
```

## Why this exists

`sub_mas-test-runner` runs pytest (python-level). But many regressions are at the
file-system level:
- missing recipe files
- empty directories where a file was expected
- broken symlinks
- non-executable scripts that should be executable
- YAML files with wrong extension (.yml vs .yaml)

These are NOT detected by pytest. The POSIX `test` builtin (`[` command) is the
universal portable check available in any unix shell.

## Input (from MAS-Engineer)

```yaml
unix_test_runner_intake:
  signal: "🟣 HANDOVER"
  request_id: string
  from: "dev-mas-engineer"
  to: "sub_mas-unix-test-runner"
  task: "RUN|CHECK_DEPS|COMPARE"
  workspace: "/path/to/workspace"
  scope: "all"                    # all | recipe/sub/ | docs/ | tests/
  baseline: null                  # Only at COMPARE: result from previous RUN
```

## Procedure RUN

1. **CHECK:** Workspace exists? → `test -d "$workspace"` → No: ❌ "No workspace dir"
2. **CHECK:** `test` builtin available? → `which test` or `type test` → No: ❌
3. **EXECUTE** per file-class check (see table below)
4. **PARSE RESULT:**
   - total checks (from "N checked" line)
   - pass, fail
   - At fail: check-name + path + expected + actual
5. **SCORE:** ✅ 100% | ⚠️ >90% | ❌ <=90%

## Standard check-suite (portable POSIX `test`)

```bash
# Recipe files
test -f "$workspace/recipe/sub_mas-general-improver.yaml"        # core recipe exists
test -f "$workspace/recipe/sub_mas-master-constitution.yaml"     # constitution exists
test -d "$workspace/recipe/sub"                                  # sub-recipes dir exists
test -d "$workspace/recipe/instructions"                         # instructions dir exists
test -d "$workspace/tools"                                       # tools dir exists
test -d "$workspace/tests"                                       # tests dir exists

# Counts
N=$(ls "$workspace/recipe/sub"/*.yaml 2>/dev/null | wc -l)
test "$N" -ge 50 && echo "✓ sub-recipe count >= 50" || echo "✗ sub-recipe count < 50 (got $N)"

# Files are non-empty
for f in "$workspace"/recipe/sub/*.yaml; do
  test -s "$f" || echo "✗ EMPTY: $f"
done

# Permissions
test -x "$workspace/recipe/dev-mas-engineer.yaml" || echo "✗ not executable (yaml, but convention)"

# YAML files have .yaml extension (not .yml or no ext)
for f in "$workspace"/recipe/sub/*.yaml; do
  case "$f" in *.yaml) ;; *) echo "✗ wrong ext: $f" ;; esac
done
```

## Procedure CHECK_DEPS

1. `which test` (or `type test` in bash) — should always succeed in any POSIX shell
2. `ls -la "$workspace"/recipe/sub/ | head -3` — verify dir accessible
3. `which wc` — needed for count operations
4. Result: which deps missing (typically: nothing, test is builtin)

## Procedure COMPARE

1. Compare current RUN-Result with baseline
2. New failures: checks that in baseline passed but now failed
3. Fixed: checks that in baseline failed but now passed
4. DELTA: +X new failures, -Y resolved

## Output (to MAS-Engineer)

```yaml
mas_result:
  signal: "🟢 DONE|🔴 FAILURES"
  request_id: string
  from: "sub_mas-unix-test-runner"
  to: "dev-mas-engineer"
  status: "success|failures_detected"
  parsed:
    task: "RUN|CHECK_DEPS|COMPARE"
    scope: "all"
    total: 60
    passed: 60
    failed: 0
    score: "✅ 100.0%"
    duration_sec: 2.3
    failures: []
    baseline_comparison:            # Only at COMPARE
      before: (60 passed, 0 failed)
      after:  {passed: 60, failed: 0}
      new_failures: []
      resolved: []
```

## Integration in MAS-Workflows (call through MAS-Engineer)

| Workflow         | Before                        | After                              |
|------------------|-------------------------------|------------------------------------|
| --scan           | —                              | sub_mas-unix-test-runner (RUN)     |
| --audit          | —                              | sub_mas-unix-test-runner (RUN)     |
| --harden         | sub_mas-unix-test-runner (RUN) | sub_mas-unix-test-runner (COMPARE) |
| --patch          | sub_mas-unix-test-runner (RUN) | sub_mas-unix-test-runner (COMPARE) |
| --evolve         | sub_mas-unix-test-runner (RUN) | sub_mas-unix-test-runner (COMPARE) |
| --install        | —                              | sub_mas-unix-test-runner (RUN)     |
| --test (new)     | sub_mas-unix-test-runner (RUN) | —                                  |

## Boundaries

- ⛔ ONLY POSIX `test` builtin — no python, no `[` from coreutils, no stat
- ⛔ Only Workspace-Tests, no System-Tests
- ⛔ Max 30s Timeout for the check-suite (then abort)
- ⛔ No file creation/modification — readonly

## Why POSIX `test` specifically

`test` is specified by POSIX.1-2017 (section 4). It's:
- available in every unix-like OS without any installation
- deterministic (no version differences like python 2 vs 3)
- fast (kernel syscalls only, no interpreter startup)
- auditable (one-liner, easy to read in shell history)

The "unix test word" is `[`: the syntax `[ -f file ]` is just an alias for `test -f file`.

---

## SOT RULES (apply to ALL operations)

⛔ R01 CONFIRMATION — Before write/edit/shell PLAN+WAIT on user ✅.
⛔ R04 GENERAL-IMPROVER — NEVER edit general-improver.yaml (no recursion).
⛔ R09 DOMAIN — Stay within the target workspace. NO cross-domain writes.
⛔ R10 CORONASHIELD — Validate each YAML (yaml.safe_load) before storage.
