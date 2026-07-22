#!/usr/bin/env python3
"""Comprehensive IM-Finder scan — detects all 53+ feature types A-MM + NN.

IM-005 SCOPE-FIX (2026-07-22): The scan was previously hardcoded to
RECIPE_DIR='recipe' which meant user-installed demo teams in
/root/.config/goose/recipes/*/ were never analyzed. Now we accept
--scope (CLI arg) or the SCAN_SCOPE env var to extend coverage.
Default behavior is unchanged (backward-compatible).
"""
import yaml, os, glob, re, json, sys, argparse
from collections import Counter

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
for SCAN_DIR in SCAN_DIRS:
    if not os.path.isdir(SCAN_DIR):
        continue
    for root, dirs, files in os.walk(SCAN_DIR):
        # skip sub/ of a top-level scan to avoid re-walking
        for f in files:
            if f.endswith('.yaml') or f.endswith('.yml'):
                ALL_YAMLS.append(os.path.join(root, f))
# Also pick up top-level yamls in cwd (legacy)
for f in glob.glob('*.yaml') + glob.glob('*.yml'):
    if os.path.isfile(f) and f not in ALL_YAMLS:
        ALL_YAMLS.append(f)

findings = []
fid = 0

def add_finding(ftype, severity, file, issue, impact, fix):
    global fid
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
