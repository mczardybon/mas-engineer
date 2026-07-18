#!/usr/bin/env python3
"""Manually drive the MCP server via stdio JSON-RPC, like a human would.
This tests server.js exactly as goose (or any MCP client) would use it.
"""
import subprocess
import json
import sys
import time
import os

WS = '/tmp/mas-engineer/mas-engineer'
MCP = f'{WS}/.mas/mcp'

def send(proc, msg):
    """Send JSON-RPC message as newline-delimited JSON (MCP SDK accepts both)."""
    body = json.dumps(msg).encode('utf-8')
    proc.stdin.write(body + b'\n')
    proc.stdin.flush()

def recv(proc, timeout=5):
    """Read one newline-delimited JSON response (MCP SDK supports both)."""
    import select
    end = time.time() + timeout
    buf = b''
    while time.time() < end:
        if proc.stdout in select.select([proc.stdout], [], [], 0.2)[0]:
            chunk = proc.stdout.read(4096)
            if not chunk:
                break
            buf += chunk
            # Try newline-delimited first
            if b'\n' in buf:
                # Find a complete JSON line
                for line in buf.split(b'\n'):
                    line = line.strip()
                    if line.startswith(b'{') and line.endswith(b'}'):
                        try:
                            return json.loads(line.decode('utf-8'))
                        except:
                            continue
            # Try Content-Length framed
            if b'\r\n\r\n' in buf:
                header_end = buf.find(b'\r\n\r\n')
                header = buf[:header_end].decode('utf-8', errors='ignore')
                cl = None
                for ln in header.split('\r\n'):
                    if ln.lower().startswith('content-length:'):
                        try:
                            cl = int(ln.split(':', 1)[1].strip())
                        except:
                            pass
                if cl and len(buf) >= header_end + 4 + cl:
                    body = buf[header_end+4:header_end+4+cl]
                    return json.loads(body.decode('utf-8'))
        else:
            time.sleep(0.1)
    return None

def main():
    print('═' * 60)
    print('PHASE 2: Manual MCP server drive via JSON-RPC')
    print('═' * 60)

    # Start server.js with stdio
    proc = subprocess.Popen(
        ['/usr/bin/node', 'server.js'],
        cwd=MCP,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0
    )
    time.sleep(1)
    if proc.poll() is not None:
        print('❌ Server died on startup')
        print(proc.stderr.read().decode())
        return 1
    print(f'✅ Server alive (PID {proc.pid})\n')

    # 1. initialize
    print('--- 1. initialize ---')
    send(proc, {
        'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
        'params': {
            'protocolVersion': '2024-11-05',
            'capabilities': {},
            'clientInfo': {'name': 'manual-test', 'version': '1.0'}
        }
    })
    r = recv(proc)
    if r and 'result' in r:
        srv = r['result'].get('serverInfo', {})
        print(f'   ✅ Server: {srv.get("name")} v{srv.get("version")}')
        print(f'   ✅ Protocol: {r["result"].get("protocolVersion")}')
        caps = r['result'].get('capabilities', {})
        print(f'   ✅ Capabilities: {list(caps.keys())}')
    else:
        print(f'   ❌ Bad response: {r}')
        proc.kill()
        return 1

    # 2. notifications/initialized
    print('\n--- 2. notifications/initialized ---')
    send(proc, {'jsonrpc': '2.0', 'method': 'notifications/initialized'})
    time.sleep(0.5)
    print('   ✅ Sent')

    # 3. tools/list
    print('\n--- 3. tools/list ---')
    send(proc, {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'})
    r = recv(proc)
    if r and 'result' in r and 'tools' in r['result']:
        tools = r['result']['tools']
        for t in tools:
            print(f'   ✅ Tool: {t["name"]}')
            print(f'      desc: {t["description"][:80]}')
            print(f'      schema: {list(t["inputSchema"]["properties"].keys())}')
    else:
        print(f'   ❌ Bad response: {r}')

    # 4. resources/list
    print('\n--- 4. resources/list ---')
    send(proc, {'jsonrpc': '2.0', 'id': 3, 'method': 'resources/list'})
    r = recv(proc)
    if r and 'result' in r:
        for res in r['result'].get('resources', []):
            print(f'   ✅ Resource: {res["uri"]}')
            print(f'      name: {res["name"]}')
            print(f'      mimeType: {res["mimeType"]}')

    # 5. resources/read
    print('\n--- 5. resources/read ui://framework-dashboard/main ---')
    send(proc, {
        'jsonrpc': '2.0', 'id': 4, 'method': 'resources/read',
        'params': {'uri': 'ui://framework-dashboard/main'}
    })
    r = recv(proc)
    if r and 'result' in r:
        content = r['result']['contents'][0]
        html = content['text']
        print(f'   ✅ Content length: {len(html)} bytes')
        print(f'   ✅ URI: {content["uri"]}')
        print(f'   ✅ mimeType: {content["mimeType"]}')
        print(f'   ✅ First 150 chars: {html[:150]}')
    else:
        print(f'   ❌ Bad response: {r}')

    # 6. tools/call show_framework_dashboard
    print('\n--- 6. tools/call show_framework_dashboard (no workspace) ---')
    send(proc, {
        'jsonrpc': '2.0', 'id': 5, 'method': 'tools/call',
        'params': {'name': 'show_framework_dashboard', 'arguments': {}}
    })
    r = recv(proc, timeout=10)
    if r and 'result' in r:
        content = r['result']['content'][0]
        html = content['text']
        print(f'   ✅ Response length: {len(html)} bytes')
        print(f'   ✅ Type: {content["type"]}')
        print(f'   ✅ Has __WORKSPACE__: {"window.__WORKSPACE__" in html}')
        # Check workspace was injected
        import re
        m = re.search(r'window\.__WORKSPACE__\s*=\s*["\']([^"\']+)', html)
        if m:
            print(f'   ✅ Workspace injected: {m.group(1)}')
        # Check it has dashboard elements
        for keyword in ['agent', 'health', 'dispatch', 'change']:
            if keyword.lower() in html.lower():
                print(f'   ✅ Contains "{keyword}"')
    else:
        print(f'   ❌ Bad response: {r}')

    # 7. tools/call with explicit workspace
    print('\n--- 7. tools/call with workspace arg ---')
    send(proc, {
        'jsonrpc': '2.0', 'id': 6, 'method': 'tools/call',
        'params': {'name': 'show_framework_dashboard', 'arguments': {'workspace': '/custom/ws'}}
    })
    r = recv(proc, timeout=10)
    if r and 'result' in r:
        html = r['result']['content'][0]['text']
        import re
        m = re.search(r'window\.__WORKSPACE__\s*=\s*["\']([^"\']+)', html)
        if m:
            ws = m.group(1)
            if ws == '/custom/ws':
                print(f'   ✅ Custom workspace correctly injected: {ws}')
            else:
                print(f'   ❌ Wrong workspace: {ws} (expected /custom/ws)')

    # 8. ping
    print('\n--- 8. ping ---')
    send(proc, {'jsonrpc': '2.0', 'id': 99, 'method': 'ping'})
    r = recv(proc)
    if r and 'result' in r:
        print(f'   ✅ Pong: {r["result"]}')

    # Cleanup
    proc.terminate()
    time.sleep(0.5)
    proc.kill()
    print('\n═' * 60)
    print('PHASE 2: COMPLETE')
    print('═' * 60)
    return 0

if __name__ == '__main__':
    sys.exit(main())
