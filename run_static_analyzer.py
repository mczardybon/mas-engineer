#!/usr/bin/env python3
"""
MAS Static Analyzer (v1.0.0) — Syntax, Lint, Types
Reads instructions from recipe/instructions/static-analyzer.md
"""
import ast
import json
import os
import subprocess
import sys
from pathlib import Path

WORKSPACE = "/workspace/mas-engineer-src"
MAX_FILES = 50
EXCLUDE_DIRS = ["venv", ".venv", "__pycache__", "node_modules", ".git"]

def discover_python_files(target):
    """Step 1: Discover Python files."""
    files = []
    for root, dirs, fnames in os.walk(target):
        # Filter excluded dirs in-place
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".")]
        for fname in fnames:
            if fname.endswith(".py"):
                files.append(os.path.join(root, fname))
    return files[:MAX_FILES]

def check_syntax(filepath):
    """Step 2a — Syntax Check via ast.parse."""
    try:
        with open(filepath) as f:
            ast.parse(f.read())
        return {"syntax": "valid"}
    except SyntaxError as e:
        return {
            "syntax": "invalid",
            "line": e.lineno,
            "offset": e.offset,
            "msg": f"SyntaxError: {e.msg}"
        }
    except Exception as e:
        return {"syntax": "error", "msg": str(e)}

def check_lint_simple(filepath):
    """Step 2b — Simplified lint via AST (pyflakes fallback)."""
    issues = []
    try:
        with open(filepath) as f:
            source = f.read()
        tree = ast.parse(source)
    except (SyntaxError, Exception):
        return issues

    # Track imports and usage
    imports = {}  # name -> (line, alias, fullname)
    used_names = set()
    
    for node in ast.walk(tree):
        # Collect imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name.split(".")[0]
                imports[name] = (node.lineno, alias.asname, alias.name)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                imports[name] = (node.lineno, alias.asname, f"{node.module}.{alias.name}" if node.module else alias.name)
        # Track name usage
        elif isinstance(node, ast.Name):
            used_names.add(node.id)
        elif isinstance(node, ast.Attribute):
            used_names.add(node.attr)

    # Check unused imports (in function scope too — simplified)
    for name, (line, asname, fullname) in imports.items():
        # Skip __future__ imports
        if fullname.startswith("__future__"):
            continue
        if name not in used_names and not any(name == n.split(".")[0] for n in used_names):
            issues.append({
                "type": "lint",
                "line": line,
                "msg": f"'{fullname}' imported but unused"
            })

    return issues

def check_type_hints(filepath):
    """Step 2c — Type hint check."""
    funcs = []
    try:
        with open(filepath) as f:
            source = f.read()
        tree = ast.parse(source)
    except (SyntaxError, Exception):
        return funcs

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            has_return = node.returns is not None
            typed_args = sum(1 for a in node.args.args if a.annotation)
            total_args = len(node.args.args)
            # Skip special methods like __init__
            if node.name.startswith("__") and node.name.endswith("__"):
                continue
            if not has_return or typed_args < total_args:
                funcs.append({
                    "name": node.name,
                    "line": node.lineno,
                    "has_return_type": has_return,
                    "typed_args": typed_args,
                    "total_args": total_args
                })

    return funcs

def analyze_file(filepath):
    """Run all 3 checks on a single file."""
    relpath = os.path.relpath(filepath, WORKSPACE)
    findings = []
    
    # 2a — Syntax
    syntax = check_syntax(filepath)
    if syntax["syntax"] == "invalid":
        findings.append({
            "file": relpath,
            "severity": "ERROR",
            "line": syntax["line"],
            "check": "syntax",
            "message": syntax["msg"]
        })
    
    # 2b — Lint (skip if syntax errors)
    if syntax["syntax"] == "valid":
        lint_issues = check_lint_simple(filepath)
        for issue in lint_issues:
            findings.append({
                "file": relpath,
                "severity": "WARNING",
                "line": issue["line"],
                "check": "lint",
                "message": issue["msg"]
            })
    
    # 2c — Type hints (skip if syntax errors)
    if syntax["syntax"] == "valid":
        type_issues = check_type_hints(filepath)
        for func in type_issues:
            if not func["has_return_type"]:
                findings.append({
                    "file": relpath,
                    "severity": "INFO",
                    "line": func["line"],
                    "check": "type_hint",
                    "message": f"Function '{func['name']}' missing return type annotation"
                })
            if func["typed_args"] < func["total_args"]:
                untyped = func["total_args"] - func["typed_args"]
                findings.append({
                    "file": relpath,
                    "severity": "INFO",
                    "line": func["line"],
                    "check": "type_hint",
                    "message": f"Function '{func['name']}' has {untyped} argument(s) without type hints"
                })
    
    return findings

