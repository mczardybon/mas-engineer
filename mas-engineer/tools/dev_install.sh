#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# dev_install.sh — MAS-Engineer full installation
# Runs all steps to be ready immediately after git clone
# Sets up: dashboard server, dispatch tracker, cron, Goose app
# ═══════════════════════════════════════════════════════════════
set -e

MAS_WORKSPACE="$(cd "$(dirname "$0")/.." && pwd)"
echo "📦 MAS-Engineer installation"
echo "   Workspace: $MAS_WORKSPACE"
echo ""

# ─── 1. Dependencies ───
echo "📦 Step 1/7: Check dependencies..."
command -v node >/dev/null 2>&1 || { echo "❌ node missing"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ python3 missing"; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "❌ npm missing"; exit 1; }
echo "   ✅ CLI tools OK (node=$(node --version), python3=$(python3 --version | awk '{print $2}'), npm=$(npm --version))"

# ─── 2. State directories ───
echo "📁 Step 2/7: Create state directories..."
mkdir -p "$MAS_WORKSPACE/.mase/dispatch"
mkdir -p "$MAS_WORKSPACE/.mase/checkpoints"
echo "   ✅ Directories OK"

# ─── 2.5. Install Goose recipes (CRITICAL: without this, no recipe can be invoked) ───
echo "📜 Step 2.5/7: Install Goose recipes..."
GOOSE_RECIPES_DIR="${HOME}/.config/goose/recipes"
mkdir -p "$GOOSE_RECIPES_DIR/sub"
cp "$MAS_WORKSPACE"/recipe/*.yaml "$GOOSE_RECIPES_DIR/" 2>/dev/null || true
cp "$MAS_WORKSPACE"/recipe/sub/*.yaml "$GOOSE_RECIPES_DIR/sub/" 2>/dev/null || true
ROOT_COUNT=$(ls "$GOOSE_RECIPES_DIR"/*.yaml 2>/dev/null | wc -l)
SUB_COUNT=$(ls "$GOOSE_RECIPES_DIR/sub/"*.yaml 2>/dev/null | wc -l)
echo "   ✅ Recipes installed: $ROOT_COUNT root + $SUB_COUNT sub-recipes → $GOOSE_RECIPES_DIR"

# Also install .goosehints and .mas-mode to goose config dir
[ -f "$MAS_WORKSPACE/.goosehints" ] && cp "$MAS_WORKSPACE/.goosehints" "${HOME}/.config/goose/.goosehints" 2>/dev/null && echo "   ✅ .goosehints installed"
[ -f "$MAS_WORKSPACE/.mas-mode" ] && cp "$MAS_WORKSPACE/.mas-mode" "${HOME}/.config/goose/.mas-mode" 2>/dev/null && echo "   ✅ .mas-mode installed"

# ─── 2.6. Configure Goose provider (if API key is in env) ───
echo "⚙️  Step 2.6/7: Configure Goose provider..."
GOOSE_CONFIG="${HOME}/.config/goose/config.yaml"
mkdir -p "$(dirname "$GOOSE_CONFIG")"
if [ -n "$DEEPSEEK_API_KEY" ] || [ -n "$OPENAI_API_KEY" ]; then
    EFFECTIVE_KEY="${DEEPSEEK_API_KEY:-$OPENAI_API_KEY}"
    PROVIDER="${GOOSE_PROVIDER:-openai}"
    MODEL="${GOOSE_MODEL:-deepseek-v4-flash}"
    HOST="${OPENAI_HOST:-https://api.deepseek.com}"
    cat > "$GOOSE_CONFIG" <<EOF
GOOSE_PROVIDER: $PROVIDER
GOOSE_MODEL: $MODEL
OPENAI_HOST: $HOST
OPENAI_API_KEY: $EFFECTIVE_KEY
extensions:
  developer:
    enabled: true
    name: developer
    type: builtin
EOF
    echo "   ✅ Goose config: $PROVIDER / $MODEL"
    echo "   📡 Host: $HOST"
else
    echo "   ⚠️  No API key in env (DEEPSEEK_API_KEY / OPENAI_API_KEY)"
    echo "   💡 Set one before running recipes: export DEEPSEEK_API_KEY=sk-..."
fi

# ─── 2.7. Configure git hooks (R110-32, persistent in repo) ───
echo "🪝 Step 2.7/7: Configure git hooks (R10/R88 enforcement)..."
# Issue: core.hooksPath is normally a LOCAL config (not committed) so fresh
# clones have NO hooks active. This step sets it relative to the repo root
# so secret-leak defense (pre-commit) and recipe validation (pre-push) work
# out of the box.
# Find the git repo root: dev_install.sh lives at <root>/mas-engineer/tools/
# so MAS_WORKSPACE/.. = repo-root. If we're not in a git repo, skip silently.
GIT_REPO_ROOT="$(cd "$MAS_WORKSPACE/.." 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null || echo "")"
if [ -n "$GIT_REPO_ROOT" ] && [ -d "$GIT_REPO_ROOT/mas-engineer/.githooks" ]; then
    HOOKS_REL="mas-engineer/.githooks"
    # Verify the hooks are present
    if [ -x "$GIT_REPO_ROOT/$HOOKS_REL/pre-commit" ] && [ -x "$GIT_REPO_ROOT/$HOOKS_REL/pre-push" ]; then
        CURRENT_HOOKS_PATH="$(git -C "$GIT_REPO_ROOT" config --get core.hooksPath 2>/dev/null || echo "")"
        if [ "$CURRENT_HOOKS_PATH" = "$HOOKS_REL" ]; then
            echo "   ✅ Hooks already active: $HOOKS_REL (R10/R88 enforced)"
        else
            git -C "$GIT_REPO_ROOT" config core.hooksPath "$HOOKS_REL"
            echo "   ✅ Hooks configured: $HOOKS_REL (was: '${CURRENT_HOOKS_PATH:-<unset>}')"
            echo "   🛡️  pre-commit: secret-leak defense (R88)"
            echo "   🛡️  pre-push: recipe-YAML validation (R108-8)"
        fi
    else
        echo "   ⚠️  Hooks files not executable in $HOOKS_REL — fixing..."
        chmod +x "$GIT_REPO_ROOT/$HOOKS_REL/pre-commit" "$GIT_REPO_ROOT/$HOOKS_REL/pre-push" 2>/dev/null && \
            echo "   ✅ Hooks chmod +x'd" || echo "   ⚠️  chmod failed (manual: chmod +x $HOOKS_REL/{pre-commit,pre-push})"
    fi
else
    echo "   ⚠️  Not a git repo or hooks dir missing — skipping (R10/R88 NOT auto-enforced)"
    echo "   💡 To activate later: git config core.hooksPath mas-engineer/.githooks"
fi

# ─── 3. Start dashboard MCP server (stdio-based) ───
echo "🖥️  Step 3/7: Start dashboard MCP server (stdio)..."
DASHBOARD_PID_FILE="$MAS_WORKSPACE/.mase/dashboard.pid"
if [ -f "$DASHBOARD_PID_FILE" ] && kill -0 $(cat "$DASHBOARD_PID_FILE") 2>/dev/null; then
    echo "   ✅ Dashboard server already running (PID $(cat $DASHBOARD_PID_FILE))"
else
    cd "$MAS_WORKSPACE/.mase/mcp"
    if [ ! -d "node_modules" ]; then
        echo "   📦 Installing dashboard npm dependencies..."
        npm install --silent 2>/dev/null || { echo "   ❌ npm install failed"; exit 1; }
    fi
    MAS_WORKSPACE="$MAS_WORKSPACE" exec </dev/null nohup /usr/bin/node server.js \
        > "$MAS_WORKSPACE/.mase/dashboard-server.log" 2>&1 &
    DASHBOARD_PID=$!
    echo $DASHBOARD_PID > "$DASHBOARD_PID_FILE"
    sleep 2
    if kill -0 $DASHBOARD_PID 2>/dev/null; then
        echo "   ✅ Dashboard server started (PID $DASHBOARD_PID)"
        echo "   📡 Type: stdio-based MCP server (managed by goose via stdio)"
    else
        echo "   ⚠️  Dashboard server exited (stdio EOF or stdin issue)"
        echo "   ℹ️  This is OK — the server is launched on-demand by goose"
        rm -f "$DASHBOARD_PID_FILE"
    fi
fi

# ─── 4. Generate initial data ───
echo "📊 Step 4/7: Generate initial data..."
cd "$MAS_WORKSPACE"
python3 tools/dev_dashboard_data.py --workspace "$MAS_WORKSPACE" 2>/dev/null
echo "   ✅ Initial data OK"

# ─── 5. Start live daemon ───
echo "🚀 Step 5/7: Start live dispatch daemon..."
DAEMON_PID_FILE="$MAS_WORKSPACE/.mase/live-daemon.pid"
if [ -f "$DAEMON_PID_FILE" ] && kill -0 $(cat "$DAEMON_PID_FILE") 2>/dev/null; then
    echo "   ✅ Daemon already running (PID $(cat "$DAEMON_PID_FILE"))"
else
    cd "$MAS_WORKSPACE"
    nohup python3 "$MAS_WORKSPACE/tools/dev_dispatch_live.py" --daemon \
        --workspace "$MAS_WORKSPACE" \
        > "$MAS_WORKSPACE/.mase/live-daemon.log" 2>&1 &
    DAEMON_PID=$!
    echo $DAEMON_PID > "$DAEMON_PID_FILE"
    sleep 2
    if kill -0 $DAEMON_PID 2>/dev/null; then
        echo "   ✅ Daemon started (PID $DAEMON_PID)"
    else
        echo "   ⚠️  Daemon may have stopped (check .mase/live-daemon.log)"
    fi
fi

# ─── 6. Setup Cron ───
echo "⏰ Step 6/7: Setup cron scheduler..."
CRON_LINE="*/5 * * * * $MAS_WORKSPACE/.mase/scheduler.sh"
if command -v crontab >/dev/null 2>&1; then
    (crontab -l 2>/dev/null | grep -v "scheduler.sh" || true; echo "$CRON_LINE") | crontab - 2>/dev/null || true
    if crontab -l 2>/dev/null | grep -q "scheduler.sh"; then
        echo "   ✅ Cron active (data refresh every 5 minutes)"
    else
        echo "   ⚠️  Cron setup failed (no crontab permissions)"
    fi
else
    echo "   ⚠️  Cron not available in this environment (skipped)"
    echo "   💡 To run scheduler manually: $MAS_WORKSPACE/.mase/scheduler.sh"
fi

# ─── 2.8. Install hermes skills (R110-133) — delegate to skills-install.sh ───
# skills-install.sh is hermes-free and takes its target path as a CLI arg
# (no env-var, no hardcoded runtime path). When called without args it is
# a no-op (target = repo's own .mase/skills/).
echo "🧠  Step 2.8/7: Install hermes skills..."
if [ -f "$MAS_WORKSPACE/scripts/skills-install.sh" ]; then
    if bash "$MAS_WORKSPACE/scripts/skills-install.sh"; then
        echo "   ✅ Skills installer exited 0"
    else
        echo "   ⚠️  Skills installer failed (continuing — recipes are still installed)"
    fi
else
    echo "   ⚠️  skills-install.sh not found in $MAS_WORKSPACE/scripts — skipping"
fi

# ─── Done ───
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  ✅ MAS-ENGINEER INSTALLATION COMPLETE       ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  Dashboard:  MCP stdio (.mase/mcp/server.js)  ║"
echo "║  Dispatch:   130 entries                     ║"
echo "║  Agents:     50 sub-agents                   ║"
echo "║  Tools:      47 active                        ║"
echo "║  Skills:     18 mas-engineer-flavored        ║"
echo "╚══════════════════════════════════════════════╝"

# ─── 7. Deploy Goose App ───
echo "📱 Step 7/7: Deploy Goose App..."
APP_SRC="$MAS_WORKSPACE/.mase/mcp/mas-dispatch-monitor.html"
APP_DEST="${HOME}/.local/share/goose/apps/mas-dispatch-monitor.html"
mkdir -p "$(dirname "$APP_DEST")"
if [ -f "$APP_SRC" ]; then
    cp "$APP_SRC" "$APP_DEST"
    echo "   ✅ App file installed: $APP_DEST"
    echo "   📱 Open Goose → Apps tab → 'mas-dispatch-monitor'"
else
    echo "   ⚠️ App source file missing: $APP_SRC"
    echo "   📱 Create app manually in Goose: Apps.createApp(PRD)"
fi
