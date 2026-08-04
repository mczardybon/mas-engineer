#!/usr/bin/env python3
"""Comprehensive IM-Finder scan — detects all 53+ feature types A-MM + NN.

IM-005 SCOPE-FIX (2026-07-22): The scan was previously hardcoded to
RECIPE_DIR='recipe' which meant user-installed demo teams in
/root/.config/goose/recipes/*/ were never analyzed. Now we accept
--scope (CLI arg) or the SCAN_SCOPE env var to extend coverage.
Default behavior is unchanged (backward-compatible).
"""
import yaml, os, glob, re, json, sys, argparse
from pathlib import Path
from collections import Counter

# --- SEVERITY FILTER (R28 + R97 fix) ---
# Default (R97): ONLY medium,high — suppress low-severity style findings
# (e.g. "session cleanup missing", "no retry logic" — best-practice opinions,
# not bugs). Set SEVERITY_FILTER=low,medium,high (or pass
# --severity-filter=low,medium,high) to see all findings.
SEVERITY_FILTER = {'medium', 'high'}
for _a in sys.argv[1:]:
    if _a.startswith('--severity-filter='):
        SEVERITY_FILTER = {s.strip() for s in _a.split('=', 1)[1].split(',') if s.strip()}
        break
_env_sev = os.environ.get('SEVERITY_FILTER')
if _env_sev:
    SEVERITY_FILTER = {s.strip() for s in _env_sev.split(',') if s.strip()}

# SCAN_SCOPE may be a single directory, a comma-separated list, or multiple
# --scope args.  Default = 'recipe' (backward compatible).
def _collect_scope_dirs():
    raw = []
    # 1. CLI arg
    for arg in sys.argv[1:]:
        if arg.startswith('--scope='):
            raw.append(arg.split('=', 1)[1])
    # 2. Env var
    env = os.environ.get('SCAN_SCOPE')
    if env:
        raw.append(env)
    # 3. Fallback
    if not raw:
        raw = ['recipe']
    # Split on comma for env, allow duplicates; de-dup
    dirs = []
    for r in raw:
        for d in r.split(','):
            d = d.strip()
            if d and d not in dirs:
                dirs.append(d)
    return dirs

SCAN_DIRS = _collect_scope_dirs()
ALL_YAMLS = []
# Directories to skip during scan (excluded by name match)
EXCLUDED_DIR_NAMES = {
    '.backups',          # mas-engineer auto-backups (R27 fix)
    '.git',              # version control
    'node_modules',      # dependencies
    '__pycache__',       # python bytecode
    'legacy',            # R84 fix: archived ORIGINAL files (20+ stale findings per scan)
    'demo-team',         # R84 fix: on-demand demo-team recipes (varianz, nicht framework-bug)
}
# Path patterns to skip (substring match on full path)
# R97 fix: external scope (/.config/goose/recipes/ — marketing/sales/translator
# demo teams) is HARD-EXCLUDED by default. These are on-demand generated demo
# teams with known generation variance — scanning them adds 277+ findings of
# noise. To scan them, pass --include-external-recipes (or set
# MAS_INCLUDE_EXTERNAL_RECIPES=1). --scope alone is NOT enough.
_INCLUDE_EXTERNAL = '--include-external-recipes' in sys.argv or os.environ.get('MAS_INCLUDE_EXTERNAL_RECIPES', '').lower() in ('1', 'true', 'yes')
_USER_EXPLICIT_SCOPE = len(SCAN_DIRS) > 1 or (len(SCAN_DIRS) == 1 and SCAN_DIRS[0] != 'recipe')
EXCLUDED_PATH_PATTERNS = [
    '/.config/goose/recipes/',  # external demo teams (R97: hard-excluded by default)
    '/.config/goose/sessions/', # goose runtime session data
    '/.config/goose/memory/',   # goose memory
    '/.config/goose/workspace/',# goose workspace
    '/.local/share/goose/',     # goose internal storage
    '-ORIGINAL.yaml',           # R84 fix: archival copies of split agents
    '.bak',                     # R80 fix: stale backup files
]

