#!/usr/bin/env bash
# PicoCloth 10-Node Fleet Launcher
# Launches Node-A through Node-J

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PICOCLOTH_DIR="$(dirname "$SCRIPT_DIR")"
PICOCLAW_BINARY="${PICOCLAW_BINARY:-/tmp/picoclaw/picoclaw}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

log() { echo -e "${BLUE}[LAUNCH]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERR]${NC} $1"; }
info() { echo -e "${CYAN}[INFO]${NC} $1"; }

NODES=(node-a node-b node-c node-d node-e node-f node-g node-h node-i node-j)
PORTS=(18790 18791 18792 18793 18794 18795 18796 18797 18798 18799)

stop_all() {
    log "Stopping all PicoCloth services..."
    for pid_file in "$PICOCLOTH_DIR"/*/pid; do
        if [ -f "$pid_file" ]; then
            local pid=$(cat "$pid_file" 2>/dev/null || echo "")
            local service=$(basename "$(dirname "$pid_file")")
            if [ -n "$pid" ] && kill "$pid" 2>/dev/null; then
                success "Stopped $service (PID: $pid)"
            fi
            rm -f "$pid_file"
        fi
    done
    success "All services stopped"
}

launch_node() {
    local node_id=$1
    local node_dir="${PICOCLOTH_DIR}/${node_id}"
    local home_dir="${node_dir}/home"
    local workspace="${node_dir}/workspace"
    local log_file="${node_dir}/node.log"
    
    log "Launching $node_id..."
    mkdir -p "$home_dir" "$workspace"
    
    if [ ! -f "${home_dir}/config.json" ]; then
        cp "${node_dir}/config.json" "${home_dir}/config.json"
    fi
    
    export PICOCLAW_HOOK_TWIN_DIR="${PICOCLOTH_DIR}/shared/digital-twins/${node_id}"
    export PICOCLAW_HOOK_PROJECT_DIR="${PICOCLOTH_DIR}/shared/project"
    export PICOCLAW_HOOK_NODE_ID="${node_id}"
    export PICOCLAW_HOOK_MAX_FACTS="8"
    
    (
        export PICOCLAW_HOME="$home_dir"
        nohup "$PICOCLAW_BINARY" gateway > "$log_file" 2>&1 &
        echo $! > "${node_dir}/pid"
    )
    
    success "$node_id launched (PID: $(cat "${node_dir}/pid" 2>/dev/null || echo "unknown"))"
}

launch_mcp_fleet_server() {
    log "Launching MCP Fleet Server..."
    export FLEET_NODE_ID="fleet-server"
    export FLEET_SHARED_DIR="${PICOCLOTH_DIR}/shared"
    nohup python3 "${PICOCLOTH_DIR}/mcp-fleet-server/server.py" > "${PICOCLOTH_DIR}/mcp-fleet-server/server.log" 2>&1 &
    echo $! > "${PICOCLOTH_DIR}/mcp-fleet-server/pid"
    success "MCP Fleet Server launched (PID: $(cat "${PICOCLOTH_DIR}/mcp-fleet-server/pid"))"
}

show_dashboard() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════════╗"
    echo "║           🪶 PICO CLOTH 10-NODE FLEET DASHBOARD                     ║"
    echo "╠══════════════════════════════════════════════════════════════════════╣"
    echo "║                                                                      ║"
    for i in "${!NODES[@]}"; do
        local node="${NODES[$i]}"
        local port="${PORTS[$i]}"
        printf "║  %-10s │ Port: %-5s │ http://127.0.0.1:%s\n" "$node" "$port" "$port"
    done
    echo "║  MCP Fleet Server │ stdio transport via config                        ║"
    echo "║  Langfuse         │ http://localhost:3000                             ║"
    echo "║  Shared Memory    │ ${PICOCLOTH_DIR}/shared/                         ║"
    echo "║                                                                      ║"
    echo "╠══════════════════════════════════════════════════════════════════════╣"
    echo "║  COMMANDS:                                                           ║"
    echo "║    ./scripts/orchestrator.sh status     # Full fleet health          ║"
    echo "║    ./scripts/orchestrator.sh monitor    # Live monitoring            ║"
    echo "║    tail -f node-*/node.log              # Node logs                  ║"
    echo "╚══════════════════════════════════════════════════════════════════════╝"
    echo ""
}

main() {
    case "${1:-start}" in
        start)
            echo "🚀 PicoCloth 10-Node Fleet Launcher"
            echo "===================================="
            
            if ! command -v "$PICOCLAW_BINARY" &> /dev/null; then
                error "PicoClaw binary not found at $PICOCLAW_BINARY"
                exit 1
            fi
            
            for node_id in "${NODES[@]}"; do
                launch_node "$node_id"
                sleep 0.5
            done
            
            launch_mcp_fleet_server
            
            sleep 2
            show_dashboard
            log "Fleet launching! Give nodes 10-15 seconds to initialize."
            ;;
        
        stop)
            stop_all
            ;;
        
        restart)
            stop_all
            sleep 2
            main start
            ;;
        
        *)
            echo "Usage: $0 {start|stop|restart}"
            ;;
    esac
}

main "$@"
