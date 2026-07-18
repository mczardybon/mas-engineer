# PLAN: Alle 132 offenen findings eliminieren

**Stand:** 09d721b (post 4 commits)
**Source:** `.state/pipeline/findings.yaml` (24.898 bytes, 132 findings)
**Goal:** Alle findings = 0 (oder so weit wie es geht mit vertretbarem Aufwand)

---

## 0. INVENTAR (was uns erwartet)

132 findings in 12 Typen, verteilt auf 50 Dateien (49 sub_mas-*.yaml + 1 tools/auto-dashboard-v2-update.yaml).

| Typ    | #  | Severity | Was es bedeutet                                       |
|--------|----|---------:|-------------------------------------------------------|
| KK5    | 41 | 🟡 med   | R10 (CORONASHIELD) missing — kein YAML-Schutz        |
| GG5    | 38 | 🟡 med   | instructions > 2000 chars                            |
| O2     | 16 | 🟡 med   | Reference to non-existent file (stale path)          |
| KK2    | 10 | 🟡 med   | dev_rule_checker reference missing                    |
| KK3    |  6 | 🟡 med   | R01 (CONFIRMATION) missing                           |
| KK4    |  6 | 🟡 med   | R09 (DOMAIN) missing                                 |
| KK6    |  6 | 🟡 med   | Only 1/5 SOT-Refs — needs ≥3                         |
| MM3    |  4 | 🟡 med   | prompt: no ⛔ (Boundary-Indicator)                   |
| GG4    |  2 | 🟡 med   | prompt < 100 chars                                    |
| GG3    |  1 | 🟢 low   | prompt: no emoji                                     |
| MM4    |  1 | 🟢 low   | title: no emoji                                      |
| GG     |  1 | 🟡 med   | no version field                                     |
| **Σ**  |132 |          |                                                       |

**Betroffene Dateien-Top-Liste (sortiert nach findings-Anzahl):**
- sub_mas-dashboard-refresh.yaml  → 5 findings (KK2, KK3, KK4, KK5, KK6)
- sub_mas-doc-writer.yaml         → 5 findings (KK2, KK3, KK4, KK5, KK6)
- sub_mas-git-operator.yaml       → 5 findings (KK2, KK3, KK4, KK5, KK6)
- sub_mas-json-utility.yaml       → 5 findings (KK2, KK3, KK4, KK5, KK6)
- sub_mas-python-repair.yaml      → 6 findings (GG5, KK2, KK3, KK4, KK5, KK6)
- sub_mas-recipe-designer.yaml    → 6 findings (GG5, KK2, KK3, KK4, KK5, KK6)
- sub_mas-im-validator.yaml       → 5 findings (GG3, GG4, GG5, MM3, O2)
- tools/auto-dashboard-v2-update.yaml → 1 finding (GG)

---

## 1. STRATEGIE — wirtschaftlich, nicht dogmatisch

**Prinzipien:**
1. **Reihenfolge = Wert:** Was am einfachsten viele findings fixt, zuerst.
2. **1 Pass pro Finding-Typ, alle betroffenen Dateien gleichzeitig.**
3. **Verifikation nach JEDEM Pass** (yaml.safe_load + pre-push-validator).
4. **Bei Stale-References (O2) pragmatisch:** entweder Pfad fixen oder Referenz entfernen — beides OK.
5. **Bei GG5 (instructions > 2000 chars):** der Code funktioniert, das ist ein Style-Issue. **Niedrige Prio** — externe .md-Datei pro Recipe ist viel Aufwand für wenig Wert. Ich werde es in 1 Sammelpass lösen, falls Zeit reicht.

**Estimated Aufwand pro Pass (parallelisiert mit 8 Workern):**
- KK2/KK3/KK4/KK5 (1-line Footer-Insertionen): ~30s
- KK6 (SOT-Refs hinzufügen): ~60s
- O2 (path analysis + edit): ~120s
- MM3/MM4 (emoji insert): ~20s
- GG3/GG4 (prompt-extension): ~30s
- GG5 (instructions outsource): ~600s (groß, aber parallel)
- GG (version field): ~5s

