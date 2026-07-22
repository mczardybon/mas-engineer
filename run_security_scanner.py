#!/usr/bin/env python3
"""
MAS Security Scanner (v1.0.0) — SQL injection, secrets, unsafe deserialization, command injection
Reads instructions from recipe/instructions/security-scanner.md
"""
import json
import os
import re
import sys

WORKSPACE = "/workspace/mas-engineer-src"
MAX_FILES = 50
EXCLUDE_DIRS = ["venv", ".venv", "__pycache__", "node_modules", ".git"]

def discover_source_files(target):
    """Discover .py, .js, .ts, .yaml, .yml, .env, .json files."""
    extensions = (".py", ".js", ".ts", ".yaml", ".yml", ".env", ".json")
    files = []
    for root, dirs, fnames in os.walk(target):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".")]
        for fname in fnames:
            if fname.endswith(extensions):
                files.append(os.path.join(root, fname))
    return files[:MAX_FILES]

def detect_sql_injection(filepath, relpath):
    """2a — SQL Injection Detection."""
    sql_risky_patterns = [
        (r"cursor\.execute\(.*f['\"]", "fstring_in_execute"),
        (r"cursor\.execute\(.*\s*\+\s*", "concat_in_execute"),
        (r"cursor\.execute\(.*%.*%", "percent_format_in_execute"),
        (r"\.format\(.*\).*SELECT", "format_in_sql"),
        (r"f['\"].*SELECT.*\{.*\}.*['\"]", "fstring_sql_injection"),
        (r"execute_query\(.*f['\"]", "fstring_in_execute_query"),
    ]
    findings = []
    try:
        with open(filepath) as f:
            lines = f.readlines()
    except Exception:
        return findings

    for i, line in enumerate(lines, 1):
        for pattern, vuln_type in sql_risky_patterns:
            if re.search(pattern, line):
                findings.append({
                    "file": relpath,
                    "severity": "CRITICAL",
                    "category": "sql_injection",
                    "line": i,
                    "snippet": line.strip()[:120],
                    "message": f"Potential SQL injection: {vuln_type} on line {i}"
                })
    return findings

def detect_hardcoded_secrets(filepath, relpath):
    """2b — Hardcoded Secrets Detection."""
    secret_patterns = [
        (r"(?i)(api[_-]?key|apikey|secret|password|token|auth)\s*=\s*['\"][^'\"]+['\"]", "hardcoded_credential"),
        (r"-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----", "private_key"),
        (r"(?i)(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36}", "github_token"),
        (r"(?i)sk-[A-Za-z0-9]{32,}", "openai_api_key"),
        (r"(?i)A[KS]IA[0-9A-Z]{16}", "aws_access_key"),
        (r"(?i)AKIA[0-9A-Z]{16}", "aws_access_key_id"),
    ]
    findings = []
    
    # Skip test/example files for secret detection
    file_lower = relpath.lower()
    if "test" in file_lower or "example" in file_lower:
        return findings

    try:
        with open(filepath) as f:
            content = f.read()
            lines = content.split("\n")
    except Exception:
        return findings

    for i, line in enumerate(lines, 1):
        for pattern, vuln_type in secret_patterns:
            if re.search(pattern, line):
                # Skip innocent patterns like "password" in comments/docs
                severity = "HIGH" if vuln_type != "hardcoded_credential" else "MEDIUM"
                findings.append({
                    "file": relpath,
                    "severity": severity,
                    "category": vuln_type,
                    "line": i,
                    "snippet": line.strip()[:120],
                    "message": f"Possible {vuln_type} found on line {i}"
                })
    return findings

def detect_unsafe_deserialization(filepath, relpath):
    """2c — Unsafe Deserialization Detection."""
    unsafe_patterns = [
        (r"pickle\.(loads|load)\(", "pickle_deserialization"),
        (r"yaml\.load\(", "unsafe_yaml_load"),
        (r"eval\(", "eval_execution"),
        (r"exec\(", "exec_execution"),
        (r"__import__\(", "dynamic_import"),
        (r"marshal\.(loads|load)\(", "marshal_deserialization"),
        (r"cPickle\.(loads|load)\(", "cPickle_deserialization"),
    ]
    findings = []
    try:
        with open(filepath) as f:
            lines = f.readlines()
    except Exception:
        return findings

    for i, line in enumerate(lines, 1):
        for pattern, vuln_type in unsafe_patterns:
            if re.search(pattern, line):
                severity = "HIGH" if vuln_type in ("pickle_deserialization", "cPickle_deserialization", "eval_execution") else "MEDIUM"
                findings.append({
                    "file": relpath,
                    "severity": severity,
                    "category": "unsafe_deserialization",
                    "line": i,
                    "snippet": line.strip()[:120],
                    "message": f"Unsafe deserialization: {vuln_type} on line {i}"
                })
    return findings

