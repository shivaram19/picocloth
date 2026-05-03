#!/usr/bin/env python3
"""
Test suite for the LinkedIn Outreach Bot.

Tests:
1. Import validation
2. Target JSON parsing
3. Message generation
4. Browser initialization
5. Dry-run flow (no actual LinkedIn interaction)
"""

import os
import sys
import json
import unittest
from unittest.mock import Mock, patch, MagicMock

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from outreach_bot import LinkedInOutreachBot, human_delay, DAILY_CONNECT_LIMIT


class TestOutreachBot(unittest.TestCase):

    def setUp(self):
        self.bot = LinkedInOutreachBot(headless=True, dry_run=True)

    def tearDown(self):
        if self.bot.driver:
            self.bot.driver.quit()

    def test_01_imports(self):
        """All modules import correctly."""
        print("\n✓ Test 01: Imports OK")

    def test_02_targets_json_valid(self):
        """Targets JSON is valid and contains required fields."""
        with open("targets.json", "r") as f:
            data = json.load(f)

        targets = data.get("targets", [])
        self.assertGreater(len(targets), 0, "No targets found")

        required_fields = ["name", "profile_url", "company", "priority", "connection_message"]
        for target in targets:
            for field in required_fields:
                self.assertIn(field, target, f"Missing field '{field}' in target {target.get('name')}")

        print(f"✓ Test 02: Targets JSON valid ({len(targets)} targets)")

    def test_03_message_generation(self):
        """Message generation produces non-empty personalized messages."""
        target = {
            "name": "Test User",
            "company": "TestCorp",
            "priority": "high",
            "connection_message": ""
        }
        profile_data = {
            "name": "Test User",
            "company": "TestCorp Inc"
        }

        message = self.bot._generate_message(target, profile_data)
        self.assertIsNotNone(message)
        self.assertGreater(len(message), 20)
        self.assertIn("Test", message)

        # Test with custom message
        target["connection_message"] = "Hi Test, custom message here."
        message2 = self.bot._generate_message(target, profile_data)
        # _generate_message ignores connection_message field; that's handled in process_targets
        # So it should still generate from template
        self.assertIn("Test", message2)

        print("✓ Test 03: Message generation OK")

    def test_04_browser_initialization(self):
        """Chrome WebDriver initializes successfully."""
        self.bot.setup_driver()
        self.assertIsNotNone(self.bot.driver)
        self.assertIsNotNone(self.bot.wait)

        # Test navigation to a simple page
        self.bot.driver.get("https://example.com")
        self.assertIn("Example Domain", self.bot.driver.title)

        print("✓ Test 04: Browser initialization OK")

    def test_05_dry_run_mode(self):
        """Dry-run mode skips actual LinkedIn interactions."""
        self.assertTrue(self.bot.dry_run)

        # In dry-run, login should return True without doing anything
        result = self.bot.login("fake@email.com", "fakepass")
        self.assertTrue(result)

        # In dry-run, connection request should log but not send
        result = self.bot.send_connection_request(
            "https://linkedin.com/in/test", "Test message"
        )
        self.assertTrue(result)
        self.assertEqual(self.bot.connections_sent_today, 0)

        print("✓ Test 05: Dry-run mode OK")

    def test_06_daily_limit(self):
        """Daily connection limit is enforced."""
        self.bot.connections_sent_today = DAILY_CONNECT_LIMIT
        self.bot.dry_run = False  # Temporarily disable dry-run to test limit

        result = self.bot.send_connection_request(
            "https://linkedin.com/in/test", "Test message"
        )
        self.assertFalse(result)

        self.bot.dry_run = True
        print("✓ Test 06: Daily limit enforcement OK")

    def test_07_profile_scrape_simulation(self):
        """Profile scraping with mocked driver."""
        self.bot.setup_driver()
        self.bot.driver.get("https://example.com")

        # Mock the page as a LinkedIn profile
        self.bot.driver.execute_script("""
            document.body.innerHTML = `
                <h1>John Doe</h1>
                <div class="text-body-medium">CEO at TestCorp</div>
                <section>
                    <h2><span>About</span></h2>
                    <div class="inline-show-more-text">Experienced leader in construction tech.</div>
                </section>
                <section>
                    <h2><span>Experience</span></h2>
                    <a href="/company/testcorp/">TestCorp</a>
                </section>
            `;
        """)

        name = self.bot._extract_name()
        self.assertEqual(name, "John Doe")

        headline = self.bot._extract_headline()
        self.assertIn("CEO", headline)

        about = self.bot._extract_about()
        self.assertIn("construction", about)

        company = self.bot._extract_current_company()
        self.assertIn("TestCorp", company)

        print("✓ Test 07: Profile scrape simulation OK")

    def test_08_logger(self):
        """Logger creates files and tracks stats."""
        self.bot.logger.log("TEST_EVENT", {"key": "value"})
        self.bot.logger.save_stats()

        self.assertTrue(os.path.exists("outreach_log.jsonl"))
        self.assertTrue(os.path.exists("outreach_stats.json"))

        with open("outreach_stats.json", "r") as f:
            stats = json.load(f)
        self.assertIn("started_at", stats)

        print("✓ Test 08: Logger OK")


def run_tests():
    print("="*60)
    print("LINKEDIN OUTREACH BOT — TEST SUITE")
    print("="*60)

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestOutreachBot)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*60)
    if result.wasSuccessful():
        print("ALL TESTS PASSED ✅")
    else:
        print(f"TESTS FAILED: {len(result.failures)} failures, {len(result.errors)} errors")
    print("="*60)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