---

## 2. PHASENPLAN (Reihenfolge)

### PHASE C1 — Footer-Footers (KK2, KK3, KK4, KK5)
- **Was:** 4 standardisierte Footer-Zeilen in jeden betroffenen Recipe-prompt einbauen:
  - KK2: `## dev_rule_checker\npython3 tools/dev_rule_checker.py --all --action "{action}"`
  - KK3: `## R01 CONFIRMATION\nBefore wwrite/edit — Show plan + WAIT for ✅`
  - KK4: `## R09 DOMAIN\nMode determines domain. mas→mas-engineer/, framework→framework/`
  - KK5: `## R10 CORONASHIELD\nEvery YAML must be validated before storing (via sub_mas-recovery-immune)`
- **Wo:** alle Dateien in der KK-Liste (41 + 10 + 6 + 6 = unique ~30 Dateien)
- **Wie:** Python-Skript das die Footer in den `prompt:` string appended (VOR `settings:`, NACH allen anderen Top-Level-Keys)
- **Wichtig:** **In den prompt: string einfügen, nicht als top-level YAML-Keys!** (Lesson aus Phase A)
- **Verify:** yaml.safe_load, kein duplicate-key error, 50/50 recipes still load
- **Expected outcome:** -63 findings (KK2 + KK3 + KK4 + KK5)

### PHASE C2 — Stale References (O2)
- **Was:** 16 Referenzen auf nicht-existente Dateien untersuchen
- **Strategie pro finding:**
  1. Check ob die referenzierte Datei woanders existiert (case-insensitive, ähnlicher Name)
  2. Falls ja: Pfad korrigieren
  3. Falls nein: aus dem prompt entfernen (oder den Pfad dokumentieren wo er sein SOLLTE)
- **Vermutlich viele Fälle:** Referenzen auf `.state/pipeline/ranked_findings.yaml`, `.state/knowledge/09-im-features.md`, etc. — diese existieren nicht, aber gehören zur MAS-Architektur. Pragmatische Lösung: **entfernen oder durch generischen Hinweis ersetzen**.
- **Verify:** grep -r alle O2-Pfade — keiner darf mehr existieren
- **Expected outcome:** -16 findings

### PHASE C3 — SOT-References (KK6)
- **Was:** 6 recipes brauchen ≥3 SOT-Refs statt 1
- **Was ist SOT:** "Source of Truth" = `.state/knowledge/`, `.state/rules/`, `.state/workflows.yaml`, `.state/templates/`
- **Standard-Set für Recipes:** 5-7 SOT-Refs die JEDES Recipe sinnvoll referenzieren sollte:
  - `.state/knowledge/01-sot.md` (falls existent)
  - `.state/knowledge/05-rules.md` (Rules R01-R18)
  - `.state/workflows.yaml`
  - `.state/rules/hard_rules.yaml`
  - `.state/rules/rules_5_extreme.yaml`
- **Wie:** Suche welche existieren, füge die ersten 3-4 in den prompt ein
- **Expected outcome:** -6 findings

### PHASE C4 — Boundary-Indicator (MM3, MM4)
- **Was:** 4 prompts haben kein `⛔`, 1 title hat kein emoji
- **Lösung:** Prepend `⛔` zum prompt-string, prepend emoji zum title
- **Expected outcome:** -5 findings

### PHASE C5 — Prompt length (GG3, GG4)
- **Was:** 2 prompts < 100 chars, 1 prompt ohne emoji
- **Lösung:** Erweitere auf 100+ chars, füge emoji hinzu
- **Expected outcome:** -3 findings

### PHASE C6 — Instructions length (GG5)
- **Was:** 38 recipes haben instructions > 2000 chars
- **Lösung:** Für jedes Recipe eine `instructions-<name>.md` erstellen und in der YAML auf `instructions: @include: instructions-<name>.md` referenzieren
- **Pragmatisch:** Falls Goose `@include` nicht versteht → einfach die instructions auf 2000 kürzen (top + bottom)
- **Aufwand:** hoch (~600s)
- **Prio:** NIEDRIG — diese recipes funktionieren, das ist nur Style. **Falls C1-C5 erfolgreich, eventuell SKIP.**
- **Expected outcome:** -38 findings (oder 0 wenn skip)