def detect_command_injection(filepath, relpath):
    """2d — Command Injection Detection."""
    cmd_patterns = [
        (r"os\.system\(.*f['\"]", "os_system_fstring"),
        (r"subprocess\.(call|Popen|run)\(.*shell\s*=\s*True", "subprocess_shell_true"),
        (r"os\.popen\(", "os_popen"),
        (r"`.*\$", "shell_in_backticks"),
    ]
    findings = []
    try:
        with open(filepath) as f:
            lines = f.readlines()
    except Exception:
        return findings

    for i, line in enumerate(lines, 1):
        for pattern, vuln_type in cmd_patterns:
            if re.search(pattern, line):
                findings.append({
                    "file": relpath,
                    "severity": "CRITICAL" if vuln_type != "os_popen" else "HIGH",
                    "category": "command_injection",
                    "line": i,
                    "snippet": line.strip()[:120],
                    "message": f"Potential command injection: {vuln_type} on line {i}"
                })
    return findings

def get_severity_sort_key(severity):
    mapping = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    return mapping.get(severity, 99)

def main():
    target = WORKSPACE
    files = discover_source_files(target)
    total = len(files)
    
    print(f"🛡️  Security Scanner (v1.0.0)")
    print(f"Scanning {total} files in {target}")
    print("=" * 60)
    
    all_findings = []
    
    for i, filepath in enumerate(files, 1):
        relpath = os.path.relpath(filepath, WORKSPACE)
        findings = []
        
        # Run all 4 checks
        findings.extend(detect_sql_injection(filepath, relpath))
        findings.extend(detect_hardcoded_secrets(filepath, relpath))
        findings.extend(detect_unsafe_deserialization(filepath, relpath))
        findings.extend(detect_command_injection(filepath, relpath))
        
        all_findings.extend(findings)
        if findings:
            print(f"  [{i}/{total}] {relpath} — {len(findings)} vulnerability(ies)")
    
    print("\n" + "=" * 60)
    print("📊 AGGREGATE RESULTS")
    
    # Categorize by severity
    critical = [f for f in all_findings if f["severity"] == "CRITICAL"]
    high = [f for f in all_findings if f["severity"] == "HIGH"]
    medium = [f for f in all_findings if f["severity"] == "MEDIUM"]
    low = [f for f in all_findings if f["severity"] == "LOW"]
    
    files_with_vulns = len(set(f["file"] for f in all_findings))
    
    print(f"  Files scanned:              {total}")
    print(f"  Files with vulnerabilities: {files_with_vulns}")
    print(f"  CRITICAL (SQL/command inj): {len(critical)}")
    print(f"  HIGH (secrets/deserialize): {len(high)}")
    print(f"  MEDIUM (potential issues):  {len(medium)}")
    print(f"  LOW (suspect patterns):     {len(low)}")
    
    # Risk score (0-10)
    risk_score = min(10, (len(critical) * 3 + len(high) * 1.5 + len(medium) * 0.5))
    if risk_score > 7:
        risk_level = "HIGH"
    elif risk_score > 4:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"
    
    print(f"  Risk Score: {risk_score:.1f}/10 ({risk_level})")
    
    # Sort findings by severity
    all_findings.sort(key=lambda f: get_severity_sort_key(f["severity"]))
    
    # Print findings grouped
    if critical:
        print(f"\n{'='*60}")
        print(f"🔴 CRITICAL ({len(critical)})")
        print(f"{'='*60}")
        for f in critical:
            print(f"  🔴 {f['file']}:{f['line']} [{f['category']}]")
            print(f"     {f['snippet']}")
    
    if high:
        print(f"\n{'='*60}")
        print(f"🟠 HIGH ({len(high)})")
        print(f"{'='*60}")
        for f in high:
            print(f"  🟠 {f['file']}:{f['line']} [{f['category']}]")
            print(f"     {f['snippet']}")
    
    if medium:
        print(f"\n{'='*60}")
        print(f"🟡 MEDIUM ({len(medium)})")
        print(f"{'='*60}")
        for f in medium[:15]:
            print(f"  🟡 {f['file']}:{f['line']} [{f['category']}]")
            print(f"     {f['snippet']}")
        if len(medium) > 15:
            print(f"     ... and {len(medium) - 15} more")
    
    # Build report
    report = {
        "security_scanner_result": {
            "signal": "🟢 DONE",
            "from": "security-scanner",
            "to": "code-reviewer",
            "status": "success",
            "parsed": {
                "task": "SCAN",
                "files_scanned": total,
                "files_with_vulnerabilities": files_with_vulns,
                "summary": {
                    "CRITICAL": len(critical),
                    "HIGH": len(high),
                    "MEDIUM": len(medium),
                    "LOW": len(low)
                },
                "risk_score": round(risk_score, 1),
                "risk_level": risk_level,
                "findings": all_findings
            }
        }
    }
    
    output_path = os.path.join(WORKSPACE, "security-scan-report.json")
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✅ Report written to {output_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
