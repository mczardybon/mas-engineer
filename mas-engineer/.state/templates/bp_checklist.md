# BP-CHECKLIST.md — Best-Practices-Checklist (37 Feature-Typen A-KK)

## Settings optimization (typee A)
- [ ] A1: timeout too low? (2+ timeouts in 10 calls -> current * 1.5)
- [ ] A2: max_steps too low? (will vor Abschluss erreicht -> +10)
- [ ] A3: timeout too high? (Average < 20% timeout -> * 3)
- [ ] A4: max_steps too high? (Average < 30% max -> * 3)

## Prompt quality (Type B)
- [ ] B1: Prompt zu vage? (User asks 3x "what are you doing?")
- [ ] B2: Prompt too long? (> 500 characters)
- [ ] B3: Context missing? (Agent asks after Infos)
- [ ] B4: Prompt != Instructions? (Contradiction?)

## Instructions (typee C)
- [ ] C1: ⛔-Rule missing? (Agent tut Verbotenes)
- [ ] C2: Procedure unclear? (Agent asks for sequence/order)
- [ ] C3: Boundaries missing? (Agent oversteps scope)
- [ ] C4: referenceen outdated? (not-existente files)

## Workflow (typee D)
- [ ] D1: Step sequence wrong?
- [ ] D2: Step forgotten?
- [ ] D3: Superfluous step? (80% skipped)
- [ ] D4: Unclear question?

## Detectionspattern (typee E)
- [ ] E1: Command ohne Match?
- [ ] E2: pattern matcht wrong?
- [ ] E3: Dead detection? (> 50 sessions no match)

## Prompt-Block (typee F)
- [ ] F1: Command without prompt entry?
- [ ] F2: Sorting wrong? (Most frequent not at top)
- [ ] F3: Description unklar?
- [ ] F4: MODE-GUARD missing?

## Health (typee G)
- [ ] G1: Agent degraded? (Score < 80)
- [ ] G2: High failure rate? (> 10%)
- [ ] G3: Loops detected?
- [ ] G4: Agent dead?

## Anomalien (typee H)
- [ ] H1: Duration > 2x Average?
- [ ] H2: Tokens > 3x Average?
- [ ] H3: Kosten > 5x Average?
- [ ] H4: Session stale? (> 60min idle)

## Prompt quality (Type I)
- [ ] I1: Score < 5/10?
- [ ] I2: Identity missing? ("Who am I")
- [ ] I3: No ⛔-Boundaries?
- [ ] I4: Zu long? (> 500 characters)
- [ ] I5: Not self-contained?

## Config (typee J)
- [ ] J1: Config faulty?
- [ ] J2: Config-Value obsolete?

## Docs (typee K)
- [ ] K1: Doc outdated?
- [ ] K2: Doc missing?

## Goose (typee L)
- [ ] L1: Too many sessions?
- [ ] L2: Too many skills?
- [ ] L3: Logs too large?

## Migration (typee M)
- [ ] M1: Breaking Changes?
- [ ] M2: Non-Breaking?

## Recipe (typee N)
- [ ] N1: Duplicate recipes?
- [ ] N2: Old Version?
- [ ] N3: Missing Dependencies?

## Structure (Type O)
- [ ] O1: Instructions != Ist-State?
- [ ] O2: reference auf not-existente file?
- [ ] O3: outdateder Zaehlimpuls?
- [ ] O4: Hardcoded path?

## Tools (typee P)
- [ ] P1: Syntax-Error?
- [ ] P2: Hardcoded paths?
- [ ] P3: Import-Error?

## Calibration (typee Q)
- [ ] Q1: Oversized? (< 20% Auslastung)
- [ ] Q2: Tightly sized? (> 80% Auslastung)

## Git (typee R)
- [ ] R1: Code reduced? (positive)
- [ ] R2: Code bloated? (negative)
- [ ] R3: ⛔-Rules increased? (Safety improved)
- [ ] R4: Prompt shortened? (Token efficiency)
- [ ] R5: New file? (Only if necessary)

## Tests (typee V)
- [ ] V1: No Tests?
- [ ] V2: < 50% tested?

## Prompt-Erosion (typee GG)
- [ ] GG1: ⛔ missing im prompt?
- [ ] GG2: Version missing?
- [ ] GG3: Emoji missing?
- [ ] GG4: Prompt zu short? (< 100 characters)
- [ ] GG5: Instructions too long? (> 2000 characters)

## Drift (typee FF + JJ)
- [ ] FF1: timeout deviating?
- [ ] FF2: max_steps deviating?
- [ ] JJ1: Installation deviating?

## Backup (typee HH)
- [ ] HH1: > 50 Backup-directoryse?
- [ ] HH2: > 100 .bak-files?
- [ ] HH3: No backup before change?
- [ ] HH4: Backup > 30 days old?

## Monitoring (typee Y + CC + DD)
- [ ] Y1: Recovery slower?
- [ ] CC1: OOM/MemoryError?
- [ ] DD1: Tool not found?
