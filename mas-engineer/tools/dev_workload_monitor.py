#!/usr/am/env python3
"""
dev_workload_monitor.py — Workload-Analyse for MAS-Agenten
Erkennt aboutlastete Agenten und deployt Relief-Agents via SOT+Generator.

Aufruf:
  python3 dev_workload_monitor.py --hours 24          # Report all Agenten
  python3 dev_workload_monitor.py --hours 24 --json    # JSON-Output
  python3 dev_workload_monitor.py --deploy             # Auto-Deploy kritische Agenten
  python3 dev_workload_monitor.py --deploy --agent scanner  # Only a Agenten
"""
import os, sys, json, time, sqlite3, yaml, subprocess

def scan_sessions(agent_name=None, hours=24):
    """Read Session-DB, aggregiere Metriken pro Agent."""
    db_path = os.path.expanduser("~/.config/goose/sessions/sessions.db")
    if not os.path.exists(db_path):
        return []
    
    cutoff = time.time() - hours * 3600
    cutoff_str = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(cutoff))
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    if agent_name:
        cur.execute("""
            SELECT name, COUNT(*), COALESCE(SUM(total_tokens), 0), 
                   COALESCE(SUM(CAST(total_tokens > 50000 AS INTEGER)), 0)
            FROM sessions 
            WHERE session_type='sub_agent' AND created_at > ? AND name LIKE ?
            GROUP BY name
            ORDER BY 2 DESC
        """, (cutoff_str, f'%{agent_name}%'))
    else:
        cur.execute("""
            SELECT name, COUNT(*), COALESCE(SUM(total_tokens), 0),
                   COALESCE(SUM(CAST(total_tokens > 50000 AS INTEGER)), 0)
            FROM sessions 
            WHERE session_type='sub_agent' AND created_at > ?
            GROUP BY name
            ORDER BY 2 DESC
        """, (cutoff_str,))
    
    rows = [{"name": r[0], "count": r[1], "tokens": r[2], "errors": r[3]} for r in cur.fetchall()]
    conn.close()
    return rows

def compute_workload(sessions):
    """Score 0-100% aus Token-Verbrauch + Anfrage-Frequenz."""
    if not sessions:
        return []
    
    max_tokens = max(s["tokens"] for s in sessions) or 1
    max_count = max(s["count"] for s in sessions) or 1
    max_errors = max(s["errors"] for s in sessions) or 1
    
    workloads = []
    for s in sessions:
        token_score = (s["tokens"] / max_tokens) * 40
        freq_score = (s["count"] / max_count) * 30
        error_score = (s["errors"] / max_errors) * 30
        score = round(token_score + freq_score + error_score, 1)
        
        if score < 40:
            level = "idle"
        elif score < 60:
            level = "normal"
        elif score < 80:
            level = "elevated"
        else:
            level = "critical"
        
        workloads.append({
            "name": s["name"],
            "score": score,
            "level": level,
            "tokens": s["tokens"],
            "count": s["count"],
            "errors": s["errors"]
        })
    
    return sorted(workloads, key=lambda w: -w["score"])

def recommend(workloads, threshold=80):
    """Generiere Vorschlaege for Workloads > threshold."""
    recs = []
    for w in workloads:
        if w["score"] >= threshold:
            recs.append({
                "agent": w["name"].replace("sub_mas-", "").replace(".yaml", ""),
                "score": w["score"],
                "level": w["level"],
                "auto_deploy": w["score"] >= 80
            })
    return recs

