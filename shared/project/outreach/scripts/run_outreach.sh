#!/bin/bash
# =============================================================================
# PicoCloth Outreach — Server-Side Runner
#
# Run this on the SERVER. It checks for a session and runs the pipeline.
# If no session exists, it tells you exactly how to create one.
# =============================================================================

set -euo pipefail

cd "$(dirname "$0")/.."
source ../tools/linkedin-scraper/venv/bin/activate 2>/dev/null || true

SESSION_FILE="state/sessions/linkedin_state.json"
LIMIT="${1:-0}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🪶 PicoCloth Outreach Engine${NC}"
echo ""

# Check for session
if [[ ! -f "$SESSION_FILE" ]] || [[ $(wc -c < "$SESSION_FILE") -lt 1000 ]]; then
    echo -e "${YELLOW}🔑 No valid LinkedIn session found.${NC}"
    echo ""
    echo "You have two options:"
    echo ""
    echo "OPTION A: Run from your LOCAL machine (recommended)"
    echo "  1. Copy this script to your laptop:"
    echo ""
    echo "     scp $(whoami)@$(hostname -I | awk '{print $1}'):$(pwd)/scripts/local_export_and_run.sh ."
    echo ""
    echo "  2. Run it:"
    echo ""
    echo "     ./local_export_and_run.sh $(whoami)@$(hostname -I | awk '{print $1}') $(pwd)"
    echo ""
    echo "OPTION B: Export session manually"
    echo "  1. On your local machine:"
    echo "     python3 session_exporter.py --output linkedin_state.json"
    echo ""
    echo "  2. Upload:"
    echo "     scp linkedin_state.json $(whoami)@$(hostname -I | awk '{print $1}'):$(pwd)/state/sessions/"
    echo ""
    exit 1
fi

echo -e "${GREEN}✅ Session found. Running outreach pipeline...${NC}"
echo ""

# Run pipeline
python3 picocloth_outreach_engine.py --targets targets.csv --limit "$LIMIT"
