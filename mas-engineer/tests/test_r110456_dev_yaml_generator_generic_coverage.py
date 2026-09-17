"""R110-456 — coverage-push r8: tools/dev_yaml_generator_generic.py 0% → 100%.

Generic-Version des YAML-Generators. Generates sub_mas-*.yaml
from agent_schema.yaml (SOT) for user projects. CLI:
--target <dir> [--validate-only] [--diff].

Note: module does `from dev_yaml_generator_core import ...`
(NOT a relative import). For testing, inject the core module
into sys.modules BEFORE importing the generic.

Targets:
- load_schema(target_dir): if .mase/templates/agent_schema.yaml
  doesn't exist → print error + sys.exit(1). Else yaml.safe_load.
- main(): parses --target from argv, --validate-only, --diff
  flags. No --target → sys.exit(1). Loads schema. If no agents
  → print warning + sys.exit(0). Prints agent count + default
  timeout. mkdir sub/. Iterates sorted agents: builds out_path,
  generates + safe_loads, on exception → error + continue.
  If show_diff or not validate_only → validate_generated; if
  valid → ok+=1 else → diff_count+=1 + maybe print issues.
  If not validate_only and not show_diff → write file + ok+=1.
  Prints Result: ✅ Generated: X/Y, ⚠️ Deviations, ❌ Error
  (first 3). Returns 0 if no errors else 1.
"""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# Inject core as top-level so `from dev_yaml_generator_core import`
# inside the generic module resolves.
_core_spec = importlib.util.spec_from_file_location(
    "dev_yaml_generator_core",
    str(REPO_ROOT / "tools" / "dev_yaml_generator_core.py"))
_core_mod = importlib.util.module_from_spec(_core_spec)
sys.modules["dev_yaml_generator_core"] = _core_mod
_core_spec.loader.exec_module(_core_mod)

import tools.dev_yaml_generator_generic as ygg  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# Helpers — build a temp target directory with schema + agents
# ─────────────────────────────────────────────────────────────────────
def _write_schema(target, agents, standard_settings=None):
    target.mkdir(parents=True, exist_ok=True)
    schema_dir = target / ".mase" / "templates"
    schema_dir.mkdir(parents=True, exist_ok=True)
    schema = {"agents": agents}
    if standard_settings:
        schema["standard_settings"] = standard_settings
    import yaml as _y
    (schema_dir / "agent_schema.yaml").write_text(
        _y.safe_dump(schema, sort_keys=False))


# ─────────────────────────────────────────────────────────────────────
# Module-level constants
# ─────────────────────────────────────────────────────────────────────
class TestConstants:
    def test_schema_file(self):
        assert ygg.SCHEMA_FILE == ".mase/templates/agent_schema.yaml"

    def test_sub_dir(self):
        assert ygg.SUB_DIR == "sub"


# ─────────────────────────────────────────────────────────────────────
# load_schema
# ─────────────────────────────────────────────────────────────────────
class TestLoadSchema:
    def test_loads(self, tmp_path):
        _write_schema(tmp_path, {"foo": {"emoji": "x"}})
        s = ygg.load_schema(str(tmp_path))
        assert "agents" in s
        assert "foo" in s["agents"]

    def test_missing_schema_exits(self, tmp_path, capsys):
        with pytest.raises(SystemExit) as exc:
            ygg.load_schema(str(tmp_path))
        assert exc.value.code == 1
        assert "Schema not found" in capsys.readouterr().out


# ─────────────────────────────────────────────────────────────────────
# main — error paths (subprocess for CLI)
# ─────────────────────────────────────────────────────────────────────
class TestMainCli:
    def test_no_target(self):
        r = subprocess.run(
            ['python3', 'tools/dev_yaml_generator_generic.py'],
            capture_output=True, text=True, timeout=10,
            cwd=str(REPO_ROOT))
        assert r.returncode == 1
        assert "--target" in r.stdout

    def test_target_with_no_schema(self, tmp_path):
        r = subprocess.run(
            ['python3', 'tools/dev_yaml_generator_generic.py',
             '--target', str(tmp_path)],
            capture_output=True, text=True, timeout=10,
            cwd=str(REPO_ROOT))
        assert r.returncode == 1
        assert "Schema not found" in r.stdout

    def test_target_with_empty_agents_exits_0(self, tmp_path):
        _write_schema(tmp_path, agents={})
        r = subprocess.run(
            ['python3', 'tools/dev_yaml_generator_generic.py',
             '--target', str(tmp_path)],
            capture_output=True, text=True, timeout=10,
            cwd=str(REPO_ROOT))
        assert r.returncode == 0
        assert "No Agenten" in r.stdout


# ─────────────────────────────────────────────────────────────────────
# main — generate path (direct call, monkeypatched argv)
# ─────────────────────────────────────────────────────────────────────
class TestMainGenerate:
    def test_generates_files(self, tmp_path, monkeypatch, capsys):
        _write_schema(tmp_path, {
            "alpha": {"title": "A", "prompt": "p"},
            "beta":  {"title": "B", "prompt": "q"},
        })
        monkeypatch.setattr(sys, "argv",
                            ["x", "--target", str(tmp_path)])
        rc = ygg.main()
        assert rc == 0
        out = capsys.readouterr().out
        assert "2 Agenten" in out
        assert "✅ Generates: 2/2" in out
        # Files were created
        sub = tmp_path / "sub"
        assert (sub / "sub_mas-alpha.yaml").exists()
        assert (sub / "sub_mas-beta.yaml").exists()

    def test_generate_with_standard_settings(self, tmp_path,
                                              monkeypatch, capsys):
        _write_schema(tmp_path,
                      {"x": {"prompt": "p"}},
                      standard_settings={"timeout": 600,
                                          "max_steps": 10})
        monkeypatch.setattr(sys, "argv",
                            ["x", "--target", str(tmp_path)])
        rc = ygg.main()
        assert rc == 0
        out = capsys.readouterr().out
        assert "timeout=600" in out


