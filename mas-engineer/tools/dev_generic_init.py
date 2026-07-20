#!/usr/bin/env python3
"""dev_generic_init.py — Generic-Init Tool v1.0.0
Initializes external projects WITHOUT agent copy.
Creates: Configuration + symlink to MAS tools + guidelines.

Usage:
  python3 dev_generic_init.py --init project_name
  python3 dev_generic_init.py --init ./path/to/project
  python3 dev_generic_init.py --repair-symlinks
  python3 dev_generic_init.py --status

Flags:
  --dry-run     Show only, do not create
  --verbose     Verbose output
"""
import os
import sys
import yaml
import shutil
import json
import subprocess
import argparse
from pathlib import Path

VERSION = "1.0.0"

# constants
MAS_CONFIG = os.path.expanduser("~/.config/goose/recipes")
MAS_SUBS = os.path.join(MAS_CONFIG, "sub")
MAS_TOOLS = os.path.join(MAS_CONFIG, "mas-engineer-tools")
MAS_STATE = os.path.join(MAS_CONFIG, ".state")
WORKSPACE = os.environ.get('MAS_WORKSPACE',
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Structure detection: traditional (mas-engineer/) vs port mode (flat)
if os.path.exists(os.path.join(WORKSPACE, "mas-engineer")):
    MAS_DIR = os.path.join(WORKSPACE, "mas-engineer")
else:
    MAS_DIR = WORKSPACE
STATE_TEMPLATES = os.path.join(MAS_DIR, ".state", "templates")
STATE_RULES = os.path.join(MAS_DIR, ".state", "rules")
MAS_TOOLS = os.path.join(WORKSPACE, "tools")  # actual location of dev_*.py tools

# Colors
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
RED = "\033[0;31m"
BOLD = "\033[1m"
NC = "\033[0m"

def ok(msg): print(f"  {GREEN}✅{NC} {msg}")
def warn(msg): print(f"  {YELLOW}⚠️{NC} {msg}")
def error(msg): print(f"  {RED}❌{NC} {msg}")
def info(msg): print(f"  {BLUE}ℹ️{NC} {msg}")
def header(msg): print(f"\n{BLUE}{BOLD}━━━ {msg} ━━━{NC}")


def get_mas_state():
    """Checks ob MAS-Installation available ist."""
    state = {
        "mas_installed": os.path.exists(MAS_CONFIG),
        "subs_available": os.path.exists(MAS_SUBS),
        "tools_available": os.path.exists(MAS_TOOLS),
        "im_agents": [],
        "si_agents": [],
        "tools_list": [],
    }
    if state["subs_available"]:
        for f in os.listdir(MAS_SUBS):
            if f.startswith("sub_mas-im-"):
                state["im_agents"].append(f)
    if state["tools_available"]:
        state["tools_list"] = sorted([f for f in os.listdir(MAS_TOOLS) if f.startswith("dev_")])
    return state


def create_symlinks(project_path, dry_run=False):
    """Creates symlink: project/tools → MAS-Tools-Installation."""
    tools_dir = os.path.join(project_path, "tools")

    if os.path.exists(tools_dir):
        if os.path.islink(tools_dir):
            target = os.readlink(tools_dir)
            if target == MAS_TOOLS:
                ok(f"tools/ → Symlink exists already ({target})")
                return True
            else:
                warn(f"tools/ → Symlink points to {target}, not to MAS")
                info("Remove old symlink...")
                if not dry_run:
                    os.unlink(tools_dir)
        elif os.path.isdir(tools_dir):
            warn(f"tools/ is an actual directory — skip")
            info("Delete tools/ manually and run --repair-symlinks")
            return False

    if not dry_run:
        os.symlink(MAS_TOOLS, tools_dir)
    ok(f"Symlink: {tools_dir} → {MAS_TOOLS}")
    return True


def create_project_config(project_path, project_name, dry_run=False):
    """Creates project.yaml with metadata — never overwrites existing."""
    config_path = os.path.join(project_path, "project.yaml")
    if os.path.exists(config_path):
        info(f"project.yaml exists already — skipped")
        return
    config = {
        "name": project_name,
        "version": "1.0.0",
        "type": "generic-project",
        "created_with": f"dev_generic_init.py v{VERSION}",
        "mas_dependency": {
            "type": "symlink",
            "tools_source": MAS_TOOLS,
            "analysis": "remote (im-* Agenten aus MAS-Installation)",
        },
        "structure": {
            "tools": "symlink (no copy)",
            "agents": "selbst creates (dev_template_generator.py --create)",
            "rules": ".state/rules/rules.yaml",
            "templates": "recipe/template/agent_template.yaml",
        },
    }
    if not dry_run:
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    ok(f"project.yaml ({len(yaml.dump(config))} bytes)")


def create_rules(project_path, dry_run=False):
    """Creates empty rule system — never overwrites existing."""
    rules_dir = os.path.join(project_path, ".state", "rules")
    rules_file = os.path.join(rules_dir, "rules.yaml")
    template_file = os.path.join(STATE_TEMPLATES, "user_rules_template.yaml")

    if os.path.exists(rules_file):
        info(f"rules.yaml exists already — skipped")
        return

    if not dry_run:
        os.makedirs(rules_dir, exist_ok=True)

    if os.path.exists(template_file):
        if not dry_run:
            shutil.copy2(template_file, rules_file)
        ok(f"rules.yaml (Template)")
    else:
        # Fallback: own default rule set
        default_rules = {
            "version": "1.0.0",
            "rules": {
                "R01": {
                    "name": "CONFIRMATION_REQUIRED",
                    "hardness": "EXTREME-STRONG",
                    "description": "No write/edit/shell without user confirmation",
                },
                "R04": {
                    "name": "RECURSION_PROTECTION",
                    "hardness": "EXTREME-STRONG",
                    "description": "Never edit your own agent",
                },
                "R09": {
                    "name": "DOMAIN_SEPARATION",
                    "hardness": "EXTREME-STRONG",
                    "description": "Only write in own project directory",
                },
            },
        }
        if not dry_run:
            with open(rules_file, "w") as f:
                yaml.dump(default_rules, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        ok(f"rules.yaml (Default, {len(default_rules['rules'])} rules)")


def create_guidelines(project_path, project_name_clean, dry_run=False):
    """Creates 00-GUIDELINES.md — never overwrites existing."""
    guidelines_file = os.path.join(project_path, "00-GUIDELINES.md")
    if os.path.exists(guidelines_file):
        info(f"00-GUIDELINES.md exists already — skipped")
        return
    project_name = project_name_clean
    content = """# 00-GUIDELINES.md — Projekt-Guidelines

Initialisiert mit dev_generic_init.py v{VERSION}

## Reasonprinzipien
- Jeder Agent = 1 YAML-file in `recipe/sub/`
- Agenten are Goose-Sub-Agents (no external Services)
- Communication via YAML-Structs
- Domain separation: only im eigenen Projekt-Directory write

## Agent-Typen (reference)
^| type | Task | Example |
|-----|---------|----------|
| Analyse | Data read + pattern detect | sub_{project}-analyst |
| Recovery | Aus Errorn erholen | sub_{project}-checkpoint |
| Monitoring | Monitor metrics | sub_{project}-health |
| Generator | Documents/Signale generate | sub_{project}-docgen |
| Verbetterung | Analyzen + Optimieren | sub_{project}-improver |

## YAML-Struktur
```yaml
name: sub_{project}-mein-agent
version: 1.0.0
settings:
  timeout: 120
  max_steps: 30
instructions: |
  # sub_{{project}}-mein-agent — 🎯 Kurzdescription
  ...
```

## Best Practices
1. **Prompts**: < 300 Zeichen
2. **Instructions**: < 2000 Zeichen
3. **⛔ Rules**: Run before each critical step
4. **Version**: always in erster line
5. **Namen**: sub_{{project}}-{function}

## Tools (Symlink auf MAS-Installation)
- `dev_template_generator.py` — Agenten-Generator
- `dev_rule_checker.py` — Rule-validation
- `dev_yaml_generator.py` — YAML-Generator
- `dev_workflow_runner.py` — Workflow-Execution
- `dev_goose_db.py` — Session-Analyse

## Analyse (Remote via im-* Agenten)
The im-* agents of the MAS installation can analyze your project:
```
sub_mas-im-pipeline → Verbetterungs-Pipeline
sub_mas-im-finder  → Optimierungspotential (36 Typen)
sub_mas-im-rank    → Priorisierung
sub_mas-im-designer → Patch-Draft
sub_mas-im-validator → validation
```

## Distribution
```bash
dev_build.sh --project {project}   # → standalone ZIP without MAS
```
""".format(VERSION=VERSION, project=project_name_clean, function="analyst")

    guidelines_file = os.path.join(project_path, "00-GUIDELINES.md")
    if not dry_run:
        with open(guidelines_file, "w") as f:
            f.write(content)
    ok(f"00-GUIDELINES.md ({len(content)} bytes)")


def create_bp_checklist(project_path, dry_run=False):
    """Creates BP-CHECKLIST.md with 36 feature types — never overwrites existing."""
    bp_target = os.path.join(project_path, 'BP-CHECKLIST.md')
    if os.path.exists(bp_target):
        info(f"BP-CHECKLIST.md exists already — skipped")
        return
    # Copy from template (not hardcoded)
    bp_template = os.path.join(STATE_TEMPLATES, 'bp_checklist.md')
    if os.path.exists(bp_template):
        if not dry_run:
            import shutil
            shutil.copy2(bp_template, bp_target)
        ok(f"BP-CHECKLIST.md (Template, {os.path.getsize(bp_template)} bytes)")
        return
    
    # Fallback: hardcoded Content
    content = """# BP-CHECKLIST.md — Best-Practices-Checklist

## Settings optimization (A)
- [ ] A1: timeout too low? (2+ timeouts in 10 calls?)
- [ ] A2: max_steps too low? (will be reached before completion?)
- [ ] A3: timeout too high? (Ø-Duration < 20% timeout?)
- [ ] A4: max_steps too high? (Ø-Steps < 30% max?)

## Prompt-Quality (B)
- [ ] B1: Prompt too vague? (User asks 3× "what are you doing?")
- [ ] B2: Prompt too long? (> 500 Zeichen)
- [ ] B3: Context missing? (Agent asks after Infos)
- [ ] B4: Prompt ≠ Instructions? (Contradiction?)

## Instructions (C)
- [ ] C1: ⛔-Rule missing? (Agent tut Verbotenes)
- [ ] C2: Procedure unclear? (Agent asks for sequence/order)
- [ ] C3: Boundaries missing? (Agent exceeds Scope)
- [ ] C4: referenceen veraltet? (not-existente files)

## Workflow (D)
- [ ] D1: Step sequence wrong?
- [ ] D2: Step forgotten?
- [ ] D3: Redundant step? (80% skipped)
- [ ] D4: Unclear question?

## Detectionspattern (E)
- [ ] E1: Command without match?
- [ ] E2: pattern matcht wrong?
- [ ] E3: Dead detection? (> 50 sessions no match)

## Prompt-Block (F)
- [ ] F1: Command without prompt entry?
- [ ] F2: Wrong sort order? (Most frequent not on top)
- [ ] F3: Description unklar?
- [ ] F4: MODE-GUARD missing?

## Health (G)
- [ ] G1: Agent degraded? (Score < 80)
- [ ] G2: High failure rate? (> 10%)
- [ ] G3: Loops detected?
- [ ] G4: Agent dead?

## Anomalien (H)
- [ ] H1: Duration > 2× Ø?
- [ ] H2: Tokens > 3× Ø?
- [ ] H3: Kosten > 5× Ø?
- [ ] H4: Session stale? (> 60min idle)

## Prompt-Quality (I)
- [ ] I1: Score < 5/10?
- [ ] I2: Identity missing? ("Who am I")
- [ ] I3: No ⛔-Boundaries?
- [ ] I4: Zu long? (> 500 Zeichen)
- [ ] I5: Not self-contained?

## Config (J)
- [ ] J1: Config ❌?
- [ ] J2: Config-Value obsolete?

## Docs (K)
- [ ] K1: Doc veraltet?
- [ ] K2: Doc missing?

## Goose (L)
- [ ] L1: Too many sessions?
- [ ] L2: Too many skills?
- [ ] L3: Logs too large?

## Migration (M)
- [ ] M1: Breaking Changes?
- [ ] M2: Non-Breaking?

## Recipe (N)
- [ ] N1: Duplicate recipes?
- [ ] N2: Old Version?
- [ ] N3: Missing Dependencies?

## Structure (Type O)
- [ ] O1: Instructions ≠ Ist-State?
- [ ] O2: reference auf not-existente file?
- [ ] O3: Outdated counter?
- [ ] O4: Hardcoded path?

## Tools (P)
- [ ] P1: Syntax-Error?
- [ ] P2: Hardcoded paths?
- [ ] P3: Import-Error?

## Calibration (Q)
- [ ] Q1: Oversized? (< 20% Auslastung)
- [ ] Q2: Tightly sized? (> 80% Auslastung)

## Git (R)
- [ ] R1: Code reduziert? (✅ positivee)
- [ ] R2: Code bloated? (⚠️ negativee)
- [ ] R3: ⛔ Rules increased? (✅ Safety)
- [ ] R4: Prompt shortened? (✅ Token-Effizienz)
- [ ] R5: New file? (⚠️ Only if needed)

## Tests (V)
- [ ] V1: No Tests?
- [ ] V2: < 50% tested?

## Prompt-Erosion (GG)
- [ ] GG1: ⛔ missing im prompt?
- [ ] GG2: Version missing?
- [ ] GG3: Emoji missing?
- [ ] GG4: Prompt zu short? (< 100 Zeichen)
- [ ] GG5: Instructions too long? (> 2000 Zeichen)

## Drift (FF + JJ)
- [ ] FF1: timeout deviating?
- [ ] FF2: max_steps deviating?
- [ ] JJ1: Installation deviating?

## Backup (HH)
- [ ] HH1: > 50 Backup-directoryse?
- [ ] HH2: > 100 .bak-files?
- [ ] HH3: No backup before change?
- [ ] HH4: Backup > 30 days old?
"""
    checklist_file = os.path.join(project_path, "BP-CHECKLIST.md")
    if not dry_run:
        with open(checklist_file, "w") as f:
            f.write(content)
    ok(f"BP-CHECKLIST.md ({len(content)} bytes)")


def create_tests(project_path, dry_run=False):
    """Creates empty tests/ directory with scaffold — NEVER overwrites existing."""
    tests_dir = os.path.join(project_path, "tests")
    init_file = os.path.join(tests_dir, "__init__.py")
    test_file = os.path.join(tests_dir, "test_agent_syntax.py")

    if os.path.exists(test_file) and os.path.exists(init_file):
        info(f"tests/ exists already — skipped")
        return

    if not dry_run:
        os.makedirs(tests_dir, exist_ok=True)

    if not os.path.exists(init_file):
        if not dry_run:
            with open(init_file, "w") as f:
                f.write("# Tests\n")
        ok(f"tests/__init__.py")

    if not os.path.exists(test_file):
        if not dry_run:
            with open(test_file, "w") as f:
                f.write('''"""Test: YAML-Syntax allr Agenten."""
import os
import yaml

SUBS_DIR = os.path.join(os.path.dirname(__file__), "..", "recipe", "sub")


def test_all_agent_yamls():
    """Checks ob all Sub-Agent-YAMLs valide are."""
    if not os.path.exists(SUBS_DIR):
        return  # No agents yet
    for f in os.listdir(SUBS_DIR):
        if f.endswith(".yaml"):
            with open(os.path.join(SUBS_DIR, f)) as fh:
                yaml.safe_load(fh)  # raises on invalid
''')
        ok(f"tests/test_agent_syntax.py")


def create_workflows(project_path, project_name_clean, dry_run=False):
    """Creates workflows.yaml mit Skelett — overwrites NEVER bestehende."""
    workflows_file = os.path.join(project_path, "workflows.yaml")
    if os.path.exists(workflows_file):
        info(f"workflows.yaml exists already — skipped")
        return
    skeleton = {
        "version": "1.0.0",
        "project": project_name_clean,
        "workflows": {
            "build-test": {
                "description": "Build and Test",
                "steps": [],
            },
            "analyse": {
                "description": "Analyse (remote via im-* Agenten)",
                "steps": [],
            },
            "deploy": {
                "description": "Deployment",
                "steps": [],
            },
        },
    }
    if not dry_run:
        with open(workflows_file, "w") as f:
            yaml.dump(skeleton, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    ok(f"workflows.yaml (3 empty Workflows)")


def create_git_infrastructure(project_path, dry_run=False):
    """Creates .gitignore + .gitattributes — overwrites NEVER bestehende."""
    gitignore_file = os.path.join(project_path, ".gitignore")
    gitattributes_file = os.path.join(project_path, ".gitattributes")

    if os.path.exists(gitignore_file) and os.path.exists(gitattributes_file):
        info(f".gitignore + .gitattributes exist already — skipped")
        return

    if not os.path.exists(gitignore_file):
        gitignore_content = """# MAS Generic Project
__pycache__/
*.pyc
*.pyo
.env
dist/
.backups/
*.bak
.state/checkpoints/
.tmp/
"""
        if not dry_run:
            with open(gitignore_file, "w") as f:
                f.write(gitignore_content)
        ok(f".gitignore")

    if not os.path.exists(gitattributes_file):
        gitattributes_content = """*.yaml linguist-language=YAML
*.md linguist-detectable=true
*.py linguist-detectable=true
"""
        if not dry_run:
            with open(gitattributes_file, "w") as f:
                f.write(gitattributes_content)
        ok(f".gitattributes")


def create_dashboard_scaffold(project_path, dry_run=False):
    """Creates Dashboard-Data-Directory + initiale data.json."""
    dash_dir = os.path.join(project_path, '.mas', 'dashboards')
    if dry_run:
        info(f"[DRY-RUN] .mas/dashboards/ mit data.json + history.json")
        return
    os.makedirs(dash_dir, exist_ok=True)
    from datetime import datetime
    initial_data = {
        "version": "1.0.0",
        "timestamp": datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
        "workspace": project_path,
        "mode": "generic",
        "project_name": os.path.basename(project_path),
        "agents": {"total": 0, "healthy": 0, "degraded": 0, "dead": 0,
                   "avg_score": 0, "scores": [], "guardian_scan": None,
                   "issues": {"total": 0, "long_instructions": 0}},
        "changes": {"total": 0, "last_10": [], "by_type": {}},
        "improvement": {"total_runs": 0, "last_run": None,
                        "schedule_status": "n/a", "next_round_after": "?"},
        "dispatch": {"total": 0, "done": 0, "failed": 0,
                     "active": 0, "avg_duration_ms": 0},
        "build": {"exists": False, "total_count": 0, "latest_name": None},
        "health": {"score": None, "last_report": None, "checks": {}},
        "health_trend": []
    }
    with open(os.path.join(dash_dir, 'data.json'), 'w') as f:
        json.dump(initial_data, f, indent=2, ensure_ascii=False)
    with open(os.path.join(dash_dir, 'history.json'), 'w') as f:
        json.dump({"health_trend": [], "build_size": []}, f, indent=2)
    ok(".mas/dashboards/ (data.json + history.json)")

    mcp_dir = os.path.join(project_path, '.mas', 'mcp')
    if os.path.exists(os.path.join(mcp_dir, 'package.json')):
        if dry_run:
            info(f"[DRY-RUN] npm install in .mas/mcp/")
        else:
            try:
                r = subprocess.run(['npm', 'install'], cwd=mcp_dir,
                                   capture_output=True, text=True, timeout=60)
                if r.returncode == 0:
                    ok(".mas/mcp/ npm install")
                else:
                    warn(f".mas/mcp/ npm install: {r.stderr.strip()[:80]}")
            except FileNotFoundError:
                warn(".mas/mcp/ npm: Node.js not installed — npm install skipped")
            except Exception as e:
                warn(f".mas/mcp/ npm install failed: {str(e)[:80]}")


def create_mas_mode(project_path, project_name_clean, dry_run=False):
    """Creates .mas-mode file for Mode detection."""
    mm_file = os.path.join(project_path, ".mas-mode")
    if dry_run:
        info(f"[DRY-RUN] .mas-mode = {project_name_clean}")
        return
    if os.path.exists(mm_file):
        info(f".mas-mode exists already — skipped")
        return
    with open(mm_file, 'w') as f:
        f.write(project_name_clean)
    ok(f".mas-mode = {project_name_clean}")


def resolve_components(comp_str):
    """Parst --components String in Set from Components."""
    if comp_str == "all":
        return {"rules", "state", "knowledge", "constitution", "enforcement", "recovery", "monitoring"}
    if comp_str == "minimal" or not comp_str:
        return set()
    return set(c.strip() for c in comp_str.split(",") if c.strip())


def copy_rules_full(project_path, dry_run=False):
    """copyrt all MAS-Rule-files (R01-R18 + Haerte-Leveln + Responsibility-Matrix)."""
    if dry_run:
        info("[DRY-RUN] .state/rules/: 6 files (rulen, hard_rules, rulen_2/4/5_extrem, responsibility_matrix)")
        return
    mas_rules = os.path.join(MAS_CONFIG, "..", "mas-engineer", ".state", "rules")
    dest_rules = os.path.join(project_path, ".state", "rules")
    os.makedirs(dest_rules, exist_ok=True)
    rule_files = ["rules.yaml", "hard_rules.yaml", "rules_2_normal.yaml",
                  "rules_4_strong.yaml", "rules_5_extreme.yaml", "responsibility_matrix.yaml"]
    copied = 0
    for rf in rule_files:
        src = os.path.join(mas_rules, rf)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(dest_rules, rf))
            copied += 1
    ok(f"Rulen: {copied}/{len(rule_files)} files copyrt")


def create_state_files(project_path, dry_run=False):
    """Creates empty/initiale State-files for das Projekt."""
    if dry_run:
        info("[DRY-RUN] .state/: changes.json, guardian.yaml, schedule.yaml, audit.log, health, checkpoints/")
        return
    from datetime import datetime
    import time
    state_dir = os.path.join(project_path, ".state")
    os.makedirs(state_dir, exist_ok=True)

    # changes.json: emptys Array
    with open(os.path.join(state_dir, "changes.json"), 'w') as f:
        json.dump([], f, indent=2)

    # guardian.yaml: empty Guardian-Struktur mit drift_log
    guardian = {
        "guardian": {
            "last_scan": None, "healthy": 0, "degraded": 0, "broken": 0,
            "total_yamls": 0, "note": "Empty Configuration — still no Scan",
            "categories": {"healthy_agents": [], "degraded_agents": [], "critical_agents": []},
            "findings_summary": {"total_issues": 0, "long_instructions": 0},
            "agents": {},
            "drift_log": [],
            "drift_summary": {"total_drifts": 0, "by_type": {}, "by_agent": {}, "trend": "stable"}
        }
    }
    with open(os.path.join(state_dir, "guardian.yaml"), 'w') as f:
        import yaml as _y
        _y.dump(guardian, f, default_flow_style=False, allow_unicode=True)

    # schedule.yaml: empty Verbetterungs-Historie
    schedule = {
        "version": "1.0.0", "last_updated": datetime.now().isoformat(),
        "history": [], "metrics": {}, "recommendation": {"status": "ready"}
    }
    with open(os.path.join(state_dir, "schedule.yaml"), 'w') as f:
        import yaml as _y
        _y.dump(schedule, f, default_flow_style=False, allow_unicode=True)

    # audit.log.jsonl: empty
    audit = os.path.join(state_dir, "audit.log.jsonl")
    if not os.path.exists(audit):
        open(audit, 'w').close()

    # .last_confirmation: current Timestamp
    with open(os.path.join(state_dir, ".last_confirmation"), 'w') as f:
        f.write(str(int(time.time())))

    # health-report.json + health-history.json
    hr = {"checks": [], "score": 0, "timestamp": None}
    with open(os.path.join(state_dir, "health-report.json"), 'w') as f:
        json.dump(hr, f, indent=2)
    hh = [{"timestamp": datetime.now().isoformat(), "score": 0}]
    with open(os.path.join(state_dir, "health-history.json"), 'w') as f:
        json.dump(hh, f, indent=2)

    # checkpoints Directory
    os.makedirs(os.path.join(state_dir, "checkpoints"), exist_ok=True)

    ok(f"State: changes.json, guardian.yaml, schedule.yaml, audit.log, health, checkpoints/")


def copy_knowledge_base(project_path, dry_run=False):
    """copyrt all 9 Knowledge-files ins Projekt."""
    src_knowledge = os.path.join(os.path.dirname(MAS_CONFIG), "mas-engineer", ".state", "knowledge")
    dst_knowledge = os.path.join(project_path, ".state", "knowledge")
    if dry_run:
        info(f"[DRY-RUN] .state/knowledge/: 9 files")
        return
    if not os.path.exists(src_knowledge):
        info("Knowledge-Source not found — skipped")
        return
    os.makedirs(dst_knowledge, exist_ok=True)
    count = 0
    for f in sorted(os.listdir(src_knowledge)):
        if f.endswith(".md"):
            shutil.copy2(os.path.join(src_knowledge, f), os.path.join(dst_knowledge, f))
            count += 1
    ok(f"Knowledge: {count} files after .state/knowledge/")


def copy_constitution(project_path, dry_run=False):
    """copyrt die MAS-Constitution als template ins Projekt."""
    src = os.path.join(os.path.dirname(MAS_CONFIG), "mas-engineer", "recipe", "sub", "sub_mas-master-constitution.yaml")
    dst = os.path.join(project_path, ".state", "constitution.yaml")
    if dry_run:
        info("[DRY-RUN] .state/constitution.yaml (11 Artikel)")
        return
    if os.path.exists(src):
        shutil.copy2(src, dst)
        ok("Constitution: .state/constitution.yaml (11 Artikel)")
    else:
        info("Constitution-template not found — skipped")


def copy_recovery_templates(project_path, dry_run=False):
    """copyrt 5 Recovery-Agent-templaten ins Projekt."""
    src_dir = os.path.join(os.path.dirname(MAS_CONFIG), "mas-engineer", "recipe", "template", "recovery")
    dst_dir = os.path.join(project_path, "recipe", "template", "recovery")
    if dry_run:
        info("[DRY-RUN] recipe/template/recovery/: immune, checkpoint, safezone, timeline, defib")
        return
    if not os.path.exists(src_dir):
        info("Recovery-Templates not found — skipped")
        return
    os.makedirs(dst_dir, exist_ok=True)
    count = 0
    for f in os.listdir(src_dir):
        if f.endswith(".yaml"):
            shutil.copy2(os.path.join(src_dir, f), os.path.join(dst_dir, f))
            count += 1
    ok(f"Recovery: {count} templaten after recipe/template/recovery/")


def copy_monitoring_files(project_path, dry_run=False):
    """Creates Monitoring-Infrastruktur-files."""
    state_dir = os.path.join(project_path, ".state")
    if dry_run:
        info("[DRY-RUN] .state/health-report.json + health-history.json")
        return
    os.makedirs(state_dir, exist_ok=True)
    hr = {"checks": [], "score": 0, "timestamp": None}
    with open(os.path.join(state_dir, "health-report.json"), 'w') as f:
        json.dump(hr, f, indent=2)
    import datetime as _dt
    hh = [{"timestamp": _dt.datetime.now().isoformat(), "score": 0}]
    with open(os.path.join(state_dir, "health-history.json"), 'w') as f:
        json.dump(hh, f, indent=2)
    ok("Monitoring: health-report.json + health-history.json")


def create_goosehints(project_path, project_name_clean, dry_run=False):
    """Creates .goosehints for Goose-Integration — never overwrites existing."""
    goosehints_file = os.path.join(project_path, ".goosehints")
    if os.path.exists(goosehints_file):
        info(f".goosehints exists already — skipped")
        return
    content = f"""# .goosehints — Generic-Improver Integration
# This project was initialized with dev_generic_init.py v{VERSION}.
#
# Tools via Symlink: tools/ → MAS-Installation
# Analysis: Remote via im-* agents (sub_mas-im-pipeline)
# Distribution: dev_build.sh --project

MAS_GENERIC_INIT_VERSION={VERSION}
MAS_ANALYSIS_MODE=remote
MAS_TOOLS=symlink
GOOSE_SESSION_TAG=[{project_name_clean}]

# Session-Tagging:
# Start each session with [{project_name_clean}] ...
# The Generic-Improver filters ONLY these sessions.
# Without tag: Fallback to working_dir or last not-MAS sessions.
"""
    goosehints_file = os.path.join(project_path, ".goosehints")
    if not dry_run:
        with open(goosehints_file, "w") as f:
            f.write(content)
    ok(f".goosehints")


def create_agent_template(project_path, dry_run=False):
    """copyrt agent_template.yaml ins Projekt — overwrites NEVER bestehende."""
    template_dst = os.path.join(project_path, "recipe", "template", "agent_template.yaml")
    if os.path.exists(template_dst):
        info(f"recipe/template/agent_template.yaml exists already — skipped")
        return

    template_src = os.path.join(WORKSPACE, "recipe", "template", "agent_template.yaml")
    if not os.path.exists(template_src):
        warn(f"agent_template.yaml not found in {template_src}")
        return

    template_dst_dir = os.path.join(project_path, "recipe", "template")
    if not dry_run:
        os.makedirs(template_dst_dir, exist_ok=True)
        shutil.copy2(template_src, template_dst)
    ok(f"recipe/template/agent_template.yaml ({os.path.getsize(template_src)} bytes)")


def cmd_init(project_name, dry_run=False, components="minimal"):
    """Initialisiert a new Projekt."""
    # Projekt-Path determine
    if os.path.isabs(project_name):
        project_path = project_name
        project_name = os.path.basename(project_path)
    else:
        project_path = os.path.abspath(project_name)

    if dry_run:
        print(f"\n{BOLD}DRY-RUN: Would initialize:{NC}")
        print(f"  Project: {project_name}")
        print(f"  Path:    {project_path}")
    else:
        header(f"Initialisiere Projekt '{project_name}'")
        print(f"  Path: {project_path}")

    # Check MAS-Installation
    mas_state = get_mas_state()
    if not mas_state["mas_installed"]:
        error("MAS-Installation not found!")
        error(f"  {MAS_CONFIG} exists not")
        return False
    ok(f"MAS-Installation found ({len(mas_state['im_agents'])} IM-Agenten, {len(mas_state['tools_list'])} Tools)")

    # Check ob Projekt exists
    if os.path.exists(project_path) and not dry_run:
        warn(f"Projekt exists already: {project_path}")
        info("Skip existing files (overwrite nothing)")
        existing = True
    else:
        existing = False

    # Directory create
    if not existing and not dry_run:
        os.makedirs(project_path, exist_ok=True)

    # 1. Symlink
    header("1. Symlink")
    create_symlinks(project_path, dry_run)

    # 2. Config
    header("2. Projekt-Configuration")
    project_name_clean = os.path.basename(project_path)
    create_project_config(project_path, project_name_clean, dry_run)

    # 3. Guidelines
    header("3. Wissen")
    create_guidelines(project_path, project_name_clean, dry_run)

    # 4. BP-Checklist
    create_bp_checklist(project_path, dry_run)

    # 5. Rulen
    header("4. Rule-System")
    create_rules(project_path, dry_run)

    # 6. Templates
    header("5. Agent-Templates")
    create_agent_template(project_path, dry_run)

    # 7. Tests
    header("6. Test scaffold")
    create_tests(project_path, dry_run)

    # 8. Workflows
    header("7. Workflow-Skelett")
    create_workflows(project_path, project_name_clean, dry_run)

    # 9. Git
    header("8. Git-Infrastruktur")
    create_git_infrastructure(project_path, dry_run)

    # 10. Goosehints
    create_goosehints(project_path, project_name_clean, dry_run)

    # 11. Dashboard
    create_dashboard_scaffold(project_path, dry_run)

    # 12. Mas-Mode
    create_mas_mode(project_path, project_name_clean, dry_run)

    # 13. Additional components (component-based)
    comps = resolve_components(components)
    if not dry_run and comps:
        header("13. MAS-Components")
    if "rules" in comps:
        copy_rules_full(project_path, dry_run)
    if "state" in comps:
        create_state_files(project_path, dry_run)
    if "knowledge" in comps:
        copy_knowledge_base(project_path, dry_run)
    if "constitution" in comps:
        copy_constitution(project_path, dry_run)
    if "recovery" in comps:
        copy_recovery_templates(project_path, dry_run)
    if "monitoring" in comps:
        copy_monitoring_files(project_path, dry_run)

    # Summary
    header("FINISHED")
    if not dry_run:
        ok(f"Projekt '{project_name_clean}' initialized ({project_path})")
        ok(f"0 Agenten copyrt — Symlink + Guidelines statt copy")
        ok("tools/ → Symlink to MAS installation")
        info("Analyse: remote via sub_mas-im-pipeline")
        info("Distribution: dev_build.sh --project → standalone ZIP")
        info("Dashboard: .mas/dashboards/ mit data.json for MCP App")
        info(".mas-mode:  mode file with project name")
        info("Setup:  goose run --recipe setup-dashboard.yaml (1x after Init)")
        print()
        info("Next Steps:")
        info("  1. Create Agenten mit dev_template_generator.py --create")
        info("  2. Optimiere mit sub_mas-im-pipeline (task=FULL_IMPROVEMENT)")
        info("  3. Distribuiere mit dev_build.sh --project")
        info("  4. Dashboard: goose session --with-extension 'node .mas/mcp/server.js'")
        info("  5. Install components: --components rules,state,knowledge,constitution,recovery,monitoring")
    return True


def cmd_bootstrap(project_name, dry_run=False, web_research=False):
    """Creates a complete MAS-framework (Bootstrap).
    Ruft generic-init --init mit --components all auf und portiert
    then die MAS-files ins Projekt."""
    if dry_run:
        info(f"[DRY-RUN] Bootstrap: {project_name}")
        info("[DRY-RUN] Step 1: generic-init --init --components all")
        info("[DRY-RUN] Step 2: recipe/sub/ (47 Agenten copyren)")
        info("[DRY-RUN] Step 3: recipe/dev-mas-engineer.yaml")
        info("[DRY-RUN] Step 4: tools/ (50 Tools copyren)")
        info("[DRY-RUN] Step 5: .mas/mcp/ (Dashboard MCP Server)")
        info("[DRY-RUN] Step 6: docs/ + .state/ Configuration")
        return True

    # Step 0: Web-Recherche-Note
    if web_research:
        header("Step 0: Web-Recherche (Note)")
        info("Web-Recherche via sub_mas-web-researcher is only im Goose-Chat possible.")
        info("Starte VOR dem Bootstrap eine Goose-Session und frage:")
        info('  "Recherchiere after currentn MAS-Techniken und show sie mit Evaluation"')
        info(f"Then: python3 dev_generic_init.py --bootstrap {project_name}")
        print()

    # Step 1: generic-init mit alln Components
    ok(f"Step 1: generic-init --init {project_name} --components all")
    cmd_init(project_name, dry_run=False, components="all")

    # Projekt-Path determine
    if os.path.isabs(project_name):
        project_path = project_name
    else:
        project_path = os.path.abspath(project_name)

    # Step 2: Portierung aus ~/.config/goose/ (der MAS Installation)
    mas_install = os.path.expanduser("~/.config/goose")
    mas_source = os.path.join(mas_install, "recipes", "..", "mas-engineer")

    header("Step 2: Sub-Agenten portieren")
    mas_subs = os.path.join(mas_source, "recipe", "sub")
    dest_subs = os.path.join(project_path, "recipe", "sub")
    if os.path.exists(mas_subs):
        shutil.copytree(mas_subs, dest_subs, dirs_exist_ok=True)
        ok(f"{len(os.listdir(mas_subs))} Sub-Agenten after recipe/sub/")

    header("Step 3: Main-Recipe portieren")
    mas_recipe = os.path.join(mas_source, "recipe")
    dest_recipe = os.path.join(project_path, "recipe")
    for f in ["dev-mas-engineer.yaml", "setup-dashboard.yaml", "dashboard-data-refresh.yaml"]:
        src = os.path.join(mas_recipe, f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(dest_recipe, f))
            ok(f"{f} portiert")

    header("Step 4: Tools portieren")
    mas_tools = os.path.join(mas_source, "tools")
    dest_tools = os.path.join(project_path, "tools")
    if os.path.exists(dest_tools) and os.path.islink(dest_tools):
        # Replace symlink with actual files
        os.unlink(dest_tools)
    if not os.path.exists(dest_tools):
        os.makedirs(dest_tools, exist_ok=True)
    count = 0
    for f in os.listdir(mas_tools):
        if f.endswith(('.py', '.sh')):
            shutil.copy2(os.path.join(mas_tools, f), os.path.join(dest_tools, f))
            count += 1
    ok(f"{count} Tools after tools/")

    header("Step 5: MCP Server portieren")
    mas_mcp = os.path.join(mas_source, ".mas", "mcp")
    dest_mcp = os.path.join(project_path, ".mas", "mcp")
    if os.path.exists(mas_mcp):
        os.makedirs(dest_mcp, exist_ok=True)
        for f in ["server.js", "dashboard.html", "package.json"]:
            src = os.path.join(mas_mcp, f)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(dest_mcp, f))
        ok("Dashboard MCP Server portiert")
        # npm install try
        try:
            subprocess.run(['npm', 'install'], cwd=dest_mcp, capture_output=True, text=True, timeout=60)
            ok("npm install in .mas/mcp/")
        except:
            warn("npm install failed — manuell execute")

    header("Step 6: Recovery-Templates + Docs")
    mas_recovery = os.path.join(mas_source, "recipe", "template", "recovery")
    dest_recovery = os.path.join(project_path, "recipe", "template", "recovery")
    if os.path.exists(mas_recovery):
        os.makedirs(dest_recovery, exist_ok=True)
        for f in os.listdir(mas_recovery):
            if f.endswith(".yaml"):
                shutil.copy2(os.path.join(mas_recovery, f), os.path.join(dest_recovery, f))
        ok("Recovery-Templates portiert")

    mas_recovery_agent = os.path.join(mas_source, "recipe", "sub")
    for f in ["sub_mas-recovery-checkpoint.yaml", "sub_mas-recovery-defib.yaml",
              "sub_mas-recovery-immune.yaml", "sub_mas-recovery-safezone.yaml",
              "sub_mas-recovery-timeline.yaml", "sub_mas-monitor-recovery.yaml"]:
        src = os.path.join(mas_recovery_agent, f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(dest_subs, f))
    ok("Recovery-Agenten portiert")

    header("Step 7: .mas-mode update")
    project_name_clean = os.path.basename(project_path)
    with open(os.path.join(project_path, ".mas-mode"), 'w') as f:
        f.write(project_name_clean)
    ok(f".mas-mode = {project_name_clean}")

    header("✅ BOOTSTRAP ABGESCHLOSSEN")
    ok(f"Projekt '{project_name_clean}' is a complete MAS-framework")
    info("47 Sub-Agenten, 50+ Tools, Dashboard, Monitoring, Recovery")
    info("Switch to the directory and start Goose:")
    info(f"  cd {project_path}")
    info(f"  goose run --recipe recipe/dev-mas-engineer.yaml")
    info(f"  oder: 'Zeig mir the framework Dashboard'")
    return True


def show_status():
    """Shows status of the MAS installation and symlinks."""
    header("MAS-Generic-Init Status")
    mas_state = get_mas_state()

    print(f"\nMAS-Installation:")
    print(f"  Installiert: {'✅' if mas_state['mas_installed'] else '❌'}")
    print(f"  IM-Agenten: {len(mas_state['im_agents'])}")
    print(f"  SI-Agenten: {len(mas_state['si_agents'])}")
    print(f"  Tools: {len(mas_state['tools_list'])}")

    # Check symlinks in current directory
    if os.path.exists("tools") and os.path.islink("tools"):
        target = os.readlink("tools")
        print(f"\nSymlink tools/ → {target}")
        print(f"  Valid: {'✅' if os.path.exists(target) else '❌'}")
    else:
        print(f"\nNo symlink in current directory")

    return True


def cmd_repair_symlinks():
    """Repairs broken symlinks."""
    header("Repair Symlinks")
    mas_state = get_mas_state()

    if not mas_state["tools_available"]:
        error("MAS-Installation not found — cannot repair symlink")
        return False

    if os.path.exists("tools"):
        if os.path.islink("tools"):
            target = os.readlink("tools")
            if target != MAS_TOOLS:
                warn(f"tools/ points to {target}, should point to {MAS_TOOLS}")
                os.unlink("tools")
                os.symlink(MAS_TOOLS, "tools")
                ok("Symlink repaired")
            else:
                ok("Symlink already correct")
        elif os.path.isdir("tools"):
            error("tools/ is an actual directory — cannot repair")
            info("Delete tools/ and run --init again")
            return False
    else:
        os.symlink(MAS_TOOLS, "tools")
        ok("Symlink created (was not present)")

    return True


def main():
    parser = argparse.ArgumentParser(description="Generic-Init Tool v" + VERSION)
    parser.add_argument("--init", metavar="PROJEKT", help="Projekt initialize")
    parser.add_argument("--bootstrap", metavar="PROJEKT", help="Complete MAS-framework bootstrap (generic-init + Portierung)")
    parser.add_argument("--status", action="store_true", help="Status anshow")
    parser.add_argument("--repair-symlinks", action="store_true", help="Repair symlinks")
    parser.add_argument("--dry-run", action="store_true", help="Only show, nothing create")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--web-research", action="store_true",
                        help="Show web-research note before bootstrap")
    parser.add_argument("--components", default="minimal",
                        help="Components: minimal|all|rules,state,knowledge,constitution,recovery,monitoring")

    args = parser.parse_args()
    verbose = args.verbose

    if args.bootstrap:
        success = cmd_bootstrap(args.bootstrap, dry_run=args.dry_run, web_research=args.web_research)
    elif args.init:
        success = cmd_init(args.init, dry_run=args.dry_run, components=args.components)
    elif args.status:
        success = cmd_status()
        sys.exit(0 if success else 1)
    elif args.repair_symlinks:
        success = cmd_repair_symlinks()
        sys.exit(0 if success else 1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
