"""
LinkedIn Profile Scraper – FAST FINAL (Attach Mode Optimized)

OUTPUT FIELDS:
- name
- about
- full_time_companies_count
- latest_company_url
- scrape_time_seconds

RUN:
python scraper_fast.py --profile "any" --attach
"""

import os
import re
import json
import time
import argparse
from typing import Tuple, Set
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


# ---------------------------------------------------------
# LOGGER (simple)
# ---------------------------------------------------------
def logger_info(msg: str):
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - INFO - {msg}")


# ---------------------------------------------------------
# SCRAPER CLASS
# ---------------------------------------------------------
class LinkedInFastScraper:

    def __init__(self, headless: bool = False, attach: bool = False):
        self.headless = headless
        self.attach = attach
        self.driver = None
        self.wait = None

    # ---------------------------------------------------------
    # DRIVER SETUP
    # ---------------------------------------------------------
    def setup_driver(self):
        chrome_options = Options()

        if self.attach:
            chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        else:
            if self.headless:
                chrome_options.add_argument("--headless=new")

            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option("useAutomationExtension", False)

        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)

        if not self.attach:
            self.driver.maximize_window()

    # ---------------------------------------------------------
    # LOGIN (only if not attach)
    # ---------------------------------------------------------
    def login(self, email: str, password: str):
        if self.attach:
            logger_info("✅ Attach mode enabled — skipping login.")
            return

        logger_info("🔐 Opening LinkedIn login...")
        self.driver.get("https://www.linkedin.com/login")
        time.sleep(1.5)

        self.wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(email)
        self.driver.find_element(By.ID, "password").send_keys(password)
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(4)

    # ---------------------------------------------------------
    # HELPERS
    # ---------------------------------------------------------
    def _get_base_profile_url(self, profile: str) -> str:
        """
        Accepts:
        - "any" in attach mode means: use current tab
        - full profile URL
        - profile id (nitishchoudhary)

        Returns:
        - normalized base profile URL: https://www.linkedin.com/in/<id>/
        """
        if self.attach:
            current = self.driver.current_url
            logger_info(f"🔎 Current tab URL: {current}")
            logger_info(f"🔎 Current tab TITLE: {self.driver.title}")

            # If user passed "any", just use current tab url
            if profile.strip().lower() == "any":
                # if user already opened /details/experience/ remove it
                current = re.sub(r"/details/experience/?$", "/", current)
                current = re.sub(r"/recent-activity/.*$", "/", current)
                current = current.split("?")[0]

                if "/in/" in current:
                    if not current.endswith("/"):
                        current += "/"
                    logger_info(f"✅ Using base profile URL: {current}")
                    return current

        # if full url given
        if profile.startswith("http"):
            base = profile.split("?")[0].strip()
            # normalize by removing extra paths
            if "/details/" in base:
                base = base.split("/details/")[0] + "/"
            if "/recent-activity" in base:
                base = base.split("/recent-activity")[0] + "/"

            if not base.endswith("/"):
                base += "/"
            return base

        # if only id provided
        return f"https://www.linkedin.com/in/{profile.strip().strip('/')}/"

    def _wait_profile_hydrated(self):
        """
        Wait for profile top section loaded.
        Handles both classic UI (h1) and SDUI (h2).
        """
        # First wait for main content area
        try:
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "main")))
        except Exception:
            # Fallback to body
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Then wait for name element (try multiple selectors)
        name_selectors = [
            "//h1",  # Classic LinkedIn
            "//h2[contains(@class, 'bc8ea8e7') or contains(@class, '_478c24fe')]",  # SDUI
            "//*[@role='main']//h2[1]",  # SDUI fallback
        ]
        
        for selector in name_selectors:
            try:
                self.driver.find_element(By.XPATH, selector)
                return  # Found it, exit
            except Exception:
                continue
        
        # If none found, just wait a bit and continue (profile might be loaded)
        time.sleep(1)

    def _fast_scroll(self, px: int = 1500):
        self.driver.execute_script(f"window.scrollBy(0, {px});")

    def _scroll_until_experience(self, max_tries: int = 5) -> bool:
        """
        Fast scroll until Experience section exists.
        """
        for _ in range(max_tries):
            try:
                self.driver.find_element(By.XPATH, "//section[.//h2[normalize-space()='Experience']]")
                return True
            except Exception:
                self._fast_scroll(2000)
                time.sleep(0.2)

        return False

    # ---------------------------------------------------------
    # BASIC EXTRACTION
    # ---------------------------------------------------------
    def extract_name(self) -> str:
        """
        Extract name from profile - handles both classic UI and SDUI.
        """
        selectors = [
            "//h1",  # Classic LinkedIn
            "//h2[contains(@class, 'bc8ea8e7')]",  # SDUI primary
            "//h2[contains(@class, '_478c24fe')]",  # SDUI alternative
            "//h2[contains(@class, '_9113d2b2')]",  # SDUI another variant
            "//*[@role='main']//h2[normalize-space()]",  # SDUI fallback
        ]
        
        for selector in selectors:
            try:
                el = self.driver.find_element(By.XPATH, selector)
                name = el.text.strip()
                
                # Filter out false positives
                if not name or len(name) < 3:
                    continue
                    
                # Skip if contains these keywords
                skip_keywords = ["notification", "LinkedIn", "message", "connection", "·"]
                if any(kw.lower() in name.lower() for kw in skip_keywords):
                    continue
                
                # Skip if it's mostly numbers
                if sum(c.isdigit() for c in name) > len(name) / 2:
                    continue
                
                return name
            except Exception:
                continue
        
        return "Not available"

    def extract_about(self) -> str:
        try:
            sec = self.driver.find_element(By.XPATH, "//section[.//h2[normalize-space()='About']]")
            txt = sec.text.replace("About", "").strip()
            return txt
        except Exception:
            return "Not available"

    # ---------------------------------------------------------
    # EXPERIENCE EXTRACTION (FAST + ACCURATE FULL-TIME COUNT)
    # ---------------------------------------------------------
    def extract_experience_fast(self) -> Tuple[int, str]:
        """
        Returns:
          (full_time_companies_count, latest_company_url)

        ✅ latest_company_url:
            first company link inside experience section

        ✅ full_time_companies_count:
            unique companies where at least one role contains "Full-time"
            (handles multi-role companies like CRED)
        """
        found = self._scroll_until_experience()
        if not found:
            return 0, "Not available"

        try:
            exp_section = self.driver.find_element(By.XPATH, "//section[.//h2[normalize-space()='Experience']]")
        except Exception:
            return 0, "Not available"

        # -------------------------------
        # 1) latest company URL
        # -------------------------------
        latest_company_url = "Not available"
        try:
            first_company = exp_section.find_element(By.XPATH, ".//a[contains(@href,'/company/')][1]")
            href = first_company.get_attribute("href")
            if href:
                latest_company_url = href.split("?")[0]
        except Exception:
            pass

        # -------------------------------
        # 2) FULL-TIME COMPANIES COUNT (IMPROVED ✅)
        # -------------------------------
        full_time_companies: Set[str] = set()

        try:
            # Strategy: Find all experience list items, check each for "Full-time"
            # Use multiple selectors to catch different LinkedIn layouts
            
            # Try standard list items first
            items = exp_section.find_elements(
                By.XPATH,
                ".//li[contains(@class, 'artdeco-list__item') or contains(@class, 'pvs-list__paged-list-item')]"
            )
            
            # Fallback: try div-based items (SDUI)
            if not items:
                items = exp_section.find_elements(
                    By.XPATH,
                    ".//div[contains(@componentkey, 'entity-collection-item')]"
                )
            
            logger_info(f"📊 Found {len(items)} experience items to analyze")
            
            for idx, item in enumerate(items):
                try:
                    item_text = item.text
                    
                    # Check if this item contains "Full-time" (case-insensitive)
                    if "full-time" not in item_text.lower():
                        continue
                    
                    # Find company link within this item
                    company_links = item.find_elements(By.XPATH, ".//a[contains(@href, '/company/')]")
                    
                    for link in company_links:
                        href = link.get_attribute("href")
                        if href and "/company/" in href:
                            # Clean URL (remove query params)
                            clean_url = href.split("?")[0].strip()
                            full_time_companies.add(clean_url)
                            logger_info(f"  ✅ Item {idx+1}: Found full-time company: {clean_url}")
                            break  # Only take first company link per item
                    
                except Exception as e:
                    continue
                    
        except Exception as e:
            logger_info(f"⚠️  Error extracting full-time companies: {e}")

        logger_info(f"📈 Total unique full-time companies: {len(full_time_companies)}")
        return len(full_time_companies), latest_company_url

    # ---------------------------------------------------------
    # MAIN SCRAPE
    # ---------------------------------------------------------
    def scrape(self, profile: str):
        start = time.time()

        base_url = self._get_base_profile_url(profile)

        # IMPORTANT:
        # In attach mode user already opened profile, so don't reload
        if not self.attach:
            self.driver.get(base_url)
            time.sleep(1.0)

        # wait for page hydrated
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

    def close(self):
        if self.driver and not self.attach:
            self.driver.quit()


# ---------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------
def main():
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True, help="profile URL or id or 'any' in attach mode")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--attach", action="store_true")
    args = parser.parse_args()

    email = os.getenv("LINKEDIN_EMAIL")
    password = os.getenv("LINKEDIN_PASSWORD")

    scraper = LinkedInFastScraper(headless=args.headless, attach=args.attach)

    try:
        scraper.setup_driver()
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
