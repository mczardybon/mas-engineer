#!/usr/bin/env python3
"""R110-115 DIREKTIVE 1: parse .directives/R<NR>-<topic>.md into JSON.

Usage:
    python3 tools/dev_directive_parser.py <directive_path> [--json]

Output (JSON):
    {
      "directive_path": "...",
      "r_number": 110,
      "topic": "sub-mas-apply-directive-spec",
      "direktive_blocks": [
        {"nr": 1, "title": "...", "action": "...",
         "scope": "recipe/", "files": [...], "patterns": [...],
         "pre_conditions": [...], "acceptance": [...],
         "hook_points": ["pre-apply", "post-apply", "error"]}
      ],
      "scope": "recipe/,tools/,docs/",
      "pre_conditions": [...],
      "acceptance": [...]
    }
"""
import json
import re
import sys
from pathlib import Path


def parse_directive(path):
    p = Path(path)
    if not p.exists():
        return {"error": f"file not found: {path}"}
    text = p.read_text()
    # Extract R-number
    r_match = re.search(r'R(\d+)-', p.name)
    r_number = int(r_match.group(1)) if r_match else None
    # Extract topic (after R<NR>-)
    topic_match = re.search(r'R\d+-(.+?)\.md$', p.name)
    topic = topic_match.group(1) if topic_match else p.stem
    # Extract DIREKTIVE blocks
    direktive_pattern = re.compile(
        r'##\s*DIREKTIVE\s+(\d+)[^#]*?(?=##\s*DIREKTIVE|\Z)',
        re.DOTALL)
    blocks = []
    for m in direktive_pattern.finditer(text):
        nr = int(m.group(1))
        body = m.group(0)
        # Title = first non-empty line after "## DIREKTIVE N"
        title_match = re.search(r'##\s*DIREKTIVE\s+\d+[:#]?\s*([^\n]+)', body)
        title = title_match.group(1).strip() if title_match else f"DIREKTIVE {nr}"
        # Action = first paragraph (lines until blank line)
        action_match = re.search(r'##\s*DIREKTIVE[^\n]*\n\s*\n([^#\n].*?)(?:\n\s*\n|\n##|\Z)',
                                  body, re.DOTALL)
        action = action_match.group(1).strip() if action_match else ""
        # Files mentioned (rough heuristic)
        files = re.findall(
            r'[`\']([a-zA-Z_][\w/.-]*\.(?:py|yaml|md|sh|json))[`\']',
            body)
        blocks.append({
            "nr": nr,
            "title": title,
            "action": action,
            "files": sorted(set(files)),
        })
    # Scope (heuristic: look for "Scope:" or "## SCOPE" section)
    scope_match = re.search(r'(?:Scope|SCOPE)[:\s]+([^\n]+)', text)
    scope = scope_match.group(1).strip() if scope_match else ""
    # Pre-conditions
    pre_match = re.search(r'(?:Pre-conditions|PRE-CONDITIONS)[:\s]+(.+?)(?:\n\n|\n##|\Z)',
                          text, re.DOTALL)
    pre_conditions = ([pre_match.group(1).strip()] if pre_match else [])
    # Acceptance
    accept_match = re.search(r'(?:Acceptance|ACCEPTANCE)[:\s]+(.+?)(?:\n\n|\n##|\Z)',
                             text, re.DOTALL)
    acceptance = ([accept_match.group(1).strip()] if accept_match else [])
    return {
        "directive_path": str(p),
        "r_number": r_number,
        "topic": topic,
        "scope": scope,
        "pre_conditions": pre_conditions,
        "acceptance": acceptance,
        "direktive_blocks": blocks,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: dev_directive_parser.py <directive_path> [--json]",
              file=sys.stderr)
        sys.exit(2)
    path = sys.argv[1]
    result = parse_directive(path)
    if '--json' in sys.argv:
        print(json.dumps(result, indent=2))
    else:
        print(f"Directive: {result.get('r_number')} {result.get('topic')}")
        print(f"  Scope: {result.get('scope')}")
        print(f"  DIREKTIVE blocks: {len(result.get('direktive_blocks', []))}")
        for b in result.get('direktive_blocks', []):
            print(f"    DIREKTIVE {b['nr']}: {b['title']} "
                  f"({len(b['files'])} files)")
    sys.exit(0 if 'error' not in result else 1)


if __name__ == '__main__':
    main()
