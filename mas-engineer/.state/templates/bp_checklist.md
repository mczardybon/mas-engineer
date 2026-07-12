# BP-CHECKLIST.md — Best-Practices-Checklist (37 Feature-typeeen A-KK)

## Settings-Optimierung (typee A)
- [ ] A1: timeout zu niedrig? (2+ timeouts in 10 calls -> current * 1.5)
- [ ] A2: max_steps zu niedrig? (will vor Abschluss erreicht -> +10)
- [ ] A3: timeout zu hoch? (Average < 20% timeout -> * 3)
- [ ] A4: max_steps zu hoch? (Average < 30% max -> * 3)

## Prompt-Qualitaet (typee B)
- [ ] B1: Prompt zu vage? (User asks 3x "was machst du?")
- [ ] B2: Prompt zu long? (> 500 characters)
- [ ] B3: Context missing? (Agent asks after Infos)
- [ ] B4: Prompt != Instructions? (Widerspruch?)

## Instructions (typee C)
- [ ] C1: ⛔-Rule missing? (Agent tut Verbotenes)
- [ ] C2: Ablauf unklar? (Agent asks after Reihenfolge)
- [ ] C3: Boundaries missing? (Agent aboutschreitet Scope)
- [ ] C4: referenceen outdated? (not-existente files)

## Workflow (typee D)
- [ ] D1: Step-Reihenfolge wrong?
- [ ] D2: Step vergessen?
- [ ] D3: Aboutfluessiger Step? (80% aboutsprungen)
- [ ] D4: Unklare Frage?

## Detectionspattern (typee E)
- [ ] E1: Command ohne Match?
- [ ] E2: pattern matcht wrong?
- [ ] E3: Tote Detection? (> 50 Sessions no Match)

## Prompt-Block (typee F)
- [ ] F1: Command ohne Prompt-entry?
- [ ] F2: Sortierung wrong? (Frequentlyste not oben)
- [ ] F3: Description unklar?
- [ ] F4: MODUS-GUARD missing?

## Health (typee G)
- [ ] G1: Agent degradiert? (Score < 80)
- [ ] G2: Hohe failure-rate? (> 10%)
- [ ] G3: Loops erkannt?
- [ ] G4: Agent dead?

## Anomalien (typee H)
- [ ] H1: Duration > 2x Average?
- [ ] H2: Tokens > 3x Average?
- [ ] H3: Kosten > 5x Average?
- [ ] H4: Session stale? (> 60min idle)

## Prompt-Qualitaet (typee I)
- [ ] I1: Score < 5/10?
- [ ] I2: Identity missing? ("Wer am ich")
- [ ] I3: No ⛔-Boundaries?
- [ ] I4: Zu long? (> 500 characters)
- [ ] I5: Nicht allinstehend?

## Config (typee J)
- [ ] J1: Config faulty?
- [ ] J2: Config-Value obsolete?

## Docs (typee K)
- [ ] K1: Doc outdated?
- [ ] K2: Doc missing?

## Goose (typee L)
- [ ] L1: Zu many Sessions?
- [ ] L2: Zu many Skills?
- [ ] L3: Logs zu large?

## Migration (typee M)
- [ ] M1: Breaking Changes?
- [ ] M2: Non-Breaking?

## Recipe (typee N)
- [ ] N1: Doppelte Recipes?
- [ ] N2: Old Version?
- [ ] N3: Missing Dependencies?

## Struktur (typee O)
- [ ] O1: Instructions != Ist-State?
- [ ] O2: reference auf not-existente file?
- [ ] O3: outdateder Zaehlimpuls?
- [ ] O4: Hardcodierter Path?

## Tools (typee P)
- [ ] P1: Syntax-Error?
- [ ] P2: Hardcodierte Pathe?
- [ ] P3: Import-Error?

## Kalibrierung (typee Q)
- [ ] Q1: Aboutdimensioniert? (< 20% Auslastung)
- [ ] Q2: Knapp bemessen? (> 80% Auslastung)

## Git (typee R)
- [ ] R1: Code reduziert? (positivee)
- [ ] R2: Code aufgeblaht? (negativee)
- [ ] R3: ⛔-Rulen increased? (Safety verbettert)
- [ ] R4: Prompt gekuerzt? (Token-Effizienz)
- [ ] R5: New file? (Only if notig)

## Tests (typee V)
- [ ] V1: No Tests?
- [ ] V2: < 50% getestet?

## Prompt-Erosion (typee GG)
- [ ] GG1: ⛔ missing im prompt?
- [ ] GG2: Version missing?
- [ ] GG3: Emoji missing?
- [ ] GG4: Prompt zu short? (< 100 characters)
- [ ] GG5: Instructions zu long? (> 2000 characters)

## Drift (typee FF + JJ)
- [ ] FF1: timeout abweichend?
- [ ] FF2: max_steps abweichend?
- [ ] JJ1: Installation abweichend?

## Backup (typee HH)
- [ ] HH1: > 50 Backup-directoryse?
- [ ] HH2: > 100 .bak-files?
- [ ] HH3: No Backup vor Change?
- [ ] HH4: Backup > 30 Tage old?

## Monitoring (typee Y + CC + DD)
- [ ] Y1: Recovery longsamer?
- [ ] CC1: OOM/MemoryError?
- [ ] DD1: Tool not found?
