"""Targeted coverage push for tools/dev_yaml_generator_generic.py — R110-504.

Target: dev_yaml_generator_generic.py (3054 bytes, ~40 stmts, 0% covered
→ goal ~50%).

Strategy: import the module inline (sys.path-insert tools/), then mock
the two imported functions from dev_yaml_generator_core so we can test
the CLI dispatch + load_schema + main() flow without needing real
agent_schema.yaml fixtures.

Functions covered:
- load_schema (missing-file → sys.exit 1, success → returns parsed dict)
- main() CLI dispatch (no-args → sys.exit 1, no-agents → sys.exit 0 with
  warning, --validate-only, --diff, error per agent, all-ok path, default
  write path)

NOTE: `main()` does sys.exit internally for early errors (no-args,
no-agents, schema-missing). For the end-of-flow it `return`s an int
but does NOT call sys.exit on it — the `if __name__ == "__main__"`
block at the bottom calls main() without capturing the return. So
we test the early-exit sys.exit paths with pytest.raises(SystemExit)
and the end-of-flow return value by inspecting it directly.
"""
import os
import sys
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"


@pytest.fixture
def lib(tmp_path, monkeypatch):
    """Import dev_yaml_generator_generic inline."""
    if "dev_yaml_generator_generic" in sys.modules:
        del sys.modules["dev_yaml_generator_generic"]
    if "dev_yaml_generator_core" in sys.modules:
        del sys.modules["dev_yaml_generator_core"]
    sys.path.insert(0, str(TOOLS_DIR))
    import dev_yaml_generator_generic as lib  # noqa: E402
    return lib


# ─────────────────────────────────────────────────────────
# load_schema
# ─────────────────────────────────────────────────────────

def test_load_schema_file_missing(lib, tmp_path, capsys):
    """Schema file not found → print error + SystemExit(1)."""
    with pytest.raises(SystemExit) as exc_info:
        lib.load_schema(str(tmp_path))
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Schema not found" in captured.out


def test_load_schema_success(lib, tmp_path):
    """Schema file found → returns parsed YAML dict."""
    # Create .mase/templates/agent_schema.yaml
    schema_dir = tmp_path / ".mase" / "templates"
    schema_dir.mkdir(parents=True)
    schema_file = schema_dir / "agent_schema.yaml"
    schema_file.write_text("agents:\n  foo:\n    title: Foo\nstandard_settings:\n  timeout: 60\n")
    result = lib.load_schema(str(tmp_path))
    assert "agents" in result
    assert "foo" in result["agents"]


# ─────────────────────────────────────────────────────────
# main() CLI dispatch
# ─────────────────────────────────────────────────────────

def test_main_no_args(lib, capsys):
    """No --target → print error + SystemExit(1)."""
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(sys, "argv", ["dev_yaml_generator_generic"])
        with pytest.raises(SystemExit) as exc_info:
            lib.main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "--target" in captured.out
    finally:
        monkeypatch.undo()


def test_main_no_agents_in_schema(lib, tmp_path, capsys):
    """Schema with empty agents → SystemExit(0) with warning, no files."""
    schema_dir = tmp_path / ".mase" / "templates"
    schema_dir.mkdir(parents=True)
    (schema_dir / "agent_schema.yaml").write_text("agents: {}\n")
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(sys, "argv", ["d", "--target", str(tmp_path)])
        with pytest.raises(SystemExit) as exc_info:
            lib.main()
        assert exc_info.value.code == 0
    finally:
        monkeypatch.undo()
    # Per impl: no-agents exit(0) happens BEFORE sub_path creation
    # so sub/ does NOT exist
    assert not (tmp_path / "sub").exists()


def test_main_writes_all_agents(lib, tmp_path, capsys):
    """Default mode → write sub_mas-*.yaml for each agent."""
    schema_dir = tmp_path / ".mase" / "templates"
    schema_dir.mkdir(parents=True)
    schema_yaml = (
        "agents:\n"
        "  alpha:\n    title: Alpha\n"
        "  beta:\n    title: Beta\n"
        "standard_settings:\n  timeout: 60\n"
    )
    (schema_dir / "agent_schema.yaml").write_text(schema_yaml)
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(sys, "argv", ["d", "--target", str(tmp_path)])
        with mock.patch("dev_yaml_generator_generic.generate_agent_yaml",
                         return_value="version: 1\ntitle: GENERATED\n") as m_gen, \
             mock.patch("dev_yaml_generator_generic.validate_generated",
                         return_value=(True, [])):
            rc = lib.main()
    finally:
        monkeypatch.undo()
    # Per impl: rc = 0 (no errors)
    assert rc == 0
    # Both files written
    sub_dir = tmp_path / "sub"
    assert (sub_dir / "sub_mas-alpha.yaml").exists()
    assert (sub_dir / "sub_mas-beta.yaml").exists()
    # generate_agent_yaml called twice, validate_generated NOT called (not --diff)
    assert m_gen.call_count == 2


