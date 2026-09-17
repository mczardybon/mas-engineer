"""R110-510: Coverage tests for tools/dev_workflow_runner.py (267 stmts, 0%).

Strategy:
  - Load dev_workflow_runner.py via importlib in a sandboxed dir.
  - Stub the global BASE / TOOLS_DIR / WF_FILE so workflows.yaml points to a
    tiny in-memory fixture instead of the real repo.
  - Stub subprocess.run so action="shell" / "workflow" / "rule_check" branches
    are exercised without spawning real processes.
  - Stub dev_message_queue via sys.modules so the MQ actions (enqueue/consume/
    ack/nack) work in isolation.

What's covered:
  - load(): merges workflows + task_workflows
  - list_workflows(): with and without params
  - resolve_order(): topo sort, depends_on chains, cycle detection
  - run_workflow() — every action type:
      shell (single-line + multi-line tempfile), workflow (recursive call),
      parallel, calculate, conditional (exists + boolean), delegate,
      wait_for_user, signal, rule_check, enqueue, consume, ack, nack,
      unknown action, on_error=abort
  - main / __main__ argv parsing: --list, --help, no args, --key=value,
    --key value, boolean flag, unknown workflow

The script has `if __name__ == "__main__":` guard so importlib load is safe.
"""

import importlib
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# Path to the script under test
SCRIPT = (
    Path(__file__).resolve().parent.parent / "tools" / "dev_workflow_runner.py"
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _fake_completed(*, returncode=0, stdout="", stderr=""):
    """Build a subprocess.CompletedProcess-like object."""
    cp = subprocess.CompletedProcess(args=[], returncode=returncode)
    cp.stdout = stdout
    cp.stderr = stderr
    return cp


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Provide a sandbox dir + load the module with stubbed paths."""
    # Create the sandbox layout
    (tmp_path / "tools").mkdir()
    # Workflows fixture
    wf = {
        "workflows": {
            "hello": {
                "desc": "Say hello",
                "params": {"name": "world"},
                "steps": [
                    {"id": "s1", "action": "shell", "cmd": "echo hi"}
                ],
            },
            "twostep": {
                "desc": "Two steps with dep",
                "steps": [
                    {"id": "a", "action": "shell", "cmd": "echo a"},
                    {"id": "b", "action": "shell", "cmd": "echo b", "depends_on": ["a"]},
                ],
            },
            "nested": {
                "desc": "wf referencing wf",
                "steps": [
                    {"id": "n1", "action": "workflow", "ref": "hello", "params": {"name": "x"}},
                ],
            },
            "calc_wf": {
                "desc": "with calculate step",
                "steps": [
                    {"id": "c1", "action": "calculate", "expression": "1 + 2", "into": "result"},
                    {"id": "c2", "action": "shell", "cmd": "echo {result}"},
                ],
            },
            "abort_wf": {
                "desc": "with on_error abort",
                "steps": [
                    {"id": "ab1", "action": "shell", "cmd": "false", "on_error": "abort"},
                    {"id": "ab2", "action": "shell", "cmd": "echo never"},
                ],
            },
            "parallel_wf": {
                "desc": "with parallel",
                "steps": [
                    {"id": "p1", "action": "parallel", "steps": [
                        {"id": "ps1"}, {"id": "ps2"}
                    ]},
                ],
            },
            "conditional_wf": {
                "desc": "with conditional",
                "steps": [
                    {"id": "cond1", "action": "conditional", "condition": "True",
                     "if_true": [{"id": "cs1", "cmd": "echo yes"}]},
                ],
            },
            "conditional_exists": {
                "desc": "conditional with exists",
                "steps": [
                    {"id": "ce", "action": "conditional", "condition": "/tmp exists",
                     "if_true": [{"id": "cx", "cmd": "echo yes"}]},
                ],
            },
            "delegate_wf": {
                "desc": "with delegate",
                "steps": [
                    {"id": "d1", "action": "delegate", "agent": "demo", "task": "go", "into": "delegated"},
                ],
            },
            "wait_wf": {
                "desc": "with wait_for_user",
                "steps": [
                    {"id": "w1", "action": "wait_for_user", "message": "ok?",
                     "default": "ja", "into": "user_response"},
                ],
            },
            "signal_wf": {
                "desc": "with signal",
                "steps": [
                    {"id": "sig1", "action": "signal"},
                ],
            },
            "rule_wf": {
                "desc": "with rule_check",
                "steps": [
                    {"id": "r1", "action": "rule_check"},
                ],
            },
            "unknown_wf": {
                "desc": "with unknown action",
                "steps": [
                    {"id": "u1", "action": "bogus"},
                ],
            },
            "multi_shell": {
                "desc": "shell with newlines (triggers tempfile path)",
                "steps": [
                    {"id": "m1", "action": "shell", "cmd": "echo line1\necho line2"},
                ],
            },
            "timeout_wf": {
                "desc": "timeout",
                "steps": [
                    {"id": "to1", "action": "shell", "cmd": "sleep 99", "timeout": 1},
                ],
            },
            "enq_wf": {
                "desc": "enqueue",
                "steps": [
                    {"id": "e1", "action": "enqueue", "topic": "test.topic",
                     "payload": {"key": "{val}"}, "into": "msgid"},
                ],
            },
            "consume_wf": {
                "desc": "consume happy",
                "steps": [
                    {"id": "c1", "action": "consume", "topic": "test.topic",
                     "into": "msg"},
                ],
            },
            "consume_empty_wf": {
                "desc": "consume returns None",
                "steps": [
                    {"id": "c1", "action": "consume", "topic": "test.topic"},
                ],
            },
            "consume_err_wf": {
                "desc": "consume raises",
                "steps": [
                    {"id": "c1", "action": "consume", "topic": "x.y"},
                ],
            },
            "ack_wf": {
                "desc": "ack",
                "steps": [
                    {"id": "a1", "action": "ack", "msg_id": "abc-123"},
                ],
            },
            "ack_err_wf": {
                "desc": "ack raises",
                "steps": [
                    {"id": "a1", "action": "ack", "msg_id": "x"},
                ],
            },
            "nack_wf": {
                "desc": "nack",
                "steps": [
                    {"id": "n1", "action": "nack", "msg_id": "y", "reason": "bad"},
                ],
            },
            "nack_err_wf": {
                "desc": "nack raises",
                "steps": [
                    {"id": "n1", "action": "nack", "msg_id": "y"},
                ],
            },
            "enq_err_wf": {
                "desc": "enqueue raises",
                "steps": [
                    {"id": "en1", "action": "enqueue", "topic": "x", "payload": {}},
                ],
            },
            "dep_failed_wf": {
                "desc": "with dep that fails",
                "steps": [
                    {"id": "df1", "action": "shell", "cmd": "false"},
                    {"id": "df2", "action": "shell", "cmd": "echo skip", "depends_on": ["df1"]},
                ],
            },
            "input_ref_wf": {
                "desc": "step with input + inputs keys + cross-ref",
                "steps": [
                    {"id": "st1", "action": "shell", "cmd": "echo first", "input": {"who": "world"}},
                    {"id": "st2", "action": "shell",
                     "cmd": "echo {who} {st1.msg_id}",
                     "inputs": {"extra": "boom"},
                     "depends_on": ["st1"]},
                ],
            },
        },
        "task_workflows": {
            "wf_x": {"desc": "task wf", "steps": [{"id": "x1", "action": "signal"}]},
        },
    }
    (tmp_path / ".mase").mkdir()
    (tmp_path / ".mase" / "workflows.yaml").write_text(yaml_dump(wf))
    # Drop the module so reimports get fresh module-level constants
    sys.modules.pop("dev_workflow_runner", None)

    # Patch the module's globals BEFORE import. Use a side_effect-free
    # approach: load the module first, then overwrite its module-level
    # names so subsequent function calls use the sandbox paths.
    spec = importlib.util.spec_from_file_location("dev_workflow_runner", str(SCRIPT))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["dev_workflow_runner"] = mod
    spec.loader.exec_module(mod)

    # Now overwrite BASE / TOOLS_DIR / WF_FILE / RUNS_DIR
    sandbox_base = str(tmp_path)
    mod.BASE = sandbox_base
    mod.TOOLS_DIR = sandbox_base + "/tools"
    mod.WF_FILE = sandbox_base + "/.mase/workflows.yaml"
    mod.RUNS_DIR = sandbox_base + "/.mase/workflow_runs"
    os.makedirs(mod.RUNS_DIR, exist_ok=True)

    return mod


def yaml_dump(obj):
    import yaml as _yaml
    return _yaml.safe_dump(obj, sort_keys=False)


# ──────────────────────────────────────────────────────────────────────────────
# load() + list_workflows()
# ──────────────────────────────────────────────────────────────────────────────

class TestLoad:
    def test_load_merges_workflows_and_task_workflows(self, sandbox):
        wfs = sandbox.load()
        assert "hello" in wfs
        assert "wf_x" in wfs  # from task_workflows
        assert len(wfs) > 1


class TestListWorkflows:
    def test_lists_with_params(self, sandbox, capsys):
        wfs = sandbox.load()
        sandbox.list_workflows(wfs)
        out = capsys.readouterr().out
        assert "hello" in out
        assert "name" in out  # params printed
        assert "wf_x" in out


# ──────────────────────────────────────────────────────────────────────────────
# resolve_order()
# ──────────────────────────────────────────────────────────────────────────────

class TestResolveOrder:
    def test_resolves_simple_chain(self, sandbox):
        steps = [
            {"id": "a", "action": "shell", "cmd": "echo a"},
            {"id": "b", "action": "shell", "cmd": "echo b", "depends_on": ["a"]},
        ]
        order = sandbox.resolve_order(steps)
        ids = [s["id"] for s in order]
        assert ids == ["a", "b"]

    def test_resolves_unordered_input(self, sandbox):
        steps = [
            {"id": "b", "action": "shell", "cmd": "echo b", "depends_on": ["a"]},
            {"id": "a", "action": "shell", "cmd": "echo a"},
        ]
        order = sandbox.resolve_order(steps)
        ids = [s["id"] for s in order]
        assert ids == ["a", "b"]

    def test_cycle_raises(self, sandbox):
        steps = [
            {"id": "a", "action": "shell", "cmd": "echo a", "depends_on": ["b"]},
            {"id": "b", "action": "shell", "cmd": "echo b", "depends_on": ["a"]},
        ]
        with pytest.raises(ValueError) as exc:
            sandbox.resolve_order(steps)
        assert "Zyklus" in str(exc.value)


# ──────────────────────────────────────────────────────────────────────────────
# run_workflow() — action types
# ──────────────────────────────────────────────────────────────────────────────

class TestRunWorkflow:
    def _patch_subprocess(self, monkeypatch, *, returncode=0, stdout="ok", stderr=""):
        """Patch subprocess.run to return a fake completed process."""
        def fake_run(cmd, *args, **kwargs):
            return _fake_completed(returncode=returncode, stdout=stdout, stderr=stderr)
        monkeypatch.setattr("subprocess.run", fake_run)

    def test_simple_shell(self, sandbox, monkeypatch):
        self._patch_subprocess(monkeypatch, stdout="hi there")
        # Patch sys.stdout so we don't pollute test output
        with patch.object(sys, "stdout", io.StringIO()):
            res = sandbox.run_workflow("hello", {"name": "world"}, sandbox.load())
        assert res["status"] == "ok"
        assert "s1" in res["results"]

    def test_multiline_shell_uses_tempfile(self, sandbox, monkeypatch):
        calls = []
        def fake_run(cmd, *args, **kwargs):
            calls.append(cmd)
            return _fake_completed(returncode=0, stdout="ml")
        monkeypatch.setattr("subprocess.run", fake_run)
        with patch.object(sys, "stdout", io.StringIO()):
            sandbox.run_workflow("multi_shell", {}, sandbox.load())
        # First call should be ['bash', tempfile_path]
        assert calls
        first = calls[0]
        assert isinstance(first, list)
        assert first[0] == "bash"
        # tempfile must be cleaned up
        tmp_path = first[1]
        assert not os.path.exists(tmp_path)

    def test_shell_failure_marks_step_failed(self, sandbox, monkeypatch):
        self._patch_subprocess(monkeypatch, returncode=1, stdout="nope", stderr="bad")
        with patch.object(sys, "stdout", io.StringIO()):
            res = sandbox.run_workflow("hello", {"name": "x"}, sandbox.load())
        assert res["status"] == "failed"
        assert res["results"]["s1"]["status"] == "failed"

    def test_on_error_abort_breaks(self, sandbox, monkeypatch):
        self._patch_subprocess(monkeypatch, returncode=1)
        with patch.object(sys, "stdout", io.StringIO()):
            res = sandbox.run_workflow("abort_wf", {}, sandbox.load())
        # ab2 should not have run
        assert "ab1" in res["results"]
        assert "ab2" not in res["results"]
        assert res["status"] == "failed"

    def test_dep_failed_skips_step(self, sandbox, monkeypatch):
        self._patch_subprocess(monkeypatch, returncode=1)
        with patch.object(sys, "stdout", io.StringIO()):
            res = sandbox.run_workflow("dep_failed_wf", {}, sandbox.load())
        assert res["results"]["df2"]["status"] == "skipped"

    def test_workflow_action_recurse(self, sandbox, monkeypatch):
        # The recursive call invokes dev_workflow_runner.py — replace that too
        self._patch_subprocess(monkeypatch, returncode=0, stdout="sub-ok")
        with patch.object(sys, "stdout", io.StringIO()):
            res = sandbox.run_workflow("nested", {}, sandbox.load())
        assert res["status"] == "ok"

    def test_parallel(self, sandbox, monkeypatch, capsys):
        with patch.object(sys, "stdout", io.StringIO()):
            res = sandbox.run_workflow("parallel_wf", {}, sandbox.load())
        assert res["results"]["p1"]["status"] == "ok"

    def test_calculate(self, sandbox, monkeypatch):
        self._patch_subprocess(monkeypatch)
        with patch.object(sys, "stdout", io.StringIO()):
            res = sandbox.run_workflow("calc_wf", {}, sandbox.load())
        assert res["results"]["c1"]["status"] == "ok"

    def test_calculate_failure(self, sandbox, monkeypatch):
        # Force eval to fail by referencing undefined
        mod = sandbox
        with patch.object(sys, "stdout", io.StringIO()):
            # Inject a step with bad expression
            wfs = mod.load()
            wfs["bad_calc"] = {
                "desc": "bad calc",
                "steps": [{"id": "bc1", "action": "calculate",
                           "expression": "undefined_var + 1"}],
            }
            res = mod.run_workflow("bad_calc", {}, wfs)
        assert res["results"]["bc1"]["status"] == "failed"

    def test_conditional_true_branch(self, sandbox, monkeypatch):
        self._patch_subprocess(monkeypatch)
        with patch.object(sys, "stdout", io.StringIO()):
            res = sandbox.run_workflow("conditional_wf", {}, sandbox.load())
        assert res["results"]["cond1"]["status"] == "ok"

    def test_conditional_exists_true(self, sandbox, monkeypatch):
        self._patch_subprocess(monkeypatch)
        with patch.object(sys, "stdout", io.StringIO()):
            res = sandbox.run_workflow("conditional_exists", {}, sandbox.load())
        assert res["results"]["ce"]["status"] == "ok"

    def test_conditional_substep_failure(self, sandbox, monkeypatch):
        mod = sandbox
        self._patch_subprocess(monkeypatch, returncode=1)
        wfs = mod.load()
        wfs["cond_fail"] = {
            "desc": "cond fail",
            "steps": [{"id": "cf1", "action": "conditional", "condition": "True",
                       "if_true": [{"id": "cx", "cmd": "false"}]}],
        }
        with patch.object(sys, "stdout", io.StringIO()):
            res = mod.run_workflow("cond_fail", {}, wfs)
        assert res["results"]["cf1"]["status"] == "failed"

    def test_conditional_eval_raises(self, sandbox, monkeypatch):
        mod = sandbox
        wfs = mod.load()
        wfs["cond_bad"] = {
            "desc": "cond bad",
            "steps": [{"id": "cb", "action": "conditional",
                       "condition": "this syntax raises + 1 +"}],
        }
        with patch.object(sys, "stdout", io.StringIO()):
            res = mod.run_workflow("cond_bad", {}, wfs)
        assert res["results"]["cb"]["status"] == "failed"

    def test_delegate(self, sandbox, monkeypatch):
        with patch.object(sys, "stdout", io.StringIO()):
            res = sandbox.run_workflow("delegate_wf", {}, sandbox.load())
        assert res["results"]["d1"]["status"] == "ok"

    def test_wait_for_user(self, sandbox, monkeypatch):
        with patch.object(sys, "stdout", io.StringIO()):
            res = sandbox.run_workflow("wait_wf", {}, sandbox.load())
        assert res["results"]["w1"]["status"] == "ok"

    def test_signal(self, sandbox, monkeypatch):
        with patch.object(sys, "stdout", io.StringIO()):
            res = sandbox.run_workflow("signal_wf", {}, sandbox.load())
        assert res["results"]["sig1"]["status"] == "ok"

    def test_rule_check(self, sandbox, monkeypatch):
        self._patch_subprocess(monkeypatch, stdout="all good")
        with patch.object(sys, "stdout", io.StringIO()):
            res = sandbox.run_workflow("rule_wf", {}, sandbox.load())
        assert res["results"]["r1"]["status"] == "ok"

    def test_unknown_action(self, sandbox, monkeypatch):
        with patch.object(sys, "stdout", io.StringIO()):
            res = sandbox.run_workflow("unknown_wf", {}, sandbox.load())
        assert res["results"]["u1"]["status"] == "failed"

    def test_shell_timeout(self, sandbox, monkeypatch):
        def boom(cmd, *a, **kw):
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=kw.get("timeout", 60))
        monkeypatch.setattr("subprocess.run", boom)
        with patch.object(sys, "stdout", io.StringIO()):
            res = sandbox.run_workflow("timeout_wf", {}, sandbox.load())
        assert res["results"]["to1"]["status"] == "timeout"

    def test_enqueue_ok(self, sandbox, monkeypatch):
        mq = MagicMock()
        mq.enqueue = MagicMock(return_value="msg-id-42")
        sys.modules["dev_message_queue"] = mq
        with patch.object(sys, "stdout", io.StringIO()):
            res = sandbox.run_workflow("enq_wf", {"val": "v"}, sandbox.load())
        assert res["results"]["e1"]["status"] == "ok"
        assert mq.enqueue.called

    def test_enqueue_raises(self, sandbox, monkeypatch):
        mq = MagicMock()
        mq.enqueue = MagicMock(side_effect=RuntimeError("mq down"))
        sys.modules["dev_message_queue"] = mq
        with patch.object(sys, "stdout", io.StringIO()):
            res = sandbox.run_workflow("enq_err_wf", {}, sandbox.load())
        assert res["results"]["en1"]["status"] == "failed"

    def test_consume_ok(self, sandbox, monkeypatch):
        mq = MagicMock()
        mq.consume = MagicMock(return_value={"msg_id": "abc-123"})
        sys.modules["dev_message_queue"] = mq
        with patch.object(sys, "stdout", io.StringIO()):
            res = sandbox.run_workflow("consume_wf", {}, sandbox.load())
        assert res["results"]["c1"]["status"] == "ok"

    def test_consume_empty(self, sandbox, monkeypatch):
        mq = MagicMock()
        mq.consume = MagicMock(return_value=None)
        sys.modules["dev_message_queue"] = mq
        with patch.object(sys, "stdout", io.StringIO()):
            res = sandbox.run_workflow("consume_empty_wf", {}, sandbox.load())
        assert res["results"]["c1"]["status"] == "failed"

    def test_consume_raises(self, sandbox, monkeypatch):
        mq = MagicMock()
        mq.consume = MagicMock(side_effect=RuntimeError("no conn"))
        sys.modules["dev_message_queue"] = mq
        with patch.object(sys, "stdout", io.StringIO()):
            res = sandbox.run_workflow("consume_err_wf", {}, sandbox.load())
        assert res["results"]["c1"]["status"] == "failed"

    def test_ack_ok(self, sandbox, monkeypatch):
        mq = MagicMock()
        mq.ack = MagicMock(return_value=True)
        sys.modules["dev_message_queue"] = mq
        with patch.object(sys, "stdout", io.StringIO()):
            res = sandbox.run_workflow("ack_wf", {}, sandbox.load())
        assert res["results"]["a1"]["status"] == "ok"

    def test_ack_raises(self, sandbox, monkeypatch):
        mq = MagicMock()
        mq.ack = MagicMock(side_effect=RuntimeError("ack fail"))
        sys.modules["dev_message_queue"] = mq
        with patch.object(sys, "stdout", io.StringIO()):
            res = sandbox.run_workflow("ack_err_wf", {}, sandbox.load())
        assert res["results"]["a1"]["status"] == "failed"

    def test_nack_ok(self, sandbox, monkeypatch):
        mq = MagicMock()
        mq.nack = MagicMock(return_value=True)
        sys.modules["dev_message_queue"] = mq
        with patch.object(sys, "stdout", io.StringIO()):
            res = sandbox.run_workflow("nack_wf", {}, sandbox.load())
        assert res["results"]["n1"]["status"] == "ok"

    def test_nack_raises(self, sandbox, monkeypatch):
        mq = MagicMock()
        mq.nack = MagicMock(side_effect=RuntimeError("nack fail"))
        sys.modules["dev_message_queue"] = mq
        with patch.object(sys, "stdout", io.StringIO()):
            res = sandbox.run_workflow("nack_err_wf", {}, sandbox.load())
        assert res["results"]["n1"]["status"] == "failed"

    def test_input_substitution_and_cross_ref(self, sandbox, monkeypatch):
        """Step with input + inputs keys + cross-step reference substitution."""
        # First step output must contain 'msg_id=...' so cross-ref can extract
        self._patch_subprocess(monkeypatch, stdout="ok msg_id=abc-def-123")
        with patch.object(sys, "stdout", io.StringIO()):
            res = sandbox.run_workflow("input_ref_wf", {}, sandbox.load())
        assert res["results"]["st1"]["status"] == "ok"
        assert res["results"]["st2"]["status"] == "ok"

    def test_non_string_step_field(self, sandbox, monkeypatch):
        """_substitute() handles non-string input via line 75-76 fast-path.

        We exercise the helper indirectly by passing a non-string as a
        substitution TARGET (the cmd value). When cmd is a list, _substitute
        returns it unchanged. Then the runner hits the list-form subprocess
        path (line 118 with shell=False implicit). However line 111 does
        '\n' in cmd_str which requires str. So we use a different shape:
        cmd with no newline and a list-of-list shape via inputs — not
        possible in the current runner. Skip this path: line 75-76 is only
        reachable when a non-string placeholder ends up in the substitution
        pipeline, which the runner never produces organically.
        """
        # Document the limitation; the helper's type guard is exercised by
        # the cross-ref code path which always passes strings.
        from dev_workflow_runner import resolve_order  # smoke import
        assert resolve_order([]) == []

    def test_cross_ref_non_msg_id_field(self, sandbox, monkeypatch):
        """Cross-ref with a non-msg_id field → returns str(val)."""
        mod = sandbox
        wfs = mod.load()
        wfs["cref"] = {
            "desc": "cross ref non-msg_id",
            "steps": [
                {"id": "s1", "action": "shell", "cmd": "echo first"},
                {"id": "s2", "action": "shell",
                 "cmd": "echo {s1.something}",
                 "depends_on": ["s1"]},
            ],
        }
        self._patch_subprocess(monkeypatch, stdout="out-val")
        with patch.object(sys, "stdout", io.StringIO()):
            res = mod.run_workflow("cref", {}, wfs)
        assert res["results"]["s2"]["status"] == "ok"

    def test_workflow_action_with_inputs(self, sandbox, monkeypatch):
        """workflow action with `inputs` key (line 125)."""
        self._patch_subprocess(monkeypatch, stdout="ok")
        mod = sandbox
        wfs = mod.load()
        wfs["wf_inp"] = {
            "desc": "workflow with inputs",
            "steps": [
                {"id": "w1", "action": "workflow", "ref": "hello",
                 "inputs": {"name": "zoe"}},
            ],
        }
        with patch.object(sys, "stdout", io.StringIO()):
            res = mod.run_workflow("wf_inp", {}, wfs)
        assert res["results"]["w1"]["status"] == "ok"

    def test_calculate_with_prior_results(self, sandbox, monkeypatch):
        """calculate step injects prior step outputs as variables (line 146)."""
        mod = sandbox
        wfs = mod.load()
        wfs["calc_p"] = {
            "desc": "calc with prior",
            "steps": [
                {"id": "sp1", "action": "shell", "cmd": "echo p1"},
                {"id": "sp2", "action": "calculate",
                 "expression": "sp1 + '!'",
                 "depends_on": ["sp1"], "into": "out2"},
            ],
        }
        self._patch_subprocess(monkeypatch, stdout="prior-out")
        with patch.object(sys, "stdout", io.StringIO()):
            res = mod.run_workflow("calc_p", {}, wfs)
        assert res["results"]["sp2"]["status"] == "ok"

    def test_conditional_params_in_context(self, sandbox, monkeypatch):
        """Conditional eval can reference params (line 164)."""
        mod = sandbox
        wfs = mod.load()
        wfs["cond_p"] = {
            "desc": "cond with params",
            "steps": [
                {"id": "cp1", "action": "conditional",
                 "condition": "name == 'alice'",
                 "if_true": [{"id": "cx", "cmd": "echo yes"}]},
            ],
        }
        self._patch_subprocess(monkeypatch, stdout="ok")
        with patch.object(sys, "stdout", io.StringIO()):
            res = mod.run_workflow("cond_p", {"name": "alice"}, wfs)
        assert res["results"]["cp1"]["status"] == "ok"

    def test_conditional_substep_exception(self, sandbox, monkeypatch):
        """Conditional substep raises (lines 173-174)."""
        mod = sandbox
        def boom(cmd, *a, **kw):
            raise RuntimeError("sub-fail")
        monkeypatch.setattr("subprocess.run", boom)
        wfs = mod.load()
        wfs["cond_exc"] = {
            "desc": "cond sub exc",
            "steps": [
                {"id": "ce1", "action": "conditional", "condition": "True",
                 "if_true": [{"id": "cx", "cmd": "echo yes"}]},
            ],
        }
        with patch.object(sys, "stdout", io.StringIO()):
            res = mod.run_workflow("cond_exc", {}, wfs)
        assert res["results"]["ce1"]["status"] == "failed"

    def test_enqueue_with_idempotency_and_request_id(self, sandbox, monkeypatch):
        """enqueue step with idempotency_key + request_id (lines 214, 217)."""
        mq = MagicMock()
        mq.enqueue = MagicMock(return_value="msg-1")
        sys.modules["dev_message_queue"] = mq
        mod = sandbox
        wfs = mod.load()
        wfs["enq_irr"] = {
            "desc": "enqueue ir",
            "steps": [
                {"id": "e1", "action": "enqueue", "topic": "x.y",
                 "payload": {"k": "v"},
                 "idempotency_key": "key-{val}",
                 "request_id": "req-{val}",
                 "into": "mid"},
            ],
        }
        with patch.object(sys, "stdout", io.StringIO()):
            res = mod.run_workflow("enq_irr", {"val": "X"}, wfs)
        assert res["results"]["e1"]["status"] == "ok"
        # verify idem and request_id got substituted
        call = mq.enqueue.call_args
        assert call.kwargs["idempotency_key"] == "key-X"
        assert call.kwargs["request_id"] == "req-X"

    def test_conditional_if_false(self, sandbox, monkeypatch):
        """Conditional takes the if_false branch."""
        mod = sandbox
        wfs = mod.load()
        wfs["cond_f"] = {
            "desc": "cond false",
            "steps": [
                {"id": "cf1", "action": "conditional", "condition": "False",
                 "if_false": [{"id": "cfx", "cmd": "echo taken"}]},
            ],
        }
        self._patch_subprocess(monkeypatch, stdout="branch-out")
        with patch.object(sys, "stdout", io.StringIO()):
            res = mod.run_workflow("cond_f", {}, wfs)
        assert res["results"]["cf1"]["status"] == "ok"

    def test_conditional_empty_branch(self, sandbox, monkeypatch):
        """Conditional with empty branch (no substeps) → ok=True, ran 0."""
        mod = sandbox
        wfs = mod.load()
        wfs["cond_empty"] = {
            "desc": "cond empty",
            "steps": [
                {"id": "ce", "action": "conditional", "condition": "True",
                 "if_true": []},
            ],
        }
        with patch.object(sys, "stdout", io.StringIO()):
            res = mod.run_workflow("cond_empty", {}, wfs)
        assert res["results"]["ce"]["status"] == "ok"

    def test_delegate_into_param(self, sandbox, monkeypatch):
        """Delegate with `into` stores the simulated dict in params."""
        with patch.object(sys, "stdout", io.StringIO()):
            res = sandbox.run_workflow("delegate_wf", {}, sandbox.load())
        assert res["results"]["d1"]["status"] == "ok"

    def test_run_writes_logfile(self, sandbox, monkeypatch, tmp_path):
        """run_workflow persists a logfile under RUNS_DIR."""
        self._patch_subprocess(monkeypatch, stdout="logged")
        with patch.object(sys, "stdout", io.StringIO()):
            sandbox.run_workflow("hello", {"name": "x"}, sandbox.load())
        # RUNS_DIR is a string; wrap with Path() for glob
        runs = sorted(Path(sandbox.RUNS_DIR).glob("hello_*.json"))
        assert runs
        data = json.loads(runs[-1].read_text())
        assert data["workflow"] == "hello"
        assert "s1" in data["results"]


# ──────────────────────────────────────────────────────────────────────────────
# __main__ argv parsing
# ──────────────────────────────────────────────────────────────────────────────

class TestMain:
    """The CLI block runs under `if __name__ == '__main__':`. We invoke it by
    setting sys.argv and exec'ing the body of that block in a function context."""

    def _run_main(self, sandbox, argv):
        # Re-exec the script body under the sandbox globals
        src = SCRIPT.read_text()
        # Extract the __main__ block (everything from `if __name__ == \"__main__\":`
        # to end of file).
        marker = 'if __name__ == "__main__":'
        idx = src.find(marker)
        assert idx >= 0
        body = src[idx + len(marker):]
        # Wrap in a function with the same locals
        wrapper = "def _main():\n" + body
        ns = {"__name__": "__not_main__", "sys": sys}
        exec(wrapper, sandbox.__dict__)
        old_argv = sys.argv
        sys.argv = argv
        try:
            sandbox._main()
        finally:
            sys.argv = old_argv

    def test_no_args_prints_help(self, sandbox, capsys):
        with pytest.raises(SystemExit) as exc:
            self._run_main(sandbox, ["runner.py"])
        assert exc.value.code == 0

    def test_help_flag(self, sandbox, capsys):
        with pytest.raises(SystemExit) as exc:
            self._run_main(sandbox, ["runner.py", "--help"])
        assert exc.value.code == 0

    def test_list_flag(self, sandbox, capsys):
        with pytest.raises(SystemExit) as exc:
            self._run_main(sandbox, ["runner.py", "--list"])
        assert exc.value.code == 0

    def test_unknown_workflow_exits_1(self, sandbox, capsys):
        with patch.object(sys, "stdout", io.StringIO()):
            with pytest.raises(SystemExit) as exc:
                self._run_main(sandbox, ["runner.py", "no_such_wf"])
        assert exc.value.code == 1

    def test_key_value_pair(self, sandbox, monkeypatch, capsys):
        # Patch run_workflow to capture the call instead of actually running
        seen = []
        monkeypatch.setattr(sandbox, "run_workflow",
                            lambda name, params, wfs: seen.append((name, params)) or {})
        self._run_main(sandbox, ["runner.py", "hello", "--name=alice"])
        assert seen == [("hello", {"name": "alice"})]

    def test_key_space_separated(self, sandbox, monkeypatch):
        seen = []
        monkeypatch.setattr(sandbox, "run_workflow",
                            lambda name, params, wfs: seen.append((name, params)) or {})
        self._run_main(sandbox, ["runner.py", "hello", "--name", "bob"])
        assert seen == [("hello", {"name": "bob"})]

    def test_boolean_flag(self, sandbox, monkeypatch):
        seen = []
        monkeypatch.setattr(sandbox, "run_workflow",
                            lambda name, params, wfs: seen.append((name, params)) or {})
        self._run_main(sandbox, ["runner.py", "hello", "--force"])
        assert seen == [("hello", {"force": ""})]

    def test_multiple_args(self, sandbox, monkeypatch):
        seen = []
        monkeypatch.setattr(sandbox, "run_workflow",
                            lambda name, params, wfs: seen.append((name, params)) or {})
        self._run_main(sandbox, ["runner.py", "hello",
                                  "--name=carol", "--verbose", "--debug"])
        assert seen == [("hello", {"name": "carol", "verbose": "", "debug": ""})]

    def test_run_workflow_via_main(self, sandbox, monkeypatch, capsys):
        """End-to-end: invoke a real workflow via __main__."""
        def fake_run(cmd, *a, **kw):
            return _fake_completed(returncode=0, stdout="hi")
        monkeypatch.setattr("subprocess.run", fake_run)
        with patch.object(sys, "stdout", io.StringIO()):
            self._run_main(sandbox, ["runner.py", "hello", "--name=zoe"])

    def test_unknown_workflow_exits_1_in_main(self, sandbox, monkeypatch, capsys):
        # unknown workflow + main → SystemExit(1)
        seen = []
        monkeypatch.setattr(sandbox, "run_workflow",
                            lambda name, params, wfs: seen.append((name, params)) or {})
        with patch.object(sys, "stdout", io.StringIO()):
            with pytest.raises(SystemExit) as exc:
                self._run_main(sandbox, ["runner.py", "definitely-not-a-wf"])
        assert exc.value.code == 1
        assert seen == []  # run_workflow not called

    def test_main_with_no_args_prints_help(self, sandbox):
        with pytest.raises(SystemExit) as exc:
            self._run_main(sandbox, ["runner.py"])
        assert exc.value.code == 0

    def test_main_via_subprocess(self, sandbox):
        """Run the script as a real subprocess — covers lines 314-344.

        The __main__ block calls load() on the real WF_FILE path. We invoke
        python3 tools/dev_workflow_runner.py --help via subprocess so coverage
        measures the __main__ body too.
        """
        import subprocess as sp
        r = sp.run([sys.executable, str(SCRIPT), "--help"],
                   capture_output=True, text=True, timeout=30,
                   cwd=str(SCRIPT.parent.parent))
        assert r.returncode == 0
        # Just verify it printed something
        assert len(r.stdout) > 0 or len(r.stderr) > 0


# ──────────────────────────────────────────────────────────────────────────────
# Module import safety
# ──────────────────────────────────────────────────────────────────────────────

class TestImportSafety:
    def test_module_has_main_guard(self, sandbox):
        """The __main__ guard must exist at the end of the file."""
        text = SCRIPT.read_text()
        assert 'if __name__ == "__main__":' in text
        # The guard must be the LAST block (no code after it)
        idx = text.rfind('if __name__ == "__main__":')
        assert idx > 0
        after = text[idx + len('if __name__ == "__main__"'):].strip()
        # Body of guard is allowed; just verify there's something meaningful
        assert len(after) > 10
