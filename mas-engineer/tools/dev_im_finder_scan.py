#!/usr/bin/env python3
"""Python-tool scanner wrapper — R110-411b script-mode.

This is the THIN CLI WRAPPER for the Python-tool portion of the
``dev_im_finder_scan`` feature set. It wraps the Python tool walker,
the ``check_*`` helpers, the orchestration try/except dispatch, the
summary printers, and the optional ``--publish`` block inside ``main()``
so that ``importlib.util.spec_from_file_location(...)`` is side-effect-free.

The YAML scanner (which is the larger half of the original file) lives in
``tools/dev_im_finder_scan_lib.py`` and is exposed via ``run_yaml_scan()``.

Usage:
    python3 tools/dev_im_finder_scan.py --scope=recipe
    python3 tools/dev_im_finder_scan.py --scope=all
    python3 tools/dev_im_finder_scan.py --scope=recipe --publish

For unit-testing the check_* helpers, import them from
``dev_im_finder_scan_lib`` (re-exported here for backward compatibility):
    from tools.dev_im_finder_scan import check_spec_drift, add_finding
"""

# Re-export the library so existing tests that do
# `mod = importlib.util.spec_from_file_location("dev_im_finder_scan", ...)`
# and then access ``mod.check_spec_drift``, ``mod.add_finding``,
# ``mod.findings``, ``mod.fid`` etc. keep working.
import glob
import os
import re
import sys
import json
import yaml
import time
import argparse
import importlib.util as _importlib_util
from pathlib import Path
from collections import Counter

_glob = glob
_os = os
_re = re
_sys = sys

_LIB_PATH = Path(__file__).parent / 'dev_im_finder_scan_lib.py'
_lib_spec = _importlib_util.spec_from_file_location('dev_im_finder_scan_lib', str(_LIB_PATH))
_lib_mod = _importlib_util.module_from_spec(_lib_spec)
sys.modules['dev_im_finder_scan_lib'] = _lib_mod
_lib_spec.loader.exec_module(_lib_mod)

from dev_im_finder_scan_lib import (
    SEVERITY_FILTER,
    _ISSUE_DB, _ISSUE_DB_ACTIVE, _ISSUE_DB_PATH, _ISSUE_DB_MOD,
    _issue_db_module, _issue_db_settings, _get_issue_db,
    compute_issue_hash, compute_structural_pattern,
    _collect_scope_dirs,
    SCAN_DIRS, ALL_YAMLS,
    EXCLUDED_DIR_NAMES, EXCLUDED_PATH_PATTERNS,
    _INCLUDE_EXTERNAL, _USER_EXPLICIT_SCOPE,
    _is_path_excluded,
    # NOTE: findings, fid, add_finding are intentionally NOT re-exported
    # via `from ... import ...` here. Doing so would create a separate
    # binding in this module's namespace, so that `mod.findings = []` in
    # test reset_state fixtures would reassign the CLI-side binding
    # without touching the LIB-side binding that ``add_finding`` writes to.
    #
    # Instead, we expose them as PROPERTIES that always look up the LIB
    # via sys.modules, so any test that does ``mod.findings = []`` ALSO
    # clears the LIB's list (test isolation works correctly).
    # R110-411b: extracted from CLI main() body so tests can access them
    # as ``mod.check_spec_drift`` etc. via spec_from_file_location.
    _is_pycache_or_backup,
    _is_self_reference,
    _is_common_value,
    _is_in_docstring,
    _is_in_code_block,
    _is_in_table_or_example,
    _is_runtime_var_assert,
    check_spec_drift,
    check_spec_drift_reverse,
    check_hardcode_stale,
    check_stale_literal,
    run_yaml_scan,
)


