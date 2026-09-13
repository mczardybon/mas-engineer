"""Targeted coverage push for tools/dev_template_engine.py — R110-505.

Target: dev_template_engine.py (6312 bytes, ~110 stmts, 0% covered
→ goal ~40%).

Strategy: import inline + use real temp workspace dirs. The pure
helpers (load_best_practices, extract_rules) and the YAML generator
(generate_yaml) operate on Path strings so we can use tmp_path.
The main() CLI is exercised with monkeypatched sys.argv.

Functions covered:
- load_best_practices (BP file present, BP file missing)
- extract_rules (with rules, max_rules limit, empty category, missing 'rule' key)
- generate_yaml (mas mode, generic mode, with best-practices, without
  best-practices, with auto_commit, empty task)
- main() CLI dispatch (--json, --registry, default output, mode choices)
"""
import json
import os
import sys
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"


@pytest.fixture
def engine(tmp_path, monkeypatch):
    """Import dev_template_engine inline."""
    if "dev_template_engine" in sys.modules:
        del sys.modules["dev_template_engine"]
    sys.path.insert(0, str(TOOLS_DIR))
    import dev_template_engine as engine  # noqa: E402
    return engine


# ─────────────────────────────────────────────────────────
# load_best_practices — pure file IO
# ─────────────────────────────────────────────────────────

def test_load_best_practices_present(engine, tmp_path):
    """BP file exists → returns best_practices dict."""
    bp_dir = tmp_path / "mas-engineer" / ".mase"
    bp_dir.mkdir(parents=True)
    bp_file = bp_dir / "best-practices.yaml"
    bp_file.write_text(
        "best_practices:\n"
        "  structure:\n"
        "    - rule: version_in_frontmatter\n"
        "  prompt:\n"
        "    - rule: short_prompt\n"
    )
    bp = engine.load_best_practices(str(tmp_path))
    assert "structure" in bp
    assert bp["structure"][0]["rule"] == "version_in_frontmatter"


def test_load_best_practices_missing(engine, tmp_path):
    """BP file doesn't exist → returns empty dict."""
    bp = engine.load_best_practices(str(tmp_path))
    assert bp == {}


def test_load_best_practices_no_best_practices_key(engine, tmp_path):
    """YAML exists but no best_practices key → returns empty dict."""
    bp_dir = tmp_path / "mas-engineer" / ".mase"
    bp_dir.mkdir(parents=True)
    (bp_dir / "best-practices.yaml").write_text("other_key: foo\n")
    bp = engine.load_best_practices(str(tmp_path))
    assert bp == {}


# ─────────────────────────────────────────────────────────
# extract_rules — pure helper
# ─────────────────────────────────────────────────────────

def test_extract_rules_returns_rule_strings(engine):
    """Each entry's 'rule' key is extracted."""
    bp = {"structure": [{"rule": "r1"}, {"rule": "r2"}, {"rule": "r3"}]}
    rules = engine.extract_rules(bp, "structure", max_rules=3)
    assert rules == ["r1", "r2", "r3"]


def test_extract_rules_max_rules_limit(engine):
    """max_rules caps the returned list."""
    bp = {"structure": [{"rule": "r1"}, {"rule": "r2"}, {"rule": "r3"}, {"rule": "r4"}]}
    rules = engine.extract_rules(bp, "structure", max_rules=2)
    assert rules == ["r1", "r2"]


def test_extract_rules_empty_category(engine):
    """Empty category → empty list."""
    bp = {"structure": []}
    rules = engine.extract_rules(bp, "structure")
    assert rules == []


def test_extract_rules_missing_category(engine):
    """Missing category key → empty list."""
    bp = {"other": [{"rule": "x"}]}
    rules = engine.extract_rules(bp, "structure")
    assert rules == []


def test_extract_rules_default_fallback_questionmark(engine):
    """Entries without 'rule' key → '?'."""
    bp = {"structure": [{"name": "no-rule-key"}, {"rule": "ok"}]}
    rules = engine.extract_rules(bp, "structure")
    assert rules == ["?", "ok"]


# ─────────────────────────────────────────────────────────
# generate_yaml — pure helper (with workspace lookup)
# ─────────────────────────────────────────────────────────

def test_generate_yaml_mas_mode(engine, tmp_path):
    """mas mode → file is created with sub_mas- prefix."""
    output = tmp_path / "out.yaml"
    stats = engine.generate_yaml(
        name="foo", emoji="🔧", task="Fix the bug",
        output=str(output), workspace=str(tmp_path), mode="mas"
    )
    assert output.exists()
    assert stats["name"] == "sub_mas-foo"
    assert stats["mode"] == "mas"
    assert "sub_mas-foo" in output.read_text()


