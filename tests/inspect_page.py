#!/usr/bin/env python
"""Inspect the Berkeley Bowl website for the correct selectors"""

import sys
sys.path.insert(0, '/Users/mike/code/anylist-to-brkbowl')

from cart_service import CartService
import time

print("🔍 Inspecting Berkeley Bowl website...")
print("=" * 50)

try:
    service = CartService()
    service._start_browser()
    
    print("\n📍 Navigating to Berkeley Bowl...")
    service.page.goto("https://shop.heinzcatering.berkeleybowl.com/", wait_until="domcontentloaded")
    time.sleep(3)
    
    # Save HTML to file for inspection
    html_content = service.page.content()
    with open("page_content.html", "w") as f:
        f.write(html_content)
    print("✅ Saved page content to page_content.html")
    
    # Take a screenshot
    service.page.screenshot(path="page_screenshot.png")
    print("✅ Saved screenshot to page_screenshot.png")
    
    # Try to find search input with different selectors
    print("\n🔎 Searching for input elements...")
    inputs = service.page.locator("input").count()
    print(f"   Found {inputs} input elements")
    
    # Log all inputs with their attributes
    for i in range(min(inputs, 5)):  # Show first 5
        try:
            input_elem = service.page.locator("input").nth(i)
            input_type = input_elem.get_attribute("type") or ""
            input_placeholder = input_elem.get_attribute("placeholder") or ""
            input_name = input_elem.get_attribute("name") or ""
            print(f"   [{i}] type='{input_type}' placeholder='{input_placeholder}' name='{input_name}'")
        except:
            pass
    
    # Try to find search button
    print("\n🔎 Searching for buttons...")
    buttons = service.page.locator("button").count()
    print(f"   Found {buttons} button elements")
    
    # Wait for user to inspect
    print("\n⏳ Keeping browser open for 15 seconds for manual inspection...")
    time.sleep(15)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    service._close_browser()
    print("✅ Browser closed")