def _is_path_excluded(path):
    """Check if a path matches any exclusion pattern."""
    for pat in EXCLUDED_PATH_PATTERNS:
        if pat in path:
            # R97: external recipes only included with --include-external-recipes
            if pat == '/.config/goose/recipes/' and _INCLUDE_EXTERNAL:
                continue
            return True
    return False


for SCAN_DIR in SCAN_DIRS:
    if not os.path.isdir(SCAN_DIR):
        continue
    for root, dirs, files in os.walk(SCAN_DIR):
        # In-place filter: modify dirs list to skip excluded subdirs
        # (os.walk honors dirs[:] modifications)
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIR_NAMES]
        # Also skip if root path itself matches excluded pattern
        if _is_path_excluded(root + '/'):
            continue
        for f in files:
            if f.endswith('.yaml') or f.endswith('.yml'):
                full_path = os.path.join(root, f)
                if _is_path_excluded(full_path):
                    continue
                ALL_YAMLS.append(full_path)
# Also pick up top-level yamls in cwd (legacy)
for f in glob.glob('*.yaml') + glob.glob('*.yml'):
    if os.path.isfile(f) and f not in ALL_YAMLS:
        ALL_YAMLS.append(f)

findings = []
fid = 0

def add_finding(ftype, severity, file, issue, impact, fix):
    global fid
    # R28: respect SEVERITY_FILTER
    if severity not in SEVERITY_FILTER:
        return
    fid += 1
    findings.append({
        'id': f'F-{fid:03d}',
        'type': ftype,
        'severity': severity,
        'file': file,
        'issue': issue,
        'impact': impact,
        'fix': fix
    })

