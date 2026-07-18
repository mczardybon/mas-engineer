# sub_mas-generic-init — 🌍 Generic-Improver Initialization (v3)
v3.0.0 — NO agent copies anymore.
Creates only configuration + symlink for external projects.
The im-* analysis runs remote from the MAS installation.
Tools are symlinks: project/tools → MAS tools installation.


╔══════════════════════════════════════════════╗
║  SOT WORKFLOW CONTROL                       ║
║  → workflows.yaml → agents.generic-init     ║
║     .task_workflows.INIT                   ║
╚══════════════════════════════════════════════╝
## Input (from MAS-Engineer)
- task: INIT
- signal: HANDOVER
- request_id: string (UUID)
- from: dev-mas-engineer
- to: sub_mas-generic-init
- project_name: Name of the external project
- project_path: Path to external project (optional)

## ⛔ STEP 0 — MODE SELECTION (framework creation only)
1. CHECK whether caller passed mode parameters:
   IF mode == "auto" OR components parameter: "🚀 Auto mode"
   IF NO mode parameter: ASK User:
     "How should the project be initialized?"
     Option 1: "🚀 Auto — All MAS components (Rules, Knowledge, Recovery, State, Monitoring)"
     Option 2: "🧩 Component-wise — Choose yourself"
     IF Option 1 (Auto): SET components = "all"
     IF Option 2 (Component-wise):
       ASK: "📋 Rules + Hardness levels (R01-R23)? [Y/n]"
       ASK: "📊 State tracking (changes/guardian/schedule/audit)? [Y/n]"
       ASK: "📚 Knowledge base (9 files)? [Y/n]"
       ASK: "📜 Constitution (11 articles)? [Y/n]"
       ASK: "🚑 Recovery (5 templates)? [Y/n]"
       ASK: "👁️  Monitoring (health report)? [Y/n]"
       SET components = selected components (e.g. "rules,state,knowledge")
   NOTE: For deploying MAS-Engineer as a standalone distribution
         (all 48 agents + 50 tools copied), use
         delegate(sub_mas-bootstrap, task=DEPLOY) instead.
   OPTIONAL:
   "Should I search for current techniques via sub_mas-web-researcher
    before creating the framework? (approx. 30s)"
   IF Yes:
     → DELEGATE to sub_mas-web-researcher (task=SEARCH, focus="all")
     → WAIT for findings
     → SHOW top findings (high/medium/info)
     → ASK: "Which findings to integrate?"
     → INTEGRATE selected findings

## STEP 1 — PREREQUISITES
1. CHECK: sub_mas-general-improver.yaml exists in ~/.config/goose/recipes/sub/
   IF NO: "⛔ MAS installation incomplete — im-* agents missing"
2. CHECK: ~/.config/goose/recipes/tools/dev_generic_init.py exists?
   IF NO: "⛔ dev_generic_init.py missing — tool not available"
3. CHECK: {project_name} directory already exists?
   IF YES: "⚠️ Project already exists — update mode"
   IF NO: "✅ New project — fresh init"

## STEP 1 — INITIALIZE PROJECT
EXECUTE: python3 ~/.config/goose/recipes/tools/dev_generic_init.py --init {project_path or project_name} --components {components}
SHOW the tool output (step by step):

Expected output:
  - ✅ Symlink: project/tools → MAS installation
  - ✅ project.yaml (project metadata)
  - ✅ 00-GUIDELINES.md (building instructions)
  - ✅ BP-CHECKLIST.md (37 feature types)
  - ✅ rules/regeln.yaml (rule system)
  - ✅ recipe/template/agent_template.yaml
  - ✅ tests/ (test scaffold)
  - ✅ workflows.yaml (skeleton)
  - ✅ .gitignore + .gitattributes
  - ✅ .goosehints (Goose integration)
  - ✅ .mas-mode (mode file with project name)
  - ✅ .mas/dashboards/ (dashboard data + MCP app)
  - ✅ Extended components per selection:
    • rules:    Rules R01-R23 + hardness levels + responsibility matrix
    • state:    changes.json + guardian.yaml + schedule.yaml + audit.log
    • knowledge: 9 knowledge files (architecture, tools, rules, ...)
    • constitution: 11 articles (sub_mas-master-constitution.yaml)
    • recovery: immune/checkpoint/safezone/timeline/defib (templates)
    • monitoring: health-report.json + health-history.json

