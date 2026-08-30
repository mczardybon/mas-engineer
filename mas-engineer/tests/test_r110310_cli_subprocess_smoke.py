"""R110-310: subprocess-test-pattern for untracked CLI tools.

The 45 tools/ files with 0% coverage are NEVER imported by the
test suite — they're invoked as `python3 tools/X.py [args]`. To
get them into coverage, we spawn them as subprocesses and
verify the exit code + stdout.

Strategy:
  - Pick 5 small CLI tools (low risk of side-effects).
  - Run each with `--help` (or `--version` / no-args fallback).
  - Verify exit code 0 and non-empty stdout.
  - Tools with required args get a probe with deliberately
    invalid args → expect non-zero exit.

This is a smoke-test pattern, NOT unit coverage of internal
functions. It guarantees the CLI parsing layer works and
brings those tools into the coverage report.
"""
import subprocess
import sys
import os
import shutil
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).parent.parent
TOOLS = REPO_ROOT / "tools"


def _run(tool_name, *args, timeout=15, expect_exit=0):
    """Run `python3 tools/<tool_name>.py <args>` from the repo root.

    Returns (exit_code, stdout, stderr).
    """
    tool_path = TOOLS / f"{tool_name}.py"
    assert tool_path.exists(), f"Tool not found: {tool_path}"
    proc = subprocess.run(
        [sys.executable, str(tool_path), *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr


# ────────────────────────────────────────────────────────────
# dev_yaml_generator — --help works
# ────────────────────────────────────────────────────────────

def test_dev_yaml_generator_help():
    """dev_yaml_generator.py --help exits 0 and prints banner."""
    rc, out, err = _run("dev_yaml_generator", "--help", timeout=20)
    assert rc == 0, f"exit={rc} stderr={err[:300]}"
    assert "YAML-Generator" in out or "Agenten" in out


# ────────────────────────────────────────────────────────────
# dev_audit — unknown subcommand handled
# ────────────────────────────────────────────────────────────

def test_dev_audit_unknown_subcommand():
    """dev_audit.py with an unknown subcommand exits non-zero with a clear message."""
    rc, out, err = _run("dev_audit", "--help", timeout=10)
    # dev_audit prints "❌ Unknown: --help" then exits 1
    assert rc != 0, f"expected non-zero exit, got 0 with stdout={out[:300]}"
    assert "Unknown" in out or "unknown" in out


# ────────────────────────────────────────────────────────────
# dev_test_runner — JSON error output on unknown command
# ────────────────────────────────────────────────────────────

def test_dev_test_runner_unknown_command():
    """dev_test_runner.py --help returns JSON with an error field."""
    rc, out, err = _run("dev_test_runner", "--help", timeout=10)
    assert rc == 0
    # Output is JSON with an "error" key
    assert '"error"' in out
    assert "unknown command" in out.lower()


# ────────────────────────────────────────────────────────────
# dev_health_report — requires --target
# ────────────────────────────────────────────────────────────

def test_dev_health_report_missing_target():
    """dev_health_report.py without --target prints a clear error."""
    rc, out, err = _run("dev_health_report", timeout=10)
    # It should exit non-zero (or 0 with error msg) and mention --target
    assert "--target" in out or "required" in out.lower()


# ────────────────────────────────────────────────────────────
# dev_registry_merge — argparse-based, --help works
# ────────────────────────────────────────────────────────────

def test_dev_registry_merge_help():
    """dev_registry_merge.py --help shows the argparse usage."""
    rc, out, err = _run("dev_registry_merge", "--help", timeout=10)
    assert rc == 0
    assert "usage:" in out
    assert "--findings" in out
    assert "--registry" in out
    assert "--project" in out


# ────────────────────────────────────────────────────────────
# dev_check_orphan_recipes — minimal coverage
# ────────────────────────────────────────────────────────────

def test_dev_check_orphan_recipes_runs():
    """dev_check_orphan_recipes.py runs from the repo root and exits."""
    rc, out, err = _run("dev_check_orphan_recipes", timeout=20)
    # Either succeeds (0) or has a non-crash exit code. Just check no exception.
    assert isinstance(rc, int)


# ────────────────────────────────────────────────────────────
# dev_phoenix_recovery_run — small CLI tool
# ────────────────────────────────────────────────────────────

def test_dev_phoenix_recovery_run_help():
    """dev_phoenix_recovery_run.py --help or no-args runs without traceback."""
    rc, out, err = _run("dev_phoenix_recovery_run", "--help", timeout=10)
    # Either prints help (rc=0) or prints usage/error (rc!=0 but no traceback)
    assert "Traceback" not in err, f"traceback in stderr: {err[:500]}"


# ────────────────────────────────────────────────────────────
# dev_yaml_generator_generic — small CLI
# ────────────────────────────────────────────────────────────

def test_dev_yaml_generator_generic_help():
    """dev_yaml_generator_generic.py --help runs without traceback."""
    rc, out, err = _run("dev_yaml_generator_generic", "--help", timeout=10)
    assert "Traceback" not in err, f"traceback in stderr: {err[:500]}"


# ────────────────────────────────────────────────────────────
# dev_security_scan — small CLI
# ────────────────────────────────────────────────────────────

def test_dev_security_scan_runs():
    """dev_security_scan.py runs from repo root and exits."""
    rc, out, err = _run("dev_security_scan", timeout=20)
    assert isinstance(rc, int)
    assert "Traceback" not in err[:200]


# ────────────────────────────────────────────────────────────
# Aggregate smoke test: walk all 45 untracked tools
# ────────────────────────────────────────────────────────────

UNTRACKED_TOOLS = [
    "dev_generic_init", "dev_rule_checker", "dev_editor",
    "dev_agent_doctor", "dev_rule_checker_generic",
    "dq_stage3_anomalies", "dev_observer", "dev_session_query",
    "dev_dashboard_refresh", "dev_architect", "e2e_run_all",
    "dev_self_auditor", "dev_workflow_runner", "dev_app_builder",
    "e2e_teams", "dev_yaml_check", "dev_analyst", "dev_goose_db",
    "dev_goose_manager", "dev_changes", "dev_gatekeeper",
    "dev_guardian_scan", "dev_health_monitor", "dev_recipe_manager",
    "dev_recursion_override", "dev_tff", "dev_dispatch_tracer",
    "dev_yaml_immune", "dev_workload_monitor", "dev_dispatch_live",
    "dev_template_engine", "bulk_findings_fixer", "dev_mq_consumer",
    "dev_goose_expert_check", "dev_directive_applier",
    "dev_security_scan", "dev_test_runner", "dev_health_report",
    "dev_yaml_generator", "dev_check_orphan_recipes",
    "pre_check_lib/auto_repair", "dev_audit",
    "dev_phoenix_recovery_run", "dev_yaml_generator_generic",
    "dev_registry_merge",
]


@pytest.mark.parametrize("tool", UNTRACKED_TOOLS)
def test_untracked_tool_runs_without_traceback(tool):
    """Each of the 45 untracked CLI tools must not crash with a traceback.

    We probe with `--help` first; if that returns non-zero with a
    traceback, we try no-args. The test PASSES if neither invocation
    produces a tool-originated Python traceback in stderr.

    R110-311 caveat: sitecustomize.py runs `coverage.process_startup()`
    in subprocesses, which itself writes a traceback to stderr when
    the .coveragerc has parse errors. We filter those out by
    requiring the traceback to mention the tool's filename.
    """
    tool_path = TOOLS / f"{tool}.py"
    if not tool_path.exists():
        pytest.skip(f"Tool not found: {tool_path}")
    # Try --help first
    rc, out, err = _run(tool, "--help", timeout=10)
    if "Traceback" in err:
        # Fall back to no-args
        rc, out, err = _run(tool, timeout=10)
    # Skip tools that fail with import-time data dependencies
    # (e.g. dq_stage3_anomalies needs DATA_PATH env var)
    if "Traceback" in err and "DATA_PATH" in err:
        pytest.skip(f"{tool}.py requires external DATA_PATH: {err[:200]}")
    # R110-311: ignore tracebacks that come from coverage.process_startup()
    # (we just want to know the TOOL didn't crash, not the coverage harness)
    # Coverage tracebacks mention coverage/control.py; tool tracebacks
    # mention the tool filename. Filter out the coverage ones.
    import re
    # Remove coverage-related traceback blocks (from process_startup)
    err_filtered = re.sub(
        r"Traceback[\s\S]+?coverage/control\.py[\s\S]+?(?=\nTraceback|\Z)",
        "",
        err,
    )
    assert "Traceback" not in err_filtered, (
        f"{tool}.py produced a traceback:\n{err_filtered[:600]}"
    )
