"""Targeted coverage push for tools/dev_template_engine.py — R110-522.

Module: 160 lines, ~116 stmts, ~22 branches. Goal: 100% line+branch.

Strategy:
  - Cover pure functions directly (load_best_practices, extract_rules)
  - Cover generate_yaml with both empty-BP fallback paths
    (lines 62, 68, 74) and full-BP normal paths
  - Cover main() via runpy.run_path so coverage sees it
    (R110-521 lesson: subprocess loses coverage)
  - Cover the `if __name__ == "__main__"` guard by importing
    main() directly

Notes:
  - dev_template_generator.py is a DIFFERENT (940-LOC) module;
    this test file ONLY covers dev_template_engine.py.
  - module-level: line 5 has `import argparse, yaml, json, os, sys, datetime`
    AND line 6 has `import json` again — harmless duplicate.
"""
import json
import os
import runpy
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

import tools.dev_template_engine as tpl


REPO_ROOT = Path(__file__).parent.parent.resolve()


# ─── load_best_practices ─────────────────────────────────────────

def test_load_best_practices_nonexistent_returns_empty():
    """Covers line 17-22: bp_path doesn't exist → return {}."""
    assert tpl.load_best_practices("/nonexistent/path/abc") == {}


def test_load_best_practices_existing_file_loads_bp_section():
    """Covers line 18-21: bp_path exists → yaml.safe_load → return
    data['best_practices']."""
    with tempfile.TemporaryDirectory() as tmp:
        bp_dir = Path(tmp) / "mas-engineer" / ".mase"
        bp_dir.mkdir(parents=True)
        bp_file = bp_dir / "best-practices.yaml"
        bp_file.write_text(
            "best_practices:\n"
            "  structure:\n"
            "    - rule: rule-A\n"
            "    - rule: rule-B\n"
            "  settings:\n"
            "    - rule: setting-X\n"
        )
        bp = tpl.load_best_practices(tmp)
        assert bp == {
            "structure": [{"rule": "rule-A"}, {"rule": "rule-B"}],
            "settings": [{"rule": "setting-X"}],
        }


def test_load_best_practices_existing_file_no_best_practices_key():
    """Covers line 21 False branch: yaml loads but no 'best_practices'
    key → returns {}."""
    with tempfile.TemporaryDirectory() as tmp:
        bp_dir = Path(tmp) / "mas-engineer" / ".mase"
        bp_dir.mkdir(parents=True)
        bp_file = bp_dir / "best-practices.yaml"
        bp_file.write_text("other_key: 1\n")
        bp = tpl.load_best_practices(tmp)
        assert bp == {}


# ─── extract_rules ───────────────────────────────────────────────

def test_extract_rules_returns_rule_texts():
    """Covers line 24-26: list of dicts → list of rule strings."""
    bp = {"kategorie": [{"rule": "rule-A"}, {"rule": "rule-B"}, {"rule": "rule-C"}]}
    assert tpl.extract_rules(bp, "kategorie", 2) == ["rule-A", "rule-B"]


def test_extract_rules_missing_category_returns_empty():
    """Covers line 25 False branch: bp.get(kategorie, []) → []."""
    assert tpl.extract_rules({"other": [{"rule": "r"}]}, "missing", 3) == []


def test_extract_rules_missing_rule_key_returns_questionmark():
    """Covers line 26 False branch: dict has no 'rule' key → '?'."""
    bp = {"kategorie": [{"no_rule": "x"}, {"rule": "y"}]}
    assert tpl.extract_rules(bp, "kategorie", 2) == ["?", "y"]


def test_extract_rules_max_rules_zero():
    """Covers line 26: max_rules=0 → empty list."""
    bp = {"kategorie": [{"rule": "r1"}]}
    assert tpl.extract_rules(bp, "kategorie", 0) == []


# ─── generate_yaml ───────────────────────────────────────────────

def _make_workspace_with_bp(tmp: str, rules: dict) -> str:
    """Helper: write a best-practices.yaml into tmp/mas-engineer/.mase."""
    bp_dir = Path(tmp) / "mas-engineer" / ".mase"
    bp_dir.mkdir(parents=True, exist_ok=True)
    bp_file = bp_dir / "best-practices.yaml"
    lines = ["best_practices:"]
    for cat, rs in rules.items():
        lines.append(f"  {cat}:")
        for r in rs:
            lines.append(f"    - rule: {r}")
    bp_file.write_text("\n".join(lines) + "\n")
    return tmp


def test_generate_yaml_mas_mode_adds_sub_mas_prefix():
    """Covers line 30 True branch: mode='mas' → prefix='sub_mas-'."""
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "sub", "agent.yaml")
        result = tpl.generate_yaml("foo", "🔥", "do stuff", out, tmp, "mas", False)
        assert result["name"] == "sub_mas-foo"
        assert result["mode"] == "mas"


def test_generate_yaml_generic_mode_no_prefix():
    """Covers line 30 False branch: mode='generic' → prefix=''."""
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "sub", "agent.yaml")
        result = tpl.generate_yaml("foo", "🔥", "do stuff", out, tmp, "generic", False)
        assert result["name"] == "foo"
        assert result["mode"] == "generic"


