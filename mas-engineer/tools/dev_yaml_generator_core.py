#!/usr/bin/env python3
"""
dev_yaml_generator_core.py — Gemeinsamer Kern for YAML-Generierung
Contains generate_agent_yaml() und validate_generated() for beide Varianten.

Nutzung:
  from dev_yaml_generator_core import generate_agent_yaml, validate_generated
"""
import os
import yaml


def generate_agent_yaml(agent_name, agent_data, schema):
    """Generates den YAML-String for a Agenten from dem Schema."""
    std = schema.get("standard_settings", {})
    tags = schema.get("template_tags", {})

    emoji = agent_data.get("emoji", "")
    title = agent_data.get("title", f"SUB-MAS-{agent_name.upper()}")
    header = tags.get("HEADER", "{emoji} {title}").format(emoji=emoji, title=title)

    prompt_text = agent_data.get("prompt", "")
    if prompt_text and not prompt_text.startswith(header):
        prompt_text = header + "\n\n" + prompt_text
    prompt_text = prompt_text.replace("'", "''")

    instr_text = agent_data.get("instructions", "")
    instr_r01 = tags.get("R01", "")
    instr_r09 = tags.get("R09", "")

    tag_r01 = instr_r01.replace('\\', '\\\\').replace('"', '\\"')
    tag_r09 = instr_r09.replace('\\', '\\\\').replace('"', '\\"')

    if instr_r01 and tag_r01 not in instr_text:
        instr_text += instr_r01
    if instr_r09 and tag_r09 not in instr_text:
        instr_text += instr_r09

    instr_text = instr_text.replace('\\', '\\\\').replace('"', '\\"')
    instr_text = instr_text.replace('\x0c', '\\n')

    desc = agent_data.get("description", f"v1.0.0 | {title}")

    settings = dict(std)
    agent_settings = agent_data.get("settings", {})
    if agent_settings:
        for k in agent_settings:
            if agent_settings[k] is not None:
                settings[k] = agent_settings[k]

    lines = []
    lines.append('version: "1.0.0"')
    lines.append(f"title: {title}")
    lines.append(f"description: '{desc}'")
    lines.append(f'instructions: "{instr_text}"')
    lines.append(f"prompt: '{prompt_text}'")
    lines.append("settings:")
    for k, v in settings.items():
        lines.append(f"  {k}: {v}")

    return "\n".join(lines) + "\n"


def validate_generated(name, generated, current_path):
    """Validated generierten YAML gegen existing file."""
    if not os.path.exists(current_path):
        return False, ["FEHLT"]
    with open(current_path) as f:
        current = f.read()
    try:
        g = yaml.safe_load(generated)
        c = yaml.safe_load(current)
    except Exception as e:
        return False, [f"PARSE-ERROR: {e}"]
    diffs = []
    for key in ['title', 'description', 'version']:
        if g.get(key) != c.get(key):
            diffs.append(f"  {key}: gen={g.get(key)} != cur={c.get(key)}")
    gs = g.get('settings', {})
    cs = c.get('settings', {})
    for k in ['timeout', 'max_steps', 'goose_provider', 'goose_model']:
        if gs.get(k) != cs.get(k):
            diffs.append(f"  settings.{k}: gen={gs.get(k)} != cur={cs.get(k)}")
    return len(diffs) == 0, diffs
