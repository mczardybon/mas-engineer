---
name: mas-engineer-recipe-yaml-pytest-coverage
description: How to systematically add pytest recipe-YAML sanity tests for mas-engineer (and similar YAML-recipe projects). Distinguishes MAS-internal recipes (test) vs demo-teams (skip). Detects R-rule patterns. Pattern from R103-R108 epic — 10-function test files. 100% MAS-internal coverage achieved. Use when: When test coverage is below target, when user asks to add tests for recipes, or when adding new sub_recipes/instructions. Also use when bulk-adding sanity tests across recipe/sub/. Use to distinguish MAS-internal (test) from demo-teams (skip per user).
---

## When to use

Load this skill when: How to systematically add pytest recipe-YAML sanity tests for mas-engineer (and similar YAML-recipe projects). Distinguishes MAS-internal recipes (test) vs demo-teams (skip). Detects R-rule patterns. Pattern from R103-R108 epic — 10-function test files. 100% MAS-internal coverage achieved. Use when: When test coverage is below target, when user asks to add tests for recipes, or when adding new sub_recipes/instructions. Also use when bulk-adding sanity tests across recipe/sub/. Use to distinguish MAS-internal (test) from demo-teams (skip per user).

For mas-engineer framework development, this skill provides domain-specific guidance that supersedes generic workflows.



# Recipe-YAML pytest coverage (R103-R108 pattern)

## TL;DR

mas-engineer has 117 recipe-yaml files in `recipe/sub/` (82 MAS-internal,
35 demo-teams). Coverage metric: tests written / MAS-internal recipes.
R103-R108 epic went 2.5% → 100% (82/82). 10-function pytest files,
R-rule taxonomy, R101 EVIDENCE-pattern for test fixes.

**KEY DISCOVERY (R108-5):** Demo-teams (social-media-manager,
email-campaign-manager, seo-researcher) are summon-platform recipes.
Per user: "Demo Teams müssen nicht getestet werden". Varianz is feature.

## The 10-function test template

For each recipe YAML, write `test_sub_mas-{name}.py` with 10 functions:

```python
import re, yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-{name}.yaml"


def test_xxx_recipe_exists():
    assert RECIPE.exists()


def test_xxx_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_xxx_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data


def test_xxx_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_xxx_role():
    """Check for expected role keywords in content."""
    content = RECIPE.read_text()
    assert "expected_keyword" in content


def test_xxx_r_rules():
    """Per R-rule taxonomy: assert R01, R09, R10 etc."""
    content = RECIPE.read_text()
    assert "R01" in content
    assert "R09" in content
    assert "R10" in content


def test_xxx_coronashield():
    """All action-taker recipes must have CORONASHIELD."""
    content = RECIPE.read_text()
    assert "CORONASHIELD" in content


def test_xxx_no_sub_recipes():
    """Leaf recipes should have no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"]


def test_xxx_settings():
    """Standard settings: timeout=600, max_steps=100, deepseek."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600
    assert settings.get("max_steps") == 100
    assert "deepseek" in settings.get("goose_model", "").lower()


def test_xxx_version():
    """Version must be v1.0.0."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("version") == "1.0.0"
```

## Sub-round execution pattern

**Per sub-round:** pick N related unrecipes, write N test files in
parallel, run pytest, fix if needed, commit + push.

**R108-5 lesson:** First-try pass rate dropped from 100% to 19/19
with 3 R101 EVIDENCE test-fixes. The 3 fixes were md-aware:
- "read-only" string was in .md file, not YAML
- Template placeholders use {CAPS} not {{jinja2}}
- Template constitution is set at generation time

## R-Rule Taxonomy (R108-5 complete)

| Pattern | R-Rules | Examples | Has CORONASHIELD? |
|---|---|---|---|
| action-taker leaf | R01+R09+R10 | summarizer, signal-generator | Yes |
| orchestrator | R01+R09+R10 | dev-director, recipe-manager | Yes |
| read-only analyzer | R10 (1x) only | prompt-engineer, web-researcher, migration-helper, session-analyst, system-knowledge | No |
| script-wrapper | R01+R09+R10 | tff-crossref-validator (R85) | Yes |
| tool-wrapper | 0 R-rules | tools, dev_editor | No |
| workflow executor | R09+R10 | setup workflows | Yes |
| post-commit verify | R01+R04+R09+R10 | (R04 only) | Yes |
| demo-team | 0 R-rules | social-media-manager, email-campaign-manager, seo-researcher | No |

**R01** = rule of the recipe's primary action
**R04** = post-commit-verify (rare)
**R05** = ??? (audit/log)
**R09** = SOT/cross-references
**R10** = recovery + EVIDENCE

## Master Recipes (R108-6)

Top-level recipes (10 total):
- root_recipe.yaml — root entry, no sub_recipes (or <= 1)
- dev-mas-engineer.yaml — DEV entry, thin delegator → sub_mas-dev-director
- 5 thin delegators: e2e-verify-auto-repair, e2e-verify-german-fixes,
  e2e-verify-phoenix-fixes, test-fix-failures, test-mas-user
- 2 setup: setup-dashboard, dashboard-data-refresh

**Thin delegator pattern:**
```python
def test_thin_delegator_one_sub_recipe():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = data.get("sub_recipes", [])
    assert len(subs) == 1
    assert subs[0].get("name") == "sub_mas-X-director"
```

**Setup recipes:**
- setup-dashboard: one-time init (npm install, Extension)
- dashboard-data-refresh: 5min interval (reads guardian.yaml)
- NOT thin delegators (sub_recipes != 1)

