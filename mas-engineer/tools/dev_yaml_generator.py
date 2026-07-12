#!/usr/bin/env python3
"""
dev_yaml_generator.py — Generates sub_mas-*.yaml aus agent_schema.yaml (SOT)
call:
  python3 dev_yaml_generator.py [--mode mas|generic] [--target PFAD] [--validate-only] [--diff] [--write]
  
  --mode mas (default):  Nutzt .state/templates/agent_schema.yaml, writes after recipe/sub/
  --mode generic:        Nutzt --target/.state/templates/agent_schema.yaml, writes after --target/sub/
  --validate-only:       Only validate ohne zu write
  --diff:                Show Unterschiede zwischen generates und current
  --write:               Write generatede YAMLs (Default: only validate)
"""
import os, sys
from dev_yaml_generator_core import generate_agent_yaml, validate_generated

MAS_SCHEMA = ".state/templates/agent_schema.yaml"
GEN_SCHEMA = ".state/templates/agent_schema_generic.yaml"
MAS_SUB_DIR = "recipe/sub"

def find_schema(mode, target=None):
    """Finde Schema basierend auf Mode."""
    if mode == "generic" and target:
        path = os.path.join(target, ".state/templates/agent_schema.yaml")
        if os.path.exists(path):
            return path
        # Fallback: generic Variante
        path2 = os.path.join(target, ".state/templates/agent_schema_generic.yaml")
        if os.path.exists(path2):
            return path2
        print(f"❌ No Schema in {target}/.state/templates/ found")
        sys.exit(1)
    elif mode == "generic":
        if os.path.exists(GEN_SCHEMA):
            return GEN_SCHEMA
    # MAS-Mode oder Fallback
    if os.path.exists(MAS_SCHEMA):
        return MAS_SCHEMA
    print(f"❌ Schema not found: {MAS_SCHEMA}")
    sys.exit(1)

def find_sub_dir(mode, target=None):
    if mode == "generic" and target:
        p = os.path.join(target, "sub")
        os.makedirs(p, exist_ok=True)
        return p
    os.makedirs(MAS_SUB_DIR, exist_ok=True)
    return MAS_SUB_DIR

def load_schema(path):
    with open(path) as f:
        return yaml.safe_load(f)

def main():
    mode = "mas"
    target = None
    validate_only = '--validate-only' in sys.argv
    show_diff = '--diff' in sys.argv
    do_write = '--write' in sys.argv
    
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == '--mode' and i + 1 < len(args):
            mode = args[i + 1]
        if a == '--target' and i + 1 < len(args):
            target = os.path.abspath(args[i + 1])
    
    if mode not in ("mas", "generic"):
        print(f"❌ Unbekannter Mode: {mode} — erwarte 'mas' oder 'generic'")
        sys.exit(1)
    
    schema_path = find_schema(mode, target)
    sub_dir = find_sub_dir(mode, target)
    schema = load_schema(schema_path)
    agents = schema.get("agents", {})
    std = schema.get("standard_settings", {})
    
    print(f"🤖 YAML-Generator (mode={mode}): {len(agents)} Agenten aus {schema_path}")
    print(f"   Default: timeout={std.get('timeout')}, max_steps={std.get('max_steps')}")
    print(f"   Target: {sub_dir}")
    print()
    
    if not agents:
        print("⚠️  No Agenten in agent_schema.yaml (agents: {})")
        sys.exit(0)
    
    ok = 0
    diff_count = 0
    errors = []
    
    for name, data in sorted(agents.items()):
        out_name = f"sub_mas-{name}.yaml"
        out_path = os.path.join(sub_dir, out_name)
        
        try:
            generated = generate_agent_yaml(name, data, schema)
            yaml.safe_load(generated)
        except Exception as e:
            errors.append(f"  ❌ {out_name}: Generator-Error {e}")
            continue
        
        if do_write:
            with open(out_path, 'w') as f:
                f.write(generated)
            ok += 1
        elif show_diff or validate_only:
            valid, issues = validate_generated(name, generated, out_path)
            if valid:
                ok += 1
            else:
                diff_count += 1
                if show_diff:
                    for issue in issues[:3]:
                        print(f"  ⚠️  {out_name}: {issue}")
    
    print(f"\nResult:")
    print(f"  ✅ OK: {ok}/{len(agents)}")
    if diff_count:
        print(f"  ⚠️  Deviations: {diff_count}")
    if errors:
        print(f"  ❌ Error: {len(errors)}")
        for e in errors[:3]:
            print(f"    {e}")
    
    return 0 if not errors else 1

if __name__ == "__main__":
    main()
