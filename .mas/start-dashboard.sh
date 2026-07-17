#!/bin/bash
# Start the MAS Dashboard HTTP server
MAS_WORKSPACE="$(cd "$(dirname "$0")/.." && pwd)"
NODE="${NODE:-node}"
SERVER="$MAS_WORKSPACE/.mas/mcp/server.js"
PORT=3000

# Kill existing instances
pkill -f "server.js" 2>/dev/null
sleep 1

# Start server
export MAS_WORKSPACE
$NODE $SERVER &
echo "Dashboard server started on http://localhost:$PORT"
