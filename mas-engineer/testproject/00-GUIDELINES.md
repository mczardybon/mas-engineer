# 00-GUIDELINES.md — Projekt-Guidelines

Initialisiert mit dev_generic_init.py v1.0.0

## Reasonprinzipien
- Jeder Agent = 1 YAML-file in `recipe/sub/`
- Agenten are Goose-Sub-Agents (no external Services)
- Communication via YAML-Structs
- Domain separation: only im eigenen Projekt-Directory write

## Agent-Typen (reference)
^| type | Task | Example |
|-----|---------|----------|
| Analyse | Data read + pattern detect | sub_testproject-analyst |
| Recovery | Aus Errorn erholen | sub_testproject-checkpoint |
| Monitoring | Monitor metrics | sub_testproject-health |
| Generator | Documents/Signale generate | sub_testproject-docgen |
| Verbetterung | Analyzen + Optimieren | sub_testproject-improver |

## YAML-Struktur
```yaml
name: sub_testproject-mein-agent
version: 1.0.0
settings:
  timeout: 120
  max_steps: 30
instructions: |
  # sub_{project}-mein-agent — 🎯 Kurzdescription
  ...
```

## Best Practices
1. **Prompts**: < 300 Zeichen
2. **Instructions**: < 2000 Zeichen
3. **⛔ Rules**: Run before each critical step
4. **Version**: always in erster line
5. **Namen**: sub_{project}-analyst

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
dev_build.sh --project testproject   # → standalone ZIP without MAS
```
