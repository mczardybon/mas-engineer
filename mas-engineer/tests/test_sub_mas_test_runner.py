"""
test_sub_mas_test_runner.py — sanity tests for sub_mas-test-runner recipe.

These tests verify that the recipe file exists, is valid YAML, and has the
required fields per the constitution (sub_mas-master-constitution.yaml).

Run with:
    python3 -m pytest tests/test_sub_mas_test_runner.py -v
"""
import yaml
import os
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
TEST_RUNNER_RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-test-runner.yaml"
TEST_RUNNER_INSTRUCTIONS = REPO_ROOT / "recipe" / "instructions" / "sub_mas-test-runner.md"


def test_test_runner_recipe_exists():
    """Recipe file must exist at the canonical location."""
    assert TEST_RUNNER_RECIPE.exists(), f"Missing: {TEST_RUNNER_RECIPE}"


def test_test_runner_recipe_is_valid_yaml():
    """Recipe must be parseable as YAML (R10 CORONASHIELD)."""
    with open(TEST_RUNNER_RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), "Recipe must be a YAML mapping"


def test_test_runner_recipe_has_required_fields():
    """Constitution (master) requires: name, version, instructions, prompt, settings."""
    with open(TEST_RUNNER_RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "instructions", "prompt", "settings"):
        assert field in data, f"Missing required field: {field}"


def test_test_runner_recipe_references_constitution():
    """Recipe must declare which constitution it follows (R10 traceability)."""
    with open(TEST_RUNNER_RECIPE) as f:
        data = yaml.safe_load(f)
    assert "constitution" in data, "Missing constitution reference"
    assert data["constitution"] == "sub_mas-master-constitution.yaml", \
        f"Wrong constitution: {data['constitution']}"


def test_test_runner_instructions_file_exists():
    """The external instructions file must exist (referenced by recipe)."""
    assert TEST_RUNNER_INSTRUCTIONS.exists(), f"Missing: {TEST_RUNNER_INSTRUCTIONS}"


def test_test_runner_instructions_mention_pytest():
    """The instructions must mention pytest (sanity check that the test-runner
    is actually for pytest, not unittest or nose)."""
    content = TEST_RUNNER_INSTRUCTIONS.read_text()
    assert "pytest" in content, "Instructions should mention pytest"
    # Should also EXPLICITLY forbid other test frameworks
    assert "unittest" in content or "nose" in content or "tox" in content, \
        "Instructions should explicitly forbid non-pytest frameworks (R10 boundary)"


def test_test_runner_has_summon_extension():
    """sub_mas-test-runner must have the summon extension (per 2026-07-22 patches)."""
    with open(TEST_RUNNER_RECIPE) as f:
        data = yaml.safe_load(f)
    extensions = data.get("extensions", [])
    ext_names = [e.get("name") for e in extensions]
    assert "summon" in ext_names, \
        f"summon extension missing. extensions: {extensions}"
