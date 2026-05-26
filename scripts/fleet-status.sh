#!/bin/bash
# fleet-status.sh
# Shows running status of all fleet nodes

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PIDS_FILE="$PROJECT_ROOT/.fleet-pids"

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║              PicoCloth Fleet Status                       ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

if [[ ! -f "$PIDS_FILE" ]]; then
  echo "   ⚠️  No fleet running (.fleet-pids not found)"
  echo "   Run: ./scripts/launch-consultants.sh"
  exit 0
fi

NODES=(
  "consultant-academic:18797:Research & Knowledge"
  "consultant-growth:18801:Growth & Strategy"
  "consultant-solutions:18802:AI Solutions"
  "consultant-trainer:18803:Training & Education"
  "curious-kimi:18804:Question Engine"
)

printf "  %-22s %-8s %-10s %s\n" "NODE" "PORT" "STATUS" "ROLE"
printf "  %s\n" "───────────────────────────────────────────────────────"

RUNNING=0
STOPPED=0

for entry in "${NODES[@]}"; do
  IFS=: read -r node port role <<< "$entry"
  
  # Check if any PID in .fleet-pids is still alive
  ALIVE=false
  while read -r pid; do
    if kill -0 "$pid" 2>/dev/null; then
      ALIVE=true
      break
    fi
  done < "$PIDS_FILE"
  
  if $ALIVE; then
    printf "  %-22s %-8s %-10s %s\n" "$node" "$port" "🟢 running" "$role"
    ((RUNNING++))
  else
    printf "  %-22s %-8s %-10s %s\n" "$node" "$port" "🔴 stopped" "$role"
    ((STOPPED++))
  fi
done

echo ""
echo "  Running: $RUNNING | Stopped: $STOPPED"

# Show last log line per node
if [[ -d "$PROJECT_ROOT/logs" ]]; then
  echo ""
  echo "  Last heartbeat:"
  for entry in "${NODES[@]}"; do
    IFS=: read -r node port role <<< "$entry"
    LOG="$PROJECT_ROOT/logs/${node}.log"
    if [[ -f "$LOG" ]]; then
      LAST=$(tail -1 "$LOG" 2>/dev/null || echo "no logs")
      printf "    %-22s %s\n" "$node:" "$LAST"
    fi
  done
fi

echo ""
