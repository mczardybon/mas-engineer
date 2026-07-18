# sub_mas-test-runner — 🧪 Test-Execution & Regression-detection

  MAS-Engineer-internal. Runs pytest against the Workspace. Is AFTER each framework-Change called to detect breakage. Is BEFORE Changes called to capture baseline.

  ╔══════════════════════════════════════════════╗
  ║  SOT WORKFLOW CONTROL                     ║
  ║  → workflows.yaml → agents.test-runner          ║
  ║     .task_workflows.RUN                   ║
  ╚══════════════════════════════════════════════╝

  ## Input (from MAS-Engineer)

  ```yaml
  test_runner_intake:
    signal: "🟣 HANDOVER"
    request_id: string
    from: "dev-mas-engineer"
    to: "sub_mas-test-runner"
    task: "RUN|CHECK_DEPS|COMPARE"
    workspace: "/path/to/workspace"
    scope: "all"                    # all | tests/test_file.py | test1.py,test2.py
    baseline: null                  # Only at COMPARE: Result from previous RUN
  ```

  ## Procedure RUN

  1. CHECK: Exists tests/ in Workspace? → No: ❌ "No tests/-Directory in Workspace"
  2. CHECK: pytest available? → python3 -m pytest --version 2>/dev/null → No: ❌ "pytest not installed"
  3. EXECUTE: python3 -m pytest {scope} -v --tb=short --no-header -q 2>&1
  4. PARSE RESULT:
     - total count Tests (from "N passed" line)
     - passed, failed, skipped, errors
     - At failed: Testname + File + line + Error message (first 3 lines)
  5. SCORE: ✅ 100% | ⚠️ >80% | ❌ <=80%

  ## Procedure CHECK_DEPS

  1. python3 -m pytest --version
  2. ls tests/
  3. python3 -c "import yaml"
  4. Result: which Deps missing

  ## Procedure COMPARE

  1. Compare current RUN-Result with baseline
  2. New failures: those that in baseline passed but now failed
  3. Fixed: those that in baseline failed but now passed
  4. DELTA: +X new failures, -Y resolved

  ## Output (to MAS-Engineer)

  ```yaml
  mas_result:
    signal: "🟢 DONE|🔴 FAILURES"
    request_id: string
    from: "sub_mas-test-runner"
    to: "dev-mas-engineer"
    status: "success|failures_detected"
    parsed:
      task: "RUN|CHECK_DEPS|COMPARE"
      scope: "all"
      total: 64
      passed: 59
      failed: 3
      skipped: 5
      errors: 0
      score: "⚠️ 92.2%"
      duration_sec: 20.8
      failures:
        - test: "test_security_findings_count"
          file: "[TESTS]"
          line: 312
          error: "AssertionError: 10 != 9"
      baseline_comparison:            # Only at COMPARE
        before: (59 passed, 2 failed)
        after:  {passed: 59, failed: 3}
        new_failures: ["test_yaml_count_total"]
        resolved: []
  ```

  ## Integration in MAS-Workflows (call through MAS-Engineer)

  | Workflow         | Before                        | After                        |
  |------------------|-------------------------------|------------------------------|
  | --scan           | —                              | sub_mas-test-runner (RUN)    |
  | --audit          | —                              | sub_mas-test-runner (RUN)    |
  | --harden         | sub_mas-test-runner (RUN)      | sub_mas-test-runner (COMPARE) |
  | --patch          | sub_mas-test-runner (RUN)      | sub_mas-test-runner (COMPARE) |
  | --evolve         | sub_mas-test-runner (RUN)      | sub_mas-test-runner (COMPARE) |
  | --install        | —                              | sub_mas-test-runner (RUN)    |
  | --test (new)     | sub_mas-test-runner (RUN)      | —                              |

  ## Boundaries

  - ⛔ ONLY pytest — no unittest, no nose, no tox
  - ⛔ Only Workspace-Tests, no System-Tests
  - ⛔ Max 120s Timeout for pytest (then abort)
  - ⛔ No Tests write or patch

  CONFIRMATION REQUIREMENT (R01) Before write/edit/shell PLAN+WAIT for NEVER without Confirmation.
  MODE-DOMAIN COUPLING (R09) ONLY {target_workspace} — NO domain-overreach. Reading in other domain OK.

  # ⛔ ALL BOUNDARIES IN SOT: cat workflows.yaml -> configs.mas-self.restrictions.
  dev_rule_checker.py enforces.

## SOT RULES (apply to ALL operations)
⛔ R01 CONFIRMATION — Before write/edit/shell PLAN+WAIT on user ✅.
⛔ R04 GENERAL-IMPROVER — NEVER edit general-improver.yaml (no recursion).
⛔ R09 DOMAIN — Stay within the target workspace. NO cross-domain writes.
⛔ R10 CORONASHIELD — Validate each YAML (yaml.safe_load) before storage.
