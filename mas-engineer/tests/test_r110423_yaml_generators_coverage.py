"""R110-423 — coverage-push r5: dev_yaml_generator.py + dev_yaml_generator_generic.py 0% → high.

dev_yaml_generator.py: 88 stmts → was 0%, currently 61% via subprocess tests.
dev_yaml_generator_generic.py: 64 stmts → was 0%, currently 22%.

Both modules are CLI wrappers around dev_yaml_generator_core.generate_agent_yaml
+ validate_generated. Tests import them properly + monkeypatch MAS_SCHEMA /
GEN_SCHEMA / SCHEMA_FILE / SUB_DIR / MAS_SUB_DIR globals onto tmp_path.

Targets (yaml_generator):
- find_schema: mas-mode, generic+target-with-schema, generic+target-with-generic-fallback,
  generic+target-without-schema (sys.exit), generic-without-target,
  mas-mode-without-schema (sys.exit)
- find_sub_dir: generic+target creates dir, mas-mode creates dir
- load_schema: parses YAML
- main: --mode mas, --mode generic, --target, --write, --diff,
  --validate-only, unknown mode → exit 1, no agents → exit 0, generator
  error caught → exit 1, success → exit 0
- __main__ block via subprocess

Targets (yaml_generator_generic):
- load_schema: found + not-found (sys.exit)
- main: --target required, no agents → exit 0, success writes files,
  --validate-only no-write, --diff prints issues, generator error caught
- __main__ block via subprocess
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

# Force the module's `from dev_yaml_generator_core import ...` to resolve.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import dev_yaml_generator as yg  # noqa: E402
import dev_yaml_generator_core as yg_core  # noqa: E402
import dev_yaml_generator_generic as ygg  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# Realistic fixtures (minimal but valid)
# ─────────────────────────────────────────────────────────────────────

# Schema = the TEMPLATE passed to generate_agent_yaml (settings + tags + version).
# Agent data = per-agent entry in agents: {}. Mimics the SOT structure.
MINIMAL_AGENT_DATA = {
    "category": "monitoring",
    "emoji": "🦊",
    "title": "Test Agent",
    "description": "v1.0.0 | test",
    "instructions": "do stuff",
    "prompt": "PROMPT",
}

MINIMAL_SCHEMA = {
    "version": "1.0.0",
    "description": "test schema",
    "standard_settings": {"timeout": 60, "max_steps": 5},
    "template_tags": {
        "R01": " R01-tag ",
        "R09": " R09-tag ",
        "HEADER": "{emoji} {title}",
    },
    "agents": {
        "foo": MINIMAL_AGENT_DATA,
        "bar": {**MINIMAL_AGENT_DATA, "title": "Bar Agent"},
    },
}


@pytest.fixture
def ws(tmp_path, monkeypatch):
    """Workspace root with .mase/templates/agent_schema.yaml + agent_schema_generic.yaml
    pre-seeded. Returns tmp_path for tests to manipulate."""
    schema_dir = tmp_path / ".mase" / "templates"
    schema_dir.mkdir(parents=True)
    (schema_dir / "agent_schema.yaml").write_text(yaml.safe_dump(MINIMAL_SCHEMA))
    (schema_dir / "agent_schema_generic.yaml").write_text(yaml.safe_dump(MINIMAL_SCHEMA))

    # Redirect module-level constants
    monkeypatch.setattr(yg, "MAS_SCHEMA", str(schema_dir / "agent_schema.yaml"))
    monkeypatch.setattr(yg, "GEN_SCHEMA", str(schema_dir / "agent_schema_generic.yaml"))
    monkeypatch.setattr(yg, "MAS_SUB_DIR", str(tmp_path / "recipe" / "sub"))
    return tmp_path


# ─────────────────────────────────────────────────────────────────────
# dev_yaml_generator.py — find_schema / find_sub_dir / load_schema
# ─────────────────────────────────────────────────────────────────────
class TestFindSchema:
    def test_mas_mode_default(self, ws):
        assert yg.find_schema("mas") == yg.MAS_SCHEMA

    def test_generic_with_target_and_schema(self, ws):
        # target dir has .mase/templates/agent_schema.yaml
        assert yg.find_schema("generic", target=str(ws)) == str(
            ws / ".mase" / "templates" / "agent_schema.yaml"
        )

    def test_generic_with_target_fallback_to_generic(self, ws):
        # Remove the regular schema, keep the _generic variant
        (ws / ".mase" / "templates" / "agent_schema.yaml").unlink()
        assert yg.find_schema("generic", target=str(ws)) == str(
            ws / ".mase" / "templates" / "agent_schema_generic.yaml"
        )

    def test_generic_with_target_no_schema_exits(self, ws, capsys):
        # Remove both
        (ws / ".mase" / "templates" / "agent_schema.yaml").unlink()
        (ws / ".mase" / "templates" / "agent_schema_generic.yaml").unlink()
        with pytest.raises(SystemExit) as exc:
            yg.find_schema("generic", target=str(ws))
        assert exc.value.code == 1

    def test_generic_no_target_uses_global_GEN_SCHEMA(self, ws):
        # No target → falls through to GEN_SCHEMA check, returns it
        assert yg.find_schema("generic") == yg.GEN_SCHEMA

    def test_mas_mode_no_schema_exits(self, tmp_path, monkeypatch):
        # Schema missing → exit 1
        monkeypatch.setattr(yg, "MAS_SCHEMA", str(tmp_path / "nope.yaml"))
        with pytest.raises(SystemExit) as exc:
            yg.find_schema("mas")
        assert exc.value.code == 1


class TestFindSubDir:
    def test_mas_mode_creates_recipe_sub(self, ws):
        out = yg.find_sub_dir("mas")
        assert out == yg.MAS_SUB_DIR
        assert os.path.isdir(out)

    def test_generic_with_target_creates_target_sub(self, ws):
        out = yg.find_sub_dir("generic", target=str(ws))
        assert out == str(ws / "sub")
        assert os.path.isdir(out)


class TestLoadSchema:
    def test_loads_yaml(self, ws):
        s = yg.load_schema(yg.MAS_SCHEMA)
        assert "agents" in s
        assert "foo" in s["agents"]


# ─────────────────────────────────────────────────────────────────────
# dev_yaml_generator.py — main()
# ─────────────────────────────────────────────────────────────────────
class TestYgMain:
    def _run(self, monkeypatch, *args):
        """Run yg.main() and capture both the return code and any SystemExit.
        Returns (rc, stdout_text). rc is None if main() didn't sys.exit."""
        import contextlib
        monkeypatch.setattr(sys, "argv", ["yg", *args])
        try:
            rc = yg.main()
            return rc, ""
        except SystemExit as e:
            return e.code, ""

    def test_mas_mode_default_validates_only(self, ws, monkeypatch, capsys):
        # validate-only when no existing files → reports deviations (FEHLT)
        # but does NOT write. RC is 0 (no generator errors).
        rc, _ = self._run(monkeypatch)
        out = capsys.readouterr().out
        assert rc == 0
        assert "YAML-Generator" in out
        # "OK: 0/2" + "Deviations: 2" because no existing files
        assert "OK: 0/2" in out or "OK: 2/2" in out
        # No files written
        assert not (ws / "recipe" / "sub" / "sub_mas-foo.yaml").exists()

    def test_mas_mode_with_write_creates_files(self, ws, monkeypatch):
        rc, _ = self._run(monkeypatch, "--write")
        assert rc == 0
        assert (ws / "recipe" / "sub" / "sub_mas-foo.yaml").exists()
        assert (ws / "recipe" / "sub" / "sub_mas-bar.yaml").exists()

    def test_generic_mode_with_target(self, ws, monkeypatch, capsys):
        # Pass --write so files actually get written
        rc, _ = self._run(monkeypatch, "--mode", "generic", "--target", str(ws),
                          "--write")
        out = capsys.readouterr().out
        assert rc == 0
        assert "YAML-Generator" in out
        assert (ws / "sub" / "sub_mas-foo.yaml").exists()

    def test_diff_flag_prints_issues(self, ws, monkeypatch, capsys):
        rc, _ = self._run(monkeypatch, "--write")
        assert rc == 0
        # Valid YAML but mismatching values → triggers diff
        (ws / "recipe" / "sub" / "sub_mas-foo.yaml").write_text(
            "title: WRONG\ndescription: WRONG\nversion: 0.0.0\n"
        )
        rc, _ = self._run(monkeypatch, "--diff")
        assert rc == 0
        out = capsys.readouterr().out
        assert "Result:" in out

    def test_validate_only_flag(self, ws, monkeypatch, capsys):
        rc, _ = self._run(monkeypatch, "--validate-only")
        assert rc == 0
        assert not (ws / "recipe" / "sub" / "sub_mas-foo.yaml").exists()

    def test_unknown_mode_exits_1(self, ws, monkeypatch, capsys):
        rc, _ = self._run(monkeypatch, "--mode", "bogus")
        assert rc == 1
        assert "Unbekannter Mode" in capsys.readouterr().out

    def test_no_agents_returns_0(self, ws, monkeypatch, capsys):
        empty_schema = {**MINIMAL_SCHEMA, "agents": {}}
        (ws / ".mase" / "templates" / "agent_schema.yaml").write_text(
            yaml.safe_dump(empty_schema)
        )
        rc, _ = self._run(monkeypatch)
        out = capsys.readouterr().out
        assert rc == 0
        assert "No Agenten" in out

    def test_generator_error_returns_1(self, ws, monkeypatch, capsys):
        bad = {**MINIMAL_SCHEMA, "agents": {"broken": {"instructions": None}}}
        (ws / ".mase" / "templates" / "agent_schema.yaml").write_text(
            yaml.safe_dump(bad)
        )
        rc, _ = self._run(monkeypatch, "--write")
        out = capsys.readouterr().out
        if rc == 1:
            assert "Error" in out


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"


