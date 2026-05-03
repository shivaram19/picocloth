#!/usr/bin/env python3
"""
Option A: Export LinkedIn Session from Local Machine

Run this on your LOCAL machine (laptop/desktop) where you can:
1. Open a visible Chrome browser
2. Log into LinkedIn manually
3. Export the session cookies to a JSON file

Then upload the JSON file to the server and the bot will use it.

Usage:
    python3 export_session.py
    # ... log in manually in the browser window ...
    # ... press ENTER in the terminal when done ...
    # Upload linkedin_state.json to the server
"""

import json
import os
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("❌ Playwright not installed. Install it first:")
    print("   pip install playwright")
    print("   playwright install chromium")
    sys.exit(1)


def main():
    output_file = "linkedin_state.json"

    print("=" * 60)
    print("LINKEDIN SESSION EXPORTER")
    print("=" * 60)
    print("")
    print("This will open a visible Chrome window. Please:")
    print("  1. Log into LinkedIn manually (email + password + 2FA if needed)")
    print("  2. Once you're on the LinkedIn feed/homepage,")
    print("     return here and press ENTER to save the session.")
    print("")
    print("=" * 60)
    print("")

    with sync_playwright() as p:
        # Launch visible browser
        print("🚀 Launching Chrome...")
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # Go to LinkedIn
        print("🌐 Navigating to LinkedIn...")
        page.goto("https://www.linkedin.com")

        print("")
        print("👉 A Chrome window should have opened.")
        print("   Please log in to LinkedIn now.")
        print("")

        # Wait for user to log in
        try:
            input("Press ENTER after you've logged in and can see your feed...")
        except EOFError:
            # Non-interactive environment — just wait a bit and save
            print("(Non-interactive mode — saving session in 10 seconds...)")
            import time
            time.sleep(10)

        # Verify we're logged in
        page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
        import time
        time.sleep(2)

        if "feed" not in page.url:
            print(f"⚠️  Current URL: {page.url}")
            print("⚠️  You don't seem to be on the LinkedIn feed.")
            print("   Make sure you're fully logged in before pressing ENTER.")
            browser.close()
            sys.exit(1)

        # Export full storage state (cookies + localStorage)
        print("💾 Saving session state...")
        state = context.storage_state()

        with open(output_file, "w") as f:
            json.dump(state, f, indent=2)

        # Also save just the cookies in the format the bot expects
        cookies_only = {
            "cookies": state.get("cookies", []),
            "origins": state.get("origins", [])
        }
        cookies_file = "linkedin_cookies.json"
        with open(cookies_file, "w") as f:
            json.dump(cookies_only, f, indent=2)

        browser.close()

        print("")
        print("=" * 60)
        print("✅ SESSION EXPORTED SUCCESSFULLY!")
        print("=" * 60)
        print("")
        print(f"Files created:")
        print(f"  • {output_file}      (full state — use with outreach_bot_v2.py)")
        print(f"  • {cookies_file}  (cookies only — use with carbonyl_bot.py)")
        print("")
        print("Next steps:")
        print(f"  1. Upload one of these files to your server:")
        print(f"     scp {output_file} user@your-server:~/path/to/linkedin-scraper/")
        print("")
        print(f"  2. On the server, run the bot with the saved session:")
        print(f"     python3 outreach_bot_v2.py --use-state {output_file}")
        print("")
        print("=" * 60)


if __name__ == "__main__":
    main()
