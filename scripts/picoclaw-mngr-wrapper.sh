#!/usr/bin/env bash
# PicoClaw wrapper for mngr - keeps tmux session alive

NODE_ID="${1:-node-a}"
PICOCLOTH_DIR="/home/shivaramgoud/tinkering/tinkering-with-claws/picocloth"

export PICOCLAW_HOME="${PICOCLOTH_DIR}/${NODE_ID}/home"
export PICOCLAW_HOOK_TWIN_DIR="${PICOCLOTH_DIR}/shared/digital-twins/${NODE_ID}"
export PICOCLAW_HOOK_PROJECT_DIR="${PICOCLOTH_DIR}/shared/project"
export PICOCLAW_HOOK_NODE_ID="${NODE_ID}"
export PICOCLAW_HOOK_MAX_FACTS="8"
export LANGFUSE_PUBLIC_KEY=""
export LANGFUSE_SECRET_KEY=""

cd "${PICOCLOTH_DIR}"

# Start picoclaw in background and keep shell alive for mngr
/tmp/picoclaw/picoclaw gateway &
PICOPID=$!

# Wait for picoclaw
wait $PICOPID

# Keep shell alive so mngr's tmux window persists
echo "Picoclaw exited. Keeping session alive for mngr..."
exec bash
