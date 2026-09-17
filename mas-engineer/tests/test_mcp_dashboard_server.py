#!/usr/bin/env python3
"""
test_mcp_dashboard_server.py — pytest harness for .mase/mcp/server.js.

Per R110-151: bring the manual_mcp_test.py (208 LOC, runs once, prints
phases) into the pytest harness so it runs on every test invocation and
catches regressions in the MCP server contract.

Tests (8 invariants, real subprocess against server.js, NOT mocked):
  1. server starts, stays alive > 0.5s without crash
  2. initialize handshake returns name=framework-dashboard, v1.0.0,
     protocolVersion=2024-11-05
  3. tools/list returns exactly 1 tool: show_framework_dashboard,
     with inputSchema for workspace arg
  4. resources/list returns 1 resource: ui://framework-dashboard/main,
     mimeType=text/html;profile=mcp-app
  5. resources/read returns non-empty HTML containing
     __WORKSPACE_PLACEHOLDER__ and valid HTML structure (<html, <head,
     <body)
  6. tools/call (no args) returns HTML with
     window.__WORKSPACE__ = "<cwd>" injected
  7. tools/call with workspace='/custom/path' returns HTML with
     window.__WORKSPACE__ = "/custom/path" (NOT cwd, NOT placeholder)
  8. tools/call with unknown tool name returns JSON-RPC error
     (code -32601 or error.message non-empty)

Run with:
    python3 -m pytest tests/test_mcp_dashboard_server.py -v
    python3 -m pytest tests/test_mcp_dashboard_server.py -v --tb=short

Environment:
    - Requires node v18+ on PATH (or NODE_BIN env var pointing to node)
    - Requires .mase/mcp/node_modules to be installed (npm install in
      .mase/mcp)
    - Skipif: skips entire module if node missing OR node_modules
      missing (portability per R110-132)
"""
import json
import os
import re
import select
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
MCP_DIR = REPO_ROOT / ".mase" / "mcp"
SERVER_JS = MCP_DIR / "server.js"
DASHBOARD_HTML = MCP_DIR / "dashboard.html"
NODE_MODULES = MCP_DIR / "node_modules"

# Allow override via env (e.g. CI has node at /opt/node/bin/node)
NODE_BIN = os.environ.get("NODE_BIN") or shutil.which("node")


# ─── SKIP / SETUP ──────────────────────────────────────────────────


def _node_available() -> bool:
    return NODE_BIN is not None and SERVER_JS.exists() and DASHBOARD_HTML.exists() \
        and NODE_MODULES.exists()


pytestmark = pytest.mark.skipif(
    not _node_available(),
    reason=(
        f"node MCP server not available: "
        f"node={NODE_BIN}, server.js={SERVER_JS.exists()}, "
        f"dashboard.html={DASHBOARD_HTML.exists()}, "
        f"node_modules={NODE_MODULES.exists()}. "
        f"Run: NODE_BIN=/path/to/node npm install in .mase/mcp/"
    ),
)


# ─── JSON-RPC HELPERS (newline-delimited, the simpler MCP wire fmt) ─


def _send(proc, msg):
    body = (json.dumps(msg) + "\n").encode("utf-8")
    proc.stdin.write(body)
    proc.stdin.flush()


def _recv(proc, timeout=5):
    end = time.time() + timeout
    buf = b""
    while time.time() < end:
        if proc.stdout in select.select([proc.stdout], [], [], 0.2)[0]:
            chunk = proc.stdout.read(4096)
            if not chunk:
                break
            buf += chunk
            if b"\n" in buf:
                for line in buf.split(b"\n"):
                    line = line.strip()
                    if line.startswith(b"{") and line.endswith(b"}"):
                        try:
                            return json.loads(line.decode("utf-8"))
                        except json.JSONDecodeError:
                            continue
        else:
            time.sleep(0.05)
    return None


# ─── FIXTURES ──────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def mcp_server():
    """Start server.js once per module, yield (proc, send, recv), cleanup.

    Uses module scope so the 8 tests share one process — each test
    is a JSON-RPC call against the same server, which is how a real
    MCP client (goose, claude-code) uses it.
    """
    proc = subprocess.Popen(
        [NODE_BIN, "server.js"],
        cwd=str(MCP_DIR),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
    )
    # Give server a moment to bind stdio transport
    time.sleep(0.5)
    if proc.poll() is not None:
        stderr = proc.stderr.read().decode("utf-8", errors="ignore")
        pytest.fail(f"server.js died on startup: {stderr}")

    yield proc, _send, _recv

    proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


