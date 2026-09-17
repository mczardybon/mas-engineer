# Final E2E Report — 2026-07-27-demo-team-15x + teams-1

**Date:** 2026-07-27T16:15:03
**Combined result: Generation 15/15 + Dispatch 8/9 = 23/24 = 95.8%**

---

## Test 1: run_15x_demo.py — Generation (15 runs)

**Mechanik:** 3 teams × 5 runs = 15 LLM-generations, each create→validate→wipe
**Validator:** `dev_yaml_check.py VERIFY_STATE` (deterministic YAML-Syntax)

- **Result: 15/15 PASS = 100.0%**

| Team | Pass | Files avg | YAML ok | Tests reported avg | Duration avg |
|---|---|---|---|---|---|
| sales | 5/5 | 6.0 | 5/5 | 11.0 | 98.6s |
| marketing | 5/5 | 6.8 | 5/5 | 16.2 | 109.1s |
| translator | 5/5 | 6.0 | 5/5 | 9.8 | 89.4s |

---

## Test 2: e2e_teams.py — Dispatch (9 wrapper-recipes)

**Mechanik:** 3 teams × 3 levels (easy/medium/hard) = 9 wrapper-recipes with sub_recipes: array
**Validator:** marker_found + sub_recipe_invoked + expected/forbidden keywords

- **Result: 8/9 PASS = 88.9%**

| Test | Status | Duration |
|---|---|---|
| marketing/easy | ✓ | 38.8s |
| marketing/hard | ✓ | 63.8s |
| marketing/medium | ✓ | 11.6s |
| sales/easy | ✓ | 30.1s |
| sales/hard | ✓ | 110.2s |
| sales/medium | ✓ | 333.2s |
| translator/easy | ✓ | 18.5s |
| translator/hard | ✗ | 59.7s |
| translator/medium | ✓ | 22.7s |

### Failures
- **translator/hard**: forbidden keywords present (translation too literal): ['spilt milk', 'verschüttete Milch']

---

## Cross-Test Observation

- **Generation (run_15x_demo)** ist sehr stabil: 15/15 (alle YAMLs valide, alle 6-7 files, alle ~100s)
- **Dispatch (e2e_teams)** ist auch stabil: 8/9 (alle wrapper-recipes lösen sub_recipe_invoked aus)
- **Real bug gefunden:** translator-team hat 'spilt milk' zu wörtlich übersetzt (Eigenname 'Verschüttete Milch' als phrase erkannt)
- **Fix im run_15x_demo.py:** `yaml_check_passed` field nutzt jetzt den echten `dev_yaml_check.py` validator, nicht nur regex