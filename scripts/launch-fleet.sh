#!/usr/bin/env bash
# PicoCloth 2-Node Fleet Launcher
# Starts Node-A (Curiosity Brain) and Node-B (Executor)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PICOCLOTH_DIR="$(dirname "$SCRIPT_DIR")"
PICOCLAW_BINARY="${PICOCLAW_BINARY:-picoclaw}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${BLUE}[LAUNCH]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERR]${NC} $1"; }
info() { echo -e "${CYAN}[INFO]${NC} $1"; }

check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Go-built picoclaw binary
    if ! command -v "$PICOCLAW_BINARY" &> /dev/null; then
        if [ -f "/tmp/picoclaw/picoclaw" ]; then
            PICOCLAW_BINARY="/tmp/picoclaw/picoclaw"
        else
            error "PicoClaw binary not found!"
            error "Build it first: cd /tmp/picoclaw && export PATH=\$PATH:/usr/local/go/bin && make build"
            exit 1
        fi
    fi
    
    success "PicoClaw binary: $PICOCLAW_BINARY"
    
    # Check API key
    if [ -z "${XAI_API_KEY:-}" ]; then
        warn "XAI_API_KEY not set!"
        warn "Nodes will fail to initialize LLM providers."
        warn "Set it: export XAI_API_KEY=xai-..."
    else
        success "API key configured"
    fi
    
    # Initialize shared memory
    if [ ! -d "${PICOCLOTH_DIR}/shared/project" ]; then
        log "Initializing shared memory..."
        bash "${SCRIPT_DIR}/init-shared-memory.sh"
    fi
    
    # Make hook executable
    chmod +x "${PICOCLOTH_DIR}/hooks/digital_twin_guardian.py" 2>/dev/null || true
    chmod +x "${PICOCLOTH_DIR}/mcp-fleet-server/server.py" 2>/dev/null || true
}

launch_node() {
    local node_id=$1
    local node_dir="${PICOCLOTH_DIR}/${node_id}"
    local home_dir="${node_dir}/home"
    local workspace="${node_dir}/workspace"
    local log_file="${node_dir}/node.log"
    
    log "Launching $node_id..."
    
    # Create home dir and workspace
    mkdir -p "$home_dir" "$workspace"
    
    # Copy config to home dir if not exists
    if [ ! -f "${home_dir}/config.json" ]; then
        cp "${node_dir}/config.json" "${home_dir}/config.json"
        success "Config copied to $node_id home"
    fi
    
    # Set environment for hooks
    export PICOCLAW_HOOK_TWIN_DIR="${PICOCLOTH_DIR}/shared/digital-twins/${node_id}"
    export PICOCLAW_HOOK_PROJECT_DIR="${PICOCLOTH_DIR}/shared/project"
    export PICOCLAW_HOOK_NODE_ID="${node_id}"
    export PICOCLAW_HOOK_MAX_FACTS="8"
    
    # Set Langfuse credentials for observability hook
    if [ -f "${PICOCLOTH_DIR}/shared/state/langfuse-credentials.json" ]; then
        export LANGFUSE_PUBLIC_KEY=$(python3 -c "import json; print(json.load(open('${PICOCLOTH_DIR}/shared/state/langfuse-credentials.json'))['public_key'])" 2>/dev/null)
        export LANGFUSE_SECRET_KEY=$(python3 -c "import json; print(json.load(open('${PICOCLOTH_DIR}/shared/state/langfuse-credentials.json'))['secret_key'])" 2>/dev/null)
    fi
    
    # Launch in background with isolated PICOCLAW_HOME
    (
        export PICOCLAW_HOME="$home_dir"
        export LANGFUSE_PUBLIC_KEY="${LANGFUSE_PUBLIC_KEY:-}"
        export LANGFUSE_SECRET_KEY="${LANGFUSE_SECRET_KEY:-}"
        # Use nohup to survive terminal detachment
        nohup "$PICOCLAW_BINARY" gateway \
            > "$log_file" 2>&1 &
        echo $! > "${node_dir}/pid"
    )
    
    success "$node_id launched (PID: $(cat "${node_dir}/pid" 2>/dev/null || echo "unknown"))"
    info "Logs: tail -f ${log_file}"
}

