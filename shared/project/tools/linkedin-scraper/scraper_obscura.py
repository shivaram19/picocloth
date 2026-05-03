"""
LinkedIn Profile Scraper – OBSCURA + PLAYWRIGHT VERSION

Uses Obscura (stealth headless browser) via Chrome DevTools Protocol.
This avoids Chrome's heavy footprint and leverages built-in anti-detection.

OUTPUT FIELDS:
- name
- about
- full_time_companies_count
- latest_company_url
- scrape_time_seconds

USAGE:
    # 1. Start Obscura manually:
    ./obscura serve --port 9222 --stealth

    # 2. Run scraper (attach mode connects to existing Obscura):
    python scraper_obscura.py --profile "https://www.linkedin.com/in/nitishchoudhary/" --attach

    # Or let the scraper manage Obscura lifecycle:
    python scraper_obscura.py --profile "https://www.linkedin.com/in/nitishchoudhary/"
"""

import os
import re
import json
import time
import argparse
from typing import Tuple, Set, Dict, Optional
from dotenv import load_dotenv

from playwright.sync_api import sync_playwright, Page, BrowserContext

from obscura_manager import ObscuraManager


def logger_info(msg: str):
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - INFO - {msg}")


class LinkedInObscuraScraper:
    """
    LinkedIn scraper backed by Obscura via Playwright CDP connection.
    """

    def __init__(
        self,
        attach: bool = False,
        headless: bool = True,
        stealth: bool = True,
        port: int = 9222,
    ):
        self.attach = attach
        self.headless = headless
        self.stealth = stealth
        self.port = port

        self._playwright = None
        self._browser = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._obscura_mgr: Optional[ObscuraManager] = None

    # ---------------------------------------------------------
    # Setup / Teardown
    # ---------------------------------------------------------
    def setup(self):
        """Launch Playwright and connect to Obscura."""
        self._playwright = sync_playwright().start()

        if self.attach:
            # Connect to already-running Obscura
            ws_endpoint = f"ws://127.0.0.1:{self.port}"
            logger_info(f"Connecting to Obscura at {ws_endpoint} …")
            self._browser = self._playwright.chromium.connect_over_cdp(ws_endpoint)
        else:
            # Start our own Obscura instance
            self._obscura_mgr = ObscuraManager(
                port=self.port,
                stealth=self.stealth,
                verbose=True,
            )
            ws_endpoint = self._obscura_mgr.start()
            self._browser = self._playwright.chromium.connect_over_cdp(ws_endpoint)

        # Use existing default context or create one
        if self._browser.contexts:
            self._context = self._browser.contexts[0]
        else:
            self._context = self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
            )

        self._page = self._context.new_page()
        logger_info("Playwright page ready.")

    def close(self):
        if self._page:
            self._page.close()
            self._page = None
        if self._context:
            self._context.close()
            self._context = None
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._obscura_mgr:
            self._obscura_mgr.stop()
            self._obscura_mgr = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None

    # ---------------------------------------------------------
    # Login
    # ---------------------------------------------------------
    def login(self, email: str, password: str):
        if self.attach:
            logger_info("✅ Attach mode – skipping login.")
            return

        if not email or not password:
            raise ValueError("LINKEDIN_EMAIL / LINKEDIN_PASSWORD missing in .env")

        logger_info("🔐 Logging in via LinkedIn …")
        page = self._page
        page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")

        page.locator("#username").fill(email)
        page.locator("#password").fill(password)
        page.locator("button[type='submit']").click()

        # Wait for navigation to feed or similar logged-in indicator
        page.wait_for_load_state("networkidle", timeout=15000)
        logger_info("✅ Login complete.")

    # ---------------------------------------------------------
    # Navigation helpers
    # ---------------------------------------------------------
    def _normalize_profile_url(self, profile: str) -> str:
        if profile.startswith("http"):
            base = profile.split("?")[0].strip()
            if "/details/" in base:
                base = base.split("/details/")[0] + "/"
            if "/recent-activity" in base:
                base = base.split("/recent-activity")[0] + "/"
            if not base.endswith("/"):
                base += "/"
            return base
        return f"https://www.linkedin.com/in/{profile.strip().strip('/')}/"

    def _wait_profile_hydrated(self):
        """Wait until the profile top-section is visible."""
        page = self._page
        try:
            page.wait_for_selector("main", timeout=5000)
        except Exception:
            page.wait_for_selector("body", timeout=5000)

        # Try multiple name selectors
        selectors = [
            "xpath=//h1",
            "xpath=//h2[contains(@class, 'bc8ea8e7')]",
            "xpath=//h2[contains(@class, '_478c24fe')]",
            "xpath=//*[@role='main']//h2[1]",
        ]
        for sel in selectors:
            try:
                page.locator(sel).first.wait_for(state="visible", timeout=2000)
                return
            except Exception:
                continue
        time.sleep(1)

    def _fast_scroll(self, px: int = 1500):
        self._page.evaluate(f"window.scrollBy(0, {px});")

    def _scroll_until_experience(self, max_tries: int = 5) -> bool:
        for _ in range(max_tries):
            try:
                if self._page.locator("xpath=//section[.//h2[normalize-space()='Experience']]").is_visible(timeout=1000):
                    return True
            except Exception:
                pass
            self._fast_scroll(2000)
            time.sleep(0.2)
        return False

    # ---------------------------------------------------------
    # Extraction
    # ---------------------------------------------------------
    def extract_name(self) -> str:
        page = self._page
        # Strategy 1: document title (fastest)
        try:
            title = page.title()
            if " | LinkedIn" in title:
                raw_name = title.split(" | LinkedIn")[0].strip()
                clean_name = re.sub(r'^\(\d+\)\s*', '', raw_name)
                if clean_name and len(clean_name) > 2:
                    return clean_name
        except Exception:
            pass

        # Strategy 2: DOM selectors
        selectors = [
            "xpath=//h1",
            "xpath=//h2[contains(@class, 'bc8ea8e7')]",
            "xpath=//h2[contains(@class, '_478c24fe')]",
            "xpath=//h2[contains(@class, '_9113d2b2')]",
            "xpath=//*[@role='main']//h2[normalize-space()]",
        ]
        for sel in selectors:
            try:
                el = page.locator(sel).first
                name = el.inner_text(timeout=2000).strip()
                if not name or len(name) < 3:
                    continue
                skip = ["notification", "linkedin", "message", "connection", "·"]
                if any(kw in name.lower() for kw in skip):
                    continue
                if sum(c.isdigit() for c in name) > len(name) / 2:
                    continue
                return name
            except Exception:
                continue
        return "Not available"

    def extract_about(self) -> str:
        page = self._page
        try:
            # Strategy 1: id='about' anchor
            about_locator = page.locator(
                "xpath=//*[@id='about']/following-sibling::div//div[contains(@class, 'inline-show-more-text')]"
            )
            if about_locator.count() == 0:
                about_locator = page.locator(
                    "xpath=//*[@id='about']/parent::*//div[contains(@class, 'inline-show-more-text')]"
                )
            if about_locator.count() > 0:
                txt = about_locator.first.inner_text(timeout=2000).strip()
                if txt:
                    return txt
        except Exception:
            pass

        # Strategy 2: section header scan
        try:
            section = page.locator("xpath=//section[.//h2[normalize-space()='About']]").first
            txt = section.inner_text(timeout=2000).replace("About", "").strip()
            if txt:
                return txt
        except Exception:
            pass

        return "Not available"

    def extract_experience_fast(self) -> Tuple[int, str]:
        """
        Returns (full_time_companies_count, latest_company_url)
        """
        page = self._page
        found = self._scroll_until_experience()
        if not found:
            return 0, "Not available"

        try:
            exp_section = page.locator("xpath=//section[.//h2[normalize-space()='Experience']]").first
        except Exception:
            return 0, "Not available"

        # --- latest company URL ---
        latest_company_url = "Not available"
        try:
            first_link = exp_section.locator("xpath=.//a[contains(@href,'/company/')][1]").first
            href = first_link.get_attribute("href", timeout=2000)
            if href:
                latest_company_url = href.split("?")[0]
        except Exception:
            pass

        # --- full-time companies count ---
        full_time_companies: Set[str] = set()

        try:
            # Try standard list items
            items = exp_section.locator(
                "xpath=.//li[contains(@class, 'artdeco-list__item') or contains(@class, 'pvs-list__paged-list-item')]"
            ).all()

            # Fallback: SDUI divs
            if not items:
                items = exp_section.locator(
                    "xpath=.//div[contains(@componentkey, 'entity-collection-item')]"
                ).all()

            logger_info(f"📊 Found {len(items)} experience items to analyze")

            for idx, item in enumerate(items):
                try:
                    item_text = item.inner_text(timeout=1000)
                    if "full-time" not in item_text.lower():
                        continue

                    company_links = item.locator("xpath=.//a[contains(@href, '/company/')]").all()
                    for link in company_links:
                        href = link.get_attribute("href")
                        if href and "/company/" in href:
                            clean_url = href.split("?")[0].strip()
                            full_time_companies.add(clean_url)
                            logger_info(f"  ✅ Item {idx+1}: Found full-time company: {clean_url}")
                            break
                except Exception:
                    continue
        except Exception as e:
            logger_info(f"⚠️  Error extracting experience: {e}")

        logger_info(f"📈 Total unique full-time companies: {len(full_time_companies)}")
        return len(full_time_companies), latest_company_url

    # ---------------------------------------------------------
    # Main scrape
    # ---------------------------------------------------------
    def scrape(self, profile: str) -> Dict[str, str]:
        start = time.time()
        page = self._page

        base_url = self._normalize_profile_url(profile)

        if not self.attach:
            logger_info(f"🌐 Navigating to {base_url}")
            page.goto(base_url, wait_until="domcontentloaded")
            time.sleep(1.0)

        self._wait_profile_hydrated()

        name = self.extract_name()
        about = self.extract_about()

        full_time_count, latest_company_url = self.extract_experience_fast()

        end = time.time()

        return {
            "name": name,
            "about": about,
            "full_time_companies_count": full_time_count,
            "latest_company_url": latest_company_url,
            "scrape_time_seconds": round(end - start, 2)
        }


