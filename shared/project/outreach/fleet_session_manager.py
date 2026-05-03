#!/usr/bin/env python3
"""
Fleet Session Manager — PicoCloth Outreach Engine

Handles LinkedIn session lifecycle end-to-end:
  - Detect existing valid sessions
  - Auto-login with stealth (if no session)
  - Handle checkpoint/verification gracefully
  - Persist sessions for reuse
  - Warm up sessions before use

Part of the PicoCloth fleet. Node-B delegates session management here.
"""

import json
import os
import time
import random
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
from dotenv import load_dotenv

from playwright.sync_api import sync_playwright, BrowserContext, Page
from playwright_stealth import Stealth

load_dotenv()

SESSION_DIR = Path(__file__).parent / "state" / "sessions"
SESSION_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = Path(__file__).parent / "logs" / "session_manager.jsonl"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


def log_event(event: str, data: Dict = None):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "event": event,
        "data": data or {}
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"[SESSION] {event}")


class FleetSessionManager:
    """Manages LinkedIn browser sessions for the PicoCloth fleet."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.browser = None
        self.session_path = SESSION_DIR / "linkedin_state.json"

    def _launch_browser(self):
        """Launch stealth browser with anti-detection."""
        self.playwright = sync_playwright().start()

        # Random realistic viewport
        viewports = [
            {"width": 1920, "height": 1080},
            {"width": 1366, "height": 768},
            {"width": 1440, "height": 900},
            {"width": 1536, "height": 864},
        ]
        vp = random.choice(viewports)

        # Realistic user agents
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
        ua = random.choice(user_agents)

        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--window-size={},{}".format(vp["width"], vp["height"]),
            ]
        )

        self.context = self.browser.new_context(
            viewport=vp,
            user_agent=ua,
            locale="en-US",
            timezone_id="America/New_York",
            geolocation={"latitude": 40.7128, "longitude": -74.0060},  # NYC
            permissions=["geolocation"],
        )

        # Apply stealth patches
        stealth = Stealth()
        self.page = self.context.new_page()
        stealth.apply_stealth_sync(self.page)
        log_event("BROWSER_LAUNCHED", {"viewport": vp, "headless": self.headless})

    def _human_delay(self, min_sec: float = 1.0, max_sec: float = 3.0):
        """Random human-like delay."""
        time.sleep(random.uniform(min_sec, max_sec))

    def _human_scroll(self, page: Page):
        """Human-like scroll pattern."""
        for _ in range(random.randint(2, 5)):
            page.evaluate("window.scrollBy(0, {})".format(random.randint(200, 600)))
            time.sleep(random.uniform(0.5, 1.5))

    def load_existing_session(self) -> bool:
        """Try to load an existing session state file."""
        if not self.session_path.exists():
            log_event("NO_EXISTING_SESSION")
            return False

        try:
            with open(self.session_path, "r") as f:
                state = json.load(f)

            if "cookies" in state:
                self.context.add_cookies(state["cookies"])
            if "origins" in state:
                for origin in state.get("origins", []):
                    for entry in origin.get("localStorage", []):
                        self.page.evaluate(
                            "(key, value) => { localStorage.setItem(key, value); }",
                            entry["name"], entry["value"]
                        )

            log_event("SESSION_LOADED", {"cookies": len(state.get("cookies", []))})

            # Validate: visit feed
            self.page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
            self._human_delay(3, 5)

            if "feed" in self.page.url:
                log_event("SESSION_VALID")
                self._human_scroll(self.page)
                return True
            else:
                log_event("SESSION_INVALID", {"url": self.page.url})
                return False

        except Exception as e:
            log_event("SESSION_LOAD_ERROR", {"error": str(e)})
            return False

    def auto_login(self, email: str, password: str) -> bool:
        """Attempt automatic login with stealth. Returns True on success."""
        log_event("AUTO_LOGIN_START", {"email": email})

        try:
            self.page.goto("https://www.linkedin.com/", wait_until="domcontentloaded")
            self._human_delay(2, 4)

            # Click "Sign in" if on homepage
            sign_in = self.page.locator("a[data-tracking-control-name='guest_homepage-basic_nav-header-signin']").first
            if sign_in.count() > 0 and sign_in.is_visible():
                sign_in.click()
                self._human_delay(2, 3)

            # Fill credentials with human-like typing
            self.page.fill("#username", email)
            self._human_delay(0.5, 1.5)
            self.page.fill("#password", password)
            self._human_delay(0.5, 1.5)

            # Submit
            self.page.click("button[type='submit']")
            self._human_delay(5, 8)

            current_url = self.page.url
            log_event("LOGIN_SUBMITTED", {"url": current_url})

            # Check result
            if "feed" in current_url:
                log_event("AUTO_LOGIN_SUCCESS")
                self._save_session()
                return True

            if "checkpoint" in current_url or "challenge" in current_url:
                log_event("CHECKPOINT_DETECTED", {"url": current_url})
                self._handle_checkpoint(current_url)
                return False

            log_event("LOGIN_UNEXPECTED_URL", {"url": current_url})
            return False

        except Exception as e:
            log_event("AUTO_LOGIN_ERROR", {"error": str(e)})
            return False

    def _handle_checkpoint(self, checkpoint_url: str):
        """Handle LinkedIn checkpoint. Takes screenshot, saves state for human resolution."""
        screenshot_path = Path(__file__).parent / "screenshots" / "checkpoint.png"
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(screenshot_path))

        # Extract cookies at checkpoint state
        cookies = self.context.cookies()
        checkpoint_state = {
            "checkpoint_url": checkpoint_url,
            "cookies": cookies,
            "screenshot": str(screenshot_path),
            "detected_at": datetime.now().isoformat()
        }
        checkpoint_file = SESSION_DIR / "checkpoint_state.json"
        with open(checkpoint_file, "w") as f:
            json.dump(checkpoint_state, f, indent=2)

        log_event("CHECKPOINT_STATE_SAVED", {
            "url": checkpoint_url,
            "screenshot": str(screenshot_path),
            "checkpoint_file": str(checkpoint_file)
        })

        print("\n" + "=" * 70)
        print("⚠️  LINKEDIN CHECKPOINT DETECTED")
        print("=" * 70)
        print(f"Checkpoint URL: {checkpoint_url}")
        print(f"Screenshot: {screenshot_path}")
        print(f"State saved: {checkpoint_file}")
        print("")
        print("The PicoCloth fleet cannot solve CAPTCHAs autonomously.")
        print("Options:")
        print("  1. Visit the checkpoint URL on your mobile device and solve it.")
        print("  2. Use a residential proxy to avoid checkpoint.")
        print("  3. Export a session from your local browser.")
        print("=" * 70)

    def _save_session(self):
        """Persist session state for reuse."""
        state = self.context.storage_state()
        with open(self.session_path, "w") as f:
            json.dump(state, f, indent=2)
        log_event("SESSION_SAVED", {"path": str(self.session_path)})

    def ensure_session(self) -> bool:
        """End-to-end: launch browser, load or create session, return True if ready."""
        self._launch_browser()

        if self.load_existing_session():
            return True

        # Try auto-login with credentials from env
        email = os.getenv("LINKEDIN_EMAIL")
        password = os.getenv("LINKEDIN_PASSWORD")

        if email and password:
            if self.auto_login(email, password):
                return True

        log_event("SESSION_ENSURE_FAILED")
        return False

    def get_context_and_page(self) -> tuple[BrowserContext, Page]:
        """Return active context and page for Node-B to use."""
        return self.context, self.page

    def close(self):
        if self.context:
            self._save_session()
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        log_event("BROWSER_CLOSED")


if __name__ == "__main__":
    mgr = FleetSessionManager(headless=True)
    ready = mgr.ensure_session()
    print(f"\nSession ready: {ready}")
    if ready:
        ctx, page = mgr.get_context_and_page()
        print(f"Current URL: {page.url}")
    mgr.close()