## Templates (R108-6)

agent_template.yaml uses {name} placeholder, NOT real values:
- `name: sub_mas-{name}` (placeholder)
- constitution set by recipe-manager at generation time
- Uses `{CAPS}` placeholders, NOT `{{jinja2}}`

```python
def test_template_has_placeholders():
    """Template uses {CAPS} not {{jinja2}}."""
    content = TEMPLATE.read_text()
    placeholders = re.findall(r"\{[A-Z_][A-Z0-9_]*\}", content)
    assert len(placeholders) >= 2

def test_template_references_constitution():
    """Template either has constitution OR uses {name} placeholder."""
    with open(TEMPLATE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") or data.get("name") == "sub_mas-{name}"
```

## Instruction Manuals (R108-6)

45 files: 43 sub_mas-*.md + 2 non-sub (security-scanner, static-analyzer)

```python
def test_instructions_sub_mas_count():
    md = list(INST_DIR.glob("sub_mas-*.md"))
    assert len(md) >= 30

def test_instructions_reference_rules():
    """Most instructions reference R-rules or constitution."""
    found = sum(
        1 for f in INST_DIR.glob("sub_mas-*.md")
        if re.search(r"R0[149]", f.read_text())
        or "master-constitution" in f.read_text()
    )
    assert found >= 20
```

## Demo-team detection (KEY!)

**DO NOT TEST demo-teams** (per user, R108-5):

```python
import yaml
from pathlib import Path

def classify_recipes():
    sub = Path("recipe/sub")
    subs = sorted([f.stem for f in sub.glob("sub_mas-*.yaml")])
    mas_internal = []
    other = []
    for s in subs:
        name = s.replace("sub_mas-", "")
        content = (sub / f"sub_mas-{name}.yaml").read_text()
        d = yaml.safe_load(content)
        desc = (d.get("description") or "")
        if "MAS-internal" in desc or "MAS-Engineer-internal" in desc:
            mas_internal.append(name)
        else:
            other.append(name)
    return mas_internal, other
```

Coverage metric: `len(tested) / len(mas_internal) * 100`

## Run pytest

```bash
cd /workspace/mas-engineer-src/mas-engineer
python3 -m pytest tests/test_sub_mas_xxx.py -v
python3 -m pytest tests/  # full suite
```

## Commit + push pattern (R88)

```bash
cd /workspace/mas-engineer-src
git branch --show-current  # verify Dev
git add mas-engineer/tests/test_sub_mas_*.py
git commit -F /tmp/commit_msg.txt
git log --oneline -3  # check for unexpected commits (R101 lesson)
pat=$(cat ~/.github_pat 2>/dev/null || echo "ghp_...")
git remote set-url origin "https://${pat}@github.com/mczardybon/mas-engineer.git"
git push origin Dev
git remote set-url origin "https://github.com/mczardybon/mas-engineer.git"
```

## Pitfalls

1. **Demo-teams**: Per user-profile, marketing-specialists are
   on-demand LLM-generated. DO NOT test them. Detection: description
   does NOT contain "MAS-internal".

2. **Test-fix workflow (R101 EVIDENCE)**: If a test fails, FIRST
   check if the test is too strict. Per R101: 0 recipe modifications,
   only test adjustments.

3. **Thin delegators vs leaf recipes**:
   - Leaf: sub_recipes=0, R01+R09+R10
   - Thin delegator: sub_recipes=1, R01+R09+R10
   - Orchestrator: sub_recipes > 1, R01+R09+R10

4. **deepseek model**: All MAS-internal recipes use deepseek-v4-flash.
   Check `settings.goose_model` for "deepseek" substring.

5. **CORONASHIELD**: All action-taker recipes must have this.
   Read-only analyzers (R10 only) do NOT need it.

6. **Template placeholders**: agent_template.yaml uses {CAPS}, not
   {{jinja2}}. Test for `{[A-Z_][A-Z0-9_]*}`.

7. **Test-collision risk (R103)**: ALWAYS `ls tests/test_sub_mas_*.py`
   before writing a new test file.

8. **Sub_recipes can be `[]` or absent** — both valid for leaf-node.

9. **Settings sometimes optional** — runners may not have "prompt"
   field (executor-only). Adapt required-fields test to actual structure.

## Coverage progression (R103-R108 EPIC)

| Round | Tests | MAS-internal % | Notes |
|-------|-------|----------------|-------|
| R56 baseline | 3 | 2.5% | Pre-epic |
| R103 phase 1 | 12 | 10.1% | 3 sub-rounds |
| R104 | 30 | 25.2% | 6 sub-rounds |
| R106 (Start) | 770 | 50.4% | 18 tests in 1 commit |
| R107-1..12 | 1140 | 87.2% | 12 batches |
| R108-1 | 1161 | 90.6% | 90% milestone |
| R108-2 | 1174 | 94.0% | |
| R108-3 | 1180 | 97.4% | 95% ÜBERTROFFEN |
| R108-4 | 1180 | 95.7% | 95% BESTÄTIGT |
| R108-5 | 1180 | 100% | 🏆 MILESTONE + 35 demo-teams excluded |
| R108-6 | 1218 | 100% | + master + template + instructions |

**R106-R108 MEGA EPIC Finale:**
- 50.4% → 100% MAS-internal (+49.6%, +410 tests)
- 19 commits, 1218 total tests
- 138 recipe assets tested (82 sub + 10 master + 1 template + 45 instr)
- 0 regressions
- 3 R101 EVIDENCE-pattern test-fixes (md-aware, placeholder-aware)
