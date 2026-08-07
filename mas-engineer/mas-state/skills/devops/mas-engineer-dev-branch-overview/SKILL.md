---
name: mas-engineer-dev-branch-overview
description: Kompletter Überblick über den mas-engineer dev branch — Fähigkeiten, Test-Infrastruktur, Architektur. Verwenden wenn man mit mas-engineer arbeitet oder wissen muss was es kann.
category: devops
---

# MAS-Engineer Dev Branch — Overview (Stand 2026-07-27, R108)

## Repo
- URL: `https://github.com/mczardybon/mas-engineer.git`
- Branch: `Dev` (working branch)
- 1015 files, saubere historie (19+ commits, R108 100% pass)
- Path: `/workspace/dev-branch/` (lokaler clone)

## Was ist MAS-Engineer?

Ein **Multi-Agent Framework** für automatisiertes Software-Engineering. 139 sub-agents in 9 Kategorien. Verwendet Goose (AI Agent CLI) als Runtime, DeepSeek-V4-Flash als LLM.

## Architektur (3 Schichten)

### Schicht 1: Root-Recipes (5 files, ~2KB)
- `dev-mas-engineer.yaml` — Haupt-Entry-Point
- `root_recipe.yaml` — Generic root
- `e2e-verify-*.yaml` (3x) — E2E verification entry points
- `setup-dashboard.yaml` — Dashboard setup
- `test-fix-failures.yaml` — Test-failure fixer
- `test-mas-user.yaml` — User-mode test

### Schicht 2: Director-Agents (15+ files, ~2KB)
Orchestratoren, die zu spezialisierten agents delegieren. Beispiele:
- `sub_mas-dev-director` — 5 Delegation-Domains: analyze, build, test, observe, git
- `sub_mas-general-improver` — 8-stage Improvement-Pipeline (S0-S8)
- `sub_mas-degradation-director` — Degradation handling
- `sub_mas-team-packager-director` — Team packaging (NN1 split)
- `sub_mas-test-reporter-director` — Test reporting (NN1 split)
- `sub_mas-dashboard-director` — Dashboard data

### Schicht 3: Sub-Agents (139+ sub_mas-*.yaml files)
Spezialisierte agents. Master-Constitution referenziert von ALLEN. Wichtigste:
- IM-Pipeline (6): `im-session-reader`, `im-finder`, `im-rank`, `im-designer`, `im-validator`, `general-improver`
- Dev-Team (5): `dev-analyzer`, `dev-builder`, `dev-tester`, `dev-observer`, `git-operator` (v2.0.0 CLEAN-COMMIT)
- Recovery/Phoenix (5): `recovery-immune`, `recovery-checkpoint`, `recovery-safezone`, `recovery-timeline`, `recovery-defib`
- Monitoring (4): `monitor-health`, `monitor-runtime`, `monitor-session`, `monitor-recovery`
- Analysis (7+): `framework-scanner`, `framework-knowledge`, `config-auditor`, `prompt-engineer`, `goose-expert`, `test-runner`
- Security (4): `security-secrets-scanner`, `security-cmd-injection-scanner`, `security-deserialize-scanner`, `security-sqli-scanner`
- Test-Fix-Failures (6): `tff-finder`, `tff-ranker`, `tff-designer`, `tff-applier`, `tff-syntax-validator`, `tff-rule-validator`, `tff-crossref-validator`
- Code-Review (12+): `cr-orchestrator`, `cr-synthesizer-*`, `cr-validator-*`, `cr-reporter-*`
- E2E (10): `e2e-auto-repair-*`, `e2e-german-fixes-*`, `e2e-phoenix-fixes-*`

## Tools (75 files in `mas-engineer/tools/`)
- 50 Python-Tools: `dev_*.py` (analyst, architect, builder, editor, gatekeeper, etc.)
- 6 Shell-Tools: `dev_*.sh`
- 1 YAML-Tool: `auto-dashboard-v2-update.yaml`
- Deterministic scripts für alle sub-agents (R89 Phase 7: LLM-interpretierte calls → script-wrapped)

## Test-Infrastruktur (124 test files in `mas-engineer/tests/`)

### Pattern (alle test_sub_mas_*.py)
**Sanity-Tests via Pytest** — KEIN E2E mit echtem LLM, sondern statische YAML/structure validation:
1. Recipe exists
2. YAML valid parseable
3. Required fields present (name, version, prompt, settings, instructions)
4. Master-constitution referenced
5. Delegation targets vorhanden
6. R01/R09/R10 deklariert
7. R-spezifische checks (z.B. dev-director hat 5 domains, git-operator CLEAN-COMMIT)

### Kategorien
- **im-pipeline** (9): session-reader, finder, rank, designer, validator, general-improver, monitor-runtime, recovery-immune, recovery-timeline
- **e2e** (10): auto-repair (3), german-fixes (4), phoenix-fixes (3)
- **dashboard** (7): builder, collector, data-reader, director, generator, refresh, setup
- **dev-team** (6): director, analyzer, builder, tester, observer, plus root recipe test
- **recipe-validation** (7): root, agent-template, instructions, other-types, thin-delegators, recipe-designer, recipe-manager
- **degradation** (5): director, analyzer, handler, planner, reporter
- **recovery** (5): monitor-recovery, checkpoint, defib, safezone, template-recovery
- **other** (72): alle übrigen sub-agents (1 test pro agent + framework-tools + security + tff + cr + config-auditor etc.)
- **monitor** (2): monitor-health, monitor-session
- **governance** (1): master-constitution
- **pre-check-benchmark** (1): pre-check performance

