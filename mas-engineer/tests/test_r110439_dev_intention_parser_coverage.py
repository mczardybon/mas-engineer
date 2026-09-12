"""R110-439 — coverage-push r8: tools/dev_intention_parser.py 0% → 100%.

Intention parser CLI (94 lines). Parses free-form user prompts
into structured agent specs, validates SOT, prints schema.

Targets:
- load_workflows: returns parsed dict
- save_workflows: writes dict to file with proper YAML options
- analyse_intention: text → result dict
  * default type "sub", default task=first-120-chars, default
    restrictions (allowed_paths=[], forbidden_paths=[],
    requires_confirmation=True), default workflow_steps=[]
  * "autonomous"/"vollagent"/"eigener prompt" → type "voll"
  * "function"/"erweiterung"/"in existierend" → type "intern"
  * name extraction: "agent der NAME" / "tool der NAME" / "function
    die NAME" → NAME-agent
  * name fallback: words > 4 chars (filtered), use words[1] if
    multiple, else words[0], else "agent"
  * path patterns: (may|should|only|not|exclusively) X → allowed
    paths (filtered to exclude 'not'/'may')
  * "cancel"/"stopp"/"error cancel" → on_error="abort"
  * else → on_error="continue"
  * top-level requires_confirmation alias (R110-261a)
- validate_sot: schema missing → returns ['Schema-Error: ...'],
  valid SOT → [], agent missing required field → error
- __main__: --validate (✅ or errors), --schema (prints YAML),
  positional arg (JSON analyse_intention), no args (docstring)
"""

import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.dev_intention_parser as ip  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# load_workflows / save_workflows
# ─────────────────────────────────────────────────────────────────────
class TestLoadSaveWorkflows:
    def test_load_workflows(self, tmp_path, monkeypatch):
        wf_file = tmp_path / "wf.yaml"
        wf_file.write_text(yaml.safe_dump({"agents": {"a": {"x": 1}}}))
        monkeypatch.setattr(ip, "WF_FILE", str(wf_file))
        data = ip.load_workflows()
        assert data["agents"]["a"]["x"] == 1

    def test_save_workflows(self, tmp_path, monkeypatch):
        wf_file = tmp_path / "wf.yaml"
        monkeypatch.setattr(ip, "WF_FILE", str(wf_file))
        ip.save_workflows({"agents": {"b": {"y": 2}}})
        # Reload and verify
        data = ip.load_workflows()
        assert data["agents"]["b"]["y"] == 2


