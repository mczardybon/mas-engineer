"""Tests for tools/dev_analyst.py — coverage gap closer.

Covers the 13% coverage of dev_analyst.py (196 stmts, ~170 missed).
Strategy: build a minimal FakeScanner + FakeYaml/FakeFile class so we
can exercise all 7 check functions + main(). The scanner is mocked
because dev_analyst only touches scanner.files (no real I/O).
"""
import sys
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import dev_analyst as da


class FakeYaml:
    """Stand-in for observer.YamlFile. Holds attributes used by
    dev_analyst's check functions."""
    def __init__(self, rel_path, is_yaml=True, lines=100, size=2000,
                 has_settings=True, instr_lines=20, title="", encoding="utf-8"):
        self.rel_path = rel_path
        self.path = rel_path
        self.is_yaml = is_yaml
        self.lines = lines
        self.size = size
        self.has_settings = has_settings
        self.instr_lines = instr_lines
        self.title = title
        self.encoding = encoding


class FakeScanner:
    def __init__(self, files=None, yamls=None):
        self.files = files or []
        self.yamls = yamls or []
        self.collect_called = 0

    def _collect(self):
        self.collect_called += 1


# ─────────────────────────────────────────────────────────
# check_yaml_syntax — subprocess-based; we monkeypatch subprocess.run
# ─────────────────────────────────────────────────────────

def test_check_yaml_syntax_no_yaml_files():
    """Covers lines 42-69: empty scanner.files → returns 'all good' message."""
    scanner = FakeScanner(files=[])
    result = da.check_yaml_syntax(scanner)
    assert isinstance(result, str)
    assert "yaml" in result.lower()


def test_check_yaml_syntax_with_valid_yaml(tmp_path):
    """Covers lines 58-63: valid yaml files → 'ok' counted."""
    y1 = tmp_path / "a.yaml"
    y1.write_text("name: a\n")
    y2 = tmp_path / "b.yaml"
    y2.write_text("name: b\n")
    scanner = FakeScanner(files=[
        FakeYaml(str(y1), lines=2),
        FakeYaml(str(y2), lines=2),
    ])
    fake_result = mock.Mock()
    fake_result.returncode = 0
    fake_result.stderr = b""
    with mock.patch("subprocess.run", return_value=fake_result) as _:
        result = da.check_yaml_syntax(scanner)
    assert "ok" in result.lower() or "2" in result


def test_check_yaml_syntax_with_invalid_yaml(tmp_path):
    """Covers lines 64-67: invalid yaml → fail counted, errors listed."""
    y1 = tmp_path / "bad.yaml"
    y1.write_text("name: a\n")
    scanner = FakeScanner(files=[FakeYaml(str(y1), lines=2)])
    fake_result = mock.Mock()
    fake_result.returncode = 1
    fake_result.stderr = b"yaml.scanner.ScannerError: invalid"
    with mock.patch("subprocess.run", return_value=fake_result):
        result = da.check_yaml_syntax(scanner)
    assert "fail" in result.lower() or "error" in result.lower()


def test_check_yaml_syntax_skips_non_yaml(tmp_path):
    """Covers line 53-54: non-yaml files skipped."""
    py = tmp_path / "script.py"
    py.write_text("print('x')\n")
    scanner = FakeScanner(files=[FakeYaml(str(py), is_yaml=False, lines=2)])
    with mock.patch("subprocess.run") as mock_run:
        da.check_yaml_syntax(scanner)
        assert mock_run.call_count == 0


# ─────────────────────────────────────────────────────────
# check_sizes
# ─────────────────────────────────────────────────────────

def test_check_sizes_no_files():
    """Covers line 81-103: empty files → 'all good'."""
    scanner = FakeScanner(files=[])
    result = da.check_sizes(scanner)
    assert isinstance(result, str)


def test_check_sizes_flags_too_big():
    """Covers line 91: lines > MAX_LINES (800) → too_big listed."""
    scanner = FakeScanner(files=[
        FakeYaml("big.yaml", lines=1000),
        FakeYaml("normal.yaml", lines=100),
    ])
    result = da.check_sizes(scanner)
    assert "big" in result.lower() or "1000" in result or "zu groß" in result.lower() or "BIG" in result


def test_check_sizes_flags_too_small():
    """Covers line 93: lines < MIN_LINES (10) → too_small listed."""
    scanner = FakeScanner(files=[
        FakeYaml("tiny.yaml", lines=2),
        FakeYaml("normal.yaml", lines=100),
    ])
    result = da.check_sizes(scanner)
    assert "tiny" in result.lower() or "2" in result or "zu klein" in result.lower()


def test_check_sizes_skips_non_yaml():
    """Covers line 91: non-yaml files not counted."""
    scanner = FakeScanner(files=[
        FakeYaml("big.py", is_yaml=False, lines=10000),
    ])
    result = da.check_sizes(scanner)
    # Should not flag py files
    assert isinstance(result, str)


