"""Tests for mas-engineer/tools/dev_intention_parser.py — R110-285.

Coverage target: dev_intention_parser.py 49% → ~85%.

Tests:
- analyse_intention: default type, type detection (voll/intern),
  name extraction, restrictions parsing, workflow_steps
  (with/without error cancel), R110-261a top-level alias
- load_workflows / save_workflows (round-trip)
- validate_sot: detects missing required fields, skips underscored
  agents, handles schema errors
"""
import pytest
import sys
import yaml
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import dev_intention_parser as dip


class TestAnalyseIntention:
    """analyse_intention(text) → dict with type, name, task, etc."""

    def test_default_type_is_sub(self):
        r = dip.analyse_intention("I need a tool that does something")
        assert r["type"] == "sub"

    def test_task_truncated_to_120_chars(self):
        long_text = "a" * 200
        r = dip.analyse_intention(long_text)
        assert len(r["task"]) == 120

    def test_vollagent_detected(self):
        r = dip.analyse_intention("I need a vollagent that runs alone")
        assert r["type"] == "voll"

    def test_autonomous_detected_as_voll(self):
        r = dip.analyse_intention("an autonomous agent for me")
        assert r["type"] == "voll"

    def test_function_extension_detected_as_intern(self):
        r = dip.analyse_intention("a function extension for existing tool")
        assert r["type"] == "intern"

    def test_in_existing_detected_as_intern(self):
        r = dip.analyse_intention("erweiterung in existierend project")
        assert r["type"] == "intern"

    def test_name_extracted_from_pattern(self):
        r = dip.analyse_intention("agent der FooBar macht")
        # "agent der FooBar" → name = "foobar-agent" (lowercased)
        assert r["name"] is not None
        assert "foobar" in r["name"]

    def test_name_with_tool_article(self):
        r = dip.analyse_intention("tool die Helper macht")
        assert "helper" in r["name"]

    def test_name_with_function_article(self):
        r = dip.analyse_intention("function das Counter macht")
        assert "counter" in r["name"]

    def test_name_falls_back_to_words(self):
        # No "agent der NAME" pattern, but there are long words
        r = dip.analyse_intention("something important in the project")
        assert r["name"] is not None
        assert r["name"].endswith("-agent") or r["name"] == "agent"

    def test_name_default_when_no_long_words(self):
        # Only short words like "I am here"
        r = dip.analyse_intention("I am here")
        # Should be "agent" (the default)
        assert r["name"] == "agent"

    def test_requires_confirmation_in_restrictions(self):
        r = dip.analyse_intention("a thing")
        assert r["restrictions"]["requires_confirmation"] is True

    def test_r110_261a_top_level_alias(self):
        """R110-261a: result exposes `requires_confirmation` at top-level
        for backward-compat with naive callers."""
        r = dip.analyse_intention("a thing")
        assert r["requires_confirmation"] is True
        # And it matches the nested value
        assert r["requires_confirmation"] == r["restrictions"]["requires_confirmation"]

    def test_allowed_paths_extracted(self):
        # Pattern is (?:may|should|only|not|exclusively)\s+([\w/.-]+)
        # For 'agent should only foo/bar/' the regex captures 'only' and
        # 'foo/bar/'. The filter then removes any path containing 'not'/'may'.
        # 'only' is a full path of 4 chars — depends on regex engine.
        # The test is mainly that SOME paths are extracted when keywords present.
        r = dip.analyse_intention("agent should mas-engineer/tools/foo.py")
        # mas-engineer/tools/foo.py should be in there
        paths = r["restrictions"]["allowed_paths"]
        assert any("mas-engineer/tools/foo.py" in p for p in paths)

    def test_allowed_paths_skips_negation(self):
        r = dip.analyse_intention("agent should not foo and should bar/")
        # 'not foo' contains 'not' → skipped
        # 'bar/' doesn't contain 'not' → kept
        assert "bar/" in r["restrictions"]["allowed_paths"]
        # 'not foo' should NOT be in the allowed list
        assert not any("not foo" in p for p in r["restrictions"]["allowed_paths"])

    def test_no_paths_when_no_keywords(self):
        r = dip.analyse_intention("just do the thing")
        assert r["restrictions"]["allowed_paths"] == []

    def test_workflow_step_with_cancel_keyword(self):
        r = dip.analyse_intention("please cancel the operation on error")
        assert r["workflow_steps"][0]["on_error"] == "abort"
        assert r["workflow_steps"][0]["action"] == "shell"

    def test_workflow_step_with_stopp_keyword(self):
        r = dip.analyse_intention("stopp wenn was schief geht")
        assert r["workflow_steps"][0]["on_error"] == "abort"

    def test_workflow_step_default_continue(self):
        r = dip.analyse_intention("a normal agent please")
        assert r["workflow_steps"][0]["on_error"] == "continue"

    def test_returns_dict_with_required_keys(self):
        r = dip.analyse_intention("test")
        for key in ("type", "name", "task", "restrictions", "workflow_steps"):
            assert key in r


