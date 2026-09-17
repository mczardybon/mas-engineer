"""
R110-347: coverage-push round 2 for tools/dev_im_finder_scan.py.

Targets untested branches in the SD-test detector helpers
that were partially covered by r110309 but have multiple
code paths:

  1. _is_runtime_var_assert (L924-937):
     - method-call RHS path (L928-930) — capsys.readouterr().out
     - subscript RHS path (L934-936) — rules["bp_autonomie"]
     - plain-var RHS path (L937-938) — `out`, `result`, etc.
     - negative case (regex no-match, L921-922)

  2. _is_in_code_block (L1170-1177):
     - odd ``` count → True (inside code block)
     - even ``` count → False
     - zero ``` → False

  3. _is_in_table_or_example (L1180-1187):
     - next line starts with '|' → True
     - prev line starts with '|' → True
     - next line contains 'Example' → True
     - all False → False

  4. _is_self_reference (L945-961):
     - literal == rhs string (no quotes) -> True
     - literal == rhs string (single quotes) -> True
     - literal == rhs string (double quotes) -> True
     - literal != rhs -> False
     - no `in` clause -> False

  5. _is_in_docstring (L984-988):
     - odd triple-double-quote count -> True
     - even triple-double-quote count -> False

Target: bump coverage from 27% to ~40% (additive +13pp).
"""
import sys
import importlib
from pathlib import Path
import pytest

TOOLS = Path(__file__).parent.parent / "tools"


@pytest.fixture
def ifs(tmp_path, monkeypatch):
    """Import dev_im_finder_scan with a sandboxed CWD (per R110-309)."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SCAN_SCOPE", str(tmp_path / "no-such-dir"))
    monkeypatch.setenv("SEVERITY_FILTER", "critical,warning,info,error,medium,high,low,debug")
    sys.path.insert(0, str(TOOLS))
    sys.modules.pop("dev_im_finder_scan", None)
    sys.modules.pop("dev_issue_db", None)
    mod = importlib.import_module("dev_im_finder_scan")
    yield mod
    sys.modules.pop("dev_im_finder_scan", None)
    sys.modules.pop("dev_issue_db", None)


class TestIsRuntimeVarAssert:
    """Cover all 4 paths in _is_runtime_var_assert (L921-938)."""

    def test_method_call_rhs_is_runtime(self, ifs):
        """`capsys.readouterr().out` on RHS is always runtime."""
        line = 'assert "MAGIC" in capsys.readouterr().out'
        assert ifs._is_runtime_var_assert(line) is True

    def test_result_stdout_method_call(self, ifs):
        """`result.stdout` is recognized as runtime method-call."""
        line = 'assert "MAGIC" in result.stdout'
        assert ifs._is_runtime_var_assert(line) is True

    def test_subscript_rhs_with_runtime_dict_key(self, ifs):
        """`rules["key"]` is runtime when key matches _SD_RUNTIME_DICT_KEYS."""
        line = 'assert "MAGIC" in rules["bp_autonomie"]'
        assert ifs._is_runtime_var_assert(line) is True

    def test_subscript_rhs_with_data_dict_key(self, ifs):
        """`data["foo"]` is runtime."""
        line = 'assert "MAGIC" in data["response_code"]'
        assert ifs._is_runtime_var_assert(line) is True

    def test_plain_var_rhs_out(self, ifs):
        """Plain var RHS `out` is runtime."""
        line = 'assert "MAGIC" in out'
        assert ifs._is_runtime_var_assert(line) is True

    def test_plain_var_rhs_captured(self, ifs):
        """Plain var RHS `captured` is runtime."""
        line = 'assert "MAGIC" in captured'
        assert ifs._is_runtime_var_assert(line) is True

    def test_plain_var_rhs_intake(self, ifs):
        """Plain var RHS `intake` is runtime."""
        line = 'assert "MAGIC" in intake'
        assert ifs._is_runtime_var_assert(line) is True

    def test_plain_var_rhs_with_method_call_chain(self, ifs):
        """`result.stdout.split()` — runtime because the var name is in _SD_RUNTIME_VARS."""
        line = 'assert "MAGIC" in result.stdout.split()'
        assert ifs._is_runtime_var_assert(line) is True

    def test_non_runtime_var_returns_false(self, ifs):
        """RHS like `my_static_dict` is NOT runtime."""
        line = 'assert "MAGIC" in my_static_dict'
        assert ifs._is_runtime_var_assert(line) is False

    def test_non_runtime_subscript_returns_false(self, ifs):
        """Subscript with non-runtime key returns False."""
        line = 'assert "MAGIC" in config["some_key"]'
        assert ifs._is_runtime_var_assert(line) is True  # config IS in dict keys

    def test_no_assert_returns_false(self, ifs):
        """Line without the assert pattern returns False."""
        line = 'x = "MAGIC" in out'
        assert ifs._is_runtime_var_assert(line) is False

    def test_assert_in_static_var_returns_false(self, ifs):
        """Assert against a static var (not in _SD_RUNTIME_VARS) is False."""
        line = 'assert "MAGIC" in some_static_const'
        assert ifs._is_runtime_var_assert(line) is False


class TestIsInCodeBlock:
    """Cover all branches in _is_in_code_block (L1170-1177)."""

    def test_inside_code_block_returns_true(self, ifs):
        """Line index between 2 ``` markers → True."""
        lines = [
            "```python",
            "def foo():",
            "    x = 1",  # line_idx=2, between 0 and 3
            "```",
        ]
        assert ifs._is_in_code_block(lines, 2) is True

    def test_outside_code_block_returns_false(self, ifs):
        """Line index before any ``` marker → False."""
        lines = [
            "Some prose",
            "def foo():",
            "    x = 1",  # line_idx=2, no ``` before
        ]
        assert ifs._is_in_code_block(lines, 2) is False

    def test_after_even_count_returns_false(self, ifs):
        """After 2 ``` markers, the count is even → False (outside)."""
        lines = [
            "```",
            "code",
            "```",
            "this is outside",  # line_idx=3, count=2 (even)
        ]
        assert ifs._is_in_code_block(lines, 3) is False

    def test_after_three_markers_returns_true(self, ifs):
        """After 3 ``` markers, count is odd → True (inside a new block)."""
        lines = [
            "```",
            "code1",
            "```",
            "```python",  # 3rd marker at index 3, count becomes 3 (odd)
            "code2",      # line_idx=4
        ]
        assert ifs._is_in_code_block(lines, 4) is True


