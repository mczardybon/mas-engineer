# R110-210 — MM9-EXT deferred-findings Klassifizierung

**Issue:** 8 MM9-EXT findings in `.mase/pipeline/findings.yaml` waren
nach R110-209 noch im Status "deferred". R110-210 klassifiziert sie
als false-positive (alle 8).

## Kontext
- MM9-EXT findings entstehen via `dev_self_audit.Pattern A` (regex auf
  "N sub-agents" / "N tools" / "N checks" in `recipe/instructions/*.md`).
- R110-209 hat den scanner um HTML-comment-detection erweitert
  (`tools/dev_im_finder_scan.py:1137-1176`, commit 766b501), sodass
  aktive hardcode-stale findings von 1 → 0 gingen.
- Die 8 in issue-db verbleibenden "deferred" findings sind alle
  false-positives: der scanner hat sie früher emittiert, der code-fix
  verhindert das jetzt — die issue-db-einträge sind nur historische
 残り.

## Klassifizierung der 8 deferred findings

| ID | Datei:Zeile | Aktueller Inhalt | Klassifikation als | Begründung |
|----|-------------|------------------|--------------------|-----------|
| MM9-EXT-001 | config-auditor.md:137 | `summary: "13 checks passed. 1 warning..."` | false-positive | Runtime-output YAML-code-block, nicht Doku-Count |
| MM9-EXT-006 | config-auditor.md:93 | `All 52 MAS sub-agents + 43 sub-agents` | false-positive | Z.92 HTML-comment-historical: "43 = opaque legacy grouping from 87322ec, do NOT update to 112" |
| MM9-EXT-008 | generic-init.md:39 | `(historical, 2026-07-25: 112 sub-agents / 58 tools)` | false-positive | Im historischen Kontext (gepaart mit current 116/80 in Z.40) |
| MM9-EXT-012 | team-packager.md:365 | `Team has more than 20 sub-agents: warn` | false-positive | Business-threshold (nicht Doku-count), mit Update-Hint-Comment |
| MM9-EXT-016 | generic-init.md:39 | `...58 tools)` (Z.39 right-side) | false-positive | Selber historischer Kommentar wie MM9-EXT-008 |
| MM9-EXT-018 | system-knowledge.md:133 | `mas-engineer-tools/: 80 Tools (69 dev_*.py + 10 *.sh + 1 *.yaml)` | false-positive | **GELTENDER STAND** — verifiziert: 69+10+1=80 (R110-209 verification) |
| MM9-EXT-019 | system-knowledge.md:149 | `All 80 Tools with Descriptions` | false-positive | **GELTENDER STAND** — verifiziert |
| MM9-EXT-020 | team-packager.md:65-66 | `current 116/80, 2026-08-19; (historical, 2026-07-25: 112/58)` | false-positive | **GELTENDER STAND + historischer Marker** |

## Status nach R110-210

| Typ | Status | Anzahl |
|-----|--------|--------|
| MM9-EXT | fixed | 7 (R110-209 commit 766b501) |
| MM9-EXT | false-positive | 13 (5 pre-existing + 8 R110-210) |
| MM9-EXT | (total) | 20 |

**Kein offener MM9-EXT finding übrig.**

## Scanner-Verbesserungen (bereits in 766b501)
- `tools/dev_im_finder_scan.py:1137-1140` — skip ganze HTML-comment-zeilen
- `tools/dev_im_finder_scan.py:1141-1153` — skip lines preceded by
  HTML-comment-historical-marker
- `tools/dev_im_finder_scan.py:1154-1162` — skip lines preceded by
  inline-historical-parenthetical
- `tools/dev_im_finder_scan.py:1163-1169` — skip lines mit eigener
  inline-historical-referenz
- `tools/dev_im_finder_scan.py:1170-1176` — skip canonical "N checks"
  deklarationen

Diese Fixes decken die historischen-praktiken im mas-engineer ab
(snapshot semantics: dokumentierter wert vom 2026-07-25 plus
current 2026-08-19).

## Verifikation (post-R110-209, pre-R110-210)
```
$ python3 tools/dev_im_finder_scan.py
HARDCODE-STALE findings: 0   # exakt 0, vorher 1 (F-082)
total findings: 81            # exakt 1 weniger als vorher (82 → 81)
```

## Lessons learned
- R110-78 spec-drift: scanner-emitierte findings müssen mit
  ground-truth-verify abgeglichen werden, nicht blind gefixt.
- R110-209 body-claim-drift: titel sagte "4 highest-priority", tatsächlich
  7 fixed + scanner-fixture commits. R110-210 korrigiert die Klassifikation
  der issue-db-transparent (kein force-push, keine body-claim-lüge).
