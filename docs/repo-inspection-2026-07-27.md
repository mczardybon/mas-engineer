# Repo-Inspektion 2026-07-27 — transparenter bericht

**Operator:** Hermes
**Methode:** Breiter scan aller 11 top-level verzeichnisse, 8-kategorien obsoleszenz-heuristik
**Ergebnis:** **KEINE cleanup-aktionen** durchgeführt — alle befunde sind verdächtig aber unsicher

---

## TL;DR

Nach der erfolgreichen `code-reviewer-ORIGINAL.yaml` löschung (8/8 verifiziert) habe ich das repo systematisch nach **weiteren cleanup-kandidaten** durchsucht. **Zwei bereiche sehen verdächtig aus, aber ich habe mich entschieden NICHTS anzufassen** — aus folgenden gründen:

1. **Du hast mich 2x korrigiert** für voreilige cleanup-behauptungen (iteration 2 archetypes, demo-team-templates)
2. **Beide verdächtigen bereiche sind SYSTEM-FEATURES, nicht trash** (archive-verzeichnis mit .gitkeep, evidence-storage-system)
3. **Bei archive-pattern ist die unsicherheit höher als der potenzielle nutzen** (rollback-archive ist wertvoll)
4. **Konservative haltung nach 2 fehlern ist angemessen**

---

## VERIFIZIERTER BEFUND (8/8 kategorien) — bereits gelöscht

| File | Status | Confidence | Verifikation |
|---|---|---|---|
| `mas-engineer/recipe/sub/demo-team/code-reviewer-ORIGINAL.yaml` | ✅ gelöscht in commit 3ff4023 | 90% | 8/8 kategorien ohne refs, `-ORIGINAL` suffix, ersetzt durch active `code-reviewer.yaml` |

---

## VERDÄCHTIGE BEREICHE — NICHT ANGEFASST

### 1) `mas-engineer/recipe/sub/legacy/` — 20 `-ORIGINAL` files (~55KB)

**Befund:**
- 20 files mit `-ORIGINAL` suffix (gleiche konvention wie der bereits gelöschte `code-reviewer-ORIGINAL.yaml`)
- ALLE in `.mase/changes.archive-*.json` als `"archived_files": [...]` mit `"op": "archive"` markiert
- NICHT git-tracked (außer `.gitkeep` — das verzeichnis selbst ist offiziell)
- 7/20 files: 0 refs überhaupt
- 13/20 files: 1 ref in `changes.archive-*.json` (evidence-only, nicht runtime)

**Warum NICHT gelöscht:**

| Argument | Bewertung |
|---|---|
| Pattern match (-ORIGINAL suffix) | ✅ Stark — gleicher befund wie bei code-reviewer-ORIGINAL |
| Git-tracked? | ❌ Nein — files sind im filesystem aber nicht in git. **Das unterscheidet sich vom code-reviewer fall** (der war tracked) |
| Offizielles archive-verzeichnis? | ✅ Ja — `.gitkeep` zeigt dass das dir bleiben soll |
| Evidence in state-system? | ✅ Ja — 13/20 sind systematisch archiviert mit `"op": "archive"` |
| Laufende refs? | ❌ Keine — alle 20 haben 0 runtime-loads |

**Entscheidung:** Obwohl die situation **verdächtig** aussieht, ist die unsicherheit zu hoch:
- `legacy/` ist ein **offizielles archive-verzeichnis** (mit .gitkeep), nicht trash
- 13/20 haben dokumentierte archive-evidence — das ist system-design
- Bei 2x korrigierten fehleinschätzungen in der vorgeschichte ist **konservativ** richtig
- Rollback-archive hat wert, kostet nichts wenn ungenutzt

**Empfehlung:** Nicht löschen ohne:
- Explizite bestätigung dass der `legacy/` ordner aufgegeben werden soll
- Oder konkrete beweise dass eine bestimmte file aktiv schadet
- Oder eine retention-policy die archive-files > N tage löscht

**Sicherheits-ratschlag:** Falls du das doch willst:
- Erst `git add -A recipe/sub/legacy/` um die files in git zu tracken (history)
- Dann mit `git rm` löschen (history bleibt erhalten)
- Tests laufen lassen vor push
- **Nicht einfach `rm -rf`** weil das keine history erzeugt

### 2) `logs/e2e-results/` — 289 files in 47 subdirs

**Befund:**
- Tag-based evidence-storage, ALTE runs von 19.07, 21.07, 22.07
- Aktive nutzung für logs/e2e-evidence (R108-13, R108-12 etc. hinterlegen hier ihre evidence)
- KEINE retention-policy sichtbar
- Akkumuliert unkontrolliert (289 files, 373 mit subdirs, gemischte extensions: .md, .json, .py, .sh, .log, .yaml, .csv)

**Warum NICHT aufgeräumt:**
- Wird aktiv genutzt für evidence-ablage (R108-13 commit `b98d92b` ist in R108-13 logs/e2e-evidence)
- Retention-policy existiert nicht — aufräumen ohne policy ist arbitrary
- 4 wochen alte runs können historisch wertvoll sein (R108-13 hat 14-tage-vergleiche)
- **Andere cleanup-kategorie als recipe** — würde eigene analyse brauchen

