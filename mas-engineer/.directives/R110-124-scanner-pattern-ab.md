# R110-124 — dev_im_finder_scan.py: add HARDCODE-STALE + STALE-LITERAL detection (MM9-EXT scanner support)

## CONTEXT (R110-78 lesson consolidation: scanner must detect what self-audit detects)

R110-78 PHASE 3a (R110-118) implementierte sub_mas-self-audit
agent + dev_self_audit.py mit 3 patterns:
  - Pattern A: hardcoded counts (HARDCODE-*)
  - Pattern B: stale literals (STALE-LITERAL)
  - Pattern C: count-assertion drift (delegated to dev_spec_invariant.py)

PHASE 3b (R110-120) wired STEP 0.6 in sub_mas-im-finder.md so
that sub_mas-self-audit runs vor findings-write (catches drift
that pre-push Check 18 would later block).

**GAP:** The standalone scanner (tools/dev_im_finder_scan.py)
detects only YAML structure (MM1-MM9) + SD-* spec-drift. It does
NOT detect HARDCODE-STALE or STALE-LITERAL.

**Effect:** When user runs
`python3 tools/dev_im_finder_scan.py --scope=recipe/instructions/`
manually (or via dev_directive_applier.py pre-apply), it returns
"0 findings" — even when 20 HARDCODE + 6 STALE-LITERAL exist.

**R110-124 fixes this by adding 2 sister-functions to
dev_im_finder_scan.py that wrap dev_self_audit.py detectors.**
Scanner stays single source of truth for "what should be in
the recipe repo" — Pattern A/B become first-class scan
findings, not buried in sub_mas-self-audit agent only.

After R110-124:
- dev_im_finder_scan.py --scope=recipe/instructions/ emits:
  MM1-9 (YAML structure) + SD-* (test↔recipe drift) +
  HARDCODE-* (Pattern A) + STALE-LITERAL-* (Pattern B) +
  spec-invariants (Pattern C via dev_spec_invariant call)
- 3-layer defense simplified: pre-push Check 18 + im-finder
  STEP 0.6 + standalone scanner all detect same drift classes
- im-finder STEP 0.6 can SIMPLIFY (no longer needs 2 separate
  subprocess calls — scanner now covers them) — but KEEP both
  for redundancy (R02: defense in depth)

## DIREKTIVE 1: ADD check_hardcode_stale() to dev_im_finder_scan.py

Add new function after check_spec_drift_reverse() (after L922).
Import from dev_self_audit: PATTERN_A_RE, PATTERN_A_ACCEPT_CTX,
ScanPatternA logic.

```python
def check_hardcode_stale(findings, repo_root='.'):
    """R110-124: wrap dev_self_audit Pattern A (HARDCODE-* detection).

    Detects hardcoded counts (e.g. "18 checks", "112 sub-agents") in
    recipe/instructions/ that lack env-var/default/config context.
    Mirrors dev_self_audit._scan_pattern_a() but emits scanner findings.
    """
    # Import here to avoid circular import at module load.
    import importlib.util as _ilu
    _path = os.path.join(os.path.dirname(__file__) or '.',
                         'dev_self_audit.py')
    _spec = _ilu.spec_from_file_location('dev_self_audit', _path)
    _mod = _ilu.module_from_spec(_spec)
    try:
        _spec.loader.exec_module(_mod)
    except Exception as e:
        add_finding('HARDCODE-STALE-err', 'low',
                    'tools/dev_im_finder_scan.py',
                    f'pattern_a_import error: {e}',
                    'HARDCODE-STALE findings may be incomplete',
                    'Inspect traceback')
        return

    scope = os.path.join(repo_root, 'recipe', 'instructions')
    if not os.path.isdir(scope):
        return

    per_file_idx = {}
    for root, _, files in os.walk(scope):
        if _is_pycache_or_backup(root):
            continue
        for fn in sorted(files):
            if not fn.endswith('.md'):
                continue
            fp = os.path.join(root, fn)
            if _is_pycache_or_backup(fp):
                continue
            rel = os.path.relpath(fp, repo_root)
            try:
                with open(fp, errors='ignore') as fh:
                    lines = fh.readlines()
            except Exception:
                continue
            per_file_idx[rel] = 0
            for ln, line in enumerate(lines, start=1):
                stripped = line.lstrip()
                if stripped.startswith('#'):
                    continue
                if _is_in_fence(lines, ln - 1):
                    continue
                inline = _strip_inline_code_inline(line)
                for m in _mod.PATTERN_A_RE.finditer(inline):
                    if _mod.PATTERN_A_ACCEPT_CTX.search(inline):
                        continue
                    num, word = m.group(1), m.group(2)
                    per_file_idx[rel] += 1
                    add_finding(
                        f'HARDCODE-STALE-{per_file_idx[rel]:03d}',
                        'medium',
                        f'{rel}:{ln}',
                        f"hardcoded '{num} {word}' without env-var/"
                        f"default/config context",
                        f"Reference env var (e.g. IM_TOP_N), document "
                        f"'default {num}', or derive from source of truth.",
                        f"Run: grep -rn '{num} {word}' recipe/ ; if all "
                        f"matches lack env/default context: hardcode is "
                        f"stale (R110-78 spec-drift lesson).")
```

