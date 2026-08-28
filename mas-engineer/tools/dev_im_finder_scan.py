#!/usr/bin/env python3
"""Comprehensive IM-Finder scan — detects all 53+ feature types A-MM + NN.

IM-005 SCOPE-FIX (2026-07-22): The scan was previously hardcoded to
RECIPE_DIR='recipe' which meant user-installed demo teams in
/root/.config/goose/recipes/*/ were never analyzed. Now we accept
--scope (CLI arg) or the SCAN_SCOPE env var to extend coverage.
Default behavior is unchanged (backward-compatible).
"""
import yaml, os, glob, re, json, sys, argparse, time
from pathlib import Path
from collections import Counter

# --- SEVERITY FILTER (R28 + R97 fix) ---
# Default (R97): ONLY medium,high — suppress low-severity style findings
# (e.g. "session cleanup missing", "no retry logic" — best-practice opinions,
# not bugs). Set SEVERITY_FILTER=low,medium,high (or pass
# --severity-filter=low,medium,high) to see all findings.
SEVERITY_FILTER = {'medium', 'high', 'blocker'}
for _a in sys.argv[1:]:
    if _a.startswith('--severity-filter='):
        SEVERITY_FILTER = {s.strip() for s in _a.split('=', 1)[1].split(',') if s.strip()}
        break
_env_sev = os.environ.get('SEVERITY_FILTER')
if _env_sev:
    SEVERITY_FILTER = {s.strip() for s in _env_sev.split(',') if s.strip()}

# --- R110-177 PHASE 2: Issue-DB integration (issue-centric dedup) ---
# Deviance note (documented in R110-177 apply commit): the directive
# specified unconditional dedup in add_finding(). That would break the
# existing 1544-test suite (e.g. test_scanner_detects_hardcode_stale
# re-runs the scanner and asserts findings are EMITTED) and the
# R110-124 standalone behavior. Dedup is therefore OPT-IN via
# --issue-db[=PATH] (or MAS_ISSUE_DB=1). Without the flag the scanner
# behaves exactly as before R110-177. The im-finder recipe passes the
# flag so the pipeline gets the issue-centric behavior.
_ISSUE_DB_MOD = None
_ISSUE_DB = None
_ISSUE_DB_ACTIVE = False
_ISSUE_DB_PATH = '.mase/pipeline/issue_db.json'


def _issue_db_module():
    """Lazy-import dev_issue_db.py from this script's dir (R02 consumer)."""
    global _ISSUE_DB_MOD
    if _ISSUE_DB_MOD is None:
        import importlib.util as _ilu
        _path = os.path.join(os.path.dirname(__file__) or '.',
                             'dev_issue_db.py')
        _spec = _ilu.spec_from_file_location('dev_issue_db', _path)
        _mod = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        _ISSUE_DB_MOD = _mod
    return _ISSUE_DB_MOD


def _issue_db_settings():
    """Parse --issue-db[=PATH] / --no-issue-db / MAS_ISSUE_DB env."""
    global _ISSUE_DB_ACTIVE, _ISSUE_DB_PATH
    for _a in sys.argv[1:]:
        if _a == '--no-issue-db':
            _ISSUE_DB_ACTIVE = False
            return
        if _a == '--issue-db':
            _ISSUE_DB_ACTIVE = True
            _ISSUE_DB_PATH = '.mase/pipeline/issue_db.json'
            return
        if _a.startswith('--issue-db='):
            _ISSUE_DB_ACTIVE = True
            _ISSUE_DB_PATH = _a.split('=', 1)[1]
    _env = os.environ.get('MAS_ISSUE_DB')
    if _env and _env.lower() in ('1', 'true', 'yes'):
        _ISSUE_DB_ACTIVE = True


_issue_db_settings()


