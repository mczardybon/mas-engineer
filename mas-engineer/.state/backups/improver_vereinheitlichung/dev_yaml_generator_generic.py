#!/usr/bin/env python3
"""
dev_yaml_generator_generic.py — Generic-Version des YAML-Generators
Generiert sub_mas-*.yaml aus agent_schema.yaml (SOT) fuer User-Projekte.
Aufruf: python3 dev_yaml_generator_generic.py --target <user-projekt> [--validate-only] [--diff]
  --target: Zielverzeichnis (User-Projekt)
  --validate-only: Nur validieren ohne zu schreiben
  --diff: Zeige Unterschiede zwischen generiert und aktuell
"""
import os, sys, yaml

SCHEMA_FILE = ".state/templates/agent_schema.yaml"
SUB_DIR = "sub"

def load_schema(target_dir):
    path = os.path.join(target_dir, SCHEMA_FILE)
    if not os.path.exists(path):
        print(f"❌ Schema nicht gefunden: {path}")
        sys.exit(1)
    with open(path) as f:
        return yaml.safe_load(f)

def generate_agent_yaml(agent_name, agent_data, schema):
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
    if not os.path.exists(current_path):
        return False, ["FEHLT"]
    with open(current_path) as f:
        current = f.read()
    
    try:
        g = yaml.safe_load(generated)
        c = yaml.safe_load(current)
    except Exception as e:
        return False, [f"PARSE-FEHLER: {e}"]
    
    diffs = []
    for key in ['title', 'description', 'version']:
        if g.get(key) != c.get(key):
            diffs.append(f"  {key}: gen={g.get(key)} != cur={c.get(key)}")
    
    # Settings vergleichen
    gs = g.get('settings', {})
    cs = c.get('settings', {})
    for k in ['timeout', 'max_steps', 'goose_provider', 'goose_model']:
        if gs.get(k) != cs.get(k):
            diffs.append(f"  settings.{k}: gen={gs.get(k)} != cur={cs.get(k)}")
    
    return len(diffs) == 0, diffs

def main():
    args = sys.argv[1:]
    target = None
    for i, a in enumerate(args):
        if a == '--target' and i + 1 < len(args):
            target = args[i + 1]
    
    validate_only = '--validate-only' in args
    show_diff = '--diff' in args
    
    if not target:
        print("❌ --target <verzeichnis> erforderlich")
        sys.exit(1)
    
    target = os.path.abspath(target)
    print(f"🔧 Generic YAML-Generator für: {target}")
    
    schema = load_schema(target)
    agents = schema.get("agents", {})
    std = schema.get("standard_settings", {})
    
    if not agents:
        print("⚠️  Keine Agenten in agent_schema.yaml (agents: {})")
        print("   → Fülle agents: mit deinen Agenten, dann erneut ausführen")
        sys.exit(0)
    
    print(f"   {len(agents)} Agenten, Standard: timeout={std.get('timeout')}")
    
    sub_path = os.path.join(target, SUB_DIR)
    os.makedirs(sub_path, exist_ok=True)
    
    ok = 0
    diff_count = 0
    errors = []
    
    for name, data in sorted(agents.items()):
        out_name = f"sub_mas-{name}.yaml"
        out_path = os.path.join(sub_path, out_name)
        
        try:
            generated = generate_agent_yaml(name, data, schema)
            yaml.safe_load(generated)
        except Exception as e:
            errors.append(f"  ❌ {out_name}: Generator-Fehler {e}")
            continue
        
        if show_diff or not validate_only:
            valid, issues = validate_generated(name, generated, out_path)
            if valid:
                ok += 1
            else:
                diff_count += 1
                if show_diff:
                    for issue in issues[:3]:
                        print(f"  ⚠️ {out_name}: {issue}")
        
        if not validate_only and not show_diff:
            with open(out_path, 'w') as f:
                f.write(generated)
            ok += 1
    
    print(f"\nErgebnis:")
    print(f"  ✅ Generiert: {ok}/{len(agents)}")
    if diff_count:
        print(f"  ⚠️  Abweichungen: {diff_count}")
    if errors:
        print(f"  ❌ Fehler: {len(errors)}")
        for e in errors[:3]:
            print(f"    {e}")
    
    return 0 if not errors else 1

if __name__ == "__main__":
    main()