def main():
    target = WORKSPACE
    files = discover_python_files(target)
    total = len(files)
    
    print(f"🔍 Static Analyzer (v1.0.0)")
    print(f"Scanning {total} Python files in {target}")
    print("=" * 60)
    
    all_findings = []
    files_with_issues = 0
    
    for i, filepath in enumerate(files, 1):
        relpath = os.path.relpath(filepath, WORKSPACE)
        findings = analyze_file(filepath)
        if findings:
            files_with_issues += 1
        all_findings.extend(findings)
        print(f"  [{i}/{total}] {relpath} — {len(findings)} issue(s)")
    
    # Step 3 — Aggregate
    errors = [f for f in all_findings if f["severity"] == "ERROR"]
    warnings = [f for f in all_findings if f["severity"] == "WARNING"]
    infos = [f for f in all_findings if f["severity"] == "INFO"]
    
    # Missing types summary
    funcs_no_return = set()
    funcs_partial = set()
    type_findings = [f for f in all_findings if f["check"] == "type_hint"]
    for f in type_findings:
        if "missing return type" in f["message"]:
            funcs_no_return.add(f["message"].split("'")[1])
        if "without type hints" in f["message"]:
            funcs_partial.add(f["message"].split("'")[1])
    
    print("\n" + "=" * 60)
    print("📊 AGGREGATE RESULTS")
    print(f"  Files scanned:       {total}")
    print(f"  Files with issues:   {files_with_issues}")
    print(f"  Errors (syntax):     {len(errors)}")
    print(f"  Warnings (lint):     {len(warnings)}")
    print(f"  Info (type hints):   {len(infos)}")
    print(f"  Funcs no return type: {len(funcs_no_return)}")
    print(f"  Funcs partial types:  {len(funcs_partial)}")
    
    # Step 4 — Structured Report
    report = {
        "static_analyzer_result": {
            "signal": "🟢 DONE",
            "from": "static-analyzer",
            "to": "code-reviewer",
            "status": "success",
            "parsed": {
                "task": "ANALYZE",
                "files_scanned": total,
                "files_with_issues": files_with_issues,
                "summary": {
                    "errors": len(errors),
                    "warnings": len(warnings),
                    "info": len(infos)
                },
                "findings": all_findings,
                "missing_types_summary": {
                    "functions_without_return_type": len(funcs_no_return),
                    "functions_with_partial_types": len(funcs_partial)
                }
            }
        }
    }
    
    output_path = os.path.join(WORKSPACE, "static-analysis-report.json")
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✅ Report written to {output_path}")
    
    # Print findings grouped by severity
    if errors:
        print(f"\n{'='*60}")
        print(f"🔴 ERRORS ({len(errors)})")
        print(f"{'='*60}")
        for e in errors:
            print(f"  ⛔ {e['file']}:{e['line']} — {e['message']}")
    
    if warnings:
        print(f"\n{'='*60}")
        print(f"🟡 WARNINGS ({len(warnings)})")
        print(f"{'='*60}")
        for w in warnings[:20]:
            print(f"  ⚠️  {w['file']}:{w['line']} — {w['message']}")
        if len(warnings) > 20:
            print(f"  ... and {len(warnings) - 20} more")
    
    if infos:
        print(f"\n{'='*60}")
        print(f"ℹ️  INFO — Type Hints ({len(infos)})")
        print(f"{'='*60}")
        for info in infos[:15]:
            print(f"  📝 {info['file']}:{info['line']} — {info['message']}")
        if len(infos) > 15:
            print(f"  ... and {len(infos) - 15} more")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