def test_generate_yaml_with_bp_rules():
    """Covers line 34-36: struktur/settings/prompt lists populated from BP."""
    with tempfile.TemporaryDirectory() as tmp:
        _make_workspace_with_bp(tmp, {
            "structure": ["s1", "s2", "s3", "s4"],  # 4 rules, max=3
            "settings": ["set1", "set2", "set3"],    # 3 rules, max=2
            "prompt": ["p1", "p2"],                   # 2 rules, max=2
        })
        out = os.path.join(tmp, "sub", "agent.yaml")
        result = tpl.generate_yaml("foo", "🔥", "do stuff", out, tmp, "mas", False)
        assert result["bp_rules"] == 9  # 3 + 2 + 2 + 2 (the "no_rule" ones)
        # Verify file was written
        assert os.path.exists(out)
        # Read YAML back and verify keys
        with open(out) as f:
            data = yaml.safe_load(f)
        assert "version" in data
        assert "title" in data
        assert "description" in data
        assert "prompt" in data
        assert "instructions" in data
        assert "settings" in data
        assert data["settings"]["timeout"] == 600
        assert data["settings"]["max_turns"] == 100
        assert data["settings"]["goose_provider"] == "openai"


def test_generate_yaml_no_bp_uses_fallback_branches():
    """Covers lines 62, 68, 74 False branches: empty BP → fallback rules."""
    with tempfile.TemporaryDirectory() as tmp:
        # No best-practices.yaml at all
        out = os.path.join(tmp, "sub", "agent.yaml")
        result = tpl.generate_yaml("foo", "🔥", "do stuff", out, tmp, "mas", False)
        # Fallback rules are used → bp_rules=0
        assert result["bp_rules"] == 0
        with open(out) as f:
            data = yaml.safe_load(f)
        # Verify fallback rules appear in instructions
        assert "version: 1.0.0 in Frontmatter" in data["instructions"]
        assert "timeout: 600 = Sweet-Spot" in data["instructions"]
        assert "prompt unter 500 Zeichen" in data["instructions"]


def test_generate_yaml_with_auto_commit_appends_block():
    """Covers line 75-78 True branch: auto_commit=True → append to prompt."""
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "sub", "agent.yaml")
        result = tpl.generate_yaml("foo", "🔥", "do stuff", out, tmp, "mas", True)
        with open(out) as f:
            data = yaml.safe_load(f)
        assert "AUTO-COMMIT AKTIV" in data["prompt"]
        assert "[MAS]" in data["prompt"]


def test_generate_yaml_empty_task_uses_arbeiten_fallback():
    """Covers line 33 False branch: task.split() empty → scope='arbeiten'."""
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "sub", "agent.yaml")
        result = tpl.generate_yaml("foo", "🔥", "", out, tmp, "mas", False)
        with open(out) as f:
            data = yaml.safe_load(f)
        assert "arbeiten" in data["instructions"]


def test_generate_yaml_creates_parent_dirs():
    """Covers line 111: output_path.parent.mkdir(parents=True, exist_ok=True)."""
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "deep", "nested", "path", "agent.yaml")
        tpl.generate_yaml("foo", "🔥", "do stuff", out, tmp, "mas", False)
        assert os.path.exists(out)


def test_generate_yaml_scope_from_first_word():
    """Covers line 33 True branch: task.split()[0].lower() → scope."""
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "sub", "agent.yaml")
        result = tpl.generate_yaml("foo", "🔥", "Validate Everything", out, tmp, "mas", False)
        with open(out) as f:
            data = yaml.safe_load(f)
        assert "validate" in data["instructions"]


def test_generate_yaml_returns_all_stats_fields():
    """Covers line 118-127: return dict has all expected keys."""
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "sub", "agent.yaml")
        result = tpl.generate_yaml("foo", "🔥", "do stuff", out, tmp, "mas", False)
        expected = {"name", "emoji", "task", "prompt_len", "instructions_len",
                    "bp_rules", "output", "mode"}
        assert set(result.keys()) == expected


# ─── main() dispatch ─────────────────────────────────────────────

def _run_main_via_runpy(args, monkeypatch, *, registry=None):
    """Run dev_template_engine.main() in-process via runpy so coverage
    captures it (R110-521 lesson: subprocess loses coverage).

    monkeypatch required for sys.argv.
    """
    argv = ["dev_template_engine.py"] + list(args)
    monkeypatch.setattr(sys, "argv", argv)
    sys.modules.pop("tools.dev_template_engine", None)
    try:
        return runpy.run_module("tools.dev_template_engine", run_name="__main__")
    finally:
        # Re-import so subsequent tests that do `import tools.dev_template_engine`
        # (e.g. test_main_dunder_name_guard) find it in sys.modules.
        # Without this, runpy leaves only __main__ in sys.modules and the
        # original module name is gone until something else imports it.
        if "tools.dev_template_engine" not in sys.modules:
            import tools.dev_template_engine  # noqa: F401