### Run
```bash
cd /workspace/dev-branch/mas-engineer
python3 -m pytest tests/ -v
```

## Echte E2E-Tests (live, mit LLM)

### `e2e-results/` (10+ runs, alle mit echter DeepSeek-API)
- `2026-07-19/`, `2026-07-21-*` (multiple), `2026-07-22-*`, `2026-07-23-*`, `2026-07-24-*`, `2026-07-25-*`, `2026-07-27-*`
- Format pro run: `<run-name>/<recipe>.yaml` + `run_*.py` script + log/output files
- Testet vollständige goose-runs mit echtem LLM, nicht nur YAML-validation

### Wichtigste E2E-Runs (R108/R109)
- `2026-07-27-sales-30x` — 30 runs Sales-Team, 30/30 PASS, Wilson [88.6%, 100%]
- `2026-07-27-demo-team-15x` — 15 runs Demo-Team
- `2026-07-27-demo-team-build-optimize-tasks-15x` — 15 runs, 15/15 cycles
- `2026-07-22-real-e2e` — 28 runs Sales-Team (3 real teams)
- `2026-07-24-demo-team-generation-rate` — 14 runs für Health-Report

### Run-Scripts (`run_*.py` im e2e-results/)
- `run_30x_sales.py` (9.7KB) — 30x sales-orchestrator test
- `run_15x_demo.py` (10.1KB) — 15x demo-team test
- `run_translators.py` (2.4KB) — translator demo
- `tools/run_demo_team_15x_build_optimize_tasks.py` (12.3KB) — build/optimize 15x

**Pattern:** argparse mit `--n`, `--start`, `--timeout`, `--per-run-sleep`, `--recipe`, `--output-dir`. Default `subprocess.run(goose run --recipe ... --no-session --params query=...)` mit `capture_output=True` + `timeout=...`. Result ist JSON oder log-file.

## Master-Constitution (gilt für ALLE 56+ agents)

### 11 Articles
1. **Role Assignment** — Domänen-Verantwortung
2. **Constitutional Rank** — Höchste Regel
3. **Scope Discipline** — Nur definierte Tasks
4. **Communication Log** — specialist_result/error/handover
5. **Signal Discipline** — Machine-readable YAML
6. **Quality Obligation** — Coverage + thresholds
7. **No Plan Bypass** — Keine unautorisierten Erweiterungen
8. **Escalation Obligation** — P0 = sofortiger Stop
9. **Worktree Compliance** — Nur in worktree arbeiten
10. **Burden of Proof** — Steps + result + quantified quality
11. **Commandment of Readability** — Conventions + BEGIN/END comments

### 4+ SOT Rules (gelten für ALLE Operationen)
- **R01 CONFIRMATION** — Vor write/edit/shell: PLAN+WAIT auf user ✅
- **R04 GENERAL-IMPROVER** — NEVER edit general-improver.yaml (no recursion)
- **R09 DOMAIN** — Stay within target workspace. NO cross-domain writes
- **R10 CORONASHIELD** — Validate YAML (yaml.safe_load) vor storage
- **R11 GOOSE-EXPERT** — MANDATORY summon für Goose-architektur tasks. Verdict MUSS attached sein. Failing = REJECTED

## Settings-Konvention
- `timeout`: 600 (director), 180 (git-operator)
- `max_steps`/`max_turns`: 100
- `goose_provider`: openai
- `goose_model`: deepseek-v4-flash
- `temperature`: 0.2 (git), 0.3 (default)

## Run-Command-Pattern
```bash
export PATH="/root/.local/bin:$PATH"
export DEEPSEEK_API_KEY="sk-..."
export OPENAI_API_KEY="$DEEPSEEK_API_KEY"  # weil goose openai-provider nutzt
export OPENAI_HOST="https://api.deepseek.com"
export GOOSE_TELEMETRY_ENABLED="false"

goose run --recipe <recipe.yaml> --no-session --params query="..."
# ODER: --no-session -q (quiet mode)
```

## Wichtige Sub-Recipe-Discovery Lessons
- Sub-recipes in `sub_recipes:` werden relativ zu HAUPT-recipe aufgelöst
- `--no-session` flag in goose 1.44 nicht mehr unterstützt (war in 1.42)
- Recipes müssen nach `~/.config/goose/recipes/` installiert sein (via `install.sh`)
- DeepSeek-Key muss in BOTH `.env` (als DEEPSEEK_API_KEY) UND als OPENAI_API_KEY exportiert werden

## Erfolgs-Metriken
- **R108 (2026-07-27)**: 100% (19 commits, 1218/1218 tests)
- **Sales-30x**: 30/30 PASS, Wilson [88.6%, 100%]
- **Build-optimize-tasks 3-team POC**: 15/15 cycles, Wilson [79.6%, 100%]