for yp in sorted(ALL_YAMLS):
    try:
        with open(yp) as f:
            data = yaml.safe_load(f)
    except Exception as e:
        add_finding('Q2', 'high', yp, f'YAML parse error: {e}',
                    'Cannot process this file', 'Fix YAML syntax')
        continue
    if data is None:
        continue

    fname = os.path.basename(yp)

    # --- MM: YAML Structure (9 types) ---
    top_keys = set(data.keys())
    if not top_keys & {'about', 'name', 'version'}:
        add_finding('MM1', 'medium', yp, f'top-level keys wrong: {top_keys}',
                    'Missing standard top-level keys', 'Add about/name/version')

    if 'prompt' not in data:
        add_finding('MM2', 'medium', yp, 'missing prompt: field',
                    'Agent has no prompt block', 'Add prompt: field')

    if 'instructions' not in data:
        add_finding('MM3', 'medium', yp, 'missing instructions: field',
                    'Agent has no instructions block', 'Add instructions: field')

    settings = data.get('settings', {})
    if settings:
        for req in ['temperature']:
            if req not in settings:
                add_finding('MM4', 'medium', yp,
                            f'settings missing required keys: [{req}]',
                            'Agent may use Goose defaults instead of optimized MAS values',
                            f'add missing settings: [{req}]')

    # P-F012-4: MM5 (constitution: missing) is a MAS-engineer convention, NOT a Goose-native field.
    # SKIP for sub-agents (they inherit master-constitution).
    # APPLY only for top-level orchestrators (dev-mas-engineer, im-*).
    is_sub_agent = 'sub' in fname or '/sub/' in str(yp)
    is_top_orchestrator = any(t in fname for t in ['dev-mas-engineer', 'im-'])
    if 'constitution' not in data and is_top_orchestrator and not is_sub_agent:
        add_finding('MM5', 'low', yp, 'constitution: missing',
                    'Agent may lack behavioral guardrails', 'Add constitution: field')

    if 'extensions' not in data and 'sub' in fname:
        add_finding('MM6', 'medium', yp,
                    'extensions: missing when sub-delegation may be needed',
                    'Agent cannot delegate to sub-agents', 'Add extensions: [summon]')

    desc = data.get('description', '')
    if not desc or desc.strip() in ['', 'description', 'TODO']:
        add_finding('MM7', 'low', yp, 'description: empty or placeholder',
                    'Agent purpose unclear', 'Add meaningful description')

    # --- MM8/MM9: I_AM identity / MODE-CHECK (MAS convention) ---
    # P-F012-5: SKIP templates and recovery (they get I_AM/MODE-CHECK at deploy time)
    prompt = data.get('prompt', '')
    is_template = '/template/' in str(yp) or '/recovery/' in str(yp)
    if prompt and not is_template:
        if len(prompt) > 30 and 'I_AM' not in prompt and 'I am' not in prompt:
            add_finding('MM8', 'low', yp,
                        'prompt: > 30 chars but no I_AM identity',
                        'Agent lacks clear role identity', 'Add I_AM identity to prompt')
        if ('I_AM' in prompt or 'I am' in prompt) and 'MODE-CHECK' not in prompt:
            add_finding('MM9', 'low', yp,
                        'prompt: contains I_AM but no MODE-CHECK',
                        'Agent may not detect operating mode', 'Add MODE-CHECK to prompt')

    # --- F: Prompt Block ---
    if prompt and 'MODE-CHECK' not in prompt:
        add_finding('F3', 'low', yp, 'prompt has no MODE-CHECK',
                    'Agent may not detect operating mode', 'Add MODE-CHECK to prompt')

    if prompt and 'I_AM' not in prompt and 'I am' not in prompt:
        add_finding('F4', 'low', yp, 'prompt has no I_AM identity',
                    'Agent may lack clear role definition', 'Add I_AM identity to prompt')

    # --- B: Prompt Engineering ---
    if prompt and len(prompt) > 300:
        add_finding('B2', 'low', yp, f'prompt > 300 chars ({len(prompt)})',
                    'Prompt may be too verbose', 'Shorten prompt to under 300 chars')

    if prompt and 'context' not in prompt.lower() and 'workspace' not in prompt.lower():
        add_finding('B3', 'low', yp, 'prompt missing context-info',
                    'Agent may lack operational context', 'Add context info to prompt')

    # --- A: Timeout/Steps Optimization ---
    timeout = settings.get('timeout', 0) if settings else 0
    max_steps = settings.get('max_steps', 0) if settings else 0

    if timeout and timeout < 60:
        add_finding('A1', 'medium', yp, f'timeout={timeout}s too low (< 60s)',
                    'Agent may timeout before completing tasks',
                    f'set timeout={min(timeout*2, 3600)}')
    if max_steps and max_steps < 10:
        add_finding('A2', 'medium', yp, f'max_steps={max_steps} too low (< 10)',
                    'Agent may run out of steps', f'set max_steps={max_steps+10}')
    if timeout == 0:
        add_finding('A5', 'medium', yp, 'timeout=0 (unlimited)',
                    'Goose has 5min default sub-agent timeout', 'Set explicit timeout')

    # --- G: Mode-Detection ---
    instructions = data.get('instructions', '')
    if instructions and 'mode' not in instructions.lower() and 'MODE' not in instructions:
        add_finding('G2', 'low', yp,
                    'mode detection logic may be missing from instructions',
                    'Agent may not adapt to different modes',
                    'Add mode detection to instructions')

    # --- H: Constitution Reference ---
    if 'constitution' not in data:
        add_finding('H1', 'low', yp,
                    'missing R01-R18 reference (no constitution)',
                    'Agent lacks rule framework', 'Add constitution with R01-R18')

    # --- Q: YAML Schema Violations ---
    for req in ['name', 'version', 'description']:
        if req not in data:
            add_finding('Q1', 'medium', yp, f'missing required field: {req}',
                        'YAML schema incomplete', f'Add {req} field')

    known_fields = {'about', 'name', 'version', 'description', 'instructions',
                    'prompt', 'extensions', 'settings', 'constitution',
                    'parameters', 'tools', 'triggers', 'metadata', 'tags', 'category'}
    unknown = top_keys - known_fields
    if unknown:
        add_finding('Q3', 'low', yp,
                    f'extra/unknown fields: {", ".join(sorted(unknown))}',
                    'Non-standard fields may not be processed',
                    'Remove or rename unknown fields')

    # Q4: schema drift between similar recipes (R110-12)
    # Detects when recipes in the same category have inconsistent
    # instruction-path styles (inline vs external recipe/instructions/xxx.md)
    # or inconsistent extension-include patterns. This catches the off-by-one
    # path bug (R110-10): some recipes reference "recipe/instructions/x.md"
    # while others have inline "instructions: '# ...'", so the same recipe
    # run with different CWD ends up writing to different paths.
    instructions = data.get('instructions', '')
    if instructions:
        _has_external_ref = bool(re.search(
            r"#\s*Extended instructions:\s*([^\s'\"]+\.md)", str(instructions)))
        _has_inline = instructions.lstrip().startswith('#') and not _has_external_ref
        # Extract path style if external
        _m = re.search(r"#\s*Extended instructions:\s*([^\s'\"]+\.md)", str(instructions))
        _ext_path = _m.group(1) if _m else None
        # Check if path starts with 'recipe/' or is bare (off-by-one)
        if _ext_path and not _ext_path.startswith('recipe/'):
            add_finding('Q4', 'high', yp,
                        f'schema_drift: external instruction path "{_ext_path}" missing "recipe/" prefix (off-by-one risk)',
                        'Different CWD may write to wrong directory at runtime',
                        'Update path to "recipe/' + _ext_path + '"')

    # Q4b: STEP-N off-by-one path in prompt (R110-12, R110-10 bug #1)
    # Recipes that say "Create instructions/ folder" without the
    # "recipe/" prefix cause runtime off-by-one writes when the agent's
    # CWD is the project root (e.g. /tmp/multi-arch-30) instead of the
    # recipe directory. This was the R110-10 bug: 30agents recipe said
    # "STEP 4 — Create instructions/ folder" and the files landed in
    # /tmp/multi-arch-30/instructions/ instead of
    # /tmp/multi-arch-30/recipe/instructions/.
    prompt = data.get('prompt', '')
    if prompt:
        # Look for STEP-N lines that say "Create <bare-path>/" or
        # "Create folder <bare-path>" where the path does NOT start
        # with "recipe/" (would be correct).
        _offbyone_steps = re.findall(
            r"STEP\s+\d+\s*[—\-]\s*Create\s+([a-z_]+/)",
            str(prompt), flags=re.IGNORECASE
        )
        for _step_path in _offbyone_steps:
            if _step_path.rstrip('/') not in ('recipe', 'tests', 'tools', 'workflows'):
                add_finding('Q4', 'high', yp,
                            f'schema_drift: STEP creates folder "{_step_path}" without "recipe/" prefix (off-by-one risk)',
                            f'Runtime writes land in wrong directory (e.g. /tmp/proj/{_step_path} instead of /tmp/proj/recipe/{_step_path})',
                            f'Update to "Create recipe/{_step_path}"')

    # --- JJ: Extensions ---
    # P-F012-2: only fire JJ1 if extensions: is present AND not empty AND missing summon
    # SKIP files where extensions: is absent (templates, one-off recipes, recovery)
    if 'extensions' in data:
        extensions = data.get('extensions', [])
        if isinstance(extensions, list) and len(extensions) > 0:
            # summon can be either string 'summon' or dict with name='summon'
            has_summon = any(
                e == 'summon' or (isinstance(e, dict) and e.get('name') == 'summon')
                for e in extensions
            )
            if not has_summon:
                add_finding('JJ1', 'medium', yp,
                            "extensions: list missing summon (sub-agents can't be summoned)",
                            'Agent cannot delegate to sub-agents', 'Add summon to extensions')

    # --- T: Template Variables ---
    if instructions:
        hardcoded_paths = re.findall(r'/tmp/[^\s\"\'\)]+', instructions)
        if hardcoded_paths:
            add_finding('T1', 'low', yp,
                        f'hardcoded path(s): {hardcoded_paths}',
                        'Hardcoded paths may not exist on all systems',
                        'Use {workspace} variable instead')

    # --- C: Instructions Quality ---
    if instructions:
        if '⛔' not in instructions:
            add_finding('C1', 'low', yp,
                        'missing ⛔ prohibition markers in instructions',
                        'Critical steps may not be enforced',
                        'Add ⛔ markers before critical steps')
        if 'STEP' not in instructions and 'step' not in instructions.lower():
            add_finding('C2', 'low', yp,
                        'steps not numbered',
                        'Agent may skip critical phases',
                        'Add numbered STEPs to instructions')
        outdated = re.findall(r'/tmp/[^\s\"\'\)]+', instructions)
        if outdated:
            add_finding('C4', 'low', yp,
                        f'outdated path reference: {outdated}',
                        'Hardcoded /tmp/ path may not exist',
                        'Replace with {{workspace}} variable')

    # --- K: Error Handling ---
    if instructions:
        if 'try' not in instructions.lower() and 'except' not in instructions.lower():
            add_finding('K1', 'low', yp,
                        'missing try/except in instructions',
                        'Errors may go unhandled', 'Add error handling steps')
        if 'retry' not in instructions.lower():
            add_finding('K3', 'low', yp,
                        'no retry on transient errors',
                        'Transient failures may abort the agent',
                        'Add retry logic')

    # --- L: Session Management ---
    if instructions:
        if 'cleanup' not in instructions.lower() and 'clean' not in instructions.lower():
            add_finding('L1', 'low', yp,
                        'session cleanup missing from instructions',
                        'Temporary files may accumulate', 'Add cleanup step')
        if 'log' not in instructions.lower():
            add_finding('L2', 'low', yp,
                        'log rotation missing from instructions',
                        'Logs may grow unbounded', 'Add log management')

    # --- N: Delegation Logic ---
    # P-F012-3: N2 only fires for ACTIVE sub-agents in recipe/sub/, not templates/recovery
    if 'sub' in fname and isinstance(extensions, list):
        # P-F012-3 GUARD: only fire if extensions: is present AND non-empty AND missing summon
        if 'extensions' in data and len(extensions) > 0:
            has_summon = any(
                e == 'summon' or (isinstance(e, dict) and e.get('name') == 'summon')
                for e in extensions
            )
            if not has_summon:
                add_finding('N2', 'medium', yp,
                            'missing delegation capability (no summon)',
                            'Agent cannot delegate to sub-agents',
                            'Add summon to extensions')

    # --- O: Output Schema ---
    if instructions and 'output' not in instructions.lower() and 'return' not in instructions.lower():
        add_finding('O1', 'low', yp,
                    'output schema missing from instructions',
                    'Agent output format undefined',
                    'Define output schema in instructions')

    # --- U: Undo/Rollback ---
    if instructions:
        if 'undo' not in instructions.lower() and 'rollback' not in instructions.lower():
            add_finding('U1', 'low', yp,
                        'change not undoable (no rollback in instructions)',
                        'Changes may be irreversible', 'Add rollback instructions')

    # --- V: Validation Hooks ---
    if instructions:
        if 'valid' not in instructions.lower() and 'check' not in instructions.lower():
            add_finding('V1', 'low', yp,
                        'no pre-apply check in instructions',
                        'Changes may be applied without validation',
                        'Add validation step')

    # --- Y: Yield/Performance ---
    if instructions and 'loop' in instructions.lower() and 'batch' not in instructions.lower():
        add_finding('Y1', 'low', yp,
                    'possible O(n²) loop without batching',
                    'Performance may degrade with scale',
                    'Add batch processing')

    # --- BB: Boundaries ---
    if instructions and '⛔' not in instructions:
        add_finding('BB1', 'low', yp,
                    'missing ⛔ prohibition list',
                    'Agent may overstep boundaries',
                    'Add ⛔ prohibition markers')

    # --- II: I/O Format ---
    if instructions and 'format' not in instructions.lower() and 'schema' not in instructions.lower():
        add_finding('II1', 'low', yp,
                    'format mismatch risk (no format/schema in instructions)',
                    'Producer/consumer may disagree on format',
                    'Specify I/O format in instructions')