@pytest.fixture(scope="module")
def initialized_server(mcp_server):
    """Run initialize + notifications/initialized once, return the
    server fixture + a working state. Skips module if initialize fails.
    """
    proc, send, recv = mcp_server
    send(proc, {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "pytest-r110-151", "version": "1.0"},
        },
    })
    r = recv(proc)
    if not r or "result" not in r:
        pytest.fail(f"initialize failed: {r}")
    # notifications/initialized is a notification, no response expected
    send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
    time.sleep(0.2)
    return mcp_server


# ─── TESTS ────────────────────────────────────────────────────────


def test_1_server_alive_after_start(mcp_server):
    """Server stays alive > 0.5s without crash (handshake-able)."""
    proc, _, _ = mcp_server
    assert proc.poll() is None, (
        f"server exited prematurely with code {proc.returncode}"
    )


def test_2_initialize_handshake(initialized_server):
    """initialize returns name=framework-dashboard, v1.0.0, protocol
    version 2024-11-05, capabilities=tools+resources.
    """
    proc, send, recv = initialized_server
    # Re-initialize: the SDK may allow re-handshake for testing
    send(proc, {
        "jsonrpc": "2.0", "id": 100, "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-2", "version": "1.0"},
        },
    })
    r = recv(proc)
    assert r is not None, "no response to initialize"
    assert "result" in r, f"initialize returned error: {r.get('error')}"
    result = r["result"]
    assert result["serverInfo"]["name"] == "framework-dashboard", (
        f"wrong server name: {result['serverInfo']}"
    )
    assert result["serverInfo"]["version"] == "1.0.0", (
        f"wrong server version: {result['serverInfo']}"
    )
    assert result["protocolVersion"] == "2024-11-05", (
        f"wrong protocol version: {result['protocolVersion']}"
    )
    assert "tools" in result["capabilities"], (
        f"missing tools capability: {result['capabilities']}"
    )
    assert "resources" in result["capabilities"], (
        f"missing resources capability: {result['capabilities']}"
    )


def test_3_tools_list(initialized_server):
    """tools/list returns exactly 1 tool: show_framework_dashboard."""
    proc, send, recv = initialized_server
    send(proc, {"jsonrpc": "2.0", "id": 101, "method": "tools/list"})
    r = recv(proc)
    assert r is not None, "no response to tools/list"
    assert "result" in r, f"tools/list error: {r.get('error')}"
    tools = r["result"]["tools"]
    assert len(tools) == 1, f"expected 1 tool, got {len(tools)}: {tools}"
    tool = tools[0]
    assert tool["name"] == "show_framework_dashboard", (
        f"wrong tool name: {tool['name']}"
    )
    assert "description" in tool and tool["description"], (
        "tool description missing or empty"
    )
    assert "inputSchema" in tool, "tool inputSchema missing"
    assert "workspace" in tool["inputSchema"]["properties"], (
        f"workspace param missing: {tool['inputSchema']}"
    )


def test_4_resources_list(initialized_server):
    """resources/list returns 1 resource: ui://framework-dashboard/main
    with correct mimeType for MCP app rendering.
    """
    proc, send, recv = initialized_server
    send(proc, {"jsonrpc": "2.0", "id": 102, "method": "resources/list"})
    r = recv(proc)
    assert r is not None, "no response to resources/list"
    assert "result" in r, f"resources/list error: {r.get('error')}"
    resources = r["result"]["resources"]
    assert len(resources) == 1, (
        f"expected 1 resource, got {len(resources)}: {resources}"
    )
    res = resources[0]
    assert res["uri"] == "ui://framework-dashboard/main", (
        f"wrong resource URI: {res['uri']}"
    )
    assert "text/html" in res["mimeType"], (
        f"wrong mimeType for HTML resource: {res['mimeType']}"
    )


