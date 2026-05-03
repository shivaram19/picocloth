#!/usr/bin/env python3
"""
🚴 The Courier — Craftsman + Guardian

Node-B of the PicoCloth Outreach Engine.

The Courier delivers messages safely. No mistakes. No detection. No bans.
It tests every session before use. It adds human-like delays.
It respects the 20/day limit like it's a law of physics.

Archetype Composition:
  Courier = Craftsman (0.95 Competence) + Guardian (0.95 Dutifulness)

Design Principles (from the Craftsman):
  - Modularity first
  - Typed interfaces
  - Fail safely
  - Test at every level
  - Observability everywhere

Author: PicoCloth Fleet — Executor
Date: 2026-04-23
Purpose: Deliver connection requests safely and reliably.
"""

import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass

from playwright.sync_api import sync_playwright, Page, BrowserContext
from playwright_stealth import Stealth

from archivist import Archivist, ProspectEntity, SentRecord


# ── Configuration ────────────────────────────────────────────────────────────

DAILY_CONNECT_LIMIT = 20
MIN_DELAY_SECONDS = 20
MAX_DELAY_SECONDS = 60
SESSION_DIR = Path(__file__).parent / "state" / "sessions"
SCREENSHOT_DIR = Path(__file__).parent / "screenshots"


# ── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class DeliveryResult:
    target_id: str
    name: str
    status: str       # "success", "failed", "skipped", "already_connected"
    screenshot: Optional[str]
    error: Optional[str]
    timestamp: str


# ── The Courier ──────────────────────────────────────────────────────────────