# --- R110-411b: sync CLI findings ↔ LIB findings for check_* funcs --------
# The check_* functions live in the LIB and call lib.add_finding() in their
# lexical scope, which appends to LIB's module-global `findings` list. Tests
# do ``mod.findings = []`` to reset state (CLI globals). For test assertions
# on ``mod.findings`` to work, we wrap the imported check_* functions to
# sync the findings list before AND after the call.
# This is a NO-OP in production (mod.findings and lib.findings are the
# same list object after the first sync).
def _wrap_check_with_sync(_func):
    import functools as _ft
    @_ft.wraps(_func)
    def wrapper(findings, *args, **kwargs):
        # Sync CLI's findings list → LIB's findings list
        if 'findings' in globals():
            _lib_mod.findings = globals()['findings']
        if 'fid' in globals():
            _lib_mod.fid = globals()['fid']
        result = _func(findings, *args, **kwargs)
        # Sync back: LIB's findings → CLI's findings
        globals()['findings'] = _lib_mod.findings
        globals()['fid'] = _lib_mod.fid
        return result
    return wrapper

check_spec_drift = _wrap_check_with_sync(check_spec_drift)
check_spec_drift_reverse = _wrap_check_with_sync(check_spec_drift_reverse)
check_hardcode_stale = _wrap_check_with_sync(check_hardcode_stale)
check_stale_literal = _wrap_check_with_sync(check_stale_literal)


# --- R110-411b: shared-state proxy via PEP 562 __getattr__
# The test fixture does ``mod.findings = []`` to reset scanner state
# between tests. In the pre-refactor monolithic file, this worked
# because ``findings`` was a module-level binding in the SAME module
# the test loaded. Now ``findings`` lives in the LIB.
#
# PEP 562 only supports __getattr__ for modules — module-level
# __setattr__ is NOT called by Python (modules always go through
# ModuleType.__setattr__ which sets __dict__ directly). So we cannot
# intercept ``mod.findings = []`` and forward it to the LIB.
#
# Workaround: define a thin wrapper ``add_finding`` that, on each
# call, synchronizes the LIB's findings list with whatever the CLI
# module's __dict__ holds. The test's ``mod.findings = []`` puts a
# fresh list in mod.__dict__, and the next add_finding() call will
# push that fresh list into the LIB. add_finding itself stays as a
# direct reference to lib.add_finding (so the test can verify
# ``callable(mod.add_finding)`` etc.).
_PROXIED_ATTRS = frozenset({
    'findings', 'fid', 'add_finding', 'SEVERITY_FILTER',
    '_ISSUE_DB', '_ISSUE_DB_ACTIVE', '_ISSUE_DB_PATH', '_ISSUE_DB_MOD',
    '_issue_db_module', '_issue_db_settings', '_get_issue_db',
    '_collect_scope_dirs', 'SCAN_DIRS', 'ALL_YAMLS',
    'EXCLUDED_DIR_NAMES', 'EXCLUDED_PATH_PATTERNS',
    '_INCLUDE_EXTERNAL', '_USER_EXPLICIT_SCOPE',
    '_is_path_excluded',
    'compute_issue_hash', 'compute_structural_pattern',
    '_is_pycache_or_backup',
    '_is_self_reference',
    '_is_common_value',
    '_is_in_docstring',
    '_is_in_code_block',
    '_is_in_table_or_example',
    '_is_runtime_var_assert',
    'check_spec_drift',
    'check_spec_drift_reverse',
    'check_hardcode_stale',
    'check_stale_literal',
    'run_yaml_scan',
    # R110-411b: SD regex/frozenset constants live in the LIB
    '_SD_STRING_IN_RE', '_SD_INT_EQ_RE', '_SD_INT_CMP_RE',
    '_SD_URL_RE', '_SD_WS_ONLY_RE',
    '_SD_ASSERT_RUNTIME_RE', '_SD_RUNTIME_CALL_RE',
    '_SD_RUNTIME_VARS', '_SD_RUNTIME_DICT_KEYS',
    '_SD_DATA_DIRS',
    '_RECIPE_NUMERIC_RE', '_RECIPE_CHECKS_RE', '_COUNT_ANCHOR_NEXT',
})