def _get_issue_db():
    """Lazy-init IssueDB (R110-177 2.3). None when issue-db inactive."""
    global _ISSUE_DB
    if not _ISSUE_DB_ACTIVE:
        return None
    if _ISSUE_DB is None:
        _ISSUE_DB = _issue_db_module().IssueDB(db_path=_ISSUE_DB_PATH)
    return _ISSUE_DB


def compute_issue_hash(file, type, structural_pattern):
    """R110-177 1.3: stable issue identity hash (delegates to dev_issue_db)."""
    return _issue_db_module().compute_issue_hash(file, type,
                                                 structural_pattern)


def compute_structural_pattern(ftype, file, **kwargs):
    """R110-177 2.2: stable structural pattern per finding-type.

    R110-177-ADAPTATION: specified as a scanner-internal helper; the
    implementation lives in dev_issue_db.py (unit-testable without
    triggering the scanner's module-level scan). The scanner exposes
    the same name for spec-faithfulness.
    """
    return _issue_db_module().compute_structural_pattern(ftype, file,
                                                         **kwargs)


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

def add_finding(ftype, severity, file, issue, impact, fix,
                *, line_start=None, line_end=None, **pattern_kwargs):
    """Register a scanner finding.

    R110-177 PHASE 2: every finding gets a stable issue_hash +
    structural_pattern (identity triple file|type|pattern). When the
    issue-db is ACTIVE (--issue-db / MAS_ISSUE_DB=1), known issues are
    deduplicated: open issues get instance++ (no re-emit), fixed /
    wontfix / false_positive are skipped entirely. Backward-compatible:
    all new kwargs have defaults; without the flag behavior is
    unchanged (all findings emitted, no db side-effects).
    """
    global fid
    # R28: respect SEVERITY_FILTER
    if severity not in SEVERITY_FILTER:
        return
    fid += 1
    finding_id = f'F-{fid:03d}'

    # R110-177 PHASE 2: compute structural pattern + issue_hash
    struct_pattern = compute_structural_pattern(
        ftype, file,
        line_start=line_start, line_end=line_end, **pattern_kwargs
    )
    issue_hash = compute_issue_hash(file, ftype, struct_pattern)

    # R110-177 PHASE 2: dedup against IssueDB (opt-in)
    db = _get_issue_db()
    if db is not None:
        _known = db.exists(issue_hash)
        instance = {
            "file": file,
            "line_start": line_start,
            "line_end": line_end,
            "context": pattern_kwargs.get('context', 'unknown'),
            "scanner_version": "dev_im_finder_scan.py:1.5.0",
            "finding_id": finding_id,
        }
        db.register(
            hash=issue_hash, type=ftype, severity=severity, file=file,
            structural_pattern=struct_pattern, issue_summary=issue,
            fix_summary=fix, instance=instance,
        )
        if _known:
            # already known (open/fixed/wontfix/false_positive) -> skip emit
            return

    findings.append({
        'id': finding_id,
        'type': ftype,
        'severity': severity,
        'file': file,
        'issue': issue,
        'impact': impact,
        'fix': fix,
        'issue_hash': issue_hash,
        'structural_pattern': struct_pattern,
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

    # R110-270: scope-restrict recipe-structure checks (MM1-MM3, A5, Q1)
    # to files that look like recipes. Two-tier check:
    #   (1) Path-based: anything under `recipe/` is a recipe.
    #   (2) Content-based: a YAML is recipe-like if it has at least ONE
    #       of the canonical recipe markers (`instructions:`, `prompt:`,
    #       `about:`, `parameters:`). This catches:
    #         - recipe/sub/*.yaml, recipe/instructions/*.md? no, .yaml
    #         - tools/auto-dashboard-v2-update.yaml (recipe-like: has
    #           `instructions:`, `title:`, `version:`, `description:`)
    #         - root_recipe.yaml, test-executor recipes
    #       and excludes:
    #         - codecov.yml (no recipe markers)
    #         - .mase/*.yaml (framework config: `guardian:`, `workflows:`,
    #           `schedule:` — no recipe markers)
    #         - .github/*.yml (GitHub Actions: `jobs:`, `on:`, `steps:`)
    #         - .backups/*.yaml (excluded already by path patterns)
    #         - testproject/*.yaml (sandbox config: `mas_dependency:`, etc.)
    _RECIPE_PATH_HINTS = ('/recipe/',)
    _RECIPE_CONTENT_MARKERS = ('instructions:', 'prompt:', 'about:', 'parameters:')

    def _is_recipe_like(path: str, payload: dict) -> bool:
        # Path-based: anything under recipe/ is in.
        if any(h in ('/' + path) for h in _RECIPE_PATH_HINTS):
            return True
        # Content-based: at least one recipe marker in raw text.
        # We re-read the file because we already consumed the YAML
        # payload via yaml.safe_load, but the raw text has comments
        # and block-scalar markers that the payload drops. This is
        # cheap (file already in OS page cache).
        try:
            with open(path) as _f:
                _raw = _f.read()
        except OSError:
            return False
        return any(marker in _raw for marker in _RECIPE_CONTENT_MARKERS)

    if not _is_recipe_like(yp, data):
        # Non-recipe YAML (CI config, framework config, project config):
        # skip recipe-structure checks. We still emit Q2 (parse errors)
        # which fires before this guard via the try/except above. All
        # other recipe-specific findings are suppressed — they would
        # be false positives for non-recipes.
        continue

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
    # R-102: max_steps migrated to max_turns (Goose GOOSE_SUBAGENT_MAX_TURNS=25)
    max_turns = settings.get('max_turns', 0) if settings else 0
    max_steps = settings.get('max_steps', 0) if settings else 0

    if timeout and timeout < 60:
        add_finding('A1', 'medium', yp, f'timeout={timeout}s too low (< 60s)',
                    'Agent may timeout before completing tasks',
                    f'set timeout={min(timeout*2, 3600)}')
    if max_turns and max_turns < 25:
        add_finding('A2', 'medium', yp, f'max_turns={max_turns} too low (< 25)',
                    'Agent may run out of turns (Goose default GOOSE_SUBAGENT_MAX_TURNS=25)',
                    f'set max_turns={max_turns+10}')
    if max_turns and max_turns > 200:
        add_finding('A2-EXT', 'low', yp, f'max_turns={max_turns} too high (> 200)',
                    'Over-specified turn budget inflates cost/latency',
                    'set max_turns=200 (or lower)')
    if max_steps and max_steps < 10:
        add_finding('Q3', 'low', yp, f'max_steps={max_steps} too low (< 10)',
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
                    'Remove or rename unknown fields',
                    field_name=", ".join(sorted(unknown)))

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
    _skip_path = Path('.mase/pipeline/skip_recently_split.yaml')
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
    # R110-274: NN1 scope-restriction. Sub-recipes in recipe/sub/ are
    # already split sub-agents by design (per the recipe/sub/ directory
    # convention). Flagging them as "multi-role" was a false positive:
    # 18/19 NN1 issues in R110-273 were sub-recipes. Also skip
    # recipe/wf_*.yaml (workflow recipes that intentionally orchestrate
    # multiple steps). Only flag recipe/*.yaml at the top level.
    # Note: ALL_YAMLS contains RELATIVE paths (e.g. "recipe/sub/foo.yaml"),
    # not absolute, so we must match without leading slash.
    # R110-275: only skip the NN1 check, not the whole iteration —
    # NN2/NN3 must still run on sub-recipes.
    _yp_norm = yp.replace('\\', '/')
    _is_sub_or_wf = ('recipe/sub/' in _yp_norm or 'recipe/wf_' in _yp_norm)
    # R98 fix (IM-007): skip micro-agents (<60 lines) — they are split sub-agents
    # by design. NN1's "5+ role-verbs" pattern is normal for small focused agents
    # that handle a few related operations. Only flag actual orchestrators that
    # haven't been split. Filtered 23/31 false positives in R98 analysis.
    try:
        _line_count = sum(1 for _ in open(yp))
    except Exception:
        _line_count = 999
    if _line_count < 60 and not _is_sub_or_wf:
        continue
    # R110-271: NN1 threshold raised from 5 to 8 roles. Master orchestrators
    # (e.g. dev-mas-engineer-30agents.yaml with 10 roles = 30 sub-agents
    # that need to be analyzed/validated/generated/reported/scanned) are
    # by design multi-role. The "5+ role-verbs" pattern was too strict and
    # flagged legitimate orchestrators. Sub-recipes (recipe/sub/) and
    # workflow recipes (recipe/wf_*) are still skipped entirely.
    _is_master_orchestrator = (
        '30agents' in yp or 'orchestrator' in yp.lower()
        or 'master' in yp.lower())
    if (not _is_sub_or_wf and not _is_master_orchestrator
            and len(found_roles) >= 8):
        add_finding('NN1', 'medium', yp,
                    f'multi_role_agent: {len(found_roles)} distinct roles ({found_roles[:5]})',
                    'Agent may violate single-responsibility principle',
                    'Consider splitting into orchestrator + sub-agents',
                    roles=found_roles)

    # NN2: tool_overload
    extensions = data.get('extensions', [])
    if isinstance(extensions, list) and len(extensions) >= 5:
        add_finding('NN2', 'medium', yp,
                    f'tool_overload: {len(extensions)} extensions declared',
                    'Too many tools may confuse the agent',
                    'Distribute tools across specialized sub-agents',
                    extension_count=len(extensions))

    # NN3: scope_bloat
    # R110-271: threshold raised from 200 to 400 chars. Sub-recipes
    # (recipe/sub/*.yaml) legitimately document their scope in detail
    # (e.g. "wf_im_consume_findings.yaml" has 4-domain scope = recipe
    # intake, yaml emission, code audit, report generation — by design).
    # The 200-char threshold was too aggressive and flagged every
    # well-documented sub-recipe. Sub-recipes are skipped entirely;
    # top-level recipes (recipe/*.yaml) are only flagged if both
    # length > 400 AND domains >= 4 (was: 200/3).
    desc = data.get('description', '')
    if desc and len(desc) > 400 and not _is_sub_or_wf:
        domains = ['config', 'recipe', 'yaml', 'code', 'test', 'deploy',
                   'monitor', 'report', 'audit', 'security', 'pipeline',
                   'session', 'recovery', 'knowledge', 'dispatch']
        found_domains = [d for d in domains if d in desc.lower()]
        if len(found_domains) >= 4:
            add_finding('NN3', 'medium', yp,
                        f'scope_bloat: description > 200 chars with {len(found_domains)} domains ({found_domains[:3]})',
                        'Agent scope too broad',
                        'Split into domain-specific sub-agents',
                        domains=found_domains)

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
                # R110-271: skip "isolated test-input" literals that are
                # intentionally only in tests/ as fixtures, not in
                # recipe/tools/docs. Heuristic: short identifier-style
                # literals (no spaces, ≤30 chars, all-lowercase or
                # snake_case) like 'sub_l', 'sub_test-orphan-xyz', or
                # test-output markers like 'drained 3', 'registered 2
                # issues', 'skipped 2', 'changed=True' are TEST DATA
                # that must remain isolated. These are NOT drift, they
                # are test-fixture strings that should not appear in
                # production code. The 1605/1606 pytest pass rate
                # (R110-270) confirms these literals are legitimate.
                if (len(L) <= 30
                        and re.match(r'^[a-z][a-z0-9_\-]*$', L)):
                    # snake_case / kebab-case identifier, no spaces
                    continue
                if (re.search(r'\b(drained|registered|skipped|changed|'
                              r'processed|emitted)\s+\d+', L)
                        or re.match(r'^[A-Z][A-Z\s]+$', L)):  # "THIS IS NOT JSON"
                    continue
                # R110-271 (broader): also skip literals that look like
                # test-fixture paths, module:function refs, dotted module
                # names, JSON-schema keys, or short mixed-case identifiers
                # that are clearly test-internal. None of these should
                # appear in recipe/tools/docs.
                if (re.match(r'^logs/|^[^ ]+\.(md|log|yaml|json|html)\b', L)
                        or re.search(r':[a-z_]+$', L)  # module:function
                        or re.match(r'^[a-z][a-z0-9_.]*\.[a-z][a-z0-9_]*$', L)
                        or L.startswith('{') or L.endswith('}')
                        or re.match(r'^[a-z]+/[a-z]+$', L)
                        or re.match(r'^[a-z][a-z0-9_]*\.\.\.\s*[✅❌→]', L)):
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


def _is_in_code_block(lines, line_idx):
    """Return True if line_idx is inside a fenced code block (``` markers)."""
    count = 0
    for i in range(line_idx + 1):
        stripped = lines[i].lstrip()
        if stripped.startswith('```'):
            count += 1
    return count % 2 == 1


def _is_in_table_or_example(lines, line_idx):
    """Return True if line_idx is inside a markdown table or example block.
    Heuristic: previous/next non-blank line starts with '|' (table) or
    'Example:'/'```' (example block). Conservative -- false-negatives OK."""
    if line_idx + 1 < len(lines) and lines[line_idx + 1].lstrip().startswith('|'):
        return True
    if line_idx > 0 and lines[line_idx - 1].lstrip().startswith('|'):
        return True
    if line_idx + 1 < len(lines) and 'Example' in lines[line_idx + 1]:
        return True
    return False


def check_spec_drift_reverse(findings, repo_root='.'):
    """R110-112: detect recipe count-assertions not asserted in tests/.

    Reverse direction of check_spec_drift(): instead of "test asserts
    literal that recipe/tools/docs lacks", this catches "recipe/instructions
    asserts a count-anchor (e.g. '16 checks') that tests/ doesn't assert"
    (recipe-side drift = R110-111 L26 pattern).

    SCOPE (intentionally narrow):
      - only "N <count-anchor>" patterns (e.g. "16 checks", "N tests")
      - skip descriptive numeric prose ("30 seconds", "100 files")
      - count-anchors: check, checks, test, tests, assert, asserts,
        rule, rules, finding, findings, validator, validators
    """
    recipe_dirs = [
        os.path.join(repo_root, 'recipe', 'instructions'),
    ]
    tests_dir = os.path.join(repo_root, 'tests')
    if not os.path.isdir(tests_dir):
        return
    test_files = sorted(glob.glob(os.path.join(tests_dir, '**', 'test_*.py'),
                                  recursive=True))
    if not test_files:
        return
    # Pre-load per-recipe test-file contents into a dict keyed by the
    # recipe base-name. We match recipe/instructions/sub_mas-X.md to
    # tests/test_sub_mas_X.py (and the dev_-prefixed sibling if present).
    # This avoids false-positives where a meta-test fixture (e.g.
    # test_dev_spec_invariant.py mentioning "22 critical checks" inside
    # a docstring as test-data) is wrongly attributed to an unrelated
    # recipe (R110-209 scanner-bug fix).
    test_combined_per_recipe = {}
    test_combined = ''
    for tf in test_files:
        try:
            with open(tf, errors='ignore') as fh:
                content = fh.read()
        except Exception:
            continue
        test_combined += '\n' + content
        # map every test-file to the recipe base-name it tests.
        # recipe base e.g. "sub_mas-pre-push-validator" ↔ test stem
        # "test_sub_mas_pre_push_validator" (the test_/dev_ prefix and
        # hyphens→underscores). We record BOTH the unprefixed stem (so
        # lookup by base-name works) and the with-prefix stem.
        stem = os.path.basename(tf).replace('.py', '')
        # candidate keys: test stem itself (e.g. "test_sub_mas_pre_push_validator"
        # and "test_dev_spec_invariant"); and the unprefixed form
        # (e.g. "sub_mas_pre_push_validator" and "dev_spec_invariant")
        for variant in (stem, stem.removeprefix('test_')):
            test_combined_per_recipe[variant] = content
    recipe_sources = []
    for d in recipe_dirs:
        if os.path.isdir(d):
            for root, _, files in os.walk(d):
                if _is_pycache_or_backup(root):
                    continue
                for f in files:
                    if f.endswith('.md'):
                        recipe_sources.append(os.path.join(root, f))
    per_file_idx = {}
    for src in recipe_sources:
        try:
            with open(src, errors='ignore') as fh:
                lines = fh.readlines()
        except Exception:
            continue
        base = os.path.basename(src).replace('.md', '').replace('.py', '')
        per_file_idx[base] = 0
        for ln, line in enumerate(lines):
            stripped = line.lstrip()
            if stripped.startswith('#'):
                continue
            if _is_in_code_block(lines, ln):
                continue
            if _is_in_table_or_example(lines, ln):
                continue
            for m in _RECIPE_NUMERIC_RE.finditer(line):
                num, word = m.group(1), m.group(2).lower()
                # Only count-anchor patterns (R110-111 L26 trigger)
                if word not in _COUNT_ANCHOR_NEXT:
                    continue
                # Skip descriptive prose: lines that are clarifications,
                # collision-avoidance comments, or summary statistics
                # (R110-114 lesson: "1,961 findings" is descriptive, not
                # a count-anchor; "R110-94 Check 16+" is a code reference;
                # "1000 findings" in "12 days to clear 1000 findings" is
                # a workload estimate, not an assertion).
                if re.search(r'\b(Last\s+regenerated|to\s+avoid|days?\s+to\s+clear|'
                             r'found\s+in|via\s+|version|tracking|~)\b', line,
                             re.IGNORECASE):
                    continue
                # Skip if line is a comment/code reference (e.g. "R110-94 Check 16+")
                if re.search(r'R\d+-\d+\s+Check', line):
                    continue
                # Skip if the number is preceded by "~" (approximation)
                if '~' in line and re.search(rf'~\s*{re.escape(num)}', line):
                    continue
                # Skip if the number has comma-thousands ("1,961" not a test-anchor)
                if f'{int(num):,}' in line and f'{int(num):,}' != num:
                    continue
                # R110-271: skip historical references like "R110-176 had 1690
                # findings" or "AFTER R110-... +73 tests". These are commit-
                # history DOKU-anchors, not load-bearing count-assertions.
                # Heuristic: line contains "R\d+-\d+" (commit reference) and
                # either "had" or "+N" near the number.
                if re.search(r'R\d+-\d+', line):
                    if (re.search(rf'\bhad\s+{re.escape(num)}', line)
                            or re.search(rf'\+\s*{re.escape(num)}\b', line)
                            or re.search(rf'{re.escape(num)}\s+tests?\b', line)
                                and 'AFTER' in line):
                        continue
                # Skip "16 critical checks" or "17 critical checks" (test-anchor
                # is "X critical checks" not "X checks")
                literal_full = m.group(0)
                # Check for "N checks" pattern (R110-111 L26 trigger)
                checks_match = _RECIPE_CHECKS_RE.search(literal_full)
                if checks_match and test_combined:
                    # R110-209: prefer recipe-specific test-file content to
                    # avoid false-positives from meta-test fixtures.
                    # base is e.g. "sub_mas-pre-push-validator" → test stem
                    # is "test_sub_mas_pre_push_validator" (hyphens→underscores).
                    test_stem = 'test_' + base.replace('-', '_')
                    scope = test_combined_per_recipe.get(
                        test_stem,
                        test_combined_per_recipe.get(
                            base.replace('-', '_'), test_combined))
                    test_anchor = re.search(
                        r'["\'](\d+)\s+(?:critical\s+)?checks?["\']',
                        scope)
                    if test_anchor:
                        if test_anchor.group(1) != checks_match.group(1):
                            per_file_idx[base] += 1
                            add_finding(
                                f'SD-recipe_{base}-{per_file_idx[base]}',
                                'blocker',
                                f'{src}:{ln + 1}',
                                f"spec_drift_reverse: recipe asserts "
                                f"'{literal_full}' (line {ln + 1}) but test "
                                f"asserts '{test_anchor.group(0)}' — "
                                f"BLOCKER (R110-78 PHASE 1: pytest-count-"
                                f"mismatch)",
                                f"Test will pass but recipe contradicts "
                                f"itself. Update recipe OR test to match "
                                f"(R110-78 canonical = pytest-count-anchor).",
                                f"Run: grep -rn '{literal_full}' tests/ "
                                f"recipe/ ; if only recipe/ matches: test is "
                                f"stale; if tests/ matches different value: "
                                f"recipe is stale. R110-111 L26 pattern: "
                                f"'16 checks' -> '17 checks'")
                            continue
                # Generic count-anchor check: "N tests" / "N rules" etc.
                # Look for the same number with the same word in tests/.
                # R110-209: scope to recipe-specific test-file to avoid
                # false-positives from meta-test fixtures.
                pattern = re.compile(rf'\b{re.escape(num)}\s+{re.escape(word)}')
                test_stem = 'test_' + base.replace('-', '_')
                scope = test_combined_per_recipe.get(
                    test_stem,
                    test_combined_per_recipe.get(
                        base.replace('-', '_'), test_combined))
                if pattern.search(scope):
                    continue  # test-anchor present, OK
                per_file_idx[base] += 1
                add_finding(
                    f'SD-recipe_{base}-{per_file_idx[base]}', 'medium',
                    f'{src}:{ln + 1}',
                    f"spec_drift_reverse: recipe asserts "
                    f"'{literal_full}' (count-anchor) but tests/ has no "
                    f"matching assertion (recipe-side drift)",
                    f"Test will pass but recipe count-anchor has no test-"
                    f"support. Either add test-assertion for '{num} "
                    f"{word}' OR update recipe to match existing test count.",
                    f"Run: grep -rn '{num} {word}' tests/ recipe/ ; if "
                    f"only recipe/ matches: add test-anchor; if tests/ "
                    f"matches different value: recipe is stale")


# --- R110-124: Pattern A + B sister-functions -----------------------------
# Wrap dev_self_audit detectors (producer) as scanner findings (consumer).
# R02: scanner is consumer, self_audit is producer — do NOT duplicate the
# detection logic; lazy-import the module and reuse PATTERN_A_RE /
# PATTERN_A_ACCEPT_CTX / _is_in_fence / _strip_inline_code / _scan_pattern_b
# / _build_repo_literal_index. See: .mase/directives/R110-124-scanner-pattern-ab.md

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
                if _mod._is_in_fence(lines, ln - 1):
                    continue
                # R110-210: skip HTML-comment lines (snapshot semantics
                # already documented in <!-- historical ... -->)
                if '<!--' in line and '-->' in line:
                    continue
                # R110-210: skip lines where the PREVIOUS line ends an
                # HTML-comment that documents the count as opaque/historical
                # (e.g. "<!-- (historical 43 — same opaque legacy
                # grouping as CHECK 13, NOT the 112 mas-self
                # registry) -->" on L92 followed by "All 52 MAS
                # sub-agents + 43 sub-agents" on L93 — the count
                # IS the snapshot, do NOT flag)
                prev_line = lines[ln - 2] if ln - 2 >= 0 else ''
                # (a) Previous line ends an HTML-comment that documents
                # the count as opaque/historical (most common case)
                if '<!--' in prev_line and '-->' in prev_line and \
                        re.search(r'historical|same .* legacy|do NOT update|opaque', prev_line, re.I):
                    continue
                # (b) Previous line is a parenthetical/historical
                # reference explaining that a number is the
                # documented-snapshot, not the current value
                # (e.g. "R110-56, 2026-07-25: only ~2 dedicated
                # test files for 112 sub-agents; that ratio is now
                # far exceeded" — the 112 is intentionally
                # documented as the historical anchor)
                if re.search(r'\(historical|R110-\d+|historically|that .* now .* exceeded|that ratio', prev_line, re.I):
                    continue
                # (c) The line ITSELF contains a documented-historical
                # reference inline (e.g. "(R110-56, 2026-07-25: only
                # ~2 dedicated test files for 112 sub-agents; that
                # ratio is now far exceeded)" — the 112 is
                # intentionally a documented historical anchor)
                if re.search(r'\(historical|R110-\d+|historically|that .* now .* exceeded|that ratio', line, re.I):
                    continue
                # R110-210: skip canonical "N checks" declarations
                # (e.g. "Run the following 23 checks IN ORDER" —
                # the canonical check-count line; flagged previously
                # because scanner didn't know which file the count
                # was authoritative for)
                if re.search(r'run the following \d+ checks', line, re.I):
                    continue
                inline = _mod._strip_inline_code(line)
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
                        f"stale (R110-78 spec-drift lesson).",
                        literal=f'{num} {word}', file_dir=rel)


def check_stale_literal(findings, repo_root='.'):
    """R110-124: wrap dev_self_audit Pattern B (STALE-LITERAL detection).

    Detects quoted literals in recipe/instructions/ that don't appear
    anywhere else in recipe/tools/docs/tests. Mirrors
    dev_self_audit._scan_pattern_b() but emits scanner findings.

    R110-124-ADAPTATION (R110-116 honest): directive draft used severity
    'warn', but the scanner's R28 SEVERITY_FILTER (default medium,high,
    blocker) silently drops 'warn' — findings would be invisible. Emit
    'medium' instead (documented in commit body).
    """
    # [same import dance as check_hardcode_stale]
    import importlib.util as _ilu
    _path = os.path.join(os.path.dirname(__file__) or '.',
                         'dev_self_audit.py')
    _spec = _ilu.spec_from_file_location('dev_self_audit', _path)
    _mod = _ilu.module_from_spec(_spec)
    try:
        _spec.loader.exec_module(_mod)
    except Exception as e:
        add_finding('STALE-LITERAL-err', 'low',
                    'tools/dev_im_finder_scan.py',
                    f'pattern_b_import error: {e}',
                    'STALE-LITERAL findings may be incomplete',
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
            rel = os.path.relpath(fp, repo_root)
            try:
                with open(fp, errors='ignore') as fh:
                    lines = fh.readlines()
            except Exception:
                continue
            file_stem = Path(fp).stem
            per_file_idx[rel] = 0
            # Index excludes THIS file (dev_self_audit.run_self_audit
            # semantics). R110-124-ADAPTATION (R110-116 honest): the
            # directive draft passed the scope DIRECTORY as exclude_path,
            # but _build_repo_literal_index compares file-abspaths against
            # the exclude-abspath — a file never equals the dir, so
            # nothing was excluded and every literal self-indexed (Pattern
            # B became a silent no-op). Per-file exclusion restores the
            # producer semantics.
            repo_index = _mod._build_repo_literal_index(
                Path(repo_root), Path(fp))
            # Use dev_self_audit._scan_pattern_b directly
            for f in _mod._scan_pattern_b(
                    lines, rel, repo_index, file_stem):
                per_file_idx[rel] += 1
                add_finding(
                    f'STALE-LITERAL-{per_file_idx[rel]:03d}',
                    'medium',
                    f'{rel}:{f.description.split(":")[1].split(":")[0]}',
                    f.description.replace(file_stem + ':', ''),
                    f.suggested_fix,
                    f"Pattern B (R110-78): literal {f.description!r} "
                    f"appears nowhere in repo.",
                    literal=f.description, file_dir=rel)


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
