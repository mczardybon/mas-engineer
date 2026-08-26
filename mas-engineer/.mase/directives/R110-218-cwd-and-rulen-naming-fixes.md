# R110-218 — fix 2 more CWD-safety + naming bugs (dev_mode.sh + harte_rulen.yaml)

## Context

R110-217 fixed the most visible CWD-safety bug
(`dev_rule_refresh.sh` wrote to nested path when invoked from
inner subdir). During that fix, two more bugs in the same
family surfaced:

1. `tools/dev_mode.sh` lines 25, 79 — hardcoded CWD-relative
   path `mas-engineer/.mase/domains/registry.yaml`
2. `tools/dev_rule_refresh.sh` lines 64, 66 — searches for
   `harte_rulen.yaml` but the real file is `hard_rules.yaml`

Both are silent corruption sources that have been producing
bad output for months without anyone noticing.

## Bug 1: dev_mode.sh CWD-relative registry_path

### Current code

Line 25 (register_domain function):
```python
registry_path = 'mas-engineer/.mase/domains/registry.yaml'
```

Line 79 (list_domains function):
```bash
local registry="mas-engineer/.mase/domains/registry.yaml"
```

Both are inside Python heredocs that get executed at runtime
in whatever CWD the script was invoked from. Same pattern as
the R110-217 bug: only works when CWD = mas-engineer-cleanup/,
fails silently (FileNotFoundError caught nowhere, python
subprocess aborts) when CWD = mas-engineer/.

Note: line 37 of dev_mode.sh already does the right thing for
`script_dir`:
```bash
local script_dir; script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
```

So the defensive pattern is already known in this file — just
not applied to the registry_path lookups.

### Fix

In `register_domain()` (line 25): replace the CWD-relative
literal with the existing `script_dir` variable, which is
already available in scope:
```python
registry_path = '$script_dir/../.mase/domains/registry.yaml'
```

In `list_domains()` (line 79): add a script_dir lookup
(BASH_SOURCE pattern) at the top of the function, then use
it in the local registry variable:
```bash
local script_dir; script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
local registry="$script_dir/../.mase/domains/registry.yaml"
```

## Bug 2: harte_rulen.yaml vs hard_rules.yaml

### Current code

`tools/dev_rule_refresh.sh` lines 64, 66:
```python
path = '$REGL_DIR/harte_rulen.yaml'
...
print('⚠️  No harte_rulen.yaml found')
```

### Reality

`tools/dev_rule_checker.py:24`:
```python
HARTE_REGEL_DATEI = os.path.join(MAS_DIR, ".mase/rules/hard_rules.yaml")
```

`tools/dev_haerte_propagation.py:18`:
```python
rules_file = os.path.join(workspace, "mas-engineer/.mase/rules/hard_rules.yaml")
```

`tools/dev_generic_init.py:587`:
```python
rule_files = ["rules.yaml", "hard_rules.yaml", "rules_2_normal.yaml", ...]
```

The file `mas-engineer/.mase/rules/hard_rules.yaml` exists
(8656 bytes, last modified 2026-08-14). It contains the
hard_rules definition used by every other tool.

The file `harte_rulen.yaml` does NOT exist.

### Evidence of silent failure

All 4 workflow_runs from 2026-08-14 show the warning:
```
⚠️  No harte_rulen.yaml found
```

The script's main purpose (loading + splitting rules by hardness
level) has been silently broken since the R110-140 rename
(2026-08-07) that changed `harte_rulen.yaml` → `hard_rules.yaml`
in dev_rule_checker.py but missed the rename in
dev_rule_refresh.sh.

### Fix

In `tools/dev_rule_refresh.sh` line 64:
```python
path = '$REGL_DIR/hard_rules.yaml'
```

And line 66 (the warning message):
```python
print('⚠️  No hard_rules.yaml found')
```

Plus the comment on line 4:
```bash
# --mode mas     → MAS-eigene Rulen (hard_rules.yaml → rulen_5/4/2_*.yaml)
```

## Out of scope (separate R-numbers)