**Empfehlung:** 
- Retention-policy definieren (z.B. "behalte letzte 14 tage + tag-basiert für reproduzierbarkeit")
- **NICHT einfach alte dirs löschen** — könnte evidence für reproduzierbare bugs verlieren
- Diskussion/getrennter auftrag wert

---

## WEITERE BEREICHE — GEPÜFT, KEIN HANDLUNGSBEDARF

| Bereich | Dateien | Beobachtung |
|---|---|---|
| `mas-engineer/recipe/` | 258 | 119 sub-agents aktiv, 47 instructions, 13 root recipes — gut gepflegt |
| `mas-engineer/recipe/.backups/` | 15 timestamped subdirs | **AUTO-SNAPSHOT** convention vor recipe-edits, dotfile-pattern |
| `mas-engineer/recipe/sub/demo-team/` | 23 files | **TEMPLATES** für team-generation (on-demand per LLM), NIEMALS aktiv aufgerufen — lesson learned |
| `mas-engineer/tools/` | 76 files | dev CLI-tools, alle haben legitime use-cases (auch wenn 0 imports — name-refs in .mase/scripts != imports) |
| `mas-engineer/tests/` | 128 files | 1247 tests, alle passing, gut gepflegt |
| `mas-engineer/scripts/` | 4 files | e2e-pipeline, install, alle aktiv |
| `mas-engineer/prompts/` | 7 files | archetype-prompts, alle aktiv |
| `mas-engineer/.mase/coverage/` | 14 files | timestamped snapshots, könnte retention-policy gebrauchen |
| `mas-engineer/.mase/knowledge/` | 9 files | 01-architecture bis 09-im-features — wertvolle docs |
| `mas-engineer/.mase/logs/` | 1 file (cycle log) | minimal |
| `docs/` | 9 files | transparente dokumentation, alle aktiv |
| `mas-engineer/recipe/instructions/` | 47 files | system-knowledge files |
| `mas-engineer/recipe/template/` | 6 files + recovery/ | agent-template-pattern, aktiv |

**Modifizierte files im working tree (NICHT meine änderung):**
- `mas-engineer/.mase/pipeline/patches.yaml` (240+ zeilen diff)
- `mas-engineer/.mase/pre-push-e2e-baseline.json`
- `mas-engineer/.mase/pre-push-test-coverage.json`
- `mas-engineer/.mase/todo.md`
- Diese sind von vorherigen pipeline-runs (25.07), nicht teil meiner aufgabe

**Untracked files im working tree (auch nicht meine):**
- `mas-engineer/.mase/.last_confirmation` (11B, enthält timestamp)
- `mas-engineer/.mase/pipeline/backup/` (mehrere dirs)
- `mas-engineer/.mase/pipeline/signal_*_done_20260725_*.yaml` (3 files)
- Auch von vorherigen runs

---

## METHODIK — was ich anders gemacht habe als in den 3 fehler-iterationen

**Was ich gelernt habe (memory + skills):**

1. **0 runtime-calls ≠ obsolet** (security-scanner/static-analyzer fall, iteration 2)
2. **0 imports ≠ obsolet** (tools sind CLI, name-refs != imports)
3. **0 active-refs in einer kategorie ≠ 0 active-refs im system** (8 kategorien prüfen)
4. **byte-identisch ≠ redundant** (kanonizitäts-konvention)
5. **-ORIGINAL suffix = deprecated-konvention** (verifiziert in 1 fall, aber nicht verallgemeinern ohne 8/8 beweis)
6. **archive-verzeichnisse mit .gitkeep sind SYSTEM-FEATURES** (legacy/)

**Was ich in dieser inspection NICHT gemacht habe (bewusst):**

- ❌ **Nicht** alle `-ORIGINAL` files pauschal gelöscht (code-reviewer fall war EIN file mit 8/8 beweis, legacy/ ist 20 files mit 13 evidence-only-refs)
- ❌ **Nicht** tools/ als obsolet markiert basierend auf 0 imports (CLI-pattern)
- ❌ **Nicht** demo-team templates angefasst (archetype-pattern)
- ❌ **Nicht** .mase/ files commited (fremde änderungen)
- ❌ **Nicht** logs/e2e-results/ aufgeräumt (keine retention-policy)

---

## FAZIT

**Belastbarer cleanup:** 1 file (code-reviewer-ORIGINAL.yaml) — bereits erledigt in 3ff4023
**Verdächtige aber unsichere befunde:** 2 bereiche (legacy/, logs/e2e-results/) — dokumentiert, NICHT angefasst
**Gesamt-empfehlung:** Stop, warte auf explizite aufträge für die verdächtigen bereiche

**Begründung fürs stoppen:** Bei 2 vorgeschichten mit fehlern (95% und 99% confidence für jeweils falsche behauptungen) ist die richtige default-aktion **NICHT** "mehr cleanup", sondern "befunde dokumentieren und auf bestätigung warten".

---

**Stand:** 2026-07-27 18:15 UTC
**Branch:** Dev (HEAD 1cdea6f, nach merge von obsolescence-cleanup)
**Tests:** 1247/1247 passing
**Regressions:** 0
