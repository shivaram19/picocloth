#!/usr/bin/env python3
"""
LinkedIn Outreach Bot — VDC Document Intelligence

End-to-end automation:
1. Log into LinkedIn
2. Scrape target profiles
3. Send personalized connection requests
4. Log all actions

⚠️  DISCLAIMER: LinkedIn automation violates their Terms of Service.
   Use at your own risk. This tool includes rate limiting and human-like
   delays to reduce detection risk, but NO automation is 100% safe.

   Recommended: Run with --dry-run first to preview all messages.
"""

import os
import sys
import json
import time
import random
import argparse
from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    ElementNotInteractableException, WebDriverException
)

# Load environment variables
load_dotenv()

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
MIN_DELAY = 3   # Minimum seconds between actions
MAX_DELAY = 8   # Maximum seconds between actions
CONNECT_DELAY_MIN = 30  # Minimum seconds between connection requests
CONNECT_DELAY_MAX = 90  # Maximum seconds between connection requests
DAILY_CONNECT_LIMIT = 20  # LinkedIn's soft limit for free accounts

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
# HUMAN-LIKE DELAYS
# ---------------------------------------------------------------------------
def human_delay(min_sec: float = MIN_DELAY, max_sec: float = MAX_DELAY):
    """Sleep for a random duration to mimic human behavior."""
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)


def random_scroll(driver):
    """Perform random scrolling to mimic human behavior."""
    scroll_pixels = random.randint(300, 1200)
    driver.execute_script(f"window.scrollBy(0, {scroll_pixels});")
    human_delay(1, 3)


