#!/usr/bin/env python3
"""dashboard_prd_template.py — Generates PRD for mas-framework-hub-dashboard
=======================================================================
Liest current Data aus /tmp/mas-dashboard-status.json und
/tmp/mas-dashboard-signal.json, generates komplette PRD for
Apps.createApp() mit exakten valueen.
"""
import json, os, sys

STATUS_FILE = "/tmp/mas-dashboard-status.json"
SIGNAL_FILE = "/tmp/mas-dashboard-signal.json"

def load_data():
    with open(STATUS_FILE) as f:
        data = json.load(f)
    with open(SIGNAL_FILE) as f:
        sig = json.load(f)
    return data, sig

def generate_prd(d, sig):
    m = d["mas"]
    fw = d["framework"]
    dp = d["dispatch"]
    uf = d["user_framework"]
    ah = m["agent_health"]
    si = m["self_improve"]
    ss = m["session_stats"]
    bl = m["build"]
    hh = d["history"]["health_trend"]

    # Agenten-Table bauen
    agents_rows = ""
    for a in m["agent_scores"]:
        agents_rows += f'        <tr><td>{a["name"]}</td><td>{a["score"]}</td></tr>\n'

    # Change typees
    ctypees = m["changes_by_typee"]
    ctypees_rows = ""
    for k, v in sorted(ctypees.items(), key=lambda x: -x[1]):
        ctypees_rows += f'        <tr><td>{k}</td><td>{v}</td></tr>\n'

    # Dispatch-Tree
    dt = dp["tree"]
    dt_html = ""
    for line in dt:
        indent = "&nbsp;" * 4 * (len(line) - len(line.lstrip(" ")))
        dt_html += f'          <div>{indent}{line.strip()}</div>\n'

    # Health-Chart Data
    hh_labels = "', '".join([h["time"] for h in hh[-10:]])
    hh_mas = ", ".join([str(h["mas"]) for h in hh[-10:]])
    hh_fw = ", ".join([str(h["framework"]) for h in hh[-10:]])

    prd = f"""MAS-FRAMEWORK-HUB - Live Dashboard v2.4

Create a single self-contained dark-theme HTML app (1400x900px) with Chart.js from CDN.
HARDCODE ALL VALUES EXACTLY AS GIVEN. No placeholders, no dynamic updates.

DESIGN:
- Background: #0d1117, panels: #161b22, borders: #30363d
- Green: #3fb950, Orange: #f0883e, Blue: #58a6ff, Purple: #bc8cff, Red: #f85149
- Font: system-ui, 11px, monospace for data
- 3-column grid (1fr 1fr 1fr), 10px gap, 10px padding
- Panel headers: bold, 12px, border-bottom
- Scrollbar: thin, dark
- NO auto-refresh, NO setInterval, NO fetch

HEADER (full width):
  Left: "🟢 MAS-FRAMEWORK-HUB v2.4" in white bold 18px
  Center: Clock "{sig["ts"]}" in orange bold 24px monospace
  Right: Status "● Live" in green, Timestamp "{d["timestamp"]}"

PANEL 1 - MAS-ENGINEER (col 1, rows 1-3 / 1st row):
Title: "🦆 MAS-Engineer"
KPI row (green bordered cards):
  Agents: {m["agents"]} | Health: {ah["healthy"]}/{ah["total"]} | Score: {m["prompt_score_avg"]} | 10/10: {m["agents_at_10"]} | Tools: {m["tools"]}
KPI row 2:
  Changes: {m["changes"]} | Checkpoints: {m["checkpoints"]} | SI-RUNs: {si["total_runs"]} | Fleet: {"active " + str(m["fleet_max_paralll"]) if m["fleet_active"] else "inaktiv"}
Agent table (14 rows):
  sub_mas-agent-guardian 10.0
  sub_mas-config-auditor 9.0
  sub_mas-doc-generator 9.0
  sub_mas-framework-knowledge 9.0
  sub_mas-framework-scanner 8.0
  sub_mas-goose-admin 8.0
  sub_mas-goose-expert 10.0
  sub_mas-migration-helper 9.0
  sub_mas-prompt-engineer 9.0
  sub_mas-recipe-manager 7.0
  sub_mas-general-improver 8.0
  sub_mas-session-analyst 9.0
  sub_mas-test-runner 8.0
  sub_mas-yaml-editor 9.0
Last SI: {si.get("last_run", "-")}

PANEL 2 - SESSIONS & IMPROVING (col 2, row 1):
Title: "⏱ Sessions & Improving"
KPI: SI-RUNs: {si["total_runs"]} | Sessions: {ss.get("total_sessions", "?")} | Cost: {ss.get("total_cost", "?")} | Active: {ss.get("active_hours", "?")}
Line chart "healthChart" (canvas 300x150px) with Chart.js:
  labels: ['{hh_labels}']
  datasets: [{{label: 'MAS', data: [{hh_mas}], borderColor: '#3fb950'}}, {{label: 'framework', data: [{hh_fw}], borderColor: '#58a6ff'}}]

PANEL 3 - BUILDS & DISPATCH (col 3, row 1):
Title: "📦 Builds & Dispatch"
KPI: Builds: {bl["count"]} | Size: {bl["latest"]["size_kb"]}KB | Done: {dp["done"]} | Running: {dp["running"]} | Errors: {dp["errors"]}
Dispatch Tree (toggle with ▶/▼):
  {" ".join(dt)}

PANEL 4 - FRAMEWORK (col 2, row 2):
Title: "⚙ framework & Config"
KPI: Recipes: {fw["recipes"]["total"]} | Specialists: {fw["recipes"]["specialists"]} | Sub: {fw["recipes"]["subs"]} | Core: {fw["recipes"]["core"]}
Config: Provider={fw["config"]["provider"]}, Model=deepseek-chat, Extensions={len(fw["config"]["extensions"])}

PANEL 5 - USER (col 3, row 2):
Title: "👤 User-framework"
KPI: Recipes: {uf.get("recipes", 0)}
Workspace: {uf.get("workspace", "-")}
Status: {"● active" if uf.get("detected") else "○ inaktiv"} in green

PANEL 6 - ACTIONS (all columns, row 3):
Title: "🎮 Actions"
8 buttons in a row, styled dark with colored borders:
  🧪 Tests | 📦 Build | 🔄 SI-RUN | 🔍 Audit | 🛡️ Guardian | 📝 Doc-Check | 🧠 Knowledge | 📐 Blueprint
Each button: background #21262d, border #30363d, padding 8px 14px, border-radius 6px, cursor pointer.
"""

    with open("/tmp/dashboard_prd_current.txt", "w") as f:
        f.write(prd)

    print(prd)

if __name__ == "__main__":
    if not os.path.exists(STATUS_FILE):
        print("ERROR: No status data under " + STATUS_FILE)
        sys.exit(1)
    if not os.path.exists(SIGNAL_FILE):
        print("ERROR: No signal under " + SIGNAL_FILE)
        sys.exit(1)
    d = json.load(open(STATUS_FILE))
    sig = json.load(open(SIGNAL_FILE))
    generate_prd(d, sig)
