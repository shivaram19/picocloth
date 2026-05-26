#!/bin/bash
# stop-fleet.sh
# Gracefully stops all fleet nodes

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PIDS_FILE="$PROJECT_ROOT/.fleet-pids"

if [[ ! -f "$PIDS_FILE" ]]; then
  echo "No fleet appears to be running (.fleet-pids not found)"
  exit 0
fi

echo "🛑 Stopping PicoCloth consultant fleet..."

while read -r pid; do
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null && echo "   ✅ Stopped PID $pid" || echo "   ⚠️  Failed to stop PID $pid"
  else
    echo "   ⚠️  PID $pid already dead"
  fi
done < "$PIDS_FILE"

rm -f "$PIDS_FILE"

# Update fleet state
if [[ -f "$PROJECT_ROOT/shared/state/fleet-state.json" ]]; then
  jq '.status = "stopped" | .stopped_at = "'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'"' \
    "$PROJECT_ROOT/shared/state/fleet-state.json" > "$PROJECT_ROOT/shared/state/fleet-state.json.tmp"
  mv "$PROJECT_ROOT/shared/state/fleet-state.json.tmp" "$PROJECT_ROOT/shared/state/fleet-state.json"
fi

echo ""
echo "Fleet stopped. Logs preserved in logs/"
