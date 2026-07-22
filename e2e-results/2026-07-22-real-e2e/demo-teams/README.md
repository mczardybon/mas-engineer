# Demo MAS Teams (3 built, 1 partial)

3 multi-agent teams built on 2026-07-21, retested on 2026-07-22 with real e2e runs.

## sales/ — ✅ ECHT
- `sales-team.yaml` (main entry with sub_recipes)
- `sub/sales-orchestrator.yaml` (the actual orchestrator)
- `sub/lead-scraper.yaml`
- `sub/lead-verifier.yaml`
- `sub/outreach-drafter.yaml`
- `sub/deal-closer.yaml`

## marketing/ — ⚠️ PARTIAL
- `marketing-orchestrator.yaml` (main entry, no sub_recipes block — uses load(source: "name"))
- `sub/seo-researcher.yaml`
- `sub/content-writer.yaml`
- `sub/social-media-manager.yaml`
- `sub/email-campaign-manager.yaml`
- `sub/analytics-reporter.yaml`
- **Issue**: orchestrator falls back to self-execution because sub-agent names aren't
  resolved as available sources. Needs structural fix.

## translator/ — ✅ ECHT (parallel)
- `translator-orchestrator.yaml` (main entry, no sub_recipes block)
- `sub/translator-literal.yaml`
- `sub/translator-literary.yaml`
- `sub/translator-technical.yaml`
- `sub/translation-judge.yaml`

## Install
```bash
# Copy to goose recipes dir
cp -r sales marketing translator /root/.config/goose/recipes/
# Note: sub_recipes paths in sales-orchestrator.yaml are absolute,
# pointing to /root/.config/goose/recipes/sales/sub/
```
