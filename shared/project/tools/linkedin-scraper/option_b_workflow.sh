#!/bin/bash
# Option B: Carbonyl Terminal Workflow
# 
# NOTE: This script attempts visible-terminal login. If LinkedIn shows a
# checkpoint/CAPTCHA (which happens on new IPs/automation detection), it
# automatically falls back to Option A instructions — no interactive input
# required, so no EOFError in SSH.

set -e

cd "$(dirname "$0")"
source venv/bin/activate

PORT=9222
COOKIES_FILE="linkedin_cookies.json"
CARBONYL_LOG="carbonyl.log"

# --- Terminal cleanup on exit ------------------------------------------------
cleanup() {
    # Reset terminal from any ANSI corruption
    stty sane 2>/dev/null || true
    printf '\033[0m\033[?25h\033[2J\033[H' 2>/dev/null || true
    # Kill background carbonyl if we started it
    if [ -n "$CARBONYL_PID" ]; then
        kill "$CARBONYL_PID" 2>/dev/null || true
        wait "$CARBONYL_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

# --- Carbonyl log cleanup ----------------------------------------------------
> "$CARBONYL_LOG" 2>/dev/null || true

echo "=========================================="
echo "Option B: Carbonyl + Playwright Workflow"
echo "=========================================="
echo ""

# Check if Carbonyl is already running
if curl -s "http://localhost:$PORT/json/version" > /dev/null 2>&1; then
    echo "✅ Carbonyl already running on port $PORT"
    CDP_URL=$(curl -s "http://localhost:$PORT/json/version" | python3 -c "import sys,json; print(json.load(sys.stdin)['webSocketDebuggerUrl'])")
    EXISTING=1
else
    echo "🚀 Starting Carbonyl on port $PORT..."
    echo "   (Output redirected to $CARBONYL_LOG to prevent terminal corruption)"
    echo ""
    
    # Start carbonyl in background, redirect stdout/stderr to log file
    # so Python's stdin stays clean and terminal doesn't get ANSI-bombed
    carbonyl --remote-debugging-port=$PORT about:blank > "$CARBONYL_LOG" 2>&1 &
    CARBONYL_PID=$!
    
    echo "   Carbonyl PID: $CARBONYL_PID"
    echo "   Waiting for CDP to be ready..."
    
    for i in {1..15}; do
        sleep 1
        if curl -s "http://localhost:$PORT/json/version" > /dev/null 2>&1; then
            break
        fi
        echo "   ...waiting ($i/15)"
    done
    
    CDP_URL=$(curl -s "http://localhost:$PORT/json/version" | python3 -c "import sys,json; print(json.load(sys.stdin)['webSocketDebuggerUrl'])")
    echo "✅ Carbonyl ready!"
    echo ""
    EXISTING=0
fi

echo "CDP URL: ${CDP_URL:0:60}..."
echo ""

# Check for saved cookies
if [ -f "$COOKIES_FILE" ]; then
    echo "🍪 Found saved cookies: $COOKIES_FILE"
    echo "   Skipping login — bot will try to use saved session."
    USE_COOKIES="--use-cookies"
else
    echo "🔐 No saved cookies found. Will log in with credentials from .env"
    USE_COOKIES=""
fi

echo ""
echo "=========================================="
echo "Starting bot..."
echo "=========================================="
echo ""

# Run the bot — NON-INTERACTIVE, no input() calls
export _BOT_CDP_URL="$CDP_URL"
export _BOT_USE_COOKIES="$USE_COOKIES"
export _BOT_COOKIES_FILE="$COOKIES_FILE"

python3 << 'PYEOF'
import os
import sys
import json
import time
import select
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

CDP_URL = os.getenv("_BOT_CDP_URL", "").strip()
USE_COOKIES = os.getenv("_BOT_USE_COOKIES", "").strip() == "--use-cookies"
COOKIES_FILE = os.getenv("_BOT_COOKIES_FILE", "").strip()
EMAIL = os.getenv("LINKEDIN_EMAIL")
PASSWORD = os.getenv("LINKEDIN_PASSWORD")

def wait_for_key(timeout_sec=0.5):
    """Non-blocking check for a keypress. Returns True if Enter pressed."""
    try:
        if select.select([sys.stdin], [], [], timeout_sec)[0]:
            sys.stdin.readline()
            return True
    except Exception:
        pass
    return False

def print_option_a_instructions():
    print("")
    print("=" * 70)
    print("🔄  FALLBACK: Option A (Session Export)")
    print("=" * 70)
    print("")
    print("LinkedIn requires verification that cannot be completed in this")
    print("terminal environment. You need to export a session from your")
    print("local machine where you're already logged in.")
    print("")
    print("Step 1 — On your LOCAL machine (laptop/desktop):")
    print("  1. Make sure you're logged into LinkedIn in Chrome/Edge")
    print("  2. Save this script as export_session.py and run it:")
    print("")
    print("""""")
    print("     import json, os")
    print("     from playwright.sync_api import sync_playwright")
    print("     with sync_playwright() as p:")
    print("         browser = p.chromium.launch(headless=False)")
    print("         context = browser.new_context()")
    print("         page = context.new_page()")
    print("         page.goto('https://www.linkedin.com')")
    print("         print('Log in manually, then press ENTER here...')")
    print("         input()")
    print("         state = context.storage_state()")
    print("         with open('linkedin_state.json', 'w') as f:")
    print("             json.dump(state, f)")
    print("         browser.close()")
    print("""""")
    print("")
    print("Step 2 — Upload the file to this server:")
    print("  scp linkedin_state.json user@this-server:/path/to/linkedin-scraper/")
    print("")
    print("Step 3 — Run the outreach bot with the saved session:")
    print("  python3 outreach_bot_v2.py --use-state linkedin_state.json --limit 2")
    print("")
    print("=" * 70)

print("=" * 70)
print("CARBONYL + PLAYWRIGHT BOT (Non-Interactive Mode)")
print("=" * 70)
print(f"CDP: {CDP_URL[:60]}...")
print(f"Email: {EMAIL}")
print("")

with sync_playwright() as p:
    print("🔌 Connecting to Carbonyl...")
    browser = p.chromium.connect_over_cdp(CDP_URL)
    # CRITICAL: Reuse Carbonyl's default context/page
    if browser.contexts:
        ctx = browser.contexts[0]
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
    else:
        ctx = browser.new_context()
        page = ctx.new_page()
    page.set_viewport_size({"width": 1920, "height": 1080})
    print("✅ Connected!")
    print("")
    
    # Try cookies first
    logged_in = False
    if USE_COOKIES and os.path.exists(COOKIES_FILE):
        print("🍪 Loading saved cookies...")
        try:
            with open(COOKIES_FILE, "r") as f:
                cookies = json.load(f)
            ctx.add_cookies(cookies)
            page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
            time.sleep(3)
            if "feed" in page.url:
                print("✅ Saved session worked!")
                logged_in = True
            else:
                print("⚠️  Saved session expired. Need to log in again.")
        except Exception as e:
            print(f"⚠️  Failed to load cookies: {e}")
    
    # Login if needed
    if not logged_in:
        print("🔐 Navigating to LinkedIn login...")
        page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
        time.sleep(3)
        page.screenshot(path="screenshots/b_login_page.png")
        
        print("📝 Filling credentials...")
        page.fill("#username", EMAIL)
        time.sleep(0.5)
        page.fill("#password", PASSWORD)
        time.sleep(0.5)
        
        print("🖱️  Clicking submit...")
        page.click("button[type='submit']")
        time.sleep(6)
        
        page.screenshot(path="screenshots/b_after_submit.png")
        current_url = page.url
        print(f"📍 URL after submit: {current_url}")
        
        if "feed" in current_url:
            print("✅ LOGIN SUCCESSFUL!")
            try:
                cookies = ctx.cookies()
                with open(COOKIES_FILE, "w") as f:
                    json.dump(cookies, f)
                print(f"🍪 Saved {len(cookies)} cookies for next time")
            except Exception as e:
                print(f"⚠️  Could not save cookies: {e}")
            logged_in = True
            
        elif "checkpoint" in current_url or "challenge" in current_url:
            print("")
            print("=" * 70)
            print("⚠️  LINKEDIN VERIFICATION REQUIRED (CAPTCHA/2FA)")
            print("=" * 70)
            print("LinkedIn detected automation and requires human verification.")
            print("This CANNOT be completed reliably in an SSH terminal.")
            print("")
            print("Screenshot saved: screenshots/b_after_submit.png")
            print("(You can view it to see what LinkedIn is asking)")
            print("")
            print_option_a_instructions()
            sys.exit(0)  # Graceful exit, not a crash
            
        else:
            print(f"❌ Unexpected result. Check screenshots/b_after_submit.png")
            sys.exit(1)
    
    if logged_in:
        print("")
        print("=" * 70)
        print("🚀 LOGGED IN! Ready for outreach.")
        print("=" * 70)
        print("")
        
        # Auto-run outreach without interactive prompts
        print("Loading targets from targets.json...")
        try:
            with open("targets.json", "r") as f:
                targets = json.load(f).get("targets", [])
        except Exception as e:
            print(f"❌ Failed to load targets: {e}")
            sys.exit(1)
        
        if not targets:
            print("No targets found in targets.json")
            sys.exit(0)
        
        print(f"Found {len(targets)} targets. Running in NON-INTERACTIVE mode.")
        print("(All connection requests will be sent automatically)")
        print("")
        
        import random
        for i, target in enumerate(targets[:3], 1):  # Max 3 per run for safety
            print(f"\n{'='*70}")
            print(f"Target {i}/{min(len(targets), 3)}: {target['name']} ({target['company']})")
            print(f"{'='*70}")
            
            page.goto(target["profile_url"], wait_until="domcontentloaded")
            time.sleep(4)
            
            for _ in range(3):
                page.evaluate("window.scrollBy(0, 800)")
                time.sleep(1.5)
            
            page.screenshot(path=f"screenshots/b_target_{i}.png")
            print(f"📸 Screenshot saved: screenshots/b_target_{i}.png")
            
            name = page.title().split(" | ")[0] if " | " in page.title() else "Unknown"
            print(f"👤 Name: {name}")
            
            # Try to send connection request
            try:
                connect = page.locator("button[aria-label*='Connect'], button:has-text('Connect')").first
                if connect.count() > 0 and connect.is_visible():
                    print("✅ Connect button found — sending request...")
                    connect.click()
                    time.sleep(2)
                    
                    add_note = page.locator("button[aria-label*='Add a note']").first
                    if add_note.count() > 0 and add_note.is_visible():
                        add_note.click()
                        time.sleep(1)
                        msg = target.get("connection_message", "")
                        textarea = page.locator("textarea#custom-message").first
                        if textarea.count() > 0:
                            textarea.fill(msg)
                            time.sleep(1)
                    
                    send_btn = page.locator("button[aria-label*='Send invitation']").first
                    if send_btn.count() > 0 and send_btn.is_visible():
                        send_btn.click()
                        time.sleep(2)
                        print("✅ Connection request sent!")
                    else:
                        print("⚠️  Send button not found")
                else:
                    print("⚠️  Connect button not found (may already be connected)")
            except Exception as e:
                print(f"⚠️  Failed to send request: {e}")
            
            if i < min(len(targets), 3):
                delay = random.uniform(20, 40)
                print(f"⏳ Waiting {delay:.0f}s before next target...")
                time.sleep(delay)
        
        print("\n✅ Outreach complete!")
        
        # Save cookies for next run
        try:
            cookies = ctx.cookies()
            with open(COOKIES_FILE, "w") as f:
                json.dump(cookies, f)
            print(f"🍪 Session saved to {COOKIES_FILE}")
        except Exception as e:
            print(f"⚠️  Could not save session: {e}")

print("Done.")
PYEOF
