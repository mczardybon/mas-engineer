#!/usr/bin/env python3
"""Doc-link check — e2e-test.sh [5/10] (R110-253).

Scans markdown files for non-http markdown links, and reports any
whose target does not exist on disk. Used as a single source of
truth for the e2e link check; called from e2e-test.sh.

Improvements over the original inline check:
  1. Strips fenced code blocks and inline code BEFORE scanning, so
     regex patterns inside backticks are not false-positives.
  2. Uses a stricter markdown-link regex `[text](url)` that requires
     both [text] and (url) to be on the same line, neither containing
     Python-source-like chars (backslash, quotes, backticks). This
     eliminates false-positives on Python source like `["\'](\d+)`
     that the previous `](X)`-only regex would catch.

R110-253 reason: the previous check produced 4 false-positives on
.mase/directives/*.md files containing indented Python source
samples. Those are NOT markdown links — markdown's [text](url) syntax
requires the [ and ] to wrap prose link text, not be embedded inside
a Python raw string.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _strip_code import strip_code_blocks


SCOPE = os.environ.get('E2E_SCOPE', 'all')
FILE_FILTER = os.environ.get('E2E_FILE_FILTER', '')


def find_docs():
    if SCOPE == 'all':
        roots = ['docs', 'recipe/instructions', '.']
    else:
        roots = ['docs', 'recipe/instructions', 'recipe', '.']
        with open(FILE_FILTER) as f:
            changed = set(line.strip() for line in f if line.strip())
    docs = []
    for r in roots:
        if os.path.isdir(r):
            for root, _, files in os.walk(r):
                if any(x in root for x in ('/node_modules/', '/.git/',
                                            '/.monitor/memory/', '/.mase/mcp/')):
                    continue
                for fn in files:
                    if fn.endswith('.md'):
                        full = os.path.join(root, fn)
                        if SCOPE != 'all' and full not in changed:
                            continue
                        docs.append(full)
    return sorted(set(d for d in docs
                      if not d.startswith('vendor/')
                      and not d.startswith('node_modules/')))


# Markdown link pattern. Requires:
#   - [text]: 2+ chars, no ']', newline, backslash, quote, or backtick
#   - (url): 1+ chars, no ')', newline, backslash, quote, or backtick
# These exclusions eliminate the false-positive class where Python
# source code happens to contain a `](X)` substring inside a raw
# triple-quoted string.
LINK_RE = re.compile(r'\[([^\]\n\\"\'`]{2,}?)\]\(([^\)\n\\"\'`]+)\)')


def check_doc_links():
    total_broken = 0
    for doc in find_docs():
        with open(doc) as f:
            text = f.read()
        doc_dir = os.path.dirname(doc)
        # R110-253: strip fenced code + inline code first to avoid
        # false-positives on regex patterns like `r'\\d+'`.
        scan_text = strip_code_blocks(text)
        for match in LINK_RE.finditer(scan_text):
            link_text, url = match.group(1), match.group(2)
            if url.startswith(('http://', 'https://', '#', 'mailto:')):
                continue
            target = url.split('#')[0]
            if not target:
                continue
            if doc_dir and not target.startswith('/'):
                full = os.path.join(doc_dir, target)
            else:
                full = target
            if not os.path.exists(full):
                print(f'    broken: {doc} -> {url}')
                total_broken += 1
    return total_broken


if __name__ == '__main__':
    n = check_doc_links()
    sys.exit(0 if n == 0 else 1)
