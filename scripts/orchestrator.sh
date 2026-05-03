#!/usr/bin/env bash
# PicoCloth Fleet Orchestrator
# Monitors node health, balances load, manages task queue

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PICOCLOTH_DIR="$(dirname "$SCRIPT_DIR")"
SHARED_DIR="${PICOCLOTH_DIR}/shared"
STATE_DIR="${SHARED_DIR}/state"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')] ORCHESTRATOR:${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%H:%M:%S')] ERROR:${NC} $1"
}

success() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')] SUCCESS:${NC} $1"
}

check_node_health() {
    local node_id=$1
    local port=$2
    
    # Check if gateway is responding
    if curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${port}/health" 2>/dev/null | grep -q "200\|404"; then
        # 404 is fine - PicoClaw might not have /health but is responding
        echo "online"
    else
        echo "offline"
    fi
}

update_node_heartbeat() {
    local node_id=$1
    local status=$2
    local port=$3
    
    local state_file="${STATE_DIR}/fleet-state.json"
    local tmp_file="${STATE_DIR}/fleet-state.json.tmp"
    
    if [ -f "$state_file" ]; then
        python3 -c "
import json, sys
from datetime import datetime, timezone

try:
    with open('$state_file', 'r') as f:
        state = json.load(f)
except:
    state = {'version': '1.0', 'nodes': {}, 'metrics': {}}

if '$node_id' not in state.get('nodes', {}):
    state['nodes']['$node_id'] = {}

state['nodes']['$node_id']['status'] = '$status'
state['nodes']['$node_id']['last_heartbeat'] = datetime.now(timezone.utc).isoformat()
state['nodes']['$node_id']['gateway_port'] = $port
state['last_updated'] = datetime.now(timezone.utc).isoformat()

with open('$tmp_file', 'w') as f:
    json.dump(state, f, indent=2)
" 2>/dev/null && mv "$tmp_file" "$state_file"
    fi
}

process_task_queue() {
    local queue_file="${STATE_DIR}/task-queue.json"
    
    if [ ! -f "$queue_file" ]; then
        return
    fi
    
    python3 -c "
import json
from datetime import datetime, timezone

try:
    with open('$queue_file', 'r') as f:
        queue = json.load(f)
except:
    queue = []

pending = [t for t in queue if t.get('status') == 'pending']
if pending:
    print(f'Found {len(pending)} pending tasks')
    for task in pending[:3]:  # Process max 3 at a time
        print(f\"  - {task['id']} -> {task['target_node']}: {task['task'][:60]}...\")
" 2>/dev/null || true
}

show_fleet_status() {
    log "Fleet Status Report"
    echo "==================="
    
    local state_file="${STATE_DIR}/fleet-state.json"
    if [ -f "$state_file" ]; then
        python3 -c "
import json
with open('$state_file', 'r') as f:
    state = json.load(f)

print(f\"Last Updated: {state.get('last_updated', 'unknown')}\")
print(f\"Nodes: {len(state.get('nodes', {}))}\")
print()
for node_id, info in state.get('nodes', {}).items():
    status = info.get('status', 'unknown')
    emoji = '🟢' if status == 'online' else '🔴' if status == 'offline' else '🟡'
    print(f\"{emoji} {node_id}\")
    print(f\"   Status: {status}\")
    print(f\"   Role: {info.get('role', 'unknown')}\")
    print(f\"   Last Heartbeat: {info.get('last_heartbeat', 'never')}\")
    print(f\"   Active Turns: {info.get('active_turns', 0)}\")
    print(f\"   Daily Tokens: {info.get('daily_tokens_used', 0)}\")
    print()
" 2>/dev/null || echo "State file not readable"
    fi
    
    echo ""
    log "Digital Twins Archive"
    echo "====================="
    for node_dir in "${SHARED_DIR}/digital-twins"/*; do
        if [ -d "$node_dir" ]; then
            local count=$(find "$node_dir" -name "*.json" | wc -l)
            local node_name=$(basename "$node_dir")
            echo "  📦 $node_name: $count twins"
        fi
    done
    
    echo ""
    log "Shared Memory Stats"
    echo "==================="
    echo "  📁 Doctrine: $(find "${SHARED_DIR}/doctrine" -type f | wc -l) files"
    echo "  📁 Project:  $(find "${SHARED_DIR}/project" -type f | wc -l) files"
    echo "  📁 State:    $(find "${SHARED_DIR}/state" -type f | wc -l) files"
    echo "  📁 Run:      $(find "${SHARED_DIR}/run" -type f 2>/dev/null | wc -l) ephemeral"
}

# Main orchestrator loop
main() {
    log "Starting PicoCloth Fleet Orchestrator"
    log "Shared Directory: $SHARED_DIR"
    
    # Ensure shared memory exists
    if [ ! -d "$SHARED_DIR" ]; then
        error "Shared memory not initialized. Run init-shared-memory.sh first!"
        exit 1
    fi
    
    case "${1:-status}" in
        status)
            # Check Node-A (port 18790)
            local node_a_status=$(check_node_health "node-a" "18790")
            update_node_heartbeat "node-a" "$node_a_status" "18790"
            
            # Check Node-B (port 18791)
            local node_b_status=$(check_node_health "node-b" "18791")
            update_node_heartbeat "node-b" "$node_b_status" "18791"
            
            show_fleet_status
            ;;
        
        monitor)
            log "Starting continuous monitoring (Ctrl+C to stop)..."
            while true; do
                local node_a_status=$(check_node_health "node-a" "18790")
                update_node_heartbeat "node-a" "$node_a_status" "18790"
                
                local node_b_status=$(check_node_health "node-b" "18791")
                update_node_heartbeat "node-b" "$node_b_status" "18791"
                
                process_task_queue
                
                # Print compact status line
                local a_emoji=$( [ "$node_a_status" = "online" ] && echo "🟢" || echo "🔴" )
                local b_emoji=$( [ "$node_b_status" = "online" ] && echo "🟢" || echo "🔴" )
                echo -ne "\r$(date '+%H:%M:%S') | ${a_emoji} Node-A | ${b_emoji} Node-B | Queue: $(python3 -c "import json; q=json.load(open('${STATE_DIR}/task-queue.json')); print(len([t for t in q if t.get('status')=='pending'])))" 2>/dev/null || echo "?") pending    "
                
                sleep 5
            done
            ;;
        
        delegate)
            local target="${2:-}"
            local task="${3:-}"
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

task_id = f\"task-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}\"
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

print(f'Task queued: {task_id} -> {target}')
"
            success "Task delegated to $target"
            ;;
        
        *)
            echo "PicoCloth Fleet Orchestrator"
            echo "Usage: $0 {status|monitor|delegate <node> <task>}"
            echo ""
            echo "Commands:"
            echo "  status              Show full fleet status report"
            echo "  monitor             Continuous monitoring loop"
            echo "  delegate <n> <t>    Queue a task for a node"
            ;;
    esac
}

main "$@"