def test_main_validate_only_mode(lib, tmp_path):
    """--validate-only → no files written (impl quirk: no validate call).

    Per impl: `if show_diff or not validate_only:` only calls
    validate_generated when `show_diff=True` OR `validate_only=False`.
    So --validate-only does NOT trigger validate_generated — it just
    doesn't write either. This is an impl quirk we faithfully cover.
    """
    schema_dir = tmp_path / ".mase" / "templates"
    schema_dir.mkdir(parents=True)
    (schema_dir / "agent_schema.yaml").write_text("agents:\n  alpha:\n    title: Alpha\n")
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(sys, "argv", ["d", "--target", str(tmp_path), "--validate-only"])
        with mock.patch("dev_yaml_generator_generic.generate_agent_yaml",
                         return_value="version: 1\n"), \
             mock.patch("dev_yaml_generator_generic.validate_generated",
                         return_value=(True, [])) as m_val:
            rc = lib.main()
        assert rc == 0
    finally:
        monkeypatch.undo()
    # In validate-only: validate_generated NOT called (impl quirk), no file written
    assert m_val.call_count == 0
    assert not (tmp_path / "sub" / "sub_mas-alpha.yaml").exists()


def test_main_diff_mode(lib, tmp_path, capsys):
    """--diff → validate_generated called, issues printed."""
    schema_dir = tmp_path / ".mase" / "templates"
    schema_dir.mkdir(parents=True)
    (schema_dir / "agent_schema.yaml").write_text("agents:\n  alpha:\n    title: Alpha\n")
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(sys, "argv", ["d", "--target", str(tmp_path), "--diff"])
        with mock.patch("dev_yaml_generator_generic.generate_agent_yaml",
                         return_value="version: 1\n"), \
             mock.patch("dev_yaml_generator_generic.validate_generated",
                         return_value=(False, ["missing key X", "wrong value Y"])):
            rc = lib.main()
    finally:
        monkeypatch.undo()
    # In diff mode: no file written
    assert not (tmp_path / "sub" / "sub_mas-alpha.yaml").exists()
    captured = capsys.readouterr()
    assert "Deviations" in captured.out or "⚠️" in captured.out


def test_main_generator_error_caught(lib, tmp_path, capsys):
    """If generate_agent_yaml raises → caught, error counted, rc=1."""
    schema_dir = tmp_path / ".mase" / "templates"
    schema_dir.mkdir(parents=True)
    (schema_dir / "agent_schema.yaml").write_text("agents:\n  alpha:\n    title: Alpha\n")
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(sys, "argv", ["d", "--target", str(tmp_path)])
        with mock.patch("dev_yaml_generator_generic.generate_agent_yaml",
                         side_effect=ValueError("bad schema")):
            rc = lib.main()
        assert rc == 1
    finally:
        monkeypatch.undo()
    captured = capsys.readouterr()
    assert "Error" in captured.out or "❌" in captured.out


def test_main_writes_in_default_mode(lib, tmp_path, capsys):
    """Default mode + valid result → write, ok counter, rc=0."""
    schema_dir = tmp_path / ".mase" / "templates"
    schema_dir.mkdir(parents=True)
    (schema_dir / "agent_schema.yaml").write_text("agents:\n  alpha:\n    title: Alpha\n")
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(sys, "argv", ["d", "--target", str(tmp_path)])
        with mock.patch("dev_yaml_generator_generic.generate_agent_yaml",
                         return_value="version: 1\n"):
            rc = lib.main()
    finally:
        monkeypatch.undo()
    # In default mode (not validate-only, not show_diff): file IS written
    assert (tmp_path / "sub" / "sub_mas-alpha.yaml").exists()
    captured = capsys.readouterr()
    assert "Generates" in captured.out


def test_main_diff_mode_deviation_printed(lib, tmp_path, capsys):
    """--diff + invalid → issue lines printed."""
    schema_dir = tmp_path / ".mase" / "templates"
    schema_dir.mkdir(parents=True)
    (schema_dir / "agent_schema.yaml").write_text("agents:\n  alpha:\n    title: Alpha\n")
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(sys, "argv", ["d", "--target", str(tmp_path), "--diff"])
        with mock.patch("dev_yaml_generator_generic.generate_agent_yaml",
                         return_value="v: 1\n"), \
             mock.patch("dev_yaml_generator_generic.validate_generated",
                         return_value=(False, ["missing key X"])):
            lib.main()
    finally:
        monkeypatch.undo()
    captured = capsys.readouterr()
    assert "missing key X" in captured.out