# ─────────────────────────────────────────────────────────────────────
# analyse_intention
# ─────────────────────────────────────────────────────────────────────
class TestAnalyseIntention:
    def test_defaults(self):
        r = ip.analyse_intention("Hello world")
        assert r["type"] == "sub"
        assert r["task"] == "Hello world"
        assert r["restrictions"]["allowed_paths"] == []
        assert r["restrictions"]["forbidden_paths"] == []
        assert r["restrictions"]["requires_confirmation"] is True
        # A default workflow_steps gets appended in the function
        assert len(r["workflow_steps"]) == 1
        assert r["workflow_steps"][0]["on_error"] == "continue"

    def test_task_truncated_to_120(self):
        text = "x" * 200
        r = ip.analyse_intention(text)
        assert len(r["task"]) == 120

    def test_top_level_alias(self):
        r = ip.analyse_intention("Hello")
        assert r["requires_confirmation"] is True
        assert r["requires_confirmation"] == r["restrictions"][
            "requires_confirmation"]

    def test_type_voll_autonomous(self):
        r = ip.analyse_intention("Ich brauche einen autonomous agent")
        assert r["type"] == "voll"

    def test_type_voll_vollagent(self):
        r = ip.analyse_intention("Vollagent der alles kann")
        assert r["type"] == "voll"

    def test_type_voll_eigener_prompt(self):
        r = ip.analyse_intention("Mit eigener prompt")
        assert r["type"] == "voll"

    def test_type_intern_function(self):
        r = ip.analyse_intention("Eine function für X")
        assert r["type"] == "intern"

    def test_type_intern_erweiterung(self):
        r = ip.analyse_intention("Erweiterung für mein System")
        assert r["type"] == "intern"

    def test_type_intern_in_existierend(self):
        r = ip.analyse_intention("in existierend System einbauen")
        assert r["type"] == "intern"

    def test_name_agent_der(self):
        r = ip.analyse_intention("agent der foo macht")
        assert r["name"] == "foo-agent"

    def test_name_tool_die(self):
        r = ip.analyse_intention("tool die bar erstellt")
        assert r["name"] == "bar-agent"

    def test_name_function_das(self):
        r = ip.analyse_intention("function das baz macht")
        assert r["name"] == "baz-agent"

    def test_name_fallback_word(self):
        # No pattern → falls back to words > 4 chars
        r = ip.analyse_intention("something amazing")
        assert r["name"].endswith("-agent")

    def test_name_fallback_agent(self):
        # Only stopwords → fallback "agent"
        r = ip.analyse_intention("a the will")
        assert r["name"] == "agent"

    def test_workflow_abort_on_cancel(self):
        r = ip.analyse_intention("cancel bitte")
        assert r["workflow_steps"][0]["on_error"] == "abort"

    def test_workflow_abort_on_stopp(self):
        r = ip.analyse_intention("stopp jetzt")
        assert r["workflow_steps"][0]["on_error"] == "abort"

    def test_workflow_abort_on_error_cancel(self):
        r = ip.analyse_intention("error cancel on failure")
        assert r["workflow_steps"][0]["on_error"] == "abort"

    def test_workflow_continue_default(self):
        r = ip.analyse_intention("hello")
        assert r["workflow_steps"][0]["on_error"] == "continue"

    def test_workflow_step_structure(self):
        r = ip.analyse_intention("hello")
        step = r["workflow_steps"][0]
        assert step["id"] == "main"
        assert step["action"] == "shell"
        assert step["cmd"] == ""

    def test_allowed_paths_extraction(self):
        # 'should' triggers and captures the following path. Note
        # that the regex is non-overlapping, so the FIRST trigger word
        # consumes the path that follows.
        r = ip.analyse_intention("should /etc/foo.txt path")
        assert "/etc/foo.txt" in r["restrictions"]["allowed_paths"]

    def test_allowed_paths_excludes_not(self):
        r = ip.analyse_intention("not /etc/foo.txt")
        # The path "/etc/foo.txt" doesn't contain 'not' as substring,
        # so it IS kept in allowed_paths.
        assert "/etc/foo.txt" in r["restrictions"]["allowed_paths"]

    def test_path_filter_keeps_clean_paths(self):
        # Two trigger words, both follow non-overlapping paths.
        text = "should /etc/clean.txt only /var/x.txt"
        r = ip.analyse_intention(text)
        assert "/etc/clean.txt" in r["restrictions"]["allowed_paths"]
        # /var/x.txt: 'only' is the trigger (consumed) so it captures
        # /var/x.txt. Filter: 'not'/'may' not in '/var/x.txt' → kept
        assert "/var/x.txt" in r["restrictions"]["allowed_paths"]

    def test_path_filter_excludes_may_in_path(self):
        # Triggered by 'only', path itself contains 'may' as substring
        text = "only /home/maydata/file.txt"
        r = ip.analyse_intention(text)
        # '/home/maydata/file.txt' contains 'may' → filtered out
        assert "/home/maydata/file.txt" not in r["restrictions"][
            "allowed_paths"]


# ─────────────────────────────────────────────────────────────────────
# validate_sot
# ─────────────────────────────────────────────────────────────────────
class TestValidateSot:
    def test_schema_missing_returns_error(self, tmp_path, monkeypatch):
        # No schema file → ['Schema-Error: ...']
        wf = tmp_path / "wf.yaml"
        wf.write_text(yaml.safe_dump({"agents": {}}))
        monkeypatch.setattr(ip, "WF_FILE", str(wf))
        monkeypatch.setattr(ip, "SCHEMA_FILE", str(tmp_path / "nope.yaml"))
        errs = ip.validate_sot()
        assert len(errs) == 1
        assert "Schema-Error" in errs[0]

    def test_valid_sot_no_errors(self, tmp_path, monkeypatch):
        wf = tmp_path / "wf.yaml"
        schema = tmp_path / "schema.yaml"
        wf.write_text(yaml.safe_dump({
            "agents": {"a": {"name": "a", "type": "sub", "task": "t"}}}))
        schema.write_text(yaml.safe_dump({
            "agent_schema": {"required": ["name", "type", "task"]}}))
        monkeypatch.setattr(ip, "WF_FILE", str(wf))
        monkeypatch.setattr(ip, "SCHEMA_FILE", str(schema))
        errs = ip.validate_sot()
        assert errs == []

    def test_missing_required_field(self, tmp_path, monkeypatch):
        wf = tmp_path / "wf.yaml"
        schema = tmp_path / "schema.yaml"
        # 'task' missing
        wf.write_text(yaml.safe_dump({
            "agents": {"foo": {"name": "foo", "type": "sub"}}}))
        schema.write_text(yaml.safe_dump({
            "agent_schema": {"required": ["name", "type", "task"]}}))
        monkeypatch.setattr(ip, "WF_FILE", str(wf))
        monkeypatch.setattr(ip, "SCHEMA_FILE", str(schema))
        errs = ip.validate_sot()
        assert any("task" in e for e in errs)
        assert any("foo" in e for e in errs)

    def test_skips_underscore_prefix(self, tmp_path, monkeypatch):
        wf = tmp_path / "wf.yaml"
        schema = tmp_path / "schema.yaml"
        wf.write_text(yaml.safe_dump({
            "agents": {"_hidden": {"name": "h"},
                       "visible": {"name": "v", "type": "sub",
                                   "task": "t"}}}))
        schema.write_text(yaml.safe_dump({
            "agent_schema": {"required": ["name", "type", "task"]}}))
        monkeypatch.setattr(ip, "WF_FILE", str(wf))
        monkeypatch.setattr(ip, "SCHEMA_FILE", str(schema))
        errs = ip.validate_sot()
        # _hidden missing fields is NOT reported
        assert not any("_hidden" in e for e in errs)
        assert errs == []