launch_mcp_fleet_server() {
    log "Launching MCP Fleet Server..."
    
    export FLEET_NODE_ID="fleet-server"
    export FLEET_SHARED_DIR="${PICOCLOTH_DIR}/shared"
    
    nohup python3 "${PICOCLOTH_DIR}/mcp-fleet-server/server.py" \
        > "${PICOCLOTH_DIR}/mcp-fleet-server/server.log" 2>&1 &
    
    echo $! > "${PICOCLOTH_DIR}/mcp-fleet-server/pid"
    success "MCP Fleet Server launched (PID: $(cat "${PICOCLOTH_DIR}/mcp-fleet-server/pid"))"
}

launch_langfuse() {
    if command -v docker-compose &> /dev/null || command -v docker &> /dev/null; then
        log "Launching Langfuse observability stack..."
        cd "${PICOCLOTH_DIR}/langfuse"
        
        if command -v docker-compose &> /dev/null; then
            docker-compose up -d 2>/dev/null || docker compose up -d
        else
            docker compose up -d
        fi
        
        success "Langfuse starting at http://localhost:3000"
        info "Default credentials: Create account on first visit"
    else
        warn "Docker not found. Skipping Langfuse launch."
        warn "Install Docker to enable fleet observability."
    fi
}

stop_all() {
    log "Stopping all PicoCloth services..."
    
    for pid_file in "${PICOCLOTH_DIR}"/*/pid "${PICOCLOTH_DIR}"/*/*/pid; do
        if [ -f "$pid_file" ]; then
            local pid=$(cat "$pid_file")
            local service=$(basename "$(dirname "$pid_file")")
            if kill "$pid" 2>/dev/null; then
                success "Stopped $service (PID: $pid)"
            else
                warn "$service already stopped"
            fi
            rm -f "$pid_file"
        fi
    done
    
    # Stop Langfuse
    if command -v docker-compose &> /dev/null; then
        cd "${PICOCLOTH_DIR}/langfuse" && docker-compose down 2>/dev/null || true
    fi
    
    success "All services stopped"
}

show_dashboard() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║              🪶 PICO CLOTH FLEET DASHBOARD                  ║"
    echo "╠══════════════════════════════════════════════════════════════╣"
    echo "║                                                              ║"
    echo "║  Node-A (Curiosity Brain)  │  Gateway: http://127.0.0.1:18790 ║"
    echo "║  Node-B (Executor)         │  Gateway: http://127.0.0.1:18791 ║"
    echo "║  MCP Fleet Server          │  stdio via config                ║"
    echo "║  Langfuse Observability    │  http://localhost:3000           ║"
    echo "║  Shared Memory             │  ${PICOCLOTH_DIR}/shared/       ║"
    echo "║                                                              ║"
    echo "╠══════════════════════════════════════════════════════════════╣"
    echo "║  COMMANDS:                                                   ║"
    echo "║    ./scripts/orchestrator.sh status     # Fleet health       ║"
    echo "║    ./scripts/orchestrator.sh monitor    # Live monitoring    ║"
    echo "║    tail -f node-a/node.log              # Node-A logs        ║"
    echo "║    tail -f node-b/node.log              # Node-B logs        ║"
    echo "║                                                              ║"
    echo "║  TELEGRAM:                                                   ║"
    echo "║    1. Create bot with @BotFather                             ║"
    echo "║    2. Add token to node config                               ║"
    echo "║    3. Restart node                                           ║"
    echo "║                                                              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
}

# Main
main() {
    case "${1:-start}" in
        start)
            echo "🚀 PicoCloth Fleet Launcher"
            echo "=========================="
            check_prerequisites
            launch_node "node-a"
            launch_node "node-b"
            launch_mcp_fleet_server
            launch_langfuse
            
            sleep 2
            show_dashboard
            
            log "Fleet is launching! Give nodes 5-10 seconds to initialize."
            ;;
        
        stop)
            stop_all
            ;;
        
        restart)
            stop_all
            sleep 2
            main start
            ;;
        
        status)
            bash "${SCRIPT_DIR}/orchestrator.sh" status
            ;;
        
        *)
            echo "PicoCloth Fleet Launcher"
            echo "Usage: $0 {start|stop|restart|status}"
            ;;
    esac
}

main "$@"
