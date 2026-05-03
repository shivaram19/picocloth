#!/usr/bin/env bash
# PicoClaw wrapper for mngr integration
# Usage: picoclaw-wrapper.sh <node-id>

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
exec /tmp/picoclaw/picoclaw gateway
