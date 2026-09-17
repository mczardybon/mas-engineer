# Demo MAS Teams (3 built, 1 fixed by IM-005)

3 multi-agent teams built on 2026-07-21, retested on 2026-07-22 with real e2e runs.

## Final state (2026-07-22 08:16)
| Team | Status | Live verification |
|------|--------|-------------------|
| sales/ | ✅ ECHT | 10 tool-calls, 7 sub-agents, 3 leads (Finleap/N26/Vauban) |
| marketing/ | ✅ FIXED by IM-005 | 70 tool-calls, 64 sub-agents, full Q3 strategy delivered |
| translator/ | ✅ ECHT (parallel) | 7 tool-calls, 3 parallel translators + judge, Literal 29/30 wins |

## sales/ — ✅
- `sales-team.yaml` (main entry with sub_recipes)
- `sub/sales-orchestrator.yaml` (the actual orchestrator)
- `sub/lead-scraper.yaml`
- `sub/lead-verifier.yaml`
- `sub/outreach-drafter.yaml`
- `sub/deal-closer.yaml`

## marketing/ — ✅ FIXED
- `marketing-team.yaml` (main entry)
- `marketing-orchestrator-FIXED.yaml` (fixed orchestrator with sub_recipes block)
- `sub/marketing-orchestrator-BROKEN-original.yaml` (original broken version, kept for transparency)
- `sub/seo-researcher.yaml`
- `sub/content-writer.yaml`
- `sub/social-media-manager.yaml`
- `sub/email-campaign-manager.yaml`
- `sub/analytics-reporter.yaml`

## translator/ — ✅
- `translator-orchestrator.yaml` (main entry, no sub_recipes block)
- `sub/translator-literal.yaml`
- `sub/translator-literary.yaml`
- `sub/translator-technical.yaml`
- `sub/translation-judge.yaml`

## IM-005 fix details
See `../REPORT.md` and `../PARTIAL_FIX.md` for full timeline.
The marketing-orchestrator had no `sub_recipes:` block, so the 5 specialists returned
"not available" and the orchestrator fell back to self-execution. After IM-005 the
fixed orchestrator dispatches all 5 specialists in parallel (verified live with 70
tool-calls, 64 sub-agents, 0 x 401 errors).
