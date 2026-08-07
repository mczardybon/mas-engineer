#!/usr/bin/env python3
"""
dev_rule_checker.py — Method 9: Deterministic rule test
Called BEFORE every write/edit/shell action.
Blocks actions that violate hard rules.
"""

import sys
import os
import json
import yaml
import subprocess
import time

BASE_DIR = os.path.abspath(".")
MAS_DIR = os.path.join(BASE_DIR, "mas-engineer") if os.path.isdir(os.path.join(BASE_DIR, "mas-engineer")) else BASE_DIR
# MAS-Rulen liegen in mas-engineer/.mase/rules/ (not in .mase/rules/)

# --mode generic: User-Projekt (rules.yaml)
# --mode mas (default): MAS-eigene Rulen (rules_5_extreme.yaml + hard_rules.yaml)
REGEL_DATEI = os.path.join(MAS_DIR, ".mase/rules/rules_5_extreme.yaml")
REGEL_4_DATEI = os.path.join(MAS_DIR, ".mase/rules/rules_4_strong.yaml")
REGEL_GENERIC_DATEI = os.path.join(BASE_DIR, ".mase/rules/rules.yaml")
HARTE_REGEL_DATEI = os.path.join(MAS_DIR, ".mase/rules/hard_rules.yaml")
MODE_DATEI = os.path.join(BASE_DIR, ".mas-mode")
WORKFLOWS_DATEI = os.path.join(MAS_DIR, ".mase/workflows.yaml")
CONFIRMATION_DATEI = os.path.join(MAS_DIR, ".mase/.last_confirmation")

