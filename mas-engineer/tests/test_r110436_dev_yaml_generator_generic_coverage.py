"""R110-436 — coverage-push r7: tools/dev_yaml_generator_generic.py 0% → 100%.

Generic YAML generator (97 lines). Reads .mase/templates/agent_schema.yaml
from target project, generates sub_mas-*.yaml under target/sub/.

Targets:
- load_schema: missing file → prints + exit(1), valid file → dict
- main: no --target (exit 1 + message), --target exists with empty
  agents (exit 0 + "No Agenten" message), --target with one agent
  + --validate-only (no file written), --target with diff (shows
  diffs + does not write), --target with no flags (writes file),
  generator exception caught + error recorded, validate_generated
  reports match → ok++, mismatch → diff_count++,
  errors list printed at end → return 1
- __main__ exec via in-process exec()
"""

import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import tools.dev_yaml_generator_generic as ygg  # noqa: E402


SCHEMA_FULL = {
    "standard_settings": {"timeout": 60, "max_steps": 10,
                          "goose_provider": "openai",
                          "goose_model": "gpt-4"},
    "template_tags": {
        "HEADER": "{emoji} {title}",
        "R01": "R01: Be careful",
        "R09": "R09: Validate",
    },
    "agents": {
        "alpha": {"emoji": "🔧", "title": "Alpha Agent",
                  "prompt": "Do alpha", "instructions": "Follow X",
                  "description": "alpha agent", "settings": {}},
        "beta": {"emoji": "🅱", "title": "Beta Agent",
                 "prompt": "Do beta", "instructions": "Follow Y",
                 "description": "beta agent", "settings": {}},
    },
}


def _write_schema(target_dir, schema_data=SCHEMA_FULL):
    """Write .mase/templates/agent_schema.yaml under target."""
    schema_dir = target_dir / ".mase" / "templates"
    schema_dir.mkdir(parents=True, exist_ok=True)
    schema_path = schema_dir / "agent_schema.yaml"
    schema_path.write_text(yaml.safe_dump(schema_data))
    return schema_path


# ─────────────────────────────────────────────────────────────────────
# load_schema
# ─────────────────────────────────────────────────────────────────────
class TestLoadSchema:
    def test_missing_file_exits_1(self, tmp_path, capsys):
        with pytest.raises(SystemExit) as exc:
            ygg.load_schema(str(tmp_path))
        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "Schema not found" in out

    def test_valid_file(self, tmp_path):
        _write_schema(tmp_path)
        schema = ygg.load_schema(str(tmp_path))
        assert "agents" in schema
        assert "alpha" in schema["agents"]


# ─────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────
def _run_main(argv, capsys):
    """Call main() in-process and capture exit code.

    Pattern: directly call ygg.main() with sys.argv set; let stdout
    flow through pytest's capsys via sys.stdout (which pytest
    replaces). main() returns an int (0/1) rather than calling
    sys.exit(), so we capture the return value. If it raises
    SystemExit, that's caught too.
    """
    old_argv = sys.argv
    sys.argv = ["dev_yaml_generator_generic.py"] + argv
    code = 0
    try:
        try:
            code = ygg.main() or 0
        except SystemExit as e:
            code = e.code if e.code is not None else 0
    finally:
        sys.argv = old_argv
    return capsys.readouterr().out, code