### PHASE C7 — Version field (GG)
- **Was:** 1 tool yaml ohne `version:` field
- **Lösung:** `version: 1.0.0` hinzufügen
- **Expected outcome:** -1 finding

### PHASE C8 — Final verification
- pre-push-validator 8/8 PASS
- 50/50 recipes load live
- tools/ tests
- commit + push

---

## 3. SUCCESS CRITERIA

**Must-have (Phase A equivalent):**
- pre-push-validator: 8/8 PASS
- alle 50 recipes: yaml.safe_load OK
- alle 50 recipes: live `goose run --recipe` OK
- keine regressions an den bereits gefixten Files

**Nice-to-have (findings reduction):**
- KK-Regel (KK2/KK3/KK4/KK5/KK6): 63 → 0
- Stale-References (O2): 16 → 0
- Style (MM3/MM4/GG3/GG4): 8 → 0
- Meta (GG/version): 1 → 0
- GG5 (instructions length): 38 → 0 OR 38 (skip)
- **Total: 0/132 (88 if GG5 skipped)**

---

## 4. RISKS

1. **Header-Injection bricht YAML:** schon in Phase A passiert. **Mitigation:** Test mit `yaml.safe_load` NACH JEDEM Insert.
2. **Re-run von pre-push-validator zeigt neue Violations:** möglich, da wir den `version:`-Check oder `extensions:`-Check triggern. **Mitigation:** pre-push-validator NACH C1 zuerst laufen.
3. **Wort-Boundary-Probleme:** "R10" kann in YAML-Literals anders interpretiert werden. **Mitigation:** in prompt-strings bleiben, nicht in YAML-keys.
4. **Doppelte Keys:** schon 2x passiert. **Mitigation:** Vor jedem Insert: parse + count keys, ensure single-instance.
5. **Token-Budget R08:** cumulative patches werden > 50K tokens. **Mitigation:** kompakte footer (~2 Zeilen pro KK-Typ).

---

## 5. WORKFLOW PRO PASS

```
1. LESEN: welche Dateien + welche Typen in dieser Phase
2. SKRIPT: Python-Skript das für jede Datei:
   a. parse YAML
   b. finde prompt: string
   c. inject footer
   d. write back
   e. yaml.safe_load verify
3. SMOKE: alle Recipes yamllint
4. LIVE: 50 recipes goose run (parallel, 8 workers, 15s timeout)
5. FINDINGS: re-run findings-extractor
6. DECISION: continue to next phase OR fix regressions
```

---

## 6. ZEITPLAN (realistisch)

| Phase | Findings | Zeit  | Cumul. |
|-------|----------|-------|--------|
| C1    | -63      | 5 min | 5 min  |
| C2    | -16      | 8 min | 13 min |
| C3    | -6       | 4 min | 17 min |
| C4    | -5       | 2 min | 19 min |
| C5    | -3       | 2 min | 21 min |
| C6    | -38/skip | 20min | 41 min |
| C7    | -1       | 1 min | 42 min |
| C8    | verify   | 5 min | 47 min |
| **Σ** | **-132** |       | **~50 min** |

Wenn GG5 skip: ~30 min total.

---

## 7. NICHT IN DIESEM PLAN (out of scope)

- PHASE D (Phase B Tools 42/42 LIVE-Test)
- Refactoring auf eine andere Architektur
- Logic-Fixes an den recipes (Funktionalität ist OK)
- Performance-Optimierung

Diese sind bewusst rausgenommen, weil das eigentliche Ziel dieser Session die SOT-COMPLIANCE ist, nicht eine voll-characterization der Tools.

---

## 8. NÄCHSTER SCHRITT

User-Approval → PHASE C1 starten (KK-Regel-Footer).

Bei jedem Pass:
- Vorher: count findings
- Nachher: count findings + diff
- Bei regression: rollback + diagnose

Bei Abschluss: 1 commit mit allen Phase-C-Changes, dann push.
