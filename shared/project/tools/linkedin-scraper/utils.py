"""
Utility functions for LinkedIn scraper
"""

import time
import logging
from typing import Optional
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException


def setup_logger() -> logging.Logger:
    """
    Setup and configure logger
    
    Returns:
        Configured logger instance
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)


def scroll_to_load_content(driver, logger, scrolls: int = 5, delay: float = 1.5):
    """
    Scroll down the page to load dynamic content
    
    Args:
        driver: Selenium WebDriver instance
        logger: Logger instance
        scrolls: Number of scrolls to perform
        delay: Delay between scrolls in seconds
    """
    logger.info("Scrolling to load dynamic content...")
    
    for i in range(scrolls):
        # Scroll down
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(delay)
        
        # Scroll up a bit
        driver.execute_script("window.scrollBy(0, -500);")
        time.sleep(delay / 2)
    
    # Scroll back to top
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)
    
    logger.info("Scrolling complete")


def safe_extract_text(driver, by: By, selector: str, logger, timeout: int = 5) -> str:
    """
    Safely extract text from an element
    
    Args:
        driver: Selenium WebDriver instance
        by: Selenium By locator type
        selector: Element selector
        logger: Logger instance
        timeout: Maximum time to wait for element
        
    Returns:
        Extracted text or "Not available" if not found
    """
    try:
        element = driver.find_element(by, selector)
        text = element.text.strip()
        return text if text else "Not available"
    except NoSuchElementException:
        return "Not available"
    except Exception as e:
        logger.debug(f"Error extracting text with selector '{selector}': {str(e)}")
        return "Not available"


def wait_and_click(driver, by: By, selector: str, logger, timeout: int = 10) -> bool:
    """
    Wait for element and click it
    
    Args:
        driver: Selenium WebDriver instance
        by: Selenium By locator type
        selector: Element selector
        logger: Logger instance
        timeout: Maximum time to wait
        
    Returns:
        True if clicked successfully, False otherwise
    """
    try:
        element = driver.find_element(by, selector)
        driver.execute_script("arguments[0].click();", element)
        return True
    except Exception as e:
        logger.debug(f"Could not click element '{selector}': {str(e)}")
        return False


def expand_section(driver, section_name: str, logger) -> bool:
    """
    Expand a collapsible section by clicking "Show more" button
    
    Args:
        driver: Selenium WebDriver instance
        section_name: Name of the section to expand
        logger: Logger instance
        
    Returns:
        True if expanded, False otherwise
    """
    try:
        # Common "Show more" button selectors
        selectors = [
            f"div#{section_name} ~ div button[aria-expanded='false']",
            f"section#{section_name}-section button.pv-profile-section__see-more-inline",
            "button.inline-show-more-text__button"
        ]
        
        for selector in selectors:
            if wait_and_click(driver, By.CSS_SELECTOR, selector, logger):
                time.sleep(1)
                return True
                
        return False
        
    except Exception as e:
        logger.debug(f"Could not expand section '{section_name}': {str(e)}")
        return False
