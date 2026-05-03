#!/usr/bin/env bash
# PicoCloth 10-Node Fleet Orchestrator

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PICOCLOTH_DIR="$(dirname "$SCRIPT_DIR")"
SHARED_DIR="${PICOCLOTH_DIR}/shared"
STATE_DIR="${SHARED_DIR}/state"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

log() { echo -e "${BLUE}[$(date '+%H:%M:%S')] ORCHESTRATOR:${NC} $1"; }
success() { echo -e "${GREEN}[$(date '+%H:%M:%S')] SUCCESS:${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARNING:${NC} $1"; }
error() { echo -e "${RED}[$(date '+%H:%M:%S')] ERROR:${NC} $1"; }

NODES=(node-a node-b node-c node-d node-e node-f node-g node-h node-i node-j)
PORTS=(18790 18791 18792 18793 18794 18795 18796 18797 18798 18799)
ROLES=("Curiosity Brain" "Executor Builder" "Memory Guardian" "Safety Auditor" "Document Parser" "Contradiction Detector" "RFI Drafter" "Knowledge Graph" "Fleet Router" "Metrics Collector")

check_node_health() {
    local port=$1
    if curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${port}/health" 2>/dev/null | grep -q "200\|404"; then
        echo "online"
    else
        echo "offline"
    fi
}

update_heartbeat() {
    local node_id=$1
    local status=$2
    local port=$3
    local state_file="${STATE_DIR}/fleet-state.json"
    local tmp_file="${STATE_DIR}/fleet-state.json.tmp"
    
    python3 -c "
import json, sys
from datetime import datetime, timezone

try:
    with open('$state_file', 'r') as f:
        state = json.load(f)
except:
    state = {'version': '2.0', 'nodes': {}, 'metrics': {}}

if '$node_id' not in state.get('nodes', {}):
    state['nodes']['$node_id'] = {}

state['nodes']['$node_id']['status'] = '$status'
state['nodes']['$node_id']['last_heartbeat'] = datetime.now(timezone.utc).isoformat()
state['nodes']['$node_id']['gateway_port'] = $port
state['last_updated'] = datetime.now(timezone.utc).isoformat()

with open('$tmp_file', 'w') as f:
    json.dump(state, f, indent=2)
" 2>/dev/null && mv "$tmp_file" "$state_file" 2>/dev/null || true
}