def load_rules(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get("rules", [])

def get_rules(mode=None):
    """Load rules based on mode. --mode generic = rules.yaml, mas = hard_rules.yaml + workflows.yaml"""
    m = mode or "mas"
    if m == "generic":
        if os.path.exists(REGEL_GENERIC_DATEI):
            with open(REGEL_GENERIC_DATEI) as f:
                data = yaml.safe_load(f)
            return data.get("rules", data.get("rules", []))
        return []
    else:
        # Load from old files + workflows.yaml
        rules = load_rules(REGEL_DATEI) + load_rules(REGEL_4_DATEI) + load_rules(HARTE_REGEL_DATEI)
        # Load additionally aus workflows.yaml (R12-R18)
        WORKFLOWS_DATEI
        if os.path.exists(WORKFLOWS_DATEI):
            with open(WORKFLOWS_DATEI) as f:
                wf = yaml.safe_load(f)
            restrictions = wf.get("configs", {}).get("mas-self", {}).get("restrictions", {})
            for key, val in restrictions.items():
                if key.startswith("r") and isinstance(val, dict):
                    # Normierte ID: R19 aus r19_path_hierarchie, R01 aus r01_confirmation usw.
                    norm_id = key.split("_")[0].upper()
                    rules.append({
                        "id": norm_id,
                        "name": val.get("description", val.get("type", key)),
                        "hardness": 5 if val.get("level") == "extreme" else (4 if val.get("level") == "strong" else 3)
                    })
        return rules

def check_mode():
    if not os.path.exists(MODE_DATEI):
        return "unbekannt"
    with open(MODE_DATEI) as f:
        return f.read().strip()

def check_confirmation():
    """Checks if user confirmation exists within the last 5 minutes"""
    if not os.path.exists(CONFIRMATION_DATEI):
        return False
    with open(CONFIRMATION_DATEI) as f:
        ts = int(f.read().strip())
    return int(time.time()) - ts < 300

def check_rule(rule_id, action=""):
    rules = load_rules(REGEL_DATEI) + load_rules(REGEL_4_DATEI) + load_rules(HARTE_REGEL_DATEI)
    # Load auch aus workflows.yaml (R12-R19)
    import os as _wf_os
    if _wf_os.path.exists(WORKFLOWS_DATEI):
        try:
            with open(WORKFLOWS_DATEI) as f:
                wf = yaml.safe_load(f)
            restrictions = wf.get("configs", {}).get("mas-self", {}).get("restrictions", {})
            for key, val in restrictions.items():
                if key.startswith("r") and isinstance(val, dict):
                    norm_id = key.split("_")[0].upper()
                    rules.append({
                        "id": norm_id,
                        "name": val.get("description", key),
                        "hardness": 5 if val.get("level") == "extreme" else (4 if val.get("level") == "strong" else 3)
                    })
        except:
            pass
    for rule in rules:
        if rule["id"] != rule_id:
            continue
        
        if rule_id == "R01":
            has = check_confirmation()
            if not has:
                return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                        "detail": "No confirmation in the last 5 minutes", "action": "BLOCKED"}
        
        if rule_id == "R09":
            """MODE-DOMAIN-COUPLING: Mode determines the allowed domain.
            
            Checken:
            1. Logischer Import (from/import andere Domain) -> BLOCKED
            2. Mode conflict (Target-Domain != .mas-mode) -> BLOCKED  
            3. Domain-Konflikt (Target-Domaene != .active_domain) -> BLOCKED
               Exception: Readder Access (read/cat/ls) in andere Domain = OK
               Exception: framework analyzen from MAS aus = OK (only read)
            """
            import os as _os9, yaml as _yaml9
            
            # Read Configuration
            base = _os9.path.dirname(_os9.path.dirname(_os9.path.abspath(__file__)))
            reg_path = _os9.path.join(base, ".mase/domains/registry.yaml")
            mode_file = _os9.path.expanduser("~/.config/goose/.mas-mode")
            domain_file = _os9.path.expanduser("~/.config/goose/.active_domain")
            
            # Read registry
            domains = {}
            if _os9.path.exists(reg_path):
                with open(reg_path) as f:
                    reg = _yaml9.safe_load(f) or {}
                domains = reg.get("domains", {})
            
            # Read current mode
            mode = check_mode() if _os9.path.exists(MODE_DATEI) else "unbekannt"
            
            # Read active_domain
            active_domain = None
            if _os9.path.exists(domain_file):
                with open(domain_file) as f:
                    active_domain = f.read().strip()
            
            akt = action.lower()
            
            # PRUEFUNG 1: Logische Imports (import/from andere Domain)
            for dname, dconf in domains.items():
                if dname == active_domain:
                    continue
                dp = dconf["path"].rstrip("/").lower() if "path" in dconf else dname.lower()
                if f"import {dname}" in akt or f"from {dname}" in akt:
                    return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                            "detail": f"{active_domain} imports {dname} — Logical import FORBIDDEN!", "action": "BLOCKED"}
                if f"import {dp}" in akt or f"from {dp}" in akt:
                    return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                            "detail": f"{active_domain} importiert {dname} ({dp}) — Logischer Import FORBIDDEN!", "action": "BLOCKED"}
            
            # CHECK 2: Mode conflict (only for write/edit/shell)
            is_write = any(x in akt for x in ["write ", "edit ", "delete ", "mv ", "cp ", "rm ", ">", "sed "])
            if is_write and active_domain and domains:
                target_domain = None
                for dname, dconf in domains.items():
                    dp = dconf["path"].rstrip("/").lower() if "path" in dconf else dname.lower()
                    if dp in akt:
                        target_domain = dname
                        break
                
                if target_domain and target_domain != active_domain:
                    # Mode check: May active_domain write in target_domain?
                    target_mode = domains.get(target_domain, {}).get("mode", None)
                    if target_mode and mode != target_mode:
                        return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                                "detail": f"{active_domain} writes to {target_domain} (mode={target_mode}) with own mode={mode} — MODE CONFLICT!", "action": "BLOCKED"}
                    
                    # Domain-Check: Schreibzugriff auf fremde Domain
                    return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                            "detail": f"{active_domain} writes to {target_domain} — DOMAIN CONFLICT! Only read access allowed.", "action": "BLOCKED"}
            
            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"], "action": "OK"}

        if rule_id == "R02":
            """INVENTORY_CHECK: Checks if file exists + special_agents registry"""
            import os as _os, yaml as _yaml
            
            akt = action.lower()
            path = None
            for prefix in ["write ", "edit ", "cp ", "mv "]:
                if prefix in akt:
                    path = akt.split(prefix)[-1].split()[0].strip()
                    break
            
            if path and not path.startswith("/"):
                cwd = _os.getcwd()
                full_path = _os.path.join(cwd, path) if not _os.path.isabs(path) else path
                
                special_path = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), ".mase/agents/special_agents.yaml")
                if _os.path.exists(special_path):
                    with open(special_path) as _f:
                        special = _yaml.safe_load(_f)
                    if special and "agents" in special:
                        fname = _os.path.basename(path)
                        base_name = fname.replace(".yaml", "")
                        if base_name in special["agents"]:
                            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"],
                                    "detail": f"Special agent: {base_name} (special_agents.yaml)", "action": "OK"}
                
                if _os.path.exists(full_path) and "force" not in akt and "--force" not in akt:
                    return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                            "detail": f"Target exists already: {path}", "action": "BLOCKED"}
            
            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"], "action": "OK"}
        
        if rule_id == "R05":
            """AUTO_COMMIT: 1. Checkpoint BEFORE change → 2. Change → 3. commit"""
            akt = action.lower()
            is_modify = any(x in akt for x in ["write ", "edit ", "mv ", "cp ", "delete ", "rm "])
            
            if is_modify:
                # Check order: Checkpoint MUST come before change
                has_checkpoint = "checkpoint" in akt
                has_change = any(x in akt for x in ["edit ", "write ", "mv ", "cp "])
                has_commit = "git commit" in akt or "git add" in akt
                
                # Check ob ORDER eingehalten will
                if "checkpoint" in akt:
                    # Checkpoint VOR Change ist OK
                    return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"],
                            "detail": "Checkpoint BEFORE change — correct order", "action": "OK"}
                
                if has_change and not has_checkpoint and not has_commit:
                    return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                            "detail": "Change WITHOUT prior checkpoint! Order: 1. Checkpoint → 2. Change → 3. commit", "action": "BLOCKED"}
                
                if has_change and not has_checkpoint and has_commit and "git commit" in akt:
                    return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                            "detail": "commit WITHOUT prior checkpoint! ORDER VIOLATED — rollback recommended", "action": "BLOCKED"}
            
            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"], "action": "OK"}
        
        if rule_id == "R06":
            """SUB_AGENT_CONTAINMENT: Sub-Agent = NUR Analyse, Shell selbst ausexecuten"""
            akt = action.lower()
            
            # Check ob delegate() eine shell-action contains
            if "delegate" in akt and ("write" in akt or "edit" in akt or "rm " in akt or "mv " in akt):
                return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                        "detail": "Sub-agent delegated write/edit — Sub-agent ONLY for analysis, execute shell yourself!", "action": "BLOCKED"}
            
            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"], "action": "OK"}
        
        if rule_id == "R07":
            """SIGNAL_CP_DONE: CP_DONE signal required after checkpoint"""
            akt = action.lower()
            
            if "checkpoint" in akt and "cp_done" not in akt and "CP_DONE" not in akt:
                return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                        "detail": "Checkpoint without CP_DONE signal — CP_DONE must be sent after checkpoint!", "action": "WARNING"}
            
            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"], "action": "OK"}
        
        if rule_id == "R08":
            """TOKEN_BUDGET: General improver max 50K tokens"""
            akt = action.lower()
            
            if "general-improver" in akt or "general_improver" in akt or "si-run" in akt:
                extrahiere_token = False
                # Einfache Token-Schaetzung: Number Woerter * 1.3
                token_est = len(akt.split()) * 1.3
                
                if token_est > 50000:
                    return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                            "detail": f"Token budget exceeded (approx. {token_est:.0f} > 50000) — Ask user if continuation is allowed", "action": "BLOCKED"}
            
            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"], "action": "OK"}
        
        
        if rule_id == "R04":
            if "general-improver" in action.lower() and ("edit" in action.lower() or "write" in action.lower()):
                return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                        "detail": "general-improver.yaml may not be edited", "action": "BLOCKED"}
        
        if rule_id == "R110-31":
            """DOMAIN-SCOPED sub-agent registration (R110-31, R110-30 correction)
            Three domains, coupled to .mas-mode work_on (R14):
              work_on=mas      → DOMAIN 1: mas-self sub-agents, MUST be in
                                 workflows.yaml.configs.mas-self.sub_agents
              work_on=framework → DOMAIN 2: mas-generated team (orchestrator + sub-agents
                                  in same dir), NO mas-self registration required.
                                  Orchestrator's instructions.md is the registry.
              work_on=generic  → DOMAIN 3: project in framework/generic mode.
                                  mas-engineer workflows.yaml NOT involved.

            Detection priority:
              1. Read .mas-mode file (authoritative — set by R14 work_on)
              2. If .mas-mode missing, fall back to action string heuristics
            """
            akt = action.lower()
            if not any(x in akt for x in ["write", "edit", "create", "add"]):
                return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"],
                        "detail": "No write/edit action — R110-31 not applicable",
                        "action": "OK"}

            # PRIORITY 1: read .mas-mode (authoritative per R14)
            work_on = None
            mas_mode_paths = [
                os.path.join(BASE_DIR, "mas-engineer/.mas-mode"),
                os.path.join(BASE_DIR, ".mas-mode"),
                os.path.expanduser("~/.config/goose/.mas-mode"),
            ]
            for p in mas_mode_paths:
                if os.path.exists(p):
                    try:
                        work_on = open(p).read().strip().lower()
                    except Exception:
                        pass
                    break

            domain = None
            domain_source = None
            if work_on == "mas":
                domain = 1; domain_source = f".mas-mode={work_on}"
            elif work_on == "framework":
                domain = 2; domain_source = f".mas-mode={work_on}"
            elif work_on == "generic":
                domain = 3; domain_source = f".mas-mode={work_on}"

            # PRIORITY 2: action string heuristics (only if .mas-mode missing/unknown)
            if domain is None:
                is_domain_2 = any(x in akt for x in ["demo-team", "demo_team", "generated team",
                                                      "on-demand team", "user-generated team",
                                                      "orchestrator"])
                is_domain_3 = any(x in akt for x in ["project workflows.yaml", "framework mode",
                                                      "generic mode", "project sub-agent",
                                                      "project workspace"])
                is_domain_1 = ("sub_mas-" in akt or "recipe/sub/" in akt or
                               "mas-self" in akt or "mas_self" in akt)
                if is_domain_2: domain = 2
                elif is_domain_3: domain = 3
                elif is_domain_1: domain = 1
                domain_source = "string-heuristic (no .mas-mode found)"

            # If still unknown → OK with note
            if domain is None:
                return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"],
                        "detail": "Domain not determined (no .mas-mode, no clear signal). "
                                  "Use LLM judgment. See R110-31 prompt_text for the "
                                  "3-domain table keyed to .mas-mode (R14).",
                        "action": "OK"}

            # DOMAIN 2 / 3: NO mas-self registration required
            if domain == 2:
                return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"],
                        "detail": f"DOMAIN 2 ({domain_source}) — mas-generated team. "
                                  f"NO mas-self registration required. Orchestrator's "
                                  f"instructions.md is the registry.",
                        "action": "OK"}
            if domain == 3:
                return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"],
                        "detail": f"DOMAIN 3 ({domain_source}) — project in framework/generic "
                                  f"mode. mas-engineer workflows.yaml NOT involved. "
                                  f"Project owns its own workflow.",
                        "action": "OK"}

            # DOMAIN 1: check registration
            wf_path = os.path.join(MAS_DIR, ".mase/workflows.yaml")
            if not os.path.exists(wf_path):
                return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"],
                        "detail": f"DOMAIN 1 ({domain_source}) but workflows.yaml missing — "
                                  f"cannot verify registration (fresh clone?)",
                        "action": "OK"}

            with open(wf_path) as f:
                wf = yaml.safe_load(f)
            sub_agents = wf.get("configs", {}).get("mas-self", {}).get("sub_agents", {})
            all_registered = set()
            for cat, agents in sub_agents.items():
                if isinstance(agents, list):
                    all_registered.update(agents)

            import re
            mentioned_agents = re.findall(r"sub_mas-[a-z0-9-]+", akt)
            if not mentioned_agents:
                return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"],
                        "detail": f"DOMAIN 1 ({domain_source}) but no sub_mas-* name in action "
                                  f"— cannot verify. Use R10 for yaml validation.",
                        "action": "OK"}

            unregistered = [a for a in mentioned_agents if a not in all_registered]
            if unregistered:
                return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                        "detail": f"DOMAIN 1 ({domain_source}) sub-agents NOT registered: "
                                  f"{unregistered}. R18 cannot dispatch unregistered agents "
                                  f"(R110-29 lesson). Either add to workflows.yaml under a "
                                  f"fitting category, OR check .mas-mode — if work_on != "
                                  f"'mas' (it's currently {work_on}), set it correctly.",
                        "action": "BLOCKED"}
            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"],
                    "detail": f"DOMAIN 1 ({domain_source}) all sub-agents registered: "
                              f"{mentioned_agents}",
                    "action": "OK"}

        if rule_id == "R10":
            """CORONASHIELD (R110-30 extended): Every YAML must be validated before saving.

            R110-30 EXTENSION:
            - R10 NOW applies to ALL yaml save paths, not just mas-workflow.
              Originally only yaml-editor R18 + dev_editor.py enforced R10.
              Standalone recipe-pack testscripts did not invoke yaml-editor →
              BUG-1 (sub_recipe path resolution failure) went undetected.
            - R10 now also recognizes dev_yaml_immune.py (universal standalone
              wrapper) and sub_mas-yaml-immune (delegation-friendly sub-agent).
            - Graceful degradation: if dev_yaml_immune.py is missing, R10 returns
              WARNING (not BLOCKED) so mas remains runnable on fresh clones.
            - --action write/edit (CLI action-type flag) also triggers R10, not
              just string match on "write "/"edit " in the action description.
            """
            import os as _os
            import subprocess as _sp_r10
            akt = action.lower()

            # R110-30: detect action-type flag (--action-type write|edit|shell)
            # Caller passes action like "write|edit: path/to/file.yaml"
            action_type_yaml = any(x in akt for x in ["action-type write", "action-type edit", "action_type write", "action_type edit"])

            # Only bei write/edit von .yaml/.yml files check
            is_yaml_write = any(x in akt for x in [".yaml", ".yml"]) and ("write " in akt or "edit " in akt)
            is_yaml_write = is_yaml_write or action_type_yaml

            if is_yaml_write:
                # Check ob immune-check im Command ist
                # R110-30: extended trigger keywords
                has_immune = any(kw in akt for kw in [
                    "immune",           # sub_mas-yaml-immune, dev_yaml_immune
                    "CHECK_YAML",       # sub_mas-recovery-immune CHECK_YAML
                    "corona",           # R10 CORONASHIELD
                    "yaml_immune",      # explicit tool call
                    "dev_yaml_immune",  # standalone tool
                    "yaml.safe_load",   # inline python yaml validation
                ])
                if not has_immune:
                    return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                            "detail": "YAML edit without CORONASHIELD check — invoke sub_mas-yaml-immune or dev_yaml_immune.py first! R110-30: R10 now applies to ALL yaml save paths.", "action": "BLOCKED"}

                # R110-30: if dev_yaml_immune.py was called but failed, surface the error
                # Otherwise graceful: if tool missing, WARN (not BLOCK) so mas remains runnable
                immune_tool = _os.path.join(MAS_DIR if 'MAS_DIR' in dir() else BASE_DIR, "tools/dev_yaml_immune.py")
                if not _os.path.exists(immune_tool):
                    # Tool missing → graceful: WARN, not BLOCK
                    return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"],
                            "detail": "R10 yaml-immune check present in action string, but tools/dev_yaml_immune.py not found. mas continues in graceful-degradation mode (R10 falls back to check:null).", "action": "WARNING"}
            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"], "action": "OK"}

        if rule_id == "R55":
            """IM_TOP_N_ENFORCEMENT (R57 user-request 2026-07-25, R58 multiplier fix):

            Code-enforced top-N selection + end-of-run target check.

            Modes:
            1. WRITE ranked_findings.yaml / apply patches: top_N.length must equal IM_TOP_N
            2. WRITE signal_*_done.yaml (end-of-run): session counter must be >= target
               where target = IM_TOP_N * IM_TOP_N_MULTIPLIER (default 5*3=15)

            R58 rationale: mas generates 0-9 patches/run realistically, but R57's hard
            100-patch target was impossible. Multiplier makes target realistic:
            IM_TOP_N=5 * 3 = 15 patches/run. Run #1: 5 patches, #2: 10, #3: 15 (target met)."""
            import os as _os
            akt = action.lower()
            # Read IM_TOP_N + MULTIPLIER
            try:
                N = int(_os.environ.get('IM_TOP_N', '5'))
            except ValueError:
                N = 5
            if N < 1: N = 5
            if N > 500: N = 500
            try:
                M = int(_os.environ.get('IM_TOP_N_MULTIPLIER', '3'))
            except ValueError:
                M = 3
            if M < 1: M = 1
            if M > 100: M = 100
            target = N * M
            # Mode 1: WRITE ranked_findings / APPLY patches — enforce top_N == IM_TOP_N
            is_rank_write = "ranked_findings" in akt and "write" in akt
            is_patch_apply = "apply patches" in akt or "patches_applied" in akt
            if is_rank_write or is_patch_apply:
                import re
                m = re.search(r'top_n[:\s]+(\d+)|patches_applied[:\s]+(\d+)|top[_\s]?N[:\s]+(\d+)', akt, re.IGNORECASE)
                if m:
                    found_str = m.group(1) or m.group(2) or m.group(3)
                    if found_str:
                        found = int(found_str)
                        if found < N:
                            return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                                    "detail": f"top_N={found} < IM_TOP_N={N} (env var). R55 enforces >= {N} patches in selection.",
                                    "action": "BLOCKED"}
            # Mode 2: WRITE signal_*_done.yaml — enforce counter >= target
            is_signal_done = any(s in akt for s in ["signal_apply_only_done", "signal_general_improver_done",
                                                     "signal_full_improvement_done", "signal_"]) and "done" in akt
            if is_signal_done:
                # Read session counter
                import yaml as _yaml
                MAS_ROOT = "/workspace/mas-engineer-src/mas-engineer"
                counter_path = f"{MAS_ROOT}/.mase/pipeline/r55_session_count.yaml"
                session_count = 0
                if _os.path.exists(counter_path):
                    try:
                        cd = _yaml.safe_load(open(counter_path)) or {}
                        session_count = int(cd.get("data", {}).get("applied_count", 0))
                    except Exception:
                        session_count = 0
                if session_count < target:
                    return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                            "detail": f"R55: session {session_count}/{target} patches applied (IM_TOP_N={N} × {M}). {target - session_count} more patches needed before 'done' can be signaled.",
                            "action": "BLOCKED"}
            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"], "action": "OK"}

        if rule_id == "R56":
            """EDIT_SPIN-LOOP (R91 2026-07-25, patched 2026-07-25):

            Detects placeholder-edit patterns that indicate an LLM spin-loop.

            Scope: ONLY applies to 'edit' actions. Write/shell/delegate are exempt.
            The "3+ failures in 60s" BLOCK only blocks subsequent EDITS, not other actions.

            Triggers:
            1. action string contains 'before:' followed by placeholder patterns
               (NONEXISTENT_TEXT, XYZ, PLACEHOLDER, TODO_FILL, BLOCKED, MARKER, KEEP, dummy)
               AND contains 'after:' with the same placeholder (no-op edit)
            2. consecutive edit failures in current session (tracked in .mase/pipeline/r56_edit_history.yaml)
               if 3+ failures in last 60s, BLOCK subsequent edits

            The spin-loop pattern observed in R90 (subagent-184):
              22+ edits with `before: NONEXISTENT_TEXT_XYZ` `after: NONEXISTENT_TEXT_XYZ`
              on already-existing files. Each edit returns "no match", LLM retries with
              different placeholder string. Result: 0 progress, 6 min wasted, $0.04 cost.

            Per R57 user-correction: erzwungene Regeln funktionieren, instruction-edits nicht.
            This is a HARD RULE (block: true, hardness: 5).
            """
            import os as _os56, re as _re56, time as _t56
            akt = action.lower()

            # State file for tracking consecutive edit failures
            MAS_ROOT = "/workspace/mas-engineer-src/mas-engineer"
            history_path = f"{MAS_ROOT}/.mase/pipeline/r56_edit_history.yaml"

            # Load history
            history = []
            if _os56.path.exists(history_path):
                try:
                    import yaml as _y56
                    hd = _y56.safe_load(open(history_path)) or {}
                    history = hd.get("edits", [])
                except:
                    history = []

            # Clean old entries (>120s)
            now = _t56.time()
            history = [e for e in history if now - e.get("ts", 0) < 120]

            # SCOPE CHECK: only block edit-actions
            is_edit_action = akt.startswith("edit ") or "edit " in akt.split("\n")[0]

            # Check 1: placeholder pattern in current action
            placeholder_patterns = [
                r"before:\s*(?:NONEXISTENT_TEXT|TODO_FILL|BLOCKED|PLACEHOLDER|MARKER|DUMMY|XYZ|REPLACE_ME|FIXME_FILL)",
                r"before:\s*[A-Z_]+(?:_XYZ|_PLACEHOLDER|_FILL|_DUMMY|_MARKER|_KEEP|_TBD)",
            ]
            has_placeholder = any(_re56.search(p, action, _re56.IGNORECASE) for p in placeholder_patterns)

            # Check 2: no-op edit (before == after, both placeholders)
            no_op = False
            m_before = _re56.search(r"before:\s*([^\n]+)", action)
            m_after = _re56.search(r"after:\s*([^\n]+)", action)
            if m_before and m_after:
                if m_before.group(1).strip() == m_after.group(1).strip():
                    no_op = True

            # Log this attempt
            history.append({
                "ts": now,
                "has_placeholder": has_placeholder,
                "no_op": no_op,
                "is_edit": is_edit_action,
                "action_preview": action[:200],
            })

            # Count recent placeholder/no-op EDITS in last 60s
            recent_failures = sum(1 for e in history
                                  if now - e["ts"] < 60
                                  and e.get("is_edit", False)
                                  and (e["has_placeholder"] or e["no_op"]))

            # Save history
            try:
                import yaml as _y56s
                with open(history_path, "w") as f:
                    _y56s.safe_dump({"edits": history, "last_check": now, "recent_failures_60s": recent_failures}, f)
            except:
                pass

            # NON-EDIT actions (write/shell/delegate): just log, never block
            if not is_edit_action:
                return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"], "action": "OK"}

            # BLOCK on current placeholder attempt (edit-only)
            if has_placeholder:
                return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                        "detail": f"EDIT-SPIN-LOOP: 'before' contains placeholder pattern (NONEXISTENT_TEXT, XYZ, PLACEHOLDER etc.). READ THE FILE FIRST, then use the EXACT existing text as 'before'. R90-Root-Cause 2026-07-25.",
                        "action": "BLOCKED"}

            if no_op:
                return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                        "detail": f"EDIT-SPIN-LOOP: no-op edit (before == after). Edit tool is for changing text. Use 'write' to overwrite a file.",
                        "action": "BLOCKED"}

            # BLOCK on accumulated spin-loop pattern (edit-only)
            if recent_failures >= 3:
                return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                        "detail": f"EDIT-SPIN-LOOP: {recent_failures} placeholder/no-op edits in last 60s. STOP editing. Use 'write' for new content, or 'load' + exact text match for edits.",
                        "action": "BLOCKED"}

            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"], "action": "OK"}


        if rule_id == "R12":
            """WORK_MAS_DECOUPLING: MAS lebt in ~/.config/goose/.state/mas/"""
            akt = action.lower()
            if any(x in akt for x in [".mase/", "checkpoints/", ".backups/"]) and "checkpoint" not in akt:
                return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                        "detail": "MAS state in work/ detected! State belongs in ~/.config/goose/.state/mas/", "action": "WARNING"}
            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"], "action": "OK"}
        
        if rule_id == "R13":
            """NEW_PROJECT_IGNORE: Bei emptym Directory MAS-Config ignorieren"""
            # Will in prompt_1 checked — hier only Enforcement-Check
            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"],
                    "detail": "R13 is checked in prompt_1", "action": "OK"}
        
        if rule_id == "R14":
            """WORK_ON_MODE: work_on = mas | <projekt>"""
            # R110-61 (R14 path-bug fix): R14 originally hard-coded only
            # ~/.config/goose/.mas-mode (line 640), but R110-31 (same file,
            # line 301-314) already canonicalized the path resolution to
            # a 3-path priority list: mas-engineer/.mas-mode > .mas-mode >
            # ~/.config/goose/.mas-mode. Apply the same here so R14 sees
            # the same authoritative .mas-mode as R110-31 and as the rest
            # of the system. Without this fix, running from a non-default
            # cwd (e.g. a clone of mas-engineer) would make R14 BLOCK even
            # though R110-31 would correctly pass — a false-positive that
            # blocked the pre-push-gate's Check 10 e2e run.
            mode_file = None
            for p in [
                os.path.join(BASE_DIR, "mas-engineer/.mas-mode"),
                os.path.join(BASE_DIR, ".mas-mode"),
                os.path.expanduser("~/.config/goose/.mas-mode"),
            ]:
                if os.path.exists(p):
                    mode_file = p
                    break
            if mode_file is None:
                return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                        "detail": "No .mas-mode found — work_on mode not determinable", "action": "BLOCKED"}
            with open(mode_file) as _f:
                mode = _f.read().strip()
            akt = action.lower()
            if mode != "mas":
                # Im Projekt-Mode: NOE MAS-Operationen erlaubt
                if any(x in akt for x in ["sub_mas-", "mas-engineer", "workflows.yaml"]):
                    return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                            "detail": f"work_on='{mode}' — MAS operations in project mode not allowed", "action": "BLOCKED"}
            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"], "action": "OK"}
        
        if rule_id == "R15":
            """ARCHITECTURE_APPROVAL: Nutzt dev_architecture_checker.py"""
            import subprocess as _sp
            try:
                result = _sp.run(
                    ["python3", "tools/dev_architecture_checker.py", "--action", action, "--file", ""],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 1:
                    return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                            "detail": result.stdout.strip(), "action": "BLOCKED"}
            except Exception:
                return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                        "detail": "dev_architecture_checker.py not found", "action": "WARNING"}
            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"], "action": "OK"}
        
        if rule_id == "R16":
            """TOOL_BEFORE_EXPERT: Checks if tool exists before delegating to expert"""
            akt = action.lower()
            if "delegate" in akt:
                # Extract agent_name aus delegate()
                import re as _re
                m = _re.search(r"sub_mas-(\w+)", akt)
                if m:
                    agent_name = m.group(1)
                    # Check ob a Tool exists das den Job macht
                    tool_match = False
                    for tool_cat in ["analyse", "build", "harden", "dashboard"]:
                        tool_check = f"dev_{tool_cat}" in akt or tool_cat in agent_name
                        if tool_check:
                            tool_match = True
                            break
                    if not tool_match:
                        return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                                "detail": f"Delegate to {agent_name} without prior tool check! Order: 1. Tool → 2. Expert → 3. New agent", "action": "WARNING"}
            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"], "action": "OK"}
        
        if rule_id == "R17":
            """IMPROVEMENT_PUSH: Push improvements to user"""
            # Will in general-improver checked — hier only Note
            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"],
                    "detail": "R17 will in general-improver Step 8 checked", "action": "OK"}

        if rule_id == "R19":
            """PATH-HIERARCHY: ONLY execute installed tools — NEVER source tools"""
            akt = action.lower()
            # CHECK 1: Build/Install exception (BEFORE source check)
            if "dev_build.sh" in akt or "dev_install.sh" in akt:
                return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"],
                        "detail": "Build/install exception — source access allowed", "action": "OK"}
            # CHECK 2: Install path (correct)
            install_patterns = ["mas-engineer-tools/", "MAS_TOOLS_DIR"]
            for pattern in install_patterns:
                if pattern in akt:
                    return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"],
                            "detail": "Install path used — correct", "action": "OK"}
            # CHECK 3: Source path (BLOCKED)
            source_patterns = ["mas-engineer/tools/", "mas-engineer/tools/dev_"]
            for pattern in source_patterns:
                if pattern in akt:
                    return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                            "detail": f"Source-Path erkannt ('{pattern}')! Nutze $MAS_TOOLS_DIR (Install-Path) statt Source",
                            "action": "BLOCKED"}
            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"],
                    "detail": "No tool-call detected — R19 not applicable", "action": "OK"}

        if rule_id == "R18":
            """DELEGATION DUTY: NEVER shell/write/edit yourself if sub-agent exists"""
            akt = action.lower()
            # Check ob es sich um eine shell/write/edit action handelt
            ist_selbst_mach = any(x in akt for x in ["shell", "write", "edit"])
            if not ist_selbst_mach:
                return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"],
                        "detail": "No shell/write/edit action — R18 not applicable", "action": "OK"}

            # Check ob a passender Sub-Agent exists
            wf_path = os.path.join(BASE_DIR, ".mase/workflows.yaml")
            sub_agent_found = False
            if os.path.exists(wf_path):
                with open(WORKFLOWS_DATEI) as f:
                    wf = yaml.safe_load(f)
                sub_agents = wf.get("configs", {}).get("mas-self", {}).get("sub_agents", {})
                all_sub_agent_names = []
                for cat, agents in sub_agents.items():
                    all_sub_agent_names.extend(agents)

                for agent in all_sub_agent_names:
                    agent_clean = agent.replace("sub_mas-", "").replace("_", "-").lower()
                    if agent_clean in akt or any(word in akt for word in agent_clean.split("-")):
                        sub_agent_found = True
                        founder_agent = agent
                        break

            if sub_agent_found:
                return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                        "detail": f"Sub-Agent {founder_agent} exists for these Task — delegiere() statt do it yourself!",
                        "action": "BLOCKED"}
            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"],
                    "detail": "No matching sub-agent found — doing it yourself allowed", "action": "OK"}
        
        return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"], "action": "OK"}
    
    return {"violation": False, "rule": "unbekannt", "hardness": 2, "action": "OK"}