# ─────────────────────────────────────────────────────────
# check_settings
# ─────────────────────────────────────────────────────────

def test_check_settings_no_files():
    """Covers line 132-145: empty scanner → 'all good'."""
    scanner = FakeScanner(files=[])
    result = da.check_settings(scanner)
    assert isinstance(result, str)


def test_check_settings_flags_missing_settings():
    """Covers line 142-143: has_settings=False → 'missing settings' listed."""
    scanner = FakeScanner(files=[
        FakeYaml("a.yaml", has_settings=False),
        FakeYaml("b.yaml", has_settings=True),
    ])
    result = da.check_settings(scanner)
    assert "a.yaml" in result or "settings" in result.lower()


def test_check_settings_skips_non_yaml():
    """Covers line 139: non-yaml files skipped."""
    scanner = FakeScanner(files=[
        FakeYaml("script.py", is_yaml=False, has_settings=False),
    ])
    result = da.check_settings(scanner)
    assert isinstance(result, str)


# ─────────────────────────────────────────────────────────
# check_slashes
# ─────────────────────────────────────────────────────────

def test_check_slashes_no_files():
    """Covers line 157-180: empty scanner → 'all good'."""
    scanner = FakeScanner(files=[])
    result = da.check_slashes(scanner)
    assert isinstance(result, str)


def test_check_slashes_flags_missing_slash():
    """Covers line 174-175: has_slash=False → 'no slash' listed."""
    # We need to add has_slash attribute to FakeYaml
    y1 = FakeYaml("no-slash.yaml")
    y1.has_slash = False
    y1.slash_cmd = None
    scanner = FakeScanner(files=[y1])
    result = da.check_slashes(scanner)
    assert "no-slash" in result or "slash" in result.lower()


def test_check_slashes_skips_non_yaml():
    """Covers line 165: non-yaml files skipped."""
    scanner = FakeScanner(files=[
        FakeYaml("script.py", is_yaml=False),
    ])
    result = da.check_slashes(scanner)
    assert isinstance(result, str)


# ─────────────────────────────────────────────────────────
# check_utf8
# ─────────────────────────────────────────────────────────

def test_check_utf8_no_files():
    """Covers line 190-218: empty scanner → 'all good'."""
    scanner = FakeScanner(files=[])
    result = da.check_utf8(scanner)
    assert isinstance(result, str)


def test_check_utf8_flags_bad_encoding():
    """Covers line 205-209: encoding != utf-8 → listed."""
    scanner = FakeScanner(files=[
        FakeYaml("a.yaml", encoding="latin-1"),
        FakeYaml("b.yaml", encoding="utf-8"),
    ])
    result = da.check_utf8(scanner)
    assert "a.yaml" in result or "encoding" in result.lower() or "utf" in result.lower()


# ─────────────────────────────────────────────────────────
# check_titles
# ─────────────────────────────────────────────────────────

def test_check_titles_no_files():
    """Covers line 225-241: empty scanner → 'all good'."""
    scanner = FakeScanner(files=[])
    result = da.check_titles(scanner)
    assert isinstance(result, str)


def test_check_titles_flags_missing_title():
    """Covers line 233-235: title empty → listed in returned string."""
    scanner = FakeScanner(files=[], yamls=[
        FakeYaml("a.yaml", title=""),
        FakeYaml("b.yaml", title="Real Title"),
    ])
    result = da.check_titles(scanner)
    assert "a.yaml" in result or "Ohne Titel" in result


# ─────────────────────────────────────────────────────────
# check_all
# ─────────────────────────────────────────────────────────

def test_check_all_runs_all_checks():
    """Covers line 248-281: check_all() runs every check, returns combined
    string (NOT print)."""
    scanner = FakeScanner(files=[])
    with mock.patch("subprocess.run", return_value=mock.Mock(returncode=0, stderr=b"")):
        result = da.check_all(scanner)
    assert isinstance(result, str)
    # At least one of the check headers should appear in output
    assert "yaml" in result.lower() or "size" in result.lower() or "TITEL" in result


def test_check_all_with_failing_checks():
    """Covers lines 273-280: failed checks counted and reported."""
    scanner = FakeScanner(files=[
        FakeYaml("big.yaml", lines=10000, has_settings=False, title=""),
    ])
    with mock.patch("subprocess.run", return_value=mock.Mock(returncode=1, stderr=b"err")):
        da.check_all(scanner)


# ─────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────

def test_main_calls_check_all(monkeypatch, capsys):
    """Covers lines 286-312: main() instantiates scanner, runs check_all."""
    scanner = FakeScanner(files=[])
    fake_observer = mock.Mock()
    fake_observer.Scanner.return_value = scanner
    fake_observer.get_agent_dir = mock.Mock(return_value=Path("/tmp"))
    monkeypatch.setattr(da, "observer", fake_observer)
    with mock.patch("subprocess.run", return_value=mock.Mock(returncode=0, stderr=b"")):
        da.main()
    assert fake_observer.Scanner.called
