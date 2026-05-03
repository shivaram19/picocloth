#!/usr/bin/env python3
"""
Carbonyl + Playwright Integration Bot

The best of both worlds:
- Carbonyl renders the browser in your terminal (you can SEE it)
- Playwright controls it programmatically via Chrome DevTools Protocol

Usage:
    # Terminal 1: Run Carbonyl (output redirected to avoid ANSI corruption)
    carbonyl --remote-debugging-port=9222 about:blank > carbonyl.log 2>&1

    # Terminal 2: Run the bot
    python3 carbonyl_bot.py --cdp-url ws://localhost:9222/devtools/browser/...

Or use the auto-launcher:
    python3 carbonyl_bot.py --auto-launch --limit 2
"""

import os
import sys
import json
import time
import random
import argparse
import subprocess
import urllib.request
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from playwright.sync_api import sync_playwright

load_dotenv()

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
CDP_PORT = 9222
STATE_FILE = "linkedin_state.json"
COOKIES_FILE = "linkedin_cookies.json"
SCREENSHOT_DIR = "screenshots"
DAILY_CONNECT_LIMIT = 20

# ---------------------------------------------------------------------------
# LOGGER
# ---------------------------------------------------------------------------
class Logger:
    def __init__(self, log_file: str = "carbonyl_bot_log.jsonl"):
        self.log_file = log_file
        self.stats = {
            "started_at": datetime.now().isoformat(),
            "targets_total": 0,
            "profiles_scraped": 0,
            "connections_sent": 0,
            "connections_failed": 0,
            "errors": []
        }

    def log(self, event: str, data: Dict = None):
        entry = {"timestamp": datetime.now().isoformat(), "event": event, "data": data or {}}
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {event}")

    def error(self, msg: str, exc: Exception = None):
        self.stats["errors"].append({"msg": msg, "exc": str(exc) if exc else None})
        self.log("ERROR", {"msg": msg, "exc": str(exc) if exc else None})

    def save_stats(self):
        self.stats["finished_at"] = datetime.now().isoformat()
        with open("carbonyl_bot_stats.json", "w") as f:
            json.dump(self.stats, f, indent=2)


# ---------------------------------------------------------------------------
# UTILS
# ---------------------------------------------------------------------------
def print_option_a_instructions():
    """Print instructions for Option A (session export) fallback."""
    print("")
    print("=" * 70)
    print("🔄  FALLBACK: Option A (Session Export)")
    print("=" * 70)
    print("")
    print("LinkedIn requires verification that cannot be completed in this")
    print("terminal environment. Export a session from your local machine.")
    print("")
    print("Step 1 — On your LOCAL machine:")
    print("  python3 export_session.py")
    print("  (Log in manually in the browser window, then press ENTER)")
    print("")
    print("Step 2 — Upload the file to this server:")
    print("  scp linkedin_state.json user@this-server:/path/to/linkedin-scraper/")
    print("")
    print("Step 3 — Run the bot with the saved session:")
    print("  python3 outreach_bot_v2.py --use-state linkedin_state.json --limit 2")
    print("")
    print("=" * 70)


# ---------------------------------------------------------------------------
# CARBONYL LAUNCHER
# ---------------------------------------------------------------------------
def start_carbonyl(port: int = CDP_PORT) -> subprocess.Popen:
    """Start Carbonyl with remote debugging enabled."""
    print("=" * 60)
    print("STARTING CARBONYL (Terminal Browser)")
    print("=" * 60)
    print("Carbonyl output is being redirected to carbonyl.log")
    print("to prevent terminal ANSI corruption.")
    print("=" * 60)
    print()

    log_file = open("carbonyl.log", "w")
    proc = subprocess.Popen(
        ["carbonyl", f"--remote-debugging-port={port}", "about:blank"],
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )

    # Wait for CDP to be ready
    for i in range(10):
        time.sleep(1)
        try:
            with urllib.request.urlopen(
                f"http://localhost:{port}/json/version", timeout=2
            ) as resp:
                data = json.loads(resp.read().decode())
                ws_url = data["webSocketDebuggerUrl"]
                print(f"✅ Carbonyl ready! CDP URL: {ws_url}")
                return proc, ws_url
        except Exception:
            print(f"  Waiting for Carbonyl... ({i+1}/10)")
            continue

    proc.terminate()
    raise RuntimeError("Carbonyl failed to start or CDP not responding")