show_status() {
    log "PicoCloth 10-Node Fleet Status"
    echo "================================"
    
    local state_file="${STATE_DIR}/fleet-state.json"
    
    printf "%-10s │ %-20s │ %-6s │ %-8s │ %s\n" "NODE" "ROLE" "PORT" "STATUS" "LAST HEARTBEAT"
    echo "───────────┼──────────────────────┼────────┼──────────┼──────────────────────────"
    
    for i in "${!NODES[@]}"; do
        local node="${NODES[$i]}"
        local port="${PORTS[$i]}"
        local role="${ROLES[$i]}"
        local status=$(check_node_health "$port")
        
        update_heartbeat "$node" "$status" "$port"
        
        if [ "$status" = "online" ]; then
            printf "${GREEN}%-10s${NC} │ %-20s │ %-6s │ ${GREEN}%-8s${NC} │ %s\n" "$node" "$role" "$port" "ONLINE" "$(date '+%H:%M:%S')"
        else
            printf "${RED}%-10s${NC} │ %-20s │ %-6s │ ${RED}%-8s${NC} │ %s\n" "$node" "$role" "$port" "OFFLINE" "-"
        fi
    done
    
    echo ""
    log "Digital Twins Archive"
    echo "====================="
    for node_dir in "${SHARED_DIR}/digital-twins"/*; do
        if [ -d "$node_dir" ]; then
            local count=$(find "$node_dir" -name "*.json" 2>/dev/null | wc -l)
            local name=$(basename "$node_dir")
            echo "  📦 $name: $count twins"
        fi
    done
    
    echo ""
    log "Shared Memory Stats"
    echo "==================="
    echo "  📁 Doctrine: $(find "${SHARED_DIR}/doctrine" -type f 2>/dev/null | wc -l) files"
    echo "  📁 Project:  $(find "${SHARED_DIR}/project" -type f 2>/dev/null | wc -l) files"
    echo "  📁 State:    $(find "${SHARED_DIR}/state" -type f 2>/dev/null | wc -l) files"
    echo "  📁 Run:      $(find "${SHARED_DIR}/run" -type f 2>/dev/null | wc -l) ephemeral"
    
    echo ""
    log "Task Queue"
    echo "=========="
    python3 -c "
import json
try:
    with open('${STATE_DIR}/task-queue.json', 'r') as f:
        q = json.load(f)
    pending = [t for t in q if t.get('status') == 'pending']
    print(f'  Pending tasks: {len(pending)}')
    for t in pending[:5]:
        print(f'    - {t[\"id\"]} -> {t[\"target_node\"]}: {t[\"task\"][:50]}...')
except Exception as e:
    print(f'  Queue empty or unreadable ({e})')
" 2>/dev/null || echo "  Queue status unknown"
}

monitor_loop() {
    log "Starting continuous monitoring (Ctrl+C to stop)..."
    while true; do
        local online=0
        local offline=0
        
        for i in "${!NODES[@]}"; do
            local status=$(check_node_health "${PORTS[$i]}")
            update_heartbeat "${NODES[$i]}" "$status" "${PORTS[$i]}"
            if [ "$status" = "online" ]; then
                ((online++))
            else
                ((offline++))
            fi
        done
        
        local pending=$(python3 -c "import json; q=json.load(open('${STATE_DIR}/task-queue.json')); print(len([t for t in q if t.get('status')=='pending']))" 2>/dev/null || echo "0")
        
        echo -ne "\r$(date '+%H:%M:%S') | 🟢 $online online | 🔴 $offline offline | 📋 $pending pending    "
        sleep 5
    done
}

delegate_task() {
    local target="${1:-}"
    local task="${2:-}"
    if [ -z "$target" ] || [ -z "$task" ]; then
        error "Usage: orchestrator.sh delegate <node-id> <task-description>"
        exit 1
    fi
    
    python3 -c "
import json
from datetime import datetime, timezone

queue_file = '${STATE_DIR}/task-queue.json'
try:
    with open(queue_file, 'r') as f:
        queue = json.load(f)
except:
    queue = []

task_id = f'task-{datetime.now(timezone.utc).strftime(\"%Y%m%d-%H%M%S\")}'
queue.append({
    'id': task_id,
    'target_node': '$target',
    'task': '$task',
    'priority': 'normal',
    'status': 'pending',
    'created_at': datetime.now(timezone.utc).isoformat(),
    'result': None
})

with open(queue_file, 'w') as f:
    json.dump(queue, f, indent=2)

print(f'Task queued: {task_id} -> $target')
"
    success "Task delegated to $target"
}

broadcast_task() {
    local task="${1:-}"
    if [ -z "$task" ]; then
        error "Usage: orchestrator.sh broadcast <task-description>"
        exit 1
    fi
    
    for node in "${NODES[@]}"; do
        delegate_task "$node" "$task"
    done
    success "Broadcasted to all 10 nodes"
}

main() {
    case "${1:-status}" in
        status)
            show_status
            ;;
        monitor)
            monitor_loop
            ;;
        delegate)
            delegate_task "$2" "$3"
            ;;
        broadcast)
            broadcast_task "$2"
            ;;
        *)
            echo "PicoCloth 10-Node Fleet Orchestrator"
            echo "Usage: $0 {status|monitor|delegate <node> <task>|broadcast <task>}"
            echo ""
            echo "Commands:"
            echo "  status                  Show full fleet status report"
            echo "  monitor                 Continuous monitoring loop"
            echo "  delegate <n> <t>        Queue a task for a specific node"
            echo "  broadcast <t>           Queue a task for ALL nodes"
            ;;
    esac
}

main "$@"
