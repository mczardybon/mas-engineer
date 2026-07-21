#!/usr/bin/env node
/**
 * Framework Dashboard MCP Server v1.0.0
 * Serves dashboard data and HTML frontend
 * Protocol: reads .mas/dashboards/project.json + data.json
 */
const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs-extra');
const app = express();
const PORT = process.env.PORT || 3000;

// Resolve workspace: try env var, then hermit dir, then cwd
let WORKSPACE = process.env.MAS_WORKSPACE;
if (!WORKSPACE) {
  // Try to detect from common locations
  const candidates = [
    process.env.HOME ? `${process.env.HOME}/agent_new_start/mas-agent` : null,
    process.cwd(),
  ].filter(Boolean);
  for (const c of candidates) {
    if (fs.existsSync(path.join(c, '.mas', 'dashboards'))) {
      WORKSPACE = c;
      break;
    }
  }
}
if (!WORKSPACE) WORKSPACE = process.env.HOME || process.cwd();
const DASHBOARD_DIR = path.join(WORKSPACE, '.mas', 'dashboards');
const MCP_DIR = path.join(WORKSPACE, '.mas', 'mcp');

app.use(cors());
app.use(express.json({ limit: '10mb' }));

// Serve static HTML
app.use(express.static(MCP_DIR));

// Dashboard data API
app.get('/api/dashboard', async (req, res) => {
  try {
    const projectFile = path.join(DASHBOARD_DIR, 'project.json');
    const dataFile = path.join(DASHBOARD_DIR, 'data.json');
    let data = {};
    // Priority: data.json (aktuell, live-generiert) > project.json (Framework-Snapshot)
    if (await fs.pathExists(dataFile)) {
      data = await fs.readJson(dataFile);
    } else if (await fs.pathExists(projectFile)) {
      data = await fs.readJson(projectFile);
    }
    res.json({ success: true, data });
  } catch (err) {
    res.json({ success: false, error: err.message });
  }
});

// Health endpoint
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Tools count
app.get('/api/tools', async (req, res) => {
  try {
    const toolsDir = path.join(WORKSPACE, 'mas-engineer', 'tools');
    if (await fs.pathExists(toolsDir)) {
      const files = await fs.readdir(toolsDir);
      const tools = files.filter(f => f.startsWith('dev_') && (f.endsWith('.py') || f.endsWith('.sh')));
      res.json({ success: true, count: tools.length, tools });
    } else {
      res.json({ success: true, count: 0, tools: [] });
    }
  } catch (err) {
    res.json({ success: false, error: err.message });
  }
});

// Start HTTP server ALWAYS - the MCP stdio protocol is handled additionally
app.listen(PORT, '0.0.0.0', () => {
  console.log(`[Framework Dashboard] Server running on http://localhost:${PORT}`);
  console.log(`[Framework Dashboard] Workspace: ${WORKSPACE}`);
  console.log(`[Framework Dashboard] Dashboard dir: ${DASHBOARD_DIR}`);
});

// Handle MCP stdio protocol (when launched as goose extension)
const readline = require('readline');
const rl = readline.createInterface({ input: process.stdin });
const respond = (msg) => { try { process.stdout.write(JSON.stringify(msg) + '\n'); } catch(e) {} };

rl.on('line', async (line) => {
  try {
    const msg = JSON.parse(line);
    const { id, method } = msg;

    if (method === 'initialize') {
      respond({
        jsonrpc: '2.0', id,
        result: {
          protocolVersion: '2024-11-05',
          capabilities: { tools: { listChanged: false }, resources: { subscribe: false } },
          serverInfo: { name: 'framework-dashboard', version: '1.0.0' }
        }
      });
    } else if (method === 'tools/list') {
      const dataFile = path.join(DASHBOARD_DIR, 'data.json');
      const projectFile = path.join(DASHBOARD_DIR, 'project.json');
      let data = { agents: { total: 0, healthy: 0, degraded: 0 } };
      if (await fs.pathExists(dataFile)) {
        data = await fs.readJson(dataFile);
      } else if (await fs.pathExists(projectFile)) {
        data = await fs.readJson(projectFile);
      }
      const a = data.agents || {};
      respond({
        jsonrpc: '2.0', id,
        result: {
          tools: [{
            name: 'get_dashboard',
            description: `📊 Dashboard: ${a.total || 0} Agents | ✅ ${a.healthy || 0} Healthy | ⚠️ ${a.degraded || 0} Degraded`,
            inputSchema: { type: 'object', properties: {} }
          }]
        }
      });
    } else if (method === 'tools/call') {
      const dataFile = path.join(DASHBOARD_DIR, 'data.json');
      const projectFile = path.join(DASHBOARD_DIR, 'project.json');
      let data = {};
      if (await fs.pathExists(dataFile)) {
        data = await fs.readJson(dataFile);
      } else if (await fs.pathExists(projectFile)) {
        data = await fs.readJson(projectFile);
      }
      respond({
        jsonrpc: '2.0', id,
        result: { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] }
      });
    } else {
      respond({ jsonrpc: '2.0', id, result: {} });
    }
  } catch (err) {
    if (id) respond({ jsonrpc: '2.0', id, error: { code: -32603, message: err.message } });
  }
});