class TestLoadSaveWorkflows:
    """load_workflows / save_workflows round-trip."""

    def test_load_returns_parsed_yaml(self, tmp_path, monkeypatch):
        wf_file = tmp_path / "workflows.yaml"
        wf_file.write_text("agents:\n  foo: {type: sub, task: 'x'}\n")
        monkeypatch.setattr(dip, "WF_FILE", str(wf_file))
        d = dip.load_workflows()
        assert "foo" in d["agents"]

    def test_save_writes_file(self, tmp_path, monkeypatch):
        wf_file = tmp_path / "workflows.yaml"
        monkeypatch.setattr(dip, "WF_FILE", str(wf_file))
        dip.save_workflows({"agents": {"x": {"type": "sub", "task": "y"}}})
        assert wf_file.exists()
        d = yaml.safe_load(wf_file.read_text())
        assert "x" in d["agents"]

    def test_round_trip(self, tmp_path, monkeypatch):
        wf_file = tmp_path / "workflows.yaml"
        wf_file.write_text("agents:\n  a: {type: sub, task: 'first'}\n")
        monkeypatch.setattr(dip, "WF_FILE", str(wf_file))
        d = dip.load_workflows()
        d["agents"]["b"] = {"type": "voll", "task": "second"}
        dip.save_workflows(d)
        d2 = dip.load_workflows()
        assert "a" in d2["agents"]
        assert "b" in d2["agents"]


class TestValidateSot:
    """validate_sot() — checks SOT YAML against schema for required fields."""

    def _setup(self, tmp_path, schema_yaml, workflows_yaml):
        schema = tmp_path / "sot_schema.yaml"
        schema.write_text(schema_yaml)
        wf = tmp_path / "workflows.yaml"
        wf.write_text(workflows_yaml)
        return schema, wf

    def test_no_errors_when_all_fields_present(self, tmp_path, monkeypatch):
        schema, wf = self._setup(
            tmp_path,
            "agent_schema:\n  required: [name, type, task]\n",
            "agents:\n  a:\n    name: A\n    type: sub\n    task: do\n",
        )
        monkeypatch.setattr(dip, "WF_FILE", str(wf))
        monkeypatch.setattr(dip, "SCHEMA_FILE", str(schema))
        errs = dip.validate_sot()
        assert errs == []

    def test_detects_missing_required_field(self, tmp_path, monkeypatch):
        schema, wf = self._setup(
            tmp_path,
            "agent_schema:\n  required: [name, type, task]\n",
            "agents:\n  a:\n    name: A\n    type: sub\n",
        )
        monkeypatch.setattr(dip, "WF_FILE", str(wf))
        monkeypatch.setattr(dip, "SCHEMA_FILE", str(schema))
        errs = dip.validate_sot()
        assert len(errs) == 1
        assert "a" in errs[0]
        assert "task" in errs[0]

    def test_detects_multiple_missing_fields(self, tmp_path, monkeypatch):
        schema, wf = self._setup(
            tmp_path,
            "agent_schema:\n  required: [name, type, task]\n",
            "agents:\n  a: {}\n",
        )
        monkeypatch.setattr(dip, "WF_FILE", str(wf))
        monkeypatch.setattr(dip, "SCHEMA_FILE", str(schema))
        errs = dip.validate_sot()
        assert len(errs) == 3

    def test_skips_underscored_agents(self, tmp_path, monkeypatch):
        schema, wf = self._setup(
            tmp_path,
            "agent_schema:\n  required: [name, type, task]\n",
            "agents:\n  _helper: {}\n  normal: {name: N, type: sub, task: t}\n",
        )
        monkeypatch.setattr(dip, "WF_FILE", str(wf))
        monkeypatch.setattr(dip, "SCHEMA_FILE", str(schema))
        errs = dip.validate_sot()
        # _helper is skipped → no errors
        assert errs == []

    def test_returns_error_on_missing_schema(self, tmp_path, monkeypatch):
        # SCHEMA_FILE doesn't exist
        monkeypatch.setattr(dip, "WF_FILE", str(tmp_path / "wf.yaml"))
        (tmp_path / "wf.yaml").write_text("agents: {}\n")
        monkeypatch.setattr(dip, "SCHEMA_FILE", str(tmp_path / "missing.yaml"))
        errs = dip.validate_sot()
        # Should not crash, return list with schema-error
        assert len(errs) == 1
        assert "Schema-Error" in errs[0]

    def test_handles_empty_agents(self, tmp_path, monkeypatch):
        schema, wf = self._setup(
            tmp_path,
            "agent_schema:\n  required: [name, type, task]\n",
            "agents: {}\n",
        )
        monkeypatch.setattr(dip, "WF_FILE", str(wf))
        monkeypatch.setattr(dip, "SCHEMA_FILE", str(schema))
        errs = dip.validate_sot()
        assert errs == []