def deploy_relief_agent(agent_name, base=None):
    """Erzeuge Relief-Agent via SOT + Generator (SOT-konform)."""
    if base is None:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    schema_path = os.path.join(base, ".state/templates/agent_schema.yaml")
    
    if not os.path.exists(schema_path):
        return f"❌ SOT not found: {schema_path}"
    
    schema = yaml.safe_load(open(schema_path))
    relief_name = f"{agent_name}-relief"
    
    if relief_name in schema.get("agents", {}):
        return f"⚠️  {relief_name} exists already"
    
    schema.setdefault("agents", {})[relief_name] = {
        "emoji": "⚡",
        "title": f"SUB-MAS-{agent_name.upper()}-RELIEF — Entlastung for {agent_name}",
        "description": f"v1.0.0 | MAS: Relief-Agent, auto-deployed per Workload-Monitor",
        "instructions": (
            f"# {agent_name}-relief\n\n"
            f"Entlastet {agent_name} bei hoher Workload.\n"
            f"- Aboutnimmt Default-Routine-Tasks\n"
            f"- Delegiert komplexe Faelle back an {agent_name}\n"
            f"- Arbeitet autark\n\n"
            f"Boundaries:\n"
            f"- KEINE Konfig-Changeen an {agent_name}\n"
            f"- KEINE Entscheidungen ohne Ruecksprache\n"
            f"- NUR Routine-Tasks"
        ),
        "prompt": (
            f"⚡ {agent_name.upper()}-RELIEF (v1.0.0)\n\n"
            f"  NUR Routine-Tasks — Delegiere komplexes an {agent_name}\n"
            f"  ⛔ CONFIRMATIONSPFLICHT (R01)\n"
            f"  ⛔ MODUS-DOMANEN-KOPPLUNG (R09) NUR mas-engineer/"
        )
    }
    
    with open(schema_path, 'w') as f:
        yaml.dump(schema, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    
    gen_path = os.path.join(base, "tools/dev_yaml_generator.py")
    if os.path.exists(gen_path):
        # Generator will from WORKSPACE_ROOT aus aufgerufen (oben minus mas-engineer)
        workspace = os.path.dirname(base)
        r = subprocess.run(['python3', gen_path, '--target', workspace], 
                          capture_output=True, text=True, cwd=workspace)
    
    sub_dir = os.path.join(base, "recipe/sub")
    valid = 0
    total = 0
    for f in sorted(os.listdir(sub_dir)):
        if f.endswith('.yaml'):
            total += 1
            try:
                yaml.safe_load(open(os.path.join(sub_dir, f)))
                valid += 1
            except:
                pass
    
    return f"✅ {relief_name} deployed ({valid}/{total} YAMLs valide)"

def report(workloads, recommendations):
    """Formatiere als Markdown-Report."""
    lines = []
    lines.append("📊 WORKLOAD-REPORT")
    lines.append("=" * 40)
    
    for wl in workloads:
        icons = {"idle": "🟢", "normal": "📊", "elevated": "⚠️", "critical": "🔴"}
        icon = icons.get(wl["level"], "❓")
        name = wl["name"].replace("sub_mas-", "").replace(".yaml", "")[:35]
        lines.append(f"  {icon} {name:35s} {wl['score']:5.1f}%  {wl['tokens']//1000:3d}K Tokens  {wl['count']:2d} Calls")
    
    if recommendations:
        lines.append(f"\n  🔴 Recommendations ({len(recommendations)}):")
        for r in recommendations:
            lines.append(f"    - {r['agent']}: {r['score']}% — deploye Relief-Agent")
    
    return "\n".join(lines)

def main():
    import sys as _sys
    args = _sys.argv[1:]
    
    hours = 24
    threshold = 80
    agent = None
    do_deploy = False
    do_json = False
    
    for i, a in enumerate(args):
        if a == '--hours' and i+1 < len(args):
            hours = int(args[i+1])
        elif a == '--threshold' and i+1 < len(args):
            threshold = int(args[i+1])
        elif a == '--agent' and i+1 < len(args):
            agent = args[i+1]
        elif a == '--deploy':
            do_deploy = True
        elif a == '--json':
            do_json = True
    
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 1. Scannen
    sessions = scan_sessions(agent, hours)
    workloads = compute_workload(sessions)
    
    if not workloads:
        print("No Session-Data in den letzten {hours}h")
        return 0
    
    # 2. Recommendations
    recs = recommend(workloads, threshold)
    
    # 3. Deploy (falls gefordert)
    if do_deploy and recs:
        print(f"Deploye Relief-Agents for {len(recs)} Agenten...")
        for r in recs:
            if r["auto_deploy"]:
                result = deploy_relief_agent(r["agent"], base)
                print(f"  {result}")
    
    if do_deploy and agent:
        print(f"Deploye Relief-Agent for {agent}...")
        result = deploy_relief_agent(agent, base)
        print(f"  {result}")
        return 0
    
    # 4. Output
    if do_json:
        print(json.dumps({"workloads": workloads, "recommendations": recs}, indent=2))
    else:
        output = report(workloads, [r for r in recs if r["score"] >= threshold])
        print(output)
    
    return 0

if __name__ == "__main__":
    main()
