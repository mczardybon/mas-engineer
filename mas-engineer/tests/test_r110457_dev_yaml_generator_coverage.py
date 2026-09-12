"""R110-457 — coverage-push r8: tools/dev_yaml_generator.py 0% → 100%.

Standard (mas-mode) version. CLI:
  --mode mas|generic, --target PATH, --validate-only, --diff, --write

Note: same top-level `from dev_yaml_generator_core import` as
generic — must inject core into sys.modules before importing
this module. Also same latent None-settings bug fix.

Targets:
- Constants: MAS_SCHEMA, GEN_SCHEMA, MAS_SUB_DIR
- find_schema(mode, target=None):
  - mode='generic' + target + primary exists → primary
  - mode='generic' + target + primary missing + fallback exists → fallback
  - mode='generic' + target + both missing → error + sys.exit(1)
  - mode='generic' + no target + GEN_SCHEMA exists → GEN_SCHEMA
  - MAS_SCHEMA exists → MAS_SCHEMA (default branch)
  - MAS_SCHEMA missing → error + sys.exit(1)
- find_sub_dir(mode, target=None):
  - mode='generic' + target → target/sub, mkdir
  - default → MAS_SUB_DIR, mkdir
- load_schema(path): yaml.safe_load
- main():
  - default mode='mas', no target
  - --mode invalid → error + sys.exit(1)
  - --target → abspath
  - 0 agents → warn + sys.exit(0)
  - default = validate-only (no --write), nothing happens
  - --write → writes file, ok+=1
  - --diff or --validate-only → validate_generated, on
    valid ok+=1, else diff_count+=1 + maybe print first 3
  - generator Exception → errors+=1
  - returns 0 if no errors else 1
"""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

_core_spec = importlib.util.spec_from_file_location(
    "dev_yaml_generator_core",
    str(REPO_ROOT / "tools" / "dev_yaml_generator_core.py"))
_core_mod = importlib.util.module_from_spec(_core_spec)
sys.modules["dev_yaml_generator_core"] = _core_mod
_core_spec.loader.exec_module(_core_mod)

import tools.dev_yaml_generator as yg  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────
class TestConstants:
    def test_mas_schema(self):
        assert yg.MAS_SCHEMA == ".mase/templates/agent_schema.yaml"

    def test_gen_schema(self):
        assert yg.GEN_SCHEMA == ".mase/templates/agent_schema_generic.yaml"

    def test_mas_sub_dir(self):
        assert yg.MAS_SUB_DIR == "recipe/sub"


# ─────────────────────────────────────────────────────────────────────
# find_schema
# ─────────────────────────────────────────────────────────────────────
class TestFindSchema:
    def test_generic_target_primary(self, tmp_path, monkeypatch):
        target = tmp_path / "t"
        schema_dir = target / ".mase" / "templates"
        schema_dir.mkdir(parents=True)
        (schema_dir / "agent_schema.yaml").write_text("agents: {}")
        monkeypatch.chdir(tmp_path)
        result = yg.find_schema("generic", str(target))
        assert result.endswith("agent_schema.yaml")

    def test_generic_target_fallback(self, tmp_path, monkeypatch):
        target = tmp_path / "t"
        schema_dir = target / ".mase" / "templates"
        schema_dir.mkdir(parents=True)
        (schema_dir / "agent_schema_generic.yaml").write_text("agents: {}")
        monkeypatch.chdir(tmp_path)
        result = yg.find_schema("generic", str(target))
        assert result.endswith("agent_schema_generic.yaml")

    def test_generic_target_missing_exits(self, tmp_path, monkeypatch,
                                            capsys):
        target = tmp_path / "t"
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc:
            yg.find_schema("generic", str(target))
        assert exc.value.code == 1
        assert "No Schema" in capsys.readouterr().out

    def test_generic_no_target_uses_global(self, tmp_path, monkeypatch):
        # GEN_SCHEMA exists relative to cwd
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".mase" / "templates").mkdir(parents=True)
        (tmp_path / ".mase" / "templates"
         / "agent_schema_generic.yaml").write_text("agents: {}")
        result = yg.find_schema("generic")
        assert result.endswith("agent_schema_generic.yaml")

    def test_generic_no_target_missing(self, tmp_path, monkeypatch,
                                        capsys):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc:
            yg.find_schema("generic")
        assert exc.value.code == 1

    def test_mas_mode_uses_mas_schema(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".mase" / "templates").mkdir(parents=True)
        (tmp_path / ".mase" / "templates"
         / "agent_schema.yaml").write_text("agents: {}")
        result = yg.find_schema("mas")
        assert result.endswith("agent_schema.yaml")

    def test_no_schema_anywhere_exits(self, tmp_path, monkeypatch,
                                        capsys):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc:
            yg.find_schema("mas")
        assert exc.value.code == 1
        assert "Schema not found" in capsys.readouterr().out