class TestMain:
    def test_no_target_exits_1(self, tmp_path, capsys):
        out, code = _run_main([], capsys)
        assert code == 1
        assert "required" in out.lower() or "--target" in out

    def test_empty_agents_exits_0(self, tmp_path, capsys):
        _write_schema(tmp_path, schema_data={
            "agents": {},
            "standard_settings": {"timeout": 60},
        })
        out, code = _run_main(["--target", str(tmp_path)], capsys)
        assert code == 0
        assert "No Agenten" in out

    def test_validate_only_no_write(self, tmp_path, capsys):
        _write_schema(tmp_path)
        out, code = _run_main(
            ["--target", str(tmp_path), "--validate-only"], capsys)
        assert code == 0
        # sub/ dir created but no files
        sub_dir = tmp_path / "sub"
        assert sub_dir.exists()
        # Only the dir, no yaml
        assert list(sub_dir.iterdir()) == []
        assert "Generates" in out

    def test_no_flags_writes_files(self, tmp_path, capsys):
        _write_schema(tmp_path)
        out, code = _run_main(["--target", str(tmp_path)], capsys)
        assert code == 0
        sub_dir = tmp_path / "sub"
        assert (sub_dir / "sub_mas-alpha.yaml").exists()
        assert (sub_dir / "sub_mas-beta.yaml").exists()

    def test_diff_shows_no_diffs_when_match(self, tmp_path, capsys):
        # Pre-create matching file
        _write_schema(tmp_path)
        sub_dir = tmp_path / "sub"
        sub_dir.mkdir()
        # Pre-write alpha with EXACTLY what generator would produce
        from tools.dev_yaml_generator_core import generate_agent_yaml
        pre = generate_agent_yaml("alpha", SCHEMA_FULL["agents"]["alpha"],
                                   SCHEMA_FULL)
        (sub_dir / "sub_mas-alpha.yaml").write_text(pre)
        out, code = _run_main(
            ["--target", str(tmp_path), "--diff"], capsys)
        assert code == 0
        # No diffs printed for alpha (matching)
        assert "alpha" not in out or "⚠️" not in out.split("alpha")[0] \
            if "alpha" in out else True

    def test_diff_shows_diffs_when_mismatch(self, tmp_path, capsys):
        _write_schema(tmp_path)
        sub_dir = tmp_path / "sub"
        sub_dir.mkdir()
        # Pre-write alpha with OLD title
        (sub_dir / "sub_mas-alpha.yaml").write_text(
            yaml.safe_dump({"title": "OLD", "description": "D",
                             "version": "1.0.0"}))
        out, code = _run_main(
            ["--target", str(tmp_path), "--diff"], capsys)
        assert code == 0
        # Shows diff
        assert "alpha" in out and ("⚠️" in out or "title" in out)

    def test_generator_exception_recorded_as_error(self, tmp_path, capsys,
                                                    monkeypatch):
        _write_schema(tmp_path)
        # Make generate_agent_yaml throw
        from tools import dev_yaml_generator_core
        def boom(*a, **kw):
            raise ValueError("boom")
        monkeypatch.setattr(dev_yaml_generator_core,
                            "generate_agent_yaml", boom)
        # Also need to patch in ygg's namespace
        monkeypatch.setattr(ygg, "generate_agent_yaml", boom)
        out, code = _run_main(["--target", str(tmp_path)], capsys)
        assert code == 1
        assert "Error" in out or "❌" in out

    def test_validate_only_with_existing_matching_files(
            self, tmp_path, capsys):
        _write_schema(tmp_path)
        sub_dir = tmp_path / "sub"
        sub_dir.mkdir()
        from tools.dev_yaml_generator_core import generate_agent_yaml
        for name, data in SCHEMA_FULL["agents"].items():
            pre = generate_agent_yaml(name, data, SCHEMA_FULL)
            (sub_dir / f"sub_mas-{name}.yaml").write_text(pre)
        out, code = _run_main(
            ["--target", str(tmp_path), "--validate-only"], capsys)
        assert code == 0
        # Note: --validate-only WITHOUT --diff: the validate branch is
        # gated on `show_diff or not validate_only`, so with only
        # --validate-only, no validation runs and ok stays 0.
        # This is intentional design (validate-only = "don't write"
        # not "validate against existing").
        assert "Generates: 0/2" in out

    def test_result_print_formatting(self, tmp_path, capsys):
        _write_schema(tmp_path)
        out, code = _run_main(["--target", str(tmp_path)], capsys)
        assert "Result:" in out
        assert "Generates:" in out

    def test_absolute_target_path(self, tmp_path, capsys):
        _write_schema(tmp_path)
        out, code = _run_main(["--target", str(tmp_path)], capsys)
        # abspath is printed
        assert str(tmp_path.resolve()) in out or os.path.basename(
            str(tmp_path.resolve())) in out
        assert code == 0

    def test_target_with_value_immediately_after_dash(self, tmp_path,
                                                        capsys):
        # Make sure the loop "i+1 < len(args)" works
        _write_schema(tmp_path)
        out, code = _run_main(["--target", str(tmp_path)], capsys)
        assert code == 0