# --- D: Orchestrator Recipe (dev-mas-engineer.yaml) ---
dev_path = 'recipe/dev-mas-engineer.yaml'
if os.path.exists(dev_path):
    with open(dev_path) as f:
        dev_data = yaml.safe_load(f)
    dev_instructions = dev_data.get('instructions', '')
    if dev_instructions:
        if 'MODE-CHECK' not in dev_instructions and 'STEP 0' not in dev_instructions:
            add_finding('D1', 'medium', dev_path,
                        'missing STEP 0 (MODE-CHECK)',
                        'Orchestrator may not detect operating mode',
                        'Add STEP 0 MODE-CHECK')
        if 'STEP' not in dev_instructions:
            add_finding('D3', 'medium', dev_path,
                        'missing step entirely (no numbered STEPs)',
                        'Orchestrator may skip critical phases',
                        'Add numbered STEPs')

# --- E: Intention-Parser Patterns ---
ip_path = 'recipe/sub/sub_mas-intention-parser.yaml'
if os.path.exists(ip_path):
    with open(ip_path) as f:
        ip_data = yaml.safe_load(f)
    ip_instructions = ip_data.get('instructions', '')
    if ip_instructions and 'pattern' not in ip_instructions.lower():
        add_finding('E1', 'medium', ip_path,
                    'missing pattern in intention-parser',
                    'Intention parser cannot detect patterns',
                    'Add pattern definitions')

