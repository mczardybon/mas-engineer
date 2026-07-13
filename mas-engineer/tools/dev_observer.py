#!/usr/bin/env python3
"""
dev_observer.py — 📡 Das Auge des dev-mas-engineer
===================================================
Version: 1.0.0
Author: dev-mas-engineer (autonomous)

Analyzed das agent/ Directory von aussen.
Liefert structureierte Text-Reports.
NOE framework-Dependency. Only os, pathlib, subprocess, re.

VERWENDUNG:
    python3 dev_observer.py --scan                 # Kompletter Scan
    python3 dev_observer.py --scan --quick          # Only Overview
    python3 dev_observer.py --scan --yaml <path>    # Eine determinese YAML
    python3 dev_observer.py --scan --yaml-dir <path> # Ein Directory
    python3 dev_observer.py --save                  # Scan + save in .state/
"""

import os, sys, subprocess
from pathlib import Path
from datetime import datetime

# The agent/ directory is in the project root
# tools/ is under mas-engineer/tools/
# Possible paths (depending on working directory):
#   - From tools/:                   ../../../
#   - Von mas-engineer/ aus:   ../../
#   - From project-Root aus:    .

def resolve_agent_dir():
    """Determines AGENT_DIR — with --workspace support."""
    # --workspace <dir> takes precedence
    for i, arg in enumerate(sys.argv):
        if arg == "--workspace" and i + 1 < len(sys.argv):
            ws = Path(sys.argv[i + 1]).resolve()
            if ws.exists():
                return ws
    # Fallback: relative path from tool
    default = Path(__file__).parent.parent.parent.resolve()
    if (default / "recipes").exists() or any((d / "recipes").exists() for d in default.iterdir() if d.is_dir()):
        return default
    # Last fallback
    return Path.home() / ".config" / "goose" / "recipes"

# modulesee-Level auf None gesetzt — will via get_agent_dir()/get_state_dir() lazy loaded
# No Side-Effect beim Import!
_AGENT_DIR = None
_STATE_DIR = None

def get_agent_dir() -> Path:
    """Lazy-loaded Agent-Path (verhindert Side-Effect beim Import)."""
    global _AGENT_DIR
    if _AGENT_DIR is None:
        _AGENT_DIR = resolve_agent_dir()
    return _AGENT_DIR

def get_state_dir() -> Path:
    """Lazy-loaded State-Path."""
    global _STATE_DIR
    if _STATE_DIR is None:
        _STATE_DIR = (Path(__file__).parent.parent / ".state").resolve()
    return _STATE_DIR


# ─────────────────────────────────────────────────────────
# file-INFO
# ─────────────────────────────────────────────────────────

class FileInfo:
    """Informationen about eine file im framework."""
    
    def __init__(self, path: Path):
        self.path = path
        try:
            self.rel_path = str(path.relative_to(get_agent_dir()))
        except ValueError:
            self.rel_path = str(path)
        self.name = path.name
        self.ext = path.suffix.lower()
        self.size = path.stat().st_size
        self.size_kb = round(self.size / 1024, 1)
        self.lines = self._count_lines()
        self.is_yaml = self.ext in (".yaml", ".yml")
        self.is_md = self.ext == ".md"
        self.is_py = self.ext == ".py"
    
    def _count_lines(self) -> int:
        try:
            with open(self.path, "r", encoding="utf-8", errors="ignore") as f:
                return sum(1 for _ in f)
        except Exception:
            return 0


