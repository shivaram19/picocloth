#!/bin/bash
# Mngr agent wrapper for node-f
# This agent monitors and proxies to the tmux session
while true; do
    if tmux has-session -t node-f 2>/dev/null; then
        PORT=18795
        if curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${PORT}/health" 2>/dev/null | grep -q "200\|404"; then
            echo "[12:34:34] node-f: ONLINE (port ${PORT})"
        else
            echo "[12:34:34] node-f: UNRESPONSIVE (port ${PORT})"
        fi
    else
        echo "[12:34:34] node-f: TMUX SESSION MISSING"
    fi
    sleep 10
done
