# BUG: `author:` field mismatch in 20/96 sub-recipes

## Symptom
`goose run --recipe X --explain` errors out:
```
Error: author: invalid type: string "MAS Engineering", expected struct Author
```

## Root cause
goose schema expects `author: {name: "...", email: "..."}` (struct),
but these 20 recipes have `author: "MAS Engineering"` (plain string).

## Affected recipes (20)
- sub_mas-content-writer
- sub_mas-e2e-auto-repair-director/runner/validator
- sub_mas-e2e-german-fixes-checker/director/runner/validator
- sub_mas-e2e-phoenix-fixes-director/runner/validator
- sub_mas-email-campaign-manager
- sub_mas-seo-researcher
- sub_mas-social-media-manager
- sub_mas-test-fix-failures-applier/designer/director/finder/ranker/validator

## Affected user-facing recipes
- test-fix-failures.yaml (delegator → director → 5 broken sub-recipes)
- e2e-verify-auto-repair.yaml (delegator → director → 2 broken sub-recipes)
- e2e-verify-german-fixes.yaml (delegator → director → 3 broken sub-recipes)
- e2e-verify-phoenix-fixes.yaml (delegator → director → 2 broken sub-recipes)

## Reproduction
```bash
# All 20 fail:
for r in sub_mas-content-writer sub_mas-e2e-auto-repair-director ...; do
  goose run --recipe /root/.config/goose/recipes/sub/$r.yaml --explain 2>&1 | head -1
done

# All 76 without author work fine
for r in sub_mas-framework-scanner sub_mas-worktree-manager ...; do
  goose run --recipe /root/.config/goose/recipes/sub/$r.yaml --explain 2>&1 | head -1
done
```

## Fix (minimal)
Either:
1. Remove `author: "..."` line from all 20 recipes
2. Convert to struct: `author: { name: "MAS Engineering" }`

Option 1 is simplest. Framework doesn't use author field at runtime.

## Discovered
- Date: 2026-07-24
- Detection: smoke-test of new-generation sub-recipes via --explain
- Correlation: 20/20 with author broken, 0/76 without author broken (100%)
