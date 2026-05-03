"""
Quick validation script for Obscura + Playwright integration.

Usage:
    python test_obscura.py

This will:
  1. Locate the Obscura binary
  2. Start Obscura in serve mode (if not already running)
  3. Connect Playwright over CDP
  4. Fetch example.com and print the title
  5. Tear everything down
"""

import sys
from obscura_manager import ObscuraManager


def main():
    print("=" * 60)
    print("Obscura + Playwright Integration Test")
    print("=" * 60)

    # 1. Check binary
    binary = ObscuraManager._find_binary()
    if not binary:
        print("\n❌ Obscura binary NOT found.")
        print("   Download or build it first. See OBSCURA.md for instructions.\n")
        sys.exit(1)
    print(f"\n✅ Found Obscura binary: {binary}")

    # 2. Start server & connect via Playwright
    try:
        with ObscuraManager(port=9222, stealth=True, verbose=True) as mgr:
            print(f"\n✅ Obscura server ready on port {mgr.port}")

            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(
                    f"ws://127.0.0.1:{mgr.port}"
                )
                print("✅ Playwright connected to Obscura over CDP")

                context = browser.new_context()
                page = context.new_page()

                print("\n🌐 Fetching https://example.com ...")
                page.goto("https://example.com", wait_until="domcontentloaded")
                title = page.title()
                print(f"✅ Page title: '{title}'")

                # Quick JS eval test
                h1_text = page.evaluate("() => document.querySelector('h1')?.innerText")
                print(f"✅ JS eval h1 text: '{h1_text}'")

                page.close()
                context.close()
                browser.close()

            print("\n" + "=" * 60)
            print("🎉 All tests passed! Obscura + Playwright are working.")
            print("=" * 60)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