def test_5_resources_read_returns_dashboard_html(initialized_server):
    """resources/read returns non-empty HTML with __WORKSPACE_PLACEHOLDER__
    marker AND basic HTML structure (since dashboard.html must be a
    renderable page for MCP apps).
    """
    proc, send, recv = initialized_server
    send(proc, {
        "jsonrpc": "2.0", "id": 103, "method": "resources/read",
        "params": {"uri": "ui://framework-dashboard/main"},
    })
    r = recv(proc)
    assert r is not None, "no response to resources/read"
    assert "result" in r, f"resources/read error: {r.get('error')}"
    content = r["result"]["contents"][0]
    assert content["uri"] == "ui://framework-dashboard/main", (
        f"wrong content URI: {content['uri']}"
    )
    assert "text/html" in content["mimeType"], (
        f"wrong content mimeType: {content['mimeType']}"
    )
    html = content["text"]
    assert len(html) >= 100, f"HTML too small ({len(html)} bytes), not a real page"
    assert "__WORKSPACE_PLACEHOLDER__" in html, (
        "dashboard.html missing __WORKSPACE_PLACEHOLDER__ marker — "
        "server.js injection point is gone"
    )
    assert "<html" in html.lower() and "<head" in html.lower() and "<body" in html.lower(), (
        f"dashboard.html not a valid HTML page (no <html>/<head>/<body>)"
    )


def test_6_tools_call_default_workspace(initialized_server):
    """tools/call with no args injects the cwd as workspace into the
    returned HTML (the default-workspace contract from server.js:54).
    """
    proc, send, recv = initialized_server
    send(proc, {
        "jsonrpc": "2.0", "id": 104, "method": "tools/call",
        "params": {"name": "show_framework_dashboard", "arguments": {}},
    })
    r = recv(proc, timeout=10)
    assert r is not None, "no response to tools/call (default workspace)"
    assert "result" in r, f"tools/call error: {r.get('error')}"
    content = r["result"]["content"][0]
    assert content["type"] == "text", f"wrong content type: {content['type']}"
    html = content["text"]
    # workspace was injected; placeholder must be GONE
    assert "__WORKSPACE_PLACEHOLDER__" not in html, (
        "workspace placeholder still present after injection"
    )
    # extract injected workspace
    m = re.search(r'window\.__WORKSPACE__\s*=\s*["\']([^"\']+)["\']', html)
    assert m, f"window.__WORKSPACE__ not injected into HTML: {html[:200]}"
    ws = m.group(1)
    # cwd at server start is MCP_DIR; argv[0] in node context is server.js
    assert ws == str(MCP_DIR) or os.path.realpath(ws) == os.path.realpath(str(MCP_DIR)), (
        f"default workspace wrong: got {ws!r}, expected MCP_DIR={MCP_DIR}"
    )
    # CSP / UI meta must be present (server.js:67-71, 99-107)
    assert r["result"].get("_meta", {}).get("ui", {}).get("resourceUri") \
        == "ui://framework-dashboard/main", (
        f"missing UI resourceUri meta: {r['result']}"
    )


def test_7_tools_call_custom_workspace(initialized_server):
    """tools/call with explicit workspace='/custom/path' injects that
    path (NOT cwd, NOT placeholder).
    """
    proc, send, recv = initialized_server
    custom_ws = "/custom/test/workspace-R110-151"
    send(proc, {
        "jsonrpc": "2.0", "id": 105, "method": "tools/call",
        "params": {
            "name": "show_framework_dashboard",
            "arguments": {"workspace": custom_ws},
        },
    })
    r = recv(proc, timeout=10)
    assert r is not None, "no response to tools/call (custom workspace)"
    assert "result" in r, f"tools/call error: {r.get('error')}"
    html = r["result"]["content"][0]["text"]
    m = re.search(r'window\.__WORKSPACE__\s*=\s*["\']([^"\']+)["\']', html)
    assert m, f"workspace not injected: {html[:200]}"
    ws = m.group(1)
    assert ws == custom_ws, (
        f"custom workspace not honored: got {ws!r}, expected {custom_ws!r}"
    )


def test_8_tools_call_unknown_tool_returns_error(initialized_server):
    """tools/call with unknown tool name returns JSON-RPC error
    (server.js:74 throws Error, MCP SDK serializes to error response).
    """
    proc, send, recv = initialized_server
    send(proc, {
        "jsonrpc": "2.0", "id": 106, "method": "tools/call",
        "params": {"name": "nonexistent_tool", "arguments": {}},
    })
    r = recv(proc, timeout=5)
    assert r is not None, "no response to unknown tool call"
    # MCP SDK: unknown tool → error object on the response
    assert "error" in r, f"expected error for unknown tool, got: {r}"
    err = r["error"]
    # error must have a message (code may be -32601 internal error)
    assert "message" in err and err["message"], (
        f"error object missing message: {err}"
    )
    assert "nonexistent_tool" in err["message"] or "Unknown tool" in err["message"], (
        f"error message should reference the unknown tool: {err}"
    )