# ─────────────────────────────────────────────────────────────────────
# __main__ exec
# ─────────────────────────────────────────────────────────────────────
def _run_main(argv, capsys, module_globals=None):
    """Call module __main__ block with custom sys.argv.

    The dev_intention_parser.py source defines module-level
    constants (WF_FILE, SCHEMA_FILE) at import time. When we exec()
    the source, those assignments re-run and clobber our namespace
    overrides. To work around this, we rewrite the source via re.sub
    to use literal paths from `module_globals` if provided.
    """
    import re as _re
    old_argv = sys.argv
    sys.argv = ["dev_intention_parser.py"] + argv
    code = 0
    src = Path(__file__).resolve().parents[1].joinpath(
        "tools/dev_intention_parser.py").read_text()
    if module_globals:
        # Replace `WF_FILE = os.path.join(BASE, ".mase", "workflows.yaml")`
        # with `WF_FILE = "<our_path>"` etc.
        if 'WF_FILE' in module_globals:
            wf_path = repr(module_globals['WF_FILE']).replace("'", '"')
            src = src.replace(
                'WF_FILE = os.path.join(BASE, ".mase", "workflows.yaml")',
                f'WF_FILE = "{wf_path[1:-1]}"')
        if 'SCHEMA_FILE' in module_globals:
            schema_path = repr(module_globals['SCHEMA_FILE']).replace("'", '"')
            src = src.replace(
                'SCHEMA_FILE = os.path.join(BASE, ".mase", "sot_schema.yaml")',
                f'SCHEMA_FILE = "{schema_path[1:-1]}"')
        src = src.replace(
            'TEMPLATE = os.path.join(BASE, "recipe", "template", "agent_template.yaml")',
            'TEMPLATE = "/dev/null"')
        src = src.replace(
            'SUB_DIR = os.path.join(BASE, "recipe", "sub")',
            'SUB_DIR = "/dev/null"')
    ns = {"__name__": "__main__",
          "__file__": "dev_intention_parser.py"}
    try:
        try:
            exec(compile(src, "dev_intention_parser.py", "exec"), ns)
        except SystemExit as e:
            code = e.code if e.code is not None else 0
    finally:
        sys.argv = old_argv
    return capsys.readouterr().out, code


class TestMainExec:
    def test_no_args_prints_docstring(self, capsys):
        out, code = _run_main([], capsys=capsys)
        assert "Usage" in out

    def test_validate_valid(self, tmp_path, capsys):
        wf = tmp_path / "wf.yaml"
        schema = tmp_path / "schema.yaml"
        wf.write_text(yaml.safe_dump({
            "agents": {"a": {"name": "a", "type": "sub", "task": "t"}}}))
        schema.write_text(yaml.safe_dump({
            "agent_schema": {"required": ["name", "type", "task"]}}))
        out, code = _run_main(["--validate"], capsys=capsys,
                              module_globals={"WF_FILE": str(wf),
                                              "SCHEMA_FILE": str(schema)})
        assert "SOT valid" in out

    def test_validate_invalid(self, tmp_path, capsys):
        wf = tmp_path / "wf.yaml"
        schema = tmp_path / "schema.yaml"
        wf.write_text(yaml.safe_dump({
            "agents": {"x": {"name": "x"}}}))  # missing type, task
        schema.write_text(yaml.safe_dump({
            "agent_schema": {"required": ["name", "type", "task"]}}))
        out, code = _run_main(["--validate"], capsys=capsys,
                              module_globals={"WF_FILE": str(wf),
                                              "SCHEMA_FILE": str(schema)})
        assert "❌" in out

    def test_schema_prints_yaml(self, tmp_path, capsys):
        schema = tmp_path / "schema.yaml"
        schema.write_text(yaml.safe_dump({"key": "value"}))
        out, code = _run_main(["--schema"], capsys=capsys,
                              module_globals={"SCHEMA_FILE": str(schema)})
        assert "key: value" in out

    def test_positional_analyse(self, capsys):
        out, code = _run_main(["agent der foo macht"], capsys=capsys)
        # JSON output
        data = json.loads(out)
        assert "restrictions" in data
        assert "requires_confirmation" in data

    def test_unknown_flag_prints_docstring(self, capsys):
        out, code = _run_main(["--unknown"], capsys=capsys)
        assert "Usage" in out