# --- NN: Agent Architecture (Split-Detection) ---
for yp in ALL_YAMLS:
    try:
        with open(yp) as f:
            data = yaml.safe_load(f)
    except:
        continue
    if data is None:
        continue
    prompt = data.get('prompt', '') or ''
    instructions = data.get('instructions', '') or ''
    combined = prompt + ' ' + instructions
    role_verbs = ['analyze', 'validate', 'generate', 'monitor', 'dispatch',
                  'repair', 'audit', 'report', 'scan', 'design', 'rank',
                  'find', 'read', 'write', 'edit', 'deploy', 'test', 'build',
                  'configure', 'manage']
    found_roles = [v for v in role_verbs if v in combined.lower()]
    # Skip if already split (check skip_recently_split.yaml)
    _skip_path = Path('.state/pipeline/skip_recently_split.yaml')
    if _skip_path.exists():
        with open(_skip_path) as _sf:
            _skip_data = yaml.safe_load(_sf) or {}
        _skip_list = _skip_data.get('skip_list', {})
        _agent_name = Path(yp).stem  # e.g. sub_mas-foo
        if _agent_name in _skip_list:
            _skip_round = _skip_list[_agent_name].get('last_split_round', 0)
            _round_count = int(os.environ.get('IM_ROUND_COUNT', '99'))
            if _round_count - _skip_round < 5:
                continue  # recently split, skip
    # R98 fix (IM-007): skip micro-agents (<60 lines) — they are split sub-agents
    # by design. NN1's "5+ role-verbs" pattern is normal for small focused agents
    # that handle a few related operations. Only flag actual orchestrators that
    # haven't been split. Filtered 23/31 false positives in R98 analysis.
    try:
        _line_count = sum(1 for _ in open(yp))
    except Exception:
        _line_count = 999
    if _line_count < 60:
        continue
    if len(found_roles) >= 5:
        add_finding('NN1', 'medium', yp,
                    f'multi_role_agent: {len(found_roles)} distinct roles ({found_roles[:5]})',
                    'Agent may violate single-responsibility principle',
                    'Consider splitting into orchestrator + sub-agents')

    # NN2: tool_overload
    extensions = data.get('extensions', [])
    if isinstance(extensions, list) and len(extensions) >= 5:
        add_finding('NN2', 'medium', yp,
                    f'tool_overload: {len(extensions)} extensions declared',
                    'Too many tools may confuse the agent',
                    'Distribute tools across specialized sub-agents')

    # NN3: scope_bloat
    desc = data.get('description', '')
    if desc and len(desc) > 200:
        domains = ['config', 'recipe', 'yaml', 'code', 'test', 'deploy',
                   'monitor', 'report', 'audit', 'security', 'pipeline',
                   'session', 'recovery', 'knowledge', 'dispatch']
        found_domains = [d for d in domains if d in desc.lower()]
        if len(found_domains) >= 3:
            add_finding('NN3', 'medium', yp,
                        f'scope_bloat: description > 200 chars with {len(found_domains)} domains ({found_domains[:3]})',
                        'Agent scope too broad',
                        'Split into domain-specific sub-agents')

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
    if ('data.json' in _src or 'dashboards' in _src) and 'json.dump' in _src:
        # Match each json.dump/dumps call individually (non-greedy to
        # stay inside one paren-group, even if call spans multiple lines).
        # Skip json.load (read-only, no mode-drift risk).
        _json_dumps = re.findall(
            r"json\.dump(?:s)?\s*\((?:[^()]|\n)*?\)", _src)
        for _call in _json_dumps:
            # Must contain BOTH indent and ensure_ascii to be mode-safe
            _has_indent = 'indent' in _call
            _has_ascii = 'ensure_ascii' in _call
            if not (_has_indent and _has_ascii):
                add_finding('Q4c', 'medium', _pt,
                            f'data_json_drift: json.dump missing indent/ensure_ascii: "{_call[:80].strip()}..."',
                            'Different run modes may produce different on-disk JSON layouts',
                            'Pass indent=2 and ensure_ascii=False to all json.dump calls')

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
# Spec: .directives/R110-78-spec-drift.md PHASE 2 (R110-83 sub-spec).
_SD_STRING_IN_RE = re.compile(
    r'''assert\s+["']([^"']{4,80})["']\s+in\s+''')
