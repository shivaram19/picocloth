"""
LinkedIn Profile Scraper – FAST OPTIMIZED VERSION (CURRENT COMPANY URL + FULLTIME COUNT + TIME)

OUTPUT FIELDS:
- name
- about
- full_time_companies_count
- latest_company_url
- scrape_time_seconds

BEST MODE:
- --attach  (skip login, fastest & stable)
"""

import os
import json
import time
import argparse
from typing import Dict, Optional, Set
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

from utils import setup_logger

logger = setup_logger()


class LinkedInScraperFast:
    def __init__(self, headless: bool = False, attach: bool = False):
        self.headless = headless
        self.attach = attach
        self.driver = None
        self.wait = None

    # ---------------------------------------------------------
    # DRIVER SETUP (FAST CONFIG)
    # ---------------------------------------------------------
    def setup_driver(self):
        chrome_options = Options()

        # ✅ SPEED UP: do not wait for full load
        chrome_options.page_load_strategy = "eager"

        # ✅ SPEED UP: block heavy content
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.managed_default_content_settings.stylesheets": 2,
            "profile.managed_default_content_settings.fonts": 2,
            "profile.default_content_setting_values.notifications": 2,
        }
        chrome_options.add_experimental_option("prefs", prefs)

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
        self.wait = WebDriverWait(self.driver, 5)

        if not self.attach:
            self.driver.maximize_window()

    # ---------------------------------------------------------
    # LOGIN (SKIPPED IN ATTACH MODE)
    # ---------------------------------------------------------
    def login(self, email: Optional[str], password: Optional[str]):
        if self.attach:
            logger.info("✅ Attach mode enabled — skipping login (FAST).")
            return

        if not email or not password:
            raise ValueError("LINKEDIN_EMAIL / LINKEDIN_PASSWORD missing in .env")

        logger.info("Logging in (non-attach mode)...")
        self.driver.get("https://www.linkedin.com/login")

        self.wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(email)
        self.driver.find_element(By.ID, "password").send_keys(password)
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # wait until feed / logged-in page loads
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(1)

    # ---------------------------------------------------------
    # FAST HELPERS
    # ---------------------------------------------------------
    def _open(self, url: str):
        self.driver.get(url)
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    # ---------------------------------------------------------
    # SCRAPE: NAME
    # ---------------------------------------------------------
    def extract_name(self) -> str:
        # Strategy 1: document title (Fastest & Most Reliable)
        try:
            title = self.driver.title
            if " | LinkedIn" in title:
                raw_name = title.split(" | LinkedIn")[0].strip()
                # Remove notification count prefix like "(6) " if present
                import re
                clean_name = re.sub(r'^\(\d+\)\s*', '', raw_name)
                return clean_name
        except Exception:
            pass

        # Strategy 2: h1 tag
        try:
            el = self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
            name = el.text.strip()
            if name:
                return name
        except Exception:
            pass
            
        return "Not available"

    # ---------------------------------------------------------
    # SCRAPE: ABOUT (FAST)
    # ---------------------------------------------------------
    def extract_about(self) -> str:
        """
        Fast strategy: check specific ID or commonly used ids for 'about' section
        """
        try:
            # 1. Look for the section with id='about' and get the text within
            # reliable anchor: <section id="about"> ... <div class="inline-show-more-text">
            # Sometimes id="about" is on the div above the section
            about_section = self.driver.find_elements(By.XPATH, "//*[@id='about']/following-sibling::div//div[contains(@class, 'inline-show-more-text')]")
            if not about_section:
                 about_section = self.driver.find_elements(By.XPATH, "//*[@id='about']/parent::*//div[contains(@class, 'inline-show-more-text')]")
            
            if about_section:
                return about_section[0].text.strip()

            if about_section:
                return about_section[0].text.strip()

            # 2. Fallback: Search by text header (original method)
            # Try to be more specific to avoid timeouts or wrong elements
            about_xpaths = [
                "//section[.//h2//span[contains(text(), 'About')]]//div[contains(@class,'inline-show-more-text')]",
                "//div[@id='about']/following-sibling::div//div[contains(@class, 'inline-show-more-text')]",
            ]
            for xp in about_xpaths:
                try:
                    els = self.driver.find_elements(By.XPATH, xp)
                    if els:
                        txt = els[0].text.strip()
                        if txt:
                            return txt
                except Exception:
                    continue
        except Exception:
            pass

        return "Not available"

    # ---------------------------------------------------------
    # EXPERIENCE (DETAILS PAGE)
    # - full-time company count
    # - latest/current company URL
    # ---------------------------------------------------------
    def extract_experience_fast(self, profile_url: str) -> Dict[str, str]:
        """
        Fast & minimal:
        - Go directly to /details/experience/
        - Collect only:
            ✅ unique company names with "Full-time"
            ✅ first company link containing '/company/' where 'Present' exists
        """
        base = profile_url.rstrip("/")
        exp_url = f"{base}/details/experience/"
        self._open(exp_url)

        full_time_companies: Set[str] = set()
        latest_company_url = "Not available"
        items = []

        try:
            # Scroll to trigger lazy loading (crucial for SDUI)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            self.driver.execute_script("window.scrollTo(0, 0);")
            
            # 1. Try to find the specific experience section container
            section = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, "//div[contains(@data-testid, 'ExperienceDetailsSection')]")
            ))
            
            # 2. Try standard list items (artdeco)
            items = section.find_elements(By.XPATH, ".//li[contains(@class,'artdeco-list__item')]")
            
            # 3. Fallback: SDUI often uses divs instead of lis
            if not items:
                items = section.find_elements(By.XPATH, ".//div[contains(@class,'display-flex')]")
                
        except Exception as e:
            logger.warning(f"Could not find experience items: {e}")
            # Debug: save page source
            with open("debug_experience_page.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            logger.info("Saved debug_experience_page.html")

        # Process items if found
        for item in items:
            try:
                item_text = item.text
                
                # Check for "Full-time" usage (case-insensitive)
                item_text_lower = item_text.lower()
                if "full-time" not in item_text_lower and "full time" not in item_text_lower:
                    continue

                # Capture visible spans
                spans = item.find_elements(By.XPATH, ".//span[@aria-hidden='true']")
                texts = [s.text.strip() for s in spans if s.text.strip()]

                if len(texts) >= 2:
                    t0 = texts[0]
                    t1 = texts[1]
                    
                    is_duration_t1 = any(unit in t1 for unit in [" yr", " mo"]) and any(c.isdigit() for c in t1)
                    
                    if is_duration_t1:
                        company = t0
                    else:
                        if "·" in t1:
                            company = t1.split("·")[0].strip()
                        else:
                            company = t1

                    if company and len(company) > 1 and not any(char.isdigit() for char in company):
                        full_time_companies.add(company)

                if ("Present" in item_text) and (latest_company_url == "Not available"):
                    try:
                        a_links = item.find_elements(By.XPATH, ".//a[contains(@href,'/company/')]")
                        for a in a_links:
                            href = a.get_attribute("href")
                            if href:
                                if href.startswith("/"):
                                    href = "https://www.linkedin.com" + href
                                latest_company_url = href.strip()
                                break
                    except Exception:
                        pass

            except Exception:
                continue

        return {
            "full_time_companies_count": str(len(full_time_companies)),
            "latest_company_url": latest_company_url
        }

    # ---------------------------------------------------------
    # MAIN
    # ---------------------------------------------------------
    def scrape_profile(self, profile_url: str) -> Dict[str, str]:
        # Open profile page once
        self._open(profile_url)

        name = self.extract_name()
        about = self.extract_about()

        # Experience details page scrape (fast)
        logger.info(f"Navigating to Experience Section: {profile_url.rstrip('/')}/details/experience/")
        exp = self.extract_experience_fast(profile_url)

        return {
            "name": name,
            "about": about,
            "full_time_companies_count": int(exp["full_time_companies_count"]),
            "latest_company_url": exp["latest_company_url"]
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
    parser.add_argument("--profile", required=True, help="LinkedIn profile URL")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--attach", action="store_true", help="Attach to already logged-in Chrome (FASTEST)")
    args = parser.parse_args()

    email = os.getenv("LINKEDIN_EMAIL")
    password = os.getenv("LINKEDIN_PASSWORD")

    scraper = LinkedInScraperFast(headless=args.headless, attach=args.attach)

    try:
        t0 = time.perf_counter()

        scraper.setup_driver()
        scraper.login(email, password)
        data = scraper.scrape_profile(args.profile)

        t1 = time.perf_counter()
        data["scrape_time_seconds"] = round(t1 - t0, 2)

        print(json.dumps(data, indent=2, ensure_ascii=False))

        with open("output.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info("✅ Results saved to output.json")

    finally:
        scraper.close()


if __name__ == "__main__":
    main()