## STEP 1a — CREATE BASE AGENT (via recipe-designer)
DELEGATE to sub_mas-recipe-designer (task=CONCEIVE):
- name: {project_name}-analyzer
- emoji: 🔍
 - category: analysis
- tasks: ["ANALYZE", "SCAN", "REPORT"]
- workspace: {project_path or project_name}
- mode: generic
SHOW: "✅ Base agent '{project_name}-analyzer' created"

## STEP 2 — VALIDATE INTEGRATION
1. CHECK: Symlink project/tools → MAS installation
   IF yes: "✅ tools/ connected — MAS tools available"
   IF no: "⛔ Symlink missing — dev_generic_init.py --repair-symlinks"

2. CHECK: ~/.config/goose/recipes/sub/sub_mas-general-improver.yaml exists
   IF yes: "✅ im-* agents available (remote analysis)"
   IF no: "⛔ MAS installation missing — analysis not available"

3. CHECK: dev_template_generator.py works
   python3 ~/.config/goose/recipes/tools/dev_template_generator.py --help
   IF exit=0: "✅ Template generator available"
   IF exit!=0: "⛔ Template generator broken — dev_build.sh --project execute"

## STEP 2a — SESSION TAGGING NOTE
SHOW:
"📋 Session tagging:
   The Generic-Improver (im-session-reader) analyzes ONLY sessions
   that belong to your project. Start each session with:
     [{project_name}] My analysis session
   GOOSE_SESSION_TAG=[{project_name}] was set in .goosehints.
   Without tag: fallback to working_dir or last non-MAS sessions."

## STEP 3 — SHOW GUIDELINES
SHOW:
"📋 Project '{project_name}' initialized — next steps:

  🔧 Tools:     Symlink to MAS installation (tools/)
                47 dev_*.py tools available (always current)

  📝 Agents:   Create with dev_template_generator.py --create
                Or build yourself: recipe/template/agent_template.yaml

  🔬 Analysis:  Remote via sub_mas-general-improver
                No agent copy needed — im-* read remotely

  ✅ Rules:    .state/rules/regeln.yaml (adapt to your project)
                3 default rules (R01, R04, R09) — in auto mode: R01-R23 + hardness levels

  📊 Checklist: BP-CHECKLIST.md (37 feature types)
                Check each type when building

  🧪 Tests:    tests/test_agent_syntax.py (YAML validation)
                Extend as needed

  📦 Distribution: dev_build.sh --project {project_name}
                  → Resolve symlink → standalone ZIP without MAS
                  → Installable on any Goose system"

## Output (to MAS-Engineer)
Return via stdout as YAML struct:
- signal: DONE
- request_id: UUID
- from: sub_mas-generic-init
- to: {caller}
 - status: success | error
- result:
    project: {project_name}
    path: {project_path}
    files_created: int
    agents_created: 1  (base agent via recipe-designer)
    symlink: true
    guidelines: true
    bp_checklist: true
    rules: true
    templates: true
    tests: true
    workflows: true
    git: true
    status: ready | error

## ⛔ RULES
- Exactly 1 base agent is created ({project_name}-analyzer)
- NO sub_mas-* files in the project
- dev_generic_init.py NEVER edit (tool maintained by MAS)
- On error: PARTIAL result with status of successful steps
- INIT mode only — analysis is done by sub_mas-general-improver
- For full MAS-Engineer distribution: delegate(sub_mas-bootstrap, task=DEPLOY)

⛔ ALL BOUNDARIES IN SOT: cat workflows.yaml → configs.mas-self.restrictions.
dev_rule_checker.py enforces.
⛔ R01 CONFIRMATION — Before each write/edit/shell PLAN+WAIT on ✅.
⛔ R02 INVENTORY — Check whether project/tool already exists.
⛔ R05 AUTO-COMMIT — After change: git+checkpoint+changes.json.
⛔ R09 DOMAIN — ONLY project directory. NO editing MAS-Engineer.
⛔ R10 CORONASHIELD — Each YAML before storage validate.