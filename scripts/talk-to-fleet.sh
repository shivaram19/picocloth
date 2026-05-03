#!/usr/bin/env bash
# Talk to the PicoCloth Fleet
# Usage: ./talk-to-fleet.sh <node-a|node-b> "your message here"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PICOCLOTH_DIR="$(dirname "$SCRIPT_DIR")"
PICOCLAW_BINARY="${PICOCLAW_BINARY:-/tmp/picoclaw/picoclaw}"

NODE="${1:-}"
MESSAGE="${2:-}"

if [ -z "$NODE" ] || [ -z "$MESSAGE" ]; then
    echo "Usage: $0 <node-a|node-b> \"your message here\""
    echo ""
    echo "Examples:"
    echo "  $0 node-a \"Research the latest Rust async runtime benchmarks\""
    echo "  $0 node-b \"Write a Python script that fetches weather data from Open-Meteo API\""
    exit 1
fi

case "$NODE" in
    node-a|a)
        export PICOCLAW_HOME="${PICOCLOTH_DIR}/node-a/home"
        echo "🧠 Sending to Curiosity Brain (Node-A) with Grok 4.20 Reasoning..."
        ;;
    node-b|b)
        export PICOCLAW_HOME="${PICOCLOTH_DIR}/node-b/home"
        echo "🔨 Sending to Executor (Node-B) with Grok 4.20 Multi-Agent..."
        ;;
    *)
        echo "Unknown node: $NODE. Use 'node-a' or 'node-b'"
        exit 1
        ;;
esac

echo "💬 Message: $MESSAGE"
echo "---"

"$PICOCLAW_BINARY" agent -m "$MESSAGE"
