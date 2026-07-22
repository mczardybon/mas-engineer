# BP-CHECKLIST.md — Best-Practices-Checklist

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
