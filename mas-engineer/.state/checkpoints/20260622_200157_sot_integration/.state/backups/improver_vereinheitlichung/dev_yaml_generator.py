#!/usr/bin/env python3
"""
dev_yaml_generator.py — Generiert sub_mas-*.yaml aus agent_schema.yaml (SOT)
Aufruf: python3 dev_yaml_generator.py [--validate-only] [--diff] [--write]
  --validate-only: Nur validieren ohne zu schreiben
  --diff: Zeige Unterschiede zwischen generiert und aktuell (kein Schreiben)
  --write: Generiere alle 36 YAMLs (Standard: nur validieren)
"""
import os, sys, yaml, re, json

AGENT_SCHEMA = ".state/templates/agent_schema.yaml"
SUB_DIR = "recipe/sub"

def load_schema():
    if not os.path.exists(AGENT_SCHEMA):
        print(f"❌ Schema nicht gefunden: {AGENT_SCHEMA}")
        sys.exit(1)
    with open(AGENT_SCHEMA) as f:
        return yaml.safe_load(f)

def generate_agent_yaml(agent_name, agent_data, schema):
    """Generiert den YAML-String fuer einen Agenten aus dem Schema."""
    std = schema.get("standard_settings", {})
    tags = schema.get("template_tags", {})
    
    # Header
    emoji = agent_data.get("emoji", "")
    title = agent_data.get("title", f"SUB-MAS-{agent_name.upper()}")
    header = tags.get("HEADER", "{emoji} {title}").format(emoji=emoji, title=title)
    
    # Prompt: Header + Inhalt
    prompt_text = agent_data.get("prompt", "")
    if prompt_text and not prompt_text.startswith(header):
        prompt_text = header + "\n\n" + prompt_text
    # Escaping fuer SQ-String: ' -> ''
    prompt_text = prompt_text.replace("'", "''")
    
    # Instructions: Basis + R01 + R09
    instr_text = agent_data.get("instructions", "")
    instr_r01 = tags.get("R01", "")
    instr_r09 = tags.get("R09", "")
    
    # Escaping fuer template_tags (Dieselben Escapes wie fuer instr_text)
    tag_r01 = instr_r01.replace('\\', '\\\\').replace('"', '\\"')
    tag_r09 = instr_r09.replace('\\', '\\\\').replace('"', '\\"')
    
    # Baue instructions: Basis + R01 + R09
    if instr_r01 and tag_r01 not in instr_text:
        instr_text += instr_r01
    if instr_r09 and tag_r09 not in instr_text:
        instr_text += instr_r09
    
    # Escaping fuer DQ-String (nach template_tags)
    instr_text = instr_text.replace('\\', '\\\\').replace('"', '\\"')
    # Entferne Sonderzeichen: Form Feed, etc.
    instr_text = instr_text.replace('\x0c', '\\n')  # Form Feed -> newline
    # Entferne --- innerhalb des Strings (YAML document separator)
    instr_text = instr_text.replace('\\n---\\n', '\\n---\\n'.replace('---', '-\\n-'))
    
    # Description
    desc = agent_data.get("description", f"v1.0.0 | MAS-intern: {title}")
    
    # Settings: Standard + Override
    settings = dict(std)
    agent_settings = agent_data.get("settings", {})
    for k in agent_settings:
        if agent_settings[k] is not None:
            settings[k] = agent_settings[k]
    
    # Baue YAML-Struktur
    lines = []
    lines.append("version: \"1.0.0\"")
    lines.append(f"title: {title}")
    lines.append(f"description: '{desc}'")
    lines.append(f"instructions: \"{instr_text}\"")
    lines.append(f"prompt: '{prompt_text}'")
    lines.append("settings:")
    for k, v in settings.items():
        lines.append(f"  {k}: {v}")
    
    return "\n".join(lines) + "\n"

def validate_generated(name, generated, current_path):
    """Vergleicht generierten YAML mit aktueller Datei."""
    if not os.path.exists(current_path):
        return False, "FEHLT"
    with open(current_path) as f:
        current = f.read()
    
    try:
        g = yaml.safe_load(generated)
        c = yaml.safe_load(current)
    except Exception as e:
        return False, f"PARSE-FEHLER: {e}"
    
    differences = []
    
    # Vergleiche Felder
    for key in g:
        if key != 'instructions' and key != 'prompt':  # Überspringe format-abhängige
            if g.get(key) != c.get(key):
                differences.append(f"  {key}: generiert={g.get(key)} != aktuell={c.get(key)}")
    
    return len(differences) == 0, differences

def main():
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    validate_only = '--validate-only' in sys.argv
    show_diff = '--diff' in sys.argv
    do_write = '--write' in sys.argv
    
    schema = load_schema()
    agents = schema.get("agents", {})
    std = schema.get("standard_settings", {})
    
    print(f"🤖 YAML-Generator: {len(agents)} Agenten aus {AGENT_SCHEMA}")
    print(f"   Standard: timeout={std.get('timeout')}, max_steps={std.get('max_steps')}, provider={std.get('goose_provider')}")
    print()
    
    ok = 0
    diff_agents = 0
    errors = []
    
    for name, data in sorted(agents.items()):
        out_name = f"sub_mas-{name}.yaml"
        out_path = os.path.join(SUB_DIR, out_name)
        
        generated = generate_agent_yaml(name, data, schema)
        
        try:
            g = yaml.safe_load(generated)
        except Exception as e:
            errors.append(f"  ❌ {out_name}: Generator-Fehler {e}")
            continue
        
        if validate_only or show_diff or not do_write:
            valid, issues = validate_generated(name, generated, out_path)
            if valid:
                ok += 1
            else:
                diff_agents += 1
                if show_diff:
                    print(f"  ⚠️ {out_name}: {len(issues)} Unterschiede")
                    for issue in issues[:3]:
                        print(f"    {issue}")
        else:
            ok += 1
        
        if do_write:
            with open(out_path, 'w') as f:
                f.write(generated)
    
    print(f"\nErgebnis:")
    print(f"  ✅ Identisch: {ok}/{len(agents)}")
    if diff_agents:
        print(f"  ⚠️  Unterschiede: {diff_agents}/{len(agents)}")
    if errors:
        print(f"  ❌ Fehler: {len(errors)}")
        for e in errors[:3]:
            print(f"    {e}")
    
    if errors:
        sys.exit(1)
    return 0

if __name__ == "__main__":
    main()
