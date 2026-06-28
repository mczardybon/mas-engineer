# BP-CHECKLIST.md — Best-Practices-Checkliste (37 Feature-Typen A-KK)

## Settings-Optimierung (Typ A)
- [ ] A1: timeout zu niedrig? (2+ timeouts in 10 calls -> current * 1.5)
- [ ] A2: max_steps zu niedrig? (wird vor Abschluss erreicht -> +10)
- [ ] A3: timeout zu hoch? (Durchschnitt < 20% timeout -> * 3)
- [ ] A4: max_steps zu hoch? (Durchschnitt < 30% max -> * 3)

## Prompt-Qualitaet (Typ B)
- [ ] B1: Prompt zu vage? (User fragt 3x "was machst du?")
- [ ] B2: Prompt zu lang? (> 500 Zeichen)
- [ ] B3: Kontext fehlt? (Agent fragt nach Infos)
- [ ] B4: Prompt != Instructions? (Widerspruch?)

## Instructions (Typ C)
- [ ] C1: ⛔-Regel fehlt? (Agent tut Verbotenes)
- [ ] C2: Ablauf unklar? (Agent fragt nach Reihenfolge)
- [ ] C3: Grenzen fehlen? (Agent ueberschreitet Scope)
- [ ] C4: Referenzen veraltet? (nicht-existente Dateien)

## Workflow (Typ D)
- [ ] D1: Schritt-Reihenfolge falsch?
- [ ] D2: Schritt vergessen?
- [ ] D3: Ueberfluessiger Schritt? (80% uebersprungen)
- [ ] D4: Unklare Frage?

## Erkennungsmuster (Typ E)
- [ ] E1: Befehl ohne Match?
- [ ] E2: Muster matcht falsch?
- [ ] E3: Tote Erkennung? (> 50 Sessions kein Match)

## Prompt-Block (Typ F)
- [ ] F1: Befehl ohne Prompt-Eintrag?
- [ ] F2: Sortierung falsch? (Haeufigste nicht oben)
- [ ] F3: Beschreibung unklar?
- [ ] F4: MODUS-GUARD fehlt?

## Health (Typ G)
- [ ] G1: Agent degradiert? (Score < 80)
- [ ] G2: Hohe failure-rate? (> 10%)
- [ ] G3: Loops erkannt?
- [ ] G4: Agent dead?

## Anomalien (Typ H)
- [ ] H1: Dauer > 2x Durchschnitt?
- [ ] H2: Tokens > 3x Durchschnitt?
- [ ] H3: Kosten > 5x Durchschnitt?
- [ ] H4: Session stale? (> 60min idle)

## Prompt-Qualitaet (Typ I)
- [ ] I1: Score < 5/10?
- [ ] I2: Identitaet fehlt? ("Wer bin ich")
- [ ] I3: Keine ⛔-Grenzen?
- [ ] I4: Zu lang? (> 500 Zeichen)
- [ ] I5: Nicht alleinstehend?

## Config (Typ J)
- [ ] J1: Config fehlerhaft?
- [ ] J2: Config-Wert obsolete?

## Docs (Typ K)
- [ ] K1: Doc veraltet?
- [ ] K2: Doc fehlt?

## Goose (Typ L)
- [ ] L1: Zu viele Sessions?
- [ ] L2: Zu viele Skills?
- [ ] L3: Logs zu gross?

## Migration (Typ M)
- [ ] M1: Breaking Changes?
- [ ] M2: Non-Breaking?

## Recipe (Typ N)
- [ ] N1: Doppelte Recipes?
- [ ] N2: Alte Version?
- [ ] N3: Fehlende Dependencies?

## Struktur (Typ O)
- [ ] O1: Instructions != Ist-Zustand?
- [ ] O2: Referenz auf nicht-existente Datei?
- [ ] O3: Veralteter Zaehlimpuls?
- [ ] O4: Hardcodierter Pfad?

## Tools (Typ P)
- [ ] P1: Syntax-Fehler?
- [ ] P2: Hardcodierte Pfade?
- [ ] P3: Import-Fehler?

## Kalibrierung (Typ Q)
- [ ] Q1: Ueberdimensioniert? (< 20% Auslastung)
- [ ] Q2: Knapp bemessen? (> 80% Auslastung)

## Git (Typ R)
- [ ] R1: Code reduziert? (Positiv)
- [ ] R2: Code aufgeblaht? (Negativ)
- [ ] R3: ⛔-Regeln vermehrt? (Safety verbessert)
- [ ] R4: Prompt gekuerzt? (Token-Effizienz)
- [ ] R5: Neue Datei? (Nur wenn noetig)

## Tests (Typ V)
- [ ] V1: Keine Tests?
- [ ] V2: < 50% getestet?

## Prompt-Erosion (Typ GG)
- [ ] GG1: ⛔ fehlt im prompt?
- [ ] GG2: Version fehlt?
- [ ] GG3: Emoji fehlt?
- [ ] GG4: Prompt zu kurz? (< 100 Zeichen)
- [ ] GG5: Instructions zu lang? (> 2000 Zeichen)

## Drift (Typ FF + JJ)
- [ ] FF1: timeout abweichend?
- [ ] FF2: max_steps abweichend?
- [ ] JJ1: Installation abweichend?

## Backup (Typ HH)
- [ ] HH1: > 50 Backup-Verzeichnisse?
- [ ] HH2: > 100 .bak-Dateien?
- [ ] HH3: Kein Backup vor Aenderung?
- [ ] HH4: Backup > 30 Tage alt?

## Monitoring (Typ Y + CC + DD)
- [ ] Y1: Recovery langsamer?
- [ ] CC1: OOM/MemoryError?
- [ ] DD1: Tool not found?