_SD_INT_EQ_RE = re.compile(
    r'''assert\s+\(?(\d+)\)?\s*==\s*[\w\.\(]''')
_SD_INT_CMP_RE = re.compile(
    r'''assert\s+[\w\.\(\)]+\s*(?:==|!=|>|<|>=|<=)\s*(\d+)''')
_SD_URL_RE = re.compile(r'https?://', re.IGNORECASE)
_SD_WS_ONLY_RE = re.compile(r'^\s*$')

def _is_pycache_or_backup(path: str) -> bool:
    return ('__pycache__' in path or path.endswith('.pyc')
            or '/llm-backup/' in path)

def _is_self_reference(literal: str, line: str) -> bool:
    # Heuristic: a true self-reference is when the assert checks a literal
    # against itself (e.g. assert "test_foo" in __name__ — the literal
    # IS the container). Pattern: extract the container (right of `in`)
    # and skip if it equals the literal.
    # Simpler: skip if literal is identical to the right-side of `in`.
    m = re.search(r'''in\s+(.+)$''', line)
    if m:
        rhs = m.group(1).strip().rstrip(',').strip()
        # strip quotes if present
        if (rhs.startswith('"') and rhs.endswith('"')) or \
           (rhs.startswith("'") and rhs.endswith("'")):
            rhs_inner = rhs[1:-1]
            if rhs_inner == literal:
                return True
    return False