def test_generate_yaml_generic_mode(engine, tmp_path):
    """generic mode → file is created WITHOUT sub_mas- prefix."""
    output = tmp_path / "out.yaml"
    stats = engine.generate_yaml(
        name="foo", emoji="🔧", task="Fix the bug",
        output=str(output), workspace=str(tmp_path), mode="generic"
    )
    assert stats["name"] == "foo"
    assert stats["mode"] == "generic"


def test_generate_yaml_with_best_practices(engine, tmp_path):
    """BP rules are embedded in the generated YAML instructions."""
    bp_dir = tmp_path / "mas-engineer" / ".mase"
    bp_dir.mkdir(parents=True)
    (bp_dir / "best-practices.yaml").write_text(
        "best_practices:\n"
        "  structure:\n"
        "    - rule: USE_VERSION_1_0_0\n"
        "  prompt:\n"
        "    - rule: SHORT_PROMPT\n"
    )
    output = tmp_path / "out.yaml"
    stats = engine.generate_yaml(
        name="foo", emoji="🔧", task="Fix bugs",
        output=str(output), workspace=str(tmp_path)
    )
    assert stats["bp_rules"] >= 2  # at least structure + prompt rules
    text = output.read_text()
    assert "USE_VERSION_1_0_0" in text
    assert "SHORT_PROMPT" in text


def test_generate_yaml_without_best_practices_uses_defaults(engine, tmp_path):
    """No BP file → default rule lines embedded."""
    output = tmp_path / "out.yaml"
    stats = engine.generate_yaml(
        name="foo", emoji="🔧", task="Fix bugs",
        output=str(output), workspace=str(tmp_path)
    )
    assert stats["bp_rules"] == 0
    text = output.read_text()
    # Default lines from impl when bp is empty
    assert "version: 1.0.0 in Frontmatter" in text
    assert "timeout: 600 = Sweet-Spot" in text
    assert "prompt unter 500 Zeichen" in text


def test_generate_yaml_with_auto_commit(engine, tmp_path):
    """auto_commit=True → auto-commit block in prompt."""
    output = tmp_path / "out.yaml"
    stats = engine.generate_yaml(
        name="foo", emoji="🔧", task="Fix bugs",
        output=str(output), workspace=str(tmp_path), auto_commit=True
    )
    text = output.read_text()
    assert "AUTO-COMMIT AKTIV" in text
    assert "git add -A && git commit" in text


def test_generate_yaml_without_auto_commit(engine, tmp_path):
    """auto_commit=False (default) → no auto-commit block."""
    output = tmp_path / "out.yaml"
    engine.generate_yaml(
        name="foo", emoji="🔧", task="Fix bugs",
        output=str(output), workspace=str(tmp_path)
    )
    text = output.read_text()
    assert "AUTO-COMMIT AKTIV" not in text


def test_generate_yaml_creates_output_directory(engine, tmp_path):
    """If output dir doesn't exist → it's created (parents=True)."""
    output = tmp_path / "deep" / "nested" / "out.yaml"
    engine.generate_yaml(
        name="foo", emoji="🔧", task="Fix",
        output=str(output), workspace=str(tmp_path)
    )
    assert output.exists()


def test_generate_yaml_yaml_is_valid(engine, tmp_path):
    """Generated file is parseable as YAML."""
    import yaml
    output = tmp_path / "out.yaml"
    engine.generate_yaml(
        name="foo", emoji="🔧", task="Fix bugs",
        output=str(output), workspace=str(tmp_path)
    )
    data = yaml.safe_load(output.read_text())
    assert data["version"] == "1.0.0"
    assert "prompt" in data
    assert "instructions" in data
    assert data["settings"]["timeout"] == 600


def test_generate_yaml_empty_task_uses_arbeiten(engine, tmp_path):
    """Empty task → scope falls back to 'arbeiten'."""
    output = tmp_path / "out.yaml"
    engine.generate_yaml(
        name="foo", emoji="🔧", task="",
        output=str(output), workspace=str(tmp_path)
    )
    text = output.read_text()
    assert "arbeiten" in text


def test_generate_yaml_scope_extracted_from_task(engine, tmp_path):
    """First word of task → scope."""
    output = tmp_path / "out.yaml"
    engine.generate_yaml(
        name="foo", emoji="🔧", task="Deploy the new service",
        output=str(output), workspace=str(tmp_path)
    )
    text = output.read_text()
    # scope = first word lowercase = "deploy"
    assert "deploy" in text


def test_generate_yaml_prompt_and_instructions_lengths(engine, tmp_path):
    """stats['prompt_len'] and ['instructions_len'] match actual file."""
    output = tmp_path / "out.yaml"
    stats = engine.generate_yaml(
        name="foo", emoji="🔧", task="Fix bugs",
        output=str(output), workspace=str(tmp_path)
    )
    # Re-read and check lengths
    import yaml
    data = yaml.safe_load(output.read_text())
    assert stats["prompt_len"] == len(data["prompt"])
    assert stats["instructions_len"] == len(data["instructions"])


