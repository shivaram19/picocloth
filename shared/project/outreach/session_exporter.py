#!/usr/bin/env python3
"""
🔐 Session Exporter — Human-in-the-Loop Node

Part of the PicoCloth Outreach Engine. This is NOT a standalone script.
It is SPAWNED by the Orchestrator when a valid LinkedIn session is needed.

The Orchestrator manages the entire flow:
  1. Detects no session
  2. Spawns this exporter
  3. Waits for human to log in
  4. Captures session automatically
  5. Saves to shared memory
  6. Signals completion

Archetype: The Guide (Diplomat + Guardian)
  - Clear, patient instructions
  - Protects the session (no credentials stored)
  - Validates output before signaling done

Usage (called by Orchestrator only):
    python3 session_exporter.py --output state/sessions/linkedin_state.json

Author: PicoCloth Fleet
Date: 2026-04-23
Purpose: Capture LinkedIn session via human-in-the-loop
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("❌ Playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)

load_dotenv()


def log(msg: str):
    print(f"🔐 [SessionExporter] {msg}")


def export_session(output_path: str, email: Optional[str] = None, password: Optional[str] = None):
    """
    Open a visible browser, guide human through login, capture session.

    The Guide archetype: patient, clear, protective.
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    log("=" * 60)
    log("PICOLOTH SESSION EXPORTER")
    log("=" * 60)
    log("")
    log("The Orchestrator has detected that no valid LinkedIn session exists.")
    log("This exporter will open a Chrome window. Please:")
    log("")
    log("  1. Log into LinkedIn normally in the browser window")
    log("  2. Complete any 2FA/CAPTCHA if prompted")
    log("  3. Make sure you can see your LinkedIn feed")
    log("  4. Return here and press ENTER")
    log("")
    log("We NEVER store your password. Only session cookies are saved.")
    log("=" * 60)
    log("")

    with sync_playwright() as p:
        # Launch VISIBLE browser
        log("🚀 Opening Chrome...")
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="en-US",
        )
        page = context.new_page()

        # Navigate to LinkedIn
        page.goto("https://www.linkedin.com/login")
        log("🌐 Browser opened. LinkedIn login page loaded.")
        log("")

        # If credentials provided, pre-fill them (but let human submit)
        if email and password:
            try:
                page.fill("#username", email)
                page.fill("#password", password)
                log(f"📝 Pre-filled email: {email}")
                log("   Please click 'Sign in' or complete verification.")
            except Exception:
                log("   Could not pre-fill credentials. Please log in manually.")

        log("")
        log("👉 Waiting for you to log in...")
        log("   (The browser window is open. Complete login there.)")
        log("")

        # Wait for human
        try:
            input("Press ENTER after you've logged in and can see your feed...")
        except EOFError:
            log("Non-interactive mode detected. Waiting 30 seconds...")
            time.sleep(30)

        # Verify login by navigating to feed
        log("🔍 Verifying session...")
        page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
        time.sleep(3)

        if "feed" not in page.url:
            log(f"⚠️  Verification failed. Current URL: {page.url}")
            log("   You may not be fully logged in. Please try again.")
            browser.close()
            return False

        log("✅ Verification passed! You're on the LinkedIn feed.")

        # Export full storage state
        log("💾 Capturing session state...")
        state = context.storage_state()

        # Add metadata
        state["_picocloth_metadata"] = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "source": "session_exporter",
            "url_at_export": page.url,
            "cookie_count": len(state.get("cookies", [])),
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

        log(f"💾 Session saved to: {output_file}")
        log(f"   Cookies: {len(state.get('cookies', []))}")
        log(f"   Origins: {len(state.get('origins', []))}")

        browser.close()

        log("")
        log("=" * 60)
        log("✅ SESSION EXPORT COMPLETE")
        log("=" * 60)
        log("The Orchestrator will now pick up this session and continue.")
        log("")

        return True


def main():
    parser = argparse.ArgumentParser(description="PicoCloth Session Exporter")
    parser.add_argument("--output", default="state/sessions/linkedin_state.json",
                        help="Where to save the session state")
    parser.add_argument("--email", default=os.getenv("LINKEDIN_EMAIL"),
                        help="LinkedIn email (optional, for pre-fill)")
    parser.add_argument("--password", default=os.getenv("LINKEDIN_PASSWORD"),
                        help="LinkedIn password (optional, for pre-fill)")
    args = parser.parse_args()

    success = export_session(args.output, email=args.email, password=args.password)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
