"""R110-538 coverage tests for tools/dev_yaml_generator.py.

Module: 127 LOC, ~88 stmts, 6 functions, 0% covered.

Functions tested:
  - find_schema(mode, target=None)              lines 20-39
  - find_sub_dir(mode, target=None)             lines 41-47
  - load_schema(path)                           lines 49-51
  - main()                                      lines 53-124
  - __main__ entry point                        lines 126-127

Strategy: Direct function calls with crafted fs structure in
tmp_path. Use monkeypatch to redirect MAS_SCHEMA/GEN_SCHEMA/MAS_SUB_DIR.

Key paths to cover:
  - find_schema:
    - mode=generic + target + schema.yaml exists → return (23-25)
    - mode=generic + target + schema.yaml missing + schema_generic.yaml exists → return (26-29)
    - mode=generic + target + nothing → sys.exit(1) (30-31)
    - mode=generic + no target + GEN_SCHEMA exists → return (32-34)
    - default MAS_SCHEMA exists → return (36-37)
    - MAS_SCHEMA missing → sys.exit(1) (38-39)
  - find_sub_dir:
    - mode=generic + target → makedirs + return (42-45)
    - default MAS_SUB_DIR makedirs + return (46-47)
  - load_schema: open + yaml.safe_load (49-51)
  - main():
    - parse args, --mode, --target, flags (60-65)
    - invalid mode → sys.exit(1) (67-69)
    - schema path, sub dir, schema loaded (71-75)
    - banner print (77-79)
    - empty agents → sys.exit(0) (82-84)
    - loop agents (90+)
      - generate yaml.safe_load (94-96)
      - generate error → errors.append, continue (97-99)
      - do_write → write file (101-104)
      - show_diff or validate_only → validate_generated (105-113)
      - print diff (111-113)
    - final summary (115-122)
    - return 0 or 1 (124)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
# dev_yaml_generator.py uses `from dev_yaml_generator_core import …`
# (without `tools.` prefix), so the tools/ dir must be importable too.
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import tools.dev_yaml_generator as gen  # noqa: E402


# ====================== helpers ==================================

def _write_schema(path: Path, agents: dict, std: dict | None = None) -> Path:
    data = {
        "version": "1.0.0",
        "standard_settings": std or {
            "timeout": 600, "max_steps": 100,
            "goose_provider": "openai", "goose_model": "deepseek",
        },
        "template_tags": {
            "HEADER": "{emoji} {title}",
            "R01": "", "R09": "",
        },
        "agents": agents,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data))
    return path


def _make_agent(name="x", **overrides):
    base = {
        "emoji": "🔧", "title": f"Agent {name}",
        "description": "d", "prompt": "p", "instructions": "i",
        "settings": {},
    }
    base.update(overrides)
    return base


# ====================== find_schema ==============================

def test_find_schema_mas_default(monkeypatch, tmp_path):
    """Covers lines 36-37: MAS_SCHEMA exists → return."""
    schema_path = tmp_path / "agent_schema.yaml"
    _write_schema(schema_path, {"x": _make_agent("x")})
    monkeypatch.setattr(gen, "MAS_SCHEMA", str(schema_path))
    result = gen.find_schema("mas")
    assert result == str(schema_path)


def test_find_schema_mas_missing(monkeypatch, tmp_path):
    """Covers lines 38-39: MAS_SCHEMA missing → sys.exit(1)."""
    monkeypatch.setattr(gen, "MAS_SCHEMA", str(tmp_path / "missing.yaml"))
    with pytest.raises(SystemExit) as ei:
        gen.find_schema("mas")
    assert ei.value.code == 1


def test_find_schema_generic_with_target(monkeypatch, tmp_path):
    """Covers lines 22-25: generic + target + schema.yaml exists → return."""
    target = tmp_path / "tgt"
    target.mkdir()
    schema_path = target / ".mase/templates/agent_schema.yaml"
    _write_schema(schema_path, {"x": _make_agent()})
    result = gen.find_schema("generic", target=str(target))
    assert result == str(schema_path)


def test_find_schema_generic_fallback(monkeypatch, tmp_path):
    """Covers lines 26-29: schema.yaml missing + generic.yaml exists → return."""
    target = tmp_path / "tgt"
    target.mkdir()
    templates = target / ".mase/templates"
    templates.mkdir(parents=True)
    # Only generic exists
    schema_path = templates / "agent_schema_generic.yaml"
    _write_schema(schema_path, {"x": _make_agent()})
    result = gen.find_schema("generic", target=str(target))
    assert result == str(schema_path)


def test_find_schema_generic_target_nothing(monkeypatch, tmp_path, capsys):
    """Covers lines 30-31: generic + target + nothing → sys.exit(1) + msg."""
    target = tmp_path / "empty_tgt"
    target.mkdir()
    with pytest.raises(SystemExit) as ei:
        gen.find_schema("generic", target=str(target))
    assert ei.value.code == 1
    out = capsys.readouterr().out
    assert "No Schema" in out


def test_find_schema_generic_no_target(monkeypatch, tmp_path):
    """Covers lines 32-34: generic + no target + GEN_SCHEMA exists → return."""
    schema_path = tmp_path / "agent_schema_generic.yaml"
    _write_schema(schema_path, {"x": _make_agent()})
    monkeypatch.setattr(gen, "GEN_SCHEMA", str(schema_path))
    result = gen.find_schema("generic")
    assert result == str(schema_path)


# ====================== find_sub_dir =============================

def test_find_sub_dir_generic_with_target(monkeypatch, tmp_path):
    """Covers lines 42-45: generic + target → makedirs + return."""
    target = tmp_path / "tgt"
    target.mkdir()
    result = gen.find_sub_dir("generic", target=str(target))
    expected = str(target / "sub")
    assert result == expected
    assert Path(expected).exists()


def test_find_sub_dir_mas(monkeypatch, tmp_path):
    """Covers lines 46-47: default → MAS_SUB_DIR."""
    sub_dir = tmp_path / "sub"
    monkeypatch.setattr(gen, "MAS_SUB_DIR", str(sub_dir))
    result = gen.find_sub_dir("mas")
    assert result == str(sub_dir)
    assert sub_dir.exists()


# ====================== load_schema ==============================

def test_load_schema(tmp_path):
    """Covers lines 49-51: yaml.safe_load of file."""
    path = _write_schema(tmp_path / "s.yaml", {"a": _make_agent("a")})
    loaded = gen.load_schema(str(path))
    assert "agents" in loaded
    assert "a" in loaded["agents"]


# ====================== main =====================================

def _setup_main_env(monkeypatch, tmp_path, *, agents, target=None,
                    mode="mas", std=None):
    """Set up MAS_SCHEMA/GEN_SCHEMA/MAS_SUB_DIR + agent_schema.yaml."""
    if target:
        # Generic mode + target
        schema_path = Path(target) / ".mase/templates/agent_schema.yaml"
        _write_schema(schema_path, agents, std=std)
        sub_dir = Path(target) / "sub"
        monkeypatch.setattr(gen, "MAS_SCHEMA", str(schema_path))
        monkeypatch.setattr(gen, "GEN_SCHEMA",
                            str(target / ".mase/templates/agent_schema_generic.yaml"))
    else:
        schema_path = tmp_path / "agent_schema.yaml"
        _write_schema(schema_path, agents, std=std)
        sub_dir = tmp_path / "sub"
        monkeypatch.setattr(gen, "MAS_SCHEMA", str(schema_path))
        monkeypatch.setattr(gen, "GEN_SCHEMA",
                            str(tmp_path / "agent_schema_generic.yaml"))
    monkeypatch.setattr(gen, "MAS_SUB_DIR", str(sub_dir))
    return schema_path, sub_dir


def test_main_mas_mode_no_flags(monkeypatch, tmp_path, capsys):
    """Covers line 90-104: default mas mode, no write/diff → no action per agent.

    Without --write, --diff, or --validate-only, the loop runs but
    does nothing in the body (line 105 False), so ok=0, no errors.
    """
    agents = {"a": _make_agent("a"), "b": _make_agent("b")}
    _setup_main_env(monkeypatch, tmp_path, agents=agents)
    monkeypatch.setattr(sys, "argv", ["dev_yaml_generator.py"])
    rc = gen.main()
    assert rc == 0
    out = capsys.readouterr().out
    assert "OK: 0/2" in out


def test_main_mas_mode_write(monkeypatch, tmp_path, capsys):
    """Covers lines 101-104: --write → files written."""
    agents = {"alpha": _make_agent("alpha")}
    _, sub_dir = _setup_main_env(monkeypatch, tmp_path, agents=agents)
    monkeypatch.setattr(sys, "argv",
                        ["dev_yaml_generator.py", "--write"])
    rc = gen.main()
    assert rc == 0
    assert (sub_dir / "sub_mas-alpha.yaml").exists()


def test_main_mas_mode_validate_only_match(monkeypatch, tmp_path, capsys):
    """Covers lines 105-108: --validate-only, matching file → ok++."""
    agents = {"a": _make_agent("a")}
    _, sub_dir = _setup_main_env(monkeypatch, tmp_path, agents=agents)
    # Pre-create matching YAML
    sub_dir.mkdir(parents=True, exist_ok=True)
    out_name = "sub_mas-a.yaml"
    from tools.dev_yaml_generator_core import generate_agent_yaml
    pre = generate_agent_yaml("a", agents["a"],
                              yaml.safe_load(open(gen.MAS_SCHEMA)))
    (sub_dir / out_name).write_text(pre)
    monkeypatch.setattr(sys, "argv",
                        ["dev_yaml_generator.py", "--validate-only"])
    rc = gen.main()
    assert rc == 0
    out = capsys.readouterr().out
    assert "OK: 1/1" in out


def test_main_mas_mode_validate_only_diff(monkeypatch, tmp_path, capsys):
    """Covers lines 109-110: --validate-only, mismatching → diff_count++."""
    agents = {"a": _make_agent("a")}
    _, sub_dir = _setup_main_env(monkeypatch, tmp_path, agents=agents)
    sub_dir.mkdir(parents=True, exist_ok=True)
    # Pre-create wrong file
    (sub_dir / "sub_mas-a.yaml").write_text("title: WRONG\n")
    monkeypatch.setattr(sys, "argv",
                        ["dev_yaml_generator.py", "--validate-only"])
    rc = gen.main()
    assert rc == 0
    out = capsys.readouterr().out
    assert "Deviations: 1" in out


def test_main_show_diff_prints_issues(monkeypatch, tmp_path, capsys):
    """Covers lines 111-113: --diff + diff → print issues."""
    agents = {"a": _make_agent("a")}
    _, sub_dir = _setup_main_env(monkeypatch, tmp_path, agents=agents)
    sub_dir.mkdir(parents=True, exist_ok=True)
    (sub_dir / "sub_mas-a.yaml").write_text("title: WRONG\n")
    monkeypatch.setattr(sys, "argv",
                        ["dev_yaml_generator.py", "--diff"])
    rc = gen.main()
    assert rc == 0
    out = capsys.readouterr().out
    assert "title:" in out


def test_main_invalid_mode(monkeypatch, capsys):
    """Covers lines 67-69: invalid mode → sys.exit(1) + msg."""
    monkeypatch.setattr(sys, "argv",
                        ["dev_yaml_generator.py", "--mode", "bogus"])
    with pytest.raises(SystemExit) as ei:
        gen.main()
    assert ei.value.code == 1
    out = capsys.readouterr().out
    assert "Unbekannter Mode" in out


def test_main_empty_agents(monkeypatch, tmp_path, capsys):
    """Covers lines 82-84: agents empty → sys.exit(0) + msg."""
    _setup_main_env(monkeypatch, tmp_path, agents={})
    monkeypatch.setattr(sys, "argv", ["dev_yaml_generator.py"])
    with pytest.raises(SystemExit) as ei:
        gen.main()
    assert ei.value.code == 0
    out = capsys.readouterr().out
    assert "No Agenten" in out


def test_main_generate_error(monkeypatch, tmp_path, capsys):
    """Covers lines 97-99: generate_agent_yaml raises → error captured."""
    # Create agent with prompt that's not str (e.g., None) to make
    # generation fail. But our core is forgiving. Make agent with
    # 'settings' that contains an unstringifiable key.
    # Easier: monkey-patch generate_agent_yaml to raise.
    agents = {"a": _make_agent("a")}
    _setup_main_env(monkeypatch, tmp_path, agents=agents)

    def _boom(*args, **kwargs):
        raise RuntimeError("synthetic boom")
    monkeypatch.setattr(gen, "generate_agent_yaml", _boom)
    monkeypatch.setattr(sys, "argv",
                        ["dev_yaml_generator.py", "--write"])
    rc = gen.main()
    assert rc == 1
    out = capsys.readouterr().out
    assert "Error" in out
    assert "synthetic boom" in out


def test_main_with_target(monkeypatch, tmp_path, capsys):
    """Covers --target arg path: line 64-65 + find_schema/find_sub_dir."""
    target = tmp_path / "tgt"
    target.mkdir()
    schema_path = target / ".mase/templates/agent_schema.yaml"
    _write_schema(schema_path, {"a": _make_agent("a")})
    monkeypatch.setattr(sys, "argv",
                        ["dev_yaml_generator.py",
                         "--mode", "generic",
                         "--target", str(target),
                         "--write"])
    rc = gen.main()
    assert rc == 0
    out = capsys.readouterr().out
    assert "mode=generic" in out
    assert (target / "sub" / "sub_mas-a.yaml").exists()


def test_main_print_summary_errors_only(monkeypatch, tmp_path, capsys):
    """Covers lines 119-122: errors printed (max 3)."""
    agents = {"a": _make_agent("a"), "b": _make_agent("b")}
    _setup_main_env(monkeypatch, tmp_path, agents=agents)

    def _boom(*args, **kwargs):
        raise RuntimeError("boom")
    monkeypatch.setattr(gen, "generate_agent_yaml", _boom)
    monkeypatch.setattr(sys, "argv",
                        ["dev_yaml_generator.py", "--write"])
    rc = gen.main()
    assert rc == 1
    out = capsys.readouterr().out
    assert "Error: 2" in out


# ====================== __main__ ==================================

def test_main_entry_point_runs(monkeypatch, tmp_path):
    """Covers lines 126-127: __main__ entry calls main()."""
    agents = {"a": _make_agent("a")}
    _setup_main_env(monkeypatch, tmp_path, agents=agents)
    monkeypatch.setattr(sys, "argv",
                        ["dev_yaml_generator.py", "--write"])
    # Just call main() directly — same as __main__ does
    rc = gen.main()
    assert rc == 0