# ---------------------------------------------------------------------------
# LINKEDIN OUTREACH BOT
# ---------------------------------------------------------------------------
class LinkedInOutreachBot:
    def __init__(self, headless: bool = False, dry_run: bool = False):
        self.headless = headless
        self.dry_run = dry_run
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.logger = OutreachLogger()
        self.connections_sent_today = 0

    def setup_driver(self):
        """Initialize Chrome WebDriver with anti-detection settings."""
        chrome_options = Options()

        # Anti-detection settings
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        # User agent (real Chrome on macOS)
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        if self.headless:
            chrome_options.add_argument("--headless=new")

        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        self.wait = WebDriverWait(self.driver, 15)
        self.driver.maximize_window()
        self.logger.log("DRIVER_SETUP", {"headless": self.headless})

    def login(self, email: str, password: str) -> bool:
        """Log into LinkedIn."""
        if self.dry_run:
            self.logger.log("LOGIN_SKIPPED_DRY_RUN")
            return True

        self.logger.log("LOGIN_START")
        self.driver.get("https://www.linkedin.com/login")
        human_delay(2, 4)

        try:
            # Enter email
            email_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            email_field.send_keys(email)
            human_delay(0.5, 1.5)

            # Enter password
            password_field = self.driver.find_element(By.ID, "password")
            password_field.send_keys(password)
            human_delay(0.5, 1.5)

            # Click submit
            submit_btn = self.driver.find_element(
                By.CSS_SELECTOR, "button[type='submit']"
            )
            submit_btn.click()
            human_delay(4, 7)

            # Check for verification challenges
            if "checkpoint" in self.driver.current_url:
                self.logger.log("LOGIN_VERIFICATION_REQUIRED", {
                    "url": self.driver.current_url
                })
                print("\n⚠️  LinkedIn is asking for verification.")
                print("Please complete the verification in the browser window.")
                print("Press ENTER here when done...")
                input()

            # Verify login success
            if "feed" in self.driver.current_url or "linkedin.com/in/" in self.driver.current_url:
                self.logger.log("LOGIN_SUCCESS")
                return True
            else:
                self.logger.error("Login may have failed", None)
                return False

        except Exception as e:
            self.logger.error("Login failed", e)
            return False

    def scrape_profile(self, profile_url: str) -> Dict:
        """Scrape a LinkedIn profile and return structured data."""
        self.logger.log("SCRAPE_START", {"url": profile_url})

        try:
            self.driver.get(profile_url)
            human_delay(3, 6)
            random_scroll(self.driver)

            # Extract name
            name = self._extract_name()

            # Extract headline/title
            headline = self._extract_headline()

            # Extract about
            about = self._extract_about()

            # Extract current company
            company = self._extract_current_company()

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
            self.logger.error(f"Scrape failed for {profile_url}", e)
            return {"error": str(e), "profile_url": profile_url}

    def _extract_name(self) -> str:
        """Extract profile name."""
        try:
            # Try h1 first
            name = self.driver.find_element(By.TAG_NAME, "h1").text.strip()
            if name and len(name) > 2:
                return name
        except Exception:
            pass

        # Fallback to title
        try:
            title = self.driver.title
            if " | LinkedIn" in title:
                return title.split(" | LinkedIn")[0].strip()
        except Exception:
            pass

        return "Unknown"

    def _extract_headline(self) -> str:
        """Extract profile headline."""
        try:
            # Common headline selectors
            selectors = [
                "//div[contains(@class, 'text-body-medium')][1]",
                "//div[contains(@class, 'pv-top-card-v2-ctas')]/preceding::div[contains(@class, 'text-body-medium')][1]",
            ]
            for sel in selectors:
                try:
                    el = self.driver.find_element(By.XPATH, sel)
                    text = el.text.strip()
                    if text and len(text) > 3:
                        return text
                except Exception:
                    continue
        except Exception:
            pass
        return ""

    def _extract_about(self) -> str:
        """Extract about section."""
        try:
            # Scroll to about section
            about_section = self.driver.find_elements(
                By.XPATH, "//section[.//h2//span[contains(text(), 'About')]]"
            )
            if about_section:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                    about_section[0]
                )
                human_delay(1, 2)

                # Click "Show more" if present
                show_more = self.driver.find_elements(
                    By.XPATH, "//section[.//h2//span[contains(text(), 'About')]]//button[contains(., 'more')]"
                )
                for btn in show_more:
                    try:
                        if btn.is_displayed():
                            self.driver.execute_script("arguments[0].click();", btn)
                            human_delay(0.5, 1)
                    except Exception:
                        pass

                # Extract text
                about_text = self.driver.find_elements(
                    By.XPATH,
                    "//section[.//h2//span[contains(text(), 'About')]]//div[contains(@class, 'inline-show-more-text')]"
                )
                if about_text:
                    return about_text[0].text.strip()
        except Exception:
            pass
        return ""

    def _extract_current_company(self) -> str:
        """Extract current company from experience section."""
        try:
            # Look for experience section
            exp_section = self.driver.find_elements(
                By.XPATH, "//section[.//h2//span[contains(text(), 'Experience')]]"
            )
            if exp_section:
                # First company link
                company_link = exp_section[0].find_elements(
                    By.XPATH, ".//a[contains(@href, '/company/')][1]"
                )
                if company_link:
                    return company_link[0].text.strip()
        except Exception:
            pass
        return ""

    def send_connection_request(self, profile_url: str, message: str) -> bool:
        """Send a personalized connection request."""
        if self.dry_run:
            self.logger.log("CONNECT_DRY_RUN", {
                "url": profile_url,
                "message": message
            })
            return True

        if self.connections_sent_today >= DAILY_CONNECT_LIMIT:
            self.logger.log("DAILY_LIMIT_REACHED", {
                "limit": DAILY_CONNECT_LIMIT
            })
            return False

        self.logger.log("CONNECT_START", {"url": profile_url})

        try:
            self.driver.get(profile_url)
            human_delay(3, 6)

            # Find and click "Connect" button
            connect_btn = self._find_connect_button()
            if not connect_btn:
                self.logger.log("CONNECT_BUTTON_NOT_FOUND", {"url": profile_url})
                return False

            connect_btn.click()
            human_delay(2, 4)

            # Check if "Add a note" option is available
            add_note_btn = self._find_add_note_button()
            if add_note_btn:
                add_note_btn.click()
                human_delay(1, 2)

                # Enter personalized message
                note_field = self.wait.until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//textarea[contains(@id, 'custom-message')]"
                    ))
                )
                note_field.send_keys(message)
                human_delay(1, 3)

                # Click Send
                send_btn = self.driver.find_element(
                    By.XPATH,
                    "//button[contains(@aria-label, 'Send invitation')]"
                )
                send_btn.click()
            else:
                # Just send without note
                send_btn = self.driver.find_element(
                    By.XPATH,
                    "//button[contains(@aria-label, 'Send invitation')]"
                )
                send_btn.click()

            human_delay(2, 4)
            self.connections_sent_today += 1
            self.logger.stats["connections_sent"] += 1
            self.logger.log("CONNECT_SENT", {
                "url": profile_url,
                "message_included": add_note_btn is not None
            })
            return True

        except Exception as e:
            self.logger.stats["connections_failed"] += 1
            self.logger.error(f"Connection failed for {profile_url}", e)
            return False

    def _find_connect_button(self):
        """Find the Connect button on a profile."""
        selectors = [
            "//button[contains(@aria-label, 'Connect')]",
            "//button[contains(., 'Connect')]",
            "//div[contains(@class, 'pv-top-card-v2-ctas')]//button[1]",
            "//main//button[contains(., 'Connect')]",
        ]
        for sel in selectors:
            try:
                btn = self.driver.find_element(By.XPATH, sel)
                if btn.is_displayed():
                    return btn
            except Exception:
                continue
        return None

    def _find_add_note_button(self):
        """Find the 'Add a note' button in the connection dialog."""
        try:
            btn = self.driver.find_element(
                By.XPATH, "//button[contains(@aria-label, 'Add a note')]"
            )
            if btn.is_displayed():
                return btn
        except Exception:
            pass
        return None

    def process_targets(self, targets: List[Dict]):
        """Process all targets: scrape + send connection requests."""
        self.logger.stats["targets_total"] = len(targets)
        self.logger.log("PROCESSING_START", {"total_targets": len(targets)})

        for i, target in enumerate(targets, 1):
            print(f"\n{'='*60}")
            print(f"Target {i}/{len(targets)}: {target['name']} ({target['company']})")
            print(f"Priority: {target['priority']}")
            print(f"{'='*60}")

            # Scrape profile
            profile_data = self.scrape_profile(target["profile_url"])

            # Generate personalized message
            message = target.get("connection_message", "")
            if not message:
                message = self._generate_message(target, profile_data)

            print(f"\nMessage preview:")
            print(f"{'-'*40}")
            print(message[:200] + "..." if len(message) > 200 else message)
            print(f"{'-'*40}")

            # Send connection request
            if not self.dry_run:
                success = self.send_connection_request(
                    target["profile_url"], message
                )
                if success:
                    # Delay before next connection
                    delay = random.uniform(CONNECT_DELAY_MIN, CONNECT_DELAY_MAX)
                    print(f"Waiting {delay:.0f}s before next target...")
                    time.sleep(delay)
            else:
                print("[DRY RUN] Connection not sent")

            # Save progress after each target
            self._save_progress(targets, i)

        self.logger.log("PROCESSING_COMPLETE")
        self.logger.save_stats()

    def _generate_message(self, target: Dict, profile_data: Dict) -> str:
        """Generate a personalized connection message."""
        name = profile_data.get("name", target["name"]).split()[0]
        company = profile_data.get("company", target["company"])

        templates = {
            "high": f"Hi {name}, I came across {company} while researching innovative VDC agencies. We're building an AI document intelligence platform that auto-drafts RFIs and flags spec-drawing contradictions. Would love to connect and share what we've built.",
            "medium": f"Hi {name}, {company}'s work in digital construction caught my attention. I'm building a white-label AI platform for VDC agencies — it reduces spec review time by 80%. Worth a brief conversation?",
            "low": f"Hi {name}, I noticed {company}'s focus on construction technology. We're developing AI-powered document intelligence for AEC service providers. Would love to connect and explore potential synergy."
        }
        return templates.get(target["priority"], templates["medium"])

    def _save_progress(self, targets: List[Dict], completed: int):
        """Save progress to a JSON file."""
        progress = {
            "completed": completed,
            "total": len(targets),
            "remaining": len(targets) - completed,
            "last_updated": datetime.now().isoformat(),
            "connections_sent_today": self.connections_sent_today
        }
        with open("outreach_progress.json", "w", encoding="utf-8") as f:
            json.dump(progress, f, indent=2)

    def close(self):
        """Clean up resources."""
        if self.driver:
            self.driver.quit()
        self.logger.save_stats()
        self.logger.log("BOT_SHUTDOWN")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="LinkedIn Outreach Bot for VDC Document Intelligence"
    )
    parser.add_argument(
        "--targets", default="targets.json",
        help="Path to targets JSON file"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview messages without sending (RECOMMENDED FIRST RUN)"
    )
    parser.add_argument(
        "--headless", action="store_true",
        help="Run browser in headless mode (higher detection risk)"
    )
    parser.add_argument(
        "--email", default=os.getenv("LINKEDIN_EMAIL"),
        help="LinkedIn email (or set LINKEDIN_EMAIL env var)"
    )
    parser.add_argument(
        "--password", default=os.getenv("LINKEDIN_PASSWORD"),
        help="LinkedIn password (or set LINKEDIN_PASSWORD env var)"
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Limit number of targets to process (0 = all)"
    )
    args = parser.parse_args()

    # Validate credentials
    if not args.dry_run and (not args.email or not args.password):
        print("❌ Error: LinkedIn credentials required.")
        print("Set LINKEDIN_EMAIL and LINKEDIN_PASSWORD in .env")
        print("Or use --email and --password flags")
        sys.exit(1)

    # Load targets
    if not os.path.exists(args.targets):
        print(f"❌ Error: Targets file not found: {args.targets}")
        sys.exit(1)

    with open(args.targets, "r", encoding="utf-8") as f:
        targets_data = json.load(f)
    targets = targets_data.get("targets", [])

    if args.limit > 0:
        targets = targets[:args.limit]

    print("\n" + "="*60)
    print("LINKEDIN OUTREACH BOT — VDC Document Intelligence")
    print("="*60)
    print(f"Mode: {'DRY RUN (preview only)' if args.dry_run else 'LIVE'}")
    print(f"Targets: {len(targets)}")
    print(f"Headless: {args.headless}")
    print("="*60 + "\n")

    if not args.dry_run:
        print("⚠️  WARNING: This will send REAL LinkedIn connection requests.")
        print(f"Daily limit: {DAILY_CONNECT_LIMIT} connections")
        confirm = input("Proceed? (yes/no): ")
        if confirm.lower() != "yes":
            print("Aborted.")
            sys.exit(0)

    # Initialize and run bot
    bot = LinkedInOutreachBot(headless=args.headless, dry_run=args.dry_run)

    try:
        bot.setup_driver()

        if not args.dry_run:
            login_success = bot.login(args.email, args.password)
            if not login_success:
                print("❌ Login failed. Check credentials and try again.")
                sys.exit(1)

        bot.process_targets(targets)

    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted by user.")
    finally:
        bot.close()

    # Print summary
    print("\n" + "="*60)
    print("OUTREACH SUMMARY")
    print("="*60)
    print(f"Profiles scraped: {bot.logger.stats['profiles_scraped']}")
    print(f"Connections sent: {bot.logger.stats['connections_sent']}")
    print(f"Connections failed: {bot.logger.stats['connections_failed']}")
    print(f"Errors: {len(bot.logger.stats['errors'])}")
    print(f"Log file: {bot.logger.log_file}")
    print(f"Stats file: outreach_stats.json")
    print("="*60)


if __name__ == "__main__":
    main()