HINWEIS: `_is_in_fence`, `_strip_inline_code_inline`,
`_is_pycache_or_backup` müssen entweder importiert oder
lokal definiert werden. CHECK if dev_im_finder_scan.py
already has them (it has `_is_pycache_or_backup`, but fence
+ inline-code helpers may need to be ported from
dev_self_audit).

If porting fails: use minimal subset (skip fence+inline-code
filtering for v1, R02: doc as known limitation in commit
body, add follow-up R110-125 to fix).

## DIREKTIVE 2: ADD check_stale_literal() to dev_im_finder_scan.py

Add similar wrapper for Pattern B:

```python
def check_stale_literal(findings, repo_root='.'):
    """R110-124: wrap dev_self_audit Pattern B (STALE-LITERAL detection).

    Detects quoted literals in recipe/instructions/ that don't appear
    anywhere else in recipe/tools/docs/tests. Mirrors
    dev_self_audit._scan_pattern_b() but emits scanner findings.
    """
    # [same import dance as DIREKTIVE 1]
    scope = os.path.join(repo_root, 'recipe', 'instructions')
    if not os.path.isdir(scope):
        return

    # Build the repo-wide index (one-time cost).
    repo_index = _mod._build_repo_literal_index(
        Path(repo_root), Path(scope))

    per_file_idx = {}
    for root, _, files in os.walk(scope):
        if _is_pycache_or_backup(root):
            continue
        for fn in sorted(files):
            if not fn.endswith('.md'):
                continue
            fp = os.path.join(root, fn)
            rel = os.path.relpath(fp, repo_root)
            try:
                with open(fp, errors='ignore') as fh:
                    lines = fh.readlines()
            except Exception:
                continue
            file_stem = Path(fp).stem
            per_file_idx[rel] = 0
            # Use dev_self_audit._scan_pattern_b directly
            for f in _mod._scan_pattern_b(
                    lines, rel, repo_index, file_stem):
                per_file_idx[rel] += 1
                add_finding(
                    f'STALE-LITERAL-{per_file_idx[rel]:03d}',
                    'warn',
                    f'{rel}:{f.description.split(":")[1].split(":")[0]}',
                    f.description.replace(file_stem + ':', ''),
                    f.suggested_fix,
                    f"Pattern B (R110-78): literal {f.description!r} "
                    f"appears nowhere in repo.")
```

## DIREKTIVE 3: WIRE new functions in main flow

In the main flow (after `check_spec_drift_reverse` call, around
L922-925), add:

```python
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
```

## DIREKTIVE 4: ADD test in tests/test_sub_mas_im_finder.py

```python
def test_scanner_detects_hardcode_stale():
    """R110-124: scanner emits HARDCODE-STALE-* findings (Pattern A)."""
    import subprocess
    import json
    result = subprocess.run(
        ['python3', 'tools/dev_im_finder_scan.py',
         '--scope=recipe/instructions/'],
        capture_output=True, text=True, cwd='.')
    # Parse JSON output (after ---JSON_START---)
    out = result.stdout
    assert '---JSON_START---' in out
    j = out.split('---JSON_START---')[1]
    data = json.loads(j)
    types = {f['type'] for f in data['findings']}
    hardcode_findings = [t for t in types if t.startswith('HARDCODE-STALE')]
    assert len(hardcode_findings) >= 1, \
        f"scanner should emit >=1 HARDCODE-STALE-* finding, got: {types}"


def test_scanner_detects_stale_literal():
    """R110-124: scanner emits STALE-LITERAL-* findings (Pattern B)."""
    import subprocess
    import json
    result = subprocess.run(
        ['python3', 'tools/dev_im_finder_scan.py',
         '--scope=recipe/instructions/'],
        capture_output=True, text=True, cwd='.')
    out = result.stdout
    j = out.split('---JSON_START---')[1]
    data = json.loads(j)
    types = {f['type'] for f in data['findings']}
    stale_findings = [t for t in types if t.startswith('STALE-LITERAL')]
    assert len(stale_findings) >= 1, \
        f"scanner should emit >=1 STALE-LITERAL-* finding, got: {types}"
```

## DIREKTIVE 5: RE-RUN + VERIFY (R110-116 transparency)

After DIREKTIVE 1+2+3+4:

  1. dev_im_finder_scan.py --scope=recipe/instructions/:
     - Output should include HARDCODE-STALE-* AND STALE-LITERAL-*
       finding types
     - Counts: at minimum 1 each (recipe/instructions has known
       HARDCODE + STALE-LITERAL drifts)
  2. dev_self_audit.py --scope=recipe/instructions/:
     - Should still report 20 WARN (no regression)
  3. dev_spec_invariant: 0 BLOCKER
  4. pytest 1286+2=1288 PASS
  5. test_recipe_registry_consistency: 9/9 PASS
  6. R36 cost: archive today's entries if > $20 budget

