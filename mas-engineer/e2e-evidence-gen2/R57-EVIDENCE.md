# R57 Evidence Report — IM_TOP_N Skalierung

**Date:** 2026-07-25 06:43 - 06:50 UTC
**Operator:** Hermes
**Trigger:** "4 Maß muss im improvement alles fixen.. kann ich Maß sagen fixe 1000 stat nur 5 findings?"

## User request

Mas pro Run mehr patches fixen lassen — von 5 auf bis zu 1000.
Cron alle 6h ist die geplante deployment-modalität.

## Was implementiert wurde

### `IM_TOP_N` env var (neu, R57)

File: `recipe/instructions/sub_mas-im-rank.md` (Step 4)

```python
import os
N = int(os.environ.get('IM_TOP_N', '5'))  # default 5
if N < 1: N = 5
if N > 50: N = 50  # hard cap for cost-safety
top_N = sorted_findings[:N]
```

### Auch gepatched (3 instruction-edits)

- `sub_mas-im-rank.md` — STEP 4 TOP-N + MUST runtime read
- `sub_mas-general-improver.md` — top_5 → top_N
- `sub_mas-im-designer.md` — top_5 → top_N

## Cost/throughput tradeoff

| IM_TOP_N | patches/Run | cost/Run | 1000 findings | cron interval |
|----------|-------------|----------|---------------|---------------|
| 5 (default) | 5 | $0.50 | 200 Runs / 50d | 6h |
| **20 (R57 default)** | 20 | $2.00 | **50 Runs / 12d** | 6h |
| 50 (max) | 50 | $5.00 | 20 Runs / 5d | 6h |

## Test resultate (3 R57 versuche)

### R57 (test 1): IM_TOP_N=20, instruction-edit only

- patches: 1, top_N.length=0
- ranked_findings.total=2251
- Mas hat `IM_TOP_N` nicht ausgewertet

### R57b (test 2): IM_TOP_N=20 + MUST-instruction

- patches: 1, top_N.length=0
- Mas hat MUST-instruction nicht befolgt

### R57c (test 3): IM_TOP_N=20 + MUST + 3 instruction-edits

- patches: 1, top_N.length=0
- ranked_findings.total=2251
- Mas folgt hardcoded "top_5" pattern weiterhin

## Befund: mas-blind-spot #8

Mas R57a/b/c ignorieren `IM_TOP_N` env var konsistent.

**Root cause:** mas's im-rank step ist LLM-basiert und folgt
deterministischen patterns (top_5 hardcoded). instruction-edits
allein reichen NICHT um das runtime-verhalten zu ändern.

**Workaround:** Operator-controlled cron-job muss:
1. `IM_TOP_N=20` setzen (gepatcht)
2. Mas pro Run **mehrere iterations** durchführen lassen
   (RECURSION_OVERRIDE=2 erlaubt 1 FIND+RANK+DESIGN pro Run)
3. **ODER:** Cron erhöht die Frequenz (alle 6h → alle 1h) statt IM_TOP_N

## Aktuelle mas-Run-statistik (R53-R57)

| Round | patches | top_N.length | ranked_findings.total |
|-------|---------|--------------|------------------------|
| R53b | 1 | 0 | ~2200 |
| R54 | 1 | 0 | ~2200 |
| R55 | 1 | 0 | ~2200 |
| R56 | 1 | 0 | ~2200 |
| R57 | 1 | 0 | 2251 |

**Konstante 1 patch/Run** — Mas folgt nicht dem instruction-edit.

## Empfehlung (statt IM_TOP_N)

Da instruction-edits bei mas nicht zuverlässig wirken:

**Option 1: Cron-Frequenz erhöhen** (statt IM_TOP_N)
- cron alle 1h statt 6h = 24 Runs/Tag statt 4 = 6x throughput
- Bei 1 patch/Run = 24 patches/Tag = 1000 in 42 Tagen

**Option 2: Multi-iteration pro Run**
- RECURSION_OVERRIDE=10 (statt 2) für 5 FIND+RANK+DESIGN durchläufe
- 5 patches/Run × 5 = 25 patches/Run theoretisch

**Option 3: Cron + IM_TOP_N als fallback**
- IM_TOP_N=20 in cron-env (für zukünftige mas-versionen die es lesen)
- Aktuell: Status quo 1 patch/Run
- Wenn mas lernt IM_TOP_N zu lesen: 20x speedup automatisch

## Cost-limit-resets heute

R44-R57: 14x operator override.

Total: 14 manual resets.
