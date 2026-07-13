#!/usr/bin/env python3
"""
dev_yaml_generator_generic.py — Generic-Version des YAML-Generators
Generates sub_mas-*.yaml aus agent_schema.yaml (SOT) for User-Projekte.
call: python3 dev_yaml_generator_generic.py --target <user-projekt> [--validate-only] [--diff]
  --target: Zieldirectory (User-Projekt)
  --validate-only: Only validate without writing
  --diff: Show Unterschiede zwischen generates und current
"""
import os, sys, yaml
from dev_yaml_generator_core import generate_agent_yaml, validate_generated

SCHEMA_FILE = ".state/templates/agent_schema.yaml"
SUB_DIR = "sub"

def load_schema(target_dir):
    path = os.path.join(target_dir, SCHEMA_FILE)
    if not os.path.exists(path):
        print(f"❌ Schema not found: {path}")
        sys.exit(1)
    with open(path) as f:
        return yaml.safe_load(f)

def main():
    args = sys.argv[1:]
    target = None
    for i, a in enumerate(args):
        if a == '--target' and i + 1 < len(args):
            target = args[i + 1]
    
    validate_only = '--validate-only' in args
    show_diff = '--diff' in args
    
    if not target:
        print("❌ --target <directory> required")
        sys.exit(1)
    
    target = os.path.abspath(target)
    print(f"🔧 Generic YAML-Generator for: {target}")
    
    schema = load_schema(target)
    agents = schema.get("agents", {})
    std = schema.get("standard_settings", {})
    
    if not agents:
        print("⚠️  No Agenten in agent_schema.yaml (agents: {})")
        print("   → Fill agents: with your agents, then execute again")
        sys.exit(0)
    
    print(f"   {len(agents)} Agenten, Default: timeout={std.get('timeout')}")
    
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
            errors.append(f"  ❌ {out_name}: Generator-Error {e}")
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
    
    print(f"\nResult:")
    print(f"  ✅ Generates: {ok}/{len(agents)}")
    if diff_count:
        print(f"  ⚠️  Deviations: {diff_count}")
    if errors:
        print(f"  ❌ Error: {len(errors)}")
        for e in errors[:3]:
            print(f"    {e}")
    
    return 0 if not errors else 1

if __name__ == "__main__":
    main()