# ---------------------------------------------------------------------------
# LINKEDIN AUTOMATION
# ---------------------------------------------------------------------------
class CarbonylBot:
    def __init__(self, cdp_url: str, dry_run: bool = False):
        self.cdp_url = cdp_url
        self.dry_run = dry_run
        self.logger = Logger()
        self.browser = None
        self.context = None
        self.page = None
        self.connections_sent = 0
        self._playwright = None

    def connect(self):
        """Connect Playwright to the running Carbonyl instance."""
        self.logger.log("CONNECTING_TO_CARBONYL", {"cdp_url": self.cdp_url})
        self._playwright = sync_playwright().start()
        self.browser = self._playwright.chromium.connect_over_cdp(self.cdp_url)
        # CRITICAL: Reuse Carbonyl's default context/page — creating new ones breaks terminal rendering
        if self.browser.contexts:
            self.context = self.browser.contexts[0]
            self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        else:
            self.context = self.browser.new_context()
            self.page = self.context.new_page()
        self.page.set_viewport_size({"width": 1920, "height": 1080})
        self.logger.log("CONNECTED", {"contexts": len(self.browser.contexts)})

    def is_logged_in(self) -> bool:
        """Check if already logged into LinkedIn."""
        self.page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
        time.sleep(2)
        return "feed" in self.page.url

    def login(self, email: str, password: str) -> bool:
        """Log into LinkedIn via Carbonyl."""
        if self.dry_run:
            self.logger.log("LOGIN_SKIPPED_DRY_RUN")
            return True

        if self.is_logged_in():
            self.logger.log("ALREADY_LOGGED_IN")
            return True

        self.logger.log("LOGIN_START")
        self.page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
        time.sleep(3)

        print("\n🖥️  Filling credentials programmatically...")
        self.page.fill("#username", email)
        time.sleep(1)
        self.page.fill("#password", password)
        time.sleep(1)
        self.page.click("button[type='submit']")
        time.sleep(6)

        # Check result
        if "feed" in self.page.url:
            self.logger.log("LOGIN_SUCCESS")
            self._save_state()
            return True

        if "checkpoint" in self.page.url or "challenge" in self.page.url:
            self.logger.log("VERIFICATION_REQUIRED")
            print("\n" + "=" * 70)
            print("⚠️  LINKEDIN VERIFICATION REQUIRED (CAPTCHA/2FA)")
            print("=" * 70)
            print("LinkedIn detected automation and requires human verification.")
            print("This CANNOT be completed reliably in an SSH terminal.")
            print("")
            print("Screenshot saved: screenshots/after_submit.png")
            print("")
            print_option_a_instructions()
            return False  # Graceful fallback, not a crash

        self.logger.error("Login failed — unexpected URL: " + self.page.url)
        return False

    def login_with_state(self, state_file: str = STATE_FILE) -> bool:
        """Try to login using saved session state."""
        if not os.path.exists(state_file):
            return False

        self.logger.log("LOADING_SAVED_STATE", {"file": state_file})
        try:
            with open(state_file, "r") as f:
                state = json.load(f)
            
            # Handle both full storage_state() format and simple cookies format
            cookies = state.get("cookies", state if isinstance(state, list) else [])
            self.context.add_cookies(cookies)
            
            self.page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
            time.sleep(3)
            if "feed" in self.page.url:
                self.logger.log("SAVED_STATE_WORKED")
                return True
        except Exception as e:
            self.logger.error("Failed to load saved state", e)
        return False

    def login_with_cookies(self, cookies_file: str = COOKIES_FILE) -> bool:
        """Try to login using saved cookies."""
        if not os.path.exists(cookies_file):
            return False

        self.logger.log("LOADING_COOKIES", {"file": cookies_file})
        try:
            with open(cookies_file, "r") as f:
                data = json.load(f)
            cookies = data.get("cookies", data if isinstance(data, list) else [])
            self.context.add_cookies(cookies)
            
            self.page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
            time.sleep(3)
            if "feed" in self.page.url:
                self.logger.log("COOKIES_WORKED")
                return True
        except Exception as e:
            self.logger.error("Failed to load cookies", e)
        return False

    def _save_state(self):
        """Save cookies for reuse."""
        try:
            cookies = self.context.cookies()
            with open(COOKIES_FILE, "w") as f:
                json.dump({"cookies": cookies}, f)
            self.logger.log("COOKIES_SAVED", {"count": len(cookies)})
        except Exception as e:
            self.logger.error("Failed to save cookies", e)

    def scrape_profile(self, profile_url: str) -> Dict:
        """Scrape a profile via Carbonyl."""
        self.logger.log("SCRAPE_START", {"url": profile_url})
        self.page.goto(profile_url, wait_until="domcontentloaded")
        time.sleep(3)

        # Scroll to load content
        for _ in range(3):
            self.page.evaluate("window.scrollBy(0, 800)")
            time.sleep(1.5)

        data = {
            "name": self._safe_text("h1"),
            "headline": self._safe_text("div.text-body-medium"),
            "about": self._safe_text("section:has(h2 span:has-text('About')) div.inline-show-more-text"),
            "company": self._safe_text("section:has(h2 span:has-text('Experience')) a[href*='company/']"),
            "url": profile_url,
        }

        self.logger.log("SCRAPE_SUCCESS", data)
        self.logger.stats["profiles_scraped"] += 1
        return data

    def _safe_text(self, selector: str) -> str:
        try:
            el = self.page.locator(selector).first
            if el.count() > 0:
                return el.inner_text(timeout=2000).strip()
        except Exception:
            pass
        return ""

    def send_connection_request(self, profile_url: str, message: str) -> bool:
        """Send a connection request."""
        if self.dry_run:
            self.logger.log("CONNECT_DRY_RUN", {"url": profile_url, "msg": message[:80]})
            return True

        if self.connections_sent >= DAILY_CONNECT_LIMIT:
            self.logger.log("DAILY_LIMIT_REACHED")
            return False

        self.logger.log("CONNECT_START", {"url": profile_url})
        self.page.goto(profile_url, wait_until="domcontentloaded")
        time.sleep(3)

        try:
            connect = self.page.locator("button[aria-label*='Connect'], button:has-text('Connect')").first
            if not connect.is_visible():
                self.logger.log("CONNECT_BUTTON_NOT_FOUND")
                return False

            connect.click()
            time.sleep(2)

            add_note = self.page.locator("button[aria-label*='Add a note']").first
            if add_note.is_visible():
                add_note.click()
                time.sleep(1)
                self.page.locator("textarea#custom-message").first.fill(message)
                time.sleep(1)

            self.page.locator("button[aria-label*='Send invitation']").first.click()
            time.sleep(2)

            self.connections_sent += 1
            self.logger.stats["connections_sent"] += 1
            self.logger.log("CONNECT_SENT")
            return True

        except Exception as e:
            self.logger.stats["connections_failed"] += 1
            self.logger.error("Connect failed", e)
            return False

    def process_targets(self, targets: List[Dict]):
        self.logger.stats["targets_total"] = len(targets)
        self.logger.log("PROCESSING_START", {"total": len(targets)})

        for i, target in enumerate(targets, 1):
            print(f"\n{'='*60}")
            print(f"Target {i}/{len(targets)}: {target['name']} ({target['company']})")
            print(f"{'='*60}")

            data = self.scrape_profile(target["profile_url"])
            msg = target.get("connection_message", "")

            print(f"\nMessage: {msg[:120]}...")
            if not self.dry_run:
                success = self.send_connection_request(target["profile_url"], msg)
                if success:
                    delay = random.uniform(20, 60)
                    print(f"⏳ Waiting {delay:.0f}s before next target...")
                    time.sleep(delay)
            else:
                print("[DRY RUN] Not sent")

        self.logger.log("PROCESSING_COMPLETE")
        self.logger.save_stats()

    def close(self):
        try:
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self._playwright:
                self._playwright.stop()
        except Exception as e:
            self.logger.error("Error during cleanup", e)
        self.logger.save_stats()


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Carbonyl + Playwright LinkedIn Bot")
    parser.add_argument("--cdp-url", help="Carbonyl CDP WebSocket URL (auto-detected if omitted)")
    parser.add_argument("--auto-launch", action="store_true", help="Launch Carbonyl automatically")
    parser.add_argument("--targets", default="targets.json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--email", default=os.getenv("LINKEDIN_EMAIL"))
    parser.add_argument("--password", default=os.getenv("LINKEDIN_PASSWORD"))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--use-state", help="Path to saved session state JSON (Option A)")
    parser.add_argument("--use-cookies", help="Path to saved cookies JSON")
    args = parser.parse_args()

    # Load targets
    with open(args.targets, "r") as f:
        targets = json.load(f).get("targets", [])
    if args.limit > 0:
        targets = targets[:args.limit]

    print("\n" + "=" * 60)
    print("CARBONYL + PLAYWRIGHT LINKEDIN BOT")
    print("=" * 60)
    print("This bot uses Carbonyl (terminal browser) + Playwright (automation)")
    print("=" * 60 + "\n")

    # Start or connect to Carbonyl
    carbonyl_proc = None
    cdp_url = args.cdp_url

    if args.auto_launch or not cdp_url:
        carbonyl_proc, cdp_url = start_carbonyl()
        print(f"\nCarbonyl is running. CDP URL: {cdp_url}")
        print()
        time.sleep(2)

    # Create bot
    bot = CarbonylBot(cdp_url=cdp_url, dry_run=args.dry_run)

    try:
        bot.connect()

        # Login
        if not args.dry_run:
            logged_in = False
            
            # Try saved state first
            if args.use_state and bot.login_with_state(args.use_state):
                logged_in = True
            elif args.use_cookies and bot.login_with_cookies(args.use_cookies):
                logged_in = True
            elif bot.login_with_cookies():
                logged_in = True
            elif bot.login_with_state():
                logged_in = True
            
            # Try credentials
            if not logged_in and args.email and args.password:
                logged_in = bot.login(args.email, args.password)
            
            if not logged_in:
                print("\n❌ Login failed or verification required.")
                print_option_a_instructions()
                sys.exit(1)

        # Run outreach
        bot.process_targets(targets)

    except KeyboardInterrupt:
        print("\n\n🛑 Stopped by user")
    finally:
        bot.close()
        if carbonyl_proc:
            carbonyl_proc.terminate()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Scraped: {bot.logger.stats['profiles_scraped']}")
    print(f"Sent: {bot.logger.stats['connections_sent']}")
    print(f"Failed: {bot.logger.stats['connections_failed']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