def test_main_no_args_exits_via_parser(monkeypatch, capsys):
    """Covers line 141: parser.parse_args() with --name missing → SystemExit."""
    # argparse prints to stderr and exits 2 — no need to invoke main, parser
    # itself fails. We cover this by attempting the CLI through subprocess
    # since argparse error path is straightforward.
    res = subprocess.run(
        [sys.executable, "-m", "tools.dev_template_engine"],
        cwd=str(REPO_ROOT),
        capture_output=True, text=True, timeout=10,
    )
    assert res.returncode == 2
    assert "--name" in res.stderr


def test_main_with_required_args_writes_file(monkeypatch, capsys):
    """Covers line 143-157 (no --registry, no --json path): main()
    calls generate_yaml + prints stats."""
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "sub", "agent.yaml")
        monkeypatch.setattr(sys, "argv", [
            "dev_template_engine.py",
            "--name", "myagent",
            "--emoji", "🔥",
            "--task", "do cool stuff",
            "--output", out,
            "--workspace", tmp,
            "--mode", "mas",
        ])
        sys.modules.pop("tools.dev_template_engine", None)
        try:
            runpy.run_module("tools.dev_template_engine", run_name="__main__")
        finally:
            if "tools.dev_template_engine" not in sys.modules:
                import tools.dev_template_engine  # noqa: F401
        captured = capsys.readouterr()
        assert "Agent creates: sub_mas-myagent" in captured.out
        assert "file: " + out in captured.out
        assert os.path.exists(out)


def test_main_with_json_output(monkeypatch, capsys):
    """Covers line 150-151 True branch: --json → print json.dumps(stats)."""
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "sub", "agent.yaml")
        monkeypatch.setattr(sys, "argv", [
            "dev_template_engine.py",
            "--name", "jagent",
            "--emoji", "⚙",
            "--task", "do json task",
            "--output", out,
            "--workspace", tmp,
            "--mode", "generic",
            "--json",
        ])
        sys.modules.pop("tools.dev_template_engine", None)
        try:
            runpy.run_module("tools.dev_template_engine", run_name="__main__")
        finally:
            if "tools.dev_template_engine" not in sys.modules:
                import tools.dev_template_engine  # noqa: F401
        captured = capsys.readouterr()
        # Should be valid JSON
        data = json.loads(captured.out)
        assert data["name"] == "jagent"
        assert data["mode"] == "generic"


def test_main_with_registry_calls_merge_tool(monkeypatch, capsys, tmp_path):
    """Covers line 144-148 True branch: --registry set → subprocess to
    dev_registry_merge.py. We mock subprocess.run to avoid the actual
    merge."""
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "sub", "agent.yaml")
        reg = str(tmp_path / "reg.json")
        # Mock subprocess.run so merge_tool isn't actually invoked.
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: None)
        monkeypatch.setattr(sys, "argv", [
            "dev_template_engine.py",
            "--name", "regagent",
            "--emoji", "🛡",
            "--task", "reg task",
            "--output", out,
            "--workspace", tmp,
            "--registry", reg,
        ])
        sys.modules.pop("tools.dev_template_engine", None)
        try:
            runpy.run_module("tools.dev_template_engine", run_name="__main__")
        finally:
            if "tools.dev_template_engine" not in sys.modules:
                import tools.dev_template_engine  # noqa: F401
        # If we get here without error, the --registry branch executed.
        captured = capsys.readouterr()
        assert "Agent creates: sub_mas-regagent" in captured.out


def test_main_dunder_name_guard(tmp_path, monkeypatch):
    """Covers line 159-160: `if __name__ == '__main__'` guard.

    We invoke the file directly via runpy with __name__='__main__' which
    IS covered by the other main() tests. To cover the False branch
    (import path), we just import the module — already done at top of file.
    """
    # The False branch is covered by `import tools.dev_template_engine`
    # at module top — verify by re-importing.
    # R110-571: after the previous tests popped/re-imported tools.dev_template_engine,
    # the module object referenced by `tpl` (from the top-of-file import) may differ
    # from the one currently in sys.modules. Reload from sys.modules directly so we
    # exercise the live module that `import tools.dev_template_engine` would resolve to.
    tpl = sys.modules["tools.dev_template_engine"]
    import importlib
    importlib.reload(tpl)
    assert hasattr(tpl, "main")


def test_main_auto_commit_flag(monkeypatch, capsys):
    """Covers line 143 getattr path: getattr(args, 'auto_commit', False)
    with --auto-commit → True."""
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "sub", "agent.yaml")
        monkeypatch.setattr(sys, "argv", [
            "dev_template_engine.py",
            "--name", "acagent",
            "--emoji", "🚀",
            "--task", "auto commit task",
            "--output", out,
            "--workspace", tmp,
            "--mode", "mas",
            "--auto-commit",
        ])
        sys.modules.pop("tools.dev_template_engine", None)
        try:
            runpy.run_module("tools.dev_template_engine", run_name="__main__")
        finally:
            if "tools.dev_template_engine" not in sys.modules:
                import tools.dev_template_engine  # noqa: F401
        with open(out) as f:
            import yaml as _y
            data = _y.safe_load(f)
        assert "AUTO-COMMIT AKTIV" in data["prompt"]
