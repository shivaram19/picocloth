#!/usr/bin/env python3
"""
LinkedIn Outreach Bot v2 — Playwright Edition

Built for headless/remote environments. Key features:
- Session persistence (login once, reuse cookies)
- Automatic screenshots at every step
- Screenshot-based verification flow
- Works in pure headless SSH sessions

⚠️  DISCLAIMER: LinkedIn automation violates their Terms of Service.
   Use at your own risk. For educational purposes only.
"""

import os
import sys
import json
import time
import random
import argparse
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from playwright.sync_api import sync_playwright, Page, BrowserContext

# Load environment variables
load_dotenv()

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
MIN_DELAY = 2
MAX_DELAY = 5
CONNECT_DELAY_MIN = 20
CONNECT_DELAY_MAX = 60
DAILY_CONNECT_LIMIT = 20
STATE_FILE = "linkedin_state.json"
SCREENSHOT_DIR = "screenshots"

# ---------------------------------------------------------------------------
# LOGGER
# ---------------------------------------------------------------------------
class OutreachLogger:
    def __init__(self, log_file: str = "outreach_log.jsonl"):
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
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "data": data or {}
        }
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {event}")

    def error(self, msg: str, exc: Exception = None):
        err_data = {"message": msg}
        if exc:
            err_data["exception"] = str(exc)
        self.stats["errors"].append(err_data)
        self.log("ERROR", err_data)

    def save_stats(self):
        self.stats["finished_at"] = datetime.now().isoformat()
        with open("outreach_stats.json", "w", encoding="utf-8") as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# SCREENSHOT HELPER
# ---------------------------------------------------------------------------
def ensure_screenshot_dir():
    Path(SCREENSHOT_DIR).mkdir(exist_ok=True)


def screenshot(page: Page, name: str):
    """Save a screenshot with timestamp."""
    ensure_screenshot_dir()
    ts = datetime.now().strftime("%H%M%S")
    path = f"{SCREENSHOT_DIR}/{ts}_{name}.png"
    page.screenshot(path=path, full_page=True)
    print(f"  📸 Screenshot saved: {path}")
    return path


# ---------------------------------------------------------------------------
# HUMAN-LIKE DELAYS
# ---------------------------------------------------------------------------
def human_delay(min_sec: float = MIN_DELAY, max_sec: float = MAX_DELAY):
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)


