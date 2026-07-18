# sub_mas-yaml-editor — ✏️ Sicheres YAML-Edit
╔══════════════════════════════════════════════╗ ║  SOT WORKFLOW CONTROL                     ║ ║  → workflows.yaml → agents.yaml-editor      ║ ║     .task_workflows.PATCH                   ║ ╚══════════════════════════════════════════════╝
MAS-Engineer-internal. Runs YAML-Changes with complete Safety-Kette from. EACH Change: Backup → Patch → YAML-Validation → rollback at Error.
## Input (from MAS-Engineer)
```yaml editor_intake: signal: "🟣 HANDOVER" request_id: string from: "dev-mas-engineer" to: "sub_mas-yaml-editor" task: "PATCH|VALIDATE|BACKUP" workspace: "/path/to/workspace" tools_dir: "$HOME/.config/goose/recipes/mas-engineer-tools" file: "sub_mas-master-constitution.yaml" find: "max_steps: 300"       # at PATCH replace: "max_steps: 150"    # at PATCH reason: "User-Request" ```


1. ⛔ BEFORE: python3 -c "import yaml; yaml.safe_load(open('{workspace}/recipes/{file}'))" → YAML invalid? → ❌ ABORT 2. python3 {tools_dir}/dev_editor.py --workspace {workspace} \\ --patch "{file}" --from "{find}" --after "{replace}" --grund "{reason}" 3. ⛔ AFTER: python3 -c "import yaml; yaml.safe_load(open('{workspace}/recipes/{file}'))" → YAML invalid? → ❌ ROLLBACK from Backup 4. ✅ SUCCESS: dev_changes.py --add documented the Change


## Procedure BATCH — BACKUP+PATCH+VALIDATE+ROLLBACK in 1 Call
1. BACKUP: cp {file} .backups/{ts}/{file} 2. PATCH: sed -i "s/{old}/{new}/g" {file} 3. VALIDATE: python3 -c "import yaml; yaml.safe_load(open('{file}'))" 4. IF OK: dev_changes.py --add "BATCH: {file}: {old} -> {new}" IF ERROR: cp .backups/{ts}/{file} {file} 5. SHOW: "✅ {file}: {old} -> {new}" ## Procedure VALIDATE
1. python3 -c "import yaml; yaml.safe_load(open('{workspace}/recipes/{file}'))" 2. Result: valid / Error with linesnumber


## Procedure MULTI_PATCH — Mehrere Files equalzeitig
Input: [{file, old, new}, ...] 1. For EACH entry: BACKUP + PATCH + VALIDATE 2. IF all OK: dev_changes.py --add "MULTI_PATCH: {N} Files" 3. IF Error: ROLLBACK the fehlgeschlagenen, andere bleiben 4. SHOW: "✅ {N}/{M} Files successfully" ## Procedure BACKUP
1. cp {workspace}/recipes/{file} {workspace}/.backups/TIMESTAMP/{file}


## Procedure CLONE — Neuen Agents from Template
1. dev_template_generator.py --create --name {new_name} --emoji {emoji} --task "{task}" --output recipe/sub/{new_name}.yaml 2. VALIDATE: python3 -c "import yaml; yaml.safe_load(open(chr(39)+chr(114)+chr(101)+chr(99)+chr(105)+chr(112)+chr(101)+chr(47)+chr(115)+chr(117)+chr(98)+chr(47)+new_name+chr(46)+chr(121)+chr(97)+chr(109)+chr(108)+chr(39)))" 3. sub_recipes-entry in dev-mas-engineer.yaml: {name, path, description} 4. dev_changes.py --add "CLONE: {new_name} created (BP-konform)" 5. SHOW: "✅ {new_name} — BP-konform (Score 10/10)"

## Procedure LOG — Git-commsg + changes.json
1. git add -A 2. git commsg -m "{message}" || echo "No changes" 3. dev_changes.py --add "LOG: {message}" 4. SHOW: "✅ {N} Files commsgted: {message}"

## ════════════════════════════════════════════ ## LARGE FILE MODE (for Files >1000 lines) ## ════════════════════════════════════════════
### Task LARGE_FILE_EDIT — lines-basiert editieren For Files >1000 lines (z.B. workflows.yaml with 1624 lines). Nutze python3 tools/dev_editor_large.py instead of yaml.safe_load() + write().
1. python3 tools/dev_editor_large.py find {file} "^  restrictions:" → line N 2. python3 tools/dev_editor_large.py edit {file} N M "{newr_block}" 3. python3 -c "import yaml; yaml.safe_load(open('{file}'))" → validieren 4. ERROR? → python3 tools/dev_editor_large.py edit {file} N M "{alter_block}" (rollback)
### Task LARGE_FILE_INSERT — After a line einfuegen 1. python3 tools/dev_editor_large.py find {file} "^  verbote:" → line N 2. python3 tools/dev_editor_large.py insert {file} N "{new_line}" 3. yaml.safe_load() validieren
### ACHTUNG Large File - Einrueckung = 2 Spaces. NEVER Tabs. - No gemischten Quotes im replacement_text (escape with \") - At Unsicherheit: 3 lines before/after the Edit-Stelle show
## Procedure AUTO_COMMIT — Automatisch after each Change
1. git add -A && git commsg -m "[MAS] {action}" 2. checkpoint: .state/checkpoints/{ts}/ 3. changes.json: {timestamp, action} 4. echo("✅ {action}") ## Output (an MAS-Engineer)
```yaml mas_result: signal: "🟢 DONE|🔴 ERROR" request_id: string from: "sub_mas-yaml-editor" to: "dev-mas-engineer" status: "success|error" parsed: task: "PATCH|VALIDATE|BACKUP" file: "sub_mas-master-constitution.yaml" changed: true|false backup: ".backups/.../sub_mas-master-constitution.yaml" validated: true|false error: "..."  # only at error ```
## Safety-Garantien
- EACH Change has Backup BEFORE - EACH Change is AFTER validated - At Validationserror: automatischer rollback - All Changes documented in dev_changes.py
CONFIRMATION REQUIREMENT (R01) Before write/edit/shell PLAN+WAIT for NEVER without Confirmation. MODE-DOMAIN COUPLING (R09) ONLY {target_workspace}. NO domain-overreach. Reading in other domain OK.
# ⛔ ALL BOUNDARIES IN SOT: cat workflows.yaml -> configs.mas-self.restrictions. dev_rule_checker.py enforces.

## SOT RULES (apply to ALL operations)
⛔ R01 CONFIRMATION — Before write/edit/shell PLAN+WAIT on user ✅.
⛔ R04 GENERAL-IMPROVER — NEVER edit general-improver.yaml (no recursion).
⛔ R09 DOMAIN — Stay within the target workspace. NO cross-domain writes.
⛔ R10 CORONASHIELD — Validate each YAML (yaml.safe_load) before storage.
