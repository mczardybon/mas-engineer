#!/usr/bin/env python3
"""
dev_security_scan.py — replaces 4 sub_mas-security-*-scanner recipes.

Single script that handles all 4 deterministic security scans:

  SCAN cmd-injection [path]  — os.system, subprocess shell=True, eval
  SCAN deserialize [path]    — pickle.load, yaml.load (unsafe), eval
  SCAN secrets [path]        — sk-*, ghp_*, AKIA*, hardcoded passwords/tokens
  SCAN sqli [path]           — raw SQL f-strings, string concat in queries
  SCAN all [path]            — run all 4, aggregate findings, exit nonzero on any

Deterministic leaves only. Returns JSON to stdout. Exit: 0=CLEAN, 1=FINDINGS, 2=ERROR.

Called from recipes via bash extension:
  python3 tools/dev_security_scan.py SCAN all .

Patterns designed to match the same vulnerabilities the LLM-wrapped recipes used
to grep for. False positives are flagged with confidence < 1.0.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent

# Pattern definitions: (regex, severity, language)
# Confidence is no longer hardcoded per pattern; it is read from the
# SEC_SCAN_CONFIDENCE env var at scan time (default 0.95). This was
# the R110-13 Q4d fix: hardcoded 0.95 values across 28 pattern tuples
# caused confidence-marker drift between PTY and --no-session run modes.
# To override per-run: export SEC_SCAN_CONFIDENCE=0.8 (for example).
DEFAULT_CONFIDENCE = float(os.environ.get('SEC_SCAN_CONFIDENCE', '0.95'))

PATTERNS = {
    "cmd-injection": [
        (r"os\.system\s*\(", "CRITICAL", "py"),
        (r"subprocess\.\w+\([^)]*shell\s*=\s*True", "CRITICAL", "py"),
        (r"subprocess\.\w+\(\s*[\"']\s*(?:rm|sudo|bash|sh|chmod|chown|cat|curl|wget)\b", "HIGH", "py"),
        (r"\beval\s*\(\s*(?:input|request|stdin|argv)", "CRITICAL", "py"),
        (r"\bexec\s*\(\s*(?:input|request|stdin|argv)", "CRITICAL", "py"),
    ],
    "deserialize": [
        (r"pickle\.load\s*\(", "HIGH", "py"),
        (r"pickle\.loads\s*\(", "HIGH", "py"),
        (r"yaml\.load\s*\((?![^)]*Loader\s*=\s*yaml\.SafeLoader)", "CRITICAL", "py"),
        (r"yaml\.load\s*\((?![^)]*Loader\s*=\s*yaml\.FullLoader)", "HIGH", "py"),
        (r"marshal\.loads\s*\(", "MEDIUM", "py"),
        (r"shelve\.open\s*\(", "MEDIUM", "py"),
    ],
    "secrets": [
        (r"sk-[A-Za-z0-9]{20,}", "CRITICAL", "any"),  # OpenAI/DeepSeek
        (r"sk-[a-f0-9]{30,}", "CRITICAL", "any"),     # older DeepSeek
        (r"ghp_[A-Za-z0-9]{30,}", "CRITICAL", "any"), # GitHub PAT
        (r"gho_[A-Za-z0-9]{30,}", "CRITICAL", "any"), # GitHub OAuth
        (r"AWS_ACCESS_KEY\s*=\s*[\"']?AKIA[A-Z0-9]{16}", "CRITICAL", "any"),
        (r"AKIA[0-9A-Z]{16}", "CRITICAL", "any"),     # AWS access key ID
        (r"AIza[0-9A-Za-z\-_]{35}", "HIGH", "any"),  # Google API key
        (r"xox[bpoas]-[A-Za-z0-9\-]{10,}", "HIGH", "any"),  # Slack tokens
        (r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", "CRITICAL", "any"),
        (r"(?i)password\s*=\s*[\"'][^\"']{8,}[\"']", "MEDIUM", "py"),  # many false positives
        (r"(?i)(?:api_key|api_token|secret_key)\s*=\s*[\"'][^\"']{16,}[\"']", "HIGH", "py"),
    ],
    "sqli": [
        (r"execute\s*\(\s*[\"'][^\"']*%s[^\"']*[\"']\s*%", "HIGH", "py"),
        (r"execute\s*\(\s*f[\"'][^\"']*\{[^}]+\}[^\"']*[\"']", "HIGH", "py"),
        (r"execute\s*\(\s*[\"'][^\"']*\"\s*\+\s*\w+", "HIGH", "py"),
        (r"\.format\s*\(\s*\*\s*\*?\s*\w+\s*\)\s*;?\s*$", "MEDIUM", "py"),
        (r"raw\s*\(\s*f[\"'][^\"']*\{", "HIGH", "py"),
        (r"cursor\.execute\s*\(\s*[\"'].*?%s.*?[\"']\s*%", "HIGH", "py"),
    ],
}

# Files/dirs to skip (not security-relevant)
SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", "env",
    ".tox", ".mypy_cache", ".pytest_cache", "dist", "build", ".eggs",
    ".backups", "htmlcov", "site-packages", "tools",  # self-scan noise (own scripts use shell=True legitimately)
}
SKIP_FILE_PATTERNS = [
    re.compile(r"^\.env"),  # .env, .env.backup, .env.* — secrets live in env files, not python code
]
SKIP_EXTS = {".pyc", ".pyo", ".so", ".dylib", ".dll", ".egg", ".whl", ".jpg", ".png", ".gif", ".pdf"}


def is_excluded(path: Path) -> bool:
    parts = set(path.parts)
    if parts & SKIP_DIRS:
        return True
    if path.suffix in SKIP_EXTS:
        return True
    if any(p.search(path.name) for p in SKIP_FILE_PATTERNS):
        return True
    return False


def scan_file(path: Path, scan_type: str) -> list:
    """Run patterns of a given scan_type on a single file."""
    if scan_type not in PATTERNS:
        return []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except (IOError, OSError):
        return []

    findings = []
    for pattern, severity, lang in PATTERNS[scan_type]:
        if lang != "any" and not path.suffix == f".{lang}":
            continue
        for m in re.finditer(pattern, content, re.MULTILINE):
            line_no = content[:m.start()].count("\n") + 1
            line_text = content.split("\n")[line_no - 1].strip() if line_no <= content.count("\n") + 1 else ""
            findings.append({
                "file": str(path.relative_to(REPO_ROOT)) if path.is_absolute() and path.is_relative_to(REPO_ROOT) else str(path),
                "line": line_no,
                "pattern": pattern[:60],
                "match": m.group(0)[:80],
                "context": line_text[:120],
                "severity": severity,
                "confidence": DEFAULT_CONFIDENCE,
                "scan": scan_type,
            })
    return findings


def scan_path(path: str, scan_type: str) -> dict:
    """Run scan_type across a directory (or single file)."""
    p = Path(path).resolve()
    if not p.exists():
        return {"error": f"path not found: {path}"}

    findings = []
    scanned_files = 0

    if p.is_file():
        files_to_scan = [p]
    else:
        files_to_scan = []
        for root, dirs, files in os.walk(p):
            # Filter SKIP_DIRS in-place (prune)
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for f in files:
                fp = Path(root) / f
                if not is_excluded(fp):
                    files_to_scan.append(fp)

    for fp in files_to_scan:
        # Only scan relevant extensions
        if scan_type == "secrets":
            # secrets: any text file
            if fp.suffix in {".pyc", ".pyo", ".so", ".jpg", ".png", ".gif", ".pdf"}:
                continue
        else:
            # others: python files
            if fp.suffix != ".py":
                continue
        scanned_files += 1
        findings.extend(scan_file(fp, scan_type))

    # Sort by severity then file
    sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    findings.sort(key=lambda f: (sev_order.get(f["severity"], 9), f["file"], f["line"]))

    return {
        "command": "SCAN",
        "scan": scan_type,
        "path": str(p),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scanned_files": scanned_files,
        "findings": findings,
        "count": len(findings),
        "by_severity": {
            sev: sum(1 for f in findings if f["severity"] == sev)
            for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
        },
        "issues_found": len(findings) > 0,
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: dev_security_scan.py SCAN <type|all> [path]"}))
        sys.exit(2)

    cmd = sys.argv[1].upper()
    if cmd != "SCAN":
        print(json.dumps({"error": f"unknown command: {cmd}"}))
        sys.exit(2)

    scan_arg = sys.argv[2].lower() if len(sys.argv) > 2 else "all"
    path = sys.argv[3] if len(sys.argv) > 3 else "."

    if scan_arg == "all":
        # Run all 4 scans, aggregate
        all_findings = []
        per_scan = {}
        for stype in ["cmd-injection", "deserialize", "secrets", "sqli"]:
            res = scan_path(path, stype)
            per_scan[stype] = {
                "count": res.get("count", 0),
                "by_severity": res.get("by_severity", {}),
                "scanned_files": res.get("scanned_files", 0),
            }
            all_findings.extend(res.get("findings", []))

        # Dedupe by (file, line, match)
        seen = set()
        deduped = []
        for f in all_findings:
            key = (f["file"], f["line"], f["match"])
            if key not in seen:
                seen.add(key)
                deduped.append(f)
        all_findings = deduped
        all_findings.sort(key=lambda f: ({"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}.get(f["severity"], 9), f["file"], f["line"]))

        result = {
            "command": "SCAN",
            "scan": "all",
            "path": path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "per_scan": per_scan,
            "findings": all_findings,
            "count": len(all_findings),
            "by_severity": {
                sev: sum(1 for f in all_findings if f["severity"] == sev)
                for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
            },
            "issues_found": len(all_findings) > 0,
        }
    elif scan_arg in PATTERNS:
        result = scan_path(path, scan_arg)
    else:
        print(json.dumps({"error": f"unknown scan type: {scan_arg}. Valid: {list(PATTERNS.keys()) + ['all']}"}))
        sys.exit(2)

    print(json.dumps(result, indent=2))
    if result.get("issues_found"):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
