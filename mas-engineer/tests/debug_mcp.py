#!/usr/bin/env python3
"""Debug MCP server with full stderr capture."""
import subprocess
import json
import time
import os
import sys

WS = os.getcwd()
MCP = f'{WS}/.mas/mcp'

# Test 1: Does the server even start cleanly with manual JSON-RPC?
print('=== Test: send raw JSON-RPC, capture all output ===')

proc = subprocess.Popen(
    ['/usr/bin/node', 'server.js'],
    cwd=MCP,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    bufsize=0
)
time.sleep(1)
print(f'PID: {proc.pid}, poll: {proc.poll()}')

# Check stderr first
import select
time.sleep(0.3)
if proc.stderr in select.select([proc.stderr], [], [], 0.5)[0]:
    err = proc.stderr.read(8192)
    print(f'stderr early: {err.decode()!r}')

# Send raw newline-delimited JSON (NOT content-length, simplest)
msg = json.dumps({
    'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
    'params': {
        'protocolVersion': '2024-11-05',
        'capabilities': {},
        'clientInfo': {'name': 'test', 'version': '1.0'}
    }
})
print(f'\nSending: {msg[:120]}...')
proc.stdin.write((msg + '\n').encode('utf-8'))
proc.stdin.flush()

# Wait and read
time.sleep(2)
poll = proc.poll()
print(f'After send: poll={poll}')

# Read all available output
if proc.stdout in select.select([proc.stdout], [], [], 1)[0]:
    out = proc.stdout.read(16384)
    print(f'stdout: {out.decode("utf-8", errors="ignore")!r}')
else:
    print('No stdout available')

if proc.stderr in select.select([proc.stderr], [], [], 0.5)[0]:
    err = proc.stderr.read(8192)
    print(f'stderr: {err.decode("utf-8", errors="ignore")!r}')

proc.terminate()
time.sleep(0.5)
proc.kill()
print(f'Final exit: {proc.poll()}')
