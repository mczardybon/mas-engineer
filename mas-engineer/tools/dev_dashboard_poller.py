# ⛔⛔⛔ DEPRECATED v1.0.0 — Replaces durch dev_dashboard_refresh.py (On-Demand)
#!/usr/am/env python3
"""dev_dashboard_poller.py — 3s Polling-Daemon for mas-framework-hub
==================================================================
Runs im Hintergrund als Python-Daemon.
All 3s: JSON generate + via iterageApp an die App senden.

Nutzung:
  python3 dev_dashboard_poller.py start   # Startet Daemon (Hintergrund)
  python3 dev_dashboard_poller.py stop    # Stoppt Daemon
  python3 dev_dashboard_poller.py status  # Status check
  python3 dev_dashboard_poller.py once    # Einmalig generate + senden
"""
import json, os, sys, time, subprocess, signal, atexit, tempfile

PID_FILE = os.path.join(tempfile.gettempdir(), "mas-dashboard-poller.pid")
LOG_FILE = os.path.join(tempfile.gettempdir(), "mas-dashboard-poller.log")
STATUS_FILE = os.path.join(tempfile.gettempdir(), "mas-dashboard-poller.json")
WORKSPACE = os.environ.get('MAS_WORKSPACE', '.')
TOOLS_DIR = os.path.expanduser('~/.config/goose/recipes/mas-engineer-tools')
GENERATOR = os.path.join(TOOLS_DIR, 'dev_app_builder.py')

def log(msg):
    ts = time.strftime('%H:%M:%S')
    with open(LOG_FILE, 'a') as f:
        f.write(f'[{ts}] {msg}\n')

def generate_json():
    """JSON generate via dev_app_builder.py --generate"""
    try:
        r = subprocess.run(
            ['python3', GENERATOR, '--generate', '--workspace', WORKSPACE],
            capture_output=True, text=True, timeout=30
        )
        if r.returncode == 0:
            return json.loads(r.stdout) if r.stdout.strip() else {"status": "ok"}
        else:
            log(f'generate error: {r.stderr[:200]}')
            return None
    except Exception as e:
        log(f'generate exception: {e}')
        return None

def read_json():
    """Aktuelles JSON from Disk read"""
    try:
        with open(os.path.join(tempfile.gettempdir(), 'mas-dashboard-status.json')) as f:
            return json.load(f)
    except:
        return None

def poll_cycle():
    """Einmal: generate + senden"""
    # 1. Generieren (oder read falls generate fehlschlaegt)
    result = generate_json()
    if result is None:
        data = read_json()
        if data is None:
            log('No Data available')
            return False
    else:
        data = read_json()
        if data is None:
            log('JSON was not written')
            return False
    
    # 2. iterateApp via TypeScript (geht not direkt aus Python)
    # Stattdessen: JSON ist frisch auf Disk. Die App pollt about den MAS-Prozess.
    # Wir write only den Status, dass frisches JSON ready steht.
    status = {
        "last_update": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        "cycle": poll_cycle.counter,
        "agents": data.get('mas',{}).get('agents',0),
        "si_runs": data.get('mas',{}).get('self_improve',{}).get('total_runs',0),
        "dispatch": data.get('dispatch',{}).get('total',0),
        "history": len(data.get('history',{}).get('health_trend',[])),
        "json_size": len(json.dumps(data)),
        "healthy": True
    }
    poll_cycle.counter += 1
    
    with open(STATUS_FILE, 'w') as f:
        json.dump(status, f)
    
    return True

poll_cycle.counter = 0

def daemon_loop():
    """Daemon-Hauptschleife: all 3s generate"""
    log('Daemon started (Intervall: 3s)')
    log(f'Workspace: {WORKSPACE}')
    log(f'Generator: {GENERATOR}')
    
    # Initial generate
    poll_cycle()
    log('Initialer Zyklus completed')
    
    while True:
        time.sleep(3)
        try:
            poll_cycle()
        except Exception as e:
            log(f'Error im Zyklus: {e}')

def start_daemon():
    """Daemon im Hintergrund start"""
    if os.path.exists(PID_FILE):
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        try:
            os.kill(pid, 0)  # Checkn ob Prozess lebt
            print(f'Daemon runs already (PID {pid})')
            return
        except:
            os.remove(PID_FILE)
    
    pid = os.fork()
    if pid == 0:
        # Kindprozess
        os.setsid()
        # Stdout/Stderr umleiten
        with open(LOG_FILE, 'a') as f:
            os.dup2(f.fileno(), sys.stdout.fileno())
            os.dup2(f.fileno(), sys.stderr.fileno())
        
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
        
        daemon_loop()
    else:
        print(f'Daemon started (PID {pid})')
        print(f'  Log: {LOG_FILE}')
        print(f'  PID: {PID_FILE}')
        print(f'  Intervall: 3s')

def stop_daemon():
    """Daemon stoppen"""
    if not os.path.exists(PID_FILE):
        print('Daemon runs not')
        return
    
    with open(PID_FILE) as f:
        pid = int(f.read().strip())
    
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(1)
        os.remove(PID_FILE)
        print(f'Daemon gestoppt (PID {pid})')
    except ProcessLookupError:
        print(f'Daemon not found (PID {pid})')
        os.remove(PID_FILE)
    except Exception as e:
        print(f'Error beim Stoppen: {e}')

def status():
    """Status anshow"""
    if os.path.exists(PID_FILE):
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        try:
            os.kill(pid, 0)
            alive = True
        except:
            alive = False
        if alive:
            print(f'Daemon: ✅ Runs (PID {pid})')
        else:
            print(f'Daemon: ❌ PID {pid} exists not mehr')
    else:
        print('Daemon: ⏹️  Gestoppt')
    
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE) as f:
            s = json.load(f)
        print(f'Letzter Zyklus: {s.get("last_update","?")}')
        print(f'Zyklen: {s.get("cycle",0)}')
        print(f'Agents: {s.get("agents","?")} | SI-Runs: {s.get("si_runs","?")}')
    
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            lines = f.readlines()
        last = lines[-5:] if len(lines) > 5 else lines
        print(f'\nLetzte Log-Eintraege ({len(lines)} total):')
        for l in last:
            print(f'  {l.strip()}')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Nutzung: python3 dev_dashboard_poller.py {start|stop|status|once}')
        sys.exit(1)
    
    cmd = sys.argv[1]
    if cmd == 'start':
        start_daemon()
    elif cmd == 'stop':
        stop_daemon()
    elif cmd == 'status':
        status()
    elif cmd == 'once':
        poll_cycle()
        print(f'Zyklus {poll_cycle.counter} completed')
    else:
        print(f'Unbekannter Command: {cmd}')
        print('Available: start, stop, status, once')