# ---------------------------------------------------------
# Entry point
# ---------------------------------------------------------
def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="LinkedIn scraper via Obscura + Playwright")
    parser.add_argument("--profile", required=True, help="Profile URL, ID, or 'any' in attach mode")
    parser.add_argument("--attach", action="store_true", help="Attach to already-running Obscura (fastest)")
    parser.add_argument("--headless", action="store_true", default=True, help="Run headless (default: True)")
    parser.add_argument("--no-headless", dest="headless", action="store_false")
    parser.add_argument("--stealth", action="store_true", default=True, help="Enable Obscura stealth mode")
    parser.add_argument("--no-stealth", dest="stealth", action="store_false")
    parser.add_argument("--port", type=int, default=9222, help="Obscura CDP port")
    args = parser.parse_args()

    email = os.getenv("LINKEDIN_EMAIL")
    password = os.getenv("LINKEDIN_PASSWORD")

    scraper = LinkedInObscuraScraper(
        attach=args.attach,
        headless=args.headless,
        stealth=args.stealth,
        port=args.port,
    )

    try:
        scraper.setup()
        scraper.login(email, password)

        data = scraper.scrape(args.profile)

        print(json.dumps(data, indent=2, ensure_ascii=False))

        with open("output.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger_info("✅ Results saved to output.json")

    finally:
        scraper.close()


if __name__ == "__main__":
    main()
