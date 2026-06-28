#!/usr/bin/env node
import { readFileSync, existsSync, readFileSync as readFile } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ListResourcesRequestSchema,
  ReadResourceRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const APP_HTML = readFileSync(join(__dirname, "dashboard.html"), "utf-8");

const server = new Server(
  {
    name: "framework-dashboard",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
      resources: {},
    },
  }
);

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "show_framework_dashboard",
        description: "Zeigt das Framework-Dashboard mit Agent-Status, Health-Trends, Aenderungen und Dispatch-Info",
        inputSchema: {
          type: "object",
          properties: {
            workspace: {
              type: "string",
              description: "Pfad zum Framework-Workspace (optional, default = current dir)",
            },
          },
          required: [],
        },
      },
    ],
  };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  if (name === "show_framework_dashboard") {
    const workspace = args?.workspace || process.cwd();
    // Inject workspace into HTML so the app knows where to find data
    const injectedHtml = APP_HTML.replace(
      "/* __WORKSPACE_PLACEHOLDER__ */",
      `window.__WORKSPACE__ = ${JSON.stringify(workspace)};`
    );
    return {
      content: [
        {
          type: "text",
          text: injectedHtml,
        },
      ],
      _meta: {
        ui: {
          resourceUri: "ui://framework-dashboard/main",
        },
      },
    };
  }
  throw new Error(`Unknown tool: ${name}`);
});

server.setRequestHandler(ListResourcesRequestSchema, async () => {
  return {
    resources: [
      {
        uri: "ui://framework-dashboard/main",
        name: "Framework Dashboard",
        description: "Interaktives Dashboard mit Agent-Status, Health-Trends, Aenderungen und Dispatch-Info",
        mimeType: "text/html;profile=mcp-app",
      },
    ],
  };
});

server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
  const { uri } = request.params;
  if (uri === "ui://framework-dashboard/main") {
    return {
      contents: [
        {
          uri: "ui://framework-dashboard/main",
          mimeType: "text/html;profile=mcp-app",
          text: APP_HTML,
          _meta: {
            ui: {
              csp: {
                resourceDomains: ["https://cdn.jsdelivr.net"],
                connectDomains: [],
              },
              prefersBorder: true,
            },
          },
        },
      ],
    };
  }
  throw new Error(`Resource not found: ${uri}`);
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("🦆 Framework Dashboard MCP Server running");
}

main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});