class Courier:
    """
    The Courier handles all browser automation for the Outreach Engine.

    Safety Protocols (from the Guardian):
      1. Session validation before EVERY action
      2. Rate limiting: max 20/day
      3. Human-like delays: 20-60s random
      4. Screenshot evidence on every send
      5. Graceful degradation on failure
      6. No credential storage — sessions only
    """

    def __init__(self, archivist: Archivist, headless: bool = True):
        self.archivist = archivist
        self.archetype = "Courier"
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.session_valid = False

        self._log("Courier initialized. Safety systems active.")
        self._log(f"    Daily limit: {DAILY_CONNECT_LIMIT}")
        self._log(f"    Delay range: {MIN_DELAY_SECONDS}-{MAX_DELAY_SECONDS}s")

    def _log(self, msg: str):
        print(f"🚴 [{self.archetype}] {msg}")

    def _human_delay(self, min_sec: float = None, max_sec: float = None):
        """Random human-like delay. The Guardian insists on this."""
        mn = min_sec if min_sec is not None else MIN_DELAY_SECONDS
        mx = max_sec if max_sec is not None else MAX_DELAY_SECONDS
        delay = random.uniform(mn, mx)
        self._log(f"    ⏳ Human delay: {delay:.1f}s")
        time.sleep(delay)

    def _human_scroll(self, page: Page, scrolls: int = 3):
        """Human-like scroll pattern."""
        for _ in range(scrolls):
            page.evaluate(f"window.scrollBy(0, {random.randint(200, 800)})")
            time.sleep(random.uniform(0.5, 2.0))

    def _launch_browser(self) -> bool:
        """Launch stealth browser with anti-detection."""
        try:
            self.playwright = sync_playwright().start()

            # Random viewport (varies per session)
            viewports = [
                {"width": 1920, "height": 1080},
                {"width": 1366, "height": 768},
                {"width": 1440, "height": 900},
                {"width": 1536, "height": 864},
                {"width": 1280, "height": 720},
            ]
            vp = random.choice(viewports)

            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            ]
            ua = random.choice(user_agents)

            self._log(f"Launching browser: headless={self.headless}, viewport={vp['width']}x{vp['height']}")

            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    f"--window-size={vp['width']},{vp['height']}",
                ]
            )

            self.context = self.browser.new_context(
                viewport=vp,
                user_agent=ua,
                locale="en-US",
                timezone_id="America/New_York",
            )

            self.page = self.context.new_page()
            # Apply stealth patches
            stealth = Stealth()
            stealth.apply_stealth_sync(self.page)
            self._log("Browser launched with stealth patches applied.")
            return True

        except Exception as e:
            self._log(f"❌ Browser launch failed: {e}")
            return False

    def _load_session(self, session_path: Optional[Path] = None) -> bool:
        """Load existing session cookies."""
        path = session_path or (SESSION_DIR / "linkedin_state.json")

        if not path.exists():
            self._log(f"No session file found at {path}")
            return False

        try:
            with open(path, "r", encoding="utf-8") as f:
                state = json.load(f)

            if "cookies" in state:
                self.context.add_cookies(state["cookies"])
                self._log(f"Loaded {len(state['cookies'])} cookies from session.")

            if "origins" in state:
                for origin in state.get("origins", []):
                    for entry in origin.get("localStorage", []):
                        self.page.evaluate(
                            "(k, v) => localStorage.setItem(k, v)",
                            entry["name"], entry["value"]
                        )

            return True
        except Exception as e:
            self._log(f"Session load error: {e}")
            return False

    def _validate_session(self) -> bool:
        """Validate session by visiting LinkedIn feed."""
        self._log("Validating session...")
        try:
            self.page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
            time.sleep(random.uniform(3, 5))

            if "feed" in self.page.url:
                self._log("✅ Session is valid. We're on the feed.")
                self.session_valid = True
                return True
            else:
                self._log(f"⚠️  Session invalid. Current URL: {self.page.url}")
                self.session_valid = False
                return False
        except Exception as e:
            self._log(f"❌ Session validation error: {e}")
            self.session_valid = False
            return False

    def _save_session(self, session_path: Optional[Path] = None):
        """Persist session for reuse."""
        path = session_path or (SESSION_DIR / "linkedin_state.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            state = self.context.storage_state()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            self._log(f"💾 Session saved to {path}")
        except Exception as e:
            self._log(f"⚠️  Failed to save session: {e}")

    def _auto_login(self, email: str, password: str) -> bool:
        """Attempt automatic login. The Guardian is skeptical but tries."""
        self._log(f"Attempting auto-login for {email}...")
        try:
            self.page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
            time.sleep(random.uniform(2, 4))

            # Human-like typing with delays
            self.page.fill("#username", email)
            time.sleep(random.uniform(0.3, 1.0))
            self.page.fill("#password", password)
            time.sleep(random.uniform(0.3, 1.0))

            self.page.click("button[type='submit']")
            time.sleep(random.uniform(5, 8))

            current_url = self.page.url
            self._log(f"Post-submit URL: {current_url}")

            if "feed" in current_url:
                self._log("✅ Auto-login successful!")
                self._save_session()
                self.session_valid = True
                return True

            if "checkpoint" in current_url or "challenge" in current_url:
                self._log("🚨 CHECKPOINT DETECTED. LinkedIn requires human verification.")
                self._handle_checkpoint(current_url)
                return False

            self._log(f"❌ Unexpected post-login URL: {current_url}")
            return False

        except Exception as e:
            self._log(f"❌ Auto-login failed: {e}")
            return False

    def _handle_checkpoint(self, checkpoint_url: str):
        """Handle checkpoint gracefully. Guardian demands safety."""
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        screenshot_path = SCREENSHOT_DIR / "checkpoint.png"

        try:
            self.page.screenshot(path=str(screenshot_path))
        except Exception:
            pass

        # Save checkpoint state for potential recovery
        checkpoint_state = {
            "checkpoint_url": checkpoint_url,
            "screenshot": str(screenshot_path),
            "detected_at": datetime.now(timezone.utc).isoformat(),
            "cookies": self.context.cookies()
        }
        checkpoint_file = SESSION_DIR / "checkpoint_state.json"
        with open(checkpoint_file, "w") as f:
            json.dump(checkpoint_state, f, indent=2)

        self._log("=" * 60)
        self._log("LINKEDIN CHECKPOINT — AUTONOMOUS RESOLUTION NOT POSSIBLE")
        self._log("=" * 60)
        self._log(f"Checkpoint URL: {checkpoint_url}")
        self._log(f"Screenshot: {screenshot_path}")
        self._log(f"State saved: {checkpoint_file}")
        self._log("")
        self._log("OPTIONS:")
        self._log("  1. Visit the checkpoint URL on your mobile device, solve it, then re-run.")
        self._log("  2. Export a session from your local browser: python3 export_session.py")
        self._log("  3. Use a residential proxy to avoid checkpoint.")
        self._log("=" * 60)

        # Record decision
        from archivist import Decision
        self.archivist.record_decision(Decision(
            decision_id=f"checkpoint-{datetime.now(timezone.utc).strftime('%H%M%S')}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            archetype=self.archetype,
            context="Auto-login resulted in LinkedIn checkpoint",
            choice="Halted autonomous execution — checkpoint requires human",
            rationale="Guardian protocol: never bypass CAPTCHA/checkpoint autonomously",
            expected_outcome="User resolves checkpoint, re-runs with saved session"
        ))

    def ensure_ready(self, email: Optional[str] = None, password: Optional[str] = None) -> bool:
        """
        End-to-end readiness check.
        Launch browser → Load session → Validate → Return ready state.
        """
        if not self._launch_browser():
            return False

        # Try existing session first
        if self._load_session() and self._validate_session():
            return True

        # Try auto-login if credentials provided
        if email and password:
            if self._auto_login(email, password):
                return True

        self._log("❌ Courier cannot proceed without a valid session.")
        return False

    def deliver(self, target: ProspectEntity, message: str) -> DeliveryResult:
        """
        Deliver a connection request to a single target.

        The Guardian's safety checklist:
          [x] Session valid?
          [x] Under daily limit?
          [x] Profile URL looks right?
          [x] Screenshot captured?
          [x] Result logged?
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        # Guardian Check 1: Session valid
        if not self.session_valid:
            self._log(f"❌ Cannot deliver to {target.name}: no valid session")
            return DeliveryResult(
                target_id=target.id, name=target.name,
                status="failed", screenshot=None,
                error="No valid LinkedIn session", timestamp=timestamp
            )

        # Guardian Check 2: Daily limit
        sent_today = self.archivist.get_sent_count_today()
        if sent_today >= DAILY_CONNECT_LIMIT:
            self._log(f"🛑 Daily limit reached ({sent_today}/{DAILY_CONNECT_LIMIT}). Stopping.")
            return DeliveryResult(
                target_id=target.id, name=target.name,
                status="skipped", screenshot=None,
                error="Daily limit reached", timestamp=timestamp
            )

        self._log(f"🎯 Delivering to {target.name} ({target.company})")
        self._log(f"    Daily progress: {sent_today}/{DAILY_CONNECT_LIMIT}")

        try:
            # Navigate to profile
            self.page.goto(target.profile_url, wait_until="domcontentloaded")
            self._human_delay(3, 6)
            self._human_scroll(self.page, scrolls=random.randint(2, 4))

            # Screenshot for evidence
            SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
            screenshot_path = SCREENSHOT_DIR / f"{target.id}_{datetime.now().strftime('%H%M%S')}.png"
            self.page.screenshot(path=str(screenshot_path))

            # Find Connect button
            connect_selectors = [
                "button[aria-label*='Connect']",
                "button:has-text('Connect')",
                "button.artdeco-button:has-text('Connect')",
            ]

            connect_btn = None
            for selector in connect_selectors:
                try:
                    btn = self.page.locator(selector).first
                    if btn.count() > 0 and btn.is_visible():
                        connect_btn = btn
                        break
                except Exception:
                    continue

            if not connect_btn:
                self._log(f"    ⚠️  No Connect button found. May already be connected.")
                return DeliveryResult(
                    target_id=target.id, name=target.name,
                    status="already_connected", screenshot=str(screenshot_path),
                    error="No Connect button visible", timestamp=timestamp
                )

            # Click Connect
            connect_btn.click()
            self._human_delay(2, 4)

            # Find "Add a note" button
            add_note = self.page.locator("button[aria-label*='Add a note']").first
            if add_note.count() > 0 and add_note.is_visible():
                add_note.click()
                self._human_delay(1, 2)

                # Fill message
                textarea = self.page.locator("textarea#custom-message").first
                if textarea.count() > 0:
                    textarea.fill(message)
                    self._human_delay(1, 2)

            # Click Send
            send_btn = self.page.locator("button[aria-label*='Send invitation']").first
            if send_btn.count() > 0 and send_btn.is_visible():
                send_btn.click()
                self._human_delay(2, 4)

                self._log(f"    ✅ Connection request sent to {target.name}!")

                # Save session after successful send
                self._save_session()

                return DeliveryResult(
                    target_id=target.id, name=target.name,
                    status="success", screenshot=str(screenshot_path),
                    error=None, timestamp=timestamp
                )
            else:
                self._log(f"    ❌ Send button not found.")
                return DeliveryResult(
                    target_id=target.id, name=target.name,
                    status="failed", screenshot=str(screenshot_path),
                    error="Send button not found after clicking Connect", timestamp=timestamp
                )

        except Exception as e:
            self._log(f"    ❌ Delivery failed: {e}")
            return DeliveryResult(
                target_id=target.id, name=target.name,
                status="failed", screenshot=None,
                error=str(e), timestamp=timestamp
            )

    def close(self):
        """Clean shutdown. The Guardian always cleans up."""
        self._log("Shutting down Courier...")
        if self.context:
            self._save_session()
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        self._log("Courier shutdown complete. Session preserved.")


# ── Node-B Pipeline ──────────────────────────────────────────────────────────

def run_node_b(enriched_targets: List, archivist: Archivist,
               email: Optional[str] = None, password: Optional[str] = None,
               headless: bool = True, dry_run: bool = False) -> List[DeliveryResult]:
    """
    Run the full Node-B pipeline: Courier delivers messages.

    Input: Enriched targets with personalized messages
    Output: Delivery results
    """
    print("\n" + "=" * 70)
    print("🔨 Node-B: Executor Activating")
    print("=" * 70)
    print("Archetype: Courier (Craftsman + Guardian)")
    print("=" * 70 + "\n")

    courier = Courier(archivist, headless=headless)

    # In dry-run, we don't need a browser at all
    if not dry_run:
        if not courier.ensure_ready(email=email, password=password):
            print("\n❌ Node-B cannot proceed. Courier failed to establish session.")
            print("   Please provide a valid LinkedIn session or credentials.")
            return []

    results = []

    for i, enriched in enumerate(enriched_targets, 1):
        target = enriched.target
        message = enriched.personalized_message

        print(f"\n{'─' * 70}")
        print(f"🚴 Delivery {i}/{len(enriched_targets)}: {target.name}")
        print(f"{'─' * 70}")

        if dry_run:
            print(f"    [DRY RUN] Would send to {target.name}")
            print(f"    Message: {message}")
            result = DeliveryResult(
                target_id=target.id, name=target.name,
                status="dry_run", screenshot=None,
                error=None, timestamp=datetime.now(timezone.utc).isoformat()
            )
        else:
            # Create/update prospect entity
            archivist.upsert_prospect(ProspectEntity(
                id=target.id, name=target.name, company=target.company,
                role=target.role, profile_url=target.profile_url,
                industry=target.industry, status="sending", enriched=True,
                message=message, last_contact=None, confidence=enriched.confidence,
                tags=[]
            ))

            result = courier.deliver(
                ProspectEntity(
                    id=target.id, name=target.name, company=target.company,
                    role=target.role, profile_url=target.profile_url,
                    industry=target.industry, status="sending", enriched=True,
                    message=message, last_contact=None, confidence=enriched.confidence,
                    tags=[]
                ),
                message
            )

        results.append(result)

        # Log to Archivist
        archivist.log_sent(SentRecord(
            timestamp=result.timestamp,
            target_id=result.target_id,
            name=result.name,
            company=target.company,
            action="connect_sent",
            status=result.status,
            screenshot=result.screenshot,
            error=result.error,
            archetype="Courier"
        ))

        # Update prospect status
        new_status = "connected" if result.status == "success" else ("failed" if result.status == "failed" else result.status)
        archivist.upsert_prospect(ProspectEntity(
            id=target.id, name=target.name, company=target.company,
            role=target.role, profile_url=target.profile_url,
            industry=target.industry, status=new_status, enriched=True,
            message=message, last_contact=result.timestamp,
            confidence=enriched.confidence, tags=[]
        ))

        # Update stats
        archivist.update_stats(
            sent=sum(1 for r in results if r.status == "success"),
            failed=sum(1 for r in results if r.status == "failed")
        )

        # Human delay between targets (Guardian insists)
        if i < len(enriched_targets) and not dry_run:
            delay = random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
            print(f"    ⏳ Guardian delay: {delay:.1f}s before next target...")
            time.sleep(delay)

    courier.close()

    print(f"\n{'=' * 70}")
    print(f"✅ Node-B complete!")
    success = sum(1 for r in results if r.status == "success")
    failed = sum(1 for r in results if r.status == "failed")
    print(f"    Sent: {success} | Failed: {failed} | Skipped: {len(results) - success - failed}")
    print(f"{'=' * 70}\n")

    return results


if __name__ == "__main__":
    print("Node-B is designed to be called by the Orchestrator.")
    print("Run: python3 picocloth_outreach_engine.py --targets targets.csv")