## SCOPE

  - tools/dev_im_finder_scan.py (DIREKTIVE 1+2+3: 2 new
    functions + 2 try/except call sites in main)
  - tests/test_sub_mas_im_finder.py (DIREKTIVE 4: +2 tests)
  - .directives/STATUS.md (R110-124 entry)

## PRE-CONDITIONS

  - 6e8d280 (R110-123) auf origin/cleanup ✓
  - pytest 1286/1286 PASS ✓
  - dev_spec_invariant: 0 BLOCKER ✓
  - dev_self_audit: 20 WARN (0 STALE-LITERAL) ✓
  - cost 24h: < $20 budget (R36 unlock ggf.)

## ACCEPTANCE

  - dev_im_finder_scan.py --scope=recipe/instructions/ emits
    >=1 HARDCODE-STALE-* AND >=1 STALE-LITERAL-* finding
  - pytest 1286+2=1288 PASS
  - dev_spec_invariant: 0 BLOCKER (unchanged)
  - dev_self_audit: 20 WARN (unchanged)
  - 0 secrets
  - R04-block honest: if fence/inline-code helpers couldn't be
    imported and we used simplified subset, DOCUMENT the
    limitation in commit body + create R110-125 follow-up
  - 0 amend (R110-24 non-breaking)
  - dispatched via R110-117 mechanism

## 3 HOOK POINTS

1. PRE-APPLY: pre-apply hook (R36 unlock if needed)
2. POST-APPLY: post-apply hook (pytest + scan + registry check)
3. ERROR: rollback via git checkout (R36 if changes archive
   failed)

## IDEMPOTENZ

pre-apply 2nd returns `ok=false, reason=already applied`.

## TESTING (end-to-end via R110-117 dispatch)

```bash
# 0. R36 unlock (if cost-gate)
[archive today's entries if cost > $20]

# 1. pre-apply (fresh)
rm -f .state/directive_already_applied.json
python3 tools/dev_directive_applier.py --hook pre-apply \
  .directives/R110-124-scanner-pattern-ab.md

# 2. apply via R110-117 dispatch
set -a; . ./.env; set +a
export RECURSION_OVERRIDE=2
export MAS_TASK=DIRECTIVE_APPLY
export MAS_CONFIRM=yes
export MAS_APPROVE=y
echo "per directive .directives/R110-124-scanner-pattern-ab.md apply DIREKTIVE 1+2+3+4+5: add check_hardcode_stale() + check_stale_literal() sister-functions to dev_im_finder_scan.py (wrap dev_self_audit Pattern A+B), wire them in main flow, add 2 tests. Verify scanner emits >=1 HARDCODE-STALE-* AND >=1 STALE-LITERAL-* finding. If fence/inline-code helpers fail to import, use simplified subset + document limitation + create R110-125 follow-up. ack" | \
  timeout 600 goose run --with-builtin developer \
  --recipe recipe/sub/sub_mas-general-improver.yaml --no-session \
  > /tmp/r110124-improver.log 2>&1

# 3. verify
cd tools && python3 -m dev_im_finder_scan.py --scope=../recipe/instructions/ 2>&1 | grep -E "HARDCODE-STALE|STALE-LITERAL" | head -5
# Expected: >=1 HARDCODE-STALE-* AND >=1 STALE-LITERAL-*
cd .. && python3 -m pytest tests/ -q
# Expected: 1286+2=1288 PASS
python3 -m pytest tests/test_recipe_registry_consistency.py -q
# Expected: 9/9 PASS

# 4. dev_self_audit regression check
cd tools && python3 -m dev_self_audit --scope ../recipe/instructions --repo-root .. 2>&1 | tail -3
# Expected: 20 WARN (unchanged, no regression)

# 5. dev_spec_invariant regression check
python3 -m dev_spec_invariant --repo-root .. 2>&1 | tail -1
# Expected: 0 BLOCKER

# 6. post-apply
cd .. && python3 tools/dev_directive_applier.py --hook post-apply \
  .directives/R110-124-scanner-pattern-ab.md
```

## ANTI-PATTERNS

- NICHT skip the import dance (circular import risk: use
  importlib.util lazy import inside function body, NOT top-
  level import)
- NICHT duplicate Pattern A/B logic (wrap dev_self_audit
  functions, don't reimplement)
- NICHT remove existing check_spec_drift / check_spec_drift_
  reverse calls (R02: keep all, scanner is defense in depth)
- NICHT modify dev_self_audit.py (R02: scanner is consumer,
  self_audit is producer; backward compat matters)
- NICHT amend 6e8d280 (R110-123)
- NICHT skip verifying dev_self_audit: 20 WARN unchanged
  (regression check critical)
- NICHT skip R04-block honest: if subset (no fence/inline
  filtering) used, document + create R110-125
