# ⛔⛔⛔ DEPRECATED v1.0.0 — Replaces durch dev_dashboard_refresh.py (On-Demand)
#!/usr/am/env python3
"""dev_dashboard_live.py v2.1 — Generator for Live-Dashboard
=========================================================
Startet/Stoppt a Hintergrund-Prozess der all 3s frisches
JSON generates.

Die iterateApp()-Aufrufe macht MAS selbst in der Session:
  while active:
    data = cat /tmp/mas-dashboard-status.json
    execute_typescript("Apps.iterateApp({name:'mas-framework-hub', feedback: data})")
    sleep(3)

Dieses Skript generates NUR das JSON + Signal.
"""
import json, os, sys, time, subprocess, signal, tempfile

PID_FILE = os.path.join(tempfile.gettempdir(), "mas-dashboard-generator.pid")
LOG_FILE = os.path.join(tempfile.gettempdir(), "mas-dashboard-generator.log")
SIGNAL_FILE = os.path.join(tempfile.gettempdir(), "mas-dashboard-signal.json")
WORKSPACE = os.environ.get('MAS_WORKSPACE', '.')
TOOLS_DIR = os.path.expanduser("~/.config/goose/recipes/mas-engineer-tools")

def log(msg):
    with open(LOG_FILE, 'a') as f:
        f.write(f'[{time.strftime("%H:%M:%S")}] {msg}\n')

def generate():
    r = subprocess.run(
        ["python3", os.path.join(TOOLS_DIR, "dev_app_builder.py"),
         "--generate", "--workspace", WORKSPACE],
        capture_output=True, text=True, timeout=30
    )
    if r.returncode != 0:
        log(f"ERROR: {r.stderr[:100]}")
        return False
    try:
        with open(os.path.join(tempfile.gettempdir(), "mas-dashboard-status.json")) as f:
            data = json.load(f)
    except:
        return False
    sig = {"ts": time.strftime("%H:%M:%S"), "agents": data.get("mas",{}).get("agents",0),
           "si_runs": data.get("mas",{}).get("self_improve",{}).get("total_runs",0),
           "json_size": len(json.dumps(data)), "pid": os.getpid()}
    with open(SIGNAL_FILE, 'w') as f:
        json.dump(sig, f)
    return True

def loop():
    log("Generator started (3s)")
    while True:
        try: generate()
        except Exception as e: log(f"Error: {e}")
        time.sleep(3)

def start():
    if os.path.exists(PID_FILE):
        with open(PID_FILE) as f:
            try: os.kill(int(f.read()), 0); print("Runs already"); return
            except: pass
    pid = os.fork()
    if pid == 0:
        with open(LOG_FILE, 'a') as f: os.dup2(f.fileno(), 1); os.dup2(f.fileno(), 2)
        with open(PID_FILE, 'w') as f: f.write(str(os.getpid()))
        loop()
    else:
        print(f"Generator started (PID {pid})")

def stop():
    if os.path.exists(PID_FILE):
        with open(PID_FILE) as f: pid = f.read().strip()
        try: os.kill(int(pid), signal.SIGTERM); os.remove(PID_FILE); print(f"Gestoppt (PID {pid})")
        except: os.remove(PID_FILE)
    else: print("Nicht active")

def status():
    alive = False
    if os.path.exists(PID_FILE):
        with open(PID_FILE) as f:
            pid = f.read().strip()
        try: os.kill(int(pid), 0); alive = True
        except: pass
        print(f"{'Runs' if alive else 'Tot'} (PID {pid})")
    else: print("Gestoppt")
    if os.path.exists(SIGNAL_FILE):
        s = json.load(open(SIGNAL_FILE))
        print(f"Letztes: {s.get('ts','?')} | Agents: {s.get('agents','?')}")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    {"start":start,"stop":stop,"status":status,"once":generate}.get(cmd, lambda:print("start|stop|status|once"))()
