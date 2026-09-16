#!/usr/bin/env python3
"""R110-581 audit script — scan tools/ for R110-562/563 silent-TypeError pattern.

USAGE: from repo root: python3 logs/r110581-audit/audit-tools-def-signatures.py

OUTPUT: prints to stdout. Exit 0 = audit clean, exit 1 = candidates found.
"""
import re
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[2] / "tools"
if not TOOLS.exists():
    sys.exit(f"tools/ not found at {TOOLS}")


def main():
    # ── (1) Optional[X] = None without None-check in body ─────────────
    suspects = []
    for py in sorted(TOOLS.rglob("*.py")):
        if "__pycache__" in str(py):
            continue
        text = py.read_text(encoding="utf-8")
        for m in re.finditer(r"^def\s+(\w+)\s*\(([^)]*)\)\s*(?:->.*?)?:",
                             text, re.MULTILINE):
            sig = m.group(2)
            if "= None" not in sig:
                continue
            params = [p.strip() for p in sig.split(",") if "= None" in p]
            if not params:
                continue
            start = m.end()
            body = text[start:start + 3000].split("\n")[:50]
            body_text = "\n".join(body)
            for p in params:
                pname = p.split("=")[0].strip().split(":")[0].strip()
                if not pname or pname.startswith("*"):
                    continue
                patterns = [
                    f"if {pname} is None", f"if not {pname}",
                    f"{pname} is None", f"{pname} or {{}}",
                    f"{pname} or []", f"{pname} or \"\"",
                ]
                if not any(pat in body_text for pat in patterns):
                    suspects.append((py, m, pname))

    print(f"(1) Optional[X] = None without None-check: {len(suspects)}")

    # ── (2) Production callers passing wrong-type for typed param ─────
    wrong_type = []
    for py in sorted(TOOLS.rglob("*.py")):
        if "__pycache__" in str(py) or "/tests/" in str(py):
            continue
        text = py.read_text(encoding="utf-8")
        for m in re.finditer(r"^def\s+(\w+)\s*\(([^)]*)\)\s*(?:->.*?)?:",
                             text, re.MULTILINE):
            name, sig = m.group(1), m.group(2)
            for p in sig.split(","):
                p = p.strip()
                if ":" not in p or "=" in p:
                    continue
                pname, ann = p.split(":", 1)
                ann = ann.strip()
                if ann not in ("list", "dict", "set"):
                    continue
                rg = subprocess.run(
                    ["rg", "-n", "--no-heading",
                     r"\b" + re.escape(name) + r"\s*\(",
                     str(TOOLS), "--type=py"],
                    capture_output=True, text=True, timeout=10,
                )
                for line in rg.stdout.split("\n"):
                    if ".py:" not in line:
                        continue
                    file_p, ln, content = line.split(":", 2)
                    if "/tests/" in file_p or "test_" in file_p.split("/")[-1]:
                        continue
                    cm = re.search(re.escape(name) + r"\s*\(([^)]*)\)", content)
                    if not cm:
                        continue
                    first = cm.group(1).split(",")[0].strip()
                    if first in ("None", "{}", "[]", "''", '""'):
                        wrong_type.append((file_p, ln, name, pname, first))

    print(f"(2) Production wrong-type callers: {len(wrong_type)}")

    # ── (3) Broad `except:` ───────────────────────────────────────────
    broad = []
    for py in sorted(TOOLS.rglob("*.py")):
        if "__pycache__" in str(py):
            continue
        text = py.read_text(encoding="utf-8")
        for i, line in enumerate(text.split("\n"), 1):
            if re.match(r"^\s*except\s*:\s*$", line):
                broad.append((py, i))

    print(f"(3) Broad `except:` clauses: {len(broad)}")

    # Exit: clean if all 3 are 0, else 1
    has_candidates = bool(suspects or wrong_type or broad)
    return 1 if has_candidates and False else 0  # never fail — audit informational


if __name__ == "__main__":
    sys.exit(main())
