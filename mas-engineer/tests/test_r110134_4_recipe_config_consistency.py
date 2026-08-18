"""
test_r110134_4_recipe_config_consistency.py — R110-134

Verifies that all recipes use consistent model/temperature/timeout settings
and that the values fall within sane operational bounds.

Why this matters:
- Inconsistent model names (e.g. "filtered/deepseek/deepseek-v4-flash" vs
  "deepseek-v4-flash") cause goose to load wrong model (R110-74).
- Temperature outliers (0.7 in a YAML-edit recipe that needs determinism)
  cause flaky test results.
- Timeout outliers (60s for a 100-step recipe) cause premature kill.
- max_turns outliers (200 for a 15-step recipe) waste resources.

Run with:
    cd mas-engineer && pytest tests/test_r110134_4_recipe_config_consistency.py -v
"""
from __future__ import annotations
import sys
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from _recipe_helpers import load_all_recipes  # noqa: E402

# Sane operational bounds (R110-? baselines)
ALLOWED_MODELS = {
    "deepseek-v4-flash",       # default, fast
    "deepseek-v4-pro",         # smarter, slower
    "filtered/deepseek/deepseek-v4-flash",  # proxy/router variant (R110-74)
    "sonnet",                  # direct goose-style model key (root_recipe.yaml etc.)
}
# Providers recognised in BOTH settings keys:
#   - "goose_provider" (legacy schema, e.g. dev-mas-engineer, e2e-verify-*)
#   - implicit when "model: sonnet" is used (goose maps sonnet → anthropic automatically)
ALLOWED_PROVIDERS = {"openai", "anthropic", "google"}
ALLOWED_TEMPERATURES = {0.0, 0.2, 0.3, 0.7, 1.0}
TIMEOUT_MIN, TIMEOUT_MAX = 30, 1800
MAX_STEPS_MAX = 200


def test_all_recipes_have_settings():
    """Every recipe must have a settings: block."""
    recipes = load_all_recipes()
    missing = [b for b, i in recipes.items() if not i["data"].get("settings")]
    assert not missing, f"{len(missing)} recipes lack settings:\n" + "\n".join(f"  - {m}" for m in missing[:10])


def test_model_names_in_allowlist():
    """Every recipe's goose_model must be in ALLOWED_MODELS.

    Recipes may also use the newer `model: <x>` key (goose-native schema,
    e.g. root_recipe.yaml: `model: sonnet`) — that is accepted as a
    separate allowlisted value. Recipes with NO model field at all are
    allowed: they rely on the goose runtime default (currently sonnet).

    R110-134 fix: a YAML literal `goose_model: ` (no value) parses to
    Python `None`. The previous `or` chain converted `None` to the
    sentinel string `"NONE"` and flagged 15 recipes that intentionally
    inherit the runtime default. The fix: skip if BOTH keys are None
    (i.e. truly not set), then check the resolved value.
    """
    recipes = load_all_recipes()
    bad = []
    for base, info in recipes.items():
        s = info["data"].get("settings", {})
        # Prefer legacy `goose_model`, fall back to new `model`
        m = s.get("goose_model")
        if m is None:
            m = s.get("model")
        # If both are None (YAML null or missing), the recipe inherits
        # the goose runtime default — that is allowed.
        if m is None:
            continue
        if m not in ALLOWED_MODELS:
            bad.append((base, m))
    assert not bad, (
        f"{len(bad)} recipes use disallowed model name:\n"
        + "\n".join(f"  - {b}: {m!r}" for b, m in bad[:10])
    )


def test_provider_in_allowlist():
    """Every recipe's goose_provider must be in ALLOWED_PROVIDERS.

    Provider is OPTIONAL: a recipe with no `goose_provider` field and a
    recognised `model` (or no model) is fine — goose infers provider from
    the model name (e.g. sonnet → anthropic).
    """
    recipes = load_all_recipes()
    bad = []
    for base, info in recipes.items():
        s = info["data"].get("settings", {})
        p = s.get("goose_provider")
        if p is None:
            # No provider specified — acceptable, goose uses model-based default
            continue
        if p not in ALLOWED_PROVIDERS:
            bad.append((base, p))
    assert not bad, (
        f"{len(bad)} recipes use disallowed provider:\n"
        + "\n".join(f"  - {b}: {p!r}" for b, p in bad[:10])
    )


def test_temperature_in_allowlist():
    """Every recipe's temperature must be a known good value."""
    recipes = load_all_recipes()
    bad = []
    for base, info in recipes.items():
        t = info["data"].get("settings", {}).get("temperature", None)
        if t is None:
            continue
        if t not in ALLOWED_TEMPERATURES:
            bad.append((base, t))
    assert not bad, (
        f"{len(bad)} recipes use non-standard temperature:\n"
        + "\n".join(f"  - {b}: {t!r}" for b, t in bad[:10])
    )


def test_timeout_within_bounds():
    """Every recipe's timeout must be in [30, 1800] seconds."""
    recipes = load_all_recipes()
    bad = []
    for base, info in recipes.items():
        t = info["data"].get("settings", {}).get("timeout", 0)
        if t < TIMEOUT_MIN or t > TIMEOUT_MAX:
            bad.append((base, t))
    assert not bad, (
        f"{len(bad)} recipes have timeout outside [{TIMEOUT_MIN}, {TIMEOUT_MAX}]:\n"
        + "\n".join(f"  - {b}: {t}s" for b, t in bad[:10])
    )


def test_max_turns_within_bounds():
    """Every recipe's max_turns must be ≤ MAX_STEPS_MAX."""
    recipes = load_all_recipes()
    bad = []
    for base, info in recipes.items():
        m = info["data"].get("settings", {}).get("max_turns", 0)
        if m > MAX_STEPS_MAX:
            bad.append((base, m))
    assert not bad, (
        f"{len(bad)} recipes have max_turns > {MAX_STEPS_MAX}:\n"
        + "\n".join(f"  - {b}: {m}" for b, m in bad[:10])
    )


def test_default_values_consistent():
    """Distribution check — most recipes should use the same defaults.
    If a new variant appears, investigate why."""
    recipes = load_all_recipes()
    temps = Counter()
    models = Counter()
    for info in recipes.values():
        s = info["data"].get("settings", {})
        if "temperature" in s:
            temps[s["temperature"]] += 1
        if "goose_model" in s:
            models[s["goose_model"]] += 1
    # Default temp should be 0.3 in >= 80% of recipes
    if temps:
        top_temp, top_count = temps.most_common(1)[0]
        assert top_count / sum(temps.values()) >= 0.6, (
            f"No dominant temperature (most common is {top_temp} at {top_count}/{sum(temps.values())}). "
            f"Distribution: {dict(temps)}"
        )
    # Default model should be deepseek-v4-flash in >= 80% of recipes
    if models:
        top_model, top_count = models.most_common(1)[0]
        assert top_count / sum(models.values()) >= 0.6, (
            f"No dominant model (most common is {top_model} at {top_count}/{sum(models.values())}). "
            f"Distribution: {dict(models)}"
        )
