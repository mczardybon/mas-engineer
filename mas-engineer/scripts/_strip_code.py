#!/usr/bin/env python3
"""strip_code_blocks utility — used by e2e-test.sh check [5/10] (R110-253).

Removes fenced code blocks (``` or ~~~) and inline code (`...`) from
text, replacing them with spaces. Newlines are preserved so that any
line numbers in error reports stay accurate.

This module is deliberately standalone (not a package) so e2e-test.sh
can call it via `python3 -c` without import-path gymnastics.
"""
import re


def strip_code_blocks(text):
    """Return text with fenced code blocks and inline code stripped.

    Implementation note: we do NOT use regex for the fenced-block scan
    because fences can contain triple-backticks inside, edge cases like
    unterminated fences at EOF, and ~~~ fences of different lengths.
    A simple state-machine pass is more predictable and easier to
    reason about than a regex.
    """
    out = []
    i = 0
    n = len(text)
    while i < n:
        # Match a fenced-block opener: 3+ backticks or 3+ tildes
        if (i + 2 < n and text[i] == text[i + 1] == text[i + 2] == '`') or \
           (i + 2 < n and text[i] == text[i + 1] == text[i + 2] == '~'):
            fence = text[i:i + 3]
            # The closing fence must be the same character and at least
            # as long. Find the next line that starts with the fence.
            end = -1
            j = i + 3
            while j < n:
                # Skip to next newline
                nl = text.find('\n', j)
                if nl == -1:
                    nl = n
                # Check if this line starts with `fence`
                if text[j:nl].lstrip().startswith(fence):
                    end = nl
                    if end < n and text[end] == '\n':
                        end += 1
                    break
                j = nl + 1
            if end == -1:
                # Unterminated fence — strip rest of file
                out.append(' ' * (n - i))
                break
            block = text[i:end]
            out.append(''.join(c if c == '\n' else ' ' for c in block))
            i = end
        else:
            out.append(text[i])
            i += 1
    text = ''.join(out)
    # Inline code spans: single backtick ... single backtick (no
    # newlines inside). Replace with spaces, preserving length.
    text = re.sub(r'`[^`\n]+`', lambda m: ' ' * len(m.group(0)), text)
    return text


if __name__ == '__main__':
    import sys
    with open(sys.argv[1]) as f:
        text = f.read()
    print(strip_code_blocks(text), end='')
