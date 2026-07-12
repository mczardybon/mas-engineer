#!/usr/bin/env python3
"""
dev_intention_parser.py — CLI for den Intention-Parser

Usage:
  python3 tools/dev_intention_parser.py "Ich brauche a Agent der..."
  python3 tools/dev_intention_parser.py --analyse "Description"
  python3 tools/dev_intention_parser.py --validate
  python3 tools/dev_intention_parser.py --schema
"""
import yaml, os, sys, json, re, subprocess

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF_FILE = os.path.join(BASE, ".state", "workflows.yaml")
SCHEMA_FILE = os.path.join(BASE, ".state", "sot_schema.yaml")
TEMPLATE = os.path.join(BASE, "recipe", "template", "agent_template.yaml")
SUB_DIR = os.path.join(BASE, "recipe", "sub")

def load_workflows():
    with open(WF_FILE) as f:
        return yaml.safe_load(f)

def save_workflows(data):
    with open(WF_FILE, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

def analyse_intention(text):
    result = {
        "typee": "sub",
        "name": None,
        "task": text[:120],
        "remainderrictions": {"allowed_paths": [], "forbidden_paths": [], "requires_confirmation": True},
        "workflow_steps": []
    }
    t = text.lower()
    if any(w in t for w in ["autonomous", "vollagent", "eigener prompt"]):
        result["typee"] = "voll"
    elif any(w in t for w in ["function", "erweiterung", "in existierend"]):
        result["typee"] = "intern"
    name_match = re.search(r'(?:agent|tool|function)\s+(?:der|die|das)\s+(\w+)', t)
    if name_match:
        result["name"] = name_match.group(1) + "-agent"
    if not result["name"]:
        words = [w for w in re.findall(r'\w+', t) if len(w) > 4 and w not in ['a', 'a', 'a', 'theser', 'which', 'whichr', 'sollen', 'will', 'theses']]
        result["name"] = (words[1] if len(words) > 1 else words[0] if words else "agent") + "-agent" if len(words) > 0 else "agent"
    path_patterns = re.findall(r'(?:may|should|only|not|exclusively)\s+([\w/.-]+)', t)
    if path_patterns:
        result["remainderrictions"]["allowed_paths"] = [p for p in path_patterns if 'not' not in p and 'may' not in p]
    if any(w in t for w in ["cancel", "stopp", "error cancel"]):
        result["workflow_steps"].append({"id": "main", "action": "shell", "cmd": "", "on_error": "abort"})
    else:
        result["workflow_steps"].append({"id": "main", "action": "shell", "cmd": "", "on_error": "continue"})
    return result

def validate_sot():
    errors = []
    wf = load_workflows()
    try:
        with open(SCHEMA_FILE) as f:
            schema = yaml.safe_load(f)
    except Exception as e:
        return [f"Schema-Error: {e}"]
    required = schema.get("agent_schema", {}).get("required", ["name", "typee", "task"])
    agents = wf.get("agents", {})
    for name, config in agents.items():
        if name.startswith("_"):
            continue
        for field in required:
            if field not in config:
                errors.append(f"{name}: missings required field '{field}'")
    return errors

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--validate" in args:
        errs = validate_sot()
        print("✅ SOT valide" if not errs else "\n".join(f"❌ {e}" for e in errs))
    elif "--schema" in args:
        with open(SCHEMA_FILE) as f:
            print(f.read())
    elif args and not args[0].startswith("--"):
        r = analyse_intention(" ".join(args))
        print(json.dumps(r, indent=2, ensure_ascii=False))
    else:
        print(__doc__)
