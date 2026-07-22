"""Test: YAML-Syntax allr Agenten."""
import os
import yaml

SUBS_DIR = os.path.join(os.path.dirname(__file__), "..", "recipe", "sub")


def test_all_agent_yamls():
    """Checks ob all Sub-Agent-YAMLs valide are."""
    if not os.path.exists(SUBS_DIR):
        return  # No agents yet
    for f in os.listdir(SUBS_DIR):
        if f.endswith(".yaml"):
            with open(os.path.join(SUBS_DIR, f)) as fh:
                yaml.safe_load(fh)  # raises on invalid