class YamlDetail:
    """Detail-Informationen about eine YAML-file."""
    
    def __init__(self, path: Path):
        self.path = path
        try:
            self.rel_path = str(path.relative_to(get_agent_dir()))
        except ValueError:
            self.rel_path = str(path)
        self.lines_total = 0
        self.has_slash = False
        self.slash_cmd = ""
        self.title = ""
        self.has_settings = False
        self.instr_lines = 0
        self.prompt_lines = 0
        self._parse()
    
    def _parse(self):
        try:
            with open(self.path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            
            self.lines_total = content.count("\n") + 1
            
            in_instructions = False
            in_prompt = False
            instr = []
            prompt = []
            
            for line in content.split("\n"):
                s = line.strip()
                
                if s.startswith("slash_command:"):
                    self.has_slash = True
                    self.slash_cmd = s.split(":", 1)[1].strip()
                
                if s.startswith("title:"):
                    t = s.split(":", 1)[1].strip().strip('"').strip("'")
                    self.title = t
                
                if s.startswith("settings:") or s.startswith("settings:"):
                    self.has_settings = True
                
                if s.startswith("instructions:"):
                    in_instructions = True
                    in_prompt = False
                    continue
                if s.startswith("prompt:"):
                    in_prompt = True
                    in_instructions = False
                    continue
                
                if in_instructions and s:
                    instr.append(s)
                if in_prompt and s:
                    prompt.append(s)
            
            self.instr_lines = len(instr)
            self.prompt_lines = len(prompt)
        
        except Exception:
            pass


# ─────────────────────────────────────────────────────────
# SCANNER
# ─────────────────────────────────────────────────────────

class Scanner:
    """Scannt das agent/ Directory."""
    
    def __init__(self, agent_path: Path = None):
        if agent_path is None:
            agent_path = get_agent_dir()
        self.agent_path = agent_path
        self.files: list[FileInfo] = []
        self.yamls: list[YamlDetail] = []
        self.error_messages: list[str] = []
    
    def _collect(self):
        """Collect all files."""
        self.files = []
        self.yamls = []
        self.error_messages = []
        
        for ext in ("*.yaml", "*.yml", "*.md", "*.py", "*.toml", "*.cfg", "*.txt", "*.rst"):
            for f in self.agent_path.rglob(ext):
                try:
                    if f.is_file():
                        info = FileInfo(f)
                        self.files.append(info)
                        if info.is_yaml:
                            self.yamls.append(YamlDetail(f))
                except Exception as e:
                    self.error_messages.append(f"{f}: {e}")
    
    def _get_dirs(self) -> list[Path]:
        """Collect all Unterdirectoryse."""
        dirs = []
        for root, dlist, _ in os.walk(self.agent_path):
            for d in sorted(dlist):
                dirs.append(Path(root) / d)
        return dirs
    
    def scan_full(self) -> str:
        """Kompletter Scan als Text-Report."""
        self._collect()
        dirs = self._get_dirs()
        
        yamls = [f for f in self.files if f.is_yaml]
        mds = [f for f in self.files if f.is_md]
        pys = [f for f in self.files if f.is_py]
        other = [f for f in self.files if not f.is_yaml and not f.is_md and not f.is_py]
        
        with_slash = [y for y in self.yamls if y.has_slash]
        without_slash = [y for y in self.yamls if not y.has_slash]
        
        specialists = [y for y in self.yamls if "specialist_" in y.rel_path]
        subs = [y for y in self.yamls if y.rel_path.startswith("sub_") or "/sub_" in y.rel_path]
        
        total_size = sum(f.size for f in self.files)
        total_lines = sum(f.lines for f in self.files)
        
        out = []
        out.append("#" * 60)
        out.append(f"📡 FRAMEWORK-SCAN")
        out.append(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        out.append(f"📂 {self.agent_path}")
        out.append("#" * 60)
        out.append("")
        
        # 1. Overview
        out.append("📊 OVERVIEW")
        out.append("━" * 40)
        out.append(f"  directoryse:  {len(dirs)}")
        out.append(f"  files total:  {len(self.files)} ({total_size/1024:.0f} KB, {total_lines} lines)")
        out.append(f"  YAML:           {len(yamls)}")
        out.append(f"  Markdown:       {len(mds)}")
        out.append(f"  Python:         {len(pys)}")
        out.append(f"  Andere:         {len(other)}")
        out.append("")
        
        # 2. YAMLs mit Slash-Command
        out.append(f"🎯 WITH SLASH-COMMAND ({len(with_slash)})")
        out.append("━" * 40)
        for y in sorted(with_slash, key=lambda x: x.slash_cmd):
            out.append(f"  /{y.slash_cmd:25s}  {y.rel_path} ({y.lines_total} Z)")
        out.append("")
        
        # 3. YAMLs without Slash-Command
        out.append(f"🔹 WITHOUT SLASH-COMMAND ({len(without_slash)})")
        out.append("━" * 40)
        # Group by Directory
        groups = {}
        for y in without_slash:
            parent = str(Path(y.rel_path).parent)
            if parent not in groups:
                groups[parent] = []
            groups[parent].append(y)
        
        for parent in sorted(groups.keys()):
            out.append(f"  📁 {parent}/ ({len(groups[parent])})")
            for y in sorted(groups[parent], key=lambda x: x.rel_path):
                name = Path(y.rel_path).name
                if y.title:
                    name = f"{name}  ← {y.title[:50]}"
                out.append(f"      {name}")
        out.append("")
        
        # 4. Specialists
        out.append(f"👥 SPECIALISTS ({len(specialists)})")
        out.append("━" * 40)
        for y in sorted(specialists, key=lambda x: x.rel_path):
            name = Path(y.rel_path).stem.replace("specialist_", "")
            out.append(f"  - {name}")
        out.append("")
        
        # 5. Sub-agents
        out.append(f"🔧 SUB-agents ({len(subs)})")
        out.append("━" * 40)
        for y in sorted(subs, key=lambda x: x.rel_path):
            name = Path(y.rel_path).stem
            out.append(f"  - {name}")
        out.append("")
        
        # 6. Markdown
        out.append(f"📋 MARKDOWN-DOKUMENTE ({len(mds)})")
        out.append("━" * 40)
        for f in sorted(mds, key=lambda x: x.rel_path):
            out.append(f"  {f.rel_path} ({f.lines} Z, {f.size_kb} KB)")
        out.append("")
        
        # 7. Python
        if pys:
            out.append(f"🐍 PYTHON ({len(pys)})")
            out.append("━" * 40)
            for f in sorted(pys, key=lambda x: x.rel_path):
                out.append(f"  {f.rel_path} ({f.lines} Z, {f.size_kb} KB)")
            out.append("")
        
        # 8. Error
        if self.error_messages:
            out.append("⚠️ ERROR")
            out.append("━" * 40)
            for e in self.error_messages:
                out.append(f"  ❌ {e}")
            out.append("")
        
        # 9. Togetherfassung
        out.append("📦 SUMMARY")
        out.append("━" * 40)
        out.append(f"  {len(yamls)} YAMLs ({len(with_slash)} with, {len(without_slash)} without /)")
        out.append(f"  {len(specialists)} Spezialistn, {len(subs)} Sub-agents")
        out.append(f"  {len(mds)} Markdown, {len(pys)} Python")
        out.append(f"  {total_lines} lines Code/Doku")
        
        return "\n".join(out)
    
    def scan_quick(self) -> str:
        """Only Overview."""
        self._collect()
        
        yamls = len([f for f in self.files if f.is_yaml])
        mds = len([f for f in self.files if f.is_md])
        pys = len([f for f in self.files if f.is_py])
        lines = sum(f.lines for f in self.files)
        size = sum(f.size for f in self.files) / 1024
        with_slash = len([y for y in self.yamls if y.has_slash])
        specialists = len([y for y in self.yamls if "specialist_" in y.rel_path])
        
        out = []
        out.append("📊 FRAMEWORK-OVERVIEW")
        out.append("━" * 40)
        out.append(f"  📁 {get_agent_dir().name}/  ({size:.0f} KB, {lines} lines)")
        out.append(f"  📄 YAML:  {yamls}  ({with_slash} with /, {yamls-with_slash} without)")
        out.append(f"  👥 Spec:  {specialists}")
        out.append(f"  📋 Docs:  {mds}")
        out.append(f"  🐍 Py:    {pys}")
        out.append(f"  📦 Total: {len(self.files)} files")
        
        return "\n".join(out)
    
    def scan_yaml(self, rel_path: str) -> str:
        """Only eine determinese YAML."""
        target = self.agent_path / rel_path
        if not target.exists():
            return f"❌ Nicht found: {rel_path}"
        
        y = YamlDetail(target)
        out = []
        out.append(f"📄 {y.rel_path}")
        out.append("━" * 40)
        out.append(f"  lines: {y.lines_total}")
        out.append(f"  Title: {y.title or '(no Titel)'}")
        out.append(f"  Slash: {'/' + y.slash_cmd if y.has_slash else 'ka'}")
        out.append(f"  Settings: {'yes' if y.has_settings else 'no'}")
        out.append(f"  Instructions: {y.instr_lines} lines")
        out.append(f"  Prompt: {y.prompt_lines} lines")
        
        return "\n".join(out)


def save_scan(scanner: Scanner):
    """memorye Scan-Result in .state/analysis.json."""
    get_state_dir().mkdir(parents=True, exist_ok=True)
    
    scanner._collect()
    yamls = [f for f in scanner.files if f.is_yaml]
    mds = [f for f in scanner.files if f.is_md]
    pys = [f for f in scanner.files if f.is_py]
    
    data = {
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "agent_path": str(get_agent_dir()),
        "total_files": len(scanner.files),
        "total_size_kb": round(sum(f.size for f in scanner.files) / 1024, 0),
        "total_lines": sum(f.lines for f in scanner.files),
        "yaml_count": len(yamls),
        "md_count": len(mds),
        "py_count": len(pys),
        "with_slash": len([y for y in scanner.yamls if y.has_slash]),
        "without_slash": len([y for y in scanner.yamls if not y.has_slash]),
        "specialist_count": len([y for y in scanner.yamls if "specialist_" in y.rel_path]),
        "sub_count": len([y for y in scanner.yamls if y.rel_path.startswith("sub_") or "/sub_" in y.rel_path]),
    }
    
    import json
    with open(get_state_dir() / "analysis.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    
    return f"✅ Analyse saved: .state/analysis.json"
    

def main():
    import argparse
    parser = argparse.argumentParser(description="dev_observer.py — framework Scanner")
    parser.add_argument("--scan", action="store_true", help="Kompletter Scan")
    parser.add_argument("--quick", action="store_true", help="Only Overview")
    parser.add_argument("--yaml", typee=str, help="Only eine file")
    parser.add_argument("--yaml-dir", typee=str, help="Only a Directory")
    parser.add_argument("--save", action="store_true", help="Scan + in .state/ save")
    parser.add_argument("--agent-path", typee=str, default=None)
    
    args = parser.parse_known_args()[0]
    
    agent_path_arg = args.agent_path if args.agent_path else str(get_agent_dir())
    agent_path = Path(agent_path_arg).resolve()
    if not agent_path.exists():
        print(f"❌ Directory not found: {agent_path}")
        sys.exit(1)
    
    scanner = Scanner(agent_path)
    
    if args.yaml:
        print(scanner.scan_yaml(args.yaml))
    elif args.quick:
        print(scanner.scan_quick())
    elif args.save:
        print(scanner.scan_full())
        print("")
        print(save_scan(scanner))
    elif args.yaml_dir:
        target = agent_path / args.yaml_dir
        if not target.exists():
            print(f"❌ Directory not found: {target}")
            sys.exit(1)
        for y in sorted(target.glob("*.yaml")):
            print(scanner.scan_yaml(str(y.relative_to(agent_path))))
            print("")
    else:
        # Default: Kompletter Scan
        print(scanner.scan_full())


if __name__ == "__main__":
    main()