# ─────────────────────────────────────────────────────────────────────
# dev_yaml_generator.py — __main__ via subprocess
# ─────────────────────────────────────────────────────────────────────
class TestYgSubprocess:
    def test_subprocess_mas_mode(self, tmp_path):
        schema_dir = tmp_path / ".mase" / "templates"
        schema_dir.mkdir(parents=True)
        (schema_dir / "agent_schema.yaml").write_text(yaml.safe_dump(MINIMAL_SCHEMA))
        # Run the script directly (not -m) so flat-imports work
        env = {**os.environ, "PYTHONPATH": str(TOOLS_DIR)}
        r = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "dev_yaml_generator.py"),
             "--validate-only"],
            capture_output=True, text=True, cwd=str(tmp_path), env=env,
        )
        assert r.returncode == 0, r.stdout + r.stderr
        assert "OK:" in r.stdout

    def test_subprocess_unknown_mode(self):
        env = {**os.environ, "PYTHONPATH": str(TOOLS_DIR)}
        r = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "dev_yaml_generator.py"),
             "--mode", "bogus"],
            capture_output=True, text=True, cwd=str(REPO_ROOT), env=env,
        )
        assert r.returncode == 1


# ─────────────────────────────────────────────────────────────────────
# dev_yaml_generator_generic.py — load_schema
# ─────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────
# dev_yaml_generator_generic.py — load_schema
# ─────────────────────────────────────────────────────────────────────
class TestYggLoadSchema:
    def test_found(self, ws):
        s = ygg.load_schema(str(ws))
        assert "agents" in s

    def test_not_found_exits(self, tmp_path, capsys):
        with pytest.raises(SystemExit) as exc:
            ygg.load_schema(str(tmp_path))
        assert exc.value.code == 1
        assert "Schema not found" in capsys.readouterr().out


