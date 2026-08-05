---
name: mas-engineer-yaml-editor-workflow
description: How to use sub_mas-yaml-editor for ALL YAML changes in mas-engineer (workflows.yaml, recipe/*.yaml, configs/*.yaml). Triggered when Hermes is about to write_file a *.yaml file in a mas-engineer project, or when patching workflows.yaml / recipe-registry / sub_recipes fields. Covers the 3 procedures (PATCH / VALIDATE / BATCH), the dev_editor.py tool, the dev_editor_large.py tool for >1000-line files, the BACKUP-then-PATCH-then-VALIDATE safety chain, and the ONE exception (R110-36) where direct write_file is acceptable.
category: devops
---

# sub_mas-yaml-editor — mandatory workflow for ALL YAML changes in mas-engineer

## When to use (load this skill BEFORE any YAML write)

ANY time you are about to use `write_file` or `patch` on:
- `mas-engineer/.state/workflows.yaml` (recipe registry, ~3211 lines)
- `mas-engineer/recipe/**/*.yaml` (recipe definitions, sub_recipes)
- `mas-engineer/configs/**/*.yaml` (MAS config, agents.yaml, etc.)
- `mas-engineer/.state/pipeline/validation_author_fixes.yaml` (validation patches)
- ANY other `*.yaml` in a mas-engineer repo

**STOP. Use sub_mas-yaml-editor instead of direct write_file.**

## Why (R110-36 self-discipline + R110-40 violation)

Trap 1 from `hermes-self-discipline-traps`: "Self-writing when a sub-agent is the right tool."
- R110-40 (2026-07-30): I edited `workflows.yaml` via `write_file` to remove 26 ghost entries. It worked, but I bypassed the BACKUP → PATCH → VALIDATE → ROLLBACK safety chain that yaml-editor enforces.
- R110-36 (2026-07-29): the 313-line test was correctly written directly (no sub-agent creates test files), but a YAML change in the same session was supposed to go via yaml-editor.
- The skill rule (R110-40 disclosed in commit 7d8cad2 caveat): use yaml-editor for ALL YAML changes.

## The 3 procedures (verbatim from sub_mas-yaml-editor.md)

### PATCH (single edit)
1. ⛔ BEFORE: `python3 -c "import yaml; yaml.safe_load(open('{file}'))"` → YAML invalid? → ❌ ABORT
2. `python3 {tools_dir}/dev_editor.py --workspace {workspace} --patch "{file}" --from "{find}" --after "{replace}" --grund "{reason}"`
3. ⛔ AFTER: `python3 -c "import yaml; yaml.safe_load(open('{file}'))"` → YAML invalid? → ❌ ROLLBACK from Backup
4. ✅ SUCCESS: `dev_changes.py --add` documented the change

### BATCH (multiple edits, all-or-nothing)
1. BACKUP: `cp {file} .backups/{ts}/{file}`
2. PATCH: `sed -i "s/{old}/{new}/g" {file}`
3. VALIDATE: `python3 -c "import yaml; yaml.safe_load(open('{file}'))"`
4. IF OK: `dev_changes.py --add "BATCH: {file}: {old} -> {new}"` IF ERROR: `cp .backups/{ts}/{file} {file}`
5. SHOW: "✅ {file}: {old} -> {new}"

### VALIDATE (sanity check, no edit)
1. `python3 -c "import yaml; yaml.safe_load(open('{workspace}/recipes/{file}'))"`
2. Result: valid / Error with line number

## For files >1000 lines (e.g. workflows.yaml with 3211 lines)

Use `dev_editor_large.py` (line-based editor, not full file rewrite):
- FIND: `python3 tools/dev_editor_large.py find {file} "^{pattern}"` → returns line N
- EDIT: `python3 tools/dev_editor_large.py edit {file} N M "{new_block}"`
- INSERT: `python3 tools/dev_editor_large.py insert {file} N "{new_line}"`
- ROLLBACK: `python3 tools/dev_editor_large.py edit {file} N M "{old_block}"`

**Indentation = 2 spaces. NEVER tabs. No mixed quotes in replacement (escape with \\).**

## How to invoke sub_mas-yaml-editor (recipe form)

```bash
export DEEPSEEK_API_KEY=...   # from .env (35 chars)
export OPENAI_API_KEY=$DEEPSEEK_API_KEY
export OPENAI_HOST=https://api.deepseek.com   # NO /v1
export OPENAI_MODEL=deepseek-v4-flash
goose run --recipe recipe/sub/sub_mas-yaml-editor.yaml --no-session
# Then in the prompt, send the editor_intake block from the instructions file
```

For PTY/multi-turn:
```bash
goose run --recipe recipe/sub/sub_mas-yaml-editor.yaml --interactive
```

## YAML-editor DOES NOT COMMIT (R36 bug, v2.0.0)

`git add -A` was a disaster (R36 bug: 27k lines of backup files committed).
`git commsg` was a typo of `git commit` (LLM auto-corrected, hid the bug).

Committing is `sub_mas-git-operator v2.0.0`'s job. If you are asked to "log" or "commit" a YAML change:
→ DELEGATE to sub_mas-git-operator (task=COMMIT, message=descriptive title+body, files=[changed files])
→ DO NOT run git commands yourself

## The ONE exception (R110-36, greenfield test creation)

Direct write_file is acceptable for:
- Brand-new test files (`tests/test_*.py` that don't exist yet)
- Brand-new skill files (`~/.hermes/skills/.../SKILL.md`)
- Non-YAML files (`*.sh`, `*.md`, `*.py`)

NOT acceptable for:
- ANY existing YAML in the mas-engineer repo
- ANY new YAML in the mas-engineer repo (use sub_mas-yaml-editor CLONE procedure)

## 3-question pre-write self-audit (mandatory)

```
Q1: Is the file a *.yaml in a mas-engineer project?
    YES -> STOP. Use sub_mas-yaml-editor (this skill)
    NO  -> continue to Q2

Q2: Is it a greenfield (new file that doesn't exist yet)?
    YES -> write_file OK. Disclose in commit msg: "directly, not via sub-agent"
    NO  -> STOP. The change is PATCH-shaped. Use sub_mas-yaml-editor PATCH procedure.

Q3: Is it a non-YAML file (test, script, markdown)?
    YES -> write_file OK
    NO  -> STOP. Re-read Q1.
```

## Verification: did the YAML change survive?

After sub_mas-yaml-editor reports DONE:
1. Read the changed section of the file: `head -N {file} | tail -M` or `sed -n 'A,Bp' {file}`
2. Run a yaml.safe_load on the whole file: `python3 -c "import yaml; yaml.safe_load(open('{file}'))"`
3. Run the relevant test that exercises this YAML: `pytest tests/test_recipe_registry_consistency.py -v`

If any of the 3 fail: rollback via `cp .backups/{ts}/{file} {file}` (yaml-editor creates the backup).

## Common pitfalls

- **Don't `write_file` the whole workflows.yaml** — even with 100% correct content, you bypass the backup chain. A 3211-line file with a single bad character = untracked disaster.
- **Don't `sed -i` workflows.yaml** without BACKUP first. The YAML structure (anchors, comments) breaks if your regex matches a substring inside a multi-line block.
- **Don't skip VALIDATE** because "it worked when I tried it locally". The yaml.safe_load check is the only thing that catches the case where a regex replacement broke a YAML structure.
- **Don't commit the .backups/ directory** — it's per-ts, can be huge, and is created on every BATCH.
- **Don't invoke sub_mas-yaml-editor for non-YAML files** — it refuses tasks outside YAML and will return error. Use direct write_file for tests, scripts, markdown.

## Reference

- Verified: 2026-07-30 (R110-40 commit 7d8cad2 disclosed trap-1 violation in commit body)
- Triggered by: R110-40 violation, R110-36 trap-1
- Related: `hermes-self-discipline-traps` (the meta-rule), `goose-cli-e2e-testing` (how to run any sub-agent recipe)
- Source: `recipe/instructions/sub_mas-yaml-editor.md` (54 lines, full procedures)