# ---------------------------------------------------------------------------
# LINKEDIN OUTREACH BOT v2
# ---------------------------------------------------------------------------
class LinkedInOutreachBotV2:
    def __init__(self, headless: bool = True, dry_run: bool = False):
        self.headless = headless
        self.dry_run = dry_run
        self.logger = OutreachLogger()
        self.connections_sent_today = 0
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None

    def setup(self):
        """Initialize Playwright browser with session persistence."""
        self.logger.log("BROWSER_SETUP", {"headless": self.headless})
        self.playwright = sync_playwright().start()

        # Load existing state if available
        storage_state = STATE_FILE if os.path.exists(STATE_FILE) else None

        browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )

        self.context = browser.new_context(
            storage_state=storage_state,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.page = self.context.new_page()
        self.page.set_viewport_size({"width": 1920, "height": 1080})

    def save_state(self):
        """Save browser state (cookies, localStorage) for reuse."""
        if self.context:
            self.context.storage_state(path=STATE_FILE)
            self.logger.log("STATE_SAVED", {"file": STATE_FILE})

    def is_logged_in(self) -> bool:
        """Check if already logged in using saved state."""
        self.page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
        human_delay(2, 4)
        screenshot(self.page, "feed_check")

        # If URL changed to feed, we're logged in
        if "feed" in self.page.url:
            self.logger.log("ALREADY_LOGGED_IN", {"method": "saved_state"})
            return True

        # Check for login page
        if "login" in self.page.url:
            return False

        # Check for identity verification checkpoint
        if "checkpoint" in self.page.url:
            self.logger.log("CHECKPOINT_DETECTED")
            return False

        return False

    def login(self, email: str, password: str) -> bool:
        """Log into LinkedIn with screenshot-based verification support."""
        if self.dry_run:
            self.logger.log("LOGIN_SKIPPED_DRY_RUN")
            return True

        # First check if already logged in
        if self.is_logged_in():
            return True

        self.logger.log("LOGIN_START")

        # Navigate to login
        self.page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
        human_delay(2, 4)
        screenshot(self.page, "login_page")

        try:
            # Enter credentials
            self.page.fill("#username", email)
            human_delay(0.5, 1.5)
            self.page.fill("#password", password)
            human_delay(0.5, 1.5)

            # Click submit
            self.page.click("button[type='submit']")
            self.logger.log("LOGIN_SUBMITTED")
            human_delay(4, 7)
            screenshot(self.page, "after_submit")

            # Handle verification challenges
            max_wait = 60
            waited = 0
            while waited < max_wait:
                current_url = self.page.url

                if "feed" in current_url:
                    self.logger.log("LOGIN_SUCCESS")
                    self.save_state()
                    return True

                if "checkpoint" in current_url or "challenge" in current_url:
                    self.logger.log("VERIFICATION_REQUIRED", {"url": current_url})
                    screenshot(self.page, "verification_needed")

                    print("\n" + "="*60)
                    print("⚠️  LINKEDIN VERIFICATION REQUIRED")
                    print("="*60)
                    print(f"Current URL: {current_url}")
                    print(f"Screenshot saved: screenshots/*_verification_needed.png")
                    print("\nOptions:")
                    print("1. Open the screenshot to see what LinkedIn wants")
                    print("2. Complete verification manually in a browser")
                    print("3. Export cookies from your logged-in browser and place them here")
                    print("\nPress ENTER after completing verification (or Ctrl+C to abort)")
                    print("="*60)

                    try:
                        input()
                        # Re-check
                        self.page.reload(wait_until="domcontentloaded")
                        human_delay(3, 5)
                        screenshot(self.page, "after_manual_verification")

                        if "feed" in self.page.url:
                            self.logger.log("LOGIN_SUCCESS_AFTER_VERIFICATION")
                            self.save_state()
                            return True
                    except KeyboardInterrupt:
                        return False

                # Check for PIN/2FA
                if self.page.locator("input#input__phone_verification_pin").is_visible():
                    self.logger.log("2FA_REQUIRED")
                    screenshot(self.page, "2fa_required")
                    print("\n2FA/PIN required. Check screenshot. Enter PIN and press ENTER:")
                    try:
                        pin = input("PIN: ").strip()
                        if pin:
                            self.page.fill("input#input__phone_verification_pin", pin)
                            self.page.click("button[type='submit']")
                            human_delay(4, 6)
                    except KeyboardInterrupt:
                        return False

                human_delay(2, 3)
                waited += 5

            self.logger.error("Login timed out waiting for verification")
            return False

        except Exception as e:
            screenshot(self.page, "login_error")
            self.logger.error("Login failed", e)
            return False

    def scrape_profile(self, profile_url: str) -> Dict:
        """Scrape a LinkedIn profile."""
        self.logger.log("SCRAPE_START", {"url": profile_url})

        try:
            self.page.goto(profile_url, wait_until="domcontentloaded")
            human_delay(3, 6)

            # Scroll to load content
            for _ in range(3):
                self.page.evaluate("window.scrollBy(0, 800)")
                human_delay(1, 2)

            screenshot(self.page, f"profile_{profile_url.split('/')[-2] if '/in/' in profile_url else 'unknown'}")

            # Extract name
            name = self._extract_name()
            headline = self._extract_headline()
            about = self._extract_about()
            company = self._extract_company()

            data = {
                "name": name,
                "headline": headline,
                "about": about,
                "company": company,
                "profile_url": profile_url,
                "scraped_at": datetime.now().isoformat()
            }

            self.logger.log("SCRAPE_SUCCESS", data)
            self.logger.stats["profiles_scraped"] += 1
            return data

        except Exception as e:
            screenshot(self.page, "scrape_error")
            self.logger.error(f"Scrape failed for {profile_url}", e)
            return {"error": str(e), "profile_url": profile_url}

    def _extract_name(self) -> str:
        try:
            title = self.page.title()
            if " | LinkedIn" in title:
                return title.split(" | LinkedIn")[0].strip()
        except Exception:
            pass
        try:
            return self.page.locator("h1").first.inner_text(timeout=3000).strip()
        except Exception:
            return "Unknown"

    def _extract_headline(self) -> str:
        try:
            return self.page.locator("div.text-body-medium").first.inner_text(timeout=3000).strip()
        except Exception:
            return ""

    def _extract_about(self) -> str:
        try:
            about_section = self.page.locator("section:has(h2 span:has-text('About'))")
            if about_section.count() > 0:
                # Click show more if present
                show_more = about_section.locator("button:has-text('more')")
                if show_more.count() > 0:
                    show_more.first.click()
                    human_delay(0.5, 1)

                text = about_section.locator("div.inline-show-more-text").first.inner_text(timeout=3000).strip()
                return text
        except Exception:
            pass
        return ""

    def _extract_company(self) -> str:
        try:
            exp_section = self.page.locator("section:has(h2 span:has-text('Experience'))")
            if exp_section.count() > 0:
                company = exp_section.locator("a[href*='company/']").first.inner_text(timeout=3000).strip()
                return company
        except Exception:
            pass
        return ""

    def send_connection_request(self, profile_url: str, message: str) -> bool:
        """Send a personalized connection request."""
        if self.dry_run:
            self.logger.log("CONNECT_DRY_RUN", {"url": profile_url, "message": message[:100]})
            return True

        if self.connections_sent_today >= DAILY_CONNECT_LIMIT:
            self.logger.log("DAILY_LIMIT_REACHED")
            return False

        self.logger.log("CONNECT_START", {"url": profile_url})

        try:
            self.page.goto(profile_url, wait_until="domcontentloaded")
            human_delay(3, 5)
            screenshot(self.page, "connect_page")

            # Find Connect button
            connect_btn = self.page.locator("button[aria-label*='Connect'], button:has-text('Connect')").first
            if not connect_btn.is_visible():
                self.logger.log("CONNECT_BUTTON_NOT_FOUND")
                return False

            connect_btn.click()
            human_delay(2, 4)
            screenshot(self.page, "connect_dialog")

            # Look for "Add a note" button
            add_note = self.page.locator("button[aria-label*='Add a note']").first
            if add_note.is_visible():
                add_note.click()
                human_delay(1, 2)

                # Fill message
                note_field = self.page.locator("textarea#custom-message").first
                note_field.fill(message)
                human_delay(1, 2)
                screenshot(self.page, "message_filled")

                # Send
                send_btn = self.page.locator("button[aria-label*='Send invitation']").first
                send_btn.click()
            else:
                # Send without note
                send_btn = self.page.locator("button[aria-label*='Send invitation']").first
                send_btn.click()

            human_delay(2, 4)
            self.connections_sent_today += 1
            self.logger.stats["connections_sent"] += 1
            self.logger.log("CONNECT_SENT")
            return True

        except Exception as e:
            screenshot(self.page, "connect_error")
            self.logger.stats["connections_failed"] += 1
            self.logger.error(f"Connection failed for {profile_url}", e)
            return False

    def process_targets(self, targets: List[Dict]):
        self.logger.stats["targets_total"] = len(targets)
        self.logger.log("PROCESSING_START", {"total": len(targets)})

        for i, target in enumerate(targets, 1):
            print(f"\n{'='*60}")
            print(f"Target {i}/{len(targets)}: {target['name']} ({target['company']})")
            print(f"{'='*60}")

            profile_data = self.scrape_profile(target["profile_url"])
            message = target.get("connection_message", "")

            print(f"\nMessage preview:")
            print(f"{'-'*40}")
            print(message[:200] + "..." if len(message) > 200 else message)
            print(f"{'-'*40}")

            if not self.dry_run:
                success = self.send_connection_request(target["profile_url"], message)
                if success:
                    delay = random.uniform(CONNECT_DELAY_MIN, CONNECT_DELAY_MAX)
                    print(f"Waiting {delay:.0f}s before next target...")
                    time.sleep(delay)
            else:
                print("[DRY RUN] Connection not sent")

        self.logger.log("PROCESSING_COMPLETE")
        self.logger.save_stats()

    def close(self):
        if self.context:
            self.context.close()
        if self.playwright:
            self.playwright.stop()
        self.logger.save_stats()
        self.logger.log("BOT_SHUTDOWN")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="LinkedIn Outreach Bot v2 (Playwright)")
    parser.add_argument("--targets", default="targets.json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--no-headless", dest="headless", action="store_false")
    parser.add_argument("--email", default=os.getenv("LINKEDIN_EMAIL"))
    parser.add_argument("--password", default=os.getenv("LINKEDIN_PASSWORD"))
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    if not args.dry_run and (not args.email or not args.password) and not os.path.exists(STATE_FILE):
        print("❌ Error: Credentials required (or existing state file)")
        print("Set LINKEDIN_EMAIL and LINKEDIN_PASSWORD in .env")
        print("Or login once and the session will be saved automatically")
        sys.exit(1)

    with open(args.targets, "r") as f:
        targets = json.load(f).get("targets", [])
    if args.limit > 0:
        targets = targets[:args.limit]

    print("\n" + "="*60)
    print("LINKEDIN OUTREACH BOT v2 — Playwright Edition")
    print("="*60)
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"Targets: {len(targets)}")
    print(f"Headless: {args.headless}")
    print(f"Screenshots: {SCREENSHOT_DIR}/")
    if os.path.exists(STATE_FILE):
        print(f"Session state: {STATE_FILE} (will reuse)")
    print("="*60 + "\n")

    if not args.dry_run:
        print("⚠️  This will send REAL LinkedIn connection requests.")
        confirm = input("Proceed? (yes/no): ")
        if confirm.lower() != "yes":
            print("Aborted.")
            sys.exit(0)

    bot = LinkedInOutreachBotV2(headless=args.headless, dry_run=args.dry_run)

    try:
        bot.setup()

        if not args.dry_run:
            login_ok = bot.login(args.email, args.password)
            if not login_ok:
                print("❌ Login failed.")
                sys.exit(1)

        bot.process_targets(targets)

    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted")
    finally:
        bot.close()

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Scraped: {bot.logger.stats['profiles_scraped']}")
    print(f"Sent: {bot.logger.stats['connections_sent']}")
    print(f"Failed: {bot.logger.stats['connections_failed']}")
    print(f"Screenshots: {SCREENSHOT_DIR}/")
    print(f"State: {STATE_FILE}")
    print("="*60)


if __name__ == "__main__":
    main()
