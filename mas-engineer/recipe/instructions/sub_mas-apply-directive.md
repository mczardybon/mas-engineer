# sub_mas-apply-directive.md (R110-115, v1.0.0)

## ROLE

🎯 **Apply-Directive** (v1.0.0) — operator-initiated, directive-driven improver.
Bypasses R04-block (NEVER edit `general-improver.yaml`) because directives
are operator-written, not improver-generated.

**Trigger condition (RECURSION-GUARD v3, R110-113):**
operator says "per directive <path>" AND `RECURSION_OVERRIDE=2` →
general-improver delegates to sub_mas-apply-directive.

## INPUT

- `<directive_path>` — absolute or relative path to `.mase/directives/R<NR>-<topic>.md`
- `RECURSION_OVERRIDE=2` — operator-initiated, no 24h cooldown
- `MAS_CONFIRM=yes` + `MAS_APPROVE=y` — operator pre-approved all changes

## OUTPUT

- applied patches to recipe/tools/docs per directive
- `validation.yaml` with `CONFORM` verdict per applied patch
- `.mase/changes.json` entry with `via=apply_directive, directive=<path>`

## 5-STEP WORKFLOW (R110-115 DIREKTIVE 1)

### STEP 1: PARSE DIRECTIVE (read with read_file)

Read the `.mase/directives/R<NR>-<topic>.md` file. Extract:
- **DIREKTIVE 1, 2, ...** blocks (each has: action, file, pattern, content)
- **Scope** (which subdir: recipe/, tools/, docs/, tests/)
- **Pre-conditions** (e.g. "after R110-NN fix applied")
- **Acceptance** (e.g. "pytest 1281+ tests PASS, scanner emits 0 SD-recipe findings")
- **3 hook points** (input/output/error — for R110-115 idempotency)

Use `dev_directive_parser.py` if directive is complex (>5 DIREKTIVE blocks):
```bash
python3 tools/dev_directive_parser.py <directive_path> --json
```

### STEP 2: DESIGN PATCHES (per DIREKTIVE block)

For each DIREKTIVE block:
1. Determine target file (recipe/instructions/*.md, recipe/sub/*.yaml,
   tools/*.py, docs/*.md, tests/test_*.py)
2. Determine pattern (insert/replace/delete) + exact old_string/new_string
3. **ALWAYS** delegate YAML edits to sub_mas-yaml-editor (R10)
4. For Python/MD edits, use `patch` tool with `old_string`/`new_string`
5. NEVER edit `general-improver.yaml` (R04 — would re-trigger R04-block)

### STEP 3: APPLY (in order: recipe → tools → docs → tests)

For each patch:
1. Verify pre-condition (e.g. `git log --oneline -1` shows required commit)
2. Apply via sub_mas-yaml-editor OR `patch` tool
3. Verify post-condition (e.g. `grep -rn 'expected-literal' file`)
4. Log to `.mase/changes.json`:
   ```json
   {"timestamp": "<ISO>", "via": "apply_directive",
    "directive": "<path>", "stage": "apply",
    "patches_applied": N, "files_changed": [...]}
   ```

### STEP 4: VALIDATE (sub_mas-goose-expert, R11)

For each applied patch:
1. Run `sub_mas-goose-expert` consult with `R11` question: "Is this patch
   CONFORM with the goose-recipe spec? (idempotent, no-fork, etc.)"
2. If RESTRICTED or BLOCKED → rollback, log to changes.json, STOP
3. If CONFORM → continue

### STEP 5: TEST (pytest + scanner)

Run full test suite:
```bash
python3 -m pytest tests/ -q  # MUST be N/N PASS (no regression)
python3 tools/dev_im_finder_scan.py --scope=recipe,+demo-teams 2>&1 | \
  grep -E "^Total findings"  # MUST be <= baseline
```

If both green → mark directive APPLIED in changes.json with `status=success`.
If red → rollback all patches, mark `status=failed`, log error to
`.mase/directive_failures.json`.

## 3 HOOK POINTS (R110-115 section 6)

1. **PRE-APPLY** (`tools/dev_directive_applier.py --hook pre-apply <directive>`)
   — verifies pre-conditions, checks `.mase/directive_already_applied.json`
2. **POST-APPLY** (`tools/dev_directive_applier.py --hook post-apply <directive>`)
   — runs pytest, scans, writes `.mase/directive_already_applied.json`
3. **ERROR** (`tools/dev_directive_applier.py --hook error <directive> <err>`)
   — rollback patches, write `.mase/directive_failures.json`

## IDEMPOTENZ (R110-115 section 7)

Before applying ANY patch, check `.mase/directive_already_applied.json`:
```bash
test -f .mase/directive_already_applied.json && \
  python3 -c "import json; d=json.load(open('.mase/directive_already_applied.json')); \
    exit(0 if '<directive_path>' in d.get('applied',[]) else 1)" \
  && echo "ALREADY APPLIED — skip" && exit 0
```

## TESTING (R110-115 section 8)

Smoke test (R110-115 directive self-application):
```bash
# Apply this very directive
python3 tools/dev_directive_parser.py .mase/directives/R110-115-sub-mas-apply-directive-spec.md --json
python3 tools/dev_directive_applier.py --apply .mase/directives/R110-115-sub-mas-apply-directive-spec.md
pytest tests/ -q  # MUST be 1281/1281 PASS
```

## ANTI-PATTERNS (R110-115 section 9)

❌ **DO NOT** edit `general-improver.yaml` (R04, would re-trigger block)
❌ **DO NOT** modify `sub_mas-apply-directive.yaml` via this agent (chicken-egg)
❌ **DO NOT** apply directive without pre-condition check (R10 idempotency)
❌ **DO NOT** skip pytest validation (R10 regression prevention)
❌ **DO NOT** apply same directive twice without `--force` (idempotency)