These have the same CWD-relative pattern but involve different
files / risk profiles. Defer to R110-219+:

- `tools/dev_gatekeeper.py:117` — uses
  `~/.config/goose/recipes/../mas-engineer/.mase/rules/responsibility_matrix.yaml`
  (tilde-expanded path, but CWD-dependent because the
  `recipes/..` is relative to CWD)
- `tools/dev_autobuild.sh:20` — uses `$WORKSPACE` env var
  (env-driven, not CWD-relative, but requires caller to set it)
- `tools/dev_mode.sh:46,51,56-57,62,66` (register_domain inner
  python) — these use `base = '$script_dir/..'` (correct,
  uses the script_dir var) but pull from `.mase/templates/`
  and `.mase/...` — verify these exist in both layouts

## Verification

After fix:

### dev_mode.sh
- TEST: `cd mas-engineer && bash tools/dev_mode.sh --list`
  should NOT fail with FileNotFoundError on
  `mas-engineer/.mase/domains/registry.yaml` from inner CWD

### dev_rule_refresh.sh
- TEST: `cd mas-engineer && bash tools/dev_rule_refresh.sh`
  should now find `hard_rules.yaml` and split it into
  `rulen_5_extrem.yaml` + `rulen_4_stark.yaml` + `rulen_2_normal.yaml`
  (currently these output files are not being created because
  the script early-returns on the missing file)
- TEST: outer `mas-engineer/.mase/rules/rulen_5_extrem.yaml`
  should be (re)created with content from `hard_rules.yaml`

## Directive file

`mas-engineer/.directives/R110-218-cwd-and-rulen-naming-fixes.md`
(this file) — full bug analysis, evidence, fix proposal.

## Files (this R-number)

- M  tools/dev_mode.sh
  - line 25: registry_path uses script_dir var
  - line 79-86: list_domains gets script_dir lookup
- M  tools/dev_rule_refresh.sh
  - line 4: comment update (harte_rulen → hard_rules)
  - line 64: path uses hard_rules.yaml
  - line 66: warning message uses hard_rules.yaml
- A  .directives/R110-218-cwd-and-rulen-naming-fixes.md
- A  logs/e2e-evidence-gen2/2026-08-19T15-45-00Z-R110-216-c3-nested-cleanup/R110-218-FIX-REPORT.md


---

## ADDENDUM (2026-08-19 20:45Z) — DEEPER BUG DISCOVERED

After initial fix to R110-218.a (file name `harte_rulen.yaml`
→ `hard_rules.yaml`), deeper inspection of the script revealed
that the data-structure keys are also wrong:

### Bugs found (3 in total in this script)

1. **File name** (R110-218.a, FIXED):
   `'$REGL_DIR/harte_rulen.yaml'` → `'$REGL_DIR/hard_rules.yaml'`

2. **Top-level key** (R110-218.b, NEEDS FIX):
   `data.get('rulen', [])` → `data.get('rules', [])`
   (real file uses `rules` not `rulen`)

3. **Rule-inner key** (R110-218.c, NEEDS FIX):
   `r['haerte']` → `r['hardness']`
   (real rule uses `hardness` not `haerte`)

4. **Top-level metadata key** (R110-218.d, NEEDS FIX):
   `data.get('haerte_leveln', {})` → `data.get('hardness_levels', {})`
   (real file uses `hardness_levels` not `haerte_leveln`)

5. **Output key** (R110-218.e, NEEDS FIX for consistency):
   `yaml.dump({'rulen': filtered, 'haerte': level}, ...)` →
   `yaml.dump({'rules': filtered, 'hardness': level}, ...)`
   (output should match input style)

### Evidence (real hard_rules.yaml structure)

```python
>>> import yaml
>>> d = yaml.safe_load(open('mas-engineer/.mase/rules/hard_rules.yaml'))
>>> list(d.keys())
['hardness_levels', 'last_updated', 'rules', 'version']
>>> d['rules'][0].keys()
dict_keys(['block', 'check', 'hardness', 'id', 'name', 'prompt_text'])
>>> r = d['rules'][0]
>>> r['hardness']
5
>>> r['prompt_text']
'MODE-DOMAIN-COUPLING — Mode determines domain. ...'
```

