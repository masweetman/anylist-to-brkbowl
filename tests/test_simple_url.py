#!/usr/bin/env python
"""Simple test to understand product URL format"""

import sys
sys.path.insert(0, '/Users/mike/code/anylist-to-brkbowl')

from cart_service import CartService
import time

service = CartService()
service._start_browser()

try:
    # Go to home page
    service.page.goto("https://shop.heinzcatering.berkeleybowl.com/", wait_until="domcontentloaded")
    time.sleep(2)
    service._accept_cookies()
    
    print("✅ Home page loaded")
    print(f"URL: {service.page.url}")
    
    # Search for milk
    search_box = service.page.locator('input[type="text"]').first
    if search_box.count() > 0:
        search_box.click(click_count=3)
        time.sleep(0.3)
        search_box.type("Milk", delay=80)
        time.sleep(0.5)
        search_box.press("Enter")
        time.sleep(3)
    
    print(f"\n✅ After search:")
    print(f"URL: {service.page.url}")
    
    # Try clicking first product - look for any clickable element
    print("\nLooking for any product links or buttons...")
    all_links = service.page.locator('a')
    print(f"Total links on page: {all_links.count()}")
    
    # Look at URL pattern after search
    url = service.page.url
    if "search" in url.lower() or "query" in url.lower():
        print(f"Search results page detected: {url}")
    
finally:
    service._close_browser()