def format_output(resultse, action_type=""):
    blocked = [r for r in resultse if r.get("action") == "BLOCKED"]
    
    lines = []
    lines.append("=== ⛔ REGEL-CHECK ===")
    lines.append(f"action: {action_type}")
    lines.append(f"Gechecks: {len(resultse)} Rulen")
    
    for r in resultse:
        if r.get("hardness", 0) >= 5:
            lines.append(f"⛔⛔⛔⛔⛔ {r['rule']}: {r['action']} — {r.get('detail', 'ok')}")
        elif r.get("hardness", 0) >= 4:
            lines.append(f"⛔⛔⛔ {r['rule']}: {r['action']} — {r.get('detail', 'ok')}")
        else:
            lines.append(f"⛔ {r['rule']}: {r['action']} — {r.get('detail', 'ok')}")
    
    if blocked:
        lines.append(f"\n⛔⛔⛔⛔⛔ {len(blocked)} EXTREME-STRONG VERSTOESSE!")
        lines.append("AKTION WAS BLOCKIERT — User informieren")
        for b in blocked:
            lines.append(f"  → {b['rule']}: {b['detail']}")
        return "\n".join(lines), False
    else:
        lines.append("\n✅ All Rulen eingehalten — action approved")
        return "\n".join(lines), True

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Rule check before actions")
    parser.add_argument("--check", help="Rule-ID (R01-R18)")
    parser.add_argument("--file", default=None, help="Betroffene file (for R09)")
    parser.add_argument("--action", default="", help="Geplante action (z.B. 'edit file.yaml')")
    parser.add_argument("--mode", default="mas", help="Current mode")
    parser.add_argument("--all", action="store_true", help="All Rulen check")
    parser.add_argument("--action-type", default="unbekannt", help="type of action: write|edit|delegate|shell")
    
    args = parser.parse_args()
    global CURRENT_MODE
    CURRENT_MODE = args.mode or "mas"
    
    action_info = f"{args.action_type}: {args.action}" if args.action else args.action_type
    
    if args.all:
        active_rules = get_rules(args.mode)
        # R09 ALWAYS FIRST checkn (oberste Rule) — only im MAS-Mode
        if args.mode == "mas":
            r09_result = check_rule("R09", args.action or "")
            resultse = [r09_result]
            # ALL other rules (without duplicates via ID)
            gesehene_ids = {"R09", "R19"}
            for idx, r in enumerate(active_rules):
                rid = r.get("id", f"G{idx:02d}")
                if rid not in gesehene_ids:
                    gesehene_ids.add(rid)
                    resultse.append(check_rule(rid, args.action or ""))
        else:
            resultse = [check_rule(r.get("id", f"G{i:02d}"), args.action or "") for i, r in enumerate(active_rules)]
        output, ok = format_output(resultse, action_info)
        print(output)
        sys.exit(0 if ok else 1)
    elif args.check:
        result = check_rule(args.check, args.action or "")
        if result.get("violation"):
            print(f"⛔⛔⛔⛔⛔ REGEL-VERSTOSS: {result['rule']}")
            print(f"  Detail: {result['detail']}")
            print(f"  action: {result['action']}")
            sys.exit(1)
        else:
            print(f"✅ {result['rule']}: OK")
            sys.exit(0)
    else:
        # Default: all Rulen des activeen Mode check
        active_rules = get_rules(args.mode)
        if args.mode == "mas":
            resultse = [check_rule(r["id"], args.action or "") for r in active_rules if isinstance(r, dict)]
        else:
            resultse = [{"rule": r.get("name", r.get("id", "?")), "hardness": r.get("hardness", 3),
                          "action": "WARNING" if r.get("block") else "OK",
                          "detail": r.get("prompt_text", str(r)[:100])}
                         for r in active_rules if isinstance(r, dict)]
        output, ok = format_output(resultse, action_info)
        print(output)
        sys.exit(0 if ok else 1)