Distribution: {hardness=5: 9 rules, hardness=4: 1 rule, hardness=2: 2 rules}
= 12 rules total

The script has been **silently broken** since at least R110-140
(2026-08-07) — it was logging
"⚠️  No harte_rulen.yaml found" and then doing nothing useful
(creating empty rulen_*.yaml output files).

After the R110-218.a fix it stopped logging the warning but
still produced empty output files (0 rules) because the
key-naming bugs above prevented actual rule loading.

### Updated fix plan

**Same script, additional 4 key-naming fixes** (lines 67-82):

```python
# OLD (broken):
rulen = data.get('rulen', [])
leveln = data.get('haerte_leveln', {})

for r in rulen:
    h = r['haerte']
    level = leveln.get('extrem_stark' if h >= 5 else 'stark' if h >= 4 else 'normal' if h >= 2 else 'schwach', {})
    symbol = level.get('symbol', '')
    r['text'] = f"{symbol} {r['prompt_text']}"

for level, label in [(5, '5_extrem'), (4, '4_stark'), (2, '2_normal')]:
    filtered = [r for r in rulen if r['haerte'] == level]
    outpath = f'$REGL_DIR/rulen_{label}.yaml'
    with open(outpath, 'w') as f:
        yaml.dump({'rulen': filtered, 'haerte': level}, f, default_flow_style=False)
```

**NEW (correct)**:
```python
# R110-218: real keys are 'rules' (not 'rulen') and 'hardness' (not 'haerte')
rules = data.get('rules', [])
leveln = data.get('hardness_levels', {})

for r in rules:
    h = r['hardness']
    level = leveln.get('extreme' if h >= 5 else 'strong' if h >= 4 else 'normal' if h >= 2 else 'weak', {})
    symbol = level.get('symbol', '')
    r['text'] = f"{symbol} {r['prompt_text']}"

# Also map hardness_levels sub-keys (real ones are extreme/strong/normal/weak)
# The 'schwach' German key does not exist in the real file
# but 'weak' does
for level, label in [(5, '5_extreme'), (4, '4_strong'), (2, '2_normal')]:
    filtered = [r for r in rules if r['hardness'] == level]
    outpath = f'$REGL_DIR/rules_{label}.yaml'
    with open(outpath, 'w') as f:
        yaml.dump({'rules': filtered, 'hardness': level}, f, default_flow_style=False)

print(f'Geschrieben: rules_5_extreme.yaml ({len([r for r in rules if r["hardness"]==5])} EXTREM-Rulen)')
print(f'Geschrieben: rules_4_strong.yaml ({len([r for r in rules if r["hardness"]==4])} STARK-Rulen)')
print(f'Geschrieben: rules_2_normal.yaml ({len([r for r in rules if r["hardness"]==2])} NORMAL-Rulen)')
```

Note: also changed output filename `rulen_*.yaml` → `rules_*.yaml`
to match the convention used by the rest of the codebase
(`rules_2_normal.yaml`, `rules_4_strong.yaml`, `rules_5_extreme.yaml`
already exist in the directory and are loaded by
`dev_rule_checker.py:20-21`).

### Why this is R110-218 not R110-219

These key-naming bugs are an extension of the same root cause
as the file-name bug: R110-140 rename in 2026-08-07 was
incomplete. Keeping all 5 fixes in one R-number is the
correct atomic-bugfix pattern (avoid the same class of
bug being "fixed" twice via different R-numbers).

### Verification (updated)

After R110-218 complete fix:
- `bash tools/dev_rule_refresh.sh` (any CWD) creates
  `mas-engineer/.mase/rules/rules_5_extreme.yaml` with 9 rules
  (extracted from `hard_rules.yaml`'s `rules` array, filtered
  by `hardness == 5`)
- Same for `rules_4_strong.yaml` (1 rule) and `rules_2_normal.yaml`
  (2 rules)
- Output files have `rulen: [...9 rules...]` content with
  `haerte: 5` metadata (or English equivalent)