def _is_common_value(literal: str, search_dirs) -> bool:
    # If a literal matches in 3+ files anywhere, treat as common value
    # (prevents "True", "False", etc. from triggering SD).
    hits = 0
    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        for root, _, files in os.walk(d):
            if _is_pycache_or_backup(root):
                continue
            for f in files:
                p = os.path.join(root, f)
                try:
                    with open(p, errors='ignore') as fh:
                        if literal in fh.read():
                            hits += 1
                            if hits >= 3:
                                return True
                except Exception:
                    continue
    return False

def _is_in_docstring(src_lines: str, line_idx: int) -> bool:
    # crude: count """ before line; if odd, we're inside docstring
    before = '\n'.join(src_lines[:line_idx + 1])
    return before.count('"""') % 2 == 1

def check_spec_drift(findings, repo_root='.'):
    """R110-78 PHASE 2: detect test literals not in repo."""
    tests_dir = os.path.join(repo_root, 'tests')
    if not os.path.isdir(tests_dir):
        return
    search_dirs = [
        os.path.join(repo_root, 'recipe'),
        os.path.join(repo_root, 'tools'),
        os.path.join(repo_root, 'docs'),
    ]
    per_file_idx = {}
    for tf in sorted(glob.glob(os.path.join(tests_dir, '**', 'test_*.py'),
                              recursive=True)):
        if _is_pycache_or_backup(tf):
            continue
        try:
            with open(tf, errors='ignore') as fh:
                lines = fh.readlines()
        except Exception:
            continue
        base = os.path.basename(tf).replace('.py', '').replace('test_', '')
        per_file_idx[base] = 0
        for ln, line in enumerate(lines, start=1):
            stripped = line.lstrip()
            if stripped.startswith('#'):
                continue
            if _is_in_docstring(lines, ln - 1):
                continue
            literals = []
            for m in _SD_STRING_IN_RE.finditer(line):
                literals.append(m.group(1))
            for m in _SD_INT_EQ_RE.finditer(line):
                literals.append(m.group(1))
            for m in _SD_INT_CMP_RE.finditer(line):
                literals.append(m.group(1))
            for L in literals:
                # filter rules per spec section 4
                if len(L) < 4:
                    continue
                if _SD_URL_RE.search(L):
                    continue
                if _SD_WS_ONLY_RE.match(L):
                    continue
                if _is_self_reference(L, line):
                    continue
                if _is_common_value(L, search_dirs):
                    continue
                # actual spec-drift: literal not in recipe/tools/docs
                hit = False
                for d in search_dirs:
                    if not os.path.isdir(d):
                        continue
                    for root, _, files in os.walk(d):
                        if _is_pycache_or_backup(root):
                            continue
                        for f in files:
                            p = os.path.join(root, f)
                            try:
                                with open(p, errors='ignore') as fh:
                                    if L in fh.read():
                                        hit = True
                                        break
                            except Exception:
                                continue
                        if hit:
                            break
                    if hit:
                        break
                if hit:
                    continue
                per_file_idx[base] += 1
                add_finding(
                    f'SD-test_{base}-{per_file_idx[base]}', 'medium',
                    f'{tf}:{ln}',
                    f"spec_drift: test asserts literal '{L}' but it is absent "
                    f'from recipe/, tools/, docs/ (literal-only-in-tests = '
                    f'test is stale or recipe was updated without test fix)',
                    f'Test will fail until the literal is restored or the test '
                    f'is updated to the new value (R110-71/R110-78 pattern)',
                    f"Run: grep -rn '{L}' tests/ recipe/ tools/ docs/ ; "
                    f'if only tests/ matches: update test to current value; '
                    f'if recipe/ matches different value: test is stale')

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

# --- Summary ---
by_type = Counter(f['type'] for f in findings)
by_sev = Counter(f['severity'] for f in findings)
print(f'Total findings: {len(findings)}')
print(f'By severity: {dict(by_sev)}')
print(f'By type: {dict(sorted(by_type.items()))}')
print(f'Types covered: {len(by_type)}/53+')

# Output as JSON for processing
print('---JSON_START---')
print(json.dumps({'findings': findings, 'summary': {
    'total': len(findings),
    'by_type': dict(by_type),
    'by_severity': dict(by_sev)
}}, indent=2))