# ─────────────────────────────────────────────────────────────────────
# find_sub_dir
# ─────────────────────────────────────────────────────────────────────
class TestFindSubDir:
    def test_generic_target_creates_subdir(self, tmp_path):
        target = tmp_path / "t"
        target.mkdir()
        result = yg.find_sub_dir("generic", str(target))
        assert result == str(target / "sub")
        assert (target / "sub").exists()

    def test_mas_creates_recipe_sub(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # MAS_SUB_DIR is module-level — patch for this test
        orig = yg.MAS_SUB_DIR
        yg.MAS_SUB_DIR = str(tmp_path / "recipe" / "sub")
        try:
            result = yg.find_sub_dir("mas")
            assert result == yg.MAS_SUB_DIR
            assert os.path.isdir(yg.MAS_SUB_DIR)
        finally:
            yg.MAS_SUB_DIR = orig

    def test_mas_idempotent(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        orig = yg.MAS_SUB_DIR
        yg.MAS_SUB_DIR = str(tmp_path / "recipe" / "sub")
        try:
            yg.find_sub_dir("mas")  # creates
            # Second call shouldn't raise
            yg.find_sub_dir("mas")
        finally:
            yg.MAS_SUB_DIR = orig


# ─────────────────────────────────────────────────────────────────────
# load_schema
# ─────────────────────────────────────────────────────────────────────
class TestLoadSchema:
    def test_loads_yaml(self, tmp_path):
        f = tmp_path / "s.yaml"
        f.write_text("agents:\n  foo: {}\n")
        s = yg.load_schema(str(f))
        assert "agents" in s
        assert "foo" in s["agents"]


# ─────────────────────────────────────────────────────────────────────
# main — error paths (subprocess CLI)
# ─────────────────────────────────────────────────────────────────────
class TestMainCli:
    def test_invalid_mode(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # No schema → find_schema exits before mode validation?
        # Actually mode validation happens AFTER find_schema in
        # source... wait no, mode validation is BEFORE find_schema.
        # But we need a schema for find_schema not to exit first.
        # Since we pass --mode foo with no schema, find_schema
        # still tries MAS_SCHEMA. Patch MAS_SCHEMA to exist:
        (tmp_path / ".mase" / "templates").mkdir(parents=True)
        (tmp_path / ".mase" / "templates"
         / "agent_schema.yaml").write_text("agents: {}\n")
        monkeypatch.setattr(sys, "argv",
                            ["x", "--mode", "foo"])
        with pytest.raises(SystemExit) as exc:
            yg.main()
        assert exc.value.code == 1


# ─────────────────────────────────────────────────────────────────────
# main — happy paths via direct call (monkeypatched argv)
# ─────────────────────────────────────────────────────────────────────
class TestMainGenerate:
    def _setup_mas_target(self, tmp_path, agents_dict, standard=None):
        schema_dir = tmp_path / ".mase" / "templates"
        schema_dir.mkdir(parents=True)
        import yaml as _y
        schema = {"agents": agents_dict}
        if standard:
            schema["standard_settings"] = standard
        (schema_dir / "agent_schema.yaml").write_text(
            _y.safe_dump(schema, sort_keys=False))

    def test_write_mode(self, tmp_path, monkeypatch, capsys):
        self._setup_mas_target(tmp_path, {
            "alpha": {"prompt": "p"},
            "beta":  {"prompt": "q"},
        })
        monkeypatch.chdir(tmp_path)
        # Patch MAS_SUB_DIR to tmp_path so we don't pollute
        # the repo
        monkeypatch.setattr(yg, "MAS_SUB_DIR",
                            str(tmp_path / "recipe" / "sub"))
        monkeypatch.setattr(sys, "argv",
                            ["x", "--write"])
        rc = yg.main()
        assert rc == 0
        out = capsys.readouterr().out
        assert "✅ OK: 2/2" in out
        sub = tmp_path / "recipe" / "sub"
        assert (sub / "sub_mas-alpha.yaml").exists()
        assert (sub / "sub_mas-beta.yaml").exists()

    def test_no_write_no_diff_no_validate_only(
            self, tmp_path, monkeypatch, capsys):
        # Default = no --write, no --diff, no --validate-only
        # → enters else branch but show_diff False, validate_only
        # False → no validation, no write. ok stays 0.
        self._setup_mas_target(tmp_path, {"x": {"prompt": "p"}})
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(yg, "MAS_SUB_DIR",
                            str(tmp_path / "recipe" / "sub"))
        monkeypatch.setattr(sys, "argv", ["x"])
        rc = yg.main()
        assert rc == 0
        out = capsys.readouterr().out
        assert "✅ OK: 0/1" in out

    def test_validate_only_ok(self, tmp_path, monkeypatch, capsys):
        self._setup_mas_target(tmp_path,
                                {"x": {"prompt": "p"}},
                                standard={"timeout": 300})
        monkeypatch.chdir(tmp_path)
        sub = tmp_path / "recipe" / "sub"
        sub.mkdir(parents=True)
        # Pre-write matching file
        (sub / "sub_mas-x.yaml").write_text(
            "version: \"1.0.0\"\ntitle: SUB-MAS-X\n"
            "description: 'v1.0.0 | SUB-MAS-X'\n"
            "instructions: \"\"\nprompt: ''\n"
            "settings:\n  timeout: 300\n")
        monkeypatch.setattr(yg, "MAS_SUB_DIR", str(sub))
        monkeypatch.setattr(sys, "argv", ["x", "--validate-only"])
        rc = yg.main()
        assert rc == 0
        out = capsys.readouterr().out
        assert "✅ OK: 1/1" in out

    def test_validate_only_diff(self, tmp_path, monkeypatch, capsys):
        self._setup_mas_target(tmp_path,
                                {"x": {"prompt": "p"}},
                                standard={"timeout": 300})
        monkeypatch.chdir(tmp_path)
        sub = tmp_path / "recipe" / "sub"
        sub.mkdir(parents=True)
        # Pre-write DIFFERENT file (with settings dict to avoid
        # the None-settings crash)
        (sub / "sub_mas-x.yaml").write_text(
            "title: different\nversion: '0.0.0'\n"
            "description: 'd'\nsettings:\n  timeout: 1\n"
            "  max_steps: 1\n  goose_provider: a\n  goose_model: b\n")
        monkeypatch.setattr(yg, "MAS_SUB_DIR", str(sub))
        monkeypatch.setattr(sys, "argv", ["x", "--validate-only"])
        rc = yg.main()
        assert rc == 0
        out = capsys.readouterr().out
        assert "⚠️  Deviations: 1" in out

    def test_diff_shows_issues(self, tmp_path, monkeypatch, capsys):
        self._setup_mas_target(tmp_path,
                                {"x": {"prompt": "p"}},
                                standard={"timeout": 300})
        monkeypatch.chdir(tmp_path)
        sub = tmp_path / "recipe" / "sub"
        sub.mkdir(parents=True)
        (sub / "sub_mas-x.yaml").write_text(
            "title: different\nversion: '0.0.0'\n"
            "description: 'd'\nsettings:\n  timeout: 1\n"
            "  max_steps: 1\n  goose_provider: a\n  goose_model: b\n")
        monkeypatch.setattr(yg, "MAS_SUB_DIR", str(sub))
        monkeypatch.setattr(sys, "argv", ["x", "--diff"])
        rc = yg.main()
        assert rc == 0
        out = capsys.readouterr().out
        assert "⚠️" in out

    def test_diff_issues_truncated_to_3(self, tmp_path, monkeypatch,
                                          capsys):
        # 4 settings mismatches → only first 3 printed per source
        self._setup_mas_target(tmp_path,
                                {"x": {"prompt": "p"}},
                                standard={"timeout": 300,
                                          "max_steps": 50,
                                          "goose_provider": "openai",
                                          "goose_model": "gpt-4"})
        monkeypatch.chdir(tmp_path)
        sub = tmp_path / "recipe" / "sub"
        sub.mkdir(parents=True)
        (sub / "sub_mas-x.yaml").write_text(
            "title: different\nversion: '0.0.0'\n"
            "description: 'd'\nsettings:\n  timeout: 1\n"
            "  max_steps: 1\n  goose_provider: x\n  goose_model: y\n")
        monkeypatch.setattr(yg, "MAS_SUB_DIR", str(sub))
        monkeypatch.setattr(sys, "argv", ["x", "--diff"])
        rc = yg.main()
        out = capsys.readouterr().out
        # 3 issue lines printed (first 3 of issues list)
        issue_lines = [l for l in out.split("\n")
                       if "⚠️" in l and "sub_mas-x" in l]
        assert len(issue_lines) == 3


class TestMainErrors:
    def test_generator_error_recorded(self, tmp_path, monkeypatch,
                                       capsys):
        schema_dir = tmp_path / ".mase" / "templates"
        schema_dir.mkdir(parents=True)
        import yaml as _y
        (schema_dir / "agent_schema.yaml").write_text(
            _y.safe_dump({"agents": {"x": {"prompt": "p"}}},
                          sort_keys=False))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(yg, "MAS_SUB_DIR",
                            str(tmp_path / "recipe" / "sub"))
        monkeypatch.setattr(yg, "generate_agent_yaml",
                            lambda *a, **kw: (_ for _ in ()).throw(
                                RuntimeError("boom")))
        monkeypatch.setattr(sys, "argv", ["x", "--write"])
        rc = yg.main()
        assert rc == 1
        out = capsys.readouterr().out
        assert "❌ Error: 1" in out
        assert "boom" in out


class TestMainEmptyAgents:
    def test_empty_agents_exits_0(self, tmp_path, monkeypatch,
                                    capsys):
        schema_dir = tmp_path / ".mase" / "templates"
        schema_dir.mkdir(parents=True)
        (schema_dir / "agent_schema.yaml").write_text("agents: {}\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["x"])
        with pytest.raises(SystemExit) as exc:
            yg.main()
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "No Agenten" in out


class TestMainTargetMode:
    def test_target_abspath(self, tmp_path, monkeypatch, capsys):
        target = tmp_path / "myproj"
        schema_dir = target / ".mase" / "templates"
        schema_dir.mkdir(parents=True)
        import yaml as _y
        (schema_dir / "agent_schema.yaml").write_text(
            _y.safe_dump({"agents": {"x": {"prompt": "p"}}},
                          sort_keys=False))
        monkeypatch.setattr(sys, "argv",
                            ["x", "--mode", "generic",
                             "--target", str(target),
                             "--write"])
        rc = yg.main()
        assert rc == 0
        out = capsys.readouterr().out
        assert "Target:" in out
        # File written under target/sub/
        assert (target / "sub" / "sub_mas-x.yaml").exists()