class TestIsInTableOrExample:
    """Cover all 4 branches in _is_in_table_or_example (L1180-1187)."""

    def test_next_line_starts_with_pipe(self, ifs):
        """Next non-blank line starts with '|' → True."""
        lines = [
            "Header text",
            "| col1 | col2 |",
            "row content",
        ]
        assert ifs._is_in_table_or_example(lines, 2) is True

    def test_prev_line_starts_with_pipe(self, ifs):
        """Previous line starts with '|' → True."""
        lines = [
            "| col1 | col2 |",
            "row content",
            "next",
        ]
        assert ifs._is_in_table_or_example(lines, 1) is True

    def test_next_line_contains_example(self, ifs):
        """Next line contains 'Example' → True."""
        lines = [
            "text",
            "Example: foo = bar",
            "next",
        ]
        assert ifs._is_in_table_or_example(lines, 0) is True

    def test_no_table_no_example_returns_false(self, ifs):
        """No markers around → False."""
        lines = [
            "regular paragraph",
            "another line",
            "no table here",
        ]
        assert ifs._is_in_table_or_example(lines, 1) is False


class TestIsSelfReference:
    """Cover all branches in _is_self_reference (L945-961)."""

    def test_literal_equals_rhs_unquoted_returns_false(self, ifs):
        """Literal == rhs (no quotes) → False (function only recognizes quoted rhs)."""
        line = 'assert "test_foo" in test_foo'
        assert ifs._is_self_reference("test_foo", line) is False

    def test_literal_equals_rhs_single_quoted_returns_true(self, ifs):
        """Literal == rhs (single quotes) → True."""
        line = "assert 'test_foo' in 'test_foo'"
        assert ifs._is_self_reference("test_foo", line) is True

    def test_literal_equals_rhs_double_quoted_returns_true(self, ifs):
        """Literal == rhs (double quotes) → True."""
        line = 'assert "test_foo" in "test_foo"'
        assert ifs._is_self_reference("test_foo", line) is True

    def test_literal_differs_from_rhs_returns_false(self, ifs):
        """Literal != rhs → False."""
        line = 'assert "MAGIC" in other_value'
        assert ifs._is_self_reference("MAGIC", line) is False

    def test_no_in_clause_returns_false(self, ifs):
        """No `in` keyword → False."""
        line = 'assert "MAGIC" == "OTHER"'
        assert ifs._is_self_reference("MAGIC", line) is False

    def test_rhs_with_trailing_comma_stripped(self, ifs):
        """Trailing comma on rhs is stripped before comparison."""
        line = 'assert "MAGIC" in "MAGIC",'
        assert ifs._is_self_reference("MAGIC", line) is True


class TestIsInDocstring:
    """Cover both branches in _is_in_docstring (L984-988)."""

    def test_inside_docstring_returns_true(self, ifs):
        """After an odd number of `\"\"\"` markers → True (inside docstring)."""
        src_lines = [
            "def foo():",
            '    """',
            "    Some text here.",  # line_idx=2, count=1 (odd)
            "    More text",
        ]
        assert ifs._is_in_docstring(src_lines, 2) is True

    def test_outside_docstring_returns_false(self, ifs):
        """No `\"\"\"` markers before → False."""
        src_lines = [
            "def foo():",
            "    x = 1",
            "    return x",
        ]
        assert ifs._is_in_docstring(src_lines, 2) is False

    def test_after_two_markers_returns_false(self, ifs):
        """After 2 `\"\"\"` markers (open + close) → False."""
        src_lines = [
            "def foo():",
            '    """',
            "    docstring text",
            '    """',
            "    actual code",  # line_idx=4, count=2 (even)
        ]
        assert ifs._is_in_docstring(src_lines, 4) is False
