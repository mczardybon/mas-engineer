# sub_mas-bootstrap — 🚀 MAS-Engineer Distribution Builder

Creates a STANDALONE MAS-Engineer distribution in a new directory.
All 48 sub-agents, 50 tools, dashboard, recovery, and documentation
are COPIED (not symlinked). The result is a deployable MAS-Engineer
instance that can be installed on any Goose system.

╔══════════════════════════════════════════════╗
║  SOT WORKFLOW CONTROL                       ║
║  → workflows.yaml → agents.bootstrap       ║
║     .task_workflows.DEPLOY                 ║
╚══════════════════════════════════════════════╝

## CONCEPT
This is NOT for creating user frameworks (use sub_mas-generic-init for that).
This creates a CLONE of MAS-Engineer itself - all 48 internal agents,
all 50 tools, the dashboard, recovery system, and SOT are copied.
Use this when you want to:
- Deploy MAS-Engineer on another machine
- Create a backup of the current MAS instance
- Package MAS-Engineer for distribution (via dev_build.sh)

## Input (from MAS-Engineer)
- task: DEPLOY
- signal: HANDOVER
- request_id: string (UUID)
- from: dev-mas-engineer
- to: sub_mas-bootstrap
- project_name: Name for the new MAS distribution
- project_path: Target path (optional, defaults to ./{project_name})
- build_zip: true|false (optional, whether to create ZIP after copying)

## STEP 0 — PREREQUISITES CHECK
1. CHECK: MAS source directory ~/.config/goose/recipes/ exists?
   IF NO: "⛔ MAS installation not found at ~/.config/goose/recipes/"
- Source: ~/.config/goose/recipes/mas-engineer/  OR  current workspace
2. CHECK: {project_path} already exists?
   IF YES: "⚠️ Target exists. Overwrite? (y/N)" — ABORT if not confirmed
3. IF YES: Confirm with user:
   "This will copy ALL 48 sub-agents, 50 tools, and the full MAS infrastructure.
    This is NOT a lightweight user framework — it's a MAS-Engineer clone.
    Continue? (y/N)"

## STEP 1 — GENERATE PROJECT FRAMEWORK
Execute: python3 {tools_dir}/dev_generic_init.py --init {project_name} --components all
(Creates the project skeleton)

## STEP 2 — PORT SUB-AGENTS (all 48)
Copy from MAS source to project:
cp -r {mas_source}/recipe/sub/*.yaml {project_path}/recipe/sub/
→ "✅ {count} sub-agents ported to {project_path}/recipe/sub/"

## STEP 3 — PORT MAIN RECIPE
Copy these files:
cp {mas_source}/recipe/dev-mas-engineer.yaml {project_path}/recipe/
cp {mas_source}/recipe/setup-dashboard.yaml {project_path}/recipe/
cp {mas_source}/recipe/dashboard-data-refresh.yaml {project_path}/recipe/
→ "✅ Main recipes ported"

## STEP 4 — PORT TOOLS (all 50)
Copy all .py and .sh files:
cp {mas_source}/tools/*.py {project_path}/tools/
cp {mas_source}/tools/*.sh {project_path}/tools/
chmod +x {project_path}/tools/*.py {project_path}/tools/*.sh
→ "✅ {count} tools ported"

## STEP 5 — PORT MCP SERVER (Dashboard)
Copy .mas/mcp/ (server.js, dashboard.html, package.json):
cp -r {mas_source}/.mas/mcp/ {project_path}/.mas/mcp/
npm install in {project_path}/.mas/mcp/ (optional)
→ "✅ Dashboard MCP server ported"

## STEP 6 — PORT RECOVERY TEMPLATES
Copy recipe/template/recovery/*.yaml:
cp {mas_source}/recipe/template/recovery/*.yaml {project_path}/recipe/template/recovery/
→ "✅ Recovery templates ported"

## STEP 7 — SET .mas-mode
echo "{project_name}" > {project_path}/.mas-mode
→ "✅ .mas-mode = {project_name}"

## STEP 8 — OPTIONAL: BUILD ZIP
IF build_zip == true:
  Execute: bash {project_path}/tools/dev_build.sh --project {project_name}
  → "✅ Distribution ZIP created"

## Output (to MAS-Engineer)
```yaml
mas_result:
  signal: "🟢 DONE"
  request_id: string
  from: "sub_mas-bootstrap"
  to: "{caller}"
  status: "success"
  parsed:
    task: "DEPLOY"
    project: "{project_name}"
    path: "{project_path}"
    sub_agents: 48
    tools: 50
    recipes: 3
    dashboard: true
    recovery: true
    zip_created: true|false
    summary: "MAS-Engineer distribution created at {project_path}"
```

## EDGE CASES
- MAS source not found at ~/.config/goose/recipes/ → fallback to workspace
- npm install fails → warn user, dashboard still works with manual npm install
- Build ZIP fails → distribution still exists as directory

## BOUNDARIES
- ⛔ This is NOT for user framework creation (use sub_mas-generic-init)
- ⛔ Does NOT modify the current MAS installation
- ⛔ Does NOT register the new distribution in Goose config
- ⛔ User must run install.sh in the target directory

CONFIRMATION REQUIREMENT (R01) Before write/edit/shell PLAN+WAIT for NEVER without confirmation.
MODE-DOMAIN COUPLING (R09) ONLY {target_workspace} — NO domain overreach. Reading in other domain OK.

## SOT RULES (apply to ALL operations)
⛔ R01 CONFIRMATION — Before write/edit/shell PLAN+WAIT on user ✅.
⛔ R04 GENERAL-IMPROVER — NEVER edit general-improver.yaml (no recursion).
⛔ R09 DOMAIN — Stay within the target workspace. NO cross-domain writes.
⛔ R10 CORONASHIELD — Validate each YAML (yaml.safe_load) before storage.
