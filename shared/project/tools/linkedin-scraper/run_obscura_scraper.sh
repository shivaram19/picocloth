#!/usr/bin/env bash
# =============================================================================
# Run LinkedIn scraper with Obscura (stealth headless browser)
# =============================================================================
#
# Usage:
#   ./run_obscura_scraper.sh --profile "https://www.linkedin.com/in/nitishchoudhary/"
#   ./run_obscura_scraper.sh --profile "nitishchoudhary"
#   ./run_obscura_scraper.sh --profile "any" --attach   # use already-running Obscura
#
# This script will:
#   1. Check for the Obscura binary (downloaded or built from source)
#   2. Start Obscura in serve mode with stealth enabled (unless --attach)
#   3. Run scraper_obscura.py
#   4. Stop Obscura when done
# =============================================================================

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OBSCURA_PORT=9222

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ---------------------------------------------------------------------------
# Find Obscura binary
# ---------------------------------------------------------------------------
find_obscura() {
    local candidates=(
        "$PROJECT_DIR/obscura"
        "$PROJECT_DIR/obscura-src/target/release/obscura"
    )
    for c in "${candidates[@]}"; do
        if [[ -x "$c" ]]; then
            echo "$c"
            return 0
        fi
    done
    # Try PATH
    if command -v obscura &>/dev/null; then
        command -v obscura
        return 0
    fi
    return 1
}

# ---------------------------------------------------------------------------
# Start Obscura
# ---------------------------------------------------------------------------
start_obscura() {
    local binary
    binary=$(find_obscura) || {
        log_error "Obscura binary not found."
        log_info "Download:  curl -LO https://github.com/h4ckf0r0day/obscura/releases/latest/download/obscura-x86_64-linux.tar.gz"
        log_info "Or build:  cargo build --release --features stealth"
        exit 1
    }

    log_info "Found Obscura binary: $binary"

    if lsof -Pi :"$OBSCURA_PORT" -sTCP:LISTEN -t &>/dev/null; then
        log_warn "Port $OBSCURA_PORT already in use – assuming Obscura is running."
        return 0
    fi

    log_info "Starting Obscura (stealth mode) on port $OBSCURA_PORT …"
    "$binary" serve --port "$OBSCURA_PORT" --stealth &
    OBSCURA_PID=$!

    # Wait for readiness
    local attempts=0
    while ! curl -s "http://127.0.0.1:$OBSCURA_PORT/json/list" &>/dev/null; do
        sleep 0.5
        attempts=$((attempts + 1))
        if [[ $attempts -gt 30 ]]; then
            log_error "Obscura did not become ready within 15 s."
            kill "$OBSCURA_PID" 2>/dev/null || true
            exit 1
        fi
    done
    log_info "Obscura ready – PID $OBSCURA_PID"
}

# ---------------------------------------------------------------------------
# Stop Obscura
# ---------------------------------------------------------------------------
stop_obscura() {
    if [[ -n "${OBSCURA_PID:-}" ]]; then
        log_info "Stopping Obscura (PID $OBSCURA_PID) …"
        kill "$OBSCURA_PID" 2>/dev/null || true
        wait "$OBSCURA_PID" 2>/dev/null || true
    fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
OBSCURA_PID=""
trap stop_obscura EXIT

# Parse args to decide if we need to start Obscura
ATTACH=false
for arg in "$@"; do
    if [[ "$arg" == "--attach" ]]; then
        ATTACH=true
    fi
done

if [[ "$ATTACH" == false ]]; then
    start_obscura
fi

# Activate venv if present
if [[ -f "$PROJECT_DIR/venv/bin/activate" ]]; then
    # shellcheck source=/dev/null
    source "$PROJECT_DIR/venv/bin/activate"
fi

log_info "Running scraper_obscura.py …"
python "$PROJECT_DIR/scraper_obscura.py" "$@"

log_info "Done."
