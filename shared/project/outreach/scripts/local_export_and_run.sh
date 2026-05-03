#!/bin/bash
# =============================================================================
# PicoCloth Outreach — Local Export + Remote Run
#
# Run this on YOUR LOCAL MACHINE (laptop/desktop).
# It will:
#   1. Open Chrome for you to log into LinkedIn
#   2. Export your session cookies
#   3. Upload the session to your server
#   4. Trigger the outreach pipeline on the server
#
# Usage:
#   ./local_export_and_run.sh user@your-server /path/to/outreach
#
# Prerequisites:
#   - Python 3 + pip
#   - ssh + scp access to your server
#   - LinkedIn account
# =============================================================================

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────
SERVER="${1:-}"
REMOTE_PATH="${2:-~/tinkering/tinkering-with-claws/picocloth/shared/project/outreach}"
LOCAL_SESSION="/tmp/linkedin_state.json"
LIMIT="${3:-5}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ── Helpers ──────────────────────────────────────────────────────────────────
log()  { echo -e "${BLUE}[PicoCloth]${NC} $*"; }
ok()   { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── Validate inputs ──────────────────────────────────────────────────────────
if [[ -z "$SERVER" ]]; then
    echo "Usage: $0 user@server [remote_path] [limit]"
    echo ""
    echo "Example:"
    echo "  $0 shivaramgoud@myserver.com"
    echo "  $0 shivaramgoud@myserver.com /home/shivaramgoud/outreach 3"
    exit 1
fi

# ── Step 1: Check local dependencies ─────────────────────────────────────────
log "Step 1/5: Checking local dependencies..."

if ! command -v python3 &> /dev/null; then
    err "Python 3 is required. Install it first: https://python.org"
fi

if ! python3 -c "import playwright" 2>/dev/null; then
    warn "Playwright not found. Installing..."
    pip3 install --quiet playwright python-dotenv
    python3 -m playwright install chromium
    ok "Playwright installed"
else
    ok "Playwright found"
fi

# ── Step 2: Export session ───────────────────────────────────────────────────
log "Step 2/5: Exporting LinkedIn session..."
log "         A Chrome window will open. Please log into LinkedIn and press ENTER."

# Find session_exporter.py on local machine or download it
EXPORTER="./session_exporter.py"
if [[ ! -f "$EXPORTER" ]]; then
    log "Downloading session_exporter.py from server..."
    scp "$SERVER:$REMOTE_PATH/session_exporter.py" /tmp/session_exporter.py
    EXPORTER="/tmp/session_exporter.py"
fi

# Run the exporter
python3 "$EXPORTER" --output "$LOCAL_SESSION"

if [[ ! -f "$LOCAL_SESSION" ]]; then
    err "Session export failed. No file created at $LOCAL_SESSION"
fi

SESSION_SIZE=$(wc -c < "$LOCAL_SESSION")
if [[ $SESSION_SIZE -lt 1000 ]]; then
    err "Session file too small ($SESSION_SIZE bytes). Login may have failed."
fi

ok "Session exported ($SESSION_SIZE bytes)"

# ── Step 3: Upload session ───────────────────────────────────────────────────
log "Step 3/5: Uploading session to $SERVER..."

REMOTE_SESSION_DIR="$REMOTE_PATH/state/sessions"
scp "$LOCAL_SESSION" "$SERVER:$REMOTE_SESSION_DIR/linkedin_state.json"
ok "Session uploaded"

# ── Step 4: Activate remote environment and run ──────────────────────────────
log "Step 4/5: Triggering outreach pipeline on remote server..."
log "         Targets: $LIMIT | Server: $SERVER"

ssh "$SERVER" bash -s << REMOTE_EOF
    set -e
    cd "$REMOTE_PATH"
    
    # Activate virtual environment
    if [[ -f ../tools/linkedin-scraper/venv/bin/activate ]]; then
        source ../tools/linkedin-scraper/venv/bin/activate
    elif [[ -f venv/bin/activate ]]; then
        source venv/bin/activate
    fi
    
    # Run the pipeline
    python3 picocloth_outreach_engine.py --targets targets.csv --limit $LIMIT
REMOTE_EOF

# ── Step 5: Cleanup ──────────────────────────────────────────────────────────
log "Step 5/5: Cleaning up..."
rm -f "$LOCAL_SESSION"
ok "Local session file removed"

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "============================================================"
ok "PicoCloth Outreach complete!"
echo "============================================================"
echo ""
echo "Check the server for results:"
echo "  ssh $SERVER 'cat $REMOTE_PATH/state/last_run_summary.json'"
echo ""