# ─────────────────────────────────────────────────────────
# main() — CLI dispatch
# ─────────────────────────────────────────────────────────

def test_main_minimal_args(engine, tmp_path, capsys, monkeypatch):
    """Minimal --name + --task → generates YAML + prints summary."""
    output = tmp_path / "agent.yaml"
    monkeypatch.setattr(sys, "argv", [
        "dev_template_engine",
        "--name", "foo",
        "--task", "Fix",
        "--output", str(output),
        "--workspace", str(tmp_path),
    ])
    with mock.patch.object(sys, "exit") as mock_exit:
        engine.main()
    mock_exit.assert_not_called()  # No exit on success
    assert output.exists()
    captured = capsys.readouterr()
    assert "Agent creates:" in captured.out
    assert "sub_mas-foo" in captured.out


def test_main_json_output(engine, tmp_path, capsys, monkeypatch):
    """--json → output is JSON, not human summary."""
    output = tmp_path / "agent.yaml"
    monkeypatch.setattr(sys, "argv", [
        "dev_template_engine",
        "--name", "foo",
        "--task", "Fix",
        "--output", str(output),
        "--workspace", str(tmp_path),
        "--json",
    ])
    engine.main()
    captured = capsys.readouterr()
    # Output should be valid JSON
    stats = json.loads(captured.out)
    assert stats["name"] == "sub_mas-foo"
    assert "prompt_len" in stats


def test_main_registry_invokes_merge_tool(engine, tmp_path, monkeypatch):
    """--registry → subprocess.run called with merge_tool."""
    output = tmp_path / "agent.yaml"
    monkeypatch.setattr(sys, "argv", [
        "dev_template_engine",
        "--name", "foo",
        "--task", "Fix",
        "--output", str(output),
        "--workspace", str(tmp_path),
        "--registry", "/tmp/fake-registry.yaml",
    ])
    with mock.patch("subprocess.run") as m_run:
        engine.main()
    # subprocess.run called once (for registry merge)
    assert m_run.call_count == 1
    args = m_run.call_args[0][0]
    # argv: ['python3', merge_tool, '--findings', ..., '--registry', ...]
    assert "dev_registry_merge" in args[1]


def test_main_no_registry_skips_subprocess(engine, tmp_path, monkeypatch):
    """Without --registry → subprocess.run NOT called."""
    output = tmp_path / "agent.yaml"
    monkeypatch.setattr(sys, "argv", [
        "dev_template_engine",
        "--name", "foo",
        "--task", "Fix",
        "--output", str(output),
        "--workspace", str(tmp_path),
    ])
    with mock.patch("subprocess.run") as m_run:
        engine.main()
    assert m_run.call_count == 0


def test_main_default_emoji_is_wrench(engine, tmp_path, monkeypatch):
    """Default --emoji is wrench (🔧)."""
    output = tmp_path / "agent.yaml"
    monkeypatch.setattr(sys, "argv", [
        "dev_template_engine",
        "--name", "foo",
        "--task", "Fix",
        "--output", str(output),
        "--workspace", str(tmp_path),
    ])
    engine.main()
    import yaml
    data = yaml.safe_load(output.read_text())
    # Title should contain wrench emoji
    assert "🔧" in data["title"]


def test_main_invalid_mode_rejected(engine, tmp_path, monkeypatch):
    """Invalid --mode → argparse error + SystemExit(2)."""
    monkeypatch.setattr(sys, "argv", [
        "dev_template_engine",
        "--name", "foo",
        "--task", "Fix",
        "--mode", "invalid_mode",
    ])
    with pytest.raises(SystemExit) as exc_info:
        engine.main()
    # argparse exits with 2 on invalid choice
    assert exc_info.value.code == 2


def test_main_missing_required_name(engine, tmp_path, monkeypatch):
    """--name missing → argparse error + SystemExit(2)."""
    monkeypatch.setattr(sys, "argv", [
        "dev_template_engine",
        "--task", "Fix",
    ])
    with pytest.raises(SystemExit) as exc_info:
        engine.main()
    assert exc_info.value.code == 2


def test_main_with_project_arg_passed_to_subprocess(engine, tmp_path, monkeypatch):
    """--project → passed to subprocess via argv."""
    output = tmp_path / "agent.yaml"
    monkeypatch.setattr(sys, "argv", [
        "dev_template_engine",
        "--name", "foo",
        "--task", "Fix",
        "--output", str(output),
        "--workspace", str(tmp_path),
        "--registry", "/tmp/fake-registry.yaml",
        "--project", "my-custom-project",
    ])
    with mock.patch("subprocess.run") as m_run:
        engine.main()
    args = m_run.call_args[0][0]
    # argv includes --project my-custom-project
    assert "--project" in args
    assert "my-custom-project" in args
