#!/usr/bin/env python3
"""
dev_template_engine.py — Creates BP-konforme Sub-Agent YAMLs
"""
import argparse, yaml, json, os, sys, datetime
import json
from pathlib import Path

DEFAULT_SETTINGS = {
    'timeout': 600,
    'max_steps': 100,
    'goose_provider': 'openai',
    'goose_model': 'filtered/deepseek/deepseek-chat'
}

def load_best_practices(path):
    bp_path = Path(path) / 'mas-engineer' / '.state' / 'best-practices.yaml'
    if bp_path.exists():
        with open(bp_path) as f:
            data = yaml.safe_load(f)
        return data.get('best_practices', {})
    return {}

def extract_rules(bp, kategorie, max_rules=3):
    rules = bp.get(kategorie, [])
    return [r.get('rule', '?') for r in rules[:max_rules]]

def generate_yaml(name, emoji, task, output, workspace, mode='mas', auto_commit=False):
    bp = load_best_practices(workspace)
    prefix = 'sub_mas-' if mode == 'mas' else ''
    agent_name = prefix + name
    
    scope = task.split()[0].lower() if task.split() else 'arbeiten'
    struktur = extract_rules(bp, 'structure', 3)
    settings_r = extract_rules(bp, 'settings', 2)
    prompt_r = extract_rules(bp, 'prompt', 2)
    
    prompt = emoji + " " + name.upper() + " (v1.0.0)"
    prompt += "\n⛔ NUR " + scope + " — NOE anderen actionen"
    prompt += "\n→ Give Result als strukturierten Report back"
    
    lines = ["# " + agent_name + " — " + emoji + " " + task]
    lines.append("")
    lines.append(task)
    lines.append("")
    lines.append("## Input (vom MAS-Engineer)")
    lines.append("Der MAS-Engineer aboutgivet these parameterss via delegate():")
    lines.append("- signal: HANDOVER")
    lines.append("- request_id: string (UUID)")
    lines.append("- from: dev-mas-engineer")
    lines.append("- to: " + agent_name)
    lines.append("- task: TASK_NAME | ALTERNATE_TASK")
    lines.append("- workspace: Path to the Workspace")
    lines.append("- mode: " + mode)
    lines.append("")
    lines.append("## Best-Practices (aus " + str(len(bp)) + " Kategorien)")
    lines.append("")
    lines.append("### Struktur-Rulen:")
    for r in struktur:
        lines.append("- " + r)
    if not struktur:
        lines.append("- version: 1.0.0 in Frontmatter")
    lines.append("")
    lines.append("### Settings-Rulen:")
    for r in settings_r:
        lines.append("- " + r)
    if not settings_r:
        lines.append("- timeout: 600 = Sweet-Spot")
    lines.append("")
    lines.append("### Prompt-Rulen:")
    for r in prompt_r:
        lines.append("- " + r)
    if not prompt_r:
        lines.append("- prompt unter 500 Zeichen")
    if auto_commit:
        prompt += '\n\n# AUTO-COMMIT AKTIV:\n'
        prompt += '# NACH Change: git add -A && git commit -m "[MAS] {action}"\n'
        prompt += '# checkpoint .state/checkpoints/{ts}/ + changes.json + todo\n'

    lines.append("")
    lines.append("## STEPS:")
    lines.append("1. Read Input")
    lines.append("2. Execute " + task + " durch")
    lines.append("3. Give strukturierten Report back")
    lines.append("")
    lines.append("## Output")
    lines.append("- signal: DONE")
    lines.append("- request_id: UUID (vom Input)")
    lines.append("- from: " + agent_name)
    lines.append("- to: {from} (caller)")
    lines.append("- status: success | error | timeout")
    lines.append("- result: {result} (agentenspezifisch)")
    lines.append("")
    lines.append("⛔ NUR " + scope)
    lines.append("⛔ NOE recursion")
    lines.append("⛔ NOE Changeen an anderen files")
    
    instructions = "\n".join(lines)
    
    yaml_data = {
        'version': '1.0.0',
        'title': emoji + " " + name.upper() + " (v1.0.0)",
        'description': task + " — BP-konformer Sub-Agent",
        'prompt': prompt,
        'instructions': instructions,
        # auto_commit injected into prompt above
    'settings': dict(DEFAULT_SETTINGS)
    }
    
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    with open(output_path) as f:
        validated = yaml.safe_load(f)
    
    return {
        'name': agent_name,
        'emoji': emoji,
        'task': task,
        'prompt_len': len(validated.get('prompt', '')),
        'instructions_len': len(validated.get('instructions', '')),
        'bp_rules': sum(len(v) for v in bp.values()),
        'output': str(output_path),
        'mode': mode
    }

def main():
    parser = argparse.ArgumentParser(description='Create BP-konforme Sub-Agent YAML')
    parser.add_argument('--name', required=True)
    parser.add_argument('--emoji', default='\U0001f527')
    parser.add_argument('--task', required=True)
    parser.add_argument('--output', default='recipe/sub/sub_mas-agent.yaml')
    parser.add_argument('--workspace', default=os.getcwd())
    parser.add_argument('--mode', default='mas', choices=['mas', 'generic'])
    parser.add_argument('--auto-commit', action='store_true', help='Aktiviere Auto-commit-Block im generateden Agenten')
    parser.add_argument('--project', default=os.path.basename(os.getcwd()))
    parser.add_argument('--registry', default=None)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    
    stats = generate_yaml(args.name, args.emoji, args.task, args.output, args.workspace, args.mode, getattr(args, 'auto_commit', False))
    if args.registry:
        import subprocess
        f_item = [{'type': 'Z1', 'agent': stats['name'], 'severity': 'niedrig', 'detail': f'Neuer Agent: {stats["name"]}'}]
        merge_tool = os.path.join(os.getcwd(), 'mas-engineer', 'tools', 'dev_registry_merge.py')
        subprocess.run(['python3', merge_tool, '--findings', json.dumps(f_item), '--registry', args.registry, '--project', args.project], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    if args.json:
        print(json.dumps(stats, indent=2))
    else:
        print("Agent creates: " + stats['name'])
        print("  prompt: " + str(stats['prompt_len']) + " Z")
        print("  instructions: " + str(stats['instructions_len']) + " Z")
        print("  BP-Rulen: " + str(stats['bp_rules']))
        print("  file: " + stats['output'])

if __name__ == '__main__':
    main()
