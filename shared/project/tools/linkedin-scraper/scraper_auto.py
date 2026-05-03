"""
LinkedIn Profile Scraper – AUTO MODE (Navigate to any profile)

This version uses robust extraction logic identical to scraper_fast.py
but includes automatic navigation and 'Show more' button handling.

OUTPUT FIELDS:
- name
- about
- full_time_companies_count
- latest_company_url
- scrape_time_seconds

USAGE:
python scraper_auto.py --profile "https://www.linkedin.com/in/nitishchoudhary/" --attach
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
class LinkedInAutoScraper:

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
            logger_info("🔗 Attaching to Chrome on port 9222...")
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
        
        logger_info("✅ Driver ready")

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
    def _normalize_profile_url(self, profile: str) -> str:
        """
        Accepts:
        - full profile URL: https://www.linkedin.com/in/nitishchoudhary/
        - profile id: nitishchoudhary
        
        Returns:
        - normalized base profile URL: https://www.linkedin.com/in/<id>/
        """
        # If full URL given
        if profile.startswith("http"):
            base = profile.split("?")[0].strip()
            # Remove extra paths
            if "/details/" in base:
                base = base.split("/details/")[0] + "/"
            if "/recent-activity" in base:
                base = base.split("/recent-activity")[0] + "/"
            if not base.endswith("/"):
                base += "/"
            return base

        # If only id provided
        profile_id = profile.strip().strip('/')
        return f"https://www.linkedin.com/in/{profile_id}/"

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
            try:
                self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            except:
                pass
        
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

    def _click_show_more_buttons(self, max_clicks: int = 5):
        """
        Click all "Show more" and "Load more results" buttons on the page.
        This is needed on /details/experience/ page to reveal all items.
        """
        clicked_count = 0
        
        for attempt in range(max_clicks):
            clicked_in_this_round = False
            
            # Scroll down a bit to trigger lazy loading
            self._fast_scroll(800)
            time.sleep(0.5)
            
            # Try different button selectors
            button_xpaths = [
                "//button[contains(., 'Show more')]",
                "//button[contains(., 'Load more')]",
                "//button[contains(@aria-label, 'Show more')]",
                "//button[contains(@aria-label, 'Load more')]",
                "//button[contains(@class, 'scaffold-finite-scroll__load-button')]"
            ]
            
            for xpath in button_xpaths:
                try:
                    buttons = self.driver.find_elements(By.XPATH, xpath)
                    for btn in buttons:
                        if btn.is_displayed() and btn.is_enabled():
                            try:
                                # Use JavaScript click to avoid interception issues
                                self.driver.execute_script("arguments[0].click();", btn)
                                clicked_count += 1
                                clicked_in_this_round = True
                                logger_info(f"  ✅ Clicked button #{clicked_count}")
                                time.sleep(1.5)  # Wait for content to load
                            except Exception:
                                continue
                except Exception:
                    continue
            
            # If no buttons clicked in this round, likely done
            if not clicked_in_this_round:
                # One last check after a bigger scroll
                self._fast_scroll(1500)
                time.sleep(0.5)
        
        if clicked_count > 0:
            logger_info(f"✅ Clicked {clicked_count} 'Show more' buttons total")

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
        """
        Robust About extraction:
        1. Force load entire page (scroll to bottom).
        2. Scroll back up.
        3. Scan diligently for About section.
        """
        logger_info("📝 Hunting for About section...")
        
        # FORCE LOAD: Scroll to bottom to trigger all lazy components
        logger_info("  ...Triggering lazy load (scrolling to bottom)")
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # Scroll back to top
        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)

        found_text = "Not available"
        
        # Max scroll attempts
        max_scrolls = 10
        scroll_step = 400

        for i in range(max_scrolls):
            try:
                # ---------------------------------------------------------
                # STRATEGY FROM SCRAPER.PY (Most Reliable ID-based)
                # ---------------------------------------------------------
                # 1. Look for id='about' which is the standard anchor
                about_section = self.driver.find_elements(By.XPATH, "//*[@id='about']/following-sibling::div//div[contains(@class, 'inline-show-more-text')]")
                if not about_section:
                     about_section = self.driver.find_elements(By.XPATH, "//*[@id='about']/parent::*//div[contains(@class, 'inline-show-more-text')]")
                
                if about_section:
                    txt = about_section[0].text.strip()
                    if txt:
                        logger_info(f"  ✅ Found About via ID selector ({len(txt)} chars)")
                        return txt

                # ---------------------------------------------------------
                # STRATEGY 2: Header Scan
                # ---------------------------------------------------------
                # Try finding standard About Section Header
                # We use a broad XPath to find the 'About' text which is usually a header (h2, span, div)
                headers = self.driver.find_elements(By.XPATH, 
                    "//*[self::h2 or self::span or self::div][normalize-space()='About']"
                )
                
                for header in headers:
                    # Logic: Verify this is actually a section header
                    # Usually it's inside a section or a main card div
                    try:
                        # Get the parent container (likely the card)
                        parent = header.find_element(By.XPATH, "./ancestor::section[1] | ./ancestor::div[contains(@class, 'artdeco-card')][1]")
                        
                        # Check if visible
                        if not parent.is_displayed():
                            continue

                        # Scroll to it to ensure text renders
                        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", parent)
                        time.sleep(0.5)

                        # Check for "see more" button and click it
                        try:
                            # Standard "see more" or "...more" buttons
                            buttons = parent.find_elements(By.XPATH, ".//button[contains(., 'more')]")
                            for btn in buttons:
                                if btn.is_displayed():
                                    self.driver.execute_script("arguments[0].click();", btn)
                                    time.sleep(0.2)
                        except:
                            pass
                        
                        # Get text
                        # Search for the inline text container specifically first
                        try:
                            inline_text = parent.find_element(By.XPATH, ".//div[contains(@class, 'inline-show-more-text')]")
                            return inline_text.text.strip()
                        except:
                            pass

                        raw_text = parent.text
                        
                        # Clean it up
                        # Remove the word "About" from the start
                        # Remove "Top skills" section if present
                        lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
                        clean_lines = []
                        for line in lines:
                            if line.lower() == "about": continue
                            if "see more" in line.lower(): continue
                            if "top skills" in line.lower(): break # Stop if we hit Top Skills
                            clean_lines.append(line)
                        
                        full_text = "\n".join(clean_lines).strip()
                        
                        if len(full_text) > 10:
                            logger_info(f"  ✅ Found About section at scroll step {i} ({len(full_text)} chars)")
                            return full_text

                    except Exception as e:
                        # Element might be stale or not a true parent
                        continue
            
            except Exception:
                pass

            # Scroll down for next attempt
            # logger_info(f"  ...scanning for About (scroll {i+1}/{max_scrolls})")
            self.driver.execute_script(f"window.scrollBy(0, {scroll_step});")
            time.sleep(0.5)

        return "Not available"

    # ---------------------------------------------------------
    # EXPERIENCE EXTRACTION
    # ---------------------------------------------------------
    def extract_experience_from_details_page(self) -> Tuple[int, str]:
        """
        Extract experience from /details/experience/ page.
        This page has a different structure than the main profile.
        """
        latest_company_url = "Not available"
        full_time_companies: Set[str] = set()

        try:
            # On details page, look for the main container
            # Try multiple selectors
            items = self.driver.find_elements(
                By.XPATH,
                "//li[contains(@class, 'artdeco-list__item') or contains(@class, 'pvs-list__paged-list-item')]"
            )
            
            if not items:
                # Fallback for SDUI
                items = self.driver.find_elements(
                    By.XPATH,
                    "//div[contains(@componentkey, 'entity-collection-item')]"
                )
            
            logger_info(f"📊 Found {len(items)} experience items on details page")
            
            # Get first company URL
            try:
                # Look for the first company link in the list
                first_link = self.driver.find_element(By.XPATH, "(//li[1]//a[contains(@href, '/company/')])[1]")
                href = first_link.get_attribute("href")
                if href:
                    latest_company_url = href.split("?")[0]
            except Exception:
                pass
            
            # Count full-time companies
            for idx, item in enumerate(items):
                try:
                    item_text = item.text
                    
                    if "full-time" not in item_text.lower():
                        continue
                    
                    company_links = item.find_elements(By.XPATH, ".//a[contains(@href, '/company/')]")
                    
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
            logger_info(f"⚠️  Error extracting from details page: {e}")

        logger_info(f"📈 Total unique full-time companies: {len(full_time_companies)}")
        return len(full_time_companies), latest_company_url

    # ---------------------------------------------------------
    # MAIN SCRAPE
    # ---------------------------------------------------------
    def scrape(self, profile: str):
        start = time.time()

        # Normalize profile URL
        profile_url = self._normalize_profile_url(profile)
        logger_info(f"🌐 Navigating to: {profile_url}")
        
        # Navigate to main profile first
        self.driver.get(profile_url)
        time.sleep(3)

        # Wait for page hydrated
        self._wait_profile_hydrated()

        # Extract name from main profile
        name = self.extract_name()
        
        # IMPORTANT: Scroll down to load About section
        logger_info("📜 Scrolling diligently to load About section...")
        for i in range(6):  # Increased from 4 to 6
            self._fast_scroll(1000)
            time.sleep(0.8)  # Increased from 0.5 to 0.8
        
        # Scroll back to top
        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1.5)
        
        # Extract about from main profile
        about = self.extract_about()

        # NEW STRATEGY: Navigate to /details/experience/ page directly
        # This is more reliable than scrolling on main profile for experience
        exp_url = profile_url.rstrip('/') + '/details/experience/'
        logger_info(f"🔍 Navigating to experience page: {exp_url}")
        
        self.driver.get(exp_url)
        time.sleep(3)
        
        # Wait for experience page to load
        try:
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "main")))
        except Exception:
            pass
        
        # IMPORTANT: Click "Show more" / "Load more results" buttons
        logger_info("🔘 Clicking 'Show more' buttons to load all experience...")
        self._click_show_more_buttons(max_clicks=5)
        
        # Scroll to bottom to ensure all lazy loaded items appear
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.5)

        # Extract experience from details page
        full_time_count, latest_company_url = self.extract_experience_from_details_page()

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
    parser.add_argument("--profile", required=True, help="LinkedIn profile URL or profile ID")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--attach", action="store_true", help="Attach to already logged-in Chrome")
    args = parser.parse_args()

    email = os.getenv("LINKEDIN_EMAIL")
    password = os.getenv("LINKEDIN_PASSWORD")

    scraper = LinkedInAutoScraper(headless=args.headless, attach=args.attach)

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