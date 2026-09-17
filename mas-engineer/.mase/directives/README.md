# IM-Pipeline Directives

Direktiven sind **vorgefertigte Spec-Pakete** fuer mas-engineer's
self-improvement IM-Pipeline (S1-S8). Sie sagen der IM-Pipeline
WAS zu tun ist, ohne dass mas-engineer raten muss.

## Was ist eine Direktive?

Eine Direktive ist ein **Absichts-Spec** (intent + concrete
implementation contract), geschrieben vom User (oder einem
externen Agent), konsumiert von mas-engineer's IM-pipeline
FIND->RANK->DESIGN->VALIDATE->APPLY loop.

Eine Direktive ENTHAELT KEINEN fertigen Patch. Der Patch wird
von im-designer erzeugt, basierend auf der Direktive.

## Naming-Convention

```
R<NR>-<topic>.md
```

- `R` = "Reconstruction" / "R-Run" / historisch gewachsen
- `<NR>` = 3-stellige laufende Nummer, aufsteigend (R001, R002, ...)
- `<topic>` = lowercase, hyphen-separated, kurz

## Workflow (User-Seite)

1. Idee + spec in `.mase/directives/R<NR>-<topic>.md` schreiben
2. Datei committen auf `cleanup` branch
3. Naechster IM-pipeline-run picked das file automatisch auf
4. Status wird in der Direktive selbst getrackt (PHASE markers)
5. Wenn alle PHASEN done, Direktive wird mit `STATUS: DONE` markiert

## Workflow (mas-engineer IM-Pipeline)

```
.im/IM-pipeline.yaml stage S1 (FIND)
  -> scan .mase/directives/*.md
  -> parse "PHASE N" + "DIREKTIVE N" markers
  -> emit finding pro Direktive mit prio P2 (default)

stage S3 (RANK)
  -> sort findings by PHASE-1-first (low-risk + immediate-impact)
  -> dann PHASE 2, dann PHASE 3

stage S4 (DESIGN)
  -> liest die Direktive als spec
  -> erzeugt einen patch (kein auto-fix, kein raten)
  -> nutzt die 9-section spec wenn vorhanden

stage S5 (VALIDATE)
  -> pytest + pre-push-validator + spec-invariants
  -> bei fail: rollback + finding
  -> bei success: weiter zu S6 (APPLY)

stage S7 (SUMMARIZE)
  -> commit + push
  -> Direktive bleibt, mit PHASE-N markers aktualisiert
```

## Aktive Direktiven

| Datei | Status | PHASEN | Topic |
|---|---|---|---|
| [R110-78-spec-drift.md](R110-78-spec-drift.md) | OPEN (3 PHASEN, P1 spec done) | 1-3 | verhindert spec-drift bei count/version-korrekturen |

R110-78 wurde 2026-08-03 nach R110-71 spec-drift incident
(R110-78 commit 9c73100 admitted) erstellt. Status wird
aktualisiert sobald mas-engineer PHASE 1+ umgesetzt hat.

## Was gehoert HIERHER

- Absichts-specs (was + warum + acceptance criteria)
- Konkrete implementation contracts (9-section spec)
- PHASE markers (welcher block zuerst, stop-punkte)
- Cross-references (welche commit hat was korrigiert)
- NICHT-ZU-TUN listen (footguns, anti-patterns)
- Test-strategie (wie verifiziert man erfolg)

## Was gehoert NICHT hierher

- Echte code-patches (die kommen von im-designer)
- Echte YAML-recipes (die gehoeren in `recipe/sub/`)
- Echte Python-tools (die gehoeren in `tools/`)
- User-persona-notizen (die gehoeren in `docs/`)
- Commit-message drafts (die gehoeren in commit body, nicht hier)
- Session-logs (die gehoeren in `logs/e2e-results/<session>/`)

## Konventionen

- Sprache: deutsch (konsistent mit R110-78-original)
- Zeilenlaenge: frei (markdown, kein hard-wrap)
- Max file-size: 800 lines (darueber: splitten in 2 direktiven)
- Pro direktive: 1 topic, 3-5 implementation steps
- YAML-headers nur wenn maschinen-parsbar noetig (sonst plain text)
- Idempotenz-rules immer in section 7 ("NICHT TUN")

## Verwandte Files

- `mas-engineer/recipe/sub/sub_mas-im-finder.yaml` -- scannt
  .mase/directives/ als teil von IM-pipeline FIND phase
- `mas-engineer/recipe/sub/sub_mas-pre-push-validator.yaml`
  -- final gate BEVOR push, nutzt spec-invariants
- `mas-engineer/tools/dev_spec_invariant.py` (PHASE 3) --
  prüft test.asserts == recipe_says invariant
- `skills/SKILLS-INDEX.md` (Hermes-side) -- mas-engineer ist
  nicht fuer directives zustaendig, das ist eine separate
  konvention