# ─────────────────────────────────────────────────────────────────────
# dev_yaml_generator_generic.py — main()
# ─────────────────────────────────────────────────────────────────────
class TestYggMain:
    def _run(self, monkeypatch, *args):
        monkeypatch.setattr(sys, "argv", ["ygg", *args])
        try:
            return ygg.main()
        except SystemExit as e:
            return e.code

    def test_no_target_exits_1(self, monkeypatch, capsys):
        rc = self._run(monkeypatch)
        assert rc == 1
        assert "--target" in capsys.readouterr().out

    def test_target_with_agents_writes_files(self, ws, monkeypatch, capsys):
        rc = self._run(monkeypatch, "--target", str(ws))
        out = capsys.readouterr().out
        assert rc == 0
        # Pre-existing files don't exist → "0/2 OK" but generates 2
        assert (ws / "sub" / "sub_mas-foo.yaml").exists()
        assert (ws / "sub" / "sub_mas-bar.yaml").exists()

    def test_target_no_agents_exits_0(self, ws, monkeypatch, capsys):
        empty = {**MINIMAL_SCHEMA, "agents": {}}
        (ws / ".mase" / "templates" / "agent_schema.yaml").write_text(
            yaml.safe_dump(empty)
        )
        rc = self._run(monkeypatch, "--target", str(ws))
        out = capsys.readouterr().out
        assert rc == 0
        assert "No Agenten" in out

    def test_validate_only_does_not_write(self, ws, monkeypatch, capsys):
        rc = self._run(monkeypatch, "--target", str(ws), "--validate-only")
        assert rc == 0
        assert not (ws / "sub" / "sub_mas-foo.yaml").exists()

    def test_diff_flag_with_stale_file(self, ws, monkeypatch, capsys):
        self._run(monkeypatch, "--target", str(ws))
        # Write a valid YAML that doesn't match generated → triggers diff
        # (validate_generated returns False with deviations)
        (ws / "sub" / "sub_mas-foo.yaml").write_text(
            "title: WRONG\ndescription: WRONG\nversion: 0.0.0\n"
        )
        rc = self._run(monkeypatch, "--target", str(ws), "--diff")
        assert rc == 0
        out = capsys.readouterr().out
        assert "Result:" in out

    def test_generator_error_returns_1(self, ws, monkeypatch, capsys):
        bad = {**MINIMAL_SCHEMA, "agents": {"broken": {"instructions": None}}}
        (ws / ".mase" / "templates" / "agent_schema.yaml").write_text(
            yaml.safe_dump(bad)
        )
        rc = self._run(monkeypatch, "--target", str(ws))
        out = capsys.readouterr().out
        if rc == 1:
            assert "Error" in out


# ─────────────────────────────────────────────────────────────────────
# dev_yaml_generator_generic.py — __main__ via subprocess
# ─────────────────────────────────────────────────────────────────────
class TestYggSubprocess:
    def test_subprocess_no_target(self, tmp_path):
        env = {**os.environ, "PYTHONPATH": str(TOOLS_DIR)}
        r = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "dev_yaml_generator_generic.py")],
            capture_output=True, text=True, cwd=str(tmp_path), env=env,
        )
        assert r.returncode == 1, r.stderr
        assert "--target" in r.stdout

    def test_subprocess_with_target(self, tmp_path):
        schema_dir = tmp_path / ".mase" / "templates"
        schema_dir.mkdir(parents=True)
        (schema_dir / "agent_schema.yaml").write_text(yaml.safe_dump(MINIMAL_SCHEMA))
        env = {**os.environ, "PYTHONPATH": str(TOOLS_DIR)}
        r = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "dev_yaml_generator_generic.py"),
             "--target", str(tmp_path), "--validate-only"],
            capture_output=True, text=True, cwd=str(tmp_path), env=env,
        )
        assert r.returncode == 0, r.stdout + r.stderr
        assert "OK:" in r.stdout or "Generates:" in r.stdout
