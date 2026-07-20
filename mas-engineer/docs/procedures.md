# Procedures — MAS-Engineer

**Version:** 1.0.0

---

## Slash Commands

```
/develop              → Default dialog
/develop --scan       → Framework analysis (+ tests + governance check)
/develop --audit      → Deep analysis (+ config + sessions + tests)
/develop --harden     → Hardening (+ before/after tests + guardian)
/develop --patch ...  → Targeted change (+ regression check + guardian)
/develop --evolve ... → Evolution / new feature (+ tests + docs + guardian)
/develop --rollback    → Git log + rollback
/develop --install     → Framework + MAS install (+ tests + migration check)
/develop --uninstall   → Framework uninstall
/develop --test        → pytest against workspace
/develop --config-audit → 16 config consistency checks
/develop --prompt-review → Prompt quality check
/develop --recovery <cmd> → Phoenix Recovery (5 levels)
/develop --session-analytics → Correlate sessions with changes
/develop --doc-check   → Check docs currency
/develop --migrate <v> → Framework migration
/develop --guardian-check → Agent health (all sub-agents)
/status                → Framework status + agent health
/changes               → Last changes
```

## Tool Selection

Before every step:
1. **Can my Python tools handle this?** → yes: use dev_*.py
2. **Why not?** → MUST document why
3. **Goose built-ins** → cat, write, edit, bash, glob, grep, read
4. **Knowledge gaps** → consult https://goose-docs.ai

## Mode Detection (applies to all mode-aware agents)

1. Read `.mas-mode` from workspace or `~/.config/goose/.mas-mode`
2. `"framework"` → Framework mode: work on user's multi-agent system
3. `"mas"` → MAS mode: self-improvement
4. Other → Generic mode: new project initialization

## Improvement Pipeline (8 steps, via sub_mas-general-improver)

1. **Prerequisites** — mode detection, rule hardening, timing check
2. **Session data read** — im-session-reader (3-level project filter)
3. **Finding detection** — im-finder (53 feature types A-KK + LL + MM)
4. **Prioritization** — im-rank (dedup, sort, Constitution check)
5. **Patch design** — im-designer (type-specific logic)
6. **User review + apply** — yaml-editor (backup → patch → validate)
7. **Validation** — im-validator (yaml check, before/after scores)
8. **Push improvements** — generic-init PUSH_IMPROVEMENTS

## Recovery System (5 stages)

1. **Immune** — YAML/Python/Shell syntax check before every change
2. **Checkpoint** — Git-like snapshots in `.state/checkpoints/`
3. **Safezone** — Fork workspace (parallel work, merge only after validation)
4. **Timeline** — Automatic best checkpoint finder + restore
5. **Defib** — Emergency revival (minimal config: immune + timeline only)

## Framework Creation (via sub_mas-generic-init)

Option 1: Auto — All MAS components (symlink-based, lightweight)
Option 2: Component-wise — User chooses which components
For full MAS distribution deploys: use sub_mas-bootstrap

## Documentation Checking (via sub_mas-doc-generator)

The doc-generator checks these files for currency:
- `mas-engineer/docs/manifest.md` — Agent descriptions, tool lists
- `mas-engineer/docs/governance.md` — Rules, constitution, priorities
- `mas-engineer/docs/procedures.md` — Commands, workflows, procedures

It counts agents, tools, recipes, and verifies documented values match actual values.