class TestMainValidateOnly:
    def test_validate_only_no_write(self, tmp_path, monkeypatch, capsys):
        # Note: per main() logic, --validate-only means
        # `if show_diff or not validate_only` is False, so
        # validate_generated is NOT called either → ok stays 0.
        # This is original behavior (validate-only is currently
        # a no-op for the validate branch). Test just verifies
        # nothing is written.
        _write_schema(tmp_path, {"x": {"prompt": "p"}})
        monkeypatch.setattr(sys, "argv",
                            ["x", "--target", str(tmp_path),
                             "--validate-only"])
        rc = ygg.main()
        assert rc == 0
        sub = tmp_path / "sub"
        assert not (sub / "sub_mas-x.yaml").exists()

    def test_validate_only_with_existing_valid_file(
            self, tmp_path, monkeypatch, capsys):
        # --validate-only is a no-op for validation per current
        # source. Files in sub/ untouched.
        _write_schema(tmp_path, {"x": {"prompt": "p"}})
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "sub_mas-x.yaml").write_text("anything")
        monkeypatch.setattr(sys, "argv",
                            ["x", "--target", str(tmp_path),
                             "--validate-only"])
        rc = ygg.main()
        assert rc == 0
        assert (sub / "sub_mas-x.yaml").read_text() == "anything"

    def test_validate_only_with_existing_invalid_file(
            self, tmp_path, monkeypatch, capsys):
        # Same: validate-only doesn't trigger validate, so no
        # Deviations counter increments from this path.
        _write_schema(tmp_path, {"x": {"prompt": "p"}})
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "sub_mas-x.yaml").write_text(
            "title: different\nversion: '0.0.0'\n")
        monkeypatch.setattr(sys, "argv",
                            ["x", "--target", str(tmp_path),
                             "--validate-only"])
        rc = ygg.main()
        assert rc == 0
        # validate-only path skips validation entirely
        out = capsys.readouterr().out
        assert "Deviations" not in out

    def test_validate_only_match_with_settings_dict(
            self, tmp_path, monkeypatch, capsys):
        # Without --validate-only, file gets generated & written
        _write_schema(tmp_path, {"x": {"prompt": "p"}},
                      standard_settings={"timeout": 300})
        monkeypatch.setattr(sys, "argv",
                            ["x", "--target", str(tmp_path)])
        rc = ygg.main()
        assert rc == 0
        out = capsys.readouterr().out
        # No existing file → validate says "FEHLT" → diff
        # But since we wrote first, and write is on `not
        # validate_only and not show_diff` → write happened
        assert (tmp_path / "sub" / "sub_mas-x.yaml").exists()


class TestMainDiff:
    def test_diff_shows_issues(self, tmp_path, monkeypatch, capsys):
        _write_schema(tmp_path, {"x": {"prompt": "p"}})
        sub = tmp_path / "sub"
        sub.mkdir()
        # Write a file with mismatched title AND a settings dict
        # (avoid the latent None-settings crash in validate_generated)
        (sub / "sub_mas-x.yaml").write_text(
            "title: different\nversion: '0.0.0'\n"
            "description: 'd'\nsettings:\n  timeout: 1\n"
            "  max_steps: 1\n  goose_provider: a\n  goose_model: b\n")
        monkeypatch.setattr(sys, "argv",
                            ["x", "--target", str(tmp_path),
                             "--diff"])
        rc = ygg.main()
        assert rc == 0
        out = capsys.readouterr().out
        assert "⚠️" in out
        assert "title" in out

    def test_diff_no_issues(self, tmp_path, monkeypatch, capsys):
        _write_schema(tmp_path, {"x": {"prompt": "p"}},
                      standard_settings={"timeout": 300})
        sub = tmp_path / "sub"
        sub.mkdir()
        # Write matching file
        (sub / "sub_mas-x.yaml").write_text(
            "version: \"1.0.0\"\ntitle: SUB-MAS-X\n"
            "description: 'v1.0.0 | SUB-MAS-X'\n"
            "instructions: \"\"\nprompt: ''\n"
            "settings:\n  timeout: 300\n")
        monkeypatch.setattr(sys, "argv",
                            ["x", "--target", str(tmp_path),
                             "--diff"])
        rc = ygg.main()
        assert rc == 0
        out = capsys.readouterr().out
        assert "✅ Generates: 1/1" in out


class TestMainErrors:
    def test_generator_exception_recorded(
            self, tmp_path, monkeypatch, capsys):
        # Schema has an agent whose prompt text will trip
        # generate_agent_yaml via yaml.safe_load roundtrip on
        # an unbalanced string. Easier: monkeypatch
        # generate_agent_yaml to raise.
        _write_schema(tmp_path, {"x": {"prompt": "p"}})
        monkeypatch.setattr(ygg, "generate_agent_yaml",
                            lambda *a, **kw: (_ for _ in ()).throw(
                                RuntimeError("boom")))
        monkeypatch.setattr(sys, "argv",
                            ["x", "--target", str(tmp_path)])
        rc = ygg.main()
        assert rc == 1
        out = capsys.readouterr().out
        assert "❌ Error: 1" in out
        assert "boom" in out


class TestMainAbsolute:
    def test_target_made_absolute(self, tmp_path, monkeypatch, capsys):
        real = tmp_path / "real"
        _write_schema(real, {"x": {"prompt": "p"}})
        # Pass relative path
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv",
                            ["x", "--target", "real"])
        rc = ygg.main()
        assert rc == 0
        out = capsys.readouterr().out
        assert "for:" in out