def __getattr__(name):
    """PEP 562 module-level __getattr__ — proxies attribute access to the LIB.

    For ``findings`` / ``fid`` we return whatever the CLI module's
    __dict__ holds (the test may have reassigned it), falling back to
    the LIB's value. This makes ``mod.findings = []`` work as expected:
    the new list is visible on subsequent ``mod.findings`` reads.
    """
    if name in _PROXIED_ATTRS:
        if name in ('findings', 'fid') and name in globals():
            # Test has reassigned this in CLI module's __dict__
            return globals()[name]
        return getattr(_lib_mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def add_finding(ftype, severity, file, issue, impact, fix,
                *, line_start=None, line_end=None, **pattern_kwargs):
    """Thin wrapper around lib.add_finding.

    Before delegating, sync the LIB's ``findings``/``fid``/``SEVERITY_FILTER``
    with whatever the CLI module's __dict__ holds. This makes the test's
    ``mod.findings = []`` / ``mod.SEVERITY_FILTER = {...}`` resets visible
    to the LIB (which otherwise would append to / filter against its own
    stale state).
    """
    if 'findings' in globals():
        _lib_mod.findings = globals()['findings']
    if 'fid' in globals():
        _lib_mod.fid = globals()['fid']
    if 'SEVERITY_FILTER' in globals():
        _lib_mod.SEVERITY_FILTER = globals()['SEVERITY_FILTER']
    result = _lib_mod.add_finding(
        ftype, severity, file, issue, impact, fix,
        line_start=line_start, line_end=line_end, **pattern_kwargs,
    )
    # Sync back so subsequent mod.findings / mod.fid reads see the update
    globals()['findings'] = _lib_mod.findings
    globals()['fid'] = _lib_mod.fid
    return result


def main():
    """R110-411b: entry point for the Python-tool scanner.

    Runs the YAML walker + dev_*.py/mcp_*.py walker, invokes all check_*
    helpers, prints the summary, and optionally enqueues findings via
    --publish.
    """

    # --- R110-411b: YAML walker (R110-78 + R110-112 + R110-124 etc.) -------
    # R110-411b moved the YAML walker out of `import`-side effects
    # (R110-362 lesson) and into run_yaml_scan() so it runs once per
    # invocation, behind the if __name__ guard at the bottom of the LIB.
    # The walker populates ALL_YAMLS and emits MM1-MM5, Q1-Q3, NN1-NN3,
    # E1, etc. findings. The CLI also calls it so that `python3 tools/
    # dev_im_finder_scan.py` reproduces the original behavior.
    run_yaml_scan()

    # --- Python tool scanner (R110-13): catches R110-10 bugs #2 and #3 ---
    # The YAML scanner above cannot see into .py files. R110-10 documented
    # 3 runtime-mode bugs; Q4 caught #1 (off-by-one path in recipe prompt).
    # Q4c catches #2 (data.json format drift) and Q4d catches #3
    # (confidence 0.95 hardcoded markers). Both walk tools/*.py directly.
    import glob as _glob
    PY_TOOLS = sorted(_glob.glob('tools/dev_*.py') + _glob.glob('tools/mcp_*.py'))
    for _pt in PY_TOOLS:
        try:
            with open(_pt) as _f:
                _src = _f.read()
        except Exception:
            continue

        # Q4c: data.json format drift (R110-10 bug #2)
        # Detects json.dump / json.dumps calls that omit explicit indent or
        # ensure_ascii. When the dashboard generator runs in PTY mode vs
        # --no-session mode, missing options lead to different file
        # layouts (e.g. compact on one side, pretty on the other). R110-10
        # saw exactly this: data.json was valid in both modes but
        # dashboard consumers misparsed because the format silently differed.
        # Only flag files that actually write to a dashboard/JSON output
        # path (contain 'data.json' or 'dashboards' string) — pure
        # logging/serialization tools are out of scope.
        #
        # R110-270 refinement: NDJSON writes (one JSON object per line,
        # written via `f.write(json.dumps(...))`) are intentionally compact
        # and do not need `indent` — but DO benefit from `ensure_ascii=False`
        # to keep file diffs stable across encodings. Skip files that are
        # clearly NDJSON writers (one json.dumps per write call, then
        # newline-appended) and require BOTH flags only for pretty-printed
        # multi-line JSON output.
        if ('data.json' in _src or 'dashboards' in _src) and 'json.dump' in _src:
            # Match each json.dump/dumps call individually (non-greedy to
            # stay inside one paren-group, even if call spans multiple lines).
            # Skip json.load (read-only, no mode-drift risk).
            _json_dumps = re.findall(
                r"json\.dump(?:s)?\s*\((?:[^()]|\n)*?\)", _src)
            for _call in _json_dumps:
                # R110-277: recursion guard — skip when the matched
                # `json.dumps(...)` substring is just a fragment of the
                # detector's own issue-message literals (lines 800, 805 etc.
                # contain "print(json.dumps(...))" inside the fix-text).
                # Heuristic: a real json.dump call has at least one
                # identifier / dict-literal / variable name between the
                # parens; an issue-message fragment has only "..." or
                # whitespace.
                _arg = _call.split('(', 1)[1].rstrip(')').strip()
                if not _arg or _arg in ('...',) or set(_arg) <= {' ', '.'}:
                    continue
                # Must contain BOTH indent and ensure_ascii to be mode-safe
                # for multi-line pretty output. NDJSON-only writers
                # (no indent expected) are still flagged if ensure_ascii is
                # missing, but only when the call is for an interactive
                # stdout/print path (heuristic: look for a 'print' wrapper
                # within +/- 2 lines of the call).
                # R110-271: for print(json.dumps(...)) (stdout output), only
                # ensure_ascii=False is required — indent=2 is not needed
                # for human-readable stdout (R110-270 design decision: kept
                # compact for grep-friendliness). For file-write, ensure_ascii
                # alone is still required.
                _has_indent = 'indent' in _call
                _has_ascii = 'ensure_ascii' in _call
                _is_print = bool(re.search(
                    r'print\s*\(\s*' + re.escape(_call[:20]),
                    _src))
                if _is_print and not _has_ascii:
                    add_finding('Q4c', 'medium', _pt,
                                f'data_json_drift: print json.dumps missing ensure_ascii: "{_call[:80].strip()}..."',
                                'Non-ASCII output may differ across encodings',
                                'Pass ensure_ascii=False to all print(json.dumps(...)) calls')
                elif not _is_print and not _has_ascii:
                    # NDJSON/file-write: only flag missing ensure_ascii
                    add_finding('Q4c', 'low', _pt,
                                f'data_json_drift: file-write json.dump missing ensure_ascii: "{_call[:80].strip()}..."',
                                'ensure_ascii=False keeps file diffs stable across encodings',
                                'Pass ensure_ascii=False to NDJSON/file-write json.dump calls')

        # Q4d: hardcoded confidence markers (R110-10 bug #3)
        # Detects numeric confidence values (0.X or 1.0) hardcoded in
        # pattern/secrets/regex definitions. When the scanner is invoked
        # from PTY mode vs --no-session mode, hardcoded values get logged
        # literally, but downstream consumers expect to read confidence
        # from session metadata. R110-10 found that 6+ secret-detection
        # patterns had hardcoded 0.95 values, and the discrepancy surfaced
        # as "log marker drift" between run modes.
        if 'confidence' in _src:
            # Simpler: count confidence-like values that appear inside
            # a 3-tuple position (after a quoted string, before another
            # quoted string). Format in PATTERNS dict is:
            #   (r"regex", "SEVERITY", 0.95, "py")
            # so we look for ", 0.X, " or ", 1.0, " patterns.
            # Bumped severity to 'medium' (was 'low' in first cut) because
            # R97 SEVERITY_FILTER = {medium, high} would otherwise hide
            # this finding, and the R110-10 confidence-drift bug
            # manifested as silent log misparse, not just style.
            _conf_hardcoded = re.findall(
                r",\s*(0\.\d+|1\.0)\s*,\s*[\"']", _src)
            if len(_conf_hardcoded) >= 3:
                add_finding('Q4d', 'medium', _pt,
                            f'confidence_marker_drift: {len(_conf_hardcoded)} hardcoded confidence values in pattern tuples',
                            'Log mode compares confidence by string match; hardcoded values differ between run modes',
                            'Read confidence from session metadata, not from pattern tuples')

    # --- SD: Spec-Drift detection (R110-78 PHASE 2, R110-105) ---
    # Detects test-files in tests/ that assert literals which no longer
    # appear anywhere in recipe/, tools/, or docs/ (R110-71 spec-drift
    # incident pattern). Emits SD-<test-basename>-<idx> findings.
    # Spec: .mase/directives/R110-78-spec-drift.md PHASE 2 (R110-83 sub-spec).
    _SD_STRING_IN_RE = re.compile(
        r'''assert\s+["']([^"']{4,80})["']\s+in\s+''')
    _SD_INT_EQ_RE = re.compile(
        r'''assert\s+\(?(\d+)\)?\s*==\s*[\w\.\(]''')
    _SD_INT_CMP_RE = re.compile(
        r'''assert\s+[\w\.\(\)]+\s*(?:==|!=|>|<|>=|<=)\s*(\d+)''')
    _SD_URL_RE = re.compile(r'https?://', re.IGNORECASE)
    _SD_WS_ONLY_RE = re.compile(r'^\s*$')

    # R110-279: regex to match `assert "LITERAL" in <RHS>` where RHS is a
    # captured/runtime value. The regex captures the literal (group 1) and
    # the RHS expression (group 2) so the skip-rule can decide whether the
    # RHS is a runtime-var (out, result, content, intake, capsys, ...) or
    # a static source literal (recipe, yaml, etc.). The optional `\s*\[...\]`
    # at the end handles subscript access like `rules["bp_autonomie"]`.
    # The pattern is NOT anchored to start-of-line because the assert
    # clause may follow a semicolon-separated assignment on the same line,
    # e.g. `captured = capsys.readouterr(); assert "x" in captured.out`.
    # Caller is responsible for `re.search` (not `re.match`).
    _SD_ASSERT_RUNTIME_RE = re.compile(
        r'''assert\s+["']([^"']{4,80})["']\s+in\s+'''
        r'''([a-zA-Z_][\w\.]*(?:\(\))?(?:\.[a-zA-Z_]\w*)*)\s*(?:\[[^\]]*\])?''')

    # R110-279: recognized runtime-variable names on the RHS of `in`. These
    # are captured in the test (capsys.readouterr().out, file.read_text(),
    # function return values, etc.). A literal asserted against a runtime
    # value is by definition not a static source-literal — it can only be
    # produced by the code under test. The drift detector's purpose is to
    # catch stale static literals; runtime-var asserts are a different
    # concern (the test itself will fail if the function regresses).
    _SD_RUNTIME_VARS = frozenset({
        'out', 'output', 'stdout', 'stderr', 'result', 'content',
        'captured', 'captured_output', 'intake', 'printed', 'printed_output',
        'response', 'rules', 'data', 'config', 'cli', 'cli_output',
        'tmp', 'tmpdir', 'tmp_path', 'tmpdir_str',
    })

    # R110-279: regex for common "captured-output" method calls on the RHS,
    # e.g. capsys.readouterr().out, result.stdout, CliRunner().invoke(...).output.
    # These are always runtime values regardless of the variable name.
    _SD_RUNTIME_CALL_RE = re.compile(
        r'''capsys\.readouterr\(\)\.(?:out|err)\b'''
        r'''|context\.(?:stdout|stderr)\b'''
        r'''|cli\.invoke\([^)]*\)\.output\b'''
        r'''|runner\.invoke\([^)]*\)\.output\b'''
        r'''|result\.(?:stdout|stderr|output)\b''')

    # R110-279: recognized subscript keys (e.g. rules["bp_autonomie"]) for
    # dict-of-rules / dict-of-config runtime vars. A literal in a runtime
    # dict access is still a runtime check, not static-source drift.
    _SD_RUNTIME_DICT_KEYS = frozenset({
        'rules', 'data', 'config', 'cfg', 'result', 'response', 'intake',
        'parsed', 'output', 'captured', 'output_data',
    })

    # --- R110-112 reverse-mode: detect recipe count-assertions not in tests/ ---
    # Targeted: only detect count-assertions like "N checks", "N tests",
    # "N critical X", "N rules" that are load-bearing spec-anchors (the
    # R110-111 L26 pattern). Descriptive numeric prose ("30 seconds",
    # "100 files") is NOT a count-assertion and is correctly skipped.
    _RECIPE_NUMERIC_RE = re.compile(r'\b(\d{2,})\s+(\w[\w-]*)')
    _RECIPE_CHECKS_RE = re.compile(r'(\d+)\s+(critical\s+)?checks?\b')
    _COUNT_ANCHOR_NEXT = {'check', 'checks', 'test', 'tests', 'assert',
                          'asserts', 'rule', 'rules', 'finding', 'findings',
                          'validator', 'validators'}


    # --- R110-124: Pattern A + B sister-functions -----------------------------
    # Wrap dev_self_audit detectors (producer) as scanner findings (consumer).
    # R02: scanner is consumer, self_audit is producer — do NOT duplicate the
    # detection logic; lazy-import the module and reuse PATTERN_A_RE /
    # PATTERN_A_ACCEPT_CTX / _is_in_fence / _strip_inline_code / _scan_pattern_b
    # / _build_repo_literal_index. See: .mase/directives/R110-124-scanner-pattern-ab.md

    # IDEMPOTENZ (spec section 7): grep-based check avoids re-inserting
    # check_spec_drift body if a previous run already wrote it.
    # (Unconditional call below is safe; function is module-scope and only
    # defined once per file.)
    try:
        check_spec_drift(findings, '.')
    except Exception as _sd_err:
        add_finding('SD-err', 'low', 'tools/dev_im_finder_scan.py',
                    f'spec_drift_check errored: {_sd_err}',
                    'SD findings may be incomplete', 'Inspect traceback')

    # R110-112: run reverse-mode check
    try:
        check_spec_drift_reverse(findings, '.')
    except Exception as _sd_rev_err:
        add_finding('SD-rev-err', 'low', 'tools/dev_im_finder_scan.py',
                    f'spec_drift_reverse_check errored: {_sd_rev_err}',
                    'SD-recipe findings may be incomplete', 'Inspect traceback')

    # R110-124: Pattern A + B drift detection
    try:
        check_hardcode_stale(findings, '.')
    except Exception as _ha_err:
        add_finding('HARDCODE-STALE-err', 'low',
                    'tools/dev_im_finder_scan.py',
                    f'hardcode_check errored: {_ha_err}',
                    'HARDCODE-STALE findings may be incomplete',
                    'Inspect traceback')
    try:
        check_stale_literal(findings, '.')
    except Exception as _sl_err:
        add_finding('STALE-LITERAL-err', 'low',
                    'tools/dev_im_finder_scan.py',
                    f'stale_literal_check errored: {_sl_err}',
                    'STALE-LITERAL findings may be incomplete',
                    'Inspect traceback')

    # --- Summary ---
    by_type = Counter(f['type'] for f in findings)
    by_sev = Counter(f['severity'] for f in findings)
    print(f'Total findings: {len(findings)}')
    print(f'By severity: {dict(by_sev)}')
    print(f'By type: {dict(sorted(by_type.items()))}')
    print(f'Types covered: {len(by_type)}/53+')

    # Output as JSON for processing
    # R110-276: ensure_ascii=False so non-ASCII findings survive the
    # round-trip to consumers (e2e-evidence archive, downstream scanners).
    print('---JSON_START---')
    print(json.dumps({'findings': findings, 'summary': {
        'total': len(findings),
        'by_type': dict(by_type),
        'by_severity': dict(by_sev)
    }}, indent=2, ensure_ascii=False))

    # --- R110-177 PHASE 2: persist issue-db (only when active) ---
    # ISSUE_DB summary goes to STDERR so the stdout JSON block stays
    # parseable (existing consumers split on ---JSON_START---).
    _issue_db = _get_issue_db()
    if _issue_db is not None:
        _issue_db.save()  # atomic write
        _sum = _issue_db._data['summary']
        print(f"ISSUE_DB: total={_sum['total_issues']} "
              f"open={_sum['by_status']['open']} "
              f"fixed={_sum['by_status']['fixed']} "
              f"wontfix={_sum['by_status']['wontfix']}", file=sys.stderr)

    # --- R110-165 phase 1.2: optional --publish to enqueue im.finding.created ---
    # Detect flag in sys.argv (we don't use argparse for backward compat).
    if any(a == '--publish' or a.startswith('--publish=') for a in sys.argv):
        _publish_topic = 'im.finding.created'
        _request_id = next(
            (a.split('=', 1)[1] for a in sys.argv
             if a.startswith('--publish-request-id=')),
            f'im-finder-{int(time.time())}'
        )
        _payload = {
            'request_id': _request_id,
            'source': 'dev_im_finder_scan',
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'findings_total': len(findings),
            'findings_by_severity': dict(by_sev),
            'findings_by_type': dict(by_type),
            # only ship the high+medium findings inline; low-severity are counted but not listed
            # (R110-191 fix: real finding keys are 'file'/'issue', not 'location'/'description' —
            #  ship both so consumers using either spec work; pre-existing since R110-165 266ceb7)
            'findings_top': [
                {k: f[k] for k in ('type', 'severity', 'file', 'issue')
                 if k in f} | {'location': f['file'], 'description': f['issue']}
                for f in findings
                if f.get('severity') in ('high', 'blocker')
            ][:20],
        }
        try:
            import subprocess as _sp
            _enq = _sp.run(
                ['python3', str(Path(__file__).resolve().parent / 'dev_message_queue.py'),
                 '--enqueue', _publish_topic, json.dumps(_payload),
                 '--idempotency-key', f'{_request_id}-im-finder',
                 '--request-id', _request_id],
                capture_output=True, text=True, timeout=30, cwd=Path(__file__).resolve().parent.parent,
            )
            _msg_id = (_enq.stdout or '').strip()
            if _enq.returncode != 0 or not _msg_id:
                print(f'[PUBLISH-ERROR] enqueue failed: exit={_enq.returncode} stderr={_enq.stderr.strip()}', file=sys.stderr)
            else:
                print(f'[PUBLISH-OK] {_publish_topic} msg_id={_msg_id}', file=sys.stderr)
        except Exception as _e:
            print(f'[PUBLISH-ERROR] {_e!r}', file=sys.stderr)

# --- R110-411b: script-mode guard (was: bare module-level block pre-R110-411b) ---
# Without this guard, `import dev_im_finder_scan` would walk
# tools/dev_*.py + tools/mcp_*.py at import-time, causing 30s+
# timeouts in test fixtures (R110-362 lesson). Now the walk is
# gated behind `python3 tools/dev_im_finder_scan.py ...`.
if __name__ == '__main__':
    main()
