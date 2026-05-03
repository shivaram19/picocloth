#!/usr/bin/env bash
# PicoCloth 10-Node Fleet Orchestrator
# Uses tmux for process management + direct HTTP health checks

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PICOCLOTH_DIR="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

NODES=(node-a node-b node-c node-d node-e node-f node-g node-h node-i node-j)
PORTS=(18790 18791 18792 18793 18794 18795 18796 18797 18798 18799)
ROLES=("Curiosity Brain" "Executor Builder" "Memory Guardian" "Safety Auditor" "Document Parser" "Contradiction Detector" "RFI Drafter" "Knowledge Graph" "Fleet Router" "Metrics Collector")

check_health() {
    local port=$1
    if curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${port}/health" 2>/dev/null | grep -q "200\|404"; then
        echo "online"
    else
        echo "offline"
    fi
}

show_dashboard() {
    clear 2>/dev/null || true
    echo "╔════════════════════════════════════════════════════════════════════════════╗"
    echo "║           🪶 PICO CLOTH 10-NODE FLEET — ORCHESTRATOR                      ║"
    echo "╠════════════════════════════════════════════════════════════════════════════╣"
    echo "║                                                                            ║"
    
    local online=0
    local offline=0
    
    for i in "${!NODES[@]}"; do
        local status=$(check_health "${PORTS[$i]}")
        local emoji="🟢"
        local color="$GREEN"
        if [ "$status" = "offline" ]; then
            emoji="🔴"
            color="$RED"
            ((offline++))
        else
            ((online++))
        fi
        
        printf "║  %b%-10s%b │ %-22s │ Port %-5s │ %b%-6s%b │ tmux %-3s  ║\n" \
            "$color" "${NODES[$i]}" "$NC" "${ROLES[$i]}" "${PORTS[$i]}" "$color" "$status" "$NC" \
            "$(tmux has-session -t "${NODES[$i]}" 2>/dev/null && echo "✅" || echo "❌")"
    done
    
    echo "║                                                                            ║"
    echo "╠════════════════════════════════════════════════════════════════════════════╣"
    printf  "║  Fleet Health: %b%-2s online%b / %b%-2s offline%b / 10 total                    ║\n" "$GREEN" "$online" "$NC" "$RED" "$offline" "$NC"
    echo "╠════════════════════════════════════════════════════════════════════════════╣"
    echo "║  COMMANDS:                                                                 ║"
    echo "║    fleet status              → Show this dashboard                         ║"
    echo "║    fleet monitor             → Live monitoring loop                        ║"
    echo "║    fleet exec <node> <cmd>   → Run command on node via tmux                ║"
    echo "║    fleet msg <node> <msg>    → Send message to node via picoclaw           ║"
    echo "║    fleet restart <node>      → Restart a specific node                     ║"
    echo "║    fleet stop <node>         → Stop a specific node                        ║"
    echo "║    fleet logs <node>         → Tail node logs                              ║"
    echo "║    fleet broadcast <msg>     → Send message to ALL nodes                   ║"
    echo "╚════════════════════════════════════════════════════════════════════════════╝"
}

monitor_loop() {
    while true; do
        show_dashboard
        sleep 5
    done
}

exec_on_node() {
    local node=$1
    shift
    tmux send-keys -t "$node" "$*" Enter
    echo "Command sent to $node: $*"
}

send_message() {
    local node=$1
    local msg="${2:-}"
    if [ -z "$msg" ]; then
        echo "Usage: fleet msg <node> <message>"
        return 1
    fi
    cd "$PICOCLOTH_DIR"
    bash scripts/talk-to-fleet.sh "$node" "$msg" 2>&1 | tail -20
}

restart_node() {
    local node=$1
    tmux kill-session -t "$node" 2>/dev/null || true
    sleep 1
    
    tmux new-session -d -s "$node" \
        -e "PICOCLAW_HOME=${PICOCLOTH_DIR}/${node}/home" \
        -e "PICOCLAW_HOOK_TWIN_DIR=${PICOCLOTH_DIR}/shared/digital-twins/${node}" \
        -e "PICOCLAW_HOOK_PROJECT_DIR=${PICOCLOTH_DIR}/shared/project" \
        -e "PICOCLAW_HOOK_NODE_ID=${node}" \
        -e "PICOCLAW_HOOK_MAX_FACTS=8" \
        -c "${PICOCLOTH_DIR}" \
        "/tmp/picoclaw/picoclaw gateway"
    echo "🔄 $node restarted"
}

stop_node() {
    local node=$1
    tmux kill-session -t "$node" 2>/dev/null || true
    echo "🛑 $node stopped"
}

show_logs() {
    local node=$1
    local log="${PICOCLOTH_DIR}/${node}/node.log"
    if [ -f "$log" ]; then
        tail -30 "$log"
    else
        echo "No log found for $node"
    fi
}

broadcast() {
    local msg="${1:-}"
    if [ -z "$msg" ]; then
        echo "Usage: fleet broadcast <message>"
        return 1
    fi
    for node in "${NODES[@]}"; do
        echo "→ Sending to $node..."
        cd "$PICOCLOTH_DIR"
        bash scripts/talk-to-fleet.sh "$node" "$msg" 2>&1 | tail -5 &
    done
    wait
    echo "Broadcast complete"
}

case "${1:-status}" in
    status)
        show_dashboard
        ;;
    monitor)
        monitor_loop
        ;;
    exec)
        exec_on_node "$2" "${@:3}"
        ;;
    msg|message)
        send_message "$2" "${*:3}"
        ;;
    restart)
        restart_node "$2"
        ;;
    stop)
        stop_node "$2"
        ;;
    logs)
        show_logs "$2"
        ;;
    broadcast)
        broadcast "${*:2}"
        ;;
    *)
        echo "PicoCloth Fleet Orchestrator"
        echo "Usage: fleet {status|monitor|exec <node> <cmd>|msg <node> <msg>|restart <node>|stop <node>|logs <node>|broadcast <msg>}"
        ;;
esac
